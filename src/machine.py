import logging
import subprocess
from collections import abc, Counter
from dataclasses import dataclass, field

from . import command
from .default import Default
from .utils import get_mem_with_unit
from .spgio import Printer, MessageHandler
from .job import CPUJob, GPUJob, Job, JobCondition


@dataclass
class Machine:
    """ data class for storing machine informations """
    use: bool                               # Whether to be used or not: True for use
    name: str                               # Name of machine. ex) tenet1
    cpu: str                                # Name of cpu
    num_cpu: int                            # Number of cpu cores
    ram: str                                # Size of RAM
    comment: str                            # comment of machine. Not used
    gpu: str = field(default="")            # Name of gpu (if exists)
    num_gpu: int = field(default=0)         # Number of gpus (if exists)
    vram: str = field(default="")           # Size of VRAM per each gpu (if exists)

    def __post_init__(self) -> None:
        self.use = (self.use == "True")     # Use to boolean
        self.num_cpu = int(self.num_cpu)    # number of cpus to int

        # Current job/free information
        self.job_list: list[Job] = []       # List of running jobs
        self.num_job: int = 0               # Number of running jobs = len(jobList)
        self.num_free_cpu: int = 0          # Number of free cpu cores
        self.free_ram: str = ""             # Size of free memory

        # KILL
        self.num_kill: int = 0              # Number of killed jobs

        # Default variables
        self.cmd_ssh = command.ssh_to_machine(self.name)
        self.message_handler = MessageHandler()
        self.logger = logging.getLogger("SPG")
        self.log_dict = {"machine": self.name, "user": Default().user}

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return machine information according to format spec
            - info: machine information
        r    - free: machine free information
            - otherwise: machine name
        """
        machine_info = self.name
        if format_spec.lower() == "info":
            machine_info = Printer.machine_info_format.format(
                self.name, self.cpu, self.num_cpu, "core", self.ram
            )

        elif format_spec.lower() == "free":
            machine_info = Printer.machine_free_info_format.format(
                self.name, self.cpu, str(self.num_free_cpu), "core", f"{self.free_ram} free"
            )
        return machine_info

    ###################################### Basic Utility ######################################
    def _find_cmd_from_pid(self, pid: str) -> list[str]:
        """
            Find cmd line in job_list by pid
            There can be serveral dispatchable entities with same pid.
            Return all jobs with such pid
            Args
                pid: target pid
            Return
                cmd: list of commands having target pid
        """
        # Find list of cmd sharing same pid
        cmd_list = [job.cmd for job in self.job_list if job.pid == pid]

        # Job with input pid is not registered
        if not cmd_list:
            self.message_handler.error(
                f"ERROR: No such process in {self.name}: {pid}"
            )
            exit()

        return cmd_list

    ########################### Get Information of Machine Instance ###########################
    def _get_process_list(self, get_process_cmd: list[str]) -> list[str]:
        """
            Get list of processes
            When error occurs during SSH, return None
            Args
                get_process_cmd: cmd to find process inside ssh client
            Return
                CPU Machine: List of process from 'ps'
                GPU Machine: List of process from 'nvidia-smi'
        """
        result = subprocess.run(self.cmd_ssh + get_process_cmd,
                                capture_output=True,
                                text=True)
        # Check scan error
        if result.stderr:
            self.message_handler.error(
                f"ERROR from {self.name}: {result.stderr.strip()}"
            )
            raise RuntimeError

        # If there is no error return list of stdout
        return result.stdout.strip().split("\n")

    def _get_free_ram(self) -> str:
        """ Return absolute value of free RAM """
        free_ram = subprocess.check_output(self.cmd_ssh + command.free_ram(),
                                           text=True)
        return free_ram.split("\n")[1].split()[-1]

    def scan_job(self,
                 user_name: str | None,
                 job_condition: JobCondition | None = None) -> None:
        """
            Scan the processes of input user.
            job_list, num_job will be updated
            when machine is GPUMachine: num_free_gpu, free_vram will also be updated
            Args
                user_name: Refer command.ps_from_user for more description
                scan_level: Refer Job.is_important for more description
        """
        # Get list of raw process
        try:
            process_list = self._get_process_list(command.ps_from_user(user_name))
        except RuntimeError:
            # When error occurs, Do nothing and return since error is already reported
            return

        # Save scanned job informations
        for process in process_list:
            job = CPUJob(self.name, process)
            if job.is_important() and job.match(job_condition):
                self.job_list.append(job)
        self.num_job = len(self.job_list)

        # If user name is None, update free informations too
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()

    def get_user_count(self) -> Counter[str]:
        """ Return the Counter of {user name: number of jobs} """
        return Counter(job.user_name for job in self.job_list)

    ##################################### Run or Kill Job #####################################
    def run(self, cmd: str) -> None:
        """ run input command at current directory """
        # Run cmd on background
        subprocess.Popen(self.cmd_ssh + command.run_at_cwd(cmd))

        # Print the result and save to logger
        self.message_handler.success(f"SUCCESS {self.name:<10}: run '{cmd}'")

        # Log
        self.logger.info(f"spg run {cmd}", extra=self.log_dict)

    def kill(self, job: Job) -> None:
        """ Kill job and all the process until it's session leader """
        # Find cmd list for print result
        cmd_list = self._find_cmd_from_pid(job.pid)

        # Open process for ssh
        ssh_process = subprocess.Popen(self.cmd_ssh,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True)

        # list of kill commands that should be run at machine
        cmd_kill = command.kill_pid(job.pid)
        pid = job.pid

        # command to kill very processes until reaching session leader
        while pid != job.sid:
            # Update pid to it's ppid
            pid = subprocess.check_output(self.cmd_ssh + command.pid_to_ppid(pid),
                                          text=True).strip()
            # When ppid is root process, do not touch
            if pid == "1":
                break
            cmd_kill += command.kill_pid(pid)

        # Run kill cmd inside ssh target machine
        _, kill_err = ssh_process.communicate(" ".join(cmd_kill))

        # When error occurs, save it
        if kill_err:
            kill_err_list = kill_err.strip().split("\n")
            self.message_handler.error(
                "\n".join(f"ERROR from {self.name}: {err}"
                          for err in kill_err_list)
            )
            return

        # Print the result and log
        for cmd in cmd_list:
            self.message_handler.success(f"SUCCESS {self.name:<10}: kill '{cmd}'")
            self.logger.info(f"spg kill {cmd}", extra=self.log_dict)

        # Update number of kills
        self.num_kill += 1


