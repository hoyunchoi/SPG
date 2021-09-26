import re
import argparse
import subprocess
from collections import Counter
from typing import Optional
from dataclasses import dataclass

from default import default
from interaction import Printer, message_handler, run_kill_logger
from command import Command
from job import CPUJob, GPUJob, Job


@dataclass
class Machine:
    """
        data class for storing machine informations
        GPUMachine will be inherited from this class
    """
    use: bool                       # Whether to be used or not: 1 for use, 0 for not use
    name: str                       # Name of machine. ex) tenet1
    cpu: str                        # Name of cpu
    num_cpu: int                    # Number of cpu cores
    ram: str                        # Size of RAM
    comment: str                    # comment of machine. Not used
    gpu: Optional[str] = ''         # Name of gpu (if exists)
    num_gpu: Optional[int] = 0      # Number of gpus (if exists)
    vram: Optional[str] = ''        # Size of VRAM per each gpu (if exists)

    def __post_init__(self) -> None:
        """
            Post processing initialize
        """
        self.use = self.use.lower() in ['true', '1']
        self.num_cpu = int(self.num_cpu)

        # Current job/free information
        self.job_dict: dict[str, Job] = {}       # Dictionary of running jobs with key of PID
        self.num_job: int = 0                    # Number of running jobs = len(jobList)
        self.num_free_cpu: int = 0               # Number of free cpu cores
        self.free_ram: str = ''                  # Size of free memory

        # KILL
        self.num_kill: int = 0                   # Number of killed jobs

        # Default variables
        self.log_dict = {'machine': self.name, 'user': default.user}
        self.cmd_ssh = Command.get_ssh_cmd(self.name)

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
    def __find_cmd_from_pid(self, pid: str) -> str:
        """
            Find command line in userJobList by pid
            Args
                pid: target pid
            Return
                command: command of the process
        """
        try:
            return self.job_dict[pid].cmd

        # Job with input pid is not registered
        except KeyError:
            message_handler.error(f'ERROR: No such process in {self.name}: {pid}')
            exit()

    @staticmethod
    def get_group_name(machine_name: str) -> int:
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
    def _get_process_list(self, get_process_cmd: str) -> Optional[list[str]]:
        """
            Get list of processes
            When error occurs during SSH, return None
            Args
                get_process_cmd: command to find process inside ssh client
            Return
                CPU Machine: List of process from 'ps'
                GPU Machine: List of process from 'nvidia-smi'
        """
        result = subprocess.run(f'{self.cmd_ssh} \"{get_process_cmd}\"',
                                capture_output=True,
                                text=True,
                                shell=True)
        # Check scan error
        if result.stderr:
            message_handler.error(f'ERROR from {self.name}: {result.stderr.strip()}')
            return None
        # If there is no error return list of stdout
        return result.stdout.strip().split('\n')

    def _get_free_ram(self) -> str:
        """
            Return absolute value of free RAM
        """
        result = subprocess.run(f'{self.cmd_ssh} \"{Command.get_free_ram_cmd()}\"',
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        return result.stdout.strip()

    def scan_job(self, user_name: str, scan_level: int) -> None:
        """
            Scan the processes of input user.
            job_dict, num_job will be updated
            when user_name is None: free informations will also be updated
            when machine is GPUMachine: num_free_gpu, free_vram will also be updated
            Args
                user_name: Refer getprocessList for more description
                scan_level: Refer 'Job.is_important' for more description

            For CPU Machine, select important job from _get_process_list
            For GPU Machine, do thread job __scanGPU over GPUs
        """
        # Get list of raw process: Use ps command
        process_list = self._get_process_list(Command.get_ps_cmd(user_name))

        # When error occurs, process_list is None. Do nothing and return
        if process_list is None:
            return

        # Save scanned job informations
        for process in process_list:
            if process:
                job = CPUJob(self.name, process)
                if job.is_important(scan_level):
                    self.job_dict[job.pid] = job
        self.num_job = len(self.job_dict)

        # If user name is None, update free informations too
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()

    def get_user_count(self) -> Counter[str, int]:
        """
            Return the Counter of {user name: number of jobs}
        """
        user_list = [job.user_name for job in self.job_dict.values()]
        return Counter(user_list)

    ##################################### Run or Kill Job #####################################
    def run(self, command: str) -> None:
        """
            run process
            Args
                path: Where command is done
                cmds: list of commands including program/arguments
        """
        # cd to path and run the command as background process
        subprocess.run(f'{self.cmd_ssh} \"{Command.get_run_cmd(command)}\" &',
                       shell=True)

        # Print the result and save to logger
        message_handler.success(f"SUCCESS {self.name:<10}: run \'{command}\'")
        run_kill_logger.info(f'spg run {command}', extra=self.log_dict)

    def KILL(self, args: argparse.Namespace) -> None:
        """
            Kill every job satisfying args
        """
        self.log_dict['user'] = args.user_name
        self.num_kill = 0
        for job in self.job_dict.values():
            if job.is_kill(args):
                # Find command for print result/logging
                command = self.__find_cmd_from_pid(job.pid)

                # self.killPID(job.pid)
                self.__kill(job)
                self.num_kill += 1

                # Print the result and save to logger
                message_handler.success(f"SUCCESS {self.name:<10}: kill \'{command}\'")
                run_kill_logger.info(f'spg kill {command}', extra=self.log_dict)

    def __kill(self, job: Job) -> None:
        """
            Kill job and all the process until it's session leader
        """
        # Command to kill very processes until reaching session leader
        cmd_kill = f'{self.cmd_ssh} \"{Command.get_kill_cmd(job.pid)}; '
        pid = job.pid
        while pid != job.sid:
            # Update pid to it's ppid
            pid = subprocess.check_output(f'{self.cmd_ssh} \"{Command.get_ppid_cmd(pid)}\"',
                                          text=True,
                                          shell=True).strip()
            cmd_kill += f'{Command.get_kill_cmd(job.pid)}; '
        cmd_kill += '\"'

        # Run kill command
        result = subprocess.run(cmd_kill, shell=True, capture_output=True, text=True)

        # When error occurs, save it
        if result.stderr:
            kill_error_list = result.stderr.strip().split('\n')
            message_handler.error('\n'.join(f'ERROR from {self.name}: {kill_error}'
                                            for kill_error in kill_error_list))


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

    def __get_free_vram(self) -> str:
        """
            Get free vram information
            When one or more gpus is free, print it's total vram
            Otherwise, print largest available memory
        """
        # When one or more gpu is free
        if self.num_free_gpu:
            return self.vram

        # Otherwise, get list of free vram
        result = subprocess.run(f'{self.cmd_ssh} \"{Command.get_free_vram_cmd()}\"',
                                stdout=subprocess.PIPE,
                                text=True,
                                shell=True)
        free_vram_list = result.stdout.strip().split('\n')
        max_free_vram = max(float(free_vram) for free_vram in free_vram_list)
        max_free_vram *= 1.04858      # Mebibyte to Megabyte
        return Job.get_mem_with_unit(max_free_vram, 'MB')

    def scan_job(self, user_name: str, scan_level: int) -> None:
        """
            update job_dict and num_free_gpu
            1. For every process in GPUs, check their pid
                2-1. If there is no process, update num_free_gpu
                2-2. If there is such process, find ps information by pid
                    3-1. If user_name from ps information matches, check the importance of job
                        4-1. If the job is important, save the job to job_dict
        """
        # Get list of raw process: Use nvidia-smi command
        process_list = self._get_process_list(Command.get_ns_process_cmd())

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
            ps_info = subprocess.run(f'{self.cmd_ssh} \"{Command.get_ps_from_pid_cmd(pid)}\"',
                                     stdout=subprocess.PIPE,
                                     text=True,
                                     shell=True).stdout

            # Store the information to job Dict
            if (user_name is None) or (ps_info.strip().split()[0] == user_name):
                job = GPUJob(f'{self.name}-GPU{ns_info[0]}', ps_info, *ns_info[2:])
                if job.is_important(scan_level):      # Most likely to be true
                    self.job_dict[pid] = job
        self.num_job = len(self.job_dict)

        # Update free information
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()
            self.free_vram = self.__get_free_vram()


if __name__ == "__main__":
    print("This is moudle 'Machine' from SPG")
