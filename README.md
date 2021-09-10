# SPG
#### Statistical Physics Group
This is job schedular for statistical physics group server at Department of Physics and Astronomy, Seoul National University, Korea

## Requirements
- python3.9+
- tqdm
- termcolor
- colorama

## How to use
#### General usage
`$ spg -h`
```
usage: spg (-h) (-s) {option} (args)

Statistical Physics Group

optional arguments:
  -h, --help         show this help message and exit
  -s, --silent       when given, run spg without progress bar

SPG options:
  For more information of each {option},
  type 'spg {option} -h' or 'spg {option} --help'

  Available options
    list             Print information of machines registered in SPG
    free             Print free informations of available machines
    job              print current status of jobs
    user             Print job count of users per machine group
    run              Run a job
    runs             Run several jobs
    KILL             kill job
    machine          Deprecated
    all              Deprecated
    me               Deprecated
    kill             Deprecated
    killall          Deprecated
    killmachine      Deprecated
    killthis         Deprecated
    killbefore       Deprecated
```

#### spg list
`$ spg list -h`
```
usage: spg machine (-g group list) (-m machine list)
When group/machine are both given, group is ignored
When machine is specified, there is no group summary

optional arguments:
  -h, --help            show this help message and exit
  -g  [ ...], --groupList  [ ...]
                        List of target machine group name, seperated by space
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machineList  [ ...]
                        List of target machine name, seperated by space
                        ex) tenet1 / tenet1 tenet2
```

#### spg free
`$ spg free -h`
```
usage: spg free (-g group list) (-m machine list)
When group/machine are both given, group is ignored
When machine is specified, there is no group summary

optional arguments:
  -h, --help            show this help message and exit
  -g  [ ...], --groupList  [ ...]
                        List of target machine group name, seperated by space
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machineList  [ ...]
                        List of target machine name, seperated by space
                        ex) tenet1 / tenet1 tenet2
```
#### spg job
`$ spg job -h`
```
usage: spg job (-a) (-g group list) (-m machine list) (-u user name)
When group/machine are both given, group is ignored
When all flag is set, user if ignored

optional arguments:
  -h, --help            show this help message and exit
  -g  [ ...], --groupList  [ ...]
                        List of target machine group name, seperated by space
                        Currently available: ['tenet', 'xenet', 'kuda']
  -m  [ ...], --machineList  [ ...]
                        List of target machine name, seperated by space
                        ex) tenet1 / tenet1 tenet2
  -a, --all             When given, print jobs of all users
  -u , --userName       Target user name. Default: me
```

#### spg user
`$ spg user -h`
```
usage: spg free (-g group list)

optional arguments:
  -h, --help            show this help message and exit
  -g  [ ...], --groupList  [ ...]
                        List of target machine group name, seperated by space
                        Currently available: ['tenet', 'xenet', 'kuda']
```

#### spg run
`$ spg run -h`
```
usage: spg run [machine name] [program] (arguments)

CAUTION!
1. Invoke the job in the directory where you want the prrun
2. Don't append '&' character at the tail of commands.
   spg will do it for you
3. If you want to use redirection symbols < or >,
   type them in a quote, such as '<' or '>'

positional arguments:
  machineName  target machine name
  command      command you want to run. [program] (arguments)

optional arguments:
  -h, --help   show this help message and exit
```
#### spg runs
`$ spg runs -h`
```
usage: spg runs [command file] [group name] (start end)

CAUTION!
1. Invoke the job in the directory where you want the prrun
2. Don't append '&' character at the tail of commands.
   spg will do it for you
3. If you want to use redirection symbols < or >,
   type them in a quote, such as '<' or '>'
4. You can assign maximum of 50 jobs at one time.
5. Executed commands will be dropped from input command file

positional arguments:
  cmdFile     Files containing commands. Sepearated by lines.
  groupName   Target machine group name with optinal start, end number
              When start and end number is given, only use machines between them
              ex) tenet 100 150: search tenet100~tenet150

optional arguments:
  -h, --help  show this help message and exit
```
#### spg KILL
`$ spg KILL -h`
```
usage: spg kill (-m machine list) (-g group list) (-u user name) (-p pidList) (-c command) (-t time)
CAUTION!!
1. Jobs to be killed should satisfy all the given options.
2. When given a multi-threaded job, this command kills it's session leader.
3. When group/machine are both given, group is ignored.

optional arguments:
  -h, --help            show this help message and exit
  -u , --userName       Target user name
                        If you are not root, you can only specify yourself (default)
  -m  [ ...], --machineList  [ ...]
                        List of target machine name, seperated by space
                        ex) tenet1 / tenet1 tenet2
  -g  [ ...], --groupList  [ ...]
                        List of target machine group name, seperated by space
                        Currently available: ['tenet', 'xenet', 'kuda']
  -p  [ ...], --pidList  [ ...]
                        Kill my jobs with specific pid.
                        When this option is given, you should specifiy single machine name.
                        List of pid of target job, seperated by space.
  -c  [ ...], --command  [ ...]
                        Kill my jobs whose commands includes pattern.
                        List of words to search. Target command should have exact pattern.
  -t  [ ...], --time  [ ...]
                        Kill my jobs started less than given time.
                        Time interval seperated by space.
                        ex) 1w 5d 11h 50m 1s
```

## Structure
#### Common
Define user and corresponding spg machines
Administrator of SPG should update the machine/user info

#### Arguments
Argument class
Get options of spg and their help documents

#### Job
Job Class: Store information of job

#### Machine
Machine Class: Store information of machine and running jobs

#### MachineGroup
MachineGroup Class: Store information of machine group: list of machines with same prefix

#### SPG
SPG Class: Run spg commands and print


