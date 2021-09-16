import tqdm
import logging
import argparse
from typing import Callable
from threading import Thread
from collections import deque, Counter

from Default import Default
from Handler import MessageHandler
from Machine import Machine


class Group:
    """ Save the information of each machine group """

    def __init__(self,
                 groupName: str,
                 groupFile: str,
                 default: Default,
                 messageHandler: MessageHandler,
                 runKillLogger: logging.Logger) -> None:
        """
            Initialize machine group information from group File
            Args:
                groupName: name of machine group
                groupFile: Full path of machine file. ex) /root/admin/spg/tenet.machine
                First line should be comment
        """

        # Default informations
        self.name: str = groupName                  # Name of machine group. Ex) tenet
        self.machineDict: dict[str, Machine] = {}   # Dictionary of machines with key of machine name
        self.nMachine: int = 0                      # Number of machines in the group = len(machineList)
        self.nCore: int = 0                         # Number of cores in the group

        # Free informations
        self.freeMachineList: list[Machine] = []    # List of machines with at least one free core
        self.nFreeMachine: int = 0                  # Number of machines with at least one free core = len(freeMachineList)
        self.nFreeCore: int = 0                     # Number of free cores

        # Current informations
        self.busyMachineList: list[Machine] = []    # List of machines running one or more jobs
        self.nJob: int = 0                          # Number of running jobs

        # Print option
        self.bar: tqdm.tqdm = None
        self.barWidth: int = None
        self.scanningMachineSet: set[str] = set()   # Set of machine names who are still scanning
        self.strLine: str = None                    # String line to be printed

        # KILL
        self.nKill: int = 0                         # Number of killed jobs

        # Read group file
        file = open(groupFile, "r")
        informationList = file.readlines()
        file.close()

        # Initialize list of machines. First 4 lines are comments
        for information in informationList[4:]:
            machine = Machine(information,
                              default,
                              messageHandler,
                              runKillLogger)
            if machine.use:
                self.machineDict[machine.name] = machine
        self.nCore += sum(machine.nCore for machine in self.machineDict.values())
        self.nMachine = len(self.machineDict)

    ###################################### Basic Utility ######################################
    def updateBar(self, machineName: str) -> None:
        """
            update the state of bar
        """
        self.scanningMachineSet.remove(machineName)
        self.bar.update(1)

        # Print any remaining machine name in scanningMachineSet
        try:
            self.bar.set_description_str(desc=f'|Scanning {next(iter(self.scanningMachineSet))}|')
        # When nothing remains at scanningMachineSet, scanning is finished
        except StopIteration:
            self.bar.set_description_str(desc='|Scanning finished|')

    def progressBar(func: Callable) -> Callable:
        """
            Define progressbar with tqdm before function
            Finish and close progressbar with tqdm after function
        """

        def decorator(self, *args, **kwargs) -> None:
            # Define progressbar and related variables
            self.scanningMachineSet = set(machineName for machineName in self.machineDict)
            self.bar = tqdm.tqdm(total=self.nMachine,
                                 bar_format='{desc}{bar}|{percentage:3.1f}%|',
                                 ascii=True,
                                 ncols=self.barWidth,
                                 miniters=1)

            # Main function
            func(self, *args, **kwargs)

            # Close progressbar
            self.bar.close()
        return decorator

    ############################ Get Information of Group Instance ############################
    def getJobInfo(self) -> tuple[int, list[Machine]]:
        """
            Get running job informations
            CAUTION! You should scan first
            Return
                nJob: number of running jobs
                busyMachineList: list of machines who is running one or more jobs
        """
        busyMachineList = [machine for machine in self.machineDict.values() if machine.nJob]
        nJob = sum(busyMachine.nJob for busyMachine in busyMachineList)
        return nJob, busyMachineList

    def getFreeInfo(self) -> tuple[int, list[Machine]]:
        """
            Get free information
            Return
                nFreeCore: number of free cores
                freeMachineList: list of machine who has one or more free cores
        """
        freeMachineList = [machine for machine in self.machineDict.values() if machine.nFreeCore]
        nFreeCore = sum(machine.nFreeCore for machine in freeMachineList)
        return nFreeCore, freeMachineList

    def getUserCount(self) -> Counter[str, int]:
        """
            Return the dictionary of {user name: number of jobs}
        """
        userCount = Counter()
        for machine in self.machineDict.values():
            userCount.update(machine.getUserCount())
        return userCount

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        """
            Return machine information in line format
            Args
                format_spec: which information to return
                    - job: return formatted job information
                    - free: return formatted free information
                    - None: return formatted group information
            When 'free' is given, return free information of machine
        """
        if format_spec == 'job':
            return '\n'.join(f'{machine:job}' + '\n' + self.strLine for machine in self.busyMachineList)
        elif format_spec == 'free':
            return '\n'.join(f'{machine:free}' for machine in self.freeMachineList)
        else:
            return '\n'.join(f'{machine}' for machine in self.machineDict.values())

    ############################## Scan Job Information and Save ##############################
    @progressBar
    def scanJob(self, userName: str, scanLevel: int) -> None:
        """
            Scan job of every machines in machineList
            nJob, busyMachineList will be updated
            If user Name is not given, nFreeCore, freeMachineList, nFreeMachine will be updated
            Args
                userName: refer Machine.getJobList
                scanLevel: refer Job.isImportant
        """

        def scanJob_updateBar(machine: Machine):
            """ Scan job and update bar """
            self.updateBar(machine.name)
            machine.scanJob(userName, scanLevel)

        # Scan job
        threadList = [Thread(target=scanJob_updateBar, args=(machine,))
                      for machine in self.machineDict.values()]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Save the scanned information
        self.nJob, self.busyMachineList = self.getJobInfo()
        if userName is None:
            self.nFreeCore, self.freeMachineList = self.getFreeInfo()
            self.nFreeMachine = len(self.freeMachineList)

    def scanJob_silent(self, userName: str, scanLevel: int) -> None:
        """
            Scan job of every machines in machineList without progressbar
            nJob, busyMachineList will be updated
            If user Name is not given, nFreeCore, freeMachineList, nFreeMachine will be updated
            Args
                userName: refer Machine.getJobList
                scanLevel: refer Job.isImportant
        """
        # Scan job
        threadList = [Thread(target=machine.scanJob, args=(userName, scanLevel))
                      for machine in self.machineDict.values()]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Save the scanned information
        self.nJob, self.busyMachineList = self.getJobInfo()
        if userName is None:
            self.nFreeCore, self.freeMachineList = self.getFreeInfo()
            self.nFreeMachine = len(self.freeMachineList)

    ##################################### Run or Kill Job #####################################
    def runs(self, curPath: str,
             cmdQueue: deque[str],
             maxCalls: int,
             startEnd: tuple[int] = None) -> deque[str]:
        """
            Run jobs in cmdQueue
            CAUTION! You should scan first
            Return
                cmdQueue: Remaining commands after run
        """
        # Get list of machine
        if startEnd is None:        # When start/end machine index is not given
            freeMachineList = self.freeMachineList
        else:                       # When start/end machine index is given
            freeMachineList = [freeMachine for freeMachine in self.freeMachineList
                               if startEnd[0] <= Machine.getIndex(freeMachine.name) <= startEnd[1]]

        # Run commands
        threadList = []
        for _, machine in zip(range(min(len(cmdQueue), maxCalls)), freeMachineList):
            for _ in range(machine.nFreeCore):
                if cmdQueue:
                    command = cmdQueue.popleft().strip()
                    threadList.append(Thread(target=machine.run, args=(curPath, command)))
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Return the remining command queue
        return cmdQueue

    def KILL(self, args: argparse.Namespace) -> None:
        threadList = [Thread(target=machine.KILL, args=(args,)) for machine in self.busyMachineList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Summarize the kill result
        self.nKill = 0
        for machine in self.busyMachineList:
            self.nKill += machine.nKill
        return None


if __name__ == "__main__":
    print("This is module 'Group' from SPG")