class GPUMachine(Machine):
    def __post_init__(self) -> None:
        # Do same thing with normal (cpu) machine
        super().__post_init__()
        self.num_gpu = int(self.num_gpu)

        # GPU free information
        self.num_free_gpu = 0
        self.free_vram = ""

    def __format__(self, format_spec: str) -> str:
        machine_info = super().__format__(format_spec)    # Format of (CPU) Machine
        if format_spec.lower() == "info":
            machine_info += "\n" + Printer.machine_info_format.format(
                "", self.gpu, self.num_gpu, "gpus", self.vram
            )

        elif format_spec.lower() == "free":
            machine_info += "\n" + Printer.machine_free_info_format.format(
                "", self.gpu, self.num_free_gpu, "gpus", f"{self.free_vram} free"
            )
        return machine_info

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
        free_vram_list = subprocess.check_output(self.cmd_ssh + command.free_vram(),
                                                 text=True).strip().split("\n")

        # Get maximum free vram
        max_free_vram = max(float(free_vram) for free_vram in free_vram_list)
        max_free_vram *= 1.04858                                    # Mebibyte to Megabyte
        return get_mem_with_unit(max_free_vram, "MB")[:-1]          # Drop byte character (B)

    def scan_job(self,
                 user_name: str | None,
                 job_condition: JobCondition | None = None) -> None:
        """
            update job_list and num_free_gpu
            1. For every process in GPUs, check their pid
                2-1. If there is no process, update num_free_gpu
                2-2. If there is such process, find ps information by pid
                    3-1. If user_name from ps information matches, check the importance of job
                        4-1. If the job is important, save the job to job_list
        """
        def filter_by_user(ps_info_list: list[str]) -> abc.Iterable[str]:
            """ Return iterable of ps_info which belongs to user_name """
            # When user name is None, return all ps info
            if user_name is None:
                for ps_info in ps_info_list:
                    yield ps_info

            # When user name is specified, return ps info belongs to user
            for ps_info in ps_info_list:
                if ps_info.strip().split()[0] == user_name:
                    yield ps_info
        # Get list of raw process: Use nvidia-smi
        try:
            process_list = self._get_process_list(command.ns_process())
        except RuntimeError:
            # When error occurs, Do nothing and return since error is already reported
            return

        # First two lines of process list are column names
        for process in process_list[2:]:
            (gpu_idx, pid, _, gpu_percent,
             vram_percent, _, _, vram_use, _) = process.strip().split()

            # When no information is detected, nvidia-smi returns "-"
            if pid == "-":
                self.num_free_gpu += 1  # num_free_gpu is updated regardless of user_name
                continue
            vram_use = get_mem_with_unit(vram_use, "MB")
            if gpu_percent == "-":
                gpu_percent = "0"
            if vram_percent == "-":
                vram_percent = f"{float(vram_use[:-2]) / float(self.vram[:-1]) * 100.0:.0f}"

            # Get 'ps' information from PID of ns_info
            ps_info_list = subprocess.check_output(self.cmd_ssh + command.ps_from_pid(pid),
                                                   text=True).strip().split("\n")

            # Store the information to job list
            for ps_info in filter_by_user(ps_info_list):
                job = GPUJob(machine_name=f"{self.name}-GPU{gpu_idx}",
                             info=ps_info,
                             gpu_percent=gpu_percent,
                             vram_percent=vram_percent,
                             vram_use=vram_use)
                if job.match(job_condition):
                    self.job_list.append(job)
                    break                             # Single job per pid
        self.num_job = len(self.job_list)

        # Update free information
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()
            self.free_vram = self._get_free_vram()


if __name__ == "__main__":
    print("This is moudle Machine from SPG")
