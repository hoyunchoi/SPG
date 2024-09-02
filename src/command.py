from pathlib import Path

from .default import DEFAULT


####################################### ssh command #######################################
def ssh_to_machine(machine_name: str) -> str:
    """SSH to input machine"""
    return (
        "ssh -T "  # Disable pseudo-tty allocation: Do not need terminal
        "-o StrictHostKeyChecking=no "  # SSH without checking host key(fingerprint) at known_hosts
        "-o ConnectTimeout=4 "  # Timeout in seconds for connecting ssh
        "-o UpdateHostKeys=no "  # Do not update know_hosts if it already exists
        f"{machine_name}"  # Target machine to ssh
    )


################################ ps & free memory commands ################################
def ps_from_user(user_name: str) -> str:
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
    if user_name == "":
        # When user name is none, take all users registered in SPG except root
        user_name = ",".join(DEFAULT.USERS[1:])
    return (
        "ps H "  # Show threads as if they were processes
        "--no-headers "  # Do not print header
        f"--user {user_name} "  # Only select effective user ID.
        "--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,etime:15,stime,args"
    )


def ps_from_pid(pid: int) -> str:
    """Same as ps_from_user but specified by pid"""
    return (
        "ps H "  # Show threads as if they were processes
        "--no-headers "  # Do not print header
        f"-q {pid} "  # Only select job with input pid
        "--format ruser:15,stat,pid,sid,pcpu,pmem,rss:10,time:15,start_time,args"
    )


def pid_to_ppid(pid: int) -> str:
    """ps command to find ppid(parent pid) of input process"""
    return (
        "ps --no-headers "  # Do not print header
        f"-q {pid} "  # Search by pid
        "--format ppid"  # Only return paraent pid
    )


def free_ram() -> str:
    """free command to get free ram"""
    return (
        "free --bytes "  # Show memory in unit of byte
        "| grep Mem "  # Grep only a line of memory values
        "| awk '{print $NF}'"  # return last value: available memory in bytes
    )


################################### nvidia-smi commands ###################################
def ns_process() -> str:
    """nvidia-smi command to get process running at gpu"""
    return (
        "nvidia-smi pmon "  # nvidia-smi process monitor mode
        "--count 1 "  # Only sample single result
        "--select um "  # Monitor both utilization and memory usage
        "--delay 10 "  # Collect within 10 seconds interval
        "| tail -n +3"  # Omit first two lines: column names
    )


def free_vram() -> str:
    """nvidia-smi command to get free vram"""
    return (
        "nvidia-smi "
        "--query-gpu=memory.free "  # Query related to gpu: free vram in MiB
        "--format=csv,noheader"  # Print format: csv format without header
    )


################################### run & kill commands ###################################
def run_at_cwd(command: str) -> str:
    """Run input command at current path"""
    return (
        f"cd {Path.cwd()}; "  # Change pwd to current directory
        f"{command}"  # run command
    )


def kill_pid(pid: int) -> str:
    """Kill process with input pid"""
    return (
        f"kill -15 {pid} "  # Safe kill
        # f"kill -9 {pid} "      # Force kill
        "2> /dev/null;"  # Ignore stderr of killing
    )
