from enum import Enum

class TestItem(Enum):
    # silent
    SILENT_USER = "-s user"

    # option list
    LIST = "list"
    LIST_MACHINE = "list -m tenet1"
    LIST_MACHINES = "list -m tenet1 tenet2 kuda1"
    LIST_GROUP = "list -g kuda"
    LIST_MACHINE_GROUP = "list -g tenet -m tenet1"
    LIST_MACHINE_GROUP_SUPPRESS = "list -g xenet -m tenet1 xenet1"

    # option free
    FREE = "free"
    FREE_MACHINE = "free -m tenet1"
    FREE_MACHINES = "free -m tenet1 tenet2 kuda1"
    FREE_GROUP = "free -g kuda"
    FREE_MACHINE_GROUP = "free -g tenet -m tenet1"
    FREE_MACHINE_GROUP_SUPPRESS = "free -g xenet -m tenet1 xenet1"

    # option job
    JOB = "job"
    JOB_MACHINE = "job -m tenet1"
    JOB_MACHINES = "job -m tenet1 tenet2 kuda1"
    JOB_GROUP = "job -g kuda"
    JOB_MACHINE_GROUP = "job -g tenet -m tenet1"
    JOB_MACHINE_GROUP_SUPPRESS = "job -g xenet -m tenet1 xenet1"
    JOB_USER = "job -u root"
    JOB_USER_ERR = "job -u roo"
    JOB_ALL = "job -a"
    JOB_PID = "job -m tenet1 -p 1234 5678"
    JOB_PID_ERR = "job -m tenet1 tenet2 -p 1234"
    JOB_CMD = "job -m tenet1 -c python test.py"
    JOB_TIME = "job -m tenet1 -t 1h 30m"
    JOB_TIME_ERR = "job -m tenet1 -t 1a"
    JOB_START = "job -m tenet1 -s 10:00"

    # option user
    USER = "user"
    USER_MACHINE = "user -m tenet1"
    USER_MACHINES = "user -m tenet1 tenet2 kuda1"
    USER_GROUP = "user -g kuda"
    USER_MACHINE_GROUP = "user -g tenet -m tenet1"
    USER_MACHINE_GROUP_SUPPRESS = "user -g xenet -m tenet1 xenet1"

    # option run
    RUN = "run tenet1 python test.py"
    RUN_ARGUMENT = "run tenet1 'python test.py -N 10'"

    # option runs
    RUNS = "runs test.txt tenet"
    RUNS_BOUNDARY = "runs test.txt tenet 1 5"

    # option KILL
    KILL = "KILL"
    KILL_MACHINE = "KILL -m tenet1"
    KILL_MACHINES = "KILL -m tenet1 tenet2 kuda1"
    KILL_GROUP = "KILL -g kuda"
    KILL_MACHINE_GROUP = "KILL -g tenet -m tenet1"
    KILL_MACHINE_GROUP_SUPPRESS = "KILL -g xenet -m tenet1 xenet1"
    KILL_USER_ERR = "KILL -u root"
    KILL_ALL_ERR = "KILL -a"
    KILL_PID = "KILL -m tenet1 -p 1234 5678"
    KILL_PID_ERR = "KILL -m tenet1 tenet2 -p 1234"
    KILL_CMD = "KILL -m tenet1 -c python test.py"
    KILL_TIME = "KILL -m tenet1 -t 1h 30m"
    KILL_TIME_ERR = "KILL -m tenet1 -t 1a"
    KILL_START = "KILL -m tenet1 -s 10:00"

    # option machine
    MACHINE = "machine"
    MACHINE_MACHINE = "machine -m tenet1"
    MACHINE_MACHINES = "machine -m tenet1 tenet2 kuda1"
    MACHINE_GROUP = "machine -g kuda"
    MACHINE_MACHINE_GROUP = "machine -g tenet -m tenet1"
    MACHINE_MACHINE_GROUP_SUPPRESS = "machine -g xenet -m tenet1 xenet1"

    # option all
    ALL = "all"
    ALL_MACHINE = "all -m tenet1"
    ALL_MACHINES = "all -m tenet1 tenet2 kuda1"
    ALL_GROUP = "all -g kuda"
    ALL_MACHINE_GROUP = "all -g tenet -m tenet1"
    ALL_MACHINE_GROUP_SUPPRESS = "all -g xenet -m tenet1 xenet1"

    # option me
    ME = "me"
    ME_MACHINE = "me -m tenet1"
    ME_MACHINES = "me -m tenet1 tenet2 kuda1"
    ME_GROUP = "me -g kuda"
    ME_MACHINE_GROUP = "me -g tenet -m tenet1"
    ME_MACHINE_GROUP_SUPPRESS = "me -g xenet -m tenet1 xenet1"

    # option kill
    KILL_lower = "kill tenet1 1234"
    KILL_lower_pids = "kill tenet1 1234 5678"

    # option killall
    KILLALL = "killall"
    KILLALL_MACHINE = "killall -m tenet1"
    KILLALL_MACHINES = "killall -m tenet1 tenet2 kuda1"
    KILLALL_GROUP = "killall -g kuda"
    KILLALL_MACHINE_GROUP = "killall -g tenet -m tenet1"
    KILLALL_MACHINE_GROUP_SUPPRESS = "killall -g xenet -m tenet1 xenet1"
    KILLALL_USER_ERR = "killall -m tenet1 -u root"

    # option killmachine
    KILLMACHINE = "killmachine tenet1"

    # option killthis
    KILLTHIS = "killthis python test.py"
    KILLTHIS_MACHINE = "killthis python test.py -m tenet1"
    KILLTHIS_MACHINES = "killthis python test.py -m tenet1 tenet2 kuda1"
    KILLTHIS_GROUP = "killthis python test.py -g kuda"
    KILLTHIS_MACHINE_GROUP = "killthis python test.py -g tenet -m tenet1"
    KILLTHIS_MACHINE_GROUP_SUPPRESS = "killthis python test.py -g xenet -m tenet1 xenet1"

    # option killbefore
    KILLBEFORE = "killbefore 1h 30m"
    KILLBEFORE_MACHINE = "killbefore 1h 30m -m tenet1"
    KILLBEFORE_MACHINES = "killbefore 1h 30m -m tenet1 tenet2 kuda1"
    KILLBEFORE_GROUP = "killbefore 1h 30m -g kuda"
    KILLBEFORE_MACHINE_GROUP = "killbefore 1h 30m -g tenet -m tenet1"
    KILLBEFORE_MACHINE_GROUP_SUPPRESS = "killbefore 1h 30m -g xenet -m tenet1 xenet1"