import argparse
from abc import ABC, abstractmethod

from .spgio import Printer, MessageHandler
from .utils import get_mem_with_unit, ps_time_to_seconds


class Job(ABC):
    """
        Abstract class for storing job informations
        CPUJob/GPUJob will be inherited from this class
    """

    def __init__(self, machine_name: str, info: str, *gpu_info) -> None:
        """
            Args
                machine_name: Name of machine where this job is running
                info: Contain information of job, as the result of 'ps'
                      Refer Commands.getPSCmd for detailed format
                args: Used for GPU machine that should be initialized
                      by other information than info
        """
        self.machine_name = machine_name        # Name of machine where this job is running
        self.info = info.strip().split()

        self.user_name = self.info[0]           # Name of user who is reponsible for the job
        self.state = self.info[1]               # Current state of job. Ex) R, S, D, ...
        self.pid = self.info[2]                 # Process ID of job
        self.sid = self.info[3]                 # Process ID of session leader
        self.cpu_percent = self.info[4]         # Single core utilization percentage
        self.ram_percent = self.info[5]         # Memory utilization percentage
        self.ram_use = self.info[6]             # Absolute value of ram utilization
        self.time = self.info[7]                # Cumulative CPU time
        self.start = self.info[8]               # Starting time or date
        self.cmd = " ".join(self.info[9:])      # Command of the job

        self._initialize(*gpu_info)

    @abstractmethod
    def _initialize(self, *args) -> None:
        """
            Initialize CPU/GPU specific informations from info
            For CPU job: RAM initialization
            For GPU job: GPU core utilization, VRAM memory utilization
        """
        pass

    ########################## Get Line Format Information for Print ##########################
    @abstractmethod
    def __format__(self, format_spec: str) -> str:
        """
            Format of job using Job.format
            Args
                format_spec: which information to return
                    - info: full information of job
                    - otherwise: job pid
        """
        pass

    ################################## Check job information ##################################
    def is_important(self, scan_level: int) -> bool:
        """
            Check if the job is important or not with following rules
            1. Whether the state of job is 'R': Running or 'D': waiting for IO
            1-1 when job state is 'R', it should have either 5(%)cpu usage or 1(sec) time
            2. Whether the fraction of commands is in exception list
            Args
                job: target job to be determined
                scan_level: level of exception list. 2: more strict
            Return
                True: It is important job. Should be counted
                False: It is not important job. Should be skipped
        """
        scan_mode_exception = [
            "kworker",                   # Kernel worker
            "ps H --no-headers",         # From SPG scanning process
            "sshd",                      # SSH daemon process
            "@notty",                    # Login which does not require a terminal
            "/usr/lib/systemd/systemd"   # User-specific systemd
            , ".vscode-server"           # Remote SSH of vscode
        ]
        if scan_level >= 2:
            scan_mode_exception += ["scala.tools.nsc.CompileServer"]  # Not sure what this is

        # Filter job by exception
        for exception in scan_mode_exception:
            if exception in self.cmd:
                return False

        # If filterd job has 20+% cpu usage, count it as important regardless of it's state
        if float(self.cpu_percent) > 20.0:
            return True

        match list(self.state):
            case ["R", *_]:
                # State is 'R': Filter job by cpu usage and running time
                if (float(self.cpu_percent) > 5.0) or (ps_time_to_seconds(self.time) > 1):
                    return True
                else:
                    return False
            case ["D", *_]:
                # State is 'D'
                return True
            case ["Z", *_]:
                # State is 'Z'. Warning message
                MessageHandler().warning(
                    f"WARNING: {self.machine_name} has Zombie process {self.pid}"
                )
                return False

        # State is at S state with lower cpu usage
        return False

    def match(self, args: argparse.Namespace) -> bool:
        """ Check if this job fulfills the condition of args """
        # When pid list is given, job's pid should be one of them
        if (args.pid is not None) and (self.pid not in args.pid):
            return False

        # When command pattern is given, job's command should include the pattern
        if (args.command is not None) and (args.command not in self.cmd):
            return False

        # When time is given, job's time should be less than the time
        if (args.time is not None) and (ps_time_to_seconds(self.time) >= args.time):
            return False

        # When start is given, job's start should be same as the argument
        if (args.start is not None) and (self.start != args.start):
            return False

        # Every options are considered. When passed, the job should be killed
        return True


class CPUJob(Job):
    def _initialize(self, *gpu_info) -> None:
        self.ram_use = get_mem_with_unit(self.ram_use, "KB")

    def __format__(self, format_spec: str) -> str:
        job_info = self.pid

        if format_spec == "info":
            job_info = Printer.job_info_format.format(
                self.machine_name, self.user_name, self.state, self.pid, self.cpu_percent,
                self.ram_percent, self.ram_use, self.time, self.start, self.cmd
            )

        return job_info


class GPUJob(Job):
    def _initialize(self, *gpu_info) -> None:
        """ Add aditional information about GPU """
        self.gpu_percent, self.vram_percent, self.vram_use = gpu_info
        self.ram_use = get_mem_with_unit(self.ram_use, "KB")
        self.vram_use = get_mem_with_unit(self.vram_use, "MB")

    def __format__(self, format_spec: str) -> str:
        job_info = self.pid

        if format_spec == "info":
            job_info = Printer.job_info_format.format(
                self.machine_name, self.user_name, self.state, self.pid, self.gpu_percent,
                self.vram_percent, self.vram_use, self.time, self.start, self.cmd
            )

        return job_info


if __name__ == "__main__":
    print("This is module Job from SPG")
