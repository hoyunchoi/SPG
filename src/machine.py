import subprocess
from collections import Counter, abc
from functools import cache
from shlex import split

from . import command as Command
from .default import DEFAULT
from .job import CPUJob, GPUJob, Job, JobCondition
from .ram import Ram
from .spgio import LOGGER, MESSAGE_HANDLER, Printer


class Machine:
    __slots__ = [
        "name",
        "cpu",
        "num_cpu",
        "ram",
        "comment",
        "jobs",
        "pid_tree",
        "error",
    ]

    def __init__(
        self, name: str, cpu: str, num_cpu: str, ram: str, comment: str
    ) -> None:
        # Machine spec
        self.name = name  # Name of machine. ex) tenet1
        self.cpu = cpu  # Name of cpu
        self.num_cpu = int(num_cpu)  # Number of cpu cores
        self.ram = Ram.from_string(f"{ram}B")  # Size of RAM
        self.comment = comment  # comment of machine. Not used

        # Current job/free information
        self.error: bool = False  # If error occurs during scanning, set True
        self.jobs: list[Job] = []  # List of running jobs
        self.pid_tree: dict[int, set[int]] = {}  # pid of running jobs with parents

    ####################### Basic informations, regardless of scanning #######################
    @property
    @cache
    def num_core(self) -> int:
        """Number of compute units inside machine"""
        return self.num_cpu

    @property
    @cache
    def log_info(self) -> dict[str, str]:
        """# Information to be logged"""
        return {"machine": self.name, "user": DEFAULT.user}

    @property
    @cache
    def command_ssh(self) -> str:
        """Command to ssh to machine"""
        return Command.ssh_to_machine(self.name)

    ##################### Busy, free informations, valid after scanning #####################
    @property
    def num_job(self) -> int:
        """Number of running jobs at machine"""
        return len(self.jobs)

    @property
    def num_free_cpu(self) -> int:
        """Number of free cpu cores"""
        if self.error:
            return 0
        return max(0, self.num_cpu - self.num_job)

    @property
    def num_available(self) -> int:
        """Number of available(free) compute units inside machine"""
        return self.num_free_cpu

    @property
    def free_ram(self) -> Ram:
        """Absolute value of free RAM"""
        free_ram = subprocess.check_output(
            split(f'{self.command_ssh} "{Command.free_ram()}"'), text=True
        )  # free ram in unit of "Byte"
        return Ram.from_string(f"{free_ram.strip()}B")

    ######################### kill informations, valid after killing #########################
    @property
    def num_kill(self) -> int:
        """Number of killed jobs"""
        return len(self.pid_tree[0])

    ########################## Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
        Return machine information according to format spec
        - info: machine information
        - free: machine free information
        - otherwise: machine name
        """
        if format_spec.lower() == "info":
            return Printer.machine_info_format.format(
                self.name, self.cpu, self.num_cpu, "core", f"{self.ram}"
            )

        elif format_spec.lower() == "free":
            return Printer.machine_free_info_format.format(
                self.name,
                self.cpu,
                self.num_free_cpu,
                "core",
                f"{self.free_ram} free",
            )
        else:
            return self.name

    ###################################### Basic Utility ######################################
    def _get_command_from_pid(self, pid: int) -> str:
        """Find command of job having input pid"""
        # Find list of command sharing same pid
        commands = [job.command for job in self.jobs if job.pid == pid]

        # Job with input pid is not registered or multiple jobs are registered
        if len(commands) != 1:
            MESSAGE_HANDLER.error(
                f"ERROR: Problem at identifying process in {self.name}: {pid=}"
            )
            exit()

        return commands[0]

    def _stack_pid_tree(self, depth: int, pid: int) -> None:
        """
        Store pid into specific depth of pid tree
        depth=0: leaf process
        depth=1: parent of leaf processes (depth=0)
        depth=2: parent of depth=1 processes
        """
        if depth in self.pid_tree:
            self.pid_tree[depth].add(pid)
        else:
            self.pid_tree[depth] = {pid}

    def _track_pid_tree(self, pid: int, sid: int) -> None:
        """Track pid tree from leaf(pid) to root(sid)"""
        depth = 0
        self._stack_pid_tree(depth, pid)
        while pid != sid:
            # Find ppid(parent pid) of input pid
            ppid = subprocess.check_output(
                split(f"{self.command_ssh} '{Command.pid_to_ppid(pid)}'"), text=True
            ).strip()

            # Increase depth and update pid to it's ppid
            depth, pid = depth + 1, int(ppid)
            self._stack_pid_tree(depth, pid)

    ########################### Get Information of Machine Instance ###########################
    def _get_process_infos(self, command_process: str) -> list[str]:
        """
        Get list of processes\n
        When error occurs during SSH, raise RuntimeError
        Args
            command_process: command to find process inside ssh client
                             This could be either 'ps' or 'nvidia-smi'
        """
        result = subprocess.run(
            split(f"{self.command_ssh} '{command_process}'"),
            capture_output=True,
            text=True,
        )
        # Check scan error
        if result.stderr:
            MESSAGE_HANDLER.error(f"ERROR from {self.name}: {result.stderr.strip()}")
            raise RuntimeError

        # If there is no error return list of stdout
        return result.stdout.strip().split("\n")

    def scan(
        self,
        user_name: str = "",
        job_condition: JobCondition | None = None,
        include_parents: bool = False,
    ) -> None:
        """
        Scan machine and store running jobs
        Args
            user_name: Refer command.ps_from_user
            job_condition: Refer Job.match_condition
            include_parents: If true, store parents of running jobs until session leader
        """
        try:
            ps_infos = self._get_process_infos(Command.ps_from_user(user_name))
        except RuntimeError:
            # When error occurs, Do nothing and return since error is already reported
            self.error = True
            return

        for ps_info in ps_infos:
            # Skip empty string: no process
            if ps_info == "":
                continue

            # Create job and filter out not important
            job = CPUJob.from_info(self.name, ps_info)
            if not job.is_important or not job.match_condition(job_condition):
                continue

            # Store scanned information
            self.jobs.append(job)
            if include_parents:
                self._track_pid_tree(job.pid, job.sid)

    def get_user_count(self) -> Counter[str]:
        """Return the Counter of {user name: number of jobs}"""
        return Counter(job.user_name for job in self.jobs)

    ##################################### Run or Kill Job #####################################
    def run(self, command: str) -> None:
        """run input command at current directory"""
        # Run command on background, not waiting to finish
        subprocess.Popen(split(f"{self.command_ssh} '{Command.run_at_cwd(command)}'"))

        # Print the result and save to logger
        MESSAGE_HANDLER.success(f"SUCCESS {self.name:<10}: run '{command}'")

        # Log
        LOGGER.info(f"spg run {command}", extra=self.log_info)

    def kill(self) -> None:
        """Kill all jobs registered during scanning session"""
        # Filter machine who has nothing to kill
        if not self.pid_tree:
            return

        # stack kill command from depth=0 to higher depth
        command_kill = ""
        for pids in self.pid_tree.values():
            command_kill += " ".join(Command.kill_pid(pid) for pid in pids)

        # Run kill command inside ssh target machine
        kill_result = subprocess.run(
            split(f"{self.command_ssh} '{command_kill}'"),
            capture_output=True,
            text=True,
        )

        # When error occurs, save it
        if kill_result.stderr:
            kill_errs = kill_result.stderr.strip().split("\n")
            MESSAGE_HANDLER.error(
                "\n".join(f"ERROR from {self.name}: {err}" for err in kill_errs)
            )
            return

        # Print the result and log
        for pid in self.pid_tree[0]:
            command = self._get_command_from_pid(pid)
            MESSAGE_HANDLER.success(f"SUCCESS {self.name:<10}: kill '{command}'")
            LOGGER.info(f"spg kill {command}", extra=self.log_info)


class GPUMachine(Machine):
    __slots__ = ["gpu", "num_gpu", "vram", "free_gpus"]

    def __init__(
        self,
        name: str,
        cpu: str,
        num_cpu: str,
        ram: str,
        gpu: str,
        num_gpu: str,
        vram: str,
        comment: str,
    ) -> None:
        super().__init__(name, cpu, num_cpu, ram, comment)
        self.gpu = gpu
        self.num_gpu = int(num_gpu)
        self.vram = Ram.from_string(f"{vram}B")

        # Current state of machine
        self.free_gpus: set[int] = set()  # free gpu index

    ####################### Basic informations, regardless of scanning #######################
    @property
    @cache
    def num_core(self) -> int:
        """Number of compute units inside machine"""
        return self.num_gpu

    ##################### Busy, free informations, valid after scanning #####################
    @property
    def num_free_gpu(self) -> int:
        """Number of free gpus"""
        if self.error:
            return 0
        return len(self.free_gpus)

    @property
    def num_available(self) -> int:
        """Number of available(free) compute units inside machine"""
        return self.num_free_gpu

    @property
    def free_vram(self) -> Ram:
        """
        When one or more gpus is free, print it's total vram
        Otherwise, print largest available vram
        """
        # When one or more gpu is free
        if self.error:
            return Ram()
        if self.num_free_gpu:
            return self.vram

        # Otherwise, get list of free vram
        free_vrams = (
            subprocess.check_output(
                split(f"{self.command_ssh} '{Command.free_vram()}'"), text=True
            )
            .strip()
            .split("\n")
        )

        # Get maximum free vram
        return max(map(Ram.from_string, free_vrams))

    ########################## Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        machine_info = super().__format__(format_spec)  # Format of (CPU) Machine
        if format_spec.lower() == "info":
            machine_info += "\n" + Printer.machine_info_format.format(
                "", self.gpu, self.num_gpu, "gpus", f"{self.vram}"
            )

        elif format_spec.lower() == "free":
            machine_info += "\n" + Printer.machine_free_info_format.format(
                "", self.gpu, self.num_free_gpu, "gpus", f"{self.free_vram} free"
            )
        return machine_info

    ########################### Get Information of Machine Instance ###########################
    def _get_ps_infos_from_pid(self, pid: int) -> list[str]:
        """Find ps info of job having input pid"""
        return (
            subprocess.check_output(
                split(f"{self.command_ssh} '{Command.ps_from_pid(pid)}'"), text=True
            )
            .strip()
            .split("\n")
        )

    def scan(
        self,
        user_name: str | None,
        job_condition: JobCondition | None = None,
        include_parents: bool = True,
    ) -> None:
        """
        Scan machine and store running jobs\n
        Arguments: refer Machine.scan

        1. For every process in GPUs, check their pid

        2-1. If there is no process, mark the gpu index as free gpu index
        2-2. If there is such process, retrieve gpu utilization, vram usage, ps information by pid

        3-1. Filter ps information by user name and job conditions (it is always important)
        """

        def filter_by_user(ps_infos: abc.Iterable[str]) -> abc.Iterable[str]:
            """Return iterable of ps_info which belongs to user_name"""
            for ps_info in ps_infos:
                if user_name == "" or ps_info.strip().split()[0] == user_name:
                    yield ps_info

        # Get list of raw process: Use nvidia-smi
        try:
            ns_infos = self._get_process_infos(Command.ns_process())
        except RuntimeError:
            # When error occurs, Do nothing and return since error is already reported
            self.error = True
            return

        for ns_info in ns_infos:
            ns_info = ns_info.strip().split()

            # Index of gpu running the ns_info process
            gpu_idx = int(ns_info[0])

            # When no information is detected, nvidia-smi returns pid as "-"
            pid = int(ns_info[1].replace("-", "-1"))
            if pid == -1:
                self.free_gpus.add(gpu_idx)
                continue

            # Retrieve process informations from ns_info
            gpu_percent = float(ns_info[3].replace("-", "0"))  # For redundancy
            vram_use = Ram.from_string(f"{ns_info[9].replace("-", "0")}MB")
            vram_percent = vram_use / self.vram * 100.0
            ps_infos = self._get_ps_infos_from_pid(pid)  # Multiple ps info per pid

            for ps_info in filter_by_user(ps_infos):
                job = GPUJob.from_info(
                    machine_name=f"{self.name}-GPU{gpu_idx}",
                    ps_info=ps_info,
                    gpu_percent=gpu_percent,
                    vram_use=vram_use,
                    vram_percent=vram_percent,
                )

                if not job.match_condition(job_condition):
                    continue

                # Store scanned information
                self.jobs.append(job)
                if include_parents:
                    self._track_pid_tree(job.pid, job.sid)
                break  # One job per pid of single gpu


if __name__ == "__main__":
    print("This is moudle Machine from SPG")
