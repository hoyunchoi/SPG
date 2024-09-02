from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .ram import Ram
from .seconds import Seconds
from .spgio import MESSAGE_HANDLER, Printer

EXCEPTIONS = [
    "kworker",  # Kernel worker
    "ps H --no-headers",  # From SPG scanning process
    "sshd",  # SSH daemon process
    "@notty",  # Login which does not require a terminal
    "/usr/lib/systemd/systemd",  # User-specific systemd
    "scala.tools.nsc.CompileServer",  # Not sure what this is
    ".vscode-server",  # Remote SSH of vscode
]


def interpret_ps_info(ps_info: str) -> dict[str, Any]:
    """
    Interpret ps information to keyword arguments of Job
    Args
        ps_info: Contain information of job, as the result of 'ps'
                Refer Commands.getPSCmd for detailed format
    Return
        Dictionary of keyword arguments
    """
    infos = ps_info.strip().split()

    return {
        "user_name": infos[0],
        "state": infos[1],
        "pid": int(infos[2]),
        "sid": int(infos[3]),
        "cpu_percent": float(infos[4]),
        "ram_percent": float(infos[5]),
        "ram_use": Ram.from_string(f"{infos[6]}KB"),
        "time": Seconds.from_ps(infos[7]),
        "start": infos[8],
        "command": " ".join(infos[9:]),
    }


@dataclass(slots=True)
class JobCondition:
    pid: list[int]
    command: str
    time: Seconds
    start: str


@dataclass(slots=True)
class Job(ABC):
    """Abstract class for storing job informations"""

    machine_name: str  # Name of machine where this job is running
    user_name: str  # Name of user who is reponsible
    state: str  # Current state Ex) R, S, D, ...
    pid: int  # Process ID
    sid: int  # Process ID of session leader
    cpu_percent: float  # Single core utilization percentage
    ram_percent: float  # Memory utilization percentage
    ram_use: Ram  # Absolute value of ram utilization
    time: Seconds  # Cumulative CPU time from start
    start: str  # Starting time or date of format [DD-]HH:MM:SS
    command: str  # Running command

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
    @property
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

        # Filter job by exception
        if any(map(lambda exception: exception in self.command, EXCEPTIONS)):
            return False

        # If filterd job has 20+% cpu usage, count it as important regardless of it's state
        if self.cpu_percent > 20.0:
            return True

        if "R" in self.state:
            # State is 'R': Filter job by cpu usage and running time
            if self.ram_use.byte == 0.0:
                MESSAGE_HANDLER.warning(
                    f"WARNING: {self.machine_name} has zero-memory process {self.pid}"
                )
            return (self.cpu_percent > 5.0) or (self.time.value > 1)
        elif "D" in self.state:
            # State is 'D'
            if self.ram_use.byte == 0.0:
                MESSAGE_HANDLER.warning(
                    f"WARNING: {self.machine_name} has zero-memory process {self.pid}"
                )
            return True
        elif "Z" in self.state:
            # State is 'Z'. Warning message
            MESSAGE_HANDLER.warning(
                f"WARNING: {self.machine_name} has Zombie process {self.pid}"
            )
            return False

        # State is at S state with lower cpu usage
        return False

    def match_condition(self, condition: JobCondition | None) -> bool:
        """Check if this job meets the given condition"""
        # When no condition is given, every job matchs to the condition
        if condition is None:
            return True

        # When pid list is given, job's pid should be one of them
        if (condition.pid != []) and (self.pid not in condition.pid):
            return False

        # When command pattern is given, job's command should include the pattern
        if (condition.command != "") and (condition.command not in self.command):
            return False

        # When time is given, job's time should be less than the time
        if (condition.time != Seconds()) and (self.time >= condition.time):
            return False

        # When start is given, job's start should be exactly same as the argument
        if (condition.start != "") and (self.start != condition.start):
            return False

        # Every options are considered. When passed, the job should be killed
        return True


@dataclass(slots=True)
class CPUJob(Job):
    @classmethod
    def from_info(cls, machine_name: str, ps_info: str) -> Job:
        """
        Args
            machine_name: Name of machine where this job is running
            ps_info: Contain information of job, as the result of 'ps'
                  Refer Commands.getPSCmd for detailed format
            gpu_info: GPU-specific informations: gpu_percent, vram_percent, vram_use
        """
        return cls(machine_name=machine_name, **interpret_ps_info(ps_info))

    def __format__(self, format_spec: str) -> str:
        job_info = f"{self.pid}"

        if format_spec == "info":
            job_info = Printer.job_info_format.format(
                self.machine_name,
                self.user_name,
                self.state,
                self.pid,
                f"{self.cpu_percent:.1f}",
                f"{self.ram_percent:.1f}",
                f"{self.ram_use}",
                f"{self.time:ps}",
                self.start,
                self.command,
            )
        return job_info


@dataclass(slots=True)
class GPUJob(Job):
    gpu_percent: float
    vram_percent: float
    vram_use: Ram

    @classmethod
    def from_info(
        cls,
        machine_name: str,
        ps_info: str,
        gpu_percent: float,
        vram_use: Ram,
        vram_percent: float,
    ) -> Job:
        """
        Args
            machine_name: Name of machine where this job is running
            ps_info: Contain information of job, as the result of 'ps'
                  Refer Commands.getPSCmd for detailed format
            gpu_info: GPU-specific informations: gpu_percent, vram_percent, vram_use
        """
        return cls(
            machine_name=machine_name,
            gpu_percent=gpu_percent,
            vram_use=vram_use,
            vram_percent=vram_percent,
            **interpret_ps_info(ps_info),
        )

    def __format__(self, format_spec: str) -> str:
        job_info = f"{self.pid}"

        if format_spec == "info":
            job_info = Printer.job_info_format.format(
                self.machine_name,
                self.user_name,
                self.state,
                self.pid,
                f"{self.gpu_percent:.1f}",
                f"{self.vram_percent:.1f}",
                f"{self.vram_use}",
                f"{self.time:ps}",
                self.start,
                self.command,
            )

        return job_info
