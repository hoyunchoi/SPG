import textwrap
from dataclasses import dataclass
from collections.abc import Sequence
from argparse import Action, ArgumentParser, Namespace, RawTextHelpFormatter

from .option import Option
from .default import Default
from .output import MessageHandler
from .utils import get_machine_group, input_time_to_seconds, yes_no


class CommandAction(Action):
    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str,
                 nargs: int | str,
                 metavar: str | None = ...,
                 required: bool = False,
                 help: str | None = ...):
        super().__init__(option_strings, dest, nargs=nargs, metavar=metavar, required=required, help=help)

    def __call__(self,
                 parser: ArgumentParser,
                 namespace: Namespace,
                 values: Sequence[str] | None,
                 option_string: str | None) -> None:
        if isinstance(values, Sequence):
            values = " ".join(values)
        setattr(namespace, self.dest, values)


def add_optional_group(parser: ArgumentParser) -> None:
    """ Add optional argument of "-g" or "--groupList" to input parser """
    parser.add_argument(
        "-g", "--group",
        nargs="+",
        choices=Default.GROUP,
        metavar="",
        help=textwrap.dedent(
            f"""\
            List of target machine group names, separated by space.
            Currently available: {Default.GROUP}
            """
        )
    )
    return None


def add_optional_machine(parser: ArgumentParser) -> None:
    """ Add optional argument of "-m" or "--machineList" to input parser """
    parser.add_argument(
        "-m", "--machine",
        nargs="+",
        metavar="",
        help=textwrap.dedent(
            """\
            List of target machine names, separated by space.
            ex) tenet1 / tenet1 tenet2
            """
        )
    )
    return None


def add_optional_user(parser: ArgumentParser) -> None:
    """ Add optional argument of "-u" or "--user" to input parser """
    parser.add_argument(
        "-u", "--user",
        metavar="",
        default=Default().user,
        help="Target user name."
    )


def add_optional_all_user(parser: ArgumentParser) -> None:
    """ Add optional argument of "-a" or "--all" to input parser """
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="When given, print jobs of all users."
    )


def add_optional_pid(parser: ArgumentParser) -> None:
    """ Add optional argument of "-p" or "--pid" to input parser """
    parser.add_argument(
        "-p", "--pid",
        metavar="",
        nargs="+",
        help=textwrap.dedent(
            """\
            Jobs with specific PID.
            When this option is given, you should specify a single machine name.
            List of pid of target job, separated by space.
            """
        )
    )


def add_optional_command(parser: ArgumentParser) -> None:
    """ Add optional argument of "-c" or "--command" to input parser """
    parser.add_argument(
        "-c", "--command",
        metavar="",
        nargs="+",
        action=CommandAction,
        help=textwrap.dedent(
            """\
            Jobs whose commands include pattern.
            List of words to search. The target command should have the exact pattern.
            """
        )
    )


def add_optional_time(parser: ArgumentParser) -> None:
    """ Add optional argument of "-t" or "--time" to input parser """
    parser.add_argument(
        "-t", "--time",
        metavar="",
        nargs="+",
        help=textwrap.dedent(
            """\
            Jobs running less than the given time.
            Time interval separated by space.
            ex) 1w 5d 11h 50m 1s
            """
        )
    )


def add_optional_start(parser: ArgumentParser) -> None:
    """ Add optional argument of "-s" or "--start" to input parser """
    parser.add_argument(
        "-s", "--start",
        metavar="",
        help=textwrap.dedent(
            """\
            Jobs started at a specific time.
            The start time should exactly match.
            """
        )
    )


