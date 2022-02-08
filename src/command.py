from shlex import split
from pathlib import Path

from .default import Default

####################################### ssh command #######################################
def ssh_to_machine(machineName: str) -> list[str]:
    """ SSH to input machine """
    return split(
        "ssh -T "                       # Disable pseudo-tty allocation: Do not need terminal
        "-o StrictHostKeyChecking=no "  # SSH without checking host key(fingerprint) at known_hosts
        "-o ConnectTimeout=4 "          # Timeout in seconds for connecting ssh
        "-o UpdateHostKeys=no "         # Do not update know_hosts if it already exists
        f"{machineName}"                # Target machine to ssh
    )

################################ ps & free memory commands ################################
def ps_from_user(user_name: str | None) -> list[str]:
    """
    ps command to find job information w.r.t input user
    --format: format to be printed
                ruser:15 - real user name maximum length of 15
                stat - current state of proccess. ex) R, S, ...
                pid - process ID
                sid - process ID of session leader
                pcpu - cpu utilization (unit of percent)
                pmem - memory utilization (unit of percent)
                rss:10 - memory utilization (unit of kilobytes), maximum length of 10
                etime:15 - cumulative CPU time in '[DD-]HH:MM:SS' format, maximum length of 15
                stime - starting time or date
                args - command with all its arguments as a string
    """
    if user_name is None:
        # When user name is none, take all users registered in SPG
        user_name = ",".join(Default.USER["kahng"] + Default.USER["baek"])
    return split(
        "ps H "                 # Show threads as if they were processes
        "--no-headers "         # Do not print header
        f"--user {user_name} "  # Only select effective user ID.
        "--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,etime:15,stime,args"
    )

def ps_from_pid(pid: str) -> list[str]:
    """ Same as ps_from_user but specified by pid """
    return split(
        "ps H "             # Show threads as if they were processes
        "--no-headers "     # Do not print header
        f"-q {pid} "        # Only select job with input pid
        "--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args"
    )

def pid_to_ppid(pid: str) -> list[str]:
    """ ps command to find ppid(parent pid) of input process """
    return split(
        "ps --no-headers "  # Do not print header
        f"-q {pid} "        # Search by pid
        "--format ppid"     # Only return paraent pid
    )

def free_ram() -> list[str]:
    """ free command to get free ram """
    return split(
        "free -h "      # Show output fieds in human-readable unit
        "--si "         # Use unit of kilo, mega, giga byte instead of kibi, mebi, gibi byte
    )

################################### nvidia-smi commands ###################################
def ns_process() -> list[str]:
    """ nvidia-smi command to get process running at gpu """
    return split(
        "nvidia-smi pmon "  # nvidia-smi process monitor mode
        "--count 1 "        # Only sample single result
        "--select um "      # Monitor both utilization and memory usage
        "--delay 10 "       # Collect within 10 seconds interval
    )

def free_vram() -> list[str]:
    """ nvidia-smi command to get free vram """
    return split(
        "nvidia-smi "
        "--query-gpu=memory.free "      # Query related to gpu: free vram in MiB
        "--format=csv,noheader,nounits" # Print format: csv format without header/unit(MiB)
    )

################################### run & kill commands ###################################
def run_at_cwd(command: str) -> list[str]:
    """ Run input command at current path """
    return split(
        f"cd {Path.cwd()}; "    # Change pwd to current directory
        f"{command}"            # run command
    )

def kill_pid(pid: str) -> list[str]:
    """ Kill process with input pid """
    return split(
        f"kill -15 {pid} "      # Safe kill
        # f"kill -9 {pid} "      # Force kill
        "2> /dev/null;"         # Ignore stderr of killing
    )


if __name__ == "__main__":
    print("This is module Commands from SPG")
