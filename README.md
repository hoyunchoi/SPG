# SPG: Statistical Physics Group
#### This is the job schedular for the statistical physics group at the Department of Physics and Astronomy, Seoul National University, Korea.

SPG can monitor/run/kill processes on registered remote SSH servers.

*WARNING: Scanning the whole server is quite network-intensive. Do not run `spg` several times in a short time.*

## Requirements
- Shell environment
  - `ssh`[^ssh]
  - `ps`[^ps]
  - `free`[^free]
  - `kill`[^kill]
  - `nvidia-smi`[^nvidia-smi](gpu server only)
- Python
  - version 3.10 or higher
  - tqdm
  - colorama

# How does SPG works
## Server hierarchy and registering server
Servers registered in SPG are called **machine**. It belongs to a single **group**, which is a set of similar machines. The name of the machine should be (group name) + (machine id). Currently, there are three groups.

- tenet: Machines with consumer-grade CPUs. Mainly used for CPU-based simulations.
- xenet: Machines with server-grade CPUs. Mainly used for jobs that require a lot of memory (100+GB)
- kuda: Machines with GPU. Mainly used for GPU computation such as deep learning.

Each group has its corresponding JSON file which contains the information of every machine that belongs to the group. To register the server at SPG, you should append the following information to the matching group file.
```
example.json
________________________________________________________________________________________________________
{
    "example1": {
        "use": "True",          // True if the machine is available, False if not
        "name": "kuda1",        // Name of the machine
        "cpu": "E5-2680v4x2",   // CPU model name
        "num_cpu": "28",        // Number of cpu cores
        "ram": "128G",          // Size of system memory installed
        "gpu": "GTX-1080",      // GPU model name (gpu server only)
        "num_gpu": "4",         // Number of gpu installed (gpu server only)
        "vram": "8G",           // Size of vram of single gpu (gpu server only)
        "comment": ""           // When status of machine is changed, log the history. Not used in SPG.
    },
}
```
Temporarily, three group files are separated by user group: administrator/baek/kahng. They will be merged into a single file in a short time. The list of users, group name, and path of JSON files can be configured at `src/default.py`.

### Monitor/Run/Kill processes
SPG uses the `subprocess` module on python to execute commands for monitoring, running, killing processes. Detailed commands executed can be found in `src/command.py`.

#### Monitoring process
To monitor processes running in a machine, `ps` is used. Since `ps` only monitors resources related to processes, available system memory is monitored using `free`. In the case of GPU-server, `nvidia-smi` is also used. Due to the limitation of `nvidia-smi`, only 4 GPUs can be monitored. When a single machine has more than 4 GPUs, this should be updated.

