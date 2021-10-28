import argparse
import textwrap

from machine import Machine
from default import Default
from spgio import InputHandler, MessageHandler


class Argument:
    def __init__(self) -> None:
        # default values and message handler
        self.default = Default()
        self.message_handler = MessageHandler()

        # Generate base SPG parser
        self.spg_parser = argparse.ArgumentParser(prog='spg',
                                                  formatter_class=argparse.RawTextHelpFormatter,
                                                  description='Statistical Physics Group',
                                                  usage='spg (-h) (-s) {option} (args)')
        self.spg_parser.add_argument('-s', '--silent',
                                     action='store_true',
                                     help='when given, run spg without progress bar')

        # Generate sub parser
        description = textwrap.dedent('''\
                                    For more information of each {option},
                                    type \'spg {option} -h\' or \'spg {option} --help\'
                                    ''')
        self.option_parser = self.spg_parser.add_subparsers(dest='option',
                                                            title='SPG options',
                                                            required=True,
                                                            metavar='Available options',
                                                            description=description)

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

    ###################################### Basic Utility ######################################
    def _get_kill_question(self, args: argparse.Namespace) -> str:
        """
            Get kill question based on input args
        """
        question = 'Do you want to kill '
        # When user is specified
        if args.user_name != self.default.user:
            question += f"jobs of user {args.user_name}"
        else:
            question += "your jobs"

        # Kill by PID
        if args.pid_list is not None:
            question += f" with pid {args.pid_list} of machine '{args.machine_name_list[0]}'?"
            return question

        # Kill by machine
        if args.machine_name_list is not None:
            question += f" at machine {args.machine_name_list}"
        # Kill by group
        elif args.group_name_list is not None:
            question += f" at group {args.group_name_list}"
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

        return question + '?'

    def _redirect_deprecated(self, args: argparse.Namespace) -> argparse.Namespace:
        # Redirect to list
        if args.option == 'machine':
            args.option = 'list'
            self.message_handler.warning("This method will be deprecated. Use 'spg list' instead")

        # Redirect to job
        elif args.option == 'me':
            args.option = 'job'
            args.all = False
            args.user_name = self.default.user
            self.message_handler.warning("This method will be deprecated. Use 'spg job' instead")

        elif args.option == 'all':
            args.option = 'job'
            args.all = True
            args.user_name = None
            self.message_handler.warning("This method will be deprecated. Use 'spg job -a' instead")

        # Redirect to KILL
        elif args.option == 'kill':
            args.option = 'KILL'
            args.machine_name_list = [args.machine_name]
            args.pid_list = args.pid_list
            self.message_handler.warning("This method will be deprecated. Use 'spg KILL -m [machine name] -p [pid list]' instead")

        elif args.option == 'killall':
            args.option = 'KILL'
            args.pid_list = None
            args.command = None
            args.time = None
            self.message_handler.warning("This method will be deprecated. Use 'spg KILL' instead")

        elif args.option == 'killmachine':
            args.option = 'KILL'
            args.pid_list = None
            args.command = None
            args.time = None
            args.machine_name_list = [args.machine_name]
            self.message_handler.warning("This method will be deprecated. Use 'spg KILL -m [machine list]' instead")

        elif args.option == 'killthis':
            args.option = 'KILL'
            args.pid_list = None
            args.command = args.pattern
            args.time = None
            self.message_handler.warning("This method will be deprecated. Use 'spg KILL -c [command]' instead")

        elif args.option == 'killbefore':
            args.option = 'KILL'
            args.pid_list = None
            args.command = None
            self.message_handler.warning("This method will be deprecated. Use 'spg KILL -t [time]' instead")

        return args

    def to_seconds(self, timeWindow: list[str]) -> int:
        """ Convert time window (str) to time window (seconds) """
        unit_to_second = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        try:
            return sum(int(time[:-1]) * unit_to_second[time[-1]] for time in timeWindow)
        except (KeyError, ValueError):
            self.message_handler.error('Invalid time window: ' + '  '.join(timeWindow))
            self.message_handler.error('Run \'spg KILL -h\' for more help')
            exit()

    def _check_command_option(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Change option command from list of string to string
        """
        try:
            args.command = ' '.join(args.command)
        # When command is not given, do nothing
        except (AttributeError, TypeError):
            pass
        return args

    def _check_job_option(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'job'
        """
        # Check if input user name is valid
        for user_list in Default.USER.values():
            if args.user_name in user_list:
                break
        else:
            self.message_handler.error(f"Invalid user name: {args.user_name}")
            exit()

        # When 'all' flag is true, set user name to None
        # Refer Commands.get_ps_cmd for the reason
        if args.all:
            args.user_name = None

        return args

    def _check_user_option(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'user'
        """
        if args.machine_name_list is not None:
            args.group_name_list = list(set(Machine.get_group_name(machine_name)
                                            for machine_name in args.machine_name_list))
        return args

    def _check_KILL_option(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'KILL'
        """
        # Double check if you really want to kill job
        question = self._get_kill_question(args)
        if not InputHandler.yes_no(question):
            exit()

        # When specifying user name, you should be root
        if (args.user_name != self.default.user) and (self.default.user != 'root'):
            self.message_handler.error('When specifying user at kill option, you should be root')
            exit()

        # When pid list is given, you should specify machine name
        if (args.pid_list is not None) and (len(args.machine_name_list) != 1):
            self.message_handler.error('When killing job with pid list, you should specify single machine name')
            exit()

        # When time is given, change it to integer
        if args.time is not None:
            args.time = self.to_seconds(args.time)
        return args

    def _check_runs_option(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'Runs'
        """
        # Only group name is specified
        if len(args.group_name) == 1:
            args.start_end = None
            args.group_name = args.group_name[0]

        # Group name and their start, end numbers are specified
        elif len(args.group_name) == 3:
            args.start_end = tuple([int(args.group_name[1]), int(args.group_name[2])])
            args.group_name = args.group_name[0]

        else:
            self.message_handler.error('When running several jobs, you should specifiy machine group and optional start/end number')
            exit()
        return args

    def get_args(self) -> argparse.Namespace:
        """
            Return arguments as namespace
        """
        args = self.spg_parser.parse_args()

        # Redirect deprecated options
        args = self._redirect_deprecated(args)

        # option command
        args = self._check_command_option(args)

        # When main option is job
        if args.option == 'job':
            return self._check_job_option(args)

        # When main option is user
        if args.option == 'user':
            return self._check_user_option(args)

        # When main option is KILL
        if args.option == 'KILL':
            return self._check_KILL_option(args)

        # When main option is runs
        if args.option == 'runs':
            return self._check_runs_option(args)

        return args

    ###################################### Basic Utility ######################################
    def _add_optional_argument_group(self, parser: argparse.ArgumentParser) -> None:
        """
            Add optional argument of '-g' or '--groupList' to input parser
        """
        document = textwrap.dedent(f'''\
                                    List of target machine group name, seperated by space
                                    Currently available: {Default.GROUP}
                                    ''')
        parser.add_argument('-g', '--group',
                            nargs='+',
                            choices=Default.GROUP,
                            metavar='',
                            dest='group_name_list',
                            help=document)
        return None

    def _add_optional_argument_machine(self, parser: argparse.ArgumentParser) -> None:
        """
            Add optional argument of '-m' or '--machineList' to input parser
        """
        document = textwrap.dedent('''\
                                   List of target machine name, seperated by space
                                   ex) tenet1 / tenet1 tenet2
                                   ''')
        parser.add_argument('-m', '--machine',
                            nargs='+',
                            metavar='',
                            dest='machine_name_list',
                            help=document)
        return None

    def _add_optional_argument_user(self, parser: argparse.ArgumentParser) -> None:
        """
            Add optional argument of '-u' or '--user' to input parser
        """
        document = textwrap.dedent('''\
                                   Target user name
                                   If you are not root, you can only specify yourself (default)
                                   ''')
        parser.add_argument('-u', '--user',
                            metavar='',
                            default=self.default.user,
                            dest='user_name',
                            help=document)

    ####################################### Sub parsers #######################################
    def _list(self) -> None:
        """
            Add 'list' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg machine (-g group list) (-m machine list)
                                   When group/machine are both given, group is ignored
                                   ''')
        parser_list = self.option_parser.add_parser('list',
                                                    help='Print information of machines registered in SPG',
                                                    formatter_class=argparse.RawTextHelpFormatter,
                                                    usage=document)
        self._add_optional_argument_group(parser_list)
        self._add_optional_argument_machine(parser_list)

    def _free(self) -> None:
        """
            Add 'free' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg free (-g group list) (-m machine list)
                                   When group/machine are both given, group is ignored
                                   ''')
        parser_free = self.option_parser.add_parser('free',
                                                    help='Print free informations of available machines',
                                                    formatter_class=argparse.RawTextHelpFormatter,
                                                    usage=document)
        self._add_optional_argument_group(parser_free)
        self._add_optional_argument_machine(parser_free)

    def _job(self) -> None:
        """
            Add 'job' option
            'group', 'machine', 'user', 'all' as optional argument
            When group/machine names are both given, group name is ignored
            When user/all are both given, user is ignored
        """
        document = textwrap.dedent('''\
                                   spg job (-a) (-g group list) (-m machine list) (-u user name)
                                   When group/machine are both given, group is ignored
                                   When --all flag is set, --user option is ignored
                                   ''')
        parser_job = self.option_parser.add_parser('job',
                                                   help='print current status of jobs',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        self._add_optional_argument_group(parser_job)
        self._add_optional_argument_machine(parser_job)
        parser_job.add_argument('-a', '--all',
                                action='store_true',
                                help='When given, print jobs of all users')
        parser_job.add_argument('-u', '--userName',
                                metavar='',
                                default=self.default.user,
                                dest='user_name',
                                help='Target user name. Default: me')

    def _user(self) -> None:
        """
            Add 'user' option
            'group' as optional argument
        """
        document = textwrap.dedent('''\
                                   spg free (-g group list)
                                   When group/machine are both given, group is ignored
                                   ''')
        parser_user = self.option_parser.add_parser('user',
                                                    help='Print job count of users per machine group',
                                                    formatter_class=argparse.RawTextHelpFormatter,
                                                    usage=document)
        self._add_optional_argument_group(parser_user)
        self._add_optional_argument_machine(parser_user)

    def _run(self) -> None:
        """
            Add 'run' option
            'machine' as positional argument: necessary option
            'cmd' as positional argument with more than 1 inputs
        """
        document = textwrap.dedent('''\
                                   spg run [machine] [program] (arguments)

                                   CAUTION!
                                   1. Invoke the job in the directory where you want the program to run
                                   2. Don't append \'&\' character at the tail of commands.
                                      spg will do it for you
                                   3. If you want to use redirection symbols < or >,
                                      type them in a quote, such as \'<\' or \'>\'
                                   ''')
        parser_run = self.option_parser.add_parser('run',
                                                   help='Run a job',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        parser_run.add_argument('machine_name',
                                help='target machine name')
        parser_run.add_argument('command',
                                nargs='+',
                                help='command you want to run. [program] (arguments)')

    def _runs(self) -> None:
        """
            Add 'runs' option
            'group' as positional argument: necessary option
            'cmdFile' as positional argument
        """
        document = textwrap.dedent('''\
                                   spg runs [command file] [group] (start end)

                                   CAUTION!
                                   1. Invoke the job in the directory where you want the program to run
                                   2. Don't append \'&\' character at the tail of commands.
                                      spg will do it for you
                                   3. If you want to use redirection symbols < or >,
                                      type them in a quote, such as \'<\' or \'>\'
                                   4. You can assign maximum of 50 jobs at one time.
                                   5. Executed commands will be dropped from input command file
                                   ''')
        parser_runs = self.option_parser.add_parser('runs',
                                                    help='Run several jobs',
                                                    formatter_class=argparse.RawTextHelpFormatter,
                                                    usage=document)
        parser_runs.add_argument('cmd_file', help='Files containing commands. Sepearated by lines.')
        groupNameDocument = textwrap.dedent('''\
                                            Target machine group name with optinal start, end number
                                            When start and end number is given, only use machines between them
                                            ex) tenet 100 150: search tenet100~tenet150
                                            ''')
        parser_runs.add_argument('group_name',
                                 nargs='+',
                                 help=groupNameDocument)

    def _KILL(self) -> None:
        """
            Add 'KILL' option
        """
        document = textwrap.dedent('''\
                                   spg kill (-m machine list) (-g group list) (-u user name) (-p pid_list) (-c command) (-t time)
                                   CAUTION!!
                                   1. Jobs to be killed should satisfy all the given options.
                                   2. When given a multi-threaded job, this command kills it's session leader.
                                   3. When group/machine are both given, group is ignored.
                                   ''')
        parser_KILL = self.option_parser.add_parser('KILL',
                                                    help='kill job',
                                                    formatter_class=argparse.RawTextHelpFormatter,
                                                    usage=document)
        self._add_optional_argument_user(parser_KILL)
        self._add_optional_argument_machine(parser_KILL)
        self._add_optional_argument_group(parser_KILL)

        # Kill by pid
        pid_document = textwrap.dedent('''\
                                      Kill my jobs with specific pid.
                                      When this option is given, you should specifiy single machine name.
                                      List of pid of target job, seperated by space.
                                      ''')
        parser_KILL.add_argument('-p', '--pid',
                                 metavar='',
                                 nargs='+',
                                 dest='pid_list',
                                 help=pid_document)

        # Kill by command pattern
        command_document = textwrap.dedent('''\
                                          Kill my jobs whose commands includes pattern.
                                          List of words to search. Target command should have exact pattern.
                                          ''')
        parser_KILL.add_argument('-c', '--command',
                                 metavar='',
                                 nargs='+',
                                 dest='command',
                                 help=command_document)

        # Kill by time
        time_document = textwrap.dedent('''\
                                       Kill my jobs running less than given time.
                                       Time interval seperated by space.
                                       ex) 1w 5d 11h 50m 1s
                                       ''')
        parser_KILL.add_argument('-t', '--time',
                                 metavar='',
                                 nargs='+',
                                 dest='time',
                                 help=time_document)

        # Kill by start
        start_document = textwrap.dedent('''\
                                        Kill my jobs started at specific time
                                        Start time should exactly match with the result of "spg job"
                                        ''')
        parser_KILL.add_argument('-s', '--start',
                                 metavar='',
                                 dest='start',
                                 help=start_document)

    ######################################## Deprecate ########################################
    def _add_positional_argument_machine(self, parser: argparse.ArgumentParser) -> None:
        """
            Add positional argument 'machine_name' to input parser
        """
        parser.add_argument('machine_name',
                            help='target machine name')
        return None

    def _machine(self) -> None:
        """
            deprecated
        """
        parser_machine = self.option_parser.add_parser('machine', help='Deprecated')
        self._add_optional_argument_group(parser_machine)
        self._add_optional_argument_machine(parser_machine)

    def _all(self) -> None:
        """
            Add 'all' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg all (-g group list) (-m machine list)
                                   When group/machine are both given, group is ignored
                                   When machine is specified, there is no group summary
                                   ''')
        parser_all = self.option_parser.add_parser('all', help='Deprecated',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        self._add_optional_argument_group(parser_all)
        self._add_optional_argument_machine(parser_all)
        parser_all.add_argument('-u', '--user',
                                metavar='',
                                default=None,
                                dest='user_name',
                                help='Target user name')

    def _me(self) -> None:
        """
            Add 'me' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg me (-g group list) (-m machine list)
                                   When group/machine are both given, group is ignored
                                   When machine is specified, there is no group summary
                                   ''')
        parser_me = self.option_parser.add_parser('me', help='Deprecated',
                                                  formatter_class=argparse.RawTextHelpFormatter,
                                                  usage=document)
        parser_me.add_argument('-u', '--user',
                               metavar='',
                               default=self.default.user,
                               dest='user_name',
                               help='Target user name')
        self._add_optional_argument_group(parser_me)
        self._add_optional_argument_machine(parser_me)

    def _kill(self) -> None:
        """
            Add 'kill' option
            'machine' as positional argument
            'pid list' as positional argument with more than 1 inputs
        """
        parser_kill = self.option_parser.add_parser('kill', help='Deprecated',
                                                    formatter_class=argparse.RawTextHelpFormatter,
                                                    usage='spg kill [machine name] [pid list]')
        self._add_positional_argument_machine(parser_kill)
        parser_kill.add_argument('pid_list',
                                 nargs='+',
                                 help='List of pid of target job. Seperated by space')

    def _killall(self) -> None:
        """
            Add 'killall' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg killall (-g group list) (-m machine list) (-u user name)
                                   When group/machine are both given, group is ignored
                                   ''')
        parser_killall = self.option_parser.add_parser('killall', help='Deprecated',
                                                       formatter_class=argparse.RawTextHelpFormatter,
                                                       usage=document)
        self._add_optional_argument_group(parser_killall)
        self._add_optional_argument_machine(parser_killall)
        self._add_optional_argument_user(parser_killall)

    def _killmachine(self) -> None:
        """
            deprecated
        """
        parser_killmachine = self.option_parser.add_parser('killmachine', help='Deprecated')
        self._add_positional_argument_machine(parser_killmachine)
        self._add_optional_argument_user(parser_killmachine)

    def _killthis(self) -> None:
        """
            Add 'killthis' option
            'pattern' as positional argument with more than 1 inputs
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg killthis [pattern] (-g group name) (-m machine name)
                                   When group/machine names are both given, group name is ignored
                                   ''')
        parser_killthis = self.option_parser.add_parser('killthis', help='Deprecated',
                                                        formatter_class=argparse.RawTextHelpFormatter,
                                                        usage=document)
        parser_killthis.add_argument('pattern',
                                     nargs='+',
                                     help='List of words to search. Target command should have exact pattern')
        self._add_optional_argument_group(parser_killthis)
        self._add_optional_argument_machine(parser_killthis)
        self._add_optional_argument_user(parser_killthis)

    def _killbefore(self) -> None:
        """
            Add 'killbefore' option
            'time' as positional argument with more than 1 inputs
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg killbefore [time] (-g group name) (-m machine name)
                                   When group/machine names are both given, group name is ignored
                                   ''')
        parser_killbefore = self.option_parser.add_parser('killbefore', help='Deprecated',
                                                          formatter_class=argparse.RawTextHelpFormatter,
                                                          usage=document)
        parser_killbefore.add_argument('time',
                                       nargs='+',
                                       help='Time interval seperated by space. ex) 1w 5d 11h 50m 1s')
        self._add_optional_argument_group(parser_killbefore)
        self._add_optional_argument_machine(parser_killbefore)
        self._add_optional_argument_user(parser_killbefore)


if __name__ == "__main__":
    print("This is moudel Argument from SPG")
