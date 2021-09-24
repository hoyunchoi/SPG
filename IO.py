import os
import sys
import atexit
import argparse
import colorama
from termcolor import cprint
from tqdm import tqdm
import logging
from logging.handlers import RotatingFileHandler

from Default import Default, default


class InputHandler:
    @staticmethod
    def YesNo(msg: str = None) -> bool:
        """
            Get input yes or no
            If other input is given, ask again for 5 times
            'yes', 'y', 'Y', 'Ye', ... : pass
            'no', 'n', 'No', ... : fail
        """
        if msg is not None:
            print(msg)

        for _ in range(5):
            reply = str(input('(y/n): ')).strip().lower()
            if reply[0] == 'y':
                return True
            elif reply[0] == 'n':
                return False
            else:
                print("You should provied either 'y' or 'n'", end=' ')
        return False


class tqdmSPG:
    """
        tqdm used for spg
    """

    def __init__(self, pool: set[str], barWidth: int) -> None:
        self.pool = pool
        self.bar = tqdm(total=len(self.pool),
                        bar_format='{desc}{bar}|{percentage:3.1f}%|',
                        ascii=True,
                        ncols=barWidth,
                        file=sys.stdout,
                        miniters=1)

    def update(self, target: str) -> None:
        """
            Update state of bar
            Args
                target: element of pool which should be dropped
        """
        # Remove target from pool
        self.pool.remove(target)

        # Description of bar
        # Print any remaining in pool
        try:
            description = f'|Scanning {next(iter(self.pool))}|'
        # When nothing remains at pool, scanning is finished
        except StopIteration:
            description = '|Scanning finished|'
        self.bar.set_description_str(desc=description)

        # Update state of bar
        self.bar.update(1)


class Printer:
    """ Defaults format """
    jobInfoFormat: str = '| {:<10} | {:<15} | {:<3} | {:>7} | {:>6} | {:>6} | {:>7} | {:>11} | {:>5} | {}'
    machineInfoFormat: str = '| {:<10} | {:<11} | {:>10} | {:>5}'
    machineFreeInfoFormat: str = '| {:<10} | {:<11} | {:>10} | {:>10}'
    groupInfoFormat: str = '| {:<10} | total {:>4} machines & {:>4} units'
    groupJobInfoFormat: str = '| {:<10} | total {:>4} jobs'

    """
        Main printer of SPG
        Handles tqdm bar and plain output of SPG
    """

    def __init__(self) -> None:
        # Format
        self.lineFormat: str = None                     # Format of main line
        self.summaryFormat: str = None                  # Format of summary line

        # tqdm
        self.barWidth = 40                              # Default width of tqdm bar
        self.tqdmDict: dict[str, tqdmSPG] = {}          # Dictionary of tqdm bar. key: group name, value: tqdm

        # plain text
        self.columnLine = ' ' * self.barWidth           # Default line with column name
        self.strLine = self.updateStrLine()             # Default string line decorator

    def initialize(self, args: argparse.Namespace) -> None:
        """
            Initialize printer object
        """
        if args.option == 'list':
            self.lineFormat = Printer.machineInfoFormat
            self.summaryFormat = Printer.groupInfoFormat
            self.columnLine = self.lineFormat.format('Machine', 'ComputeUnit', 'tot units', 'mem')
        elif args.option == 'free':
            self.lineFormat = Printer.machineFreeInfoFormat
            self.summaryFormat = Printer.groupInfoFormat
            self.columnLine = self.lineFormat.format('Machine', 'ComputeUnit', 'free units', 'free mem')
        elif args.option == 'job':
            self.lineFormat = Printer.jobInfoFormat
            self.summaryFormat = Printer.groupJobInfoFormat
            self.columnLine = self.lineFormat.format('Machine', 'User', 'ST', 'PID', 'CPU(%)', 'MEM(%)', 'Memory', 'Time', 'Start', 'Command')
        elif args.option == 'user':
            # Group name list is not specified. Take every groups
            if args.groupNameList is None:
                groupNameList = Default.MACHINEGROUP
            else:
                groupNameList = args.groupNameList
            self.lineFormat = '| {:<15} | {:>8} |' + '{:>8} |' * len(groupNameList)
            self.summaryFormat = self.lineFormat
            self.columnLine = self.lineFormat.format('User', 'total', *groupNameList)

        self.updateStrLine()
        self.updateBarWidth(args.silent)

    def updateStrLine(self) -> str:
        self.strLine = '+' + '=' * (len(self.columnLine) - 1)
        return self.strLine

    def updateBarWidth(self, silent: bool) -> None:
        """
            Update bar width
            When silent is given, bar width should be None
            Otherwise, bar width should minimum of column line length and terminal width.
        """
        if silent:
            self.barWidth = None
            return
        self.barWidth = min(len(self.columnLine), default.terminalWidth)

    ######################################## tqdm util ########################################
    def addTQDM(self, groupName: str, pool: set[str]) -> None:
        """
            Add tqdm for spg to tqdm dict
            When barWidth is None, this should not create bar
        """
        if self.barWidth is None:
            return
        self.tqdmDict[groupName] = tqdmSPG(pool, self.barWidth)

    def updateTQDM(self, groupName: str, target: str) -> None:
        """
            Update state of tqdm bar with description
        """
        self.tqdmDict[groupName].update(target)

    def closeTQDM(self, groupName: str) -> None:
        """
            Close tqdm bar
            When barWidth is None, this should not close bar
        """
        if self.barWidth is None:
            return
        self.tqdmDict[groupName].bar.close()

    ########################################## Print ##########################################
    def print(self, content: str = None) -> None:
        if content is None:
            tqdm.write(self.strLine)
        else:
            tqdm.write(content)

    def printLineFormat(self, *args) -> None:
        tqdm.write(self.lineFormat.format(*args))

    def printSummaryFormat(self, *args) -> None:
        tqdm.write(self.summaryFormat.format(*args))

    def firstSection(self) -> None:
        """
            Print first section of SPG
            +===========
            column name
            +===========
        """
        self.print()
        self.print(self.columnLine)
        self.print()

