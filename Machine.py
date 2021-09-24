import re
import argparse
import subprocess
from collections import Counter
from typing import Optional
from abc import ABC, abstractmethod

from Default import default
from IO import Printer, messageHandler, runKillLogger
from Commands import Commands
from Job import CPUJob, GPUJob, Job

class Machine(ABC):
    # I know global variable is not optimal...
    global default, messageHandler, runKillLogger

    """
        Abstract class for storing machine informations
        CPUMachine/GPUMachine will be inherited from this class
    """
    def __init__(self, info: str) -> None:
        """
            Args
                info: Information of machine. Should be following format
                0.Use|#1.Name|#2.CPU/GPU|#3.nCore/nGPU|#4.Memory
                Refer *.machine file in spg directory
        """
        self.info = info.strip().split('|')

        self.use = bool(int(self.info[0]))      # Whether to be used or not: 1 for use, 0 for not use
        self.name = self.info[1]                # Name of machine. ex) tenet1
        self.computeUnit = self.info[2]         # Name of compute unit(CPU/GPU)
        self.nUnit = int(self.info[3])          # Number of comput units(CPU/GPU)
        self.mem = self.info[4]                 # Size of memory(RAM per machine, VRAM per GPU)

        # Current job/free information
        self.jobDict: dict[str, Job] = {}       # Dictionary of running jobs with key of PID
        self.nJob: int = 0                      # Number of running jobs = len(jobList)
        self.nFreeUnit: int = 0                 # Number of free units
        self.freeMem: str = ''                  # Size of free memory

        # KILL
        self.nKill: int = 0                     # Number of killed jobs

        # Default variables
        self.logDict = {'machine': self.name, 'user': default.user}
        self.cmdSSH = Commands.getSSHCmd(self.name)

    ########################## Get Line Format Information for Print ##########################
    @abstractmethod
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
        pass

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
            job = self.jobDict[pid]
        # Job with input pid is not registered
        except KeyError:
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
    def _getProcessList(self, getProcessCmd:str) -> Optional[list[str]]:
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


    @abstractmethod
    def _getFreeMem(self) -> str:
        """
            Return absolute value of free memory
        """
        pass

    @abstractmethod
    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            Scan the processes of input user.
            jobDict, nJob will be updated
            when userName is None, nFreeUnit, freeMem will also be updated
            Args
                userName: Refer getprocessList for more description
                scanLevel: Refer 'Job.isImportant' for more description

            For CPU Machine, select important job from _getProcessList
            For GPU Machine, do thread job __scanGPU over GPUs
        """
        pass

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


class CPUMachine(Machine):
    def __format__(self, format_spec: str) -> str:
        if format_spec.lower() == 'job':
            return '\n'.join(f'{job}' for job in self.jobDict.values())
        elif format_spec.lower() == 'free':
            return Printer.machineFreeInfoFormat.format(self.name, self.computeUnit, f'{self.nFreeUnit} cores', f'{self.freeMem} free')
        else:
            return Printer.machineInfoFormat.format(self.name, self.computeUnit, f'{self.nUnit} cores', self.mem)

    def _getFreeMem(self) -> str:
        result = subprocess.run(f'{self.cmdSSH} \"{Commands.getFreeRAMCmd()}\"',
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        return result.stdout.strip()

    def scanJob(self, userName: str, scanLevel: int) -> None:
        # Get list of raw process
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
            self.nFreeUnit = max(0, self.nUnit - self.nJob)
            self.freeMem = self._getFreeMem()
        return None


class GPUMachine(Machine):
    def __format__(self, format_spec: str) -> str:
        if format_spec.lower() == 'job':
            return '\n'.join(f'{job}' for job in self.jobDict.values())
        elif format_spec.lower() == 'free':
            return Printer.machineFreeInfoFormat.format(self.name, self.computeUnit, f'{self.nFreeUnit} GPUs ', f'{self.freeMem} free')
        else:
            return Printer.machineInfoFormat.format(self.name, self.computeUnit, f'{self.nUnit} GPUs ', self.mem)

    def _getFreeMem(self) -> str:
        # When one or more gpu is free, print it's memory
        if self.nFreeUnit:
            return self.mem

        # Otherwise, print largest available memory
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
            update jobDict and nFreeUnit
            1. For every process in GPUs, check their pid
                2-1. If there is no process, update nFreeUnit
                2-2. If there is such process, find ps information by pid
                    3-1. If userName from ps information matches, check the importance of job
                        4-1. If the job is important, save the job to jobDict
        """
        # Get list of raw process
        processList: Optional[list[str]] = self._getProcessList(Commands.getNSProcessCmd())

        # When error occurs, processList is None. Do nothing and return
        if processList is None:
            return None

        for process in processList:
            # Check the process
            nsInfo = process.strip().split()    # gpuIdx, pid, gpuPercent, vramPercent, vramUse
            pid = nsInfo[1]

            # When no information is detected, nvidia-smi returns '-'
            if pid == '-':
                self.nFreeUnit += 1     # nFreeUnit is updated regardless of userName
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
            self.freeMem = self._getFreeMem()

if __name__ == "__main__":
    print("This is moudle 'Machine' from SPG")
