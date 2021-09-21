from typing import Optional

class Commands():
    """
        Store commands
    """
    @staticmethod
    def getSSHCmd(machineName: str) -> str:
        """
            StrictHostKeyChecking: ssh without checking host key(fingerprint) at known_hosts
            ConnectTimeout: Timeout in seconds for connecting ssh
            UpdateHostKeys=no: Do not update know_hosts if it already exists
        """
        return f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=4 {machineName} -o UpdateHostKeys=no'

    @staticmethod
    def getPSCmd(userName: Optional[str]) -> str:
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
        return  f'ps H --no-headers --user {userName} \
                   --format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args'

    @staticmethod
    def getPPIDCmd(pid: str) -> str:
        """
            Return ppid of input pid
            -q: search by pid
            --format ppid: parent pid
        """
        return f'ps -q {pid} --format ppid'

    @staticmethod
    def getFreeMemCmd() -> str:
        """
            -h: Show output fieds in human-readable unit
            --si: Use unit of kilo, mega, giga byte instead of kibi, mebi, gibi byte
            awk: Only print available memory
        """
        return 'free -h --si | awk \'(NR==2){print \$7}\''

    @staticmethod
    def getRunCmd(path:str, command:str) -> str:
        """
            Return run command at input path
        """
        return f'cd {path}; {command}'

    @staticmethod
    def getKillCmd(pid: str) -> str:
        """
            Return kill command of input pid
        """
        return f'kill -9 {pid}'

    @staticmethod
    def getNSProcessCmd(gpuIdx: int):
        """
            pmon: process monitor mode
            -i: index of gpu
            -c: sampling count
            -s: which information to monitor
                u - utilization
                m - memory
            tail/awk: Only return pid/gpu utilization(percent)/gpu memory(in MB)
        """
        return f'nvidia-smi pmon -i {gpuIdx} -c 1 -s um ' + '| tail -n +3 | awk \'{print \$2,\$4,\$8}\''

if __name__ == "__main__":
    print(Commands.getNSProcessCmd(1))
