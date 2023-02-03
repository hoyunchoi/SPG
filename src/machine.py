import logging
import subprocess
from collections import Counter, abc
from dataclasses import dataclass, field

from . import command
from .default import Default
from .job import CPUJob, GPUJob, Job, JobCondition
from .ram import Ram
from .spgio import MessageHandler, Printer


@dataclass
class Machine:
    """data class for storing machine informations"""

    use: str | bool  # Whether to be used or not: True for use
    name: str  # Name of machine. ex) tenet1
    cpu: str  # Name of cpu
    num_cpu: int  # Number of cpu cores
    ram: Ram  # Size of RAM
    comment: str  # comment of machine. Not used
    gpu: str = field(default="")  # Name of gpu (if exists)
    num_gpu: int = field(default=0)  # Number of gpus (if exists)
    vram: Ram = field(default=Ram())  # Size of VRAM per each gpu (if exists)

    def __post_init__(self) -> None:
        # Machine info
        if self.use != "True":
            self.use = False
            return
        self.num_cpu = int(self.num_cpu)  # number of cpus to int
        self.ram = Ram.from_string(f"{self.ram}B")

        # Current job/free information
        self.job_list: list[Job] = []  # List of running jobs
        self.num_job: int = 0  # Number of running jobs = len(jobList)
        self.num_free_cpu: int = 0  # Number of free cpu cores
        self.free_ram = Ram()  # Size of free memory

        # KILL
        # pid of jobs to be killed, max depth is 10
        self.kill_pid_tree: dict[int, set[int]] = {i: set() for i in range(10)}
        self.num_kill: int = 0  # Number of killed jobs

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
        - free: machine free information
        - otherwise: machine name
        """
        machine_info = self.name
        if format_spec.lower() == "info":
            machine_info = Printer.machine_info_format.format(
                self.name, self.cpu, self.num_cpu, "core", self.ram
            )

        elif format_spec.lower() == "free":
            machine_info = Printer.machine_free_info_format.format(
                self.name,
                self.cpu,
                str(self.num_free_cpu),
                "core",
                f"{self.free_ram} free",
            )
        return machine_info

    ###################################### Basic Utility ######################################
    def _find_cmd_from_pid(self, pid: int) -> str:
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
        cmds = [job.cmd for job in self.job_list if job.pid == pid]

        # Job with input pid is not registered
        if len(cmds) != 1:
            self.message_handler.error(f"ERROR: Problem at identifying process in {self.name}: {pid=}")
            exit()

        return cmds[0]

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
        result = subprocess.run(
            self.cmd_ssh + get_process_cmd, capture_output=True, text=True
        )
        # Check scan error
        if result.stderr:
            self.message_handler.error(
                f"ERROR from {self.name}: {result.stderr.strip()}"
            )
            raise RuntimeError

        # If there is no error return list of stdout
        return result.stdout.strip().split("\n")

    def _get_free_ram(self) -> Ram:
        """Return absolute value of free RAM"""
        free_ram = (
            subprocess.check_output(self.cmd_ssh + command.free_ram(), text=True)
            .split("\n")[1]
            .split()[-1]
        )
        return Ram.from_string(f"{free_ram}B")  # KB, MB, GB unit

    def scan_job(
        self, user_name: str | None, job_condition: JobCondition | None = None
    ) -> None:
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
            if process == "":  # Skip empty string: no process
                continue
            job = CPUJob(self.name, process)
            if job.is_important() and job.match_condition(job_condition):
                self.job_list.append(job)
        self.num_job = len(self.job_list)

        # If user name is None, update free informations too
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()

    def get_user_count(self) -> Counter[str]:
        """Return the Counter of {user name: number of jobs}"""
        return Counter(job.user_name for job in self.job_list)

    ##################################### Run or Kill Job #####################################
    def run(self, cmd: str) -> None:
        """run input command at current directory"""
        # Run cmd on background
        subprocess.run(self.cmd_ssh + command.run_at_cwd(cmd))

        # Print the result and save to logger
        self.message_handler.success(f"SUCCESS {self.name:<10}: run '{cmd}'")

        # Log
        self.logger.info(f"spg run {cmd}", extra=self.log_dict)

    def scan_killed_pids(self, job: Job) -> None:
        """Kill job and all the process until it's session leader"""
        depth, pid = 0, job.pid
        self.kill_pid_tree[depth].add(pid)

        # command to kill very processes until reaching session leader
        while pid != job.sid:
            # Update pid to it's ppid
            ppid = int(
                subprocess.check_output(
                    self.cmd_ssh + command.pid_to_ppid(pid), text=True
                ).strip()
            )
            pid = ppid
            depth += 1
            self.kill_pid_tree[depth].add(pid)

        # Update number of kills
        self.num_kill += 1

    def kill(self) -> None:
        # Filter machine who has nothing to kill
        if not self.kill_pid_tree[0]:
            return

        # stack kill command from depth=0 to higher depth
        cmd_kill = []
        for pids in self.kill_pid_tree.values():
            for pid in pids:
                cmd_kill.extend(command.kill_pid(pid))

        # Run kill cmd inside ssh target machine
        kill_result = subprocess.run(
            self.cmd_ssh + cmd_kill, capture_output=True, text=True
        )

        # When error occurs, save it
        if kill_result.stderr:
            kill_errs = kill_result.stderr.strip().split("\n")
            self.message_handler.error(
                "\n".join(f"ERROR from {self.name}: {err}" for err in kill_errs)
            )
            return

        # Print the result and log
        for pid in self.kill_pid_tree[0]:
            cmd = self._find_cmd_from_pid(pid)
            self.message_handler.success(f"SUCCESS {self.name:<10}: kill '{cmd}'")
            self.logger.info(f"spg kill {cmd}", extra=self.log_dict)


