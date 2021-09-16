import os
import atexit
import colorama
from termcolor import cprint
import logging
from logging.handlers import RotatingFileHandler

from Default import Default

class InputHandler:
    @staticmethod
    def YesNo(msg:str = None) -> bool:
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
            cprint('\n'.join(self.successList), 'green')
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


if __name__ == "__main__":
    print("This is module 'Handler' from SPG")
