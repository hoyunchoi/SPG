import re
import colorama
import subprocess
import argparse
from typing import Optional
from termcolor import colored
from collections import Counter

from Job import Job


class Machine:
    """ Save the information of each machine """

    def __init__(self, information: str) -> None:
        information = information.strip().split("|")

        # 0.Use|#1.Name|#2.CPU|#3.nCore|#4.Memory
        self.use = bool(int(information[0]))    # Whether to be used or not: 1 for use, 0 for not use
        self.name = information[1]              # Name of machine. ex) tenet1
        self.cpu = information[2]               # Name of cpu inside machine
        self.nCore = int(information[3])        # Number of cores inside machine
        self.memory = information[4]            # Size of memory inside machine

        # Current job information
        self.jobList: list[Job] = []            # List of running jobs
        self.nJob: int = 0                      # Number of running jobs = len(jobList)

        # Current free information
        self.nFreeCore: int = 0                 # Number of free cores = nCore-nCurJob
        self.freeMem: str = ''                  # Size of free memory

        # Error lists
        self.scanErrList = []                   # List of errors during scanning
        self.killErrList = []                   # List of errors during killing job

        # Default variables
        self.cmdSSH = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=4 -o UpdateHostKeys=no {self.name} '

    ###################################### Basic Utility ######################################
    def __lt__(self, other) -> bool:
        """
            Comparison of machine w.r.t name
        """
        return self.getIndex() < other.getIndex()

    def __str__(self) -> str:
        """
            When print the machine, it prints it's name
        """
        return self.name

    def findCmdFromPID(self, pid: str) -> str:
        """
            Find command line in userJobList by pid
            CAUTION
            You should run scanUserJob before this function
        """
        for job in self.jobList:
            if job.pid == pid:
                return job.cmd
        colorama.init()
        print(colored(f"ERROR: No such process in {self.name}: {pid}", 'red'))
        exit()

    def getIndex(self) -> int:
        """
            Get index of machine.
            ex) tenet100 -> 100
        """
        return int(re.sub('[^0-9]', '', self.name))

    ########################### Get Information of Machine Instance ###########################
    def getFreeMem(self) -> str:
        """
            Return absolute value of free memory
        """
        cmdGetFreeMem = self.cmdSSH + '\"free -h --si | awk \'(NR==2){print \$7}\'\"'
        result = subprocess.run(cmdGetFreeMem,
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        return result.stdout.strip()

    def getJobList(self, scanLevel: int, userName: str) -> Optional[list[Job]]:
        """
            Scan the sub-process of input user.
            When error occurs during scanning, save the error to scanErrList and return None
            Args
                scanLevel: Refer 'Job.isImportant' for more description
                userName: user name to find jobs. If none, take every users registered in group 'user'
            Return
                userJobList: List of jobs that is important.
        """
        # Get list of jobs
        if userName is None:
            # Scan every user registered in group 'user'
            cmdGetProcess = self.cmdSSH + '\"ps H --user $(getent group users | cut -d: -f4)\
                                            --format ruser:15,stat,pid,pcpu,pmem,rss:10,time:15,start_time,args\"'
        else:
            # Scan specifically input user
            cmdGetProcess = self.cmdSSH + f'\"ps H --user {userName}\
                                            --format ruser:15,stat,pid,pcpu,pmem,rss:10,time:15,start_time,args\"'
        result = subprocess.run(cmdGetProcess,
                                capture_output=True,
                                text=True,
                                shell=True)

        # Check scan error
        if result.stderr:
            self.scanErrList.append(f'ERROR from {self.name}: {result.stderr.strip()}')
            return None

        # Save important sub-process into joblist
        jobInfoList = result.stdout.strip().split('\n')[1:]     # First line is header
        jobList = []
        for jobInfo in jobInfoList:
            job = Job(self.name, jobInfo)
            if job.isImportant(scanLevel):
                jobList.append(job)
        return jobList

    def getUserCount(self) -> Counter[str, int]:
        """
            Return the dictionary of {user name: number of jobs}
            CAUTION! You should run scanUserJob before running this function
        """
        userList = [job.userName for job in self.jobList]
        return Counter(userList)

    ########################## Get Line Format Information for Print ##########################
    def getInfoLine(self) -> str:
        """
            Return line format of machine information
        """
        line = '| {:<10} | {:<11} | {:2d} cores | {:>5}'.format(self.name, self.cpu, self.nCore, self.memory)
        return line

    def getFreeInfoLine(self) -> str:
        """
            Return line format of machine free information
        """
        line = '| {:<10} | {:<11} | {:2d} cores | {:>5} free'.format(self.name, self.cpu, self.nFreeCore, self.freeMem)
        return line

    def getJobLine(self) -> str:
        """
            Return list of jobs running in line format
        """
        jobLine = ''
        for job in self.jobList:
            jobLine += job.getLine() + "\n"
        return jobLine

    ############################## Scan Job Information and Save ##############################
    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            nJob, jobList will be updated
            when userName is None, nFreeCore, freeMem will also be updated
        """
        jobList = self.getJobList(scanLevel=scanLevel, userName=userName)

        # When error occurs during getJobList
        if jobList is None:
            return None

        # Save the scanned information
        self.jobList = jobList
        self.nJob = len(jobList)
        if userName is None:
            self.nFreeCore = max(0, self.nCore - self.nJob)
            self.freeMem = self.getFreeMem()

        return None

    ##################################### Run or Kill Job #####################################
    def run(self, path: str, command: str) -> None:
        """
            run process
            Args
                path: Where command is done
                cmds: list of commands including program/arguments
        """
        # Go to machine
        cmdRun = self.cmdSSH + f'\"cd {path}; {command}\" &'
        subprocess.run(cmdRun, shell=True)
        return None

    def killPID(self, pid: str) -> None:
        """
            Kill process by input pid
        """
        cmdKill = self.cmdSSH + f'\"kill -9 {pid}\"'
        result = subprocess.run(cmdKill, shell=True, capture_output=True, text=True)
        killErrList = result.stderr.strip().split('\n') if result.stderr else []
        for killErr in killErrList:
            self.killErrList.append(f'ERROR from {self.name}: {killErr}')

        print(f'{self.name}: killed \"{self.findCmdFromPID(pid)}\"')
        return None

    def KILL(self, args:argparse.Namespace) -> int:
        """
            Kill every job satisfying args
        """
        nKill = 0
        for job in self.jobList:
            if job.checkKill(args):
                self.killPID(job.pid)
                nKill += 1
        return nKill


    ######################################## Deprecate ########################################
    def killAll(self) -> int:
        """
            Kill every job belongs to user
            Get user job from self.userJobList
        """
        nKill = 0
        for job in self.jobList:
            self.killPID(job.pid)
            nKill += 1
        return nKill

    def killThis(self, pattern: list[str]) -> int:
        """
            Kill every job which has sepcific patter
            Get user job from self.userJobList
        """
        nKill = 0
        for job in self.jobList:
            # Get user job as list if it matches pattern
            if job.cmd.find(' '.join(pattern)) != -1:
                self.killPID(job.pid)
                nKill += 1
        return nKill

    def killBefore(self, timeWindow: int) -> int:
        """
            Kill all user job started before timeWindow (seconds)
            Get user job from self.userJobList
        """
        nKill = 0
        for job in self.jobList:
            if job.getTimeWindow() < timeWindow:
                self.killPID(job.pid)
                nKill += 1
        return nKill

if __name__ == "__main__":
    print("This is moudle 'Machine' from SPG")