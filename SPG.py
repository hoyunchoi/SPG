#! /usr/bin/python
import sys
import argparse
import colorama
import subprocess
from typing import Callable
from threading import Thread
from termcolor import colored
from collections import deque, Counter

from Common import groupFileDict, defaultPath
from Arguments import Arguments
from Machine import Machine
from MachineGroup import MachineGroup


class SPG:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        global groupFileDict, defaultPath
        self.defaultPath = defaultPath

        # Initialize machine group list
        self.groupList: list[MachineGroup] = [MachineGroup(groupName, groupFile)
                                              for groupName, groupFile in groupFileDict.items()]

        # Initialize error list
        self.scanErrList = []
        self.killErrList = []

        # Print option
        self.silent: bool = None
        self.barWidth: int = None
        try:
            self.terminalWidth = int(subprocess.check_output(['stty', 'size']).split()[-1])
        except subprocess.CalledProcessError:
            self.terminalWidth = sys.maxsize    # Not running at normal terminal: maximum terminal width

        # Super Short for list, kill
        self.superShortPrintWidth = 45
        self.superShortStrLine = self.getStrLine(self.superShortPrintWidth)

        # Short for free
        self.shortPrintWidth = 50
        self.shortStrLine = self.getStrLine(self.shortPrintWidth)

        # Long for job
        self.longPrintWidth = 104
        self.longStrLine = self.getStrLine(self.longPrintWidth)

    ###################################### Basic Utility ######################################
    def __call__(self, args: argparse.Namespace) -> None:
        """
            Run functions according to the input argumetns
        """
        self.silent = args.silent
        if args.option == 'list':
            self.list(args)
        elif args.option == 'free':
            self.free(args)
        elif args.option == 'job':
            self.job(args)
        elif args.option == 'user':
            self.user(args)
        elif args.option == 'run':
            self.run(args)
        elif args.option == 'runs':
            self.runs(args)
        elif args.option == 'KILL':
            self.KILL(args)

    @staticmethod
    def getStrLine(width: int) -> str:
        return '+' + '=' * (width - 1)

    def errReport(func: Callable) -> Callable:
        """
            Report the error after the functions
        """

        def decorator(self, *args, **kwargs) -> None:
            func(self, *args, **kwargs)

            # Report error
            colorama.init()
            for err in self.scanErrList + self.killErrList:
                print(colored(err, 'red'), file=sys.stderr)
            return None
        return decorator

    def findMachineFromName(self, machineName: str) -> Machine:
        """
            Find Machine instance in groupList
        """
        for group in self.groupList:
            for machine in group.machineList:
                if machine.name == machineName:
                    return machine

        # Can't find machine in spg list
        colorama.init()
        print(colored(f"ERROR: No such machine: {machineName}", 'red'))
        exit()

    def findGroupFromName(self, groupName: str) -> MachineGroup:
        """
            Find group instance in groupList
        """
        for group in self.groupList:
            if group.name == groupName:
                return group

        # Can't find group in spg list
        colorama.init()
        print(colored(f"ERROR: No such machine group: {groupName}", 'red'))
        exit()

    ############################## Scan Job Information and Save ##############################
    def scanJob(self, groupList: list[MachineGroup],
                userName: str,
                scanLevel: int) -> None:
        """
            Scan running jobs
            Args
                targetGroupList: list of group to scan
                userName: whose job to scan
                scanLevel: refer Job.isImportant
        """
        # Scan job without tqdm bar
        if self.silent:
            threadList = [Thread(target=group.scanJob_silent, args=(userName, scanLevel)) for group in groupList]
        # Scan job with tqdm bar
        else:
            for group in groupList:
                group.barWidth = self.barWidth
            threadList = [Thread(target=group.scanJob, args=(userName, scanLevel)) for group in groupList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()
        for group in groupList:
            self.scanErrList += group.scanErrList
        return None

    def scanJob_machine(self, machineNameList: list[str],
                        userName: str,
                        scanLevel: int) -> list[Machine]:
        """
            Scan running jobs
            Args
                targetGroupList: list of machine names to scan
                userName: Refer Machine.scanJob
                scanLevel: refer Job.isImportant
        """
        machineList = [self.findMachineFromName(machineName) for machineName in machineNameList]
        threadList = [Thread(target=machine.scanJob, args=(userName, scanLevel)) for machine in machineList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()
        return machineList

    ####################################### SPG command #######################################
    def list(self, args: argparse.Namespace) -> None:
        """
            Print information of machines registered in SPG
        """
        # Set width
        print(self.superShortStrLine)
        print("| SPG Machine Information :: List")
        print(self.superShortStrLine)

        # When machine list is specified
        if args.machineNameList:
            for machineName in args.machineNameList:
                machine = self.findMachineFromName(machineName)
                print(machine.getInfoLine())
            print(self.superShortStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList
        for group in groupList:
            if group.nMachine:
                for machineInfoLine in group.getInfoLineList():
                    print(machineInfoLine)
                print(self.superShortStrLine)

        # Print total summary
        for group in groupList:
            if group.nMachine:
                print('| {:<10} | total {:3d} machines & {:3d} cores'.format(group.name, group.nMachine, group.nCore))
        print(self.superShortStrLine)
        return None

    @errReport
    def free(self, args: argparse.Namespace) -> None:
        """
            Print list of machine free information
        """
        # When machine list is specified
        if args.machineNameList:
            print(self.shortStrLine)
            machineList = self.scanJob_machine(args.machineNameList, userName=None, scanLevel=2)
            for machine in machineList:
                self.scanErrList += machine.scanErrList
                if machine.nFreeCore:
                    print(machine.getFreeInfoLine())
            print(self.shortStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Start print
        print(self.shortStrLine)
        if not self.silent:
            self.barWidth = min(self.shortPrintWidth, self.terminalWidth)
        self.scanJob(groupList, userName=None, scanLevel=2)

        # Print by machine
        if not self.silent:
            print(self.shortStrLine)
        print("| SPG Machine Information :: Free Cores")
        print(self.shortStrLine)
        for group in groupList:
            if group.nFreeMachine:
                for machineFreeInfoLine in group.getFreeInfoLineList():
                    print(machineFreeInfoLine)
                print(self.shortStrLine)

        # Print summary
        for group in groupList:
            if group.nMachine:
                print('| {:<10} | total {:3d} machines & {:3d} cores'.format(group.name, group.nFreeMachine, group.nFreeCore))
        print(self.shortStrLine)
        return None

    @errReport
    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """
        # When machine list is specified
        if args.machineNameList:
            print(self.longStrLine)
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=2)
            for machine in machineList:
                self.scanErrList += machine.scanErrList
                if machine.nJob:
                    print(machine.getJobLine(), end='')
                    print(self.longStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Set width
        if not self.silent:
            self.barWidth = min(self.longPrintWidth, self.terminalWidth)

        # Start print
        print(self.longStrLine)
        self.scanJob(groupList, userName=args.userName, scanLevel=2)
        if not self.silent:
            print(self.longStrLine)
        print('| {:<10} | {:<15} | {:<2} | {:>7} | {:>6} | {:>6} | {:>6} | {:>11} | {:>5} | {}'.format('Machine', "User", 'ST', 'PID', 'CPU(%)', 'MEM(%)', 'MEMORY', 'Time', 'Start', 'Command'))
        print(self.longStrLine)

        # Print result
        for group in groupList:
            if group.nJob:
                for jobLine in group.getJobLineList(self.longStrLine):
                    print(jobLine)

        # Print summary
        for group in groupList:
            print('| {:<10} | total {:>3d} jobs'.format(group.name, group.nJob))
        print(self.longStrLine)
        return None

    @errReport
    def user(self, args: argparse.Namespace) -> None:
        """
            Print job count of users per machine group
        """
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Set width
        strLine = '+' + '=' * (29 + 10 * (len(groupList)))
        if not self.silent:
            self.barWidth = min(len(strLine), self.terminalWidth)

        # Scanning
        print(strLine)
        self.scanJob(groupList, userName=None, scanLevel=2)
        if not self.silent:
            print(strLine)

        # Get user count
        userCount = Counter()
        groupUserCountDict = {}
        for group in groupList:
            if group.nJob:
                groupUserCount = group.getUserCount()
                groupUserCountDict[group.name] = groupUserCount
                userCount += groupUserCount

        # Print result
        lineformat = '| {:<15} | {:>8} |' + '{:>8} |' * len(groupList)
        print(lineformat.format('User', 'total', *tuple([group.name for group in groupList])))
        print(strLine)
        for user, totCount in userCount.items():
            count = [None] * len(groupList)
            for i, group in enumerate(groupList):
                try:
                    count[i] = groupUserCountDict[group.name][user]
                except KeyError:
                    count[i] = 0
                count.append(groupUserCount.get(user, 0))
            print(lineformat.format(user, totCount, *tuple(count)))
        print(strLine)

        # Print summary
        nJobList = [group.nJob for group in groupList]
        print(lineformat.format('total', sum(nJobList), *tuple(nJobList)))
        print(strLine)

        return None

    @errReport
    def run(self, args: argparse.Namespace) -> None:
        """
            Run a job
        """
        machine = self.findMachineFromName(args.machineName)
        machine.run(self.defaultPath, args.command)

        return None

    @errReport
    def runs(self, args: argparse.Namespace, maxCalls: int = 50) -> None:
        """
            Run several jobs
        """
        # Handle arguments
        group = self.findGroupFromName(args.groupName)
        with open(args.cmdFile, 'r') as f:
            cmdQueue = f.read().splitlines()
        cmdQueue = deque(cmdQueue)
        cmdNumBefore = len(cmdQueue)

        # Scanning
        if not self.silent:
            self.barWidth = min(self.shortPrintWidth, self.terminalWidth)
            print(self.shortStrLine)
        self.scanJob([group], userName=None, scanLevel=2)
        if not args.silent:
            print(self.shortStrLine)

        # Run jobs
        cmdQueue = group.runs(self.defaultPath, cmdQueue, maxCalls, args.startEnd)
        cmdNumAfter = len(cmdQueue)

        # Remove the input file and re-write with remaining command queue
        subprocess.run(f'rm {args.cmdFile}', shell=True)
        with open(args.cmdFile, 'w') as f:
            f.write('\n'.join(str(cmd) for cmd in cmdQueue))
        print(f"Run {cmdNumBefore - cmdNumAfter} jobs")
        return None

    @errReport
    def KILL(self, args: argparse.Namespace) -> None:
        """
            kill job
        """
        # When machine list is specified
        if args.machineNameList:
            nKill = 0
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=1)
            for machine in machineList:
                nKill += machine.KILL(args)
                self.killErrList += machine.killErrList
            print(f'\nKilled {nKill} jobs')
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Scanning
        if not self.silent:
            self.barWidth = min(self.superShortPrintWidth, self.terminalWidth)
            print(self.superShortStrLine)
        self.scanJob(groupList, args.userName, scanLevel=1)
        if not self.silent:
            print(self.superShortStrLine)

        # Kill jobs
        threadList = [Thread(target=group.KILL, args=(args,)) for group in groupList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Summarize the kill result
        nKill = 0
        self.killErrList = []
        for group in groupList:
            nKill += group.nKill
            self.killErrList += group.killErrList
        print(f'\nKilled {nKill} jobs')
        return None

    ######################################## Deprecate ########################################
    def machine(self, args: argparse.Namespace) -> None:
        """
            deprecated
        """
        self.list(args)
        colorama.init()
        print(colored('This option will be deprecated. Use \'spg list\' instead.', 'red'))

    @errReport
    def me(self, args: argparse.Namespace) -> None:
        """
            Print current status of my jobs
        """
        # When machine list is specified
        if args.machineNameList:
            machineList = self.scanUserJob_machine(args.machineNameList, args.userName, 2)
            for machine in machineList:
                self.scanErrList += machine.scanErrList
                if machine.nUserJob:
                    print(machine.getUserJobLine(), end='')
                    print(self.longStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Set width
        print(self.longStrLine)
        if not self.silent:
            self.barWidth = min(self.longPrintWidth, self.terminalWidth)
        self.scanUserJob(groupList, args.userName, scanLevel=2)

        # Print result
        if not self.silent:
            print(self.longStrLine)
        print('| {:<10} | {:<15} | {:<2} | {:>7} | {:>6} | {:>6} | {:>6} | {:>11} | {:>5} | {}'.format('Machine', "User", 'ST', 'PID', 'CPU(%)', 'MEM(%)', 'MEMORY', 'Time', 'Start', 'Command'))
        print(self.longStrLine)

        for group in groupList:
            if group.nUserJob:
                for userJobLine in group.getUserJobLineList(self.longStrLine):
                    print(userJobLine)

        # Print summary
        for group in groupList:
            if group.nMachine:
                print('| {:<10} | total {:>3d} jobs'.format(group.name, group.nUserJob))
        print(self.longStrLine)
        return None

    @errReport
    def all(self, args: argparse.Namespace) -> None:
        """
            Print current status of all running jobs
        """
        # When machine list is specified
        if args.machineNameList:
            print(self.longStrLine)
            machineList = self.scanAllJob_machine(args.machineNameList, 2)
            for machine in machineList:
                self.scanErrList += machine.scanErrList
                if machine.nAllJob:
                    print(machine.getAllJobLine(), end='')
                    print(self.longStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Start print
        print(self.longStrLine)
        if not self.silent:
            self.barWidth = min(self.longPrintWidth, self.terminalWidth)
        self.scanAllJob(groupList, scanLevel=2)

        # Print by machine
        if not self.silent:
            print(self.longStrLine)
        print('| {:<10} | {:<15} | {:<2} | {:>7} | {:>6} | {:>6} | {:>6} | {:>11} | {:>5} | {}'.format('Machine', "User", 'ST', 'PID', 'CPU(%)', 'MEM(%)', 'MEMORY', 'Time', 'Start', 'Command'))
        print(self.longStrLine)
        for group in groupList:
            if group.nAllJob:
                for allJobLine in group.getAllJobLineList(self.longStrLine):
                    print(allJobLine)

        # Print summary
        for group in groupList:
            if group.nMachine:
                print('| {:<10} | total {:>3d} jobs'.format(group.name, group.nAllJob))
        print(self.longStrLine)
        return None

    @errReport
    def kill(self, args: argparse.Namespace) -> None:
        """
            deprecated
        """
        machine = self.findMachineFromName(args.machineName)
        machine.scanUserJob(args.userName, scanLevel=1)
        for pid in args.pidList:
            machine.kill(pid)
        self.killErrList += machine.killErrList
        return None

    @errReport
    def killAll(self, args: argparse.Namespace) -> None:
        """
            deprecated
        """
        # When machine list is specified
        if args.machineNameList:
            nKill = 0
            machineList = self.scanUserJob_machine(args.machineNameList, args.userName, 1)
            for machine in machineList:
                nKill += machine.killAll()
                self.killErrList += machine.killErrList
            print(f'\nKilled {nKill} jobs')
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Scanning
        if not self.silent:
            self.barWidth = min(self.shortPrintWidth, self.terminalWidth)
            print(self.shortStrLine)
        self.scanUserJob(groupList, args.userName, scanLevel=1)
        if not self.silent:
            print(self.shortStrLine)

        # Kill jobs
        nKill = 0
        for group in groupList:
            nKill += group.killAll()
            self.killErrList += group.killErrList
        print(f'\nKilled {nKill} jobs')
        return None

    @errReport
    def killMachine(self, args: argparse.Namespace) -> None:
        """
            deprecated
        """
        self.killAll_machine([args.machineName])

        colorama.init()
        print(colored('This option will be deprecated. Use \'spg killall -m [machine name]\' instead.', 'red'))

    @errReport
    def killThis(self, args: argparse.Namespace) -> None:
        """
            deprecated
        """
        # When machine list is specified
        if args.machineNameList:
            nKill = 0
            machineList = self.scanUserJob_machine(args.machineNameList, args.userName, 1)
            for machine in machineList:
                nKill += machine.killThis(args.pattern)
                self.killErrList += machine.killErrList
            print(f'\nKilled {nKill} jobs')
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Scanning
        if not self.silent:
            self.barWidth = min(self.shortPrintWidth, self.terminalWidth)
            print(self.shortStrLine)
        self.scanUserJob(groupList, args.userName, scanLevel=1)
        if not self.silent:
            print(self.shortStrLine)

        # Kill jobs
        nKill = 0
        for group in groupList:
            nKill += group.killThis(args.pattern)
            self.killErrList += group.killErrList
        print(f'\nKilled {nKill} jobs')
        return None

    @errReport
    def killBefore(self, args: argparse.Namespace) -> None:
        """
            deprecated
        """
        def toSeconds(timeWindow: list[str]) -> int:
            """ Convert time window (str) to time window (seconds) """
            toSecond = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
            try:
                return sum(int(time[:-1]) * toSecond[time[-1]] for time in timeWindow)
            except (KeyError, ValueError):
                colorama.init()
                print(colored('Invalid time window: ' + '  '.join(timeWindow), 'red'))
                print(colored('print \'spg killbefore -h\' for more help', 'red'))
                exit()
        timeWindow = toSeconds(args.time)

        # When machine list is specified
        if args.machineNameList:
            nKill = 0
            machineList = self.scanUserJob_machine(args.machineNameList, args.userName, 1)
            for machine in machineList:
                nKill += machine.killBefore(timeWindow)
                self.killErrList += machine.killErrList
            print(f'\nKilled {nKill} jobs')
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = self.groupList

        # Scanning
        if not self.silent:
            self.barWidth = min(self.longPrintWidth, self.terminalWidth)
            print(self.shortStrLine)
        self.scanUserJob(groupList, args.userName, scanLevel=1)
        if not self.silent:
            print(self.shortStrLine)

        # Kill jobs
        nKill = 0
        for group in self.groupList:
            nKill += group.killBefore(timeWindow)
            self.killErrList += group.killErrList
        print(f'\nKilled {nKill} jobs')
        return None


def main():
    # Get arguments
    arguments = Arguments()
    args = arguments.getArgs()

    # Run SPG according to arguments
    spg = SPG()
    spg(args)


if __name__ == "__main__":
    main()
