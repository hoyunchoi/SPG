#! /usr/bin/python
import sys
import logging
import argparse
import subprocess
from threading import Thread
from collections import deque, Counter

from Machine import Machine
from Arguments import Arguments
from MachineGroup import MachineGroup
from Common import groupFileDict, defaultPath
from Handler import ErrorHandler, SuccessHandler, WarningHandler, getRunKillLogger


class SPG:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 runKillLogger: logging.Logger,
                 successHandler: SuccessHandler,
                 warnHandler: WarningHandler,
                 errHandler: ErrorHandler) -> None:
        self.defaultPath = defaultPath                      # Path of current location where spg is executed
        self.groupDict: dict[str, MachineGroup] = {}        # Dictionary of machine group with key of group name

        # Message handlers
        self.successHandler = successHandler                        # Standard output handler
        self.warnHandler = warnHandler                      # Warning handler
        self.errHandler = errHandler                        # Error handler

        # Print option
        self.silent: bool = None                            # Whether to print progressbar or not. Will be determined by arguments
        self.terminalWidth: int = None                      # Width of current terminal
        self.barWidth: int = None                           # Progressbar width.

        # Initialization
        for groupName, groupFile in groupFileDict.items():
            self.groupDict[groupName] = MachineGroup(groupName,
                                                     groupFile,
                                                     runKillLogger,
                                                     self.successHandler,
                                                     self.errHandler)
        try:
            self.terminalWidth = int(subprocess.check_output(['stty', 'size']).split()[-1])
        except subprocess.CalledProcessError:
            self.terminalWidth = sys.maxsize    # Not running at normal terminal: maximum terminal width

        # Super Short for list, kill
        self.superShortPrintWidth = 46
        self.superShortStrLine = self.getStrLine(self.superShortPrintWidth)

        # Short for free
        self.shortPrintWidth = 51
        self.shortStrLine = self.getStrLine(self.shortPrintWidth)

        # Long for job
        self.longPrintWidth = 104
        self.longStrLine = self.getStrLine(self.longPrintWidth)

        # Options
        self.option = {'list': self.list,
                       'free': self.free,
                       'job': self.job,
                       'user': self.user,
                       'run': self.run,
                       'runs': self.runs,
                       'KILL': self.KILL}

    ###################################### Basic Utility ######################################
    def __call__(self, args: argparse.Namespace) -> None:
        """
            Run functions according to the input argumetns
        """
        self.silent = args.silent
        self.option.get(args.option)(args)

    @staticmethod
    def getStrLine(width: int) -> str:
        return '+' + '=' * (width - 1)

    def findGroupFromName(self, groupName: str) -> MachineGroup:
        """
            Find group instance in groupList
        """
        group = self.groupDict.get(groupName)
        if group is None:
            self.errHandler.append(f'ERROR: No such machine group: {groupName}')
            exit()

        return group

    def findMachineFromName(self, machineName: str) -> Machine:
        """
            Find Machine instance in groupList
        """
        groupName = Machine.getGroupName(machineName)

        # Find group
        group = self.findGroupFromName(groupName)

        # Find machine
        machine = group.machineDict.get(machineName)
        if machine is None:
            self.errHandler.append(f'ERROR: No such machine: {machineName}')
            exit()

        return machine

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
                print(f'{machine}')
            print(self.superShortStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())
        for group in groupList:
            print(f'{group}')
            print(self.superShortStrLine)

        # Print total summary
        for group in groupList:
            print(f'| {group.name:<10} | total {group.nMachine:3d} machines & {group.nCore:4d} cores')
        print(self.superShortStrLine)
        return None

    def free(self, args: argparse.Namespace) -> None:
        """
            Print list of machine free information
        """
        # When machine list is specified
        if args.machineNameList:
            print(self.shortStrLine)
            machineList = self.scanJob_machine(args.machineNameList, userName=None, scanLevel=2)
            for machine in machineList:
                if machine.nFreeCore:
                    print(f'{machine:free}')
            print(self.shortStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

        # Start print
        print(self.shortStrLine)
        self.barWidth = min(self.shortPrintWidth, self.terminalWidth)
        self.scanJob(groupList, userName=None, scanLevel=2)
        if not self.silent:
            print(self.shortStrLine)
        print("| SPG Machine Information :: Free Cores")
        print(self.shortStrLine)

        # Print result
        for group in groupList:
            if group.nFreeMachine:
                print(f'{group:free}')
                print(self.shortStrLine)

        # Print summary
        for group in groupList:
            print(f'| {group.name:<10} | total {group.nFreeMachine:3d} machines & {group.nFreeCore:4d} cores')
        print(self.shortStrLine)
        return None

    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """
        # When machine list is specified
        if args.machineNameList:
            print(self.longStrLine)
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=2)
            for machine in machineList:
                if machine.nJob:
                    print(f'{machine:job}')
                    print(self.longStrLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

        # Start print
        print(self.longStrLine)
        self.barWidth = min(self.longPrintWidth, self.terminalWidth)
        self.scanJob(groupList, userName=args.userName, scanLevel=2)
        if not self.silent:
            print(self.longStrLine)
        print(f'| {"Machine":<10} | {"User":<15} | {"ST":<2} | {"PID":>7} | {"CPU(%)":>6} | {"MEM(%)":>6} | {"Memory":>6} | {"Time":>11} | {"Start":>5} | {"Command"}')
        print(self.longStrLine)

        # Print result
        for group in groupList:
            if group.nJob:
                group.strLine = self.longStrLine
                print(f'{group:job}')

        # Print summary
        for group in groupList:
            print(f'| {group.name:<10} | total {group.nJob:>3d} jobs')
        print(self.longStrLine)
        return None

    def user(self, args: argparse.Namespace) -> None:
        """
            Print job count of users per machine group
        """
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

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
        totalUserCount = Counter()      # Total number of jobs per user
        groupUserCountDict = dict()     # Number of jobs per user per group
        for group in groupList:
            groupUserCount = group.getUserCount()
            groupUserCountDict[group.name] = groupUserCount
            totalUserCount.update(groupUserCount)

        # Print result per user
        lineformat = '| {:<15} | {:>8} |' + '{:>8} |' * len(groupList)
        print(lineformat.format('User', 'total', *tuple([group.name for group in groupList])))
        print(strLine)
        for user, totCount in totalUserCount.items():
            print(lineformat.format(user, totCount,
                                    *tuple(groupUserCountDict[group.name].get(user, 0) for group in groupList)))
        print(strLine)

        # Print summary
        print(lineformat.format('total', sum(totalUserCount.values()),
                                *tuple(group.nJob for group in groupList)))
        print(strLine)

        return None

    def run(self, args: argparse.Namespace) -> None:
        """
            Run a job
        """
        # Find machine and scan current state
        machine = self.findMachineFromName(args.machineName)
        machine.scanJob(userName=None, scanLevel=2)

        # When no free core is detected, doule check the run command
        if machine.nFreeCore == 0:
            self.warnHandler.append(f'WARNING: {args.machineName} has no free core!')

        # Run a job
        machine.run(self.defaultPath, args.command)
        return None

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

        self.successHandler.append(f'\nRun {cmdNumBefore - cmdNumAfter} jobs')
        return None

    def KILL(self, args: argparse.Namespace) -> None:
        """
            kill job
        """
        # When machine list is specified
        if args.machineNameList:
            nKill = 0
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=1)
            for machine in machineList:
                machine.KILL(args)
                nKill += machine.nKill
            self.successHandler.append(f'\nKilled {nKill} jobs')
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

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
        for group in groupList:
            nKill += group.nKill
        self.successHandler.append(f'\nKilled {nKill} jobs')
        return None


def main():
    # Create message handlers: sequence of creation matters
    errHandler = ErrorHandler()
    warnHandler = WarningHandler()
    successHandler = SuccessHandler()

    # Define run, kill logger
    runKillLogger = getRunKillLogger()

    # Get arguments
    arguments = Arguments(warnHandler, errHandler)
    args = arguments.getArgs()

    # Run SPG according to arguments
    spg = SPG(runKillLogger, successHandler, warnHandler, errHandler)
    spg(args)


if __name__ == "__main__":
    main()
