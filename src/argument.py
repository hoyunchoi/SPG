import sys
import textwrap
from argparse import Action, ArgumentParser, Namespace, RawTextHelpFormatter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import cast, get_args

from .default import DEFAULT
from .name import extract_alphabet
from .option import Option
from .seconds import Seconds
from .spgio import MESSAGE_HANDLER


def yes_no(message: str = "") -> bool:
    """
    Get input yes or no
    If other input is given, ask again for 5 times
    'yes', 'y', 'Y', ... : pass
    'no', 'n', 'No', ... : fail
    """
    # Print message first if given
    if message:
        print(message)

    # Ask 5 times
    for _ in range(5):
        reply = str(input("(y/n): ")).strip().lower()
        if reply[0] == "y":
            return True
        elif reply[0] == "n":
            return False
        print("You should provied either 'y' or 'n'", end=" ")
    return False


class SingleStringAction(Action):
    """Convert multiple string arguments to single string"""

    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        nargs: int | str,
        default: str = "",
        metavar: str | None = None,
        required: bool = False,
        help: str | None = None,
    ):
        super().__init__(
            option_strings,
            dest,
            nargs=nargs,
            default=default,
            metavar=metavar,
            required=required,
            help=help,
        )

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: Sequence[str] | None,
        option_string: str | None,
    ) -> None:
        if isinstance(values, Sequence):
            setattr(namespace, self.dest, " ".join(values))


def add_optional_group(parser: ArgumentParser) -> None:
    """Restrict target groups to handle"""
    parser.add_argument(
        "-g",
        "--group",
        nargs="+",
        choices=DEFAULT.GROUPS,
        default=["tenet", "xenet"],
        metavar="",
        help=textwrap.dedent(f"""\
            List of target machine group names, separated by space.
            Currently available: {DEFAULT.GROUPS}
            """),
    )
    return None


def add_optional_machine(parser: ArgumentParser) -> None:
    """Restrict target machines to handle"""
    parser.add_argument(
        "-m",
        "--machine",
        nargs="+",
        metavar="",
        default=[],
        help=textwrap.dedent("""\
            List of target machine names, separated by space.
            ex) tenet1 / tenet1 tenet2
            """),
    )
    return None


def add_optional_user(parser: ArgumentParser) -> None:
    """Restrict target user to handle"""
    parser.add_argument(
        "-u", "--user", metavar="", default=DEFAULT.user, help="Target user name."
    )


def add_optional_all_user(parser: ArgumentParser) -> None:
    """Target user to be all user"""
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="When given, do the command to all users. Overwrite --user option.",
    )


def add_optional_pid(parser: ArgumentParser) -> None:
    """Restrict pid of a target job to handle"""
    parser.add_argument(
        "-p",
        "--pid",
        metavar="",
        nargs="*",
        default=[],
        type=int,
        help=textwrap.dedent("""\
            Jobs with specific PID (Process ID).
            When this option is given, you should specify a single machine name.
            List of pid of target job, separated by space.
            """),
    )


def add_optional_command(parser: ArgumentParser) -> None:
    """Restrict command of a target job to handle"""
    parser.add_argument(
        "-c",
        "--command",
        metavar="",
        nargs="*",
        default="",
        action=SingleStringAction,
        help=textwrap.dedent("""\
            Jobs whose commands include pattern.
            List of words to search. The target command should have the exact pattern.
            """),
    )


def add_optional_time(parser: ArgumentParser) -> None:
    """Restrict running time of a target job to handle"""
    parser.add_argument(
        "-t",
        "--time",
        metavar="",
        nargs="*",
        default="",
        help=textwrap.dedent("""\
            Jobs running less than the given time.
            Time interval separated by space.
            ex) 1w 5d 11h 50m 1s
            """),
    )


def add_optional_start(parser: ArgumentParser) -> None:
    """Restrict start time of a target job to handle"""
    parser.add_argument(
        "-s",
        "--start",
        metavar="",
        nargs=1,
        default="",
        help=textwrap.dedent("""\
            Jobs started at a specific time.
            The start time should exactly match as the result of spg job.
            """),
    )


