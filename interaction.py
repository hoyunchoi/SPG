import os
import sys
import atexit
import argparse
import colorama
from termcolor import cprint
from tqdm import tqdm
import logging
from logging.handlers import RotatingFileHandler

from default import Default, default


class InputHandler:
    """
        Handle user input
    """
    @staticmethod
    def yes_no(msg: str = None) -> bool:
        """
            Get input yes or no
            If other input is given, ask again for 5 times
            'yes', 'y', 'Y', 'Ye', ... : pass
            'no', 'n', 'No', ... : fail
        """
        # Print message first if given
        if msg is not None:
            print(msg)

        # Ask 5 times
        for _ in range(5):
            reply = str(input('(y/n): ')).strip().lower()
            if reply[0] == 'y':
                return True
            if reply[0] == 'n':
                return False
            print("You should provied either 'y' or 'n'", end=' ')
        return False


class tqdm_spg:
    """
        tqdm used for spg
    """

    def __init__(self, pool: set[str], bar_width: int) -> None:
        self.pool = pool
        self.bar = tqdm(total=len(self.pool),
                        bar_format='{desc}{bar}|{percentage:3.1f}%|',
                        ascii=True,
                        ncols=bar_width,
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
    """
        Main printer of SPG
        Handles tqdm bar and plain output of SPG
    """
    job_info_format: str = '| {:<10} | {:<15} | {:<3} | {:>7} | {:>6} | {:>6} | {:>7} | {:>11} | {:>5} | {}'
    machine_info_format: str = '| {:<10} | {:<11} | {:>4} {:<4} | {:>5}'
    machine_free_info_format: str = '| {:<10} | {:<11} | {:>4} {:<4} | {:>10}'
    group_info_format: str = '| {:<10} | total {:>4} machines & {:>4} core'
    group_gpu_info_format: str = '| {:<10} | {:>26} gpus'
    group_job_info_format: str = '| {:<10} | total {:>4} jobs'

    def __init__(self) -> None:
        # Print function
        self.print_fn = tqdm.write                      # Function to use at printing
        # Format
        self.line_format: str = None                    # Format of main line
        self.summary_format: str = None                 # Format of summary line

        # tqdm
        self.bar_width = 40                             # Default width of tqdm bar
        self.tqdm_dict: dict[str, tqdm_spg] = {}        # Dictionary of tqdm bar. key: group name, value: tqdm

        # plain text
        self.column_line = ' ' * self.bar_width         # Default line with column name
        self.str_line = self.__update_str_line()        # Default string line decorator

    def initialize(self, args: argparse.Namespace) -> None:
        """
            Initialize printer object
        """
        if args.option == 'list':
            self.column_line = Printer.machine_info_format.format('Machine', 'ComputeUnit',
                                                                  'tot', 'unit', 'mem')

        elif args.option == 'free':
            self.column_line = Printer.machine_free_info_format.format('Machine', 'ComputeUnit',
                                                                       'free', 'unit', 'free mem')

        elif args.option == 'job':
            self.column_line = Printer.job_info_format.format('Machine', 'User', 'ST', 'PID', 'CPU(%)',
                                                              'MEM(%)', 'Memory', 'Time', 'Start', 'Command')

        elif args.option == 'user':
            # Group name list is not specified. Take every groups
            if args.group_name_list is None:
                group_name_list = Default.GROUP
            else:
                group_name_list = args.group_name_list
            self.line_format = '| {:<15} | {:>8} |' + '{:>8} |' * len(group_name_list)
            self.summary_format = self.line_format
            self.column_line = self.line_format.format('User', 'total', *group_name_list)

        self.__update_str_line()
        self.__update_bar_width(args.silent)

    def __update_str_line(self) -> str:
        self.str_line = '+' + '=' * (len(self.column_line) - 1)
        return self.str_line

    def __update_bar_width(self, silent: bool) -> None:
        """
            Update bar width
            When silent is given, bar width should be None
            Otherwise, bar width should minimum of column line length and terminal width.
        """
        # When silent is true, bar_width should be None
        if silent:
            self.bar_width = None
            return
        # Otherwise, bar_width should be minimum between length of column line and terminal width
        self.bar_width = min(len(self.column_line), default.terminal_width)

    ######################################## tqdm util ########################################
    def add_tqdm(self, group_name: str, pool: set[str]) -> None:
        """
            Add tqdm for spg to tqdm dict
            When bar_width is None, this should not create bar
        """
        if self.bar_width is None:
            return
        self.tqdm_dict[group_name] = tqdm_spg(pool, self.bar_width)

    def update_tqdm(self, group_name: str, target: str) -> None:
        """
            Update state of tqdm bar with description
        """
        self.tqdm_dict[group_name].update(target)

    def close_tqdm(self, group_name: str) -> None:
        """
            Close tqdm bar
            When bar_width is None, this should not close bar
        """
        if self.bar_width is None:
            return
        self.tqdm_dict[group_name].bar.close()

    ########################################## Print ##########################################
    def print(self, msg: str = None) -> None:
        """
            Print input msg
            When msg is None, print default value: string line
        """
        if msg is None:
            self.print_fn(self.str_line)
        else:
            self.print_fn(msg)

    def print_line_format(self, *args) -> None:
        """
            Print input arguments at line format
        """
        self.print_fn(self.line_format.format(*args))

    def print_summary_format(self, *args) -> None:
        """
            Print input arguments at summary format
        """
        self.print_fn(self.summary_format.format(*args))

    def print_first_section(self) -> None:
        """
            Print first section of SPG
            +===========
            column name
            +===========
        """
        self.print_fn(self.str_line)
        self.print_fn(self.column_line)
        self.print_fn(self.str_line)

class MessageHandler:
    """
        Store message from spg and print before exit
    """

    def __init__(self) -> None:
        self.success_list: list[str] = []    # List of success messages
        self.warning_list: list[str] = []    # List of warning messages
        self.error_list: list[str] = []      # List of error messages

        # Register to atexit so that report method will be called before any exit state
        atexit.register(self.report)

    def report(self) -> None:
        # Initialize colorama for compatibility of Windows
        colorama.init()

        # Print success messages
        if self.success_list:
            cprint('\n'.join(self.success_list), 'green', file=sys.stderr)
        # Print warning messages
        if self.warning_list:
            cprint('\n'.join(self.warning_list), 'yellow')
        # Print error messages
        if self.error_list:
            cprint('\n'.join(self.error_list), 'red')

    def success(self, msg: str) -> None:
        self.success_list.append(msg)

    def warning(self, msg: str) -> None:
        self.warning_list.append(msg)

    def error(self, msg: str) -> None:
        self.error_list.append(msg)


def get_run_kill_logger() -> logging.Logger:
    """
        Return logging.Logger instance for logging run/kill command of SPG
    """
    # Define logger instance
    run_kill_logger = logging.getLogger('run-kill')

    # Define format of logging
    formatter = logging.Formatter(fmt='{asctime} {machine:<10} {user:<15}: {message}',
                                  style='{',
                                  datefmt='%Y-%m-%d %H:%M')

    # Define handler of logger: Limit maximum log file size as 1GB
    handler = RotatingFileHandler(os.path.join(Default.ROOT_DIR, 'spg.log'),
                                  delay=True,
                                  maxBytes=1024 * 1024 * 100,
                                  backupCount=1)
    handler.setFormatter(formatter)

    # Return logger
    run_kill_logger.addHandler(handler)
    run_kill_logger.setLevel(logging.INFO)    # log over INFO level
    return run_kill_logger


##################################### Define instance #####################################
printer = Printer()
message_handler = MessageHandler()
run_kill_logger = get_run_kill_logger()


if __name__ == "__main__":
    print("This is module 'Handler' from SPG")
