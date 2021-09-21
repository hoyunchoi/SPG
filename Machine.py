import re
import argparse
import subprocess
from typing import Optional
from threading import Thread
from collections import Counter

from Job import Job, GPUJob
from Default import default
from Handler import messageHandler, runKillLogger
from Commands import Commands


class Machine:
    # I know global variable is not optimal...
    global default, messageHandler, runKillLogger

    """ Save the information of each machine """
    infoFormat: str = '| {:<10} | {:<11} | {:>10} | {:>5}'
    freeInfoFormat: str = '| {:<10} | {:<11} | {:>10} | {:>10}'

    def __init__(self, information: str) -> None:
        # 0.Use|#1.Name|#2.CPU|#3.nCore|#4.Memory
        information = information.strip().split('|')

        self.use = bool(int(information[0]))    # Whether to be used or not: 1 for use, 0 for not use
        self.name = information[1]              # Name of machine. ex) tenet1
        self.cpu = information[2]               # Name of cpu inside machine
        self.nCore = int(information[3])        # Number of cores inside machine
        self.memory = information[4]            # Size of memory inside machine

        # Current job information
        self.jobDict: dict[str, Job] = {}       # Dictionary of running jobs with key of PID
        self.nJob: int = 0                      # Number of running jobs = len(jobList)

        # Current free information
        self.nFreeCore: int = 0                 # Number of free cores = nCore-nJob
        self.freeMem: str = ''                  # Size of free memory

        # KILL
        self.nKill: int = 0                     # Number of killed jobs

        # Extra default informations for logging
        self.logDict = {'machine': self.name, 'user': default.user}

        # Default variables
        self.cmdSSH = Commands.getSSHCmd(self.name)

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
            messageHandler.error(f'ERROR: No such process in {self.name}: {pid}')
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
            Not going to catch error
        """
        result = subprocess.run(f'{self.cmdSSH} \"{Commands.getFreeMemCmd()}\"',
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        return result.stdout.strip()

    def getRawProcess(self, userName: str) -> Optional[list[str]]:
        """
            Get raw output of 'ps' command
            When error occurs, scanErrList is updated
            Args
                userName: user name to find processes. If None, refer Commands.getPSCmd.
        """
        # get result of ps command
        result = subprocess.run(f'{self.cmdSSH} \"{Commands.getPSCmd(userName)}\"',
                                capture_output=True,
                                text=True,
                                shell=True)

        # Check scan error
        if result.stderr:
            messageHandler.error(f'ERROR from {self.name}: {result.stderr.strip()}')
            return None
        return result.stdout.strip().split('\n')

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
            return Machine.freeInfoFormat.format(self.name, self.cpu, f'{self.nFreeCore} cores', f'{self.freeMem} free')
        else:
            return Machine.infoFormat.format(self.name, self.cpu, f'{self.nCore} cores', self.memory)

    ############################## Scan Job Information and Save ##############################
    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            Scan the sub-process of input user.
            When error occurs during scanning, save the error to error handler and return None
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
        cmdRun = f'{self.cmdSSH} \"{Commands.getRunCmd(path, command)}\" &'
        subprocess.run(cmdRun, shell=True)

        # Print the result and save to logger
        messageHandler.success(f"SUCCESS {self.name:<10}: run \'{command}\'")
        runKillLogger.info(f'spg run {command}', extra=self.logDict)
        return None

    def KILL(self, args: argparse.Namespace) -> None:
        """
            Kill every job satisfying args
        """
        self.logDict['user'] = args.userName
        self.nKill = 0
        for job in self.jobDict.values():
            if job.checkKill(args):
                # Find command for print result/logging
                command = self.findCmdFromPID(job.pid)

                # self.killPID(job.pid)
                self.killJob(job)
                self.nKill += 1

                # Print the result and save to logger
                messageHandler.success(f"SUCCESS {self.name:<10}: kill \'{command}\'")
                runKillLogger.info(f'spg kill {command}', extra=self.logDict)
        return None

    def killJob(self, job: Job) -> None:
        """
            Kill job and all the process until it's session leader
        """
        # Command to kill very processes until reaching session leader
        cmdKill = f'{self.cmds} \"{Commands.getKillCmd(job.pid)}; '
        pid = job.pid
        while pid != job.sid:
            # Update pid to it's ppid
            pid = subprocess.check_output(f'{self.cmdSSH} \"{Commands.getPPIDCmd(pid)}\"',
                                          text=True, shell=True).split('\n')[1].strip()
            cmdKill += f'{Commands.getKillCmd(job.pid)}; '
        cmdKill += '\"'

        # Run kill command
        result = subprocess.run(cmdKill, shell=True, capture_output=True, text=True)

        # When error occurs, save it
        if result.stderr:
            killErrList = result.stderr.strip().split('\n')
            messageHandler.error('\n'.join(f'ERROR from {self.name}: {killErr}' for killErr in killErrList))
        else:
            killErrList = []

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


class GPUMachine(Machine):
    def __init__(self, information: str) -> None:
        super().__init__(information)           # Initialize like Machine

        self.gpu = self.cpu                     # Name of GPU inside machine
        self.nGPU = self.nCore                  # Number of GPUs inside machine
        self.gpuMemory = self.memory            # Size of memory inside each GPU

        # Current job information
        self.gpuJobDict: dict[str, GPUJob] = {} # Dictionary of running GPU jobs with key of PID

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
            return '\n'.join(f'{gpuJob}' for gpuJob in self.gpuJobDict.values())
        elif format_spec.lower() == 'free':
            return GPUMachine.freeInfoFormat.format(self.name, self.gpu, f'{self.nFreeCore} GPUs', f'{self.gpuMemory} free')
        else:
            return GPUMachine.infoFormat.format(self.name, self.gpu, f'{self.nCore} GPUs', self.memory)

    ############################## Scan Job Information and Save ##############################
    def matchGPUProcess(self, gpuIdx: int) -> None:

        result = subprocess.run(f'{self.cmdSSH} \"{Commands.getNSProcessCmd(gpuIdx)}\"',
                        stdout=subprocess.PIPE,
                        text=True,
                        shell=True)
        processList = result.stdout.strip().split('\n')

        # Something running at gpu
        for process in processList:
            pid, gpuPercent, gpuMem = tuple(process.split())

            # No process at gpu
            if pid == '-':
                self.nFreeCore += 1
                continue

            job = self.jobDict.get(pid)
            # process in gpu is there, but it does not belongs to current user
            if job is None:
                continue

            # Register cpu job to gpu job dict
            gpuJob = GPUJob(f'{self.name}-gpu{gpuIdx}', job.info)
            gpuJob.setGPUPercent(gpuPercent)
            gpuJob.setMemory(gpuMem, self.gpuMemory)
            self.gpuJobDict[gpuJob.pid] = gpuJob


    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            Scan the sub-process of input user.
            When error occurs during scanning, save the error to error handler and return None
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

        # Get list of cpu job
        for process in rawProcess:
            job = Job(self.name, process)
            if job.isImportant(scanLevel):
                self.jobDict[job.pid] = job

        # match cpu job with gpu id
        threadList = [Thread(target=self.matchGPUProcess, args=(gpuIdx, )) for gpuIdx in range(self.nGPU)]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()


if __name__ == "__main__":
    # print("This is moudle 'Machine' from SPG")
    info = '1|kuda4|RTX-2080Ti|4|11G|'
    gpuMachine = GPUMachine(info)

    gpuMachine.scanJob('hoyun', 2)
