import sys
import textwrap
from argparse import Action, ArgumentParser, Namespace, RawTextHelpFormatter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from .default import Default
from .name import extract_alphabet
from .option import Option
from .seconds import Seconds
from .spgio import MessageHandler


def yes_no(message: str | None = None) -> bool:
    """
    Get input yes or no
    If other input is given, ask again for 5 times
    'yes', 'y', 'Y', ... : pass
    'no', 'n', 'No', ... : fail
    """
    # Print message first if given
    if message is not None:
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


class CommandAction(Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        nargs: int | str,
        metavar: str | None = ...,
        required: bool = False,
        help: str | None = ...,
    ):
        super().__init__(
            option_strings,
            dest,
            nargs=nargs,
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
            values = " ".join(values)
        setattr(namespace, self.dest, values)


def add_optional_group(parser: ArgumentParser) -> None:
    """Add optional argument of "-g" or "--groupList" to input parser"""
    parser.add_argument(
        "-g",
        "--group",
        nargs="+",
        choices=Default().GROUP,
        default=["tenet", "xenet"],
        metavar="",
        help=textwrap.dedent(
            f"""\
            List of target machine group names, separated by space.
            Currently available: {Default().GROUP}
            """
        ),
    )
    return None


def add_optional_machine(parser: ArgumentParser) -> None:
    """Add optional argument of "-m" or "--machineList" to input parser"""
    parser.add_argument(
        "-m",
        "--machine",
        nargs="+",
        metavar="",
        help=textwrap.dedent(
            """\
            List of target machine names, separated by space.
            ex) tenet1 / tenet1 tenet2
            """
        ),
    )
    return None


def add_optional_user(parser: ArgumentParser) -> None:
    """Add optional argument of "-u" or "--user" to input parser"""
    parser.add_argument(
        "-u", "--user", metavar="", default=Default().user, help="Target user name."
    )


def add_optional_all_user(parser: ArgumentParser) -> None:
    """Add optional argument of "-a" or "--all" to input parser"""
    parser.add_argument(
        "-a", "--all", action="store_true", help="When given, print jobs of all users."
    )


def add_optional_pid(parser: ArgumentParser) -> None:
    """Add optional argument of "-p" or "--pid" to input parser"""
    parser.add_argument(
        "-p",
        "--pid",
        metavar="",
        nargs="+",
        help=textwrap.dedent(
            """\
            Jobs with specific PID.
            When this option is given, you should specify a single machine name.
            List of pid of target job, separated by space.
            """
        ),
    )


def add_optional_command(parser: ArgumentParser) -> None:
    """Add optional argument of "-c" or "--command" to input parser"""
    parser.add_argument(
        "-c",
        "--command",
        metavar="",
        nargs="+",
        action=CommandAction,
        help=textwrap.dedent(
            """\
            Jobs whose commands include pattern.
            List of words to search. The target command should have the exact pattern.
            """
        ),
    )


def add_optional_time(parser: ArgumentParser) -> None:
    """Add optional argument of "-t" or "--time" to input parser"""
    parser.add_argument(
        "-t",
        "--time",
        metavar="",
        nargs="+",
        help=textwrap.dedent(
            """\
            Jobs running less than the given time.
            Time interval separated by space.
            ex) 1w 5d 11h 50m 1s
            """
        ),
    )


def add_optional_start(parser: ArgumentParser) -> None:
    """Add optional argument of "-s" or "--start" to input parser"""
    parser.add_argument(
        "-s",
        "--start",
        metavar="",
        help=textwrap.dedent(
            """\
            Jobs started at a specific time.
            The start time should exactly match.
            """
        ),
    )


def get_args(user_input: str | list[str] | None = None) -> Namespace:
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
        description=textwrap.dedent(
            """\
            Arguments inside square brackets [] are required arguments while parentheses () are optional.
            For more information of each [option], type 'spg [option] -h' or 'spg [option] --help'.
            """
        ),
    )

    ####################################### List Parser #######################################
    parser_list = option_parser.add_parser(
        name="list",
        help="Print information of machines registered in SPG.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg list (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            """
        ),
    )
    add_optional_group(parser_list)
    add_optional_machine(parser_list)

    ####################################### Free Parser #######################################
    parser_free = option_parser.add_parser(
        name="free",
        help="Print free information of available machines.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg free (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            """
        ),
    )
    add_optional_group(parser_free)
    add_optional_machine(parser_free)

    ####################################### Job Parser #######################################
    parser_job = option_parser.add_parser(
        name="job",
        help="print current status of jobs.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg job (-g groups) (-m machines) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
            Listed jobs will satisfy all the given options.
            When group/machine are both given, the group is ignored.
            When -a, --all flag is set, --user option is ignored.
            """
        ),
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
        usage=textwrap.dedent(
            """\
            spg user (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            """
        ),
    )
    add_optional_group(parser_user)
    add_optional_machine(parser_user)

    ####################################### Run Parser #######################################
    parser_run = option_parser.add_parser(
        name="run",
        help="Run a job.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg run [machine] [program] (arguments)

            CAUTION!
            1. Invoke the job in the directory where you want the program to run.
            2. If your program uses -, -- arguments or redirection symbols < or >,
                wrap the program and arguments with a quote: ' or ".
            """
        ),
    )
    parser_run.add_argument("machine", help="target machine name.")
    parser_run.add_argument(
        "command",
        metavar="command",
        nargs="+",
        action=CommandAction,
        help="command you want to run: [program] (arguments)",
    )

    ####################################### Runs Parser #######################################
    parser_runs = option_parser.add_parser(
        name="runs",
        help="Run several jobs.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg runs [command file] [group] (start end)

            CAUTION!
            1. Invoke the job in the directory where you want the program to run.
            2. You can assign a maximum of 50 jobs at one time.
            3. Executed commands will be erased from the input command file.
            """
        ),
    )
    parser_runs.add_argument(
        "command", help="Files containing commands. Separated by lines."
    )
    parser_runs.add_argument(
        "group",
        nargs="+",
        help=textwrap.dedent(
            """\
            Target machine group name with and optional start, end number.
            When the start and end number is given, only use machines between them.
            ex1) tenet: search every available tenet machines
            ex2) tenet 100 150: search tenet100 ~ tenet150
            """
        ),
    )
    parser_runs.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="When given, force to run jobs at busy machines.",
    )
    parser_runs.add_argument(
        "--limit",
        help=textwrap.dedent(
            """\
            Limit number of jobs assigned to single machine.
            Assign a small number of (free cores) and (limit)
            This option can be useful when allocating jobs by number of free cores causes memory-overflow problem.
            """
        ),
        type=int,
        default=sys.maxsize,
    )

    ####################################### KILL Parser #######################################
    parser_KILL = option_parser.add_parser(
        name="KILL",
        help="Kill jobs satisfying conditions.",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg KILL (-g groups) (-m machines) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
            When group/machine are both given, the group is ignored.

            CAUTION!!
            1. Jobs to be killed should satisfy all the given options.
            2. When PID is given, only a single machine should be specified.
            3. When given a multi-process job, this command kills its session leader.
            """
        ),
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
        usage=textwrap.dedent(
            """\
            spg all (-g groups) (-m machines)
            When group/machine are both given, the group is ignored.
            When machine is specified, there is no group summary.
            """
        ),
    )
    add_optional_group(parser_all)
    add_optional_machine(parser_all)

    ###################################### Deprecate me ######################################
    parser_me = option_parser.add_parser(
        name="me",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg me (-g groups) (-m machines)
            When group/machine are both given, the group is ignored
            When machine is specified, there is no group summary
            """
        ),
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
        "pid", nargs="+", help="List of pid of target job, separated by space."
    )

    #################################### Deprecate killall ####################################
    parser_killall = option_parser.add_parser(
        name="killall",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg killall (-g groups) (-m machines) (-u user name)
            When group/machine are both given, the group is ignored.
            """
        ),
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
        usage=textwrap.dedent(
            """\
            spg killthis [pattern] (-g group name) (-m machine name)
            When group/machine names are both given, group name is ignored.
            """
        ),
    )
    parser_killthis.add_argument(
        "command",
        metavar="command",
        nargs="+",
        action=CommandAction,
        help="List of words to search. Target command should have exact pattern.",
    )
    add_optional_group(parser_killthis)
    add_optional_machine(parser_killthis)

    ################################## Deprecate killbefore ###################################
    parser_killbefore = option_parser.add_parser(
        name="killbefore",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage=textwrap.dedent(
            """\
            spg killbefore [time] (-g group name) (-m machine name)
            When group/machine names are both given, group name is ignored.
            """
        ),
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

    option: Option
    silent: bool = False
    machine: list[str] | None = None  # Target machine
    group: list[str] | None = None  # Target group
    start_end: tuple[int, int] | None = None  # Boundary of target group
    all: bool = False  # If true, overwrite user argument to None
    user: str | None = Default().user  # Target user, default: current user
    pid: list[int] | None = None  # Target pid
    time: Seconds | None = None  # Target time window
    start: str | None = None  # Target start time

    # run: running command, runs: command file, job/KILL: target command
    command: str | None = None

    # additional options for runs
    force: bool = False  # If true, assign jobs even to busy machine
    limit: int = sys.maxsize  # Limit the number of jobs assigned to single machine

    def __post_init__(self) -> None:
        self.option = self._redirect_option(cast(str, self.option))

        match self.option:
            case Option.list | Option.free | Option.user:
                user = cast(str, self.user)

                self.all = True
                self.group = self._overwrite_group(self.machine)
                self.user = self._check_user(self.all, user)

            case Option.job:
                user = cast(str, self.user)
                pids = cast(list[str] | None, self.pid)
                time = cast(list[str] | None, self.time)

                self.user = self._check_user(self.all, user)
                self.pid = self._check_pid(pids, self.machine)
                self.group = self._overwrite_group(self.machine)
                self.time = self._check_time(time)

            case Option.run:
                machine_name = cast(str, self.machine)

                self.machine = [machine_name]
                self.group = [extract_alphabet(machine_name)]

            case Option.runs:
                group = cast(list[str], self.group)

                self.group, self.start_end = self._check_group_boundary(group)
                self.machine = None

            case Option.KILL:
                user = cast(str, self.user)
                pids = cast(list[str] | None, self.pid)
                time = cast(list[str] | None, self.time)

                self.user = self._check_user(self.all, user)
                self._check_permission(self.user)
                self.pid = self._check_pid(pids, self.machine)
                self.group = self._overwrite_group(self.machine)
                self.time = self._check_time(time)
                self._double_check_KILL()

    @classmethod
    def from_input(cls, user_input: str | list[str] | None = None):
        return cls(**vars(get_args(user_input)))

    ###################################### Basic Utility ######################################
    def _redirect_option(self, option: str) -> Option:
        """Redirect option to Option class or check deprecated options"""
        if option in Option.__members__:
            # When given option is proper, return it's counterpart
            return Option[option]

        message_handler = MessageHandler()
        match option:
            # Redirect to list
            case "machine":
                message_handler.error(
                    "'spg machine' is Deprecated. Use 'spg list' instead."
                )

            # Redirect to job
            case "me":
                message_handler.error("'spg me' is Deprecated. Use 'spg job' instead.")
            case "all":
                message_handler.error(
                    "'spg all' is Deprecated. Use 'spg job -a' instead."
                )

            # Redirect to KILL
            case "kill":
                message_handler.error(
                    "'spg kill' is Deprecated. "
                    "Use 'spg KILL -m [machine] -p [pid]' instead."
                )
            case "killall":
                message_handler.error(
                    "'spg killall' is Deprecated. Use 'spg KILL' instead."
                )
            case "killmachine":
                message_handler.error(
                    "'spg killmachine' is Deprecated. Use 'spg KILL -m [machine]' instead."
                )
            case "killthis":
                message_handler.error(
                    "'spg killthis' is Deprecated. Use 'spg KILL -c [command]' instead."
                )
            case "killbefore":
                message_handler.error(
                    "'spg killbefore' is Deprecated. Use 'spg KILL -t [time]' instead."
                )
        exit()

    def _overwrite_group(self, machines: list[str] | None) -> list[str] | None:
        """Overwrite group option by machine option if it exists"""
        if machines is None:
            return self.group

        # Group from machine
        return list(
            dict.fromkeys(extract_alphabet(machine_name) for machine_name in machines)
        )

    def _check_user(self, all_user: bool, user: str) -> str | None:
        """Check if input user is registered. """
        if all_user:
            return None

        # Check if input user name is valid
        if user in Default().USERS:
            return user

        MessageHandler().error(f"Invalid user name: {self.user}.")
        exit()

    def _check_pid(
        self, pids: list[str] | None, machines: list[str] | None
    ) -> list[int] | None:
        """When pid list is given, you should specify machine name"""
        if pids is None:
            return pids

        if machines is None or len(machines) != 1:
            MessageHandler().error(
                "When killing job with pid, "
                "you should specify single machine name."
            )
            exit()

        return [int(pid) for pid in pids]

    def _check_group_boundary(
        self, group: list[str]
    ) -> tuple[list[str], tuple[int, int] | None]:
        """Check args for option 'runs'"""
        match group:
            case [group_name]:
                return [group_name], None
            case [group_name, start, end]:
                return [group_name], (int(start), int(end))
            case _:
                MessageHandler().error(
                    "When using 'runs' option, "
                    "you should specifiy machine group and optional start/end number."
                )
                exit()

    def _check_time(self, time: list[str] | None) -> Seconds | None:
        if time is None:
            return None

        try:
            return Seconds.from_input(time)
        except (KeyError, ValueError):
            MessageHandler().error(f"Invalid time window: {' '.join(time)}")
            MessageHandler().error("Run 'spg KILL -h' for more help")
            exit()

    def _check_permission(self, user: str | None) -> None:
        """Check argument user for option 'KILL'"""

        # When killing other user, you should be root
        if (user != Default().user) and (Default().user != "root"):
            MessageHandler().error("When killing other user's job, you should be root.")
            exit()

    def _double_check_KILL(self) -> None:
        """Double check if you really want to kill job"""
        question = "Do you want to kill "

        # When user is specified
        if self.user == Default().user:
            question += "your jobs"
        elif self.user is None:
            question += "jobs of all users"
        else:
            question += f"jobs of user {self.user}"

        # Kill by PID
        if self.pid is not None:
            question += f" with pid {self.pid}"

        # Kill by machine
        if self.machine is not None:
            question += f" at machine {self.machine}"
        # Kill by group
        elif self.group is not None:
            question += f" at group {self.group}"
        # Kill without restriction
        else:
            question += " at all machines"

        # Kill condition of command
        if self.command is not None:
            question += f" with command including '{self.command}'"

        # Kill condition of time
        if self.time is not None:
            question += f" with running less than '{self.time:human}'"

        # Kill condition of start
        if self.start is not None:
            question += f" starts at time '{self.start}'"

        # Get user input
        if not yes_no(question + "?"):
            MessageHandler().success("\nAborting...")
            exit()
