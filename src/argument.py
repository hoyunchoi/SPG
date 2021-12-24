import argparse
import textwrap

from .default import Default
from .spgio import MessageHandler
from .utils import get_machine_group, input_time_to_seconds, yes_no


class Argument:
    def __init__(self) -> None:
        # default values and message handler
        self.default = Default()
        self.message_handler = MessageHandler()

        # Generate base SPG parser
        self.main_parser = argparse.ArgumentParser(
            prog="spg",
            formatter_class=argparse.RawTextHelpFormatter,
            description="Statistical Physics Group",
            usage="spg (-h) (-s) [option] ..."
        )
        self.main_parser.add_argument(
            "-s", "--silent",
            action="store_true",
            help="when given, run spg without progress bar"
        )

        # Generate sub-parser
        self.option_parser = self.main_parser.add_subparsers(
            dest="option",
            title="SPG options",
            required=True,
            metavar="Available options",
            description=textwrap.dedent(
                """\
                Arguments inside square brackets [] are necessary aruments while parentheses () are optional
                For more information of each [option],
                type 'spg [option] -h' or 'spg [option] --help'
                """
            )
        )

        # Generate options
        self._list()
        self._free()
        self._job()
        self._user()
        self._run()
        self._runs()
        self._KILL()
        self._machine()        # Will be deprecated
        self._all()            # Will be deprecated
        self._me()             # Will be deprecated
        self._kill()           # Will be deprecated
        self._killall()        # Will be deprecated
        self._killmachine()    # Will be deprecated
        self._killthis()       # Will be deprecated
        self._killbefore()     # Will be deprecated

    def get_args(self) -> argparse.Namespace:
        """
        Return argparse namespace contains following
            silent: bool
            option: str
            machine
                run: str
                runs: None
                list, free, job, user, KILL: list[str] | None
            group
                run: None
                runs: str
                list, free, job, user, KILL: list[str] | None

            command
                run: str -> running command
                runs: str -> command file
                job, KILL: str | None -> target command

            start_end
                runs: tuple[int,int] | None -> Boundary of target machine

            attributes only for matching jobs: option job/KILL
                all: bool | None -> If true, overwrite user argument to None
                user: str | None -> Target user, default: current user
                pid: list[str] | None -> Target pid
                time: int | None -> Target time window
                start: str | None -> Target start time
        """
        args = self.main_parser.parse_args()

        # Redirect deprecated options
        self._redirect_deprecated(args)

        # Check arguments for each options are proper or not
        match args.option:
            case "list" | "free" | "user":
                self._overwrite_group(args)
            case "job":
                self._check_user(args)
                if args.all:
                    args.user = None
                self._check_pid(args)
                self._overwrite_group(args)
                self._unlist_command(args)
                self._time_to_seconds(args)
            case "run":
                self._unlist_command(args)
                args.group = None
            case "runs":
                self._check_group_boundary(args)
                args.machine = None
            case "KILL":
                self._check_user(args)
                if args.all:
                    args.user = None
                self._check_user_KILL(args)
                self._check_pid(args)
                self._overwrite_group(args)
                self._unlist_command(args)
                self._double_check_KILL(args)
                self._time_to_seconds(args)

        return args

    ###################################### Basic Utility ######################################
    def _redirect_deprecated(self, args: argparse.Namespace) -> None:
        match args.option:
            # Do not redirect
            case "list" | "free" | "job" | "user" | "run" | "runs" | "KILL":
                pass

            # Redirect to list
            case "machine":
                args.option = "list"
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg list' instead"
                )

            # Redirect to job
            case "me":
                args.option = "job"
                args.all = False
                args.user = self.default.user
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg job' instead"
                )
            case "all":
                args.option = "job"
                args.all = True
                args.user = None
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg job -a' instead"
                )

            # Redirect to KILL
            case "kill":
                args.option = "KILL"
                args.machine = [args.machine_name]
                args.pid = args.pid
                self.message_handler.warning(
                    "This method will be deprecated. "
                    "Use 'spg KILL -m [machine name] -p [pid list]' instead"
                )
            case "killall":
                args.option = "KILL"
                args.pid = None
                args.command = None
                args.time = None
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg KILL' instead"
                )
            case "killmachine":
                args.option = "KILL"
                args.pid = None
                args.command = None
                args.time = None
                args.machine = [args.machine_name]
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg KILL -m [machine list]' instead"
                )
            case "killthis":
                args.option = "KILL"
                args.pid = None
                args.command = args.pattern
                args.time = None
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg KILL -c [command]' instead"
                )
            case "killbefore":
                args.option = "KILL"
                args.pid = None
                args.command = None
                self.message_handler.warning(
                    "This method will be deprecated. Use 'spg KILL -t [time]' instead"
                )

    def _overwrite_group(self, args: argparse.Namespace) -> None:
        """ Overwrite group option by machine option is exists """
        if args.machine is None:
            return

        # Group from machine
        group = list(set(
            get_machine_group(machine_name) for machine_name in args.machine
        ))

        # Overwrite if necessary
        if args.group != group:
            if isinstance(args.group, list):
                self.message_handler.warning(
                    "Group option is suppressed by Machine option"
                )
            args.group = group

    def _check_user(self, args: argparse.Namespace) -> None:
        """ Check argument user """
        # Check if input user name is valid
        for user_list in Default.USER.values():
            if args.user in user_list:
                break
        else:
            self.message_handler.error(f"Invalid user name: {args.user}")
            exit()

    def _check_pid(self, args) -> None:
        """ When pid list is given, you should specify machine name """
        if (args.pid is not None) and (len(args.machine) != 1):
            self.message_handler.error(
                "When killing job with pid list, "
                "you should specify single machine name"
            )
            exit()

    def _unlist_command(self, args: argparse.Namespace) -> None:
        """ Change option command from list of string to string """
        if args.command is None:
            return
        args.command = " ".join(args.command)

    def _time_to_seconds(self, args: argparse.Namespace) -> None:
        """ Convert time window (str) to time window (seconds) """
        if args.time is None:
            return

        args.time = input_time_to_seconds(args.time)

    def _check_group_boundary(self, args: argparse.Namespace) -> None:
        """ Check args for option 'runs' """
        match args.group:
            case [group]:
                args.group = group
                args.start_end = None
            case [group, start, end]:
                args.group = group
                args.start_end = (int(start), int(end))
            case _:
                self.message_handler.error(
                    "When using 'runs' option, "
                    "you should specifiy machine group and optional start/end number"
                )
                exit()

    def _check_user_KILL(self, args: argparse.Namespace) -> None:
        """ Check argument user for option 'KILL' """

        # When specifying user name, you should be root
        if (args.user != self.default.user) and (self.default.user != "root"):
            self.message_handler.error(
                "When killing other user's job, you should be root"
            )
            exit()

    def _double_check_KILL(self, args: argparse.Namespace) -> None:
        """ Double check if you really want to kill job """
        question = self._get_kill_question(args)
        if not yes_no(question):
            exit()

    def _get_kill_question(self, args: argparse.Namespace) -> str:
        """ Get kill question based on input args """
        question = "Do you want to kill "

        # When user is specified
        if args.user is None:
            question += "jobs of all users"
        elif args.user != self.default.user:
            question += f"jobs of user {args.user}"
        else:
            question += "your jobs"

        # Kill by PID
        if args.pid is not None:
            question += f" with pid {args.pid} at machine {args.machine[0]}"

        # Kill by machine
        if args.machine is not None:
            question += f" at machine {args.machine}"
        # Kill by group
        elif args.group is not None:
            question += f" at group {args.group}"
        # Kill without restriction
        else:
            question += f" at all machines"

        # Kill condition of command
        if args.command is not None:
            question += f" with command including '{args.command}'"

        # Kill condition of time
        if args.time is not None:
            question += f" with running less than '{' '.join(args.time)}'"

        # Kill condition of start
        if args.start is not None:
            question += f" starts at time '{args.start}'"

        return question + "?"

    ##################################### Argument Helper #####################################
    def _add_optional_group(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-g" or "--groupList" to input parser """
        parser.add_argument(
            "-g", "--group",
            nargs="+",
            choices=Default.GROUP,
            metavar="",
            help=textwrap.dedent(
                f"""\
                List of target machine group name, seperated by space
                Currently available: {Default.GROUP}
                """
            )
        )
        return None

    def _add_optional_machine(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-m" or "--machineList" to input parser """
        parser.add_argument(
            "-m", "--machine",
            nargs="+",
            metavar="",
            help=textwrap.dedent(
                """\
                List of target machine name, seperated by space
                ex) tenet1 / tenet1 tenet2
                """
            )
        )
        return None

    def _add_optional_user(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-u" or "--user" to input parser """
        parser.add_argument(
            "-u", "--user",
            metavar="",
            default=self.default.user,
            help="Target user name"
        )

    def _add_optional_all_user(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-a" or "--all" to input parser """
        parser.add_argument("-a", "--all",
                            action="store_true",
                            help="When given, print jobs of all users")

    def _add_optional_pid(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-p" or "--pid" to input parser """
        parser.add_argument(
            "-p", "--pid",
            metavar="",
            nargs="+",
            help=textwrap.dedent(
                """\
                Jobs with specific pid.
                When this option is given, you should specifiy single machine name.
                List of pid of target job, seperated by space.
                """
            )
        )

    def _add_optional_command(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-c" or "--command" to input parser """
        parser.add_argument(
            "-c", "--command",
            metavar="",
            nargs="+",
            help=textwrap.dedent(
                """\
                Jobs whose commands includes pattern.
                List of words to search. Target command should have exact pattern.
                """
            )
        )

    def _add_optional_time(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-t" or "--time" to input parser """
        parser.add_argument(
            "-t", "--time",
            metavar="",
            nargs="+",
            help=textwrap.dedent(
                """\
                Jobs running less than given time.
                Time interval seperated by space.
                ex) 1w 5d 11h 50m 1s
                """
            )
        )

    def _add_optional_start(self, parser: argparse.ArgumentParser) -> None:
        """ Add optional argument of "-s" or "--start" to input parser """
        parser.add_argument(
            "-s", "--start",
            metavar="",
            help=textwrap.dedent(
                """\
                Jobs started at specific time
                Start time should exactly match with the result of 'spg job'
                """
            )
        )

    ####################################### Sub parsers #######################################
    def _list(self) -> None:
        """ Add 'list' option """
        parser_list = self.option_parser.add_parser(
            name="list",
            help="Print information of machines registered in SPG",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg list (-g group list) (-m machine list)
                When group/machine are both given, group is ignored
                """
            )
        )
        self._add_optional_group(parser_list)
        self._add_optional_machine(parser_list)

    def _free(self) -> None:
        """ Add 'free' option """
        parser_free = self.option_parser.add_parser(
            name="free",
            help="Print free informations of available machines",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg free (-g group list) (-m machine list)
                When group/machine are both given, group is ignored
                """
            )
        )
        self._add_optional_group(parser_free)
        self._add_optional_machine(parser_free)

    def _job(self) -> None:
        """ Add 'job' option """
        parser_job = self.option_parser.add_parser(
            name="job",
            help="print current status of jobs",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg job (-g group list) (-m machine list) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)
                Counted jobs satisfy all the given options.
                When group/machine are both given, group is ignored
                When -a, --all flag is set, --user option is ignored
                """
            )
        )
        self._add_optional_machine(parser_job)
        self._add_optional_group(parser_job)
        self._add_optional_user(parser_job)
        self._add_optional_all_user(parser_job)

        self._add_optional_pid(parser_job)
        self._add_optional_command(parser_job)
        self._add_optional_time(parser_job)
        self._add_optional_start(parser_job)

    def _user(self) -> None:
        """ Add 'user' option """
        parser_user = self.option_parser.add_parser(
            name="user",
            help="Print job count of users per machine group",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg free (-g group list) (-m machine list)
                When group/machine are both given, group is ignored
                """
            )
        )
        self._add_optional_group(parser_user)
        self._add_optional_machine(parser_user)

    def _run(self) -> None:
        """ Add 'run' option """
        parser_run = self.option_parser.add_parser(
            name="run",
            help="Run a job",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg run [machine] [program] (arguments)

                CAUTION!
                1. Invoke the job in the directory where you want the program to run
                2. If your program uses -, -- arguments or redirection symbols < or >,
                   wrap the program and arguments with quote: " or "
                """
            )
        )
        parser_run.add_argument("machine",
                                help="target machine name")
        parser_run.add_argument("command",
                                nargs="+",
                                help="command you want to run. [program] (arguments)")

    def _runs(self) -> None:
        """ Add 'runs' option """
        parser_runs = self.option_parser.add_parser(
            name="runs",
            help="Run several jobs",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg runs [command file] [group] (start end)

                CAUTION!
                1. Invoke the job in the directory where you want the program to run
                2. If your program uses -, -- arguments or redirection symbols < or >,
                   wrap the program and arguments with quote: ' or "
                3. You can assign maximum of 50 jobs at one time.
                4. Executed commands will be erased from input command file
                """
            )
        )
        parser_runs.add_argument("command",
                                 help="Files containing commands. Sepearated by lines.")
        parser_runs.add_argument(
            "group",
            nargs="+",
            help=textwrap.dedent(
                """\
                Target machine group name with optinal start, end number
                When start and end number is given, only use machines between them
                ex1) tenet: search every available tenet machines
                ex2) tenet 100 150: search tenet100 ~ tenet150
                """
            )
        )

    def _KILL(self) -> None:
        """ Add 'KILL' option """
        parser_KILL = self.option_parser.add_parser(
            name="KILL",
            help="kill job",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg KILL (-g group list) (-m machine list) (-u user) (-a) (-p pid) (-c command) (-t time) (-s start)

                CAUTION!!
                1. Jobs to be killed should satisfy all the given options.
                2. When pid is given, only single machine should be specified.
                3. When given a multi-process job, this command kills it's session leader.
                4. When group/machine are both given, group is ignored.
                """
            )
        )
        self._add_optional_group(parser_KILL)
        self._add_optional_machine(parser_KILL)
        self._add_optional_user(parser_KILL)
        self._add_optional_all_user(parser_KILL)

        self._add_optional_pid(parser_KILL)
        self._add_optional_command(parser_KILL)
        self._add_optional_time(parser_KILL)
        self._add_optional_start(parser_KILL)

    ######################################## Deprecate ########################################
    def _add_positional_argument_machine(self, parser: argparse.ArgumentParser) -> None:
        """
            Add positional argument "machine_name" to input parser
        """
        parser.add_argument("machine_name",
                            help="target machine name")
        return None

    def _machine(self) -> None:
        """ deprecated """
        parser_machine = self.option_parser.add_parser("machine",
                                                       help="Deprecated")
        self._add_optional_group(parser_machine)
        self._add_optional_machine(parser_machine)

    def _all(self) -> None:
        """ deprecated """
        parser_all = self.option_parser.add_parser(
            name="all",
            help="Deprecated",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg all (-g group list) (-m machine list)
                When group/machine are both given, group is ignored
                When machine is specified, there is no group summary
                """
            )
        )
        self._add_optional_group(parser_all)
        self._add_optional_machine(parser_all)
        self._add_optional_user(parser_all)

    def _me(self) -> None:
        """ deprecated """
        parser_me = self.option_parser.add_parser(
            name="me",
            help="Deprecated",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg me (-g group list) (-m machine list)
                When group/machine are both given, group is ignored
                When machine is specified, there is no group summary
                """
            )
        )

        self._add_optional_group(parser_me)
        self._add_optional_machine(parser_me)

    def _kill(self) -> None:
        """ deprecated """
        parser_kill = self.option_parser.add_parser(
            name="kill",
            help="Deprecated",
            formatter_class=argparse.RawTextHelpFormatter,
            usage="spg kill [machine name] [pid list]"
        )
        self._add_positional_argument_machine(parser_kill)
        parser_kill.add_argument(
            "pid",
            nargs="+",
            help="List of pid of target job. Seperated by space"
        )

    def _killall(self) -> None:
        """ deprecated """
        parser_killall = self.option_parser.add_parser(
            name="killall",
            help="Deprecated",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg killall (-g group list) (-m machine list) (-u user name)
                When group/machine are both given, group is ignored
                """
            )
        )
        self._add_optional_group(parser_killall)
        self._add_optional_machine(parser_killall)
        self._add_optional_user(parser_killall)

    def _killmachine(self) -> None:
        """ deprecated """
        parser_killmachine = self.option_parser.add_parser(name="killmachine",
                                                           help="Deprecated")
        self._add_positional_argument_machine(parser_killmachine)
        self._add_optional_user(parser_killmachine)

    def _killthis(self) -> None:
        """ deprecated """
        parser_killthis = self.option_parser.add_parser(
            name="killthis",
            help="Deprecated",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg killthis [pattern] (-g group name) (-m machine name)
                When group/machine names are both given, group name is ignored
                """
            )
        )
        parser_killthis.add_argument(
            "pattern",
            nargs="+",
            help="List of words to search. Target command should have exact pattern"
        )
        self._add_optional_group(parser_killthis)
        self._add_optional_machine(parser_killthis)
        self._add_optional_user(parser_killthis)

    def _killbefore(self) -> None:
        """ deprecated """
        parser_killbefore = self.option_parser.add_parser(
            name="killbefore",
            help="Deprecated",
            formatter_class=argparse.RawTextHelpFormatter,
            usage=textwrap.dedent(
                """\
                spg killbefore [time] (-g group name) (-m machine name)
                When group/machine names are both given, group name is ignored
                """
            )
        )
        parser_killbefore.add_argument(
            "time",
            nargs="+",
            help="Time interval seperated by space. ex) 1w 5d 11h 50m 1s"
        )
        self._add_optional_group(parser_killbefore)
        self._add_optional_machine(parser_killbefore)
        self._add_optional_user(parser_killbefore)


if __name__ == "__main__":
    print("This is moduel Argument from SPG")
