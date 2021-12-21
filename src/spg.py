#! /usr/bin/python

import argparse
from pathlib import Path
import concurrent.futures as cf
from typing import Optional, Iterable
from collections import deque, Counter

from .group import Group
from .default import Default
from .machine import Machine
from .utils import get_machine_group
from .spgio import Printer, MessageHandler, ProgressBar


class SPG:
    """ SPG : Statistical Physics Group """

    def __init__(self, args: argparse.Namespace) -> None:
        # Save arguments
        self.args = args

        # Dictionary of machine group
        group_file_dict = Default().get_group_file_dict()
        self.group_dict: dict[str, Group] = {
            group_name: Group(group_name, group_file)
            for group_name, group_file in group_file_dict.items()
        }

        # Prune group dictionary
        if hasattr(args, "machine") and isinstance(args.machine, list):
            # List of target machines per each group
            machine_per_group: dict[str, list[Machine]] = {
                group_name: [] for group_name in args.group
            }
            for machine_name in args.machine:
                machine = self._find_machine_from_name(machine_name)
                group_name = get_machine_group(machine_name)
                machine_per_group[group_name].append(machine)

            # update group dict
            for group_name in list(self.group_dict):
                if group_name in args.group:
                    # Update machine dict for each group
                    self.group_dict[group_name].prune_machine_dict(
                        machine_per_group[group_name]
                    )
                else:
                    del self.group_dict[group_name]

        elif hasattr(args, "group") and isinstance(args.group, list):
            # Update group dict
            self.group_dict = {
                group_name: self.group_dict[group_name]
                for group_name in args.group
            }

        # printer and message handlers
        if hasattr(args, "group"):
            self.printer = Printer(args.option, args.group, args.silent)
        else:
            self.printer = Printer(args.option, None, args.silent)
        self.message_handler = MessageHandler()

    def __call__(self) -> None:
        # Run SPG
        getattr(self, self.args.option)()

    ###################################### Basic Utility ######################################
    def _find_group_from_name(self, group_name: str) -> Group:
        """ Find group instance with it's name """
        try:
            return self.group_dict[group_name]
        except KeyError:
            # group with input name is not registered in spg
            self.message_handler.error(f"ERROR: No such machine group: {group_name}")
            exit()

    def _find_machine_from_name(self, machine_name: str) -> Machine:
        """ Find machine instance with it's name """
        # Find group
        group_name = get_machine_group(machine_name)
        group = self._find_group_from_name(group_name)

        # Find machine inside the group
        try:
            return group.machine_dict[machine_name]
        except KeyError:
            # machine with input name is not registered in the group
            self.message_handler.error(f"ERROR: No such machine: {machine_name}")
            exit()

    ############################## Scan Job Information and Save ##############################
    def scan_job(self,
                 group_list: Iterable[Group],
                 user_name: Optional[str],
                 scan_level: int) -> None:
        """
            Scan running jobs
            Args
                group_list: target of groups to scan
                user_name: whose job to scan
                scan_level: refer Job.isImportant
        """
        def scan_group(group: Group) -> None:
            bar: Optional[ProgressBar] = self.printer.bar_dict.get(group.name)
            group.scan_job(user_name, scan_level, bar)

        if not self.printer.silent:
            # Decorate tqdm bar when using tqdm
            self.printer.print()

        # Define progressbar
        for group in group_list:
            self.printer.add_progress_bar(group.name, set(group.machine_dict))

        # Scan job for every groups in group list
        with cf.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(scan_group, group_list)

        # Close progressbar
        for group in group_list:
            self.printer.close_progress_bar(group.name)

    ####################################### SPG command #######################################
    def list(self) -> None:
        """ Print information of machines registered in SPG """
        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_dict.values():
            for machine in group.machine_dict.values():
                self.printer.print(f"{machine:info}")
            self.printer.print()

        # Summary
        for group in self.group_dict.values():
            self.printer.print(f"{group:info}")
        self.printer.print()

    def free(self) -> None:
        """ Print list of machine free information """
        # Scanning
        self.scan_job(self.group_dict.values(), user_name=None, scan_level=2)

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_dict.values():
            for machine in group.free_machine_list:
                self.printer.print(f"{machine:free}")
            if group.num_free_machine:
                self.printer.print()

        # Summary
        for group in self.group_dict.values():
            self.printer.print(f"{group:free}")
        self.printer.print()

    def job(self) -> None:
        """ Print current state of jobs """
        # Scanning
        self.scan_job(self.group_dict.values(), user_name=self.args.user, scan_level=2)

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_dict.values():
            group.num_job = 0
            for machine in group.busy_machine_list:
                for job in machine.job_list:
                    if job.match(self.args):
                        self.printer.print(f"{job:info}")
                        group.num_job += 1
                self.printer.print()

        # Summary
        for group in self.group_dict.values():
            self.printer.print(f"{group:job}")
        self.printer.print()

    def user(self) -> None:
        """ Print job count of users per machine group """
        # Scanning
        self.scan_job(self.group_dict.values(), user_name=None, scan_level=2)

        # Get user count
        num_job_per_user = Counter()
        num_job_per_user_per_group: dict[str, Counter[str]] = {}
        for group in self.group_dict.values():
            group_user_count = group.get_user_count()
            num_job_per_user_per_group[group.name] = group_user_count
            num_job_per_user.update(group_user_count)

        # First section
        self.printer.print_first_section()

        # Main section
        user_format = self.printer.user_format
        for user, tot_count in num_job_per_user.items():
            self.printer.print(user_format.format(
                user,
                tot_count,
                *tuple(num_job_per_user_per_group[group.name].get(user, 0)
                       for group in self.group_dict.values())
            ))
        self.printer.print()

        # Summary
        self.printer.print(user_format.format(
            "total",
            sum(num_job_per_user.values()),
            *tuple(group.num_job for group in self.group_dict.values())
        ))
        self.printer.print()

    def run(self) -> None:
        """ Run a job """
        # Find machine
        machine = self._find_machine_from_name(self.args.machine)

        # Scanning
        machine.scan_job(user_name=None, scan_level=2)

        # When no free core is detected, doule check the run command
        if not machine.num_free_cpu:
            self.message_handler.warning(
                f"WARNING: {self.args.machine} has no free core!"
            )

        # Run a job
        machine.run(self.args.command)

    def runs(self, max_calls: int = 50) -> None:
        """ Run several jobs """
        # Find group
        group = self._find_group_from_name(self.args.group)

        # Read command file
        cmd_file = Path(self.args.command).resolve()
        with open(cmd_file, "r") as f:
            cmd_queue = deque(f.read().splitlines())
        num_cmd_before = len(cmd_queue)

        # Scanning
        self.scan_job([group], user_name=None, scan_level=2)
        if not self.printer.silent:
            self.printer.print()

        # Run jobs
        cmd_queue = group.runs(cmd_queue, max_calls, self.args.start_end)
        num_cmd_after = len(cmd_queue)

        # Remove the input file and re-write with remaining command queue
        cmd_file.unlink()
        with open(cmd_file, "w") as f:
            f.write("\n".join(str(cmd) for cmd in cmd_queue))

        self.message_handler.success(f"\nRun {num_cmd_before - num_cmd_after} jobs")
        return None

    def KILL(self) -> None:
        """ kill all matching jobs """
        def kill_group(group: Group) -> None:
            group.KILL(self.args)

        # Scanning
        self.scan_job(self.group_dict.values(), self.args.user, scan_level=1)
        if not self.printer.silent:
            self.printer.print()

        # Kill jobs
        with cf.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(kill_group, self.group_dict.values())

        # Summarize the kill result
        num_kill = sum(group.num_kill for group in self.group_dict.values())
        self.message_handler.success(f"\nKilled {num_kill} jobs")
        return None


if __name__ == "__main__":
    print("This is module spg from SPG")