#### Running process
A command is executed at a certain machine via `ssh`. Be aware that the path where the command is executed at the SSH server is the same as the path where `spg` is called. For detailed information, see [run](#spg-run) option.

#### Killing process
Killing a process at a certain machine via `ssh` uses `kill -15`, or `SIGTERM`. This command safely kills a process with PID(Process ID). `spg` finds the PID of jobs satisfying some conditions given by the user. For detailed conditions, see [KILL](#spg-kill) option.

# How to use
## General usage
You can specify which group/machine to monitor/run/kill process via `-g group` or `-m machine` arguments.
`$ spg -h`
```
usage: spg (-h) (-s) [option] ...

Statistical Physics Group

options:
  -h, --help         show this help message and exit
  -s, --silent       when given, run spg without progress bar.

SPG options:
  Arguments inside square brackets [] are required arguments while parentheses () are optional.
  For more information of each [option], type 'spg [option] -h' or 'spg [option] --help'.

  Available Options
    list             Print information of machines registered in SPG.
    free             Print free information of available machines.
    job              print current status of jobs.
    user             Print job count of users per machine group.
    run              Run a job.
    runs             Run several jobs.
    KILL             Kill jobs satisfying conditions.
    machine          Deprecated
    all              Deprecated
    me               Deprecated
    kill             Deprecated
    killall          Deprecated
    killmachine      Deprecated
    killthis         Deprecated
    killbefore       Deprecated
```

## spg list
Print the list of all machines and group information. The information includes `machine name`, `compute unit (CPU or GPU) name`, `number of computing units`, `physical memory` per each machine. Group summary includes the total number of machines and the number of computing units of each group.

*When the CPU in which the hybrid architecture is implemented (for example, Intel Alder-lake) is introduced into the server, `compute unit` should be separated by `number of cores` and `number of threads`.*

`$ spg list -h`
```
usage: spg list (-g groups) (-m machines)
When group/machine are both given, the group is ignored.

options:
  -h, --help            show this help message and exit
  -g  [ ...], --group  [ ...]
                        List of target machine group names, separated by space.
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machine  [ ...]
                        List of target machine names, separated by space.
                        ex) tenet1 / tenet1 tenet2
```

## spg free
Print the list of free machines and group information. Free is defined by (number of installed units) - (number of running jobs). The free memory is the result of `free` command.

`$ spg free -h`
```
usage: spg free (-g groups) (-m machines)
When group/machine are both given, the group is ignored.

options:
  -h, --help            show this help message and exit
  -g  [ ...], --group  [ ...]
                        List of target machine group names, separated by space.
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machine  [ ...]
                        List of target machine names, separated by space.
                        ex) tenet1 / tenet1 tenet2
```
## spg job
Print the list of jobs responsible for a certain user. By default, the user is the one who is running the command. Job information is as follows. You can specify which job to scan by various arguments. For detailed arguments, see [KILL](#spg-kill) option.
- machine: Name of machine this job is running at
- user: Name of the user who this job belongs to
- ST: State of the job. Running(R), Sleep(S),... For detailed information, refer `ps` command.
- PID: Process ID of the job.
- CPU(%): CPU utilization in percentage. The CPU time used is divided by the time the process has been running.
- MEM(%): Memory utilization in percentage. The ratio of the process's resident set the size to the physical memory.
- Memory: Memory utilization in kilo/mega/giga byte unit.
- Time: Elapsed time since the process was started, [[DD-]hh:]mm:ss format.
- Start: Time when process was started.
- Command: Command with all its arguments.

`$ spg job -h`
```
usage: spg job (-g groups) (-m machines) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
Listed jobs will satisfy all the given options.
When group/machine are both given, the group is ignored.
When -a, --all flag is set, --user option is ignored.

options:
  -h, --help            show this help message and exit
  -m  [ ...], --machine  [ ...]
                        List of target machine names, separated by space.
                        ex) tenet1 / tenet1 tenet2
  -g  [ ...], --group  [ ...]
                        List of target machine group names, separated by space.
                        Currently available: ['tenet', 'xenet', 'kuda']
  -u , --user           Target user name.
  -a, --all             When given, print jobs of all users.
  -p  [ ...], --pid  [ ...]
                        Jobs with specific PID.
                        When this option is given, you should specify a single machine name.
                        List of pid of target job, separated by space.
  -c  [ ...], --command  [ ...]
                        Jobs whose commands include pattern.
                        List of words to search. The target command should have the exact pattern.
  -t  [ ...], --time  [ ...]
                        Jobs running less than the given time.
                        Time interval separated by space.
                        ex) 1w 5d 11h 50m 1s
  -s , --start          Jobs started at a specific time.
                        The start time should exactly match.
```

## spg user
Print number of running jobs at machine groups, per user. Similar to `spg job -a` without the detailed job information.

`$ spg user -h`
```
usage: spg user (-g groups) (-m machines)
When group/machine are both given, the group is ignored.

options:
  -h, --help            show this help message and exit
  -g  [ ...], --group  [ ...]
                        List of target machine group names, separated by space.
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machine  [ ...]
                        List of target machine names, separated by space.
                        ex) tenet1 / tenet1 tenet2
```

## spg run
Run a single job at a given machine. When using a relative path, be careful that the command will be run at the current path, where `spg` is executed. If the program need `-` or `--` arguments or redirection symbol `>` or `<`, you need to wrap the entire command with a quote. Also, the background symbol `&` is not required since `spg` will do it for you.

*The history of `spg run` is logged into the `spg.log` file.*

* Valid Examples
  - `spg run tenet1 ./example_wo_arguments.out`
  - `spg run tenet1 ./example.out 1000 0.1`
  - `spg run tenet1 "./example_redirect.out > example.txt"`
  - `spg run tenet1 /my/conda/env/python/path example_wo_arguments.py`
  - `spg run tenet1 "/my/conda/env/python/path example.py --N=1000 --a=0.1"`

* Invalid Examples
  - `spg run tenet1 ./redundant_background.out &`
  - `spg run tenet1 /redirect_not_wrapped.out > example.txt`
  - `spg run tenet1 /my/conda/env/python/path "python_not_wrapped.py --N=1000 --a=0.1"`

`$ spg run -h`
```
usage: spg run [machine] [program] (arguments)

CAUTION!
1. Invoke the job in the directory where you want the program to run.
2. If your program uses -, -- arguments or redirection symbols < or >,
    wrap the program and arguments with a quote: ' or ".

positional arguments:
  machine     target machine name.
  command     command you want to run: [program] (arguments)

options:
  -h, --help  show this help message and exit
```

## spg runs
Run several jobs at free machines automatically. The commands per each job should be stored in a single file. You should specify the machine group and optionally, the range of machine index. A maximum of 50 jobs can be run and the executed commands will be dropped from the command file.

*The history of `spg runs` is logged into the `spg.log` file.*

ex1) `spg runs example.txt tenet`: run all codes at `example.txt` on free machines in group tenet.\
ex2) `spg runs example.txt tenet 1 10`: run all codes at `example.txt` on free machines tenet1 ~ tenet10.
```
example.txt
________________________________________________________________________________________________________
# comment type 1
./example.out

// comment type 2
./example.out 1000 0.1

% comment type 3
./example_redirect.out > example.txt

/my/conda/env/python/path example_wo_arguments.py

/my/conda/env/python/path example.py --N=1000 --a=0.1
```

`$ spg runs -h`
```
usage: spg runs [command file] [group] (start end)

CAUTION!
1. Invoke the job in the directory where you want the program to run.
2. You can assign a maximum of 50 jobs at one time.
3. Executed commands will be erased from the input command file.

positional arguments:
  command     Files containing commands. Separated by lines.
  group       Target machine group name with and optional start, end number.
              When the start and end number is given, only use machines between them.
              ex1) tenet: search every available tenet machines
              ex2) tenet 100 150: search tenet100 ~ tenet150

options:
  -h, --help  show this help message and exit
```

## spg KILL
Kill target users' jobs satisfying conditions. It also kills the parent process, which belongs to the target user.
- user: Target user, who is registered at SPG. When specifying another user than yourself, you should be a root.
- all: When this flag is on, kill every user's job. You should be a root.
- pid: List of PID for a specific job. If this option is given, you also have to specify a single machine.
- command: String of commands. The target job should include the input command as a substring.
- time: A job executed for a shorter time than the input time interval.
- start: Specific time when the job started. Should exactly match with the result of `spg job`

*The history of `spg KILL` is logged into the `spg.log` file.*

`$ spg KILL -h`
```
usage: spg KILL (-g groups) (-m machines) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
When group/machine are both given, the group is ignored.

CAUTION!!
1. Jobs to be killed should satisfy all the given options.
2. When PID is given, only a single machine should be specified.
3. When given a multi-process job, this command kills its session leader.

options:
  -h, --help            show this help message and exit
  -g  [ ...], --group  [ ...]
                        List of target machine group names, separated by space.
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machine  [ ...]
                        List of target machine names, separated by space.
                        ex) tenet1 / tenet1 tenet2
  -u , --user           Target user name.
  -a, --all             When given, print jobs of all users.
  -p  [ ...], --pid  [ ...]
                        Jobs with specific PID.
                        When this option is given, you should specify a single machine name.
                        List of pid of target job, separated by space.
  -c  [ ...], --command  [ ...]
                        Jobs whose commands include pattern.
                        List of words to search. The target command should have the exact pattern.
  -t  [ ...], --time  [ ...]
                        Jobs running less than the given time.
                        Time interval separated by space.
                        ex) 1w 5d 11h 50m 1s
  -s , --start          Jobs started at a specific time.
                        The start time should exactly match.
```

# Code
### main
The main script with shebang of default global python: /usr/bin/python

### Group Files
The group files are separated by user group. Users at a user group can only access machines registered at the group files.

### singleton
Metaclass for singleton pattern. This is sub-optimal but used until finding a good alternative.

### default
Store basic information of SPG. The user group and the root directory are specified here. You can register/remove user and group files here. Furthermore, get the information of the user who is running the `spg` command.

### argument
Generate arguments and validate the user input. When something is wrong during validation, print the error message and exit the program. All options are stored into a single dataclass object: Argument

### option
Enum class of SPG options.

### spg
Do operation based on input arguments.

### group
Store group information. Initialized by reading a group file and it handles operation on machines belonging to the group. Also, `spg runs` is executed here.

### machine
Store machine information. Initialized by a single element at a group file. Handles operation on a single machine: scanning/running/killing processes.

### job
Store job information. Initialized by a result of `ps` or `nvidia-smi` commands. Handles operation on a single job: find matching jobs.

### command
Store all commands running at shell environment. Every command includes detailed comments.

### output
Handles all outputs of SPG. This includes the following.
- ProgressBar: progress bar used when scanning machines. Uses `tqdm` package
- Printer: Responsible for plain outputs and progress bar
- MessageHandler: Responsible for colored outputs such as success, warning, error
- logger: log the run/kill history. Uses rotating file handler with a size of 100MB

### utils
Some string-related operations.

[^ssh]: https://man7.org/linux/man-pages/man1/ssh.1.html
[^ps]: https://man7.org/linux/man-pages/man1/ps.1.html
[^free]: https://man7.org/linux/man-pages/man1/free.1.html
[^nvidia-smi]: https://developer.download.nvidia.com/compute/DCGM/docs/nvidia-smi-367.38.pdf
[^kill]: https://man7.org/linux/man-pages/man1/kill.1p.html