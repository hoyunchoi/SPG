#! /usr/bin/python

import argparse
import subprocess
from typing import Optional
from threading import Thread
from collections import deque, Counter

from group import Group
from machine import Machine
from argument import Argument

from default import Default
from spgio import Printer, MessageHandler, create_logger


class SPG:
    """ SPG """

    def __init__(self) -> None:
        self.group_dict: dict[str, Group] = {}    # Dictionary of machine group with key of group name

        # Initialize group dictionary
        for group_name, group_file in Default().get_group_file_dict().items():
            self.group_dict[group_name] = Group(group_name, group_file)

        # Printer and message handlers
        self.printer = Printer()
        self.message_handler = MessageHandler()

        # Options
        self.target_group_list: list[Group]       # List of groups from arguments
        self.option = {'list': self.list,
                       'free': self.free,
                       'job': self.job,
                       'user': self.user,
                       'run': self.run,
                       'runs': self.runs,
                       'KILL': self.KILL}

    def __call__(self, args: argparse.Namespace) -> None:
        """
            Run functions according to the input argumetns
        """
        # Setup printer
        self.printer.initialize(args)

        # Get group list
        try:
            self.group_list = self._find_group_list_from_argument(args)
        # In case of option 'run', machine name list is not defined
        except AttributeError:
            pass

        # Run SPG
        self.option[args.option](args)

    ###################################### Basic Utility ######################################
    def _find_group_from_name(self, group_name: str) -> Group:
        """
            Find group instance in group_list
        """
        try:
            return self.group_dict[group_name]

        # Group with input name is not registered
        except KeyError:
            self.message_handler.error(f'ERROR: No such machine group: {group_name}')
            exit()

    def _find_group_list_from_group_name_list(self, group_name_list: Optional[list[str]]) -> list[Group]:
        """
            Find list of group instance from group name list
        """
        if group_name_list is None:
            return list(self.group_dict.values())
        else:
            return [self._find_group_from_name(group_name) for group_name in group_name_list]

    def _find_machine_from_name(self, machine_name: str) -> Machine:
        """
            Find Machine instance in group_list
        """
        group_name = Machine.get_group_name(machine_name)
        group = self._find_group_from_name(group_name)

        try:
            return group.machine_dict[machine_name]

        # machine with input name is not registered in spg group
        except KeyError:
            self.message_handler.error(f'ERROR: No such machine: {machine_name}')
            exit()

    def _find_group_list_from_machine_name_list(self, machine_name_list: list[str]) -> list[Group]:
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
            # Group name already appeared before: append to the list
            if group_name in machine_list_per_group:
                machine_list_per_group[group_name].append(machine)
            # Group name appeared first time: make new list
            else:
                machine_list_per_group[group_name] = [machine]

        # update group dict
        for group_name, machine_list in machine_list_per_group.items():
            self.group_dict[group_name].machine_dict = {machine.name: machine for machine in machine_list}

        # Return list of updated group list
        return self._find_group_list_from_group_name_list(list(machine_list_per_group))

    def _find_group_list_from_argument(self, args: argparse.Namespace) -> list[Group]:
        """
            Return list of group from arguments
        """
        # When machine list is not specified
        if args.machine_name_list is None:
            return self._find_group_list_from_group_name_list(args.group_name_list)
        # When machine list is specified
        else:
            return self._find_group_list_from_machine_name_list(args.machine_name_list)

    ############################## Scan Job Information and Save ##############################
    def scan_job(self,
                 group_list: list[Group],
                 user_name: Optional[str],
                 scan_level: int) -> None:
        """
            Scan running jobs
            Args
                targetGroupList: list of group to scan
                user_name: whose job to scan
                scan_level: refer Job.isImportant
        """
        # Decorate tqdm bar
        if self.printer.bar_width is not None:
            self.printer.print()

        # Scan job for every groups in group list
        thread_list = [Thread(target=group.scan_job, args=(user_name, scan_level))
                       for group in group_list]
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

    ####################################### SPG command #######################################
    def list(self, args: argparse.Namespace) -> None:
        """
            Print information of machines registered in SPG
        """
        # first section
        self.printer.print_first_section()

        # main section
        for group in self.group_list:
            for machine in group.machine_dict.values():
                self.printer.print(f'{machine:info}')
            self.printer.print()

        # summary
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

        # main section
        for group in self.group_list:
            for machine in group.free_machine_list:
                self.printer.print(f'{machine:free}')
            if group.num_free_machine:
                self.printer.print()

        # summary
        for group in self.group_list:
            self.printer.print(f'{group:free}')
        self.printer.print()

    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """

        # Scanning
        self.scan_job(self.group_list, user_name=args.user_name, scan_level=2)

        # ----------------------- Print -----------------------
        # First section
        self.printer.print_first_section()

        # main section
        for group in self.group_list:
            for machine in group.busy_machine_list:
                for job in machine.job_list:
                    self.printer.print(f'{job:info}')
                self.printer.print()

        # Print summary
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
        total_user_count = Counter()      # Total number of jobs per user
        group_user_count_dict = {}        # Number of jobs per user per group
        for group in self.group_list:
            group_user_count = group.get_user_count()
            group_user_count_dict[group.name] = group_user_count
            total_user_count.update(group_user_count)

        # First section
        self.printer.print_first_section()

        # main section
        for user, tot_count in total_user_count.items():
            self.printer.print_line_format(user,
                                      tot_count,
                                      *tuple(group_user_count_dict[group.name].get(user, 0)
                                             for group in self.group_list))
        self.printer.print()

        # summary
        self.printer.print_summary_format('total',
                                     sum(total_user_count.values()),
                                     *tuple(group.num_job for group in self.group_list))
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
            self.message_handler.warning(f'WARNING: {args.machine_name} has no free core!')

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
        subprocess.run(['rm', args.cmd_file])
        with open(args.cmd_file, 'w') as f:
            f.write('\n'.join(str(cmd) for cmd in cmd_queue))

        self.message_handler.success(f'\nRun {num_cmd_before - num_cmd_after} jobs')
        return None

    def KILL(self, args: argparse.Namespace) -> None:
        """
            kill job
        """
        # When machine list is not specified
        if args.machine_name_list is None:
            group_list = self._find_group_list_from_group_name_list(args.group_name_list)
        # When machine list is specified
        else:
            group_list = self._find_group_list_from_machine_name_list(args.machine_name_list)

        # Scanning
        self.scan_job(group_list, args.user_name, scan_level=1)
        if not args.silent:
            self.printer.print()

        # Kill jobs
        thread_list = [Thread(target=group.KILL, args=(args,)) for group in group_list]
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        # Summarize the kill result
        num_kill = sum(group.num_kill for group in group_list)
        self.message_handler.success(f'\nKilled {num_kill} jobs')
        return None


def main():
    # Get arguments
    arguments = Argument()
    args = arguments.get_args()

    # Create logger
    create_logger()

    # Run SPG according to arguments
    spg = SPG()
    spg(args)


if __name__ == "__main__":
    main()
