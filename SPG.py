#! /usr/bin/python
from typing import Optional
from Job import Job
import argparse
import subprocess
from threading import Thread
from collections import deque, Counter

from Machine import Machine
from Group import Group
from Arguments import Arguments

from Default import default
from Handler import messageHandler


class SPG:
    # I know global variable is not optimal...
    global default, messageHandler

    """ SPG """
    groupInfoFormat: str = '| {:<10} | total {:>4} machines & {:>4} cores'
    groupJobInfoFormat: str='| {:<10} | total {:>4} jobs'

    def __init__(self) -> None:
        self.groupDict: dict[str, Group] = {}    # Dictionary of machine group with key of group name

        # Initialize group dictionary
        for groupName, groupFile in default.getGroupFileDict().items():
            self.groupDict[groupName] = Group(groupName, groupFile)

        # Print options
        self.defaultWidth = 40
        self.defaultStrLine = self.getStrLine(self.defaultWidth)

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

    ############################## Scan Job Information and Save ##############################
    def scanJob(self,
                groupList: list[Group],
                userName: str,
                scanLevel: int,
                barWidth: Optional[int]) -> None:
        """
            Scan running jobs
            Args
                targetGroupList: list of group to scan
                userName: whose job to scan
                scanLevel: refer Job.isImportant
        """
        # Scan job for every groups in group list
        for group in groupList:
            group.barWidth = barWidth
            threadList = [Thread(target=group.scanJob, args=(userName, scanLevel)) for group in groupList]
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
        firstLine = Machine.infoFormat.format('Machine', 'CPU', 'TOT cores', 'MEM')
        strLine = self.getStrLine(len(firstLine))

        # First section
        print(strLine)
        print(firstLine)
        print(strLine)

        # When machine list is specified
        if args.machineNameList:
            for machineName in args.machineNameList:
                machine = self.findMachineFromName(machineName)
                print(f'{machine}')
            print(strLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())
        for group in groupList:
            print(f'{group}')
            print(strLine)

        # Print total summary
        for group in groupList:
            print(SPG.groupInfoFormat.format(group.name, str(group.nMachine), str(group.nCore)))
        print(strLine)
        return None

    def free(self, args: argparse.Namespace) -> None:
        """
            Print list of machine free information
        """
        firstLine = Machine.freeInfoFormat.format('Machine', 'CPU', 'Free cores', 'Free mem')
        strLine = self.getStrLine(len(firstLine))
        print(strLine)


        # When machine list is specified
        if args.machineNameList:
            print(firstLine)
            print(strLine)
            machineList = self.scanJob_machine(args.machineNameList, userName=None, scanLevel=2)
            for machine in machineList:
                if machine.nFreeCore:
                    print(f'{machine:free}')
            print(strLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

        # First section
        barWidth = None if args.silent else min(len(firstLine), default.terminalWidth)
        self.scanJob(groupList, userName=None, scanLevel=2, barWidth=barWidth)
        if not args.silent:
            print(strLine)
        print(firstLine)
        print(strLine)

        # Print result
        for group in groupList:
            if group.nFreeMachine:
                print(f'{group:free}')
                print(strLine)

        # Print summary
        for group in groupList:
            print(SPG.groupInfoFormat.format(group.name, str(group.nFreeMachine), str(group.nFreeCore)))
        print(strLine)
        return None

    def job(self, args: argparse.Namespace) -> None:
        """
            Print current state of jobs
        """
        firstLine = Job.infoFormat.format('Machine', 'User', 'ST', 'PID', 'CPU(%)', 'MEM(%)', 'Memory', 'Time', 'Start', 'Command')
        strLine = self.getStrLine(len(firstLine))
        print(strLine)

        # When machine list is specified
        if args.machineNameList:
            print(firstLine)
            print(strLine)
            machineList = self.scanJob_machine(args.machineNameList, userName=args.userName, scanLevel=2)
            for machine in machineList:
                if machine.nJob:
                    print(f'{machine:job}')
                    print(strLine)
            return None

        # When machine list is not specified
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

        # Start print
        barWidth = None if args.silent else min(len(firstLine), default.terminalWidth)
        self.scanJob(groupList, userName=args.userName, scanLevel=2, barWidth=barWidth)
        if not args.silent:
            print(strLine)
        print(firstLine)
        print(strLine)

        # Print result
        for group in groupList:
            if group.nJob:
                group.strLine = strLine
                print(f'{group:job}')

        # Print summary
        for group in groupList:
            print(SPG.groupJobInfoFormat.format(group.name, str(group.nJob)))
        print(strLine)
        return None

    def user(self, args: argparse.Namespace) -> None:
        """
            Print job count of users per machine group
        """
        if args.groupNameList:
            groupList = [self.findGroupFromName(groupName) for groupName in args.groupNameList]
        else:
            groupList = list(self.groupDict.values())

        lineformat = '| {:<15} | {:>8} |' + '{:>8} |' * len(groupList)
        firstLine = lineformat.format('User', 'total', *tuple(group.name for group in groupList))
        strLine = self.getStrLine(len(firstLine))

        # Scanning
        print(strLine)
        barWidth = None if args.silent else min(len(firstLine), default.terminalWidth)
        self.scanJob(groupList, userName=None, scanLevel=2, barWidth=barWidth)
        if not args.silent:
            print(strLine)

        # Get user count
        totalUserCount = Counter()      # Total number of jobs per user
        groupUserCountDict = dict()     # Number of jobs per user per group
        for group in groupList:
            groupUserCount = group.getUserCount()
            groupUserCountDict[group.name] = groupUserCount
            totalUserCount.update(groupUserCount)

        # Print result per user
        print(firstLine)
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
        if not args.silent:
            print(self.defaultStrLine)
        barWidth = None if args.silent else min(self.defaultWidth, default.terminalWidth)
        self.scanJob([group], userName=None, scanLevel=2, barWidth=barWidth)
        if not args.silent:
            print(self.defaultStrLine)

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
        if not args.silent:
            print(self.defaultStrLine)
        barWidth = None if args.silent else min(self.defaultWidth, default.terminalWidth)
        self.scanJob(groupList, args.userName, scanLevel=1, barWidth=barWidth)
        if not args.silent:
            print(self.defaultStrLine)

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


def main():
    # Get arguments
    arguments = Arguments()
    args = arguments.getArgs()

    # Run SPG according to arguments
    spg = SPG()
    spg(args)


if __name__ == "__main__":
    main()
