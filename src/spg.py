import concurrent.futures as cf
from collections import Counter, deque
from pathlib import Path
from typing import cast

from .argument import Argument, Option
from .default import Default
from .group import Group
from .job import JobCondition
from .machine import Machine
from .name import extract_alphabet
from .spgio import MessageHandler, Printer


class SPG:
    """SPG : Statistical Physics Group"""

    def __init__(self, args: Argument) -> None:
        # Save arguments
        self.args = args
        self.message_handler = MessageHandler()

        # Dictionary of machine group
        self.groups = {
            name: Group(name, file) for name, file in Default().group_files.items()
        }

        # Prune group dictionary and corresponding machine dictionary
        if args.machine is not None:
            args.group = cast(list[str], args.group)  # Already handled in Argument

            # Match machines at pruned groups
            machines_by_group = self._sort_machines_by_group(args.machine, args.group)
            self.groups = {
                name: self.groups[name].match_machines(machine_names=machines)
                for name, machines in machines_by_group.items()
            }

        elif args.group is not None:
            # args.machine is not specified but args.group is specified
            self.groups = {
                name: self.groups[name].match_machines(start_end=args.start_end)
                for name in args.group
            }

        # printer and message handlers
        self.printer = Printer(args.option, args.silent, args.group)

    def __call__(self, option: Option) -> None:
        # Run SPG
        getattr(self, option.name)()

    ###################################### Basic Utility ######################################
    def _find_group_from_name(self, group_name: str) -> Group:
        """Find group instance with it's name"""
        if group_name in self.groups:
            return self.groups[group_name]

        # group with input name is not registered in spg
        self.message_handler.error(f"ERROR: No such machine group: {group_name}")
        exit()

    def _find_machine_from_name(self, machine_name: str) -> Machine:
        """Find machine instance with it's name"""
        # Find group
        group_name = extract_alphabet(machine_name)
        group = self._find_group_from_name(group_name)

        # Find machine inside the group
        if machine_name in group.machines:
            return group.machines[machine_name]

        # machine with input name is not registered in the group
        self.message_handler.error(f"ERROR: No such machine: {machine_name}")
        exit()

    def _sort_machines_by_group(
        self, machine_names: list[str], group_names: list[str]
    ) -> dict[str, list[str]]:
        """Find list of machines per each group"""
        machines_by_group: dict[str, list[str]] = {
            group_name: [] for group_name in group_names
        }

        for machine_name in machine_names:
            group_name = extract_alphabet(machine_name)
            machines_by_group[group_name].append(machine_name)

        return machines_by_group

    ############################## Scan Job Information and Save ##############################
    def scan(
        self,
        job_condition: JobCondition | None = None,
        include_parents: bool = False,
    ) -> None:
        """
        Scan running jobs
        Args
            scan_level: refer Job.isImportant
            include_parents: If true, also scan parents of running processes
        """

        def scan_group(group: Group) -> None:
            bar = self.printer.bars.get(group.name)
            group.scan(self.args.user, bar, job_condition, include_parents)

        # Decorate tqdm bar if necessary
        self.printer.print_line(follow_silent=True)

        # Define progressbar
        for group_name, group in self.groups.items():
            self.printer.register_progress_bar(group_name, set(group.machines))

        # Scan job for every groups in group list
        with cf.ThreadPoolExecutor(max_workers=len(self.groups)) as executor:
            executor.map(scan_group, self.groups.values())

        # Close progressbar
        self.printer.close_progress_bars()

    ####################################### SPG command #######################################
    def list(self) -> None:
        """Print information of machines registered in SPG"""
        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.groups.values():
            for machine in group.machines.values():
                self.printer.print(f"{machine:info}")
            self.printer.print_line()

        # Summary
        for group in self.groups.values():
            self.printer.print(f"{group:info}")
        self.printer.print_line()

    def free(self) -> None:
        """Print list of machine free information"""
        # Scanning
        self.scan()

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.groups.values():
            for machine in group.free_machines:
                self.printer.print(f"{machine:free}")
            if group.num_free_machine:
                self.printer.print_line()

        # Summary
        for group in self.groups.values():
            self.printer.print(f"{group:free}")
        self.printer.print_line()

    def job(self) -> None:
        """Print current state of jobs"""
        job_condition = JobCondition(
            pid=self.args.pid,
            command=self.args.command,
            time=self.args.time,
            start=self.args.start,
        )

        # Scanning
        self.scan(job_condition)

        # First section
        self.printer.print_first_section()

        # Main section
        for group in self.groups.values():
            for machine in group.busy_machines:
                for job in machine.jobs:
                    self.printer.print(f"{job:info}")
                self.printer.print_line()

        # Summary
        for group in self.groups.values():
            self.printer.print(f"{group:job}")
        self.printer.print_line()

    def user(self) -> None:
        """Print job count of users per machine group"""
        # Scan job for all users
        self.scan()

        # Get user count
        num_job_per_user = Counter()
        num_job_per_user_per_group: dict[str, Counter[str]] = {}
        for group in self.groups.values():
            user_count = group.get_user_count()
            num_job_per_user_per_group[group.name] = user_count
            num_job_per_user.update(user_count)

        # First section
        self.printer.print_first_section()

        # Main section
        for user, tot_count in num_job_per_user.items():
            self.printer.print(
                self.printer.user_format.format(
                    user,
                    tot_count,
                    *(
                        num_job_per_user_per_group[group.name].get(user, 0)
                        for group in self.groups.values()
                    ),
                )
            )
        self.printer.print_line()

        # Summary
        self.printer.print(
            self.printer.user_format.format(
                "total",
                sum(num_job_per_user.values()),
                *(group.num_job for group in self.groups.values()),
            )
        )
        self.printer.print_line()

    def run(self) -> None:
        """Run a job"""
        machine_name = cast(list[str], self.args.machine)[0]  # Already handled
        command = cast(str, self.args.command)  # Already handled

        # Find machine
        machine = self._find_machine_from_name(machine_name)

        # Scanning
        machine.scan(user_name=None)

        # When no free core is detected, doule check the run command
        if not machine.num_free_cpu:
            self.message_handler.warning(
                f"WARNING: {self.args.machine} has no free core!"
            )

        # Run a job
        machine.run(command)

    def runs(self, max_calls: int = Default().MAX_RUNS) -> None:
        """Run several jobs"""
        command_file = cast(str, self.args.command)  # Already handled
        group = list(self.groups.values())[0]  # Already handled

        # Read command file
        with open(Path(command_file).resolve(), "r") as f:
            cmds = f.read().splitlines()
        commands = deque(cmd for cmd in cmds if not cmd.startswith(("#", "//", "%")))
        num_commands_before = len(commands)

        if self.args.force:
            # Force run
            commands = group.force_runs(commands, max_calls, self.args.limit)
        else:
            # Scan first
            self.scan()
            self.printer.print_line(follow_silent=True)

            # Run several jobs
            commands = group.runs(commands, max_calls, self.args.limit)
        num_commands_after = len(commands)

        # Overwrite the remaining command queue
        with open(command_file, "w") as f:
            f.write("\n".join(command for command in commands))

        # Report summary
        self.message_handler.sort()
        self.message_handler.success(
            f"\nRun {num_commands_before - num_commands_after} jobs"
        )

    def KILL(self) -> None:
        """kill all matching jobs"""
        job_condition = JobCondition(
            pid=self.args.pid,
            command=self.args.command,
            time=self.args.time,
            start=self.args.start,
        )
        print(job_condition)

        # Scanning with all parent jobs
        self.scan(job_condition, include_parents=True)
        self.printer.print_line(follow_silent=True)

        # Kill jobs: maximum worker w.r.t Windows (61)
        with cf.ThreadPoolExecutor(max_workers=61) as executor:
            for group in self.groups.values():
                for machine in group.busy_machines:
                    executor.submit(machine.kill)

        # Summarize the kill result
        num_kill = 0
        for group in self.groups.values():
            num_kill += sum(machine.num_kill for machine in group.busy_machines)

        # Report summary
        self.message_handler.sort()
        self.message_handler.success(f"\nKilled {num_kill} jobs")