class MessageHandler:
    """
        Store message from spg and print before exit
    """

    def __init__(self) -> None:
        self.successList: list[str] = []    # List of success messages
        self.warningList: list[str] = []    # List of warning messages
        self.errorList: list[str] = []      # List of error messages

        # Register to atexit so that report method will be called before any exit state
        atexit.register(self.report)

    def report(self) -> None:
        # Initialize colorama for compatibility of Windows
        colorama.init()

        # Print success messages
        if self.successList:
            cprint('\n'.join(self.successList), 'green', file=sys.stderr)
        # Print warning messages
        if self.warningList:
            cprint('\n'.join(self.warningList), 'yellow')
        # Print error messages
        if self.errorList:
            cprint('\n'.join(self.errorList), 'red')

    def success(self, msg: str) -> None:
        self.successList.append(msg)
        return None

    def warning(self, msg: str) -> None:
        self.warningList.append(msg)
        return None

    def error(self, msg: str) -> None:
        self.errorList.append(msg)


def getRunKillLogger() -> logging.Logger:
    """
        Return logging.Logger instance for logging run/kill command of SPG
    """
    # Define logger instance
    runKillLogger = logging.getLogger('run-kill')

    # Define format of logging
    formatter = logging.Formatter(fmt='{asctime} {machine:<10} {user:<15}: {message}',
                                  style='{',
                                  datefmt='%Y-%m-%d %H:%M')

    # Define handler of logger: Limit maximum log file size as 1GB
    handler = RotatingFileHandler(os.path.join(Default.ROOTDIR, 'RunKill.log'),
                                  delay=True,
                                  maxBytes=1024 * 1024 * 100,
                                  backupCount=1)
    handler.setFormatter(formatter)

    # Return logger
    runKillLogger.addHandler(handler)
    runKillLogger.setLevel(logging.INFO)    # log over INFO level
    return runKillLogger


# Define instances
printer = Printer()
messageHandler = MessageHandler()
runKillLogger = getRunKillLogger()


if __name__ == "__main__":
    print("This is module 'Handler' from SPG")
