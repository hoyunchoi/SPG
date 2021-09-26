from typing import Optional

from default import default

class Command:
    """
        Store commands
        Every methods are static
    """
    @staticmethod
    def get_ssh_cmd(machineName: str) -> str:
        """
            StrictHostKeyChecking: ssh without checking host key(fingerprint) at known_hosts
            ConnectTimeout: Timeout in seconds for connecting ssh
            UpdateHostKeys=no: Do not update know_hosts if it already exists
        """
        return f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=4 {machineName} -o UpdateHostKeys=no'

    @staticmethod
    def get_ps_cmd(userName: Optional[str]) -> str:
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
                      time:15 - cumulative CPU time in "[DD-]HH:MM:SS" format, maximum length of 15
                      start_time - starting time or date
                      args - command with all its arguments as a string
        """
        # When user name is none, get every process belongs to user registered in group 'users'
        if userName is None:
            userName = '$(getent group users | cut -d: -f4)'
        return (f'ps H --user {userName} --no-headers '
                '--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args')

    @staticmethod
    def get_ps_from_pid_cmd(pid: str) -> str:
        """
            Same as get_ps_cmd but specified by pid
        """
        return (f'ps H - q {pid} - -no - headers '
                '--format ruser: 15, stat, pid, sid, pcpu, pmem, rss: 10, time: 15, start_time, args')

    @staticmethod
    def get_ppid_cmd(pid: str) -> str:
        """
            Return ppid of input pid
            -q: search by pid
            --format ppid: parent pid
        """
        return f'ps -q {pid} --no-headers --format ppid'

    @staticmethod
    def get_free_ram_cmd() -> str:
        """
            -h: Show output fieds in human-readable unit
            --si: Use unit of kilo, mega, giga byte instead of kibi, mebi, gibi byte
            awk: Only print available memory
        """
        return 'free -h --si | awk \'(NR==2){print \$7}\''

    @staticmethod
    def get_free_vram_cmd() -> str:
        """
            --query-gpu: Show information related to gpu
                        memory.free - free vram in MiB unit
            --format: Format of print
                        csv - csv format
                        noheader - don't print header
                        nounits - don't print unit(MiB)
        """
        return 'nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits'

    @staticmethod
    def get_run_cmd(command: str) -> str:
        """
            Return run command at input path
        """
        return f'cd {default.path}; {command}'

    @staticmethod
    def get_kill_cmd(pid: str) -> str:
        """
            Return kill command of input pid
        """
        return f'kill -9 {pid}'

    @staticmethod
    def get_ns_process_cmd() -> str:
        """
            pmon: process monitor mode
            -c: sampling count
            -s: which information to monitor
                u - utilization
                m - memory
            Return format: gpuIdx pid gpuPercent vramPercent varmUse
        """
        return (f'nvidia-smi pmon -c 1 -s um '
                '| tail -n +3 | awk \'{print \$1,\$2,\$4,\$5,\$8}\'')


if __name__ == "__main__":
    print('This is module "Commands" from SPG')
