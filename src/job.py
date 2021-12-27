from dataclasses import dataclass
from abc import ABC, abstractmethod

from .spgio import Printer, MessageHandler
from .utils import get_mem_with_unit, ps_time_to_seconds


@dataclass
class JobCondition:
    pid: list[str] | None
    command: str | None
    time: int | None
    start: str | None


class Job(ABC):
    """ Abstract class for storing job informations """

    def __init__(self, machine_name: str, info: str) -> None:
        """
            Args
                machine_name: Name of machine where this job is running
                info: Contain information of job, as the result of 'ps'
                      Refer Commands.getPSCmd for detailed format
                gpu_info: GPU-specific informations: gpu_percent, vram_percent, vram_use
        """
        self.machine_name = machine_name    # Name of machine where this job is running
        (
            self.user_name,                 # Name of user who is reponsible
            self.state,                     # Current state Ex) R, S, D, ...
            self.pid,                       # Process ID
            self.sid,                       # Process ID of session leader
            self.cpu_percent,               # Single core utilization percentage
            self.ram_percent,               # Memory utilization percentage
            self.ram_use,                   # Absolute value of ram utilization
            self.time,                      # Cumulative CPU time from start
            self.start,                     # Starting time or date of format [DD-]HH:MM:SS
            *self.cmd                       # Running command
        ) = info.strip().split()

        # Change to proper unit
        self.ram_use = get_mem_with_unit(self.ram_use, "KB")

        # Command to single line
        self.cmd = " ".join(self.cmd)

    ########################## Get Line Format Information for Print ##########################

    @abstractmethod
    def __format__(self, format_spec: str) -> str:
        """
            Return job information according to format spec
            - info: full information of job
            - otherwise: job pid
        """
        pass

    ################################## Check job information ##################################
    def is_important(self) -> bool:
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
            "kworker",                          # Kernel worker
            "ps H --no-headers",                # From SPG scanning process
            "sshd",                             # SSH daemon process
            "@notty",                           # Login which does not require a terminal
            "/usr/lib/systemd/systemd",         # User-specific systemd
            "scala.tools.nsc.CompileServer",    # Not sure what this is
            ".vscode-server"                    # Remote SSH of vscode
        ]

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

    def match(self, condition: JobCondition | None) -> bool:
        """ Check if this job fulfills the given condition """
        # When no condition is given, every job matchs to the condition
        if condition is None:
            return True

        # When pid list is given, job's pid should be one of them
        if (condition.pid is not None) and (self.pid not in condition.pid):
            return False

        # When command pattern is given, job's command should include the pattern
        if (condition.command is not None) and (condition.command not in self.cmd):
            return False

        # When time is given, job's time should be less than the time
        if (condition.time is not None) and (ps_time_to_seconds(self.time) >= condition.time):
            return False

        # When start is given, job's start should be same as the argument
        if (condition.start is not None) and (self.start != condition.start):
            return False

        # Every options are considered. When passed, the job should be killed
        return True


class CPUJob(Job):
    def __format__(self, format_spec: str) -> str:
        job_info = self.pid

        if format_spec == "info":
            job_info = Printer.job_info_format.format(
                self.machine_name, self.user_name, self.state, self.pid, self.cpu_percent,
                self.ram_percent, self.ram_use, self.time, self.start, self.cmd
            )

        return job_info


class GPUJob(Job):
    def __init__(self, machine_name: str, info: str, *gpu_info) -> None:
        super().__init__(machine_name, info)

        # Add aditional information about GPU
        self.gpu_percent, self.vram_percent, self.vram_use = gpu_info
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
