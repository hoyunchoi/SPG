import os
import sys
import atexit
import colorama
import logging
from termcolor import cprint
from abc import ABC, abstractmethod
from logging.handlers import RotatingFileHandler

from Common import rootDir

class InputHandler:
    @staticmethod
    def YesNo() -> None:
        """
            Get input yes or no
            If other input is given, ask again for 5 times
        """
        for _ in range(5):
            reply = str(input('(y/n): ')).strip().lower()
            if reply[0] == 'y':
                return None
            elif reply[0] == 'n':
                exit()
            else:
                print("You should provied either 'y' or 'n'", end=' ')


class messageHandler(ABC):
    """
        Store messages from spg and print before exit the program
    """

    def __init__(self) -> None:
        self.messageList: list[str] = []
        atexit.register(self.report)

    def append(self, message: str) -> None:
        """
            Append new error to error list
        """
        self.messageList += [message]

    @abstractmethod
    def report(self) -> None:
        """
            Report the message
        """
        pass

class SuccessHandler(messageHandler):
    """ Message : standard output """

    def report(self) -> None:
        # When there is no message to print, do nothing
        if not self.messageList:
            return None

        colorama.init()
        cprint('\n'.join(self.messageList), 'green')


class ErrorHandler(messageHandler):
    """ Message: Error """

    def report(self) -> None:
        # When there is no message to print, do nothing
        if not self.messageList:
            return None

        colorama.init()
        cprint('\n'.join(self.messageList), 'red', file=sys.stderr)


class WarningHandler(messageHandler):
    """ Message: Warning """

    def report(self) -> None:
        # When there is no message to print, do nothing
        if not self.messageList:
            return None

        colorama.init()
        cprint('\n'.join(self.messageList), 'yellow', file=sys.stderr)


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
    handler = RotatingFileHandler(os.path.join(rootDir, 'RunKill.log'),
                                  delay=True,
                                  maxBytes=1024 * 1024 * 100,
                                  backupCount=1)
    handler.setFormatter(formatter)

    # Return logger
    runKillLogger.addHandler(handler)
    runKillLogger.setLevel(logging.INFO)    # log over INFO level
    return runKillLogger


if __name__ == "__main__":
    logger = getRunKillLogger()
    d = {'machine': 'tenet1', 'option': 'run', 'cmd': './test.sh'}
    logger.info('spg run ./test.sh', extra=d)
