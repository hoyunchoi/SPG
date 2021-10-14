import json
import argparse

from pathlib import Path
from threading import Thread
from typing import Union, Any
from collections import deque, Counter

from spgio import Printer
from machine import Machine, GPUMachine


class Group:
    """
        Save the information of group of machines
        By default, machine group is defined by group file
        When SPG got specific machine list, machines will be changed
    """

    def __init__(self, group_name: str, group_file: Path) -> None:
        """
            Initialize machine group information from group File
            Args:
                group_name: name of machine group
                group_file: Full path of machine file.
                First line should be comment
        """
        # Printer for grpu
        self.printer = Printer()

        # Default informations
        self.name: str = group_name                  # Name of machine group. Ex) tenet
        self.machine_dict: dict[str, Machine] = {}   # Dictionary of machines with key of machine name
        self.num_machine: int = 0                    # Number of machines in the group = len(machineList)
        self.num_cpu: int = 0                        # Number of cpu cores in the group
        self.num_gpu: int = 0                        # Number of gpu in the group

        # Free informations
        # List of machines with at least one free core
        self.free_machine_list: list[Union[Machine, GPUMachine]] = []
        self.num_free_machine: int = 0               # Number of machines with at least one free core = len(free_machine_list)
        self.num_free_cpu: int = 0                   # Number of free cpu cores in the group
        self.num_free_gpu: int = 0                   # Number of free gpu cors in the group

        # Current informations
        self.busy_machine_list: list[Machine] = []   # List of machines running one or more jobs
        self.num_job: int = 0                        # Number of running jobs

        # KILL
        self.num_kill: int = 0                       # Number of killed jobs

        # Initialize group and corresponding machines
        self._read_group_file(group_file)
        self._update_summary()

    def __setattr__(self, name: str, value: Any) -> None:
        """
            Set attribute of group member
            when machine dictionary is updated, automatically update summary information too
        """
        super().__setattr__(name, value)
        if name == "machine_dict":
            self._update_summary()

    def _read_group_file(self, group_file: Path) -> None:
        """
            Read group file and store machine information to machine_dict
        """
        with open(group_file, 'r') as file:
            machine_dict = json.load(file)

        # Initialize dictionary of machine
        for machine_name, machine_info in machine_dict.items():
            # When no gpu keyword, machine is cpu machine
            if machine_info.get('gpu') is None:
                machine = Machine(**machine_info)
            # Otherwise, machine is gpu machine
            else:
                machine = GPUMachine(**machine_info)

            # Only store machine explicitly marked as "use" = "True"
            if machine.use:
                self.machine_dict[machine_name] = machine

    def _update_summary(self) -> None:
        """
            Update summary information of group
            number of machines
            number of cpu cores
            number of gpus
        """
        self.num_machine = len(self.machine_dict)
        self.num_cpu = sum(machine.num_cpu for machine in self.machine_dict.values())
        self.num_gpu = sum(machine.num_gpu for machine in self.machine_dict.values())

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return machine information in line format
            Args
                format_spec: which information to return
                    - info: group summary of machine information
                    - free: group summary of machine free information
                    - job: group summary of every jobs at group
                    - otherwise: group name
        """
        if format_spec == 'info':
            group_info = Printer.group_info_format.format(self.name, self.num_machine, self.num_cpu)
            if self.num_gpu:
                return (group_info + '\n' +
                        Printer.group_gpu_info_format.format('', self.num_gpu))
            else:
                return group_info

        if format_spec == 'free':
            groupFreeInfo = Printer.group_info_format.format(self.name, self.num_free_machine, self.num_free_cpu)
            if self.num_gpu:
                return (groupFreeInfo + '\n' +
                        Printer.group_gpu_info_format.format('', self.num_free_gpu))
            else:
                return groupFreeInfo

        if format_spec == "job":
            return Printer.group_job_info_format.format(self.name, self.num_job)

        return self.name

    ############################ Get Information of Group Instance ############################
    def _get_job_info(self) -> tuple[int, list[Machine]]:
        """
            Get running job informations
            Return
                num_job: number of running jobs
                busy_machine_list: list of machines who is running one or more jobs
        """
        busy_machine_list = [machine for machine in self.machine_dict.values() if machine.num_job]
        num_job = sum(busy_machine.num_job for busy_machine in busy_machine_list)

        return num_job, busy_machine_list

    def _get_free_info(self) -> tuple[int, int, list[Union[Machine, GPUMachine]]]:
        """
            Get free information
            Return
                num_free_cpu: number of free cpu cores
                num_free_gpu: number of free gpus
                free_machine_list: list of machine who has one or more free cores / gpus
        """
        free_machine_list = [machine for machine in self.machine_dict.values()
                             if machine.num_free_cpu or
                             (isinstance(machine, GPUMachine) and machine.num_free_gpu)]
        num_free_cpu = sum(machine.num_free_cpu
                           for machine in free_machine_list)
        num_free_gpu = sum(machine.num_free_gpu
                           for machine in free_machine_list
                           if isinstance(machine, GPUMachine))

        return num_free_cpu, num_free_gpu, free_machine_list

    def get_user_count(self) -> Counter[str]:
        """
            Return the dictionary of {user name: number of jobs}
        """
        user_count = Counter()
        for machine in self.machine_dict.values():
            user_count.update(machine.get_user_count())
        return user_count

    ############################## Scan Job Information and Save ##############################
    def scan_job(self, user_name: str, scan_level: int) -> None:
        """
            Scan job of every machines in machineList
            num_job, busy_machine_list will be updated
            If user Name is not given, free informations will also be updated
            Args
                user_name: refer Machine.getJobList
                scan_level: refer Job.isImportant
        """
        def scan_job_and_update_bar(machine: Machine):
            """ Scan job and update bar """
            machine.scan_job(user_name, scan_level)
            self.printer.update_tqdm(self.name, machine.name)

        # Define progressbar
        self.printer.add_tqdm(self.name, set(self.machine_dict))

        # Scan job without updating bar
        if self.printer.bar_width is None:
            thread_list = [Thread(target=machine.scan_job, args=(user_name, scan_level))
                           for machine in self.machine_dict.values()]
        # Scan job with updating bar
        else:
            thread_list = [Thread(target=scan_job_and_update_bar, args=(machine,))
                           for machine in self.machine_dict.values()]
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        # Save the scanned information
        self.num_job, self.busy_machine_list = self._get_job_info()
        if user_name is None:
            self.num_free_cpu, self.num_free_gpu, self.free_machine_list = self._get_free_info()
            self.num_free_machine = len(self.free_machine_list)

        # Close progressbar
        self.printer.close_tqdm(self.name)

    ##################################### Run or Kill Job #####################################
    def runs(self,
             cmdQueue: deque[str],
             maxCalls: int,
             startEnd: tuple[int, int] = None) -> deque[str]:
        """
            Run jobs in cmdQueue
            Return
                cmdQueue: Remaining commands after run
        """
        # When start/end machine index is not given, iterate over all machines
        if startEnd is None:
            free_machine_list = self.free_machine_list
        # When start/end machine index is given, iterate only over given machines
        else:
            free_machine_list = [free_machine for free_machine in self.free_machine_list
                                 if startEnd[0] <= Machine.get_index(free_machine.name) <= startEnd[1]]

        # Run commands
        thread_list = []
        for _, machine in zip(range(min(len(cmdQueue), maxCalls)), free_machine_list):
            # For gpu machine, number of free gpu should be counted
            if isinstance(machine, GPUMachine):
                available_slot = min(machine.num_free_cpu, machine.num_free_gpu)
            else:
                available_slot = machine.num_free_cpu

            # Iterate over available slots
            for _ in range(available_slot):
                if cmdQueue:
                    command = cmdQueue.popleft().strip()
                    thread_list.append(Thread(target=machine.run, args=(command,)))

        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        # Return the remining command queue
        return cmdQueue

    def KILL(self, args: argparse.Namespace) -> None:
        thread_list = [Thread(target=machine.KILL, args=(args,)) for machine in self.busy_machine_list]
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        # Summarize the kill result
        self.num_kill = sum(machine.num_kill for machine in self.busy_machine_list)


if __name__ == "__main__":
    print("This is module 'Group' from SPG")
