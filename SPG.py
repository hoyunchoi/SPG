#! /usr/bin/python
import argparse
import subprocess
from threading import Thread
from typing import Callable, Optional
from collections import deque, Counter

from Group import Group
from Machine import Machine
from Arguments import Arguments

from Default import default
from IO import printer, messageHandler


class SPG:
    # I know global variable is not optimal...
    global default, messageHandler, printer

    """ SPG """

    def __init__(self) -> None:
        self.groupDict: dict[str, Group] = {}    # Dictionary of machine group with key of group name

        # Initialize group dictionary
        for groupName, groupFile in default.getGroupFileDict().items():
            self.groupDict[groupName] = Group(groupName, groupFile)

        # Options
        self.option = {'list': self.list,
                       'free': self.free,
                       'job': self.job,
                       'user': self.user,
                       'run': self.run,
                       'runs': self.runs,
                       'KILL': self.KILL}

        # Print variables
        self.barWidth = 40
        self.strLine = self.getStrLine(self.barWidth)
        self.firstLine: str = ''

    ###################################### Basic Utility ######################################
    def __call__(self, args: argparse.Namespace) -> None:
        """
            Run functions according to the input argumetns
        """
        # Setup printer
        printer.initialize(args)

        # Run SPG
        self.option.get(args.option)(args)

    @staticmethod
    def getStrLine(width: int) -> str:
        return '+' + '=' * (width - 1)

    def findGroupFromName(self, groupName: str) -> Group:
        """
            Find group instance in groupList
        """
        group = self.groupDict.get(groupName)
        if group is None:
            messageHandler.error(f'ERROR: No such machine group: {groupName}')
            exit()

        return group

    def findGroupListFromGroupNameList(self, groupNameList: Optional[list[str]]) -> list[Group]:
        """
            Find list of group instance from group name list
        """
        if groupNameList is None:
            return list(self.groupDict.values())
        else:
            return [self.findGroupFromName(groupName) for groupName in groupNameList]

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
            messageHandler.error(f'ERROR: No such machine: {machineName}')
            exit()

        return machine

    def findGroupListFromMachineNameList(self, machineNameList: list[str]) -> list[Group]:
        """
            update group dict corresponding to input machine name list
            return list of updated Group instances
        """
        # key: groupName, value: list of Machines at group
        machineListPerGroup: dict[str, list[Machine]] = {}

        # Store information of machine name list
        for machineName in machineNameList:
            machine = self.findMachineFromName(machineName)
            groupName = Machine.getGroupName(machineName)
            # Group name already appeared before: append to the list
            if groupName in machineListPerGroup:
                machineListPerGroup[groupName].append(machine)
            # Group name appeared first time: make new list
            else:
                machineListPerGroup[groupName] = [machine]

        # update group dict
        for groupName, machineList in machineListPerGroup.items():
            self.groupDict[groupName].machineDict = {machine.name: machine for machine in machineList}

        # Return list of updated group list
        return self.findGroupListFromGroupNameList(list(machineListPerGroup))

    def decorateBar(func: Callable) -> Callable:
        """
            Decorate tqdm bar with proper length of strLine
            If printer.barWidth is none, tqdm bar is not printed.
            Therefore, do not print decoration line
        """

        def decorator(self, *args, **kwargs) -> None:
            if printer.barWidth is not None:
                printer.print()

            # Main function
            func(self, *args, **kwargs)

        return decorator

    ############################## Scan Job Information and Save ##############################
    @decorateBar
    def scanJob(self,
                groupList: list[Group],
                userName: str,
                scanLevel: int) -> None:
        """
            Scan running jobs
            Args
                targetGroupList: list of group to scan
                userName: whose job to scan
                scanLevel: refer Job.isImportant
        """
        for group in groupList:
            group.barWidth = printer.barWidth

        # Scan job for every groups in group list
        threadList = [Thread(target=group.scanJob, args=(userName, scanLevel))
                      for group in groupList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()
        return None

    ####################################### SPG command #######################################
    def list(self, args: argparse.Namespace) -> None:
        """
            Print information of machines registered in SPG
        """
        # When machine list is not specified
        if args.machineNameList is None:
            groupList = self.findGroupListFromGroupNameList(args.groupNameList)
        # When machine list is specified
        else:
            groupList = self.findGroupListFromMachineNameList(args.machineNameList)

        # ----------------------- Print -----------------------
        # first section
        printer.firstSection()

        # main section
        for group in groupList:
            printer.print(f'{group}')
            printer.print()

        # summary
        for group in groupList:
            printer.printSummaryFormat(group.name, str(group.nMachine), str(group.nUnit))
        printer.print()

        return None

    def free(self, args: argparse.Namespace) -> None:
        """
            Print list of machine free information
        """
        # When machine list is not specified
        if args.machineNameList is None:
            groupList = self.findGroupListFromGroupNameList(args.groupNameList)
        # When machine list is specified
        else:
            groupList = self.findGroupListFromMachineNameList(args.machineNameList)

        # Scanning
        self.scanJob(groupList, userName=None, scanLevel=2)

        # ----------------------- Print -----------------------
        # First section
        printer.firstSection()
        # main section
        for group in groupList:
            if group.nFreeMachine:
                printer.print(f'{group:free}')
                printer.print()
        # summary
        for group in groupList:
            printer.printSummaryFormat(group.name, str(group.nFreeMachine), str(group.nFreeUnit))
        printer.print()

        return None

    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """
        # When machine list is not specified
        if args.machineNameList is None:
            groupList = self.findGroupListFromGroupNameList(args.groupNameList)
        # When machine list is specified
        else:
            groupList = self.findGroupListFromMachineNameList(args.machineNameList)

        # Scanning
        self.scanJob(groupList, userName=args.userName, scanLevel=2)

        # ----------------------- Print -----------------------
        # First section
        printer.firstSection()
        # main section
        for group in groupList:
            if group.nJob:
                group.strLine = printer.strLine
                printer.print(f'{group:job}')

        # Print summary
        for group in groupList:
            printer.printSummaryFormat(group.name, str(group.nJob))
        printer.print()
        return None

    def user(self, args: argparse.Namespace) -> None:
        """
            Print job count of users per machine group
        """
        # List of machine group
        groupList = self.findGroupListFromGroupNameList(args.groupNameList)

        # Scanning
        self.scanJob(groupList, userName=None, scanLevel=2)

        # Get user count
        totalUserCount = Counter()      # Total number of jobs per user
        groupUserCountDict = dict()     # Number of jobs per user per group
        for group in groupList:
            groupUserCount = group.getUserCount()
            groupUserCountDict[group.name] = groupUserCount
            totalUserCount.update(groupUserCount)

        # ----------------------- Print -----------------------
        # First section
        printer.firstSection()

        # main section
        for user, totCount in totalUserCount.items():
            printer.printLineFormat(user,
                                    totCount,
                                    *tuple(groupUserCountDict[group.name].get(user, 0) for group in groupList))
        printer.print()

        # summary
        printer.printSummaryFormat('total',
                                   sum(totalUserCount.values()),
                                   *tuple(group.nJob for group in groupList))
        printer.print()
        return None

    def run(self, args: argparse.Namespace) -> None:
        """
            Run a job
        """
        # Find machine and scan current state
        machine = self.findMachineFromName(args.machineName)
        machine.scanJob(userName=None, scanLevel=2)

        # When no free core is detected, doule check the run command
        if not machine.nFreeUnit:
            messageHandler.warning(f'WARNING: {args.machineName} has no free core!')

        # Run a job
        machine.run(default.path, args.command)
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
        self.scanJob([group], userName=None, scanLevel=2)
        if not args.silent:
            printer.print()

        # Run jobs
        cmdQueue = group.runs(default.path, cmdQueue, maxCalls, args.startEnd)
        cmdNumAfter = len(cmdQueue)

        # Remove the input file and re-write with remaining command queue
        subprocess.run(f'rm {args.cmdFile}', shell=True)
        with open(args.cmdFile, 'w') as f:
            f.write('\n'.join(str(cmd) for cmd in cmdQueue))

        messageHandler.success(f'\nRun {cmdNumBefore - cmdNumAfter} jobs')
        return None

    def KILL(self, args: argparse.Namespace) -> None:
        """
            kill job
        """
        # When machine list is not specified
        if args.machineNameList is None:
            groupList = self.findGroupListFromGroupNameList(args.groupNameList)
        # When machine list is specified
        else:
            groupList = self.findGroupListFromMachineNameList(args.machineNameList)

        # Scanning
        self.scanJob(groupList, args.userName, scanLevel=1)
        if not args.silent:
            printer.print()

        # Kill jobs
        threadList = [Thread(target=group.KILL, args=(args,)) for group in groupList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Summarize the kill result
        nKill = sum(group.nKill for group in groupList)
        messageHandler.success(f'\nKilled {nKill} jobs')
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