def get_arguments(user_input: str | list[str] | None = None) -> Namespace:
    # Generate base SPG parser
    main_parser = ArgumentParser(
        prog="spg",
        formatter_class=RawTextHelpFormatter,
        description="Statistical Physics Group",
        usage="spg (-h) (-s) [option] ...",
    )
    main_parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        help="when given, run spg without progress bar.",
    )

    # Generate sub-parser
    option_parser = main_parser.add_subparsers(
        dest="option",
        title="SPG options",
        required=True,
        metavar="Available Options",
        description=textwrap.dedent("""\
            Arguments inside square brackets [] are required arguments while parentheses () are optional.
            For more information of each [option], type 'spg [option] -h' or 'spg [option] --help'.
            """),
    )

    ####################################### List Parser #######################################
    parser_list = option_parser.add_parser(
        name="list",
        help="Print information of machines registered in SPG.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg list (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            """),
    )
    add_optional_group(parser_list)
    add_optional_machine(parser_list)

    ####################################### Free Parser #######################################
    parser_free = option_parser.add_parser(
        name="free",
        help="Print free information of available machines.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg free (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            """),
    )
    add_optional_group(parser_free)
    add_optional_machine(parser_free)

    ####################################### Job Parser #######################################
    parser_job = option_parser.add_parser(
        name="job",
        help="print current status of jobs.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg job (-g groups) (-m machines) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
            Listed jobs will satisfy all the given options.
            When group/machine are both given, the group is ignored.
            When -a, --all flag is set, --user option is ignored.
            """),
    )
    add_optional_machine(parser_job)
    add_optional_group(parser_job)
    add_optional_user(parser_job)
    add_optional_all_user(parser_job)
    add_optional_pid(parser_job)
    add_optional_command(parser_job)
    add_optional_time(parser_job)
    add_optional_start(parser_job)

    ####################################### User Parser #######################################
    parser_user = option_parser.add_parser(
        name="user",
        help="Print job count of users per machine group.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg user (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            """),
    )
    add_optional_group(parser_user)
    add_optional_machine(parser_user)

    ####################################### Run Parser #######################################
    parser_run = option_parser.add_parser(
        name="run",
        help="Run a job.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg run [machine] [program] (arguments)

            CAUTION!
            1. Invoke the job in the directory where you want the program to run.
            2. If your program uses -, -- arguments or redirection symbols < or >,
                wrap the program and arguments with a quote: ' or ".
            """),
    )
    parser_run.add_argument("machine", nargs=1, help="target machine name.")
    parser_run.add_argument(
        "command",
        metavar="command",
        nargs="+",
        action=SingleStringAction,
        help="command you want to run: [program] (arguments)",
    )

    ####################################### Runs Parser #######################################
    parser_runs = option_parser.add_parser(
        name="runs",
        help="Run several jobs.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg runs [command file] [group] (start end)

            CAUTION!
            1. Invoke the job in the directory where you want the program to run.
            2. You can assign a maximum of 50 jobs at one time.
            3. Executed commands will be erased from the input command file.
            """),
    )
    parser_runs.add_argument(
        "command", help="Files containing commands. Separated by lines."
    )
    parser_runs.add_argument(
        "group",
        nargs="+",
        help=textwrap.dedent("""\
            Target machine group name with and optional start, end number.
            When the start and end number is given, only use machines between them.
            ex1) tenet: search every available tenet machines
            ex2) tenet 100 150: search tenet100 ~ tenet150
            """),
    )
    parser_runs.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="When given, force to run jobs at busy machines.",
    )
    parser_runs.add_argument(
        "--limit",
        help=textwrap.dedent("""\
            Limit number of jobs assigned to single machine.
            Assign a small number of (free cores) and (limit)
            This option can be useful when allocating jobs by number of free cores causes memory-overflow problem.
            """),
        type=int,
        default=sys.maxsize,
    )

    ####################################### KILL Parser #######################################
    parser_KILL = option_parser.add_parser(
        name="KILL",
        help="Kill jobs satisfying conditions.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg KILL (-g groups) (-m machines) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
            When group/machine are both given, the group is ignored.

            CAUTION!!
            1. Jobs to be killed should satisfy all the given options.
            2. When PID is given, only a single machine should be specified.
            3. When given a multi-process job, this command kills its session leader.
            """),
    )
    add_optional_group(parser_KILL)
    add_optional_machine(parser_KILL)
    add_optional_user(parser_KILL)
    add_optional_all_user(parser_KILL)
    add_optional_pid(parser_KILL)
    add_optional_command(parser_KILL)
    add_optional_time(parser_KILL)
    add_optional_start(parser_KILL)

    ################################## Deprecated subparsers ##################################
    def add_positional_machine(parser: ArgumentParser) -> None:
        """
        Add positional argument "machine_name" to input parser
        """
        parser.add_argument("machine", help="target machine name.")
        return None

    #################################### Deprecate machine ####################################
    parser_machine = option_parser.add_parser("machine", help="Deprecated")
    add_optional_group(parser_machine)
    add_optional_machine(parser_machine)

    ###################################### Deprecate all ######################################
    parser_all = option_parser.add_parser(
        name="all",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg all (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            When machine is specified, there is no group summary.
            """),
    )
    add_optional_group(parser_all)
    add_optional_machine(parser_all)

    ###################################### Deprecate me ######################################
    parser_me = option_parser.add_parser(
        name="me",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg me (-g groups) (-m machines)
            When group/machine are both given, the group is ignored
            When machine is specified, there is no group summary
            """),
    )
    add_optional_group(parser_me)
    add_optional_machine(parser_me)

    ###################################### Deprecate kill #####################################
    parser_kill = option_parser.add_parser(
        name="kill",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage="spg kill [machine name] [pid list]",
    )
    add_positional_machine(parser_kill)
    parser_kill.add_argument(
        "pid",
        nargs="+",
        type=int,
        help="List of pid of target job, separated by space.",
    )

    #################################### Deprecate killall ####################################
    parser_killall = option_parser.add_parser(
        name="killall",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg killall (-g groups) (-m machines) (-u user name)
            When group/machine are both given, the group is ignored.
            """),
    )
    add_optional_group(parser_killall)
    add_optional_machine(parser_killall)
    add_optional_user(parser_killall)

    ################################## Deprecate killmachine ##################################
    parser_killmachine = option_parser.add_parser(
        name="killmachine",
        formatter_class=RawTextHelpFormatter,
        help="Deprecated",
        usage="spg killmachine [machine name]",
    )
    add_positional_machine(parser_killmachine)
    add_optional_user(parser_killmachine)

    ################################### Deprecate killthis ####################################
    parser_killthis = option_parser.add_parser(
        name="killthis",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg killthis [pattern] (-g group name) (-m machine name)
            When group/machine names are both given, group name is ignored.
            """),
    )
    parser_killthis.add_argument(
        "command",
        metavar="command",
        nargs="+",
        action=SingleStringAction,
        default="",
        help="List of words to search. Target command should have exact pattern.",
    )
    add_optional_group(parser_killthis)
    add_optional_machine(parser_killthis)

    ################################## Deprecate killbefore ###################################
    parser_killbefore = option_parser.add_parser(
        name="killbefore",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent("""\
            spg killbefore [time] (-g group name) (-m machine name)
            When group/machine names are both given, group name is ignored.
            """),
    )
    parser_killbefore.add_argument(
        "time", nargs="+", help="Time interval separated by space. ex) 1w 5d 11h 50m 1s"
    )
    add_optional_group(parser_killbefore)
    add_optional_machine(parser_killbefore)

    # Parse the arguments
    if user_input is None:
        return main_parser.parse_args()
    elif isinstance(user_input, str):
        from shlex import split

        return main_parser.parse_args(split(user_input))
    else:
        return main_parser.parse_args(user_input)


@dataclass
class Argument:
    """Argument dataclass to store user input"""

    silent: bool  # Whether to report progress bar
    option: Option
    machine: list[str] = field(default_factory=list)  # Target machine
    group: list[str] = field(default_factory=list)  # Target group
    start_end: tuple[int, int] = (-1, -1)  # Boundary of target group
    all: bool = False  # If true, overwrite user argument to None
    user: str = DEFAULT.user  # Target user, default: current user
    pid: list[int] = field(default_factory=list)  # Target pid
    time: Seconds = field(default_factory=Seconds)  # Target time window
    start: str = ""  # Target start time

    # run: running command, runs: command file, job/KILL: target command
    command: str = ""

    # additional options for runs
    force: bool = False  # If true, assign jobs even to busy machine
    limit: int = sys.maxsize  # Limit the number of jobs assigned to single machine

    def __post_init__(self) -> None:
        self.option = self._redirect_option(cast(str, self.option))
        match self.option:
            case "list" | "free" | "user":
                self.all = True
                self.group = self._overwrite_group(self.machine)
                self.user = self._check_user(self.all, self.user)

            case "job":
                self.user = self._check_user(self.all, self.user)
                self._check_pid(self.pid, self.machine)
                self.group = self._overwrite_group(self.machine)
                self.time = self._check_time(cast(list[str], self.time))

            case "run":
                self.group = [extract_alphabet(self.machine[0])]

            case "runs":
                self.group, self.start_end = self._check_group_boundary(self.group)
                self.machine = []

            case "KILL":
                self.user = self._check_user(self.all, self.user)
                self._check_permission(self.user)
                self._check_pid(self.pid, self.machine)
                self.group = self._overwrite_group(self.machine)
                self.time = self._check_time(cast(list[str], self.time))
                self._double_check_KILL()

    @classmethod
    def from_input(cls, user_input: str | list[str] | None = None):
        return cls(**vars(get_args(user_input)))

    ###################################### Basic Utility ######################################
    def _redirect_option(self, option: str) -> Option:
        """Redirect option to Option class or check deprecated options"""
        if option in get_args(Option):
            # When given option is proper, return it's counterpart
            return cast(Option, option)

        match option:
            # Redirect to list
            case "machine":
                MESSAGE_HANDLER.error(
                    "'spg machine' is Deprecated. Use 'spg list' instead."
                )

            # Redirect to job
            case "me":
                MESSAGE_HANDLER.error("'spg me' is Deprecated. Use 'spg job' instead.")
            case "all":
                MESSAGE_HANDLER.error(
                    "'spg all' is Deprecated. Use 'spg job -a' instead."
                )

            # Redirect to KILL
            case "kill":
                MESSAGE_HANDLER.error(
                    "'spg kill' is Deprecated. "
                    "Use 'spg KILL -m [machine] -p [pid]' instead."
                )
            case "killall":
                MESSAGE_HANDLER.error(
                    "'spg killall' is Deprecated. Use 'spg KILL' instead."
                )
            case "killmachine":
                MESSAGE_HANDLER.error(
                    "'spg killmachine' is Deprecated. Use 'spg KILL -m [machine]'"
                    " instead."
                )
            case "killthis":
                MESSAGE_HANDLER.error(
                    "'spg killthis' is Deprecated. Use 'spg KILL -c [command]' instead."
                )
            case "killbefore":
                MESSAGE_HANDLER.error(
                    "'spg killbefore' is Deprecated. Use 'spg KILL -t [time]' instead."
                )
        exit()

    def _overwrite_group(self, machines: list[str]) -> list[str]:
        """Overwrite group option by machine option if it exists"""
        if len(machines) == 0:
            return self.group

        # Group from machine
        return list(
            dict.fromkeys(extract_alphabet(machine_name) for machine_name in machines)
        )

    def _check_user(self, all_user: bool, user: str) -> str:
        """Check if input user is registered."""
        if all_user:
            return ""

        # Check if input user name is valid
        if user in DEFAULT.USERS:
            return user

        MESSAGE_HANDLER.error(f"Invalid user name: {self.user}.")
        exit()

    def _check_pid(self, pids: list[int], machines: list[str]) -> None:
        """When pid list is given, you should specify machine name"""
        if len(pids) == 0:
            return

        if len(machines) != 1:
            MESSAGE_HANDLER.error(
                "When killing job with pid, you should specify single machine name."
            )
            exit()

    def _check_group_boundary(
        self, group: list[str]
    ) -> tuple[list[str], tuple[int, int]]:
        """Check args for option 'runs'"""
        match group:
            case [group_name]:
                return [group_name], (-1, -1)
            case [group_name, start, end]:
                return [group_name], (int(start), int(end))
            case _:
                MESSAGE_HANDLER.error(
                    "When using 'runs' option, "
                    "you should specifiy machine group and optional start/end number."
                )
                exit()

    def _check_time(self, time: list[str]) -> Seconds:
        if len(time) == 0:
            return Seconds()

        try:
            return Seconds.from_input(time)
        except (KeyError, ValueError):
            MESSAGE_HANDLER.error(f"Invalid time window: {' '.join(time)}")
            MESSAGE_HANDLER.error("Run 'spg KILL -h' for more help")
            exit()

    def _check_permission(self, user: str | None) -> None:
        """Check argument user for option 'KILL'"""

        # When killing other user, you should be root
        if (user != DEFAULT.user) and (DEFAULT.user != "root"):
            MESSAGE_HANDLER.error("When killing other user's job, you should be root.")
            exit()

    def _double_check_KILL(self) -> None:
        """Double check if you really want to kill job"""
        question = "Do you want to kill "

        # When user is specified
        if self.user == DEFAULT.user:
            question += "your jobs"
        elif self.user == "":
            question += "jobs of all users"
        else:
            question += f"jobs of user {self.user}"

        # Kill by PID
        if self.pid:
            question += f" with pid {self.pid}"

        # Kill by machine
        if self.machine:
            question += f" at machine {self.machine}"
        # Kill by group
        elif self.group:
            question += f" at group {self.group}"
        # Kill without restriction
        else:
            question += " at all machines"

        # Kill condition of command
        if self.command:
            question += f" with command including '{self.command}'"

        # Kill condition of time
        if self.time != Seconds():
            question += f" with running less than '{self.time:human}'"

        # Kill condition of start
        if self.start:
            question += f" starts at time '{self.start}'"

        # Get user input
        if not yes_no(question + "?"):
            MESSAGE_HANDLER.success("\nAborting...")
            exit()
