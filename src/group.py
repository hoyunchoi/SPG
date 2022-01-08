import json
from pathlib import Path
import concurrent.futures as cf
from collections import abc, deque, Counter

from .job import JobCondition
from .spgio import Printer, ProgressBar
from .machine import Machine, GPUMachine


class Group:
    """
        Save the information of group of machines
        By default, machines are read from group file
        When SPG gets specific machine list from argument, machines will be changed
    """

    def __init__(self, group_name: str, group_file: Path) -> None:
        """
            Initialize machine group information from group File
            Args:
                group_name: name of machine group
                group_file: Full path of machine file.
                First line should be comment
        """
        # Default informations
        self.name: str = group_name                 # Name of machine group. Ex) tenet
        self.machine_dict: dict[str, Machine] = {}  # Dictionary of machines

        # Summary informations
        self.num_machine: int = 0                   # Number of machines in the group
        self.num_cpu: int = 0                       # Number of cpu cores in the group
        self.num_gpu: int = 0                       # Number of gpu in the group

        # Free informations
        self.free_machine_list: list[Machine] = []  # List of machines with at least one free core
        self.num_free_machine: int = 0              # Number of machines with free core
        self.num_free_cpu: int = 0                  # Number of free cpu cores in the group
        self.num_free_gpu: int = 0                  # Number of free gpu cors in the group

        # Current informations
        self.busy_machine_list: list[Machine] = []  # List of machines having running job
        self.num_job: int = 0                       # Number of running jobs

        # KILL
        self.num_kill: int = 0                      # Number of killed jobs

        # Initialize group and corresponding machines
        self._read_group_file(group_file)
        self.update_summary()

    def _read_group_file(self, group_file: Path) -> None:
        """ Read group file and store machine information to machine_dict """
        with open(group_file, "r") as file:
            machine_dict = json.load(file)

        # Initialize dictionary of machine
        for machine_name, machine_info in machine_dict.items():
            if machine_info.get("gpu") is None:
                # When no gpu keyword, machine is cpu machine
                machine = Machine(**machine_info)
            else:
                # Otherwise, machine is gpu machine
                machine = GPUMachine(**machine_info)

            # Only store machine explicitly marked as "use = True"
            if machine.use:
                self.machine_dict[machine_name] = machine

    def update_summary(self) -> None:
        """
            Update summary information of group
            number of machines / cpu cores / gpus
        """
        self.num_machine = len(self.machine_dict)
        self.num_cpu = sum(machine.num_cpu for machine in self.machine_dict.values())
        self.num_gpu = sum(machine.num_gpu for machine in self.machine_dict.values())

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return group information according to format spec
            - info: group information of machines/cores
            - free: group free informations
            - job: group information of running jobs
        """
        # group summary of machine information
        group_info = self.name
        if format_spec == "info":
            group_info = Printer.group_info_format.format(
                self.name, self.num_machine, self.num_cpu
            )
            if self.num_gpu:
                group_info += "\n" + Printer.group_gpu_info_format.format("", self.num_gpu)

        # group summary of machine free information
        elif format_spec == "free":
            group_info = Printer.group_info_format.format(
                self.name, self.num_free_machine, self.num_free_cpu
            )
            if self.num_gpu:
                group_info += "\n" + Printer.group_gpu_info_format.format("", self.num_free_gpu)

        # group summary of every jobs at group
        elif format_spec == "job":
            group_info = Printer.group_job_info_format.format(
                self.name, len(self.busy_machine_list), self.num_job
            )

        return group_info

    ############################ Get Information of Group Instance ############################
    def _get_job_info(self) -> tuple[int, list[Machine]]:
        """
            Get running job informations
            Return
                num_job: number of running jobs
                busy_machine_list: list of machines who is running one or more jobs
        """
        busy_machine_list = [machine
                             for machine in self.machine_dict.values()
                             if machine.num_job]
        num_job = sum(busy_machine.num_job for busy_machine in busy_machine_list)

        return num_job, busy_machine_list

    def _get_free_info(self) -> tuple[int, int, list[Machine]]:
        """
            Get free information
            Return
                num_free_cpu: number of free cpu cores
                num_free_gpu: number of free gpus
                free_machine_list: list of machine who has one or more free cores / gpus
        """
        def filter_free(machine_list: abc.Iterable[Machine]) -> abc.Iterable[Machine]:
            """ Return iterable of free machine """
            for machine in machine_list:
                if ((type(machine) == Machine and machine.num_free_cpu) or
                        (isinstance(machine, GPUMachine) and machine.num_free_gpu)):
                    yield machine

        free_machine_list = [machine for machine in filter_free(self.machine_dict.values())]
        num_free_cpu = sum(machine.num_free_cpu for machine in free_machine_list)
        num_free_gpu = sum(machine.num_free_gpu for machine in free_machine_list
                           if isinstance(machine, GPUMachine))

        return num_free_cpu, num_free_gpu, free_machine_list

    def get_user_count(self) -> Counter[str]:
        """ Return the dictionary of {user name: number of jobs} """
        user_count = Counter()
        for machine in self.machine_dict.values():
            user_count.update(machine.get_user_count())
        return user_count

    ############################## Scan Job Information and Save ##############################
    def scan_job(self,
                 user_name: str | None,
                 progress_bar: ProgressBar | None,
                 job_condition: JobCondition | None = None) -> None:
        """
            Scan job of every machines in machineList
            num_job, busy_machine_list will be updated
            If user Name is not given, free informations will also be updated
            Args
                user_name: Refer command.ps_from_user for more description
                scan_level: Refer Job.is_important for more description
        """
        if progress_bar is None:
            def scan_machine(machine: Machine) -> None:
                machine.scan_job(user_name, job_condition)
        else:
            def scan_machine(machine: Machine) -> None:
                machine.scan_job(user_name, job_condition)
                progress_bar.update(machine.name)

        # Multi-threaded scanning: maximum worker w.r.t Windows (61)
        with cf.ThreadPoolExecutor(max_workers=61) as executor:
            executor.map(scan_machine, self.machine_dict.values())

        # Save the scanned information
        self.num_job, self.busy_machine_list = self._get_job_info()
        if user_name is None:
            # When user_name is None, also need to update free information
            self.num_free_cpu, self.num_free_gpu, self.free_machine_list = self._get_free_info()
            self.num_free_machine = len(self.free_machine_list)

    ##################################### Run or Kill Job #####################################
    def runs(self,
             cmd_queue: deque[str],
             max_calls: int) -> deque[str]:
        """
            Run jobs in cmd_queue
            Return
                cmd_queue: Remaining commands after run
        """
        # Run commands
        with cf.ThreadPoolExecutor(max_workers=50) as executor:
            num_thread = min(len(cmd_queue), max_calls)
            for _, machine in zip(range(num_thread), self.free_machine_list):
                if isinstance(machine, GPUMachine):
                    # For gpu machine, number of free gpu should be counted
                    available = min(machine.num_free_cpu, machine.num_free_gpu)
                else:
                    available = machine.num_free_cpu

                # Iterate over available slots
                for _ in range(available):
                    try:
                        command = cmd_queue.popleft().strip()
                    except IndexError:
                        # When there is no command left in cmd_queue
                        break
                    executor.submit(machine.run, command)

        # Return the remining command queue
        return cmd_queue


if __name__ == "__main__":
    print("This is module Group from SPG")
