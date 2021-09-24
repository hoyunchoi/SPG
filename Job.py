import argparse
from typing import Union
from abc import ABC, abstractmethod

from IO import Printer, messageHandler


class Job(ABC):
    # I know global variable is not optimal...
    global messageHandler
    """
        Abstract class for storing job informations
        CPUJob/GPUJob will be inherited from this class
    """

    def __init__(self, machineName: str, info: str, *args) -> None:
        """
            Args
                machineName: Name of machine where this job is running
                info: Contain information of job, as the result of 'ps'
                      Refer Commands.getPSCmd for detailed format
                args: Used for GPU machine that should be initialized using other information than info
        """
        self.machineName = machineName  # Name of machine where this job is running
        self.info = info.strip().split()

        self.userName = self.info[0]            # Name of user who is reponsible for the job
        self.state = self.info[1]               # Current state of job. Ex) R, S, D, ...
        self.pid = self.info[2]                 # Process ID of job
        self.sid = self.info[3]                 # Process ID of session leader
        self.time = self.info[7]                # Cumulative CPU time
        self.start = self.info[8]               # Starting time or date
        self.cmd = ' '.join(self.info[9:])      # Command of the job

        self.initialize(*args)

    @abstractmethod
    def initialize(self, *args) -> None:
        """
            Initialize CPU/GPU specific informations from info
            - CPU/GPU core utilization in percentage
            - CPU/GPU memory utilization in percentage
            - CPU/GPU absolute memory utilization
        """
        pass

    ########################## Get Line Format Information for Print ##########################
    @abstractmethod
    def __format__(self, format_spec: str) -> str:
        """
            Format of job using Job.format
        """
        pass

    ###################################### Basic Utility ######################################
    @staticmethod
    def getTimeWindow(time: str) -> int:
        """
            time as second
            time has format [DD-]HH:MM:SS
        """
        toSecondList = [1, 60, 3600, 62400] # second, minute, hour, day

        timeList = time.replace('-', ':').split(':')    # [DD-]HH:MM:SS -> [DD:]HH:MM:SS
        second = sum(int(time) * toSecond for time, toSecond in zip(reversed(timeList), toSecondList))
        return second

    @staticmethod
    def getMemWithUnit(mem: Union[str, float], unit: str) -> str:
        """
            Change memory in KB unit to MB or GB
            Args
                mem: memory utilization in KB unit
            Return
                memory utilization in MB or GB unit
        """
        unitList = ['KB', 'MB', 'GB', 'TB']
        currentUnitIdx = unitList.index(unit)
        mem = float(mem)

        while mem >= 1000.0:
            mem /= 1000.0
            currentUnitIdx += 1

        return f'{mem:.1f}{unitList[currentUnitIdx]}'

    ################################## Check job information ##################################
    def isImportant(self, scanLevel: int) -> bool:
        """
            Check if the job is important or not with following rules
            1. Whether the state of job is 'R': Running or 'D': waiting for IO
            1-1 when job state is 'R', it should have either 5+(%) cpu usage or 1+(sec) running time
            2. Whether the fraction of commands is in exception list
            Args
                job: target job to be determined
                scanLevel: level of exception list. 2: more strict
            Return
                True: It is important job. Should be counted
                False: It is not important job. Should be skipped
        """
        scanModeException = ['ps H --user',     # From SPG scanning process
                             'sshd',            # SSH daemon process
                             '@notty',          # Login which does not require a terminal
                             '[']               # Not sure what this is
        if scanLevel >= 2:
            scanModeException += ['scala.tools.nsc.CompileServer']  # Not sure what this is

        # Filter job by exception
        for exception in scanModeException:
            if exception in self.cmd:
                return False

        # State is 'R'
        if 'R' in self.state:
            # Filter job by cpu usage and running time
            if (float(self.cpuPercent) < 5.0) and (self.getTimeWindow(self.time) < 1):
                return False
            else:
                return True
        # State is 'D'
        elif 'D' in self.state:
            return True
        # State is 'Z'. Warning message
        elif 'Z' in self.state:
            messageHandler.warning(f'WARNING: {self.machineName} has Zombie process {self.pid}')
            return False
        # State is not either R and D
        else:
            return False

    def checkKill(self, args: argparse.Namespace) -> bool:
        """
            Check if this job should be killed
        """
        # When pid list is given, job's pid should be one of them
        if (args.pidList is not None) and (self.pid not in args.pidList):
            return False

        # When command pattern is given, job's command should include the pattern
        if (args.command is not None) and (args.command not in self.cmd):
            return False

        # When time is given, job's time should be less than the time
        if (args.time is not None) and (self.getTimeWindow(self.time) >= args.time):
            return False

        # When start is given, job's start should be same as the argument
        if (args.start is not None) and (self.start != args.start):
            return False

        # Every options are considered. When passed, the job should be killed
        return True


class CPUJob(Job):
    def initialize(self, *args) -> None:
        self.cpuPercent = self.info[4]                              # Single core utilization percentage
        self.ramPercent = self.info[5]                              # Memory utilization percentage
        self.ramUse = self.getMemWithUnit(self.info[6], 'KB')       # Absolute value of memory utilization

    def __format__(self, format_spec: str) -> str:
        return Printer.jobInfoFormat.format(self.machineName, self.userName, self.state, self.pid, self.cpuPercent,
                                            self.ramPercent, self.ramUse, self.time, self.start, self.cmd)


class GPUJob(Job):
    def initialize(self, *args) -> None:
        """
            Args
                args: tuple of gpuPercent, vramPercent, vramUse(MB)
        """
        self.gpuPercent, self.vramPercent, vramUse = args
        self.vramUse = self.getMemWithUnit(vramUse, 'MB')

    def __format__(self, format_spec: str) -> str:
        return Printer.jobInfoFormat.format(self.machineName, self.userName, self.state, self.pid, self.gpuPercent,
                                            self.vramPercent, self.vramUse, self.time, self.start, self.cmd)


if __name__ == "__main__":
    print("This is moudel 'Job' from SPG")
