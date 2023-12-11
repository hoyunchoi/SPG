import json
import os
import pwd
from functools import cache
from pathlib import Path
from typing import Any

# Root directory for SPG
SPG_DIR = Path(__file__).parents[1]


class Default:
    """Default variables for SPG script"""

    def __init__(self) -> None:
        # Read spg config file
        with open(SPG_DIR / "config.json", "r") as file:
            config: dict[str, Any] = json.load(file)

        self.USERS: list[str] = config["users"]
        self.GROUPS: list[str] = config["groups"]
        self.MAX_RUNS: int = config["max_runs"]
        self.WIDTH: int = config["width"]

    @property
    @cache
    def user(self) -> str:
        """
        Return user's name if user is registered in SPG
        Otherwise, save error message to handler and exit program
        """
        user = pwd.getpwuid(os.geteuid()).pw_name
        if user in self.USERS:
            return user

        from .spgio import MESSAGE_HANDLER

        MESSAGE_HANDLER.error(
            f"ERROR: User '{user}' is not registerd in SPG\n"
            "Please contact to server administrator"
        )
        exit()

    @property
    @cache
    def group_files(self) -> dict[str, Path]:
        """Return dictionary of machine group file paths for each groups"""
        return {group: SPG_DIR / f"machine/{group}.json" for group in self.GROUPS}


DEFAULT = Default()
