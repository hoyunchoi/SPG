import re
import argparse
import subprocess
from collections import Counter
from typing import Optional
from dataclasses import dataclass

from Default import default
from IO import Printer, messageHandler, runKillLogger
from Commands import Commands
from Job import CPUJob, GPUJob, Job


@dataclass
class Machine:
    """
        Abstract class for storing machine informations
        CPUMachine/GPUMachine will be inherited from this class
    """
    use: bool                       # Whether to be used or not: 1 for use, 0 for not use
    name: str                       # Name of machine. ex) tenet1
    cpu: str                        # Name of cpu
    nCpu: int                       # Number of cpu cores
    ram: str                        # Size of RAM
    comment: str                    # comment of machine. Not used
    gpu: Optional[str] = ''         # Name of gpu (if exists)
    nGpu: Optional[int] = 0         # Number of gpus (if exists)
    vram: Optional[str] = ''        # Size of VRAM per each gpu (if exists)

    def __post_init__(self) -> None:
        """
            Post processing initialize
        """
        self.use = self.use.lower() in ['true', '1']
        self.nCpu = int(self.nCpu)

        # Current job/free information
        self.jobDict: dict[str, Job] = {}       # Dictionary of running jobs with key of PID
        self.nJob: int = 0                      # Number of running jobs = len(jobList)
        self.nFreeCpu: int = 0                  # Number of free cpu cores
        self.freeRam: str = ''                  # Size of free memory

        # KILL
        self.nKill: int = 0                     # Number of killed jobs

        # Default variables
        self.logDict = {'machine': self.name, 'user': default.user}
        self.cmdSSH = Commands.getSSHCmd(self.name)

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return machine information in line format
            Args
                format_spec: which information to return
                    - info: machine information
                    - free: machine free information
                    - otherwise: machine name
        """
        if format_spec.lower() == 'info':
            return Printer.machineInfoFormat.format(self.name, self.cpu, self.nCpu,
                                                    'core', self.ram)

        if format_spec.lower() == 'free':
            return Printer.machineFreeInfoFormat.format(self.name, self.cpu, str(self.nFreeCpu),
                                                        'core', f'{self.freeRam} free')

        return self.name

    ###################################### Basic Utility ######################################
    def findCmdFromPID(self, pid: str) -> str:
        """
            Find command line in userJobList by pid
            Args
                pid: target pid
            Return
                command: command of the process
        """
        try:
            return self.jobDict[pid].cmd

        # Job with input pid is not registered
        except KeyError:
            messageHandler.error(f'ERROR: No such process in {self.name}: {pid}')
            exit()

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
    def _getProcessList(self, getProcessCmd: str) -> Optional[list[str]]:
        """
            Get list of processes
            When error occurs during SSH, return None
            Args
                getProcessCmd: command to find process inside ssh client
            Return
                CPU Machine: List of process from 'ps'
                GPU Machine: List of process from 'nvidia-smi'
        """
        result = subprocess.run(f'{self.cmdSSH} \"{getProcessCmd}\"',
                                capture_output=True,
                                text=True,
                                shell=True)
        # Check scan error
        if result.stderr:
            messageHandler.error(f'ERROR from {self.name}: {result.stderr.strip()}')
            return None
        # If there is no error return list of stdout
        return result.stdout.strip().split('\n')

    def _getFreeRam(self) -> str:
        """
            Return absolute value of free RAM
        """
        result = subprocess.run(f'{self.cmdSSH} \"{Commands.getFreeRAMCmd()}\"',
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        return result.stdout.strip()

    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            Scan the processes of input user.
            jobDict, nJob will be updated
            when userName is None: free informations will also be updated
            when machine is GPUMachine: nFreeGpu, freeVram will also be updated
            Args
                userName: Refer getprocessList for more description
                scanLevel: Refer 'Job.isImportant' for more description

            For CPU Machine, select important job from _getProcessList
            For GPU Machine, do thread job __scanGPU over GPUs
        """
        # Get list of raw process: Use ps command
        processList: Optional[list[str]] = self._getProcessList(Commands.getPSCmd(userName))

        # When error occurs, processList is None. Do nothing and return
        if processList is None:
            return None

        # Save scanned job informations
        for process in processList:
            if process:
                job = CPUJob(self.name, process)
                if job.isImportant(scanLevel):
                    self.jobDict[job.pid] = job
        self.nJob = len(self.jobDict)

        # If user name is None, update free informations too
        if userName is None:
            self.nFreeCpu = max(0, self.nCpu - self.nJob)
            self.freeRam = self._getFreeRam()

        return None

    def getUserCount(self) -> Counter[str, int]:
        """
            Return the dictionary of {user name: number of jobs}
        """
        userList = [job.userName for job in self.jobDict.values()]
        return Counter(userList)

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
                self.__kill(job)
                self.nKill += 1

                # Print the result and save to logger
                messageHandler.success(f"SUCCESS {self.name:<10}: kill \'{command}\'")
                runKillLogger.info(f'spg kill {command}', extra=self.logDict)
        return None

    def __kill(self, job: Job) -> None:
        """
            Kill job and all the process until it's session leader
        """
        # Command to kill very processes until reaching session leader
        cmdKill = f'{self.cmdSSH} \"{Commands.getKillCmd(job.pid)}; '
        pid = job.pid
        while pid != job.sid:
            # Update pid to it's ppid
            pid = subprocess.check_output(f'{self.cmdSSH} \"{Commands.getPPIDCmd(pid)}\"',
                                          text=True, shell=True).strip()
            cmdKill += f'{Commands.getKillCmd(job.pid)}; '
        cmdKill += '\"'

        # Run kill command
        result = subprocess.run(cmdKill, shell=True, capture_output=True, text=True)

        # When error occurs, save it
        if result.stderr:
            killErrList = result.stderr.strip().split('\n')
            messageHandler.error('\n'.join(f'ERROR from {self.name}: {killErr}' for killErr in killErrList))
        return None