def get_args(user_input: str | list[str] | None = None) -> Namespace:
    # Generate base SPG parser
    main_parser = ArgumentParser(
        prog="spg",
        formatter_class=RawTextHelpFormatter,
        description="Statistical Physics Group",
        usage="spg (-h) (-s) [option] ..."
    )
    main_parser.add_argument(
        "-s", "--silent",
        action="store_true",
        help="when given, run spg without progress bar."
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
        )
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
        )
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
        )
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
        )
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
        )
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
        )
    )
    parser_run.add_argument(
        "machine",
        help="target machine name."
    )
    parser_run.add_argument(
        "command",
        metavar="command",
        nargs="+",
        action=CommandAction,
        help="command you want to run: [program] (arguments)"
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
        )
    )
    parser_runs.add_argument("command",
                             help="Files containing commands. Separated by lines.")
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
        )
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
        )
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
        parser.add_argument("machine",
                            help="target machine name.")
        return None

    #################################### Deprecate machine ####################################
    parser_machine = option_parser.add_parser("machine",
                                              help="Deprecated")
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
        )
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
        )
    )
    add_optional_group(parser_me)
    add_optional_machine(parser_me)

    ###################################### Deprecate kill #####################################
    parser_kill = option_parser.add_parser(
        name="kill",
        help="Deprecated",
        formatter_class=RawTextHelpFormatter,
        usage="spg kill [machine name] [pid list]"
    )
    add_positional_machine(parser_kill)
    parser_kill.add_argument(
        "pid",
        nargs="+",
        help="List of pid of target job, separated by space."
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
        )
    )
    add_optional_group(parser_killall)
    add_optional_machine(parser_killall)
    add_optional_user(parser_killall)

    ################################## Deprecate killmachine ##################################
    parser_killmachine = option_parser.add_parser(
        name="killmachine",
        formatter_class=RawTextHelpFormatter,
        help="Deprecated",
        usage="spg killmachine [machine name]"
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
        )
    )
    parser_killthis.add_argument(
        "command",
        metavar="command",
        nargs="+",
        action=CommandAction,
        help="List of words to search. Target command should have exact pattern."
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
        )
    )
    parser_killbefore.add_argument(
        "time",
        nargs="+",
        help="Time interval separated by space. ex) 1w 5d 11h 50m 1s"
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
    """ Argument dataclass to store user input """
    option: Option
    silent: bool = False
    machine: str | list[str] | None = None      # Target machine. For run, it is str
    group: str | list[str] | None = None        # Target group. For runs, it is str
    start_end: tuple[int, int] | None = None    # Boundary of target group
    all: bool = False                           # If true, overwrite user argument to None
    user: str | None = Default().user           # Target user, default: current user
    pid: list[str] | None = None                # Target pid
    time: list[str] | None = None               # Target time window in string format
    time_seconds: int | None = None             # Target time window in seconds
    start: str | None = None                    # Target start time

    # run: running command, runs: command file, job/KILL: target command
    command: str | None = None

    def __post_init__(self) -> None:
        self.option = self._redirect_deprecated_options()

        match self.option:
            case Option.list | Option.free | Option.user:
                self._overwrite_group()
            case Option.job:
                self._check_user()
                self._check_pid()
                self._overwrite_group()
                self._time_to_seconds()
            case Option.run:
                self.group = None
            case Option.runs:
                self._check_group_boundary()
                self.machine = None
            case Option.KILL:
                self._check_user()
                self._check_user_KILL()
                self._check_pid()
                self._overwrite_group()
                self._time_to_seconds()
                self._double_check_KILL()

    @classmethod
    def from_input(cls, user_input: str | list[str] | None = None):
        return cls(**vars(get_args(user_input)))

    ###################################### Basic Utility ######################################
    def _redirect_deprecated_options(self) -> Option:
        """ Redirect deprecated options """
        if self.option in list(Option):
            return self.option
        elif self.option in ["list", "free", "job", "user", "run", "runs", "KILL"]:
            # When given option is proper, do nothing and return
            return Option[self.option]

        message_handler = MessageHandler()
        match self.option:
            # Redirect to list
            case "machine":
                message_handler.warning(
                    "'spg machine' will be Deprecated. Use 'spg list' instead."
                )
                return Option.list

            # Redirect to job
            case "me":
                self.all = False
                self.user = Default().user
                message_handler.warning(
                    "'spg me' will be Deprecated. Use 'spg job' instead."
                )
                return Option.job
            case "all":
                self.all = True
                self.user = None
                message_handler.warning(
                    "'spg all' will be Deprecated. Use 'spg job -a' instead."
                )
                return Option.job

            # Redirect to KILL
            case "kill":
                assert isinstance(self.machine, str)
                self.machine = [self.machine]
                self.pid = self.pid
                message_handler.warning(
                    "'spg kill' will be Deprecated. "
                    "Use 'spg KILL -m [machine] -p [pid]' instead."
                )
                return Option.KILL
            case "killall":
                self.pid = None
                self.command = None
                self.time = None
                message_handler.warning(
                    "'spg killall' will be Deprecated. Use 'spg KILL' instead."
                )
                return Option.KILL
            case "killmachine":
                self.pid = None
                self.command = None
                self.time = None
                assert isinstance(self.machine, str)
                self.machine = [self.machine]
                message_handler.warning(
                    "'spg killmachine' will be Deprecated. Use 'spg KILL -m [machine]' instead."
                )
                return Option.KILL
            case "killthis":
                self.pid = None
                self.command = self.command
                self.time = None
                message_handler.warning(
                    "'spg killthis' will be Deprecated. Use 'spg KILL -c [command]' instead."
                )
                return Option.KILL
            case "killbefore":
                self.pid = None
                self.command = None
                message_handler.warning(
                    "'spg killbefore' will be Deprecated. Use 'spg KILL -t [time]' instead."
                )
                return Option.KILL
        raise RuntimeError(f"No such option: {self.option}.")

    def _overwrite_group(self) -> None:
        """ Overwrite group option by machine option if it exists """
        if self.machine is None:
            return

        # Group from machine
        group = list(dict.fromkeys(
            get_machine_group(machine_name) for machine_name in self.machine
        ))

        # Overwrite if necessary
        if self.group != group:
            if isinstance(self.group, list):
                MessageHandler().warning(
                    "Group option is suppressed by Machine option."
                )
            self.group = group

    def _check_user(self) -> None:
        """ Check if input user is registered """
        if self.all:
            self.user = None
            return

        # Check if input user name is valid
        for user_list in Default.USER.values():
            if self.user in user_list:
                return

        MessageHandler().error(f"Invalid user name: {self.user}.")
        exit()

    def _check_pid(self) -> None:
        """ When pid list is given, you should specify machine name """
        if self.pid is not None:
            assert isinstance(self.machine, list)
            if len(self.machine) != 1:
                MessageHandler().error(
                    "When killing job with pid list, "
                    "you should specify single machine name."
                )
                exit()

    def _time_to_seconds(self) -> None:
        """ Convert time window (str) to time window (seconds) """
        if self.time is None:
            return
        self.time_seconds = input_time_to_seconds(self.time)

    def _check_group_boundary(self) -> None:
        """ Check args for option 'runs' """
        match self.group:
            case [group]:
                self.group = group
                self.start_end = None
            case [group, start, end]:
                self.group = group
                self.start_end = (int(start), int(end))
            case _:
                MessageHandler().error(
                    "When using 'runs' option, "
                    "you should specifiy machine group and optional start/end number."
                )
                exit()

    def _check_user_KILL(self) -> None:
        """ Check argument user for option 'KILL' """

        # When specifying user name, you should be root
        if (self.user != Default().user) and (Default().user != "root"):
            MessageHandler().error(
                "When killing other user's job, you should be root."
            )
            exit()

    def _double_check_KILL(self) -> None:
        """ Double check if you really want to kill job """
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
            assert isinstance(self.machine, list)
            question += f" with pid {self.pid}"

        # Kill by machine
        if self.machine is not None:
            question += f" at machine {self.machine}"
        # Kill by group
        elif self.group is not None:
            question += f" at group {self.group}"
        # Kill without restriction
        else:
            question += f" at all machines"

        # Kill condition of command
        if self.command is not None:
            question += f" with command including '{self.command}'"

        # Kill condition of time
        if self.time is not None:
            question += f" with running less than '{' '.join(self.time)}'"

        # Kill condition of start
        if self.start is not None:
            question += f" starts at time '{self.start}'"

        # Get user input
        if not yes_no(question + "?"):
            exit("Aborting...")


if __name__ == "__main__":
    print("This is moduel Argument from SPG")
