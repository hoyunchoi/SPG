from __future__ import annotations

import concurrent.futures as cf
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

from .job import JobCondition
from .machine import GPUMachine, Machine
from .name import get_machine_index
from .spgio import Printer, ProgressBar


class Group:
    """
    Save the information of group of machines
    By default, machines are read from group file
    """

    def __init__(self, group_name: str, group_file: Path) -> None:
        """
        group_name: name of machine group
        group_file: Full path of json-formatted machine file.
        """
        # Name of machine group. Ex) tenet
        self.name = group_name

        # Read machine informations from group file
        self.machines = self.load_file(group_file)  # Dictionary of name: machine

    def load_file(self, group_file: Path) -> dict[str, Machine]:
        """Read group file and store machine information to machines"""
        machines: dict[str, Machine] = {}
        with open(group_file, "r") as file:
            machine_infos: dict[str, dict[str, Any]] = json.load(file)

        # Initialize dictionary of machine
        for name, info in machine_infos.items():
            # Only store machine explicitly marked as "use = True"
            if info.pop("use") != "True":
                continue
            # When machine info has gpu as key, machine is gpu machine
            if "gpu" in info:
                machines[name] = GPUMachine(**info)
            # Otherwise, machine is cpu machine
            else:
                machines[name] = Machine(**info)
        return machines

    def match_machines(
        self,
        *_,
        machine_names: list[str] = [],
        start_end: tuple[int, int] = (-1, -1),
    ) -> Group:
        """
        Only store machines that matches the condition
        machine_names: list of machine names inside the group
        start_end: machines with index between input start/end
        """
        if machine_names:
            self.machines = {name: self.machines[name] for name in machine_names}

        if start_end != (-1, -1):
            self.machines = {
                name: machine
                for name, machine in self.machines.items()
                if start_end[0] <= get_machine_index(name) <= start_end[1]
            }
        return self

    ####################### Basic informations, regardless of scanning #######################
    @property
    def num_machine(self) -> int:
        """Number of machines in the group"""
        return len(self.machines)

    @property
    def num_cpu(self) -> int:
        """Number of cpu cores in the group"""
        return sum(machine.num_cpu for machine in self.machines.values())

    @property
    def num_gpu(self) -> int:
        """Number of gpu in the group"""
        return sum(
            machine.num_gpu
            for machine in self.machines.values()
            if isinstance(machine, GPUMachine)
        )

    ##################### Busy, free informations, valid after scanning #####################
    @property
    def busy_machines(self) -> list[Machine]:
        """List of busy machines, which has more than one job"""
        return [machine for machine in self.machines.values() if machine.num_job]

    @property
    def num_job(self) -> int:
        """Number of running jobs inside group"""
        return sum(machine.num_job for machine in self.busy_machines)

    @property
    def free_machines(self) -> list[Machine]:
        """List of machines with at least one free core"""
        return [machine for machine in self.machines.values() if machine.num_available]

    @property
    def num_free_machine(self) -> int:
        """Number of free machines, which has more than one free core (either cpu or gpu)"""
        return len(self.free_machines)

    @property
    def num_free_cpu(self) -> int:
        """Number of free cpu cores in the group"""
        return sum(machine.num_free_cpu for machine in self.free_machines)

    @property
    def num_free_gpu(self) -> int:
        """Number of free gpu cores in the group"""
        return sum(
            machine.num_free_gpu
            for machine in self.free_machines
            if isinstance(machine, GPUMachine)
        )

    ############################# Line Format Information for Print #############################
    def __format__(self, format_spec: str) -> str:
        """
        Return group information according to format spec
        - info: group information of machines/cores
        - free: group free informations
        - job: group information of running jobs
        """
        # group summary of machine information
        if format_spec == "info":
            group_info = Printer.group_info_format.format(
                self.name, self.num_machine, self.num_cpu
            )
            if self.num_gpu:
                group_info += "\n" + Printer.group_gpu_info_format.format(
                    "", self.num_gpu
                )

        # group summary of machine free information
        elif format_spec == "free":
            group_info = Printer.group_info_format.format(
                self.name, self.num_free_machine, self.num_free_cpu
            )
            if self.num_gpu:
                group_info += "\n" + Printer.group_gpu_info_format.format(
                    "", self.num_free_gpu
                )

        # group summary of every jobs at group
        elif format_spec == "job":
            group_info = Printer.group_job_info_format.format(
                self.name, len(self.busy_machines), self.num_job
            )
        else:
            group_info = self.name

        return group_info

    ############################ Get Information of Group Instance ############################
    def get_user_count(self) -> Counter[str]:
        """Return the dictionary of {user name: number of jobs}"""
        user_count = Counter()
        for machine in self.machines.values():
            user_count.update(machine.get_user_count())
        return user_count

    ############################## Scan Job Information and Save ##############################
    def scan(
        self,
        user_name: str | None,
        progress_bar: ProgressBar | None,
        job_condition: JobCondition | None = None,
        include_parents: bool = False,
    ) -> None:
        """
        scan all machines in machines.
        Args
            user_name: Refer command.ps_from_user
            progress_bar: If given, update it's status per every machine scanning
            job_condition: Refer Job.match_condition
            include_parents: Refer machine.scan
        """
        if progress_bar is None:

            def scan_machine(machine: Machine) -> None:
                machine.scan(user_name, job_condition, include_parents)

        else:

            def scan_machine(machine: Machine) -> None:
                machine.scan(user_name, job_condition, include_parents)
                progress_bar.update(machine.name)

        # Multi-threaded scanning: maximum worker w.r.t Windows (61)
        with cf.ThreadPoolExecutor(max_workers=61) as executor:
            executor.map(scan_machine, self.machines.values())

    ##################################### Run Jobs #####################################
    def runs(
        self, commands: deque[str], max_calls: int, single_machine_limit: int
    ) -> deque[str]:
        """
        Run jobs in commands
        Args
            commands: commands to be run
            max_calls: maximum number of jobs that group can run in a single execution
            single_machine_limit: Maximum number of jobs that a machine can run
        Return
            Remaining commands after run
        """
        num_executed, num_threads = 0, min(len(commands), max_calls)

        # Run commands on free machines
        with cf.ThreadPoolExecutor(max_workers=50) as executor:
            for machine in self.free_machines:
                for _ in range(min(machine.num_available, single_machine_limit)):
                    executor.submit(machine.run, commands.popleft().strip())
                    num_executed += 1

                    if num_executed >= num_threads:
                        # number of executed reached it's limit
                        return commands

        # Return the remining command queue
        return commands

    def force_runs(
        self, commands: deque[str], max_calls: int, single_machine_limit: int
    ) -> deque[str]:
        """
        Forece run jobs in commands: Run job not only in free machine, but also in busy machines
        Args
            commands: commands to be run
            max_calls: maximum number of jobs that group can run in a single execution
            single_machine_limit: Maximum number of jobs that a machine can run
        Return
            Remaining commands after run
        """
        num_executed, num_threads = 0, min(len(commands), max_calls)

        # Run commands on every machines
        with cf.ThreadPoolExecutor(max_workers=50) as executor:
            for machine in self.machines.values():
                for _ in range(min(machine.num_core, single_machine_limit)):
                    executor.submit(machine.run, commands.popleft().strip())
                    num_executed += 1

                    if num_executed >= num_threads:
                        # number of executed reached it's limit
                        return commands

        # Return the remining command queue
        return commands