class GPUMachine(Machine):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.nGpu = int(self.nGpu)

        # GPU free information
        self.nFreeGpu = 0
        self.freeVram = ''

    def __format__(self, format_spec: str) -> str:
        machineFormat = super().__format__(format_spec) # Format of Machine
        if format_spec.lower() == 'info':
            return machineFormat + '\n' + Printer.machineInfoFormat.format('', self.gpu, self.nGpu, 'gpus', self.vram)
        if format_spec.lower() == 'job':
            return machineFormat
        if format_spec.lower() == 'free':
            return machineFormat + '\n' + Printer.machineFreeInfoFormat.format('', self.gpu, self.nFreeGpu, 'gpus', f'{self.freeVram} free')

        return self.name

    def _getFreeVRAM(self) -> str:
        """
            Get free vram information
            When one or more gpus is free, print it's total vram
            Otherwise, print largest available memory
        """
        # When one or more gpu is free
        if self.nFreeGpu:
            return self.vram

        # Otherwise, get list of free vram
        result = subprocess.run(f'{self.cmdSSH} \"{Commands.getFreeVRAMCmd()}\"',
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        freeVRAMList = result.stdout.strip().split('\n')
        maxFreeVRAM = max(float(freeVRAM) for freeVRAM in freeVRAMList)
        maxFreeVRAM *= 1.04858      # Mebibyte to Megabyte
        return Job.getMemWithUnit(maxFreeVRAM, 'MB')

    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            update jobDict and nFreeGpu
            1. For every process in GPUs, check their pid
                2-1. If there is no process, update nFreeGpu
                2-2. If there is such process, find ps information by pid
                    3-1. If userName from ps information matches, check the importance of job
                        4-1. If the job is important, save the job to jobDict
        """
        # Get list of raw process: Use nvidia-smi command
        processList: Optional[list[str]] = self._getProcessList(Commands.getNSProcessCmd())

        # When error occurs, processList is None. Do nothing and return
        if processList is None:
            return None

        # Save scanned job informations
        for process in processList:
            # Check the process
            nsInfo = process.strip().split()    # gpuIdx, pid, gpuPercent, vramPercent, vramUse
            pid = nsInfo[1]

            # When no information is detected, nvidia-smi returns '-'
            if pid == '-':
                self.nFreeGpu += 1     # nFreeGpu is updated regardless of userName
                continue

            # Get 'ps' information from PID of nsInfo
            psInfo = subprocess.run(f'{self.cmdSSH} \"{Commands.getPSFromPIDCmd(pid)}\"',
                                    stdout=subprocess.PIPE,
                                    text=True,
                                    shell=True).stdout

            # Store the information to job Dict
            if (userName is None) or (psInfo.strip().split()[0] == userName):
                job = GPUJob(f'{self.name}-GPU{nsInfo[0]}', psInfo, *nsInfo[2:])
                if job.isImportant(scanLevel):      # Most likely to be true
                    self.jobDict[pid] = job
        self.nJob = len(self.jobDict)

        # Update free information
        if userName is None:
            self.nFreeCpu = max(0, self.nCpu - self.nJob)
            self.freeRam = self._getFreeRam()
            self.freeVram = self._getFreeVRAM()


if __name__ == "__main__":
    print("This is moudle 'Machine' from SPG")
