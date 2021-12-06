#! /usr/bin/python

import argparse
from pathlib import Path
from typing import Optional
import concurrent.futures as cf
from collections import deque, Counter

from src.group import Group
from src.default import Default
from src.machine import Machine
from src.argument import Argument
from src.spgio import Printer, MessageHandler, configure_logger


class SPG:
    def __init__(self) -> None:
        """
            SPG : Statistical Physics Group
        """
        # Dictionary of machine group
        self.group_dict: dict[str, Group] = {
            group_name: Group(group_name, group_file)
            for group_name, group_file in Default().get_group_file_dict().items()
        }
        self.group_list: list[Group] = []       # Target group from arguments

        # Printer and message handlers
        self.printer = Printer()
        self.message_handler = MessageHandler()

    def __call__(self, args: argparse.Namespace) -> None:
        """
            Run functions according to the input argumetns
        """
        # Setup printer
        self.printer.initialize(args)

        # Get group list
        try:
            self.group_list = self._find_group_list_from_argument(args)
        except AttributeError:
            # In case of option 'run', machine name list is not defined
            pass

        # Run SPG
        getattr(self, args.option)(args)

    ###################################### Basic Utility ######################################
    def _find_group_from_name(self, group_name: str) -> Group:
        """
            Find group instance in group_list
        """
        try:
            return self.group_dict[group_name]

        except KeyError:
            # Group with input name is not registered in spg
            self.message_handler.error(f'ERROR: No such machine group: {group_name}')
            exit()

    def _find_group_list_from_group_name_list(
        self,
        group_name_list: Optional[list[str]]
    ) -> list[Group]:
        """
            Find list of group instance from group name list
            Args
                group_name_list: list of groups names to find. If None, return all groups
        """
        if group_name_list is None:
            return list(self.group_dict.values())
        else:
            return [self._find_group_from_name(group_name)
                    for group_name in group_name_list]

    def _find_machine_from_name(self, machine_name: str) -> Machine:
        """
            Find Machine instance in group_list
        """
        # First, find group
        group_name = Machine.get_group_name(machine_name)
        group = self._find_group_from_name(group_name)

        # Find machine inside the group
        try:
            return group.machine_dict[machine_name]
        except KeyError:
            # machine with input name is not registered in the group
            self.message_handler.error(f'ERROR: No such machine: {machine_name}')
            exit()

    def _find_group_list_from_machine_name_list(
        self,
        machine_name_list: list[str]
    ) -> list[Group]:
        """
            update group dict corresponding to input machine name list
            return list of updated Group instances
        """
        # key: group_name, value: list of Machines at group
        machine_list_per_group: dict[str, list[Machine]] = {}

        # Store information of machine name list
        for machine_name in machine_name_list:
            machine = self._find_machine_from_name(machine_name)
            group_name = Machine.get_group_name(machine_name)

            if group_name in machine_list_per_group:
                # Group name already appeared before: append to the list
                machine_list_per_group[group_name].append(machine)
            else:
                # Group name appeared first time: make new list
                machine_list_per_group[group_name] = [machine]

        # update group dict
        for group_name, machine_list in machine_list_per_group.items():
            self.group_dict[group_name].machine_dict = {
                machine.name: machine for machine in machine_list
            }

        # Return list of updated group list
        return self._find_group_list_from_group_name_list(list(machine_list_per_group))

    def _find_group_list_from_argument(self, args: argparse.Namespace) -> list[Group]:
        """
            Return list of group from arguments
        """
        if args.machine_name_list is None:
            # When machine list is not specified
            return self._find_group_list_from_group_name_list(args.group_name_list)
        else:
            # When machine list is specified
            return self._find_group_list_from_machine_name_list(args.machine_name_list)

    ############################## Scan Job Information and Save ##############################
    def scan_job(self,
                 group_list: list[Group],
                 user_name: Optional[str],
                 scan_level: int) -> None:
        """
            Scan running jobs
            Args
                group_list: list of group to scan
                user_name: whose job to scan
                scan_level: refer Job.isImportant
        """
        def scan_group(group: Group) -> None:
            group.scan_job(user_name, scan_level)

        if self.printer.bar_width is not None:
            # Decorate tqdm bar when using tqdm
            self.printer.print()

        # Scan job for every groups in group list
        with cf.ThreadPoolExecutor() as executor:
            executor.map(scan_group, group_list)

    ####################################### SPG command #######################################
    def list(self, args: argparse.Namespace) -> None:
        """
            Print information of machines registered in SPG
        """
        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_list:
            for machine in group.machine_dict.values():
                self.printer.print(f'{machine:info}')
            self.printer.print()

        # Summary
        for group in self.group_list:
            self.printer.print(f'{group:info}')
        self.printer.print()

    def free(self, args: argparse.Namespace) -> None:
        """
            Print list of machine free information
        """
        self.scan_job(self.group_list, user_name=None, scan_level=2)

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_list:
            for machine in group.free_machine_list:
                self.printer.print(f'{machine:free}')
            if group.num_free_machine:
                self.printer.print()

        # Summary
        for group in self.group_list:
            self.printer.print(f'{group:free}')
        self.printer.print()

    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """
        self.scan_job(self.group_list, user_name=args.user_name, scan_level=2)

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_list:
            for machine in group.busy_machine_list:
                for job in machine.job_list:
                    self.printer.print(f'{job:info}')
                self.printer.print()

        # Summary
        for group in self.group_list:
            self.printer.print(f'{group:job}')
        self.printer.print()

    def user(self, args: argparse.Namespace) -> None:
        """
            Print job count of users per machine group
        """
        # Scanning
        self.scan_job(self.group_list, user_name=None, scan_level=2)

        # Get user count
        num_job_per_user = Counter()
        num_job_per_user_per_group: dict[str, Counter[str]] = {}
        for group in self.group_list:
            group_user_count = group.get_user_count()
            num_job_per_user_per_group[group.name] = group_user_count
            num_job_per_user.update(group_user_count)

        # First section
        self.printer.print_first_section()

        # Main section
        for user, tot_count in num_job_per_user.items():
            self.printer.print_line_format(
                user,
                tot_count,
                *tuple(num_job_per_user_per_group[group.name].get(user, 0)
                       for group in self.group_list)
            )
        self.printer.print()

        # Summary
        self.printer.print_summary_format(
            'total',
            sum(num_job_per_user.values()),
            *tuple(group.num_job for group in self.group_list)
        )
        self.printer.print()

    def run(self, args: argparse.Namespace) -> None:
        """
            Run a job
        """
        # Find machine and scan current state
        machine = self._find_machine_from_name(args.machine_name)
        machine.scan_job(user_name=None, scan_level=2)

        # When no free core is detected, doule check the run command
        if not machine.num_free_cpu:
            self.message_handler.warning(
                f'WARNING: {args.machine_name} has no free core!'
            )

        # Run a job
        machine.run(args.command)

    def runs(self, args: argparse.Namespace, max_calls: int = 50) -> None:
        """
            Run several jobs
        """
        # Handle arguments
        group = self._find_group_from_name(args.group_name)
        with open(args.cmd_file, 'r') as f:
            cmd_queue = f.read().splitlines()
        cmd_queue = deque(cmd_queue)
        num_cmd_before = len(cmd_queue)

        # Scanning
        self.scan_job([group], user_name=None, scan_level=2)
        if not args.silent:
            self.printer.print()

        # Run jobs
        cmd_queue = group.runs(cmd_queue, max_calls, args.start_end)
        num_cmd_after = len(cmd_queue)

        # Remove the input file and re-write with remaining command queue
        Path(args.cmd_file).unlink()
        with open(args.cmd_file, 'w') as f:
            f.write('\n'.join(str(cmd) for cmd in cmd_queue))

        self.message_handler.success(f'\nRun {num_cmd_before - num_cmd_after} jobs')
        return None

    def KILL(self, args: argparse.Namespace) -> None:
        """
            kill job
        """
        def kill_group(group: Group) -> None:
            group.KILL(args)

        if args.machine_name_list is None:
            # When machine list is not specified
            group_list = self._find_group_list_from_group_name_list(args.group_name_list)
        else:
            # When machine list is specified
            group_list = self._find_group_list_from_machine_name_list(args.machine_name_list)

        # Scanning
        self.scan_job(group_list, args.user_name, scan_level=1)
        if not args.silent:
            self.printer.print()

        # Kill jobs
        with cf.ThreadPoolExecutor() as executor:
            executor.map(kill_group, group_list)

        # Summarize the kill result
        num_kill = sum(group.num_kill for group in group_list)
        self.message_handler.success(f'\nKilled {num_kill} jobs')
        return None


def main():
    # Get arguments
    arguments = Argument()
    args = arguments.get_args()

    # Create logger
    configure_logger()

    # Run SPG according to arguments
    spg = SPG()
    spg(args)


if __name__ == "__main__":
    main()
