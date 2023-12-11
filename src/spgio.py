import atexit
import logging
import shutil
import sys
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

import colorama
from tqdm import tqdm

from .default import DEFAULT, SPG_DIR
from .name import extract_alphabet
from .option import Option


class ProgressBar:
    """A tqdm wrapper per machine groups"""

    __slots__ = ["pool", "name", "bar"]

    def __init__(self, pool: set[str], bar_width: int) -> None:
        self.pool = pool
        self.name = extract_alphabet(next(iter(pool)))
        self.bar = tqdm(
            total=len(self.pool),
            bar_format="{desc}{bar}|{percentage:3.1f}%|",
            ascii=True,
            ncols=bar_width,
            file=sys.stdout,
            miniters=1,
        )

    def update(self, target: str | None = None) -> None:
        """Update state of bar with erasing target from pool"""
        if target is not None:
            self.pool.remove(target)  # Remove target from pool
            self.bar.update(1)  # Update state of bar

        try:
            # Description of bar: print any remaining in pool
            self.bar.set_description_str(f"|Scanning {next(iter(self.pool)):<8}|")
        except StopIteration:
            # When nothing remains at pool, scanning is finished
            self.bar.set_description_str(f"|Finished {self.name:<8}|")

    def close(self) -> None:
        """Close the bar"""
        self.bar.close()


class Printer:
    """Handles progress bar and plain output text of SPG"""
    job_info_format = (
        "| {:<10} | {:<15} | {:<3} | {:>7} | {:>6} | {:>6} | {:>7} | {:>11} | {:>5}"
        " | {}"
    )
    machine_info_format = "| {:<10} | {:<11} | {:>4} {:<4} | {:>7}"
    machine_free_info_format = "| {:<10} | {:<11} | {:>4} {:<4} | {:>12}"
    group_info_format = "| {:<10} | total {:>5} machines & {:>5} core"
    group_gpu_info_format = "| {:<10} | {:>28} gpus"
    group_job_info_format = "| {:<10} | total {:>4} machines & {:>4} jobs"
    user_format = "| {:<15} | {:>8} |"  # To be updated after initialization

    def __init__(
        self, option: Option, silent: bool, groups: list[str] = DEFAULT.GROUPS
    ) -> None:
        """
        option: main option
        silent: If true, do not print process bar
        groups: Only used when option is Option.user
        """
        self.print_fn: Callable[[str], None] = print if silent else tqdm.write

        # Progress bar
        self.silent = silent  # If true, skip progress bar
        self.bars: dict[str, ProgressBar] = {}  # Container of progess bar

        # Column names for each options
        match option:
            case "list":
                self.column_line = self.machine_info_format.format(
                    "Machine", "ComputeUnit", "tot", "unit", "Memory"
                )

            case "free":
                self.column_line = self.machine_free_info_format.format(
                    "Machine", "ComputeUnit", "free", "unit", "free mem"
                )
            case "job":
                self.column_line = self.job_info_format.format(
                    "Machine",
                    "User",
                    "ST",
                    "PID",
                    "CPU(%)",
                    "MEM(%)",
                    "Memory",
                    "Time",
                    "Start",
                    "Command",
                )
            case "user":
                # Print format should be dynamically changed depending on input group list
                self.user_format += "{:>8} |" * len(groups)
                self.column_line = self.user_format.format("User", "total", *groups)
            case _:
                self.column_line = " " * DEFAULT.WIDTH

        # Progress bar width should be minimum of column line length and terminal width.
        terminal_width, _ = shutil.get_terminal_size(fallback=(sys.maxsize, 1))
        self.bar_width = min(len(self.column_line), terminal_width)
        self.str_line = "+" + "=" * (self.bar_width - 1)

    ###################################### tqdm handling ######################################
    def register_progress_bar(self, group_name: str, pool: set[str]) -> None:
        """Create new progress bar assigned to group"""
        # When silent, do nothing
        if self.silent:
            return

        self.bars[group_name] = ProgressBar(pool, self.bar_width)
        self.bars[group_name].update()

    def update_progress_bar(self, group_name: str, target: str) -> None:
        """Update state of tqdm bar with description"""
        # When silent, do nothing
        if self.silent:
            return

        self.bars[group_name].update(target)

    def close_progress_bars(self) -> None:
        """Close all progress bars registerd in printer"""
        # When silent, do nothing
        if self.silent:
            return

        for bars in self.bars.values():
            bars.close()

    ########################################## Print ##########################################
    def print_line(self, follow_silent: bool = False) -> None:
        """
        print default line: self.str_line
        If follow_silent, follow silentness of printer
        """
        # When silent and directly called to follow self.silent, do nothing
        if follow_silent and self.silent:
            return
        self.print_fn(self.str_line)

    def print(self, message: str) -> None:
        """Print input message"""
        self.print_fn(message)

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


class MessageType(Enum):
    """Type of messages with corresponding colors"""

    SUCCESS = colorama.Fore.GREEN
    WARNING = colorama.Fore.YELLOW
    ERROR = colorama.Fore.RED


class MessageHandler:
    """Handles colored output of SPG"""

    def __init__(self) -> None:
        self.message: dict[MessageType, list[str]] = {
            message_type: [] for message_type in MessageType
        }

        # Register to atexit so that report method will be called before any exit state
        atexit.register(self.report)

    def report(self) -> None:
        # Initialize colorama for compatibility of Windows
        colorama.init()

        # Print message with corresponding color
        for message_type, message in self.message.items():
            if not message:
                continue
            print(
                message_type.value + "\n".join(message),
                file=sys.stderr if message_type is MessageType.ERROR else sys.stdout,
            )
        print(colorama.Style.RESET_ALL)

    def success(self, message: str) -> None:
        self.message[MessageType.SUCCESS].append(message)

    def warning(self, message: str) -> None:
        self.message[MessageType.WARNING].append(message)

    def error(self, message: str) -> None:
        self.message[MessageType.ERROR].append(message)

    def sort(self) -> None:
        """Sort messages inside message"""
        for message in self.message.values():
            message.sort()

    def clear(self) -> None:
        """Only used for test"""
        for message in self.message.values():
            message.clear()


def configure_logger() -> logging.Logger:
    """Create logger instance for SPG"""

    class UserWritableRotatingFileHandler(RotatingFileHandler):
        def doRollover(self) -> None:
            # Rotate the file
            super().doRollover()

            # Add user writable permission
            Path(self.baseFilename).chmod(0o646)

            # Warning log and log backup file still belongs to spg executor, not root
            MessageHandler().warning(
                "Log file is rotated.\n"
                "Contact to server administrator for checking log file ownership"
            )

    # Define logger instance
    logger = logging.getLogger("SPG")

    # Define format of logging
    formatter = logging.Formatter(
        fmt="{asctime} {machine:<10} {user:<15}: {message}",
        style="{",
        datefmt=r"%Y-%m-%d %H:%M",
    )

    # Define handler of logger: Limit maximum log file size as 100MiB
    handler = UserWritableRotatingFileHandler(
        SPG_DIR / "spg.log", maxBytes=100 * 1024 * 1024, backupCount=1
    )
    handler.setFormatter(formatter)

    # Return logger
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # log over INFO level

    return logger


MESSAGE_HANDLER = MessageHandler()
LOGGER = configure_logger()
