from shlex import split
from pathlib import Path
from typing import Optional


class Command:
    """ Commands should be passed to subprocess module """
    @staticmethod
    def ssh_to_machine(machineName: str) -> list[str]:
        """
            StrictHostKeyChecking: ssh without checking host key(fingerprint) at known_hosts
            ConnectTimeout: Timeout in seconds for connecting ssh
            UpdateHostKeys=no: Do not update know_hosts if it already exists
        """
        return split("ssh -T "
                     "-o StrictHostKeyChecking=no "
                     "-o ConnectTimeout=4 "
                     "-o UpdateHostKeys=no "
                     f"{machineName}")

    @staticmethod
    def ps_from_user(user_name: Optional[str]) -> list[str]:
        """
            H: Show threads as if they were processes
            --no-headers: Do not print header
            --user: Only select effective user ID.
            --format: format to be printed
                      ruser:15 - real user name maximum length of 15
                      stat - current state of proccess. ex) R, S, ...
                      pid - process ID
                      sid - process ID of session leader
                      pcpu - cpu utilization (unit of percent)
                      pmem - memory utilization (unit of percent)
                      rss:10 - memory utilization (unit of kilobytes), maximum length of 10
                      time:15 - cumulative CPU time in '[DD-]HH:MM:SS' format, maximum length of 15
                      start_time - starting time or date
                      args - command with all its arguments as a string
        """
        # When user name is none, get every process belongs to user registered in group 'users'
        if user_name is None:
            user_name = "$(getent group users | cut -d: -f4)"
        return split("ps H --no-headers "
                     f"--user {user_name} "
                     "--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args")

    @staticmethod
    def pid_to_ppid(pid: str) -> list[str]:
        """
            Return ppid of input pid
            -q: search by pid
            --format ppid: parent pid
        """
        return split("ps --no-headers "
                     f"-q {pid} "
                     "--format ppid")

    @staticmethod
    def free_ram() -> list[str]:
        """
            -h: Show output fieds in human-readable unit
            --si: Use unit of kilo, mega, giga byte instead of kibi, mebi, gibi byte
            awk: Only print available memory
        """
        return split(r"free -h --si | awk \'(NR==2){print $7}\'")

    @staticmethod
    def free_vram() -> list[str]:
        """
            --query-gpu: Show information related to gpu
                        memory.free - free vram in MiB unit
            --format: Format of print
                        csv - csv format
                        noheader - don't print header
                        nounits - don't print unit(MiB)
        """
        return split("nvidia-smi "
                     "--query-gpu=memory.free "
                     "--format=csv,noheader,nounits")

    @staticmethod
    def run_at_cwd(command: str) -> list[str]:
        """
            Return run command at input path
        """
        return split(f"cd {Path.cwd()}; {command}")

    @staticmethod
    def kill_pid(pid: str) -> list[str]:
        """
            Return kill command of input pid
            stderr of the kill command will be ignored
        """
        return split(f"kill -9 {pid} 2> /dev/null;")

    @staticmethod
    def ns_process() -> list[str]:
        """
            pmon: process monitor mode
            -c: sampling count
            -s: which information to monitor
                u - utilization
                m - memory
            Return format: gpuIdx pid gpuPercent vramPercent varmUse
        """
        return split("nvidia-smi pmon "
                     "-c 1 "
                     "-s um "
                     "| tail -n +3 "      # First two rows are column name
                     r"| awk \'{print $1,$2,$4,$5,$8}\'")

    @staticmethod
    def ps_from_pid(pid: str) -> list[str]:
        """
            Same as ps_from_user but specified by pid
        """
        return split("ps H --no-headers "
                     f"-q {pid} "
                     "--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args")


if __name__ == "__main__":
    print("This is module Commands from SPG")