class GPUMachine(Machine):
    def __post_init__(self) -> None:
        # Do same thing with normal (cpu) machine
        super().__post_init__()
        self.num_gpu = int(self.num_gpu)
        self.vram = Ram.from_string(f"{self.vram}B")

        # GPU free information
        self.num_free_gpu = 0
        self.free_vram = Ram()

    def __format__(self, format_spec: str) -> str:
        machine_info = super().__format__(format_spec)  # Format of (CPU) Machine
        if format_spec.lower() == "info":
            machine_info += "\n" + Printer.machine_info_format.format(
                "", self.gpu, self.num_gpu, "gpus", self.vram
            )

        elif format_spec.lower() == "free":
            machine_info += "\n" + Printer.machine_free_info_format.format(
                "", self.gpu, self.num_free_gpu, "gpus", f"{self.free_vram} free"
            )
        return machine_info

    def _get_free_vram(self) -> Ram:
        """
        Get free vram information
        When one or more gpus is free, print it's total vram
        Otherwise, print largest available vram
        """
        # When one or more gpu is free
        if self.num_free_gpu:
            return self.vram

        # Otherwise, get list of free vram
        free_vram_list = (
            subprocess.check_output(self.cmd_ssh + command.free_vram(), text=True)
            .strip()
            .split("\n")
        )

        # Get maximum free vram
        return max(map(Ram.from_string, free_vram_list))

    def scan_job(
        self, user_name: str | None, job_condition: JobCondition | None = None
    ) -> None:
        """
        update job_list and num_free_gpu
        1. For every process in GPUs, check their pid
            2-1. If there is no process, update num_free_gpu
            2-2. If there is such process, find ps information by pid
                3-1. If user_name from ps information matches, check the importance of job
                    4-1. If the job is important, save the job to job_list
        """

        def filter_by_user(ps_info_list: list[str]) -> abc.Iterable[str]:
            """Return iterable of ps_info which belongs to user_name"""
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
            process_info = process.strip().split()
            gpu_idx = int(process_info[0])

            # When no information is detected, nvidia-smi returns "-"
            pid = int(process_info[1].replace("-", "-1"))
            if pid == -1:
                # num_free_gpu is updated regardless of user_name
                self.num_free_gpu += 1
                continue
            gpu_percent = float(process_info[3].replace("-", "0"))
            vram_use = Ram.from_string(f"{process_info[7]}MB")
            vram_percent = vram_use / self.vram * 100.0

            # Get 'ps' information from PID of ns_info
            ps_info_list = (
                subprocess.check_output(
                    self.cmd_ssh + command.ps_from_pid(pid), text=True
                )
                .strip()
                .split("\n")
            )

            # Store the information to job list
            for ps_info in filter_by_user(ps_info_list):
                job = GPUJob(
                    machine_name=f"{self.name}-GPU{gpu_idx}",
                    ps_info=ps_info,
                    gpu_percent=gpu_percent,
                    vram_use=vram_use,
                    vram_percent=vram_percent,
                )
                if job.match_condition(job_condition):
                    self.job_list.append(job)
                    break  # Single job per pid
        self.num_job = len(self.job_list)

        # Update free information
        if user_name is None:
            self.num_free_cpu = max(0, self.num_cpu - self.num_job)
            self.free_ram = self._get_free_ram()
            self.free_vram = self._get_free_vram()


if __name__ == "__main__":
    print("This is moudle Machine from SPG")
