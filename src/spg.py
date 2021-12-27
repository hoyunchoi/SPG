#! /usr/bin/python

from pathlib import Path
import concurrent.futures as cf
from collections import abc, deque, Counter

from .group import Group
from .option import Option
from .default import Default
from .machine import Machine
from .job import JobCondition
from .argument import Argument
from .spgio import Printer, MessageHandler
from .utils import get_machine_group, get_machine_index


class SPG:
    """ SPG : Statistical Physics Group """

    def __init__(self, args: Argument) -> None:
        # Save arguments
        self.args = args

        # Dictionary of machine group
        group_file_dict = Default().get_group_file_dict()
        self.group_dict: dict[str, Group] = {
            group_name: Group(group_name, group_file)
            for group_name, group_file in group_file_dict.items()
        }

        # Prune group dictionary and corresponding machine dictionary
        if args.option is Option.runs:
            # args.group is str and has 'start_end' attribute
            assert isinstance(args.group, str)
            self.group_dict = {args.group: self.group_dict[args.group]}
            if args.start_end is not None:
                start, end = args.start_end
                group = self.group_dict[args.group]
                group.machine_dict = {
                    machine.name: machine for machine in group.machine_dict.values()
                    if (start <= get_machine_index(machine.name) <= end)
                }
                group.update_summary()

        elif isinstance(args.machine, list):
            # args.machine is specified, so as args.group
            assert isinstance(args.group, list)
            self.group_dict = {
                group_name: self.group_dict[group_name] for group_name in args.group
            }
            machine_per_group = self._find_machine_per_group(args.machine, args.group)
            # Prune machine dictionary per each groups
            for group_name, group in self.group_dict.items():
                group.machine_dict = {
                    machine.name: machine for machine in machine_per_group[group_name]
                }
                group.update_summary()

        elif isinstance(args.group, list):
            # args.machine is not specified but args.group is specified
            self.group_dict = {
                group_name: self.group_dict[group_name] for group_name in args.group
            }

        # printer and message handlers
        if args.option is Option.user:
            assert not isinstance(args.group, str)
            self.printer = Printer(args.option, args.silent, args.group)
        else:
            self.printer = Printer(args.option, args.silent)
        self.message_handler = MessageHandler()

    def __call__(self) -> None:
        # Run SPG
        getattr(self, self.args.option.name)()

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

    def _find_machine_per_group(self,
                                machine_name_list: list[str],
                                group_name_list: list[str]) -> dict[str, list[Machine]]:
        """ Find list of machines per each group """
        machine_per_group: dict[str, list[Machine]] = {
            group_name: [] for group_name in group_name_list
        }
        for machine_name in machine_name_list:
            machine = self._find_machine_from_name(machine_name)
            group_name = get_machine_group(machine_name)
            machine_per_group[group_name].append(machine)

        return machine_per_group

    ############################## Scan Job Information and Save ##############################
    def scan_job(self,
                 group_list: abc.Iterable[Group],
                 user_name: str | None,
                 job_condition: JobCondition | None = None) -> None:
        """
            Scan running jobs
            Args
                group_list: target of groups to scan
                user_name: whose job to scan
                scan_level: refer Job.isImportant
        """
        def scan_group(group: Group) -> None:
            bar = self.printer.bar_dict.get(group.name)
            group.scan_job(user_name, bar, job_condition)

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
        self.scan_job(self.group_dict.values(), user_name=None)

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
        job_condition = JobCondition(pid=self.args.pid,
                                     command=self.args.command,
                                     time=self.args.time_seconds,
                                     start=self.args.start)

        # Scanning
        self.scan_job(self.group_dict.values(), self.args.user, job_condition)

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.group_dict.values():
            for machine in group.busy_machine_list:
                for job in machine.job_list:
                    self.printer.print(f"{job:info}")
                self.printer.print()

        # Summary
        for group in self.group_dict.values():
            self.printer.print(f"{group:job}")
        self.printer.print()

    def user(self) -> None:
        """ Print job count of users per machine group """
        # Scanning
        self.scan_job(self.group_dict.values(), user_name=None)

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
        assert isinstance(self.args.machine, str)
        machine = self._find_machine_from_name(self.args.machine)

        # Scanning
        machine.scan_job(user_name=None)

        # When no free core is detected, doule check the run command
        if not machine.num_free_cpu:
            self.message_handler.warning(
                f"WARNING: {self.args.machine} has no free core!"
            )

        # Run a job
        assert self.args.command is not None
        machine.run(self.args.command)

    def runs(self, max_calls: int = 50) -> None:
        """ Run several jobs """
        # Find group
        group = next(iter(self.group_dict.values()))

        # Read command file
        assert self.args.command is not None
        cmd_file = Path(self.args.command).resolve()
        with open(cmd_file, "r") as f:
            cmd_queue = deque(f.read().splitlines())
        num_cmd_before = len(cmd_queue)

        # Scanning
        self.scan_job([group], user_name=None)
        if not self.printer.silent:
            self.printer.print()

        # Run jobs
        cmd_queue = group.runs(cmd_queue, max_calls)
        num_cmd_after = len(cmd_queue)

        # Remove the input file and re-write with remaining command queue
        cmd_file.unlink()
        with open(cmd_file, "w") as f:
            f.write("\n".join(str(cmd) for cmd in cmd_queue))

        self.message_handler.success(f"\nRun {num_cmd_before - num_cmd_after} jobs")
        return None

    def KILL(self) -> None:
        """ kill all matching jobs """
        job_condition = JobCondition(pid=self.args.pid,
                                     command=self.args.command,
                                     time=self.args.time_seconds,
                                     start=self.args.start)
        # Scanning
        self.scan_job(self.group_dict.values(), self.args.user, job_condition)
        if not self.printer.silent:
            self.printer.print()

        # Kill jobs
        with cf.ThreadPoolExecutor(max_workers=61) as executor:
            for group in self.group_dict.values():
                for machine in group.busy_machine_list:
                    for job in machine.job_list:
                        executor.submit(machine.kill, job)

        # Summarize the kill result
        num_kill = 0
        for group in self.group_dict.values():
            num_kill += sum(machine.num_kill for machine in group.busy_machine_list)
        self.message_handler.success(f"\nKilled {num_kill} jobs")
        return None


if __name__ == "__main__":
    print("This is module spg from SPG")
