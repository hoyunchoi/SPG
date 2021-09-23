#! /usr/bin/python
import tqdm
import argparse
import subprocess
from typing import Callable, Optional
from threading import Thread
from collections import deque, Counter

from Job import Job
from Group import Group
from Machine import Machine
from Arguments import Arguments

from Default import default
from Handler import messageHandler


class SPG:
    # I know global variable is not optimal...
    global default, messageHandler

    """ SPG """
    groupInfoFormat: str = '| {:<10} | total {:>4} machines & {:>4} units'
    groupJobInfoFormat: str = '| {:<10} | total {:>4} jobs'

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
        # self.printer = PrintHandler()
        self.barWidth = 40
        self.strLine = self.getStrLine(self.barWidth)
        self.firstLine: str = ''

    ###################################### Basic Utility ######################################
    def __call__(self, args: argparse.Namespace) -> None:
        """
            Run functions according to the input argumetns
        """
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

    def findGroupListFromName(self, groupNameList: Optional[list[str]]) -> list[Group]:
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

    def findMachineListFromName(self, machineNameList: list[str]) -> list[Machine]:
        """
            Find list of machine instance from machine name list
        """
        return [self.findMachineFromName(machineName) for machineName in machineNameList]

    def decorateBar(func: Callable) -> Callable:
        """
            Decorate tqdm bar with proper length of strLine
            If self.barWidth is none, tqdm bar is not printed.
            Therefore, do not print decoration line
        """

        def decorator(self, *args, **kwargs) -> None:
            if self.barWidth is not None:
                tqdm.tqdm.write(self.strLine)

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
            group.barWidth = self.barWidth

        # Scan job for every groups in group list
        threadList = [Thread(target=group.scanJob, args=(userName, scanLevel))
                      for group in groupList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()
        return None

    def scanJob_machine(self,
                        machineNameList: list[str],
                        userName: str,
                        scanLevel: int) -> list[Machine]:
        """
            Scan running jobs
            Args
                targetGroupList: list of machine names to scan
                userName: Refer Machine.scanJob
                scanLevel: refer Job.isImportant
        """
        machineList = [self.findMachineFromName(machineName)
                       for machineName in machineNameList]
        threadList = [Thread(target=machine.scanJob, args=(userName, scanLevel))
                      for machine in machineList]
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
        # self.printer.columnLine = Machine.infoFormat.format('Machine', 'ComputeUnit', 'tot units', 'mem')
        self.firstLine = Machine.infoFormat.format('Machine', 'ComputeUnit', 'tot units', 'mem')
        self.strLine = self.getStrLine(len(self.firstLine))

        # First section
        # self.printer.printFirstSection()
        tqdm.tqdm.write(self.strLine)
        tqdm.tqdm.write(self.firstLine)
        tqdm.tqdm.write(self.strLine)

        # When machine list is specified
        if args.machineNameList:
            machineList = self.findMachineListFromName(args.machineNameList)
            # self.printer.list_machine(machineList)
            tqdm.tqdm.write('\n'.join(f'{machine}' for machine in machineList))
            tqdm.tqdm.write(self.strLine)
            return None

        # When machine list is not specified
        groupList = self.findGroupListFromName(args.groupNameList)
        # self.printer.list_group(groupList)
        tqdm.tqdm.write(f'\n{self.strLine}\n'.join(f'{group}'
                                                   for group in groupList))

        # Print total summary
        tqdm.tqdm.write(self.strLine)
        tqdm.tqdm.write('\n'.join(SPG.groupInfoFormat.format(group.name,
                                                             str(group.nMachine),
                                                             str(group.nUnit))
                                  for group in groupList))
        tqdm.tqdm.write(self.strLine)
        return None

    def free(self, args: argparse.Namespace) -> None:
        """
            Print list of machine free information
        """
        self.firstLine = Machine.freeInfoFormat.format('Machine', 'ComputeUnit', 'free units', 'free mem')
        self.strLine = self.getStrLine(len(self.firstLine))

        # When machine list is specified
        if args.machineNameList:
            # First section
            tqdm.tqdm.write(self.strLine)
            tqdm.tqdm.write(self.firstLine)
            tqdm.tqdm.write(self.strLine)

            # Scan machines
            machineList = self.scanJob_machine(args.machineNameList, userName=None, scanLevel=2)

            # Print result
            tqdm.tqdm.write('\n'.join(f'{machine:free}'
                                      for machine in machineList
                                      if machine.nFreeUnit))
            tqdm.tqdm.write(self.strLine)
            return None

        # When machine list is not specified
        groupList = (list(self.groupDict.values())
                     if args.groupNameList is None
                     else [self.findGroupFromName(groupName) for groupName in args.groupNameList])
        # Scan
        self.barWidth = None if args.silent else min(len(self.firstLine), default.terminalWidth)
        self.scanJob(groupList, userName=None, scanLevel=2)

        # First section
        tqdm.tqdm.write(self.strLine)
        tqdm.tqdm.write(self.firstLine)
        tqdm.tqdm.write(self.strLine)

        # Print result
        tqdm.tqdm.write(f'\n{self.strLine}\n'.join(f'{group:free}'
                                                   for group in groupList
                                                   if group.nFreeMachine))
        tqdm.tqdm.write(self.strLine)

        # Print summary
        tqdm.tqdm.write('\n'.join(SPG.groupInfoFormat.format(group.name,
                                                             str(group.nFreeMachine),
                                                             str(group.nFreeUnit))
                                  for group in groupList))
        tqdm.tqdm.write(self.strLine)
        return None

    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """
        self.firstLine = Job.infoFormat.format('Machine', 'User', 'ST', 'PID', 'CPU(%)', 'MEM(%)', 'Memory', 'Time', 'Start', 'Command')
        self.strLine = self.getStrLine(len(self.firstLine))

        # When machine list is specified
        if args.machineNameList:
            # First section
            tqdm.tqdm.write(self.strLine)
            tqdm.tqdm.write(self.firstLine)
            tqdm.tqdm.write(self.strLine)

            # Scan machine list
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=2)

            # Print result
            tqdm.tqdm.write(f'\n{self.strLine}\n'.join(f'{machine:job}'
                            for machine in machineList
                            if machine.nJob))
            tqdm.tqdm.write(self.strLine)
            return None

        # When machine list is not specified
        groupList = (list(self.groupDict.values())
                     if args.groupNameList is None
                     else [self.findGroupFromName(groupName) for groupName in args.groupNameList])
        for group in groupList:
            group.strLine = self.strLine

        # scan
        self.barWidth = None if args.silent else min(len(self.firstLine), default.terminalWidth)
        self.scanJob(groupList, userName=args.userName, scanLevel=2)

        # First section
        tqdm.tqdm.write(self.strLine)
        tqdm.tqdm.write(self.firstLine)
        tqdm.tqdm.write(self.strLine)

        # Print result
        tqdm.tqdm.write('\n'.join(f'{group:job}'
                                  for group in groupList
                                  if group.nJob))

        # Print summary
        tqdm.tqdm.write('\n'.join(SPG.groupJobInfoFormat.format(group.name, str(group.nJob))
                                  for group in groupList))
        tqdm.tqdm.write(self.strLine)
        return None

    def user(self, args: argparse.Namespace) -> None:
        """
            Print job count of users per machine group
        """
        # List of machine group
        groupList = (list(self.groupDict.values())
                     if args.groupNameList is None
                     else [self.findGroupFromName(groupName) for groupName in args.groupNameList])

        lineformat = '| {:<15} | {:>8} |' + '{:>8} |' * len(groupList)
        self.firstLine = lineformat.format('User', 'total', *tuple(group.name for group in groupList))
        self.strLine = self.getStrLine(len(self.firstLine))

        # Scanning
        self.barWidth = None if args.silent else min(len(self.firstLine), default.terminalWidth)
        self.scanJob(groupList, userName=None, scanLevel=2)

        # Get user count
        totalUserCount = Counter()      # Total number of jobs per user
        groupUserCountDict = dict()     # Number of jobs per user per group
        for group in groupList:
            groupUserCount = group.getUserCount()
            groupUserCountDict[group.name] = groupUserCount
            totalUserCount.update(groupUserCount)

        # First section
        tqdm.tqdm.write(self.strLine)
        tqdm.tqdm.write(self.firstLine)
        tqdm.tqdm.write(self.strLine)

        # Print result per user
        for user, totCount in totalUserCount.items():
            tqdm.tqdm.write(lineformat.format(user, totCount,
                                              *tuple(groupUserCountDict[group.name].get(user, 0)
                                                     for group in groupList)))
        tqdm.tqdm.write(self.strLine)

        # Print summary
        tqdm.tqdm.write(lineformat.format('total', sum(totalUserCount.values()),
                                          *tuple(group.nJob for group in groupList)))
        tqdm.tqdm.write(self.strLine)

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
        self.barWidth = None if args.silent else min(self.barWidth, default.terminalWidth)
        self.scanJob([group], userName=None, scanLevel=2)
        if not args.silent:
            tqdm.tqdm.write(self.strLine)

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
        # When machine list is specified
        if args.machineNameList:
            nKill = 0
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=1)
            for machine in machineList:
                machine.KILL(args)
                nKill += machine.nKill
            messageHandler.success(f'\nKilled {nKill} jobs')
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

        # Scanning
        self.barWidth = None if args.silent else min(self.barWidth, default.terminalWidth)
        self.scanJob(groupList, args.userName, scanLevel=1)
        if not args.silent:
            tqdm.tqdm.write(self.strLine)

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
        messageHandler.success(f'\nKilled {nKill} jobs')
        return None


# class PrintHandler:
#     """
#         Main printer of SPG
#     """

#     def __init__(self) -> None:
#         self.print = tqdm.write                         # Function to print

#         self.barWidth = 40,                             # Default width of tqdm bar
#         self.strLine = self.getStrLine(self.barWidth)   # Default string line decorator
#         self.columnLine = ''                            # Default line with column name

#     @staticmethod
#     def getStrLine(width: int) -> str:
#         return '+' + '=' * (width - 1)

#     def __setattr__(self, name: str, value: Any) -> None:
#         super().__setattr__(name, value)

#         # When column line is given, automatically update string line decorator
#         if name == 'columnLine':
#             self.strLine = self.getStrLine(len(value))

#     def printFirstSection(self) -> None:
#         """
#             Print first section of SPG
#             +===========
#             column name
#             +===========
#         """
#         self.print('\n'.join([self.strLine, self.columnLine, self.strLine]))
#         return None

#     def list_machine(self, machineList: list[Machine]) -> None:
#         """
#             Print for spg list, specifying machine
#         """
#         self.print('\n'.join(f'{machine}' for machine in machineList))
#         self.print(self.strLine)

#     def list_group(self, groupList: list[Group]) -> None:
#         """
#             Print for spg list, specifying group
#         """
#         # Print main part
#         self.print(f'\n{self.strLine}\n'.join(f'{group}' for group in groupList))

#         # Summary
#         self.print(self.strLine)
#         self.print('\n'.join(SPG.groupInfoFormat.format(group.name,
#                                                         str(group.nMachine),
#                                                         str(group.nUnit))
#                              for group in groupList))
#         self.print(self.strLine)


def main():
    # Get arguments
    arguments = Arguments()
    args = arguments.getArgs()

    # Run SPG according to arguments
    spg = SPG()
    spg(args)


if __name__ == "__main__":
    main()
