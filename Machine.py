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
        self.jobDict: dict[str, Job] = {}       # Dictionary of running jobs with key of PID
        self.nJob: int = 0                      # Number of running jobs = len(jobList)

        # Current free information
        self.nFreeCore: int = 0                 # Number of free cores = nCore-nCurJob
        self.freeMem: str = ''                  # Size of free memory

        # Error lists
        self.scanErrList: list[str] = []        # List of errors during scanning
        self.killErrList: list[str] = []        # List of errors during killing job

        # KILL
        self.nKill: int = 0                     # Number of killed jobs

        # Default variables
        self.cmdSSH = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=4 -o UpdateHostKeys=no {self.name} '

    ###################################### Basic Utility ######################################
    def __lt__(self, other) -> bool:
        """
            Comparison of machine w.r.t name
        """
        return self.getIndex(self.machineName) < other.getIndex(other.machineName)

    def findCmdFromPID(self, pid: str) -> str:
        """
            Find command line in userJobList by pid
            CAUTION!
            You should run scanUserJob before this function
        """
        job = self.jobDict.get(pid)

        # Job with input pid is not registered
        # Print warning and exit the program
        if job is None:
            colorama.init()
            print(colored(f"ERROR: No such process in {self.name}: {pid}", 'red'))
            exit()

        return job.cmd

    @staticmethod
    def getGroupName(machineName: str) -> int:
        """
            Get group name of machine
            ex) tenet100 -> tenet
        """
        return re.sub('[0-9]', '', machineName)

    @staticmethod
    def getIndex(machineName: str) -> int:
        """
            Get index of machine.
            ex) tenet100 -> 100
        """
        return int(re.sub('[^0-9]', '', machineName))

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

    def getRawProcess(self, userName: str) -> Optional[list[str]]:
        """
            Get raw output of 'ps' command
            When error occurs, scanErrList is updated
            Args
                userName: user name to find processes. If None, take every users registered in group 'user'
        """
        # Scan every user registered in group 'user'
        if userName is None:
            cmdGetProcess = self.cmdSSH + '\"ps H --user $(getent group users | cut -d: -f4)\
                                            --format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args\"'
        # Scan specifically input user
        else:
            cmdGetProcess = self.cmdSSH + f'\"ps H --user {userName}\
                                            --format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args\"'

        # get result of ps command
        result = subprocess.run(cmdGetProcess, capture_output=True, text=True, shell=True)

        # Check scan error
        if result.stderr:
            self.scanErrList.append(f'ERROR from {self.name}: {result.stderr.strip()}')
            return None
        return result.stdout.strip().split('\n')[1:]    # First line is header

    def getUserCount(self) -> Counter[str, int]:
        """
            Return the dictionary of {user name: number of jobs}
            CAUTION! You should run scanUserJob before running this function
        """
        userList = [job.userName for job in self.jobDict.values()]
        return Counter(userList)

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return machine information in line format
            Args
                format_spec: which information to return
                    - job: return formatted job information
                    - free: return formatted free information
                    - None: return formatted machine information
            When 'free' is given, return free information of machine
        """
        if format_spec.lower() == 'job':
            return '\n'.join(f'{job}' for job in self.jobDict.values())
        elif format_spec.lower() == 'free':
            return f'| {self.name:<10} | {self.cpu:<11} | {self.nFreeCore:3d} cores | {self.freeMem:>5} free'
        else:
            return f'| {self.name:<10} | {self.cpu:<11} | {self.nCore:3d} cores | {self.memory:>5}'

    ############################## Scan Job Information and Save ##############################
    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            Scan the sub-process of input user.
            When error occurs during scanning, save the error to scanErrList and return None
            nJob, jobDict will be updated
            when userName is None, nFreeCore, freeMem will also be updated
            Args
                userName: Refer getRawProcess for more description
                scanLevel: Refer 'Job.isImportant' for more description
        """
        # Get list of raw process
        rawProcess = self.getRawProcess(userName)

        # When error occurs, rawProcess is None. Do nothing and return
        if rawProcess is None:
            return None

        # Save scanned job informations
        for process in rawProcess:
            job = Job(self.name, process)
            if job.isImportant(scanLevel):
                self.jobDict[job.pid] = job
        self.nJob = len(self.jobDict)

        # If user name is None, update free informations too
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
        # cd to path and run the command as background process
        cmdRun = self.cmdSSH + f'\"cd {path}; {command}\" &'
        subprocess.run(cmdRun, shell=True)
        return None

    def KILL(self, args: argparse.Namespace) -> None:
        """
            Kill every job satisfying args
        """
        self.nKill = 0
        for job in self.jobDict.values():
            if job.checkKill(args):
                # self.killPID(job.pid)
                self.killJob(job)
                self.nKill += 1
        return None

    def killJob(self, job: Job) -> None:
        """
            Kill job and all the process until it's session leader
        """
        # Command to kill very processes until reaching session leader
        cmdKill = self.cmdSSH + f'\" kill -9 {job.pid}; '
        pid = job.pid
        while pid != job.sid:
            # Update pid to it's ppid
            pid = subprocess.check_output(self.cmdSSH + f'\"ps -q {pid} --format ppid\"',
                                          text=True, shell=True).split('\n')[1].strip()
            cmdKill += f'kill -9 {pid}; '
        cmdKill += '\"'

        # Run kill command
        result = subprocess.run(cmdKill, shell=True, capture_output=True, text=True)

        # When error occurs, save it
        killErrList = result.stderr.strip().split('\n') if result.stderr else []
        for killErr in killErrList:
            self.killErrList.append(f'ERROR from {self.name}: {killErr}')

        # Print the result
        print(f'{self.name}: killed \"{self.findCmdFromPID(job.pid)}\"')
        return None

    # def killPID(self, pid: str) -> None:
    #     """
    #         Kill process by input pid
    #     """
    #     cmdKill = self.cmdSSH + f'\"kill -9 {pid}\"'
    #     result = subprocess.run(cmdKill, shell=True, capture_output=True, text=True)
    #     killErrList = result.stderr.strip().split('\n') if result.stderr else []
    #     for killErr in killErrList:
    #         self.killErrList.append(f'ERROR from {self.name}: {killErr}')

    #     print(f'{self.name}: killed \"{self.findCmdFromPID(pid)}\"')
    #     return None

if __name__ == "__main__":
    print("This is moudle 'Machine' from SPG")
