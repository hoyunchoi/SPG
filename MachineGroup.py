from os import get_inheritable
import tqdm
import argparse
from threading import Thread
from typing import Callable
from collections import deque, Counter

from Machine import Machine


class MachineGroup:
    """ Save the information of each machine group """

    def __init__(self, groupName: str, groupFile: str) -> None:
        """
            Initialize machine group information from group File
            Args:
                groupFile: Full path of machine file. ex) /root/admin/spg/tenet.machine
                First line should be comment
        """

        # Default informations
        self.name: str = groupName                  # Name of machine group. Ex) tenet
        self.machineList: list[Machine] = []        # List of machines in the group
        self.nMachine: int = 0                      # Number of machines in the group = len(machineList)
        self.nCore: int = 0                         # Number of cores in the group

        # Free informations
        self.freeMachineList: list[Machine] = []    # List of machines with at least one free core
        self.nFreeMachine: int = 0                  # Number of machines with at least one free core = len(freeMachineList)
        self.nFreeCore: int = 0                     # Number of free cores

        # Current informations
        self.busyMachineList: list[Machine] = []    # List of machines running one or more jobs
        self.nJob: int = 0                          # Number of running jobs

        # Initialize list of machines
        file = open(groupFile, "r")
        informations = file.readlines()
        file.close()
        for information in informations[4:]:        # First 4 lines are comments
            machine = Machine(information)
            if machine.use:
                self.machineList.append(machine)
                self.nCore += machine.nCore
        self.machineList.sort()
        self.nMachine = len(self.machineList)

        # Error lists
        self.scanErrList = []
        self.killErrList = []

        # Progress bar
        self.bar: tqdm.tqdm = None
        self.barWidth: int = None
        self.scanningMachineSet: set[str] = set()        # Set of machine names who are still scanning

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
            self.bar.set_description_str(desc=f'|Scanning finished|')

    def progressBar(func: Callable) -> Callable:
        """
            Define progressbar with tqdm before function
            Finish and close progressbar with tqdm after function
        """

        def decorator(self, *args, **kwargs) -> None:
            # Define progressbar
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
        nJob = 0
        busyMachineList = []
        for machine in self.machineList:
            if machine.nJob:
                nJob += machine.nJob
                busyMachineList.append(machine)
        return nJob, busyMachineList

    def getFreeInfo(self) -> tuple[int, list[Machine]]:
        """
            Get free information
            Return
                nFreeCore: number of free cores
                freeMachineList: list of machine who has one or more free cores
        """
        nFreeCore = 0
        freeMachineList = [machine for machine in self.machineList if machine.nFreeCore]
        nFreeCore = sum([machine.nFreeCore for machine in freeMachineList])
        return nFreeCore, freeMachineList

    def getUserCount(self) -> Counter[str, int]:
        """
            Return the dictionary of {user name: number of jobs}
        """
        userCount = Counter()
        for machine in self.machineList:
            userCount += machine.getUserCount()
        return userCount

    ########################## Get Line Format Information for Print ##########################
    def getInfoLineList(self) -> list[str]:
        """
            Return list of machine information in line format
        """
        return [machine.getInfoLine() for machine in self.machineList]

    def getJobLineList(self, strLine: str) -> list[str]:
        """
            Return list of job informations in line format
        """
        return [machine.getJobLine() for machine in self.busyMachineList]

    def getFreeInfoLineList(self) -> list[str]:
        """
            Return line format of machine free informations belongs to the group
        """
        return [machine.getFreeInfoLine() for machine in self.freeMachineList]

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
        self.scanningMachineSet = set([machine.name for machine in self.machineList])

        def scanJob_updateBar(machine: Machine):
            """ Scan job and update bar """
            self.updateBar(machine.name)
            machine.scanJob(userName, scanLevel)

        # Scan job
        threadList = [Thread(target=scanJob_updateBar, args=(machine,))
                      for machine in self.machineList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()
        for machine in self.machineList:
            self.scanErrList += machine.scanErrList

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
                      for machine in self.machineList]
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()
        for machine in self.machineList:
            self.scanErrList += machine.scanErrList

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
                               if startEnd[0] <= freeMachine.getIndex() <= startEnd[1]]

        # Run commands
        threadList = []
        for _, machine in zip(range(min(len(cmdQueue), maxCalls)), freeMachineList):
            for _ in range(machine.nFreeCore):
                if cmdQueue:
                    command = cmdQueue.popleft().strip()
                    t = Thread(target=machine.run, args=(curPath, command))
                    threadList.append(t)
                    print(f'spg run {machine.name} {command}')
        for thread in threadList:
            thread.start()
        for thread in threadList:
            thread.join()

        # Return the remining command queue
        return cmdQueue

    def KILL(self, args: argparse.Namespace) -> int:
        nKill = 0
        for machine in self.busyMachineList:
            nKill += machine.KILL(args)
            self.killErrList += machine.killErrList
        return nKill

    ######################################## Deprecate ########################################
    def killAll(self) -> int:
        nKill = 0
        for machine in self.userMachineList:
            nKill += machine.killAll()
            self.killErrList += machine.killErrList
        return nKill

    def killThis(self, pattern: list[str]) -> int:
        nKill = 0
        for machine in self.userMachineList:
            nKill += machine.killThis(pattern)
            self.killErrList += machine.killErrList
        return nKill

    def killBefore(self, timeWindow: int) -> int:
        nKill = 0
        for machine in self.userMachineList:
            nKill += machine.killBefore(timeWindow)
            self.killErrList += machine.killErrList
        return nKill


if __name__ == "__main__":
    print("This is moudel MachineGroup from SPG")