import sys
import shutil
import atexit
from tqdm import tqdm
from typing import Optional

import logging
from logging.handlers import RotatingFileHandler

import colorama
from termcolor import cprint

from .default import Default
from .singleton import Singleton


class ProgressBar:
    """ Progress bar per machine groups using tqdm """

    def __init__(self, name: str, pool: set[str], bar_width: int) -> None:
        self.name = name
        self.pool = pool
        self.bar = tqdm(total=len(self.pool),
                        bar_format="{desc}{bar}|{percentage:3.1f}%|",
                        ascii=True,
                        ncols=bar_width,
                        file=sys.stdout,
                        miniters=1)

    def update(self, target: Optional[str]) -> None:
        """
            Update state of bar
            Args
                target: element of pool which will be erased
        """
        # Remove target from pool
        if target is not None:
            self.pool.remove(target)

            # Update state of bar
            self.bar.update(1)

        try:
            # Description of bar: print any remaining in pool
            self.bar.set_description_str(f"|Scanning {next(iter(self.pool)):<8}|")
        except StopIteration:
            # When nothing remains at pool, scanning is finished
            self.bar.set_description_str(f"|Finished {self.name:<8}|")

    def close(self) -> None:
        """ Close the bar """
        self.bar.close()


class Printer:
    """ Handles progress bar and plain output of SPG """
    job_info_format = "| {:<10} | {:<15} | {:<3} | {:>7} | {:>6} | {:>6} | {:>7} | {:>11} | {:>5} | {}"
    machine_info_format = "| {:<10} | {:<11} | {:>4} {:<4} | {:>5}"
    machine_free_info_format = "| {:<10} | {:<11} | {:>4} {:<4} | {:>10}"
    group_info_format = "| {:<10} | total {:>4} machines & {:>4} core"
    group_gpu_info_format = "| {:<10} | {:>26} gpus"
    group_job_info_format = "| {:<10} | total {:>4} jobs"
    DEFAULT_WIDTH = 40

    def __init__(self, option: str, group_list: Optional[list[str]], silent: bool) -> None:
        self.print_fn = tqdm.write                 # Function to use at printing

        # Progress bar
        self.silent = silent                        # If true, skip progress bar
        self.bar_dict: dict[str, ProgressBar] = {}  # Container of progess bar

        # Column names for each options
        if option == "list":
            self.column_line = Printer.machine_info_format.format(
                "Machine", "ComputeUnit", "tot", "unit", "mem"
            )
        elif option == "free":
            self.column_line = Printer.machine_free_info_format.format(
                "Machine", "ComputeUnit", "free", "unit", "free mem"
            )
        elif option == "job":
            self.column_line = Printer.job_info_format.format(
                "Machine", "User", "ST", "PID", "CPU(%)", "MEM(%)",
                "Memory", "Time", "Start", "Command"
            )
        elif option == "user":
            # Print format should be dynamically changed depending on input group list
            if group_list is None:
                group_list = Default.GROUP
            self.user_format = "| {:<15} | {:>8} |" + "{:>8} |" * len(group_list)
            self.column_line = self.user_format.format("User", "total", *group_list)
        else:
            self.column_line = " " * self.DEFAULT_WIDTH

        # Progress bar width should be minimum of column line length and terminal width.
        terminal_width, _ = shutil.get_terminal_size(fallback=(sys.maxsize, 1))
        self.bar_width = min(len(self.column_line), terminal_width)
        self.str_line = "+" + "=" * (self.bar_width - 1)

    ######################################## tqdm util ########################################
    def add_progress_bar(self, group_name: str, pool: set[str]) -> None:
        """ Add progress bar to bar dict """
        if self.silent:
            # When silent, do nothing
            return
        self.bar_dict[group_name] = ProgressBar(group_name, pool, self.bar_width)
        self.bar_dict[group_name].update(None)

    def update_progress_bar(self, group_name: str, target: str) -> None:
        """ Update state of tqdm bar with description """
        if self.silent:
            # When silent, do nothing
            return
        self.bar_dict[group_name].update(target)

    def close_progress_bar(self, group_name: str) -> None:
        """ Close tqdm bar """
        if self.silent:
            # When silent, do nothing
            return
        self.bar_dict[group_name].close()

    ########################################## Print ##########################################
    def print(self, msg: Optional[str] = None) -> None:
        """
            Print input msg
            When msg is None, print default value: string line
        """
        if msg is None:
            self.print_fn(self.str_line)
        else:
            self.print_fn(msg)

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


class MessageHandler(metaclass=Singleton):
    """ Store message from spg and print before exit """

    def __init__(self) -> None:
        self.success_list: list[str] = []    # List of success messages
        self.warning_list: list[str] = []    # List of warning messages
        self.error_list: list[str] = []      # List of error messages

        # Register to atexit so that report method will be called before any exit state
        atexit.register(self.report)

    def report(self) -> None:
        # Initialize colorama for compatibility of Windows
        colorama.init()

        # Print success messages: sys.stderr for splitting with tqdm
        if self.success_list:
            cprint("\n".join(self.success_list), "green", file=sys.stderr)
        # Print warning messages
        if self.warning_list:
            cprint("\n".join(self.warning_list), "yellow")
        # Print error messages
        if self.error_list:
            cprint("\n".join(self.error_list), "red")

    def success(self, msg: str) -> None:
        self.success_list.append(msg)

    def warning(self, msg: str) -> None:
        self.warning_list.append(msg)

    def error(self, msg: str) -> None:
        self.error_list.append(msg)


def configure_logger() -> None:
    """ Create logger instance for SPG """
    # Define logger instance
    logger = logging.getLogger("SPG")

    # Define format of logging
    formatter = logging.Formatter(fmt="{asctime} {machine:<10} {user:<15}: {message}",
                                  style="{",
                                  datefmt="%Y-%m-%d %H:%M")

    # Define handler of logger: Limit maximum log file size as 10MB
    handler = RotatingFileHandler(Default.ROOT_DIR / "spg.log",
                                  delay=True,
                                  maxBytes=1024 * 1024 * 10,
                                  backupCount=1)
    handler.setFormatter(formatter)

    # Return logger
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)    # log over INFO level


if __name__ == "__main__":
    print("This is module spgio from SPG")
