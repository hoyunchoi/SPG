import json
import os
import pwd
from pathlib import Path
from typing import Any

from .singleton import Singleton


class Default(metaclass=Singleton):
    """Default variables for SPG script"""

    # Root directory for SPG
    SPG_DIR = Path(__file__).parents[1]

    def __init__(self) -> None:
        # Read spg config file
        with open(self.SPG_DIR / "config.json", "r") as file:
            config: dict[str, Any] = json.load(file)

        self.USERS: list[str] = config["users"]
        self.GROUP: list[str] = config["group"]
        self.MAX_RUNS: int = config["max_runs"]
        self.WIDTH: int = config["width"]

        # Get information of current user
        self.user = self.get_current_user()

    def get_current_user(self) -> str:
        """
        Return user's name if user is registered in SPG
        Otherwise, save error message to handler and exit program
        """
        user = pwd.getpwuid(os.geteuid()).pw_name
        if user in self.USERS:
            return user

        from .spgio import MessageHandler

        MessageHandler().error(
            f"ERROR: User '{user}' is not registerd in SPG\n"
            "Please contact to server administrator"
        )
        exit()

    @property
    def group_files(self) -> dict[str, Path]:
        """Return dictionary of machine group file paths for each groups"""
        return {
            group: Default.SPG_DIR / f"machine/{group}.json" for group in self.GROUP
        }
