import re
import logging
import argparse
import subprocess
from collections import Counter
from typing import Optional, Union
from dataclasses import dataclass, field

from default import Default
from command import Command
from job import CPUJob, GPUJob, Job
from spgio import Printer, MessageHandler


@dataclass
class Machine:
    """
        data class for storing machine informations
        GPUMachine will be inherited from this class
    """
    use: Union[str, bool]               # Whether to be used or not: True for use, False for not use
    name: str                           # Name of machine. ex) tenet1
    cpu: str                            # Name of cpu
    num_cpu: int                        # Number of cpu cores
    ram: str                            # Size of RAM
    comment: str                        # comment of machine. Not used
    gpu: str = field(default='')        # Name of gpu (if exists)
    num_gpu: int = field(default=0)     # Number of gpus (if exists)
    vram: str = field(default='')       # Size of VRAM per each gpu (if exists)

    def __post_init__(self) -> None:
        """
            Post processing initialize
        """
        self.use = (self.use == "True")
        self.num_cpu = int(self.num_cpu)

        # Current job/free information
        self.job_list: list[Job] = []   # List of running jobs
        self.num_job: int = 0           # Number of running jobs = len(jobList)
        self.num_free_cpu: int = 0      # Number of free cpu cores
        self.free_ram: str = ''         # Size of free memory

        # KILL
        self.num_kill: int = 0          # Number of killed jobs

        # Default variables
        self.cmd_ssh = Command.ssh_to_machine(self.name)
        self.message_handler = MessageHandler()
        self.logger = logging.getLogger("SPG")
        self.log_dict = {'machine': self.name, 'user': Default().user}

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return machine information in line format
            Args
                format_spec: which information to return
                    - info: machine information
                    - free: machine free information
                    - otherwise: machine name
        """
        if format_spec.lower() == 'info':
            return Printer.machine_info_format.format(self.name, self.cpu, self.num_cpu,
                                                      'core', self.ram)

        if format_spec.lower() == 'free':
            return Printer.machine_free_info_format.format(self.name, self.cpu, str(self.num_free_cpu),
                                                           'core', f'{self.free_ram} free')

        return self.name

    ###################################### Basic Utility ######################################
    def _find_cmd_from_pid(self, pid: str) -> list[str]:
        """
            Find command line in job_list by pid
            There can be serveral dispatchable entities with same pid.
            Return all jobs with such pid
            Args
                pid: target pid
            Return
                command: list command of the process
        """
        # Find list of command sharing same pid
        cmd_list = [job.cmd for job in self.job_list if job.pid == pid]

        # Job with input pid is not registered
        if not cmd_list:
            self.message_handler.error(f'ERROR: No such process in {self.name}: {pid}')
            exit()

        return cmd_list

    @staticmethod
    def get_group_name(machine_name: str) -> str:
        """
            Get group name of machine
            ex) tenet100 -> tenet
        """
        return re.sub('[0-9]', '', machine_name)

    @staticmethod
    def get_index(machine_name: str) -> int:
        """
            Get index of machine.
            ex) tenet100 -> 100
        """
        return int(re.sub('[^0-9]', '', machine_name))

    ########################### Get Information of Machine Instance ###########################
    def _get_process_list(self, get_process_cmd: list[str]) -> Optional[list[str]]:
        """
            Get list of processes
            When error occurs during SSH, return None
            Args
                get_process_cmd: command to find process inside ssh client
            Return
                CPU Machine: List of process from 'ps'
                GPU Machine: List of process from 'nvidia-smi'
        """
        result = subprocess.run(self.cmd_ssh + get_process_cmd,
                                capture_output=True,
                                text=True)
        # Check scan error
        if result.stderr:
            self.message_handler.error(f'ERROR from {self.name}: {result.stderr.strip()}')
            return None

        # If there is no error return list of stdout
        return result.stdout.strip().split('\n')

    def _get_free_ram(self) -> str:
        """
            Return absolute value of free RAM
        """
        # Run command without returning error
        stdout = subprocess.check_output(self.cmd_ssh + Command.free_ram(),
                                         text=True)
        return stdout.strip()

    def scan_job(self,
                 user_name: Optional[str],
                 scan_level: int) -> None:
        """
            Scan the processes of input user.
            job_list, num_job will be updated
            when user_name is None: free informations will also be updated
            when machine is GPUMachine: num_free_gpu, free_vram will also be updated
            Args
                user_name: Refer Command.ps_from_user for more description
                scan_level: Refer 'Job.is_important' for more description

            For CPU Machine, select important job from _get_process_list
            For GPU Machine, do thread job __scanGPU over GPUs
        """
        # Get list of raw process: Use ps command
        process_list = self._get_process_list(Command.ps_from_user(user_name))

        # When error occurs, process_list is None. Do nothing and return
        if process_list is None:
            return

        # Save scanned job informations
        for process in process_list:
            if process:
                job = CPUJob(self.name, process)
                if job.is_important(scan_level):
                    self.job_list.append(job)
        self.num_job = len(self.job_list)

        # If user name is None, update free informations too
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()

    def get_user_count(self) -> Counter[str]:
        """
            Return the Counter of {user name: number of jobs}
        """
        return Counter(job.user_name for job in self.job_list)

    ##################################### Run or Kill Job #####################################
    def run(self, command: str) -> None:
        """
            run process
            Args
                path: Where command is done
                cmds: list of commands including program/arguments
        """
        # Run command on background
        subprocess.Popen(self.cmd_ssh + Command.run_at_cwd(command),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             text=True)

        # Print the result and save to logger
        self.message_handler.success(f"SUCCESS {self.name:<10}: run '{command}'")

        # Log
        self.logger.info(f'spg run {command}', extra=self.log_dict)

    def KILL(self, args: argparse.Namespace) -> None:
        """
            Kill every job satisfying args
        """
        self.log_dict['user'] = args.user_name
        self.num_kill = 0

        for job in self.job_list:
            if job.is_kill(args):
                # Find command list for print result
                cmd_list = self._find_cmd_from_pid(job.pid)

                # Kill the target job
                self._kill(job)

                # Print the result and log
                for cmd in cmd_list:
                    self.message_handler.success(f"SUCCESS {self.name:<10}: kill \'{cmd}\'")
                    self.logger.info(f'spg kill {cmd}', extra=self.log_dict)

    def _kill(self, job: Job) -> None:
        """
            Kill job and all the process until it's session leader
        """
        # Open process for ssh
        ssh_process = subprocess.Popen(self.cmd_ssh,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True)

        # list of kill commands that should be run at machine
        cmd_kill: list[str] = Command.kill_pid(job.pid)
        pid = job.pid

        # Command to kill very processes until reaching session leader
        while pid != job.sid:
            # Update pid to it's ppid
            pid = subprocess.check_output(self.cmd_ssh + Command.pid_to_ppid(pid),
                                          text=True).strip()

            # When ppid is root process, do not touch
            if pid == "1":
                break
            cmd_kill += Command.kill_pid(pid)

        # Run kill command inside ssh target machine
        _, err = ssh_process.communicate(' '.join(cmd_kill))

        # When error occurs, save it
        if err:
            kill_error_list = err.strip().split('\n')
            self.message_handler.error('\n'.join(f'ERROR from {self.name}: {kill_error}'
                                                 for kill_error in kill_error_list))
        # Update number of kills
        self.num_kill += 1


class GPUMachine(Machine):
    def __post_init__(self) -> None:
        # Do same thing with normal (cpu) machine
        super().__post_init__()
        self.num_gpu = int(self.num_gpu)

        # GPU free information
        self.num_free_gpu = 0
        self.free_vram = ''

    def __format__(self, format_spec: str) -> str:
        machine_format = super().__format__(format_spec) # Format of Machine
        if format_spec.lower() == 'info':
            return (machine_format + '\n' +
                    Printer.machine_info_format.format('', self.gpu, self.num_gpu, 'gpus', self.vram))

        if format_spec.lower() == 'job':
            return machine_format

        if format_spec.lower() == 'free':
            return (machine_format + '\n' +
                    Printer.machine_free_info_format.format('', self.gpu, self.num_free_gpu,
                                                            'gpus', f'{self.free_vram} free'))
        return self.name

    def _get_free_vram(self) -> str:
        """
            Get free vram information
            When one or more gpus is free, print it's total vram
            Otherwise, print largest available memory
        """
        # When one or more gpu is free
        if self.num_free_gpu:
            return self.vram

        # Otherwise, get list of free vram
        stdout = subprocess.check_output(self.cmd_ssh + Command.free_vram(),
                                         text=True)
        free_vram_list = stdout.strip().split('\n')

        # Get maximum free vram
        max_free_vram = max(float(free_vram) for free_vram in free_vram_list)
        max_free_vram *= 1.04858                                    # Mebibyte to Megabyte
        return Job.get_mem_with_unit(max_free_vram, 'MB')[:-1]      # Drop byte(B)

    def scan_job(self, user_name: str, scan_level: int) -> None:
        """
            update job_list and num_free_gpu
            1. For every process in GPUs, check their pid
                2-1. If there is no process, update num_free_gpu
                2-2. If there is such process, find ps information by pid
                    3-1. If user_name from ps information matches, check the importance of job
                        4-1. If the job is important, save the job to job_list
        """
        # Get list of raw process: Use nvidia-smi command
        process_list = self._get_process_list(Command.ns_process())

        # When error occurs, process_list is None. Do nothing and return
        if process_list is None:
            return None

        # Save scanned job informations
        for process in process_list:
            # Check the process
            ns_info = process.strip().split()    # gpuIdx, pid, gpuPercent, vramPercent, vramUse
            pid = ns_info[1]

            # When no information is detected, nvidia-smi returns '-'
            if pid == '-':
                self.num_free_gpu += 1     # num_free_gpu is updated regardless of user_name
                continue

            # Get 'ps' information from PID of ns_info
            ps_info_list = subprocess.check_output(self.cmd_ssh + Command.ps_from_pid(pid),
                                                   text=True).strip().split('\n')

            # Store the information to job list
            for ps_info in ps_info_list:
                if (user_name is None) or (ps_info.strip().split()[0] == user_name):
                    job = GPUJob(f'{self.name}-GPU{ns_info[0]}', ps_info, *ns_info[2:])
                    if job.is_important(scan_level):      # Most likely to be true
                        self.job_list.append(job)
        self.num_job = len(self.job_list)

        # Update free information
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()
            self.free_vram = self._get_free_vram()


if __name__ == "__main__":
    print("This is moudle 'Machine' from SPG")
