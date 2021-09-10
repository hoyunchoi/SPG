import colorama
import argparse
import textwrap
from termcolor import colored

from Common import groupFileDict, currentUser

class Arguments:
    def __init__(self) -> None:
        global groupFileDict, currentUser
        self.groupNameList = list(groupFileDict.keys())
        self.currentUser = currentUser
        self.parser = argparse.ArgumentParser(prog='spg',
                                              formatter_class=argparse.RawTextHelpFormatter,
                                              description='Statistical Physics Group',
                                              usage='spg (-h) (-s) {option} (args)')
        self.parser.add_argument('-s', '--silent',
                                 action='store_true',
                                 help='when given, run spg without progress bar')
        description = textwrap.dedent('''\
                                    For more information of each {option},
                                    type \'spg {option} -h\' or \'spg {option} --help\'
                                    ''')
        self.optionParser = self.parser.add_subparsers(dest='option',
                                                       title='SPG options',
                                                       required=True,
                                                       metavar='Available options',
                                                       description=description)

        # Generate options
        self.optionList()
        self.optionFree()
        self.optionJob()
        self.optionUser()
        self.optionRun()
        self.optionRuns()
        self.optionKILL()
        self.optionMachine()        # Will be deprecated
        self.optionAll()            # Will be deprecated
        self.optionMe()             # Will be deprecated
        self.optionKill()           # Will be deprecated
        self.optionKillAll()        # Will be deprecated
        self.optionKillMachine()    # Will be deprecated
        self.optionKillThis()       # Will be deprecated
        self.optionKillBefore()     # Will be deprecated

    ###################################### Basic Utility ######################################
    def getKillQuestion(self, args: argparse.Namespace) -> str:
        """
            Get kill question based on input args
        """
        question = 'Do you want to kill '
        # When user is specified
        if args.userName != self.currentUser:
            question += f"jobs of user {args.userName}"
        else:
            question += "your jobs"

        # Kill by PID
        if args.pidList:
            question += f" with pid {args.pidList} of machine '{args.machineNameList[0]}'?"
            return question

        # Kill by machine
        if args.machineNameList:
            question += f" at machine {args.machineNameList}"
        # Kill by group
        elif args.groupNameList:
            question += f" at group {args.groupNameList}"
        # Kill without restriction
        else:
            question += f" at all machines"

        # Kill condition of command
        if args.command:
            question += f" with command including '{args.command}'"

        # Kill condition of time
        if args.time:
            question += f" with time interval of '{' '.join(args.time)}'"

        return question + '?'

    @staticmethod
    def YesNo() -> None:
        while True:
            reply = str(input('(y/n): ')).strip().lower()
            if reply[0] == 'y':
                return None
            elif reply[0] == 'n':
                exit()
            else:
                print("You should provied either 'y' or 'n'", end=' ')

    def killYesNo(self, question: str) -> None:
        """
            Double check if user really wants to kill their jobs
            If 'yes', 'y', 'Y', 'Ye', ... are given, kill the job
            If 'no', 'n', 'No', ... are given, exit the command
        """
        print(question)
        self.YesNo()


    def redirectDeprecated(self, args:argparse.Namespace) -> argparse.Namespace:
        # Redirect to list
        if args.option == 'machine':
            args.option = 'list'
            pass
        # Redirect to job
        elif args.option == 'me':
            args.option = 'job'
            args.all = False
            args.userName = self.currentUser
            print(colored("This method will be deprecated. Use 'spg job' instead", 'red'))
        elif args.option == 'all':
            args.option = 'job'
            args.all = True
            args.userName = None
            print(colored("This method will be deprecated. Use 'spg job -a' instead", 'red'))
        # Redirect to KILL
        elif args.option == 'kill':
            args.option = 'KILL'
            args.machineNameList = [args.machineName]
            args.pidList = args.pidList
            print(colored("This method will be deprecated. Use 'spg KILL -m [machine name] -p [pid list]' instead", 'red'))
        elif args.option == 'killall':
            args.option = 'KILL'
            args.pidList = None
            args.command = None
            args.time = None
            print(colored("This method will be deprecated. Use 'spg KILL' instead", 'red'))
        elif args.option == 'killmachine':
            args.option = 'KILL'
            args.pidList = None
            args.command = None
            args.time = None
            args.machineNameList = [args.machineName]
            print(colored("This method will be deprecated. Use 'spg KILL -m [machine list]' instead", 'red'))
        elif args.option == 'killthis':
            args.option = 'KILL'
            args.pidList = None
            args.command = args.pattern
            args.time = None
            print(colored("This method will be deprecated. Use 'spg KILL -c [command]' instead", 'red'))
        elif args.option == 'killbefore':
            args.option = 'KILL'
            args.pidList = None
            args.command = None
            print(colored("This method will be deprecated. Use 'spg KILL -t [time]' instead", 'red'))
        return args

    @staticmethod
    def toSeconds(timeWindow: list[str]) -> int:
        """ Convert time window (str) to time window (seconds) """
        toSecond = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        try:
            return sum(int(time[:-1]) * toSecond[time[-1]] for time in timeWindow)
        except (KeyError, ValueError):
            print(colored('Invalid time window: ' + '  '.join(timeWindow), 'red'))
            print(colored('Run \'spg KILL -h\' for more help', 'red'))
            exit()

    @staticmethod
    def checkCMDOption(args: argparse.Namespace) -> argparse.Namespace:
        """
            Change option command from list of string to string
        """
        try:
            args.command = ' '.join(args.command)
        # When command is not given, do nothing
        except (AttributeError, TypeError):
            pass
        return args

    @staticmethod
    def checkJobOption(args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'job'
        """
        # When 'all' flag is true, set user name to None
        # Refer Machine.getRawProcess for the reason
        if args.all:
            args.userName = None
        return args

    def checkKILLOption(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'KILL'
        """
        # Double check if you really want to kill job
        question = self.getKillQuestion(args)
        self.killYesNo(question)

        # When specifying user name, you should be root
        if (args.userName != self.currentUser) and (self.currentUser != 'root'):
            self.parser.error(colored('When specifying user at kill option, you should be root', 'red'))

        # When pid list is given, you should specify machine name
        if (args.pidList) and (len(args.machineNameList) != 1):
            self.parser.error(colored('When killing job with pid list, you should specify machine name', 'red'))

        # When time is given, change it to integer
        if args.time:
            args.time = self.toSeconds(args.time)
        return args

    def checkRunsOption(self, args: argparse.Namespace) -> argparse.Namespace:
        """
            Check args for option 'Run'
        """
        # Only group name is specified
        if len(args.groupName) == 1:
            args.startEnd = None
            args.groupName = args.groupName[0]
        # Group name and their start, end numbers are specified
        elif len(args.groupName) == 3:
            args.startEnd = tuple([int(args.groupName[1]), int(args.groupName[2])])
            args.groupName = args.groupName[0]
        else:
            self.parser.error('When running several jobs, you should specifiy machine group and optional start/end number')
        return args

    def getArgs(self) -> argparse.Namespace:
        """
            Return arguments as namespace
        """
        args = self.parser.parse_args()

        # Redirect deprecated options
        colorama.init()
        args = self.redirectDeprecated(args)

        # option command
        args = self.checkCMDOption(args)

        # When main option is Job
        if args.option == 'job':
            args = self.checkJobOption(args)
        # When main option is KILL
        elif args.option == 'KILL':
            args = self.checkKILLOption(args)
        # When main option is Runs
        elif args.option == 'runs':
            args = self.checkRunsOption(args)

        return args

    ###################################### Basic Utility ######################################
    def addOptionalGroupArgument(self, parser: argparse.ArgumentParser) -> None:
        """
            Add optional argument of '-g' or '--groupList' to input parser
        """
        document = textwrap.dedent(f'''\
                                    List of target machine group name, seperated by space
                                    Currently available: {self.groupNameList}
                                    ''')
        parser.add_argument('-g', '--groupList',
                            nargs='+',
                            choices=self.groupNameList,
                            metavar='',
                            dest='groupNameList',
                            help=document)
        return None

    def addOptionalMachineArgument(self, parser: argparse.ArgumentParser) -> None:
        """
            Add optional argument of '-m' or '--machineList' to input parser
        """
        document = textwrap.dedent('''\
                                   List of target machine name, seperated by space
                                   ex) tenet1 / tenet1 tenet2
                                   ''')
        parser.add_argument('-m', '--machineList',
                            nargs='+',
                            metavar='',
                            dest='machineNameList',
                            help=document)
        return None

    def addOptionalUserArgument(self, parser: argparse.ArgumentParser) -> None:
        """
            Add optional argument of '-u' or '--user' to input parser
        """
        document = textwrap.dedent('''\
                                   Target user name
                                   If you are not root, you can only specify yourself (default)
                                   ''')
        parser.add_argument('-u', '--userName',
                            metavar='',
                            default=self.currentUser,
                            dest='userName',
                            help=document)

    def addPositionalGroupArgument(self, parser: argparse.ArgumentParser) -> None:
        """
            Add positional argument 'groupName' to input parser
        """
        parser.add_argument('groupName',
                            help='target machine group name')
        return None

    def addPositionalMachineArgument(self, parser: argparse.ArgumentParser) -> None:
        """
            Add positional argument 'machineName' to input parser
        """
        parser.add_argument('machineName',
                            help='target machine name')
        return None

    ####################################### Sub parsers #######################################
    def optionMachine(self) -> None:
        """
            deprecated
        """
        parser_machine = self.optionParser.add_parser('machine', help='Deprecated')
        self.addOptionalGroupArgument(parser_machine)
        self.addOptionalMachineArgument(parser_machine)
        return None

    def optionList(self) -> None:
        """
            Add 'list' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg machine (-g group list) (-m machine list)
                                   When group/machine are both given, group is ignored
                                   When machine is specified, there is no group summary
                                   ''')
        parser_list = self.optionParser.add_parser('list',
                                                   help='Print information of machines registered in SPG',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        self.addOptionalGroupArgument(parser_list)
        self.addOptionalMachineArgument(parser_list)
        return None

    def optionFree(self) -> None:
        """
            Add 'free' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg free (-g group list) (-m machine list)
                                   When group/machine are both given, group is ignored
                                   When machine is specified, there is no group summary
                                   ''')
        parser_free = self.optionParser.add_parser('free',
                                                   help='Print free informations of available machines',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        self.addOptionalGroupArgument(parser_free)
        self.addOptionalMachineArgument(parser_free)
        return None

    def optionJob(self) -> None:
        """
            Add 'job' option
            'group', 'machine', 'user', 'all' as optional argument
            When group/machine names are both given, group name is ignored
            When user/all are both given, user is ignored
        """
        document = textwrap.dedent('''\
                                   spg job (-a) (-g group list) (-m machine list) (-u user name)
                                   When group/machine are both given, group is ignored
                                   When all flag is set, user if ignored
                                   ''')
        parser_job = self.optionParser.add_parser('job',
                                                  help='print current status of jobs',
                                                  formatter_class=argparse.RawTextHelpFormatter,
                                                  usage=document)
        self.addOptionalGroupArgument(parser_job)
        self.addOptionalMachineArgument(parser_job)
        parser_job.add_argument('-a', '--all',
                                action='store_true',
                                help='When given, print jobs of all users')
        parser_job.add_argument('-u', '--userName',
                                metavar='',
                                default=self.currentUser,
                                dest='userName',
                                help='Target user name. Default: me')
        return None

    def optionAll(self) -> None:
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
        parser_all = self.optionParser.add_parser('all', help='Deprecated',
                                                  formatter_class=argparse.RawTextHelpFormatter,
                                                  usage=document)
        self.addOptionalGroupArgument(parser_all)
        self.addOptionalMachineArgument(parser_all)
        parser_all.add_argument('-u', '--userName',
                                metavar='',
                                default=None,
                                dest='userName',
                                help='Target user name')
        return None

    def optionMe(self) -> None:
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
        parser_me = self.optionParser.add_parser('me', help='Deprecated',
                                                 formatter_class=argparse.RawTextHelpFormatter,
                                                 usage=document)
        parser_me.add_argument('-u', '--userName',
                               metavar='',
                               default=self.currentUser,
                               dest='userName',
                               help='Target user name')
        self.addOptionalGroupArgument(parser_me)
        self.addOptionalMachineArgument(parser_me)

        return None

    def optionUser(self) -> None:
        """
            Add 'user' option
            'group' as optional argument
        """
        parser_user = self.optionParser.add_parser('user',
                                                   help='Print job count of users per machine group',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage='spg free (-g group list)')
        self.addOptionalGroupArgument(parser_user)
        return None

    def optionRun(self) -> None:
        """
            Add 'run' option
            'machine' as positional argument: necessary option
            'cmd' as positional argument with more than 1 inputs
        """
        document = textwrap.dedent('''\
                                   spg run [machine name] [program] (arguments)

                                   CAUTION!
                                   1. Invoke the job in the directory where you want the prrun
                                   2. Don't append \'&\' character at the tail of commands.
                                      spg will do it for you
                                   3. If you want to use redirection symbols < or >,
                                      type them in a quote, such as \'<\' or \'>\'
                                   ''')
        parser_run = self.optionParser.add_parser('run',
                                                  help='Run a job',
                                                  formatter_class=argparse.RawTextHelpFormatter,
                                                  usage=document)
        self.addPositionalMachineArgument(parser_run)
        parser_run.add_argument('command',
                                nargs='+',
                                help='command you want to run. [program] (arguments)')
        return None

    def optionRuns(self) -> None:
        """
            Add 'runs' option
            'group' as positional argument: necessary option
            'cmdFile' as positional argument
        """
        document = textwrap.dedent('''\
                                   spg runs [command file] [group name] (start end)

                                   CAUTION!
                                   1. Invoke the job in the directory where you want the prrun
                                   2. Don't append \'&\' character at the tail of commands.
                                      spg will do it for you
                                   3. If you want to use redirection symbols < or >,
                                      type them in a quote, such as \'<\' or \'>\'
                                   4. You can assign maximum of 50 jobs at one time.
                                   5. Executed commands will be dropped from input command file
                                   ''')
        parser_runs = self.optionParser.add_parser('runs',
                                                   help='Run several jobs',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        parser_runs.add_argument('cmdFile', help='Files containing commands. Sepearated by lines.')
        groupNameDocument = textwrap.dedent('''\
                                            Target machine group name with optinal start, end number
                                            When start and end number is given, only use machines between them
                                            ex) tenet 100 150: search tenet100~tenet150
                                            ''')
        parser_runs.add_argument('groupName',
                                 nargs='+',
                                 help=groupNameDocument)
        return None

    def optionKILL(self) -> None:
        """
            Add 'KILL' option
        """
        document = textwrap.dedent('''\
                                   spg kill (-m machine list) (-g group list) (-u user name) (-p pidList) (-c command) (-t time)
                                   CAUTION!!
                                   1. Jobs to be killed should satisfy all the given options.
                                   2. When given a multi-threaded job, this command kills it's session leader.
                                   3. When group/machine are both given, group is ignored.
                                   ''')
        parser_KILL = self.optionParser.add_parser('KILL',
                                                   help='kill job',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage=document)
        self.addOptionalUserArgument(parser_KILL)
        self.addOptionalMachineArgument(parser_KILL)
        self.addOptionalGroupArgument(parser_KILL)

        # Kill by pid
        pidDocument = textwrap.dedent('''\
                                      Kill my jobs with specific pid.
                                      When this option is given, you should specifiy single machine name.
                                      List of pid of target job, seperated by space.
                                      ''')
        parser_KILL.add_argument('-p', '--pidList',
                                 metavar='',
                                 nargs='+',
                                 dest='pidList',
                                 help=pidDocument)

        # Kill by command pattern
        commandDocument = textwrap.dedent('''\
                                          Kill my jobs whose commands includes pattern.
                                          List of words to search. Target command should have exact pattern.
                                          ''')
        parser_KILL.add_argument('-c', '--command',
                                 metavar='',
                                 nargs='+',
                                 dest='command',
                                 help=commandDocument)

        # Kill by time
        timeDocument = textwrap.dedent('''\
                                       Kill my jobs started less than given time.
                                       Time interval seperated by space.
                                       ex) 1w 5d 11h 50m 1s
                                       ''')
        parser_KILL.add_argument('-t', '--time',
                                 metavar='',
                                 nargs='+',
                                 dest='time',
                                 help=timeDocument)

    ######################################## Deprecate ########################################
    def optionKill(self) -> None:
        """
            Add 'kill' option
            'machine' as positional argument
            'pid list' as positional argument with more than 1 inputs
        """
        parser_kill = self.optionParser.add_parser('kill', help='Deprecated',
                                                   formatter_class=argparse.RawTextHelpFormatter,
                                                   usage='spg kill [machine name] [pid list]')
        self.addPositionalMachineArgument(parser_kill)
        parser_kill.add_argument('pidList',
                                 nargs='+',
                                 help='List of pid of target job. Seperated by space')
        return None

    def optionKillAll(self) -> None:
        """
            Add 'killall' option
            'group', 'machine' as optional argument
            When group/machine names are both given, group name is ignored
        """
        document = textwrap.dedent('''\
                                   spg killall (-g group list) (-m machine list) (-u user name)
                                   When group/machine are both given, group is ignored
                                   ''')
        parser_killall = self.optionParser.add_parser('killall', help='Deprecated',
                                                      formatter_class=argparse.RawTextHelpFormatter,
                                                      usage=document)
        self.addOptionalGroupArgument(parser_killall)
        self.addOptionalMachineArgument(parser_killall)
        self.addOptionalUserArgument(parser_killall)

        return None

    def optionKillMachine(self) -> None:
        """
            deprecated
        """
        parser_killmachine = self.optionParser.add_parser('killmachine', help='Deprecated')
        self.addPositionalMachineArgument(parser_killmachine)
        self.addOptionalUserArgument(parser_killmachine)
        return None

    def optionKillThis(self) -> None:
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
        parser_killthis = self.optionParser.add_parser('killthis', help='Deprecated',
                                                       formatter_class=argparse.RawTextHelpFormatter,
                                                       usage=document)
        parser_killthis.add_argument('pattern',
                                     nargs='+',
                                     help='List of words to search. Target command should have exact pattern')
        self.addOptionalGroupArgument(parser_killthis)
        self.addOptionalMachineArgument(parser_killthis)
        self.addOptionalUserArgument(parser_killthis)
        return None

    def optionKillBefore(self) -> None:
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
        parser_killbefore = self.optionParser.add_parser('killbefore', help='Deprecated',
                                                         formatter_class=argparse.RawTextHelpFormatter,
                                                         usage=document)
        parser_killbefore.add_argument('time',
                                       nargs='+',
                                       help='Time interval seperated by space. ex) 1w 5d 11h 50m 1s')
        self.addOptionalGroupArgument(parser_killbefore)
        self.addOptionalMachineArgument(parser_killbefore)
        self.addOptionalUserArgument(parser_killbefore)
        return None


if __name__ == "__main__":
    print("This is moudel Argument from SPG")
