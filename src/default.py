import os
import pwd
from pathlib import Path

from .singleton import Singleton


class Default(metaclass=Singleton):
    """Default variables for SPG script"""

    ################################### You May Change Here ###################################
    # Users
    USERS = [
        "root",
        "hoyun",
        "jongshin",
        "ysl",
        "jmj",
        "bkjhun",
        "esudoz2",
        "arinaswing",
        "dotoa",
        "cookhyun",
        "ckj",
        "ebi",
        "yunsik",
        "yongjae",
        "hojun",
        "sanghoon",
        "euijoon",
        "kiwon",
        "ybaek",
        "leorigon",
        "jack2219",
        "joonsung",
    ]

    # Machine group names
    GROUP: list[str] = ["tenet", "xenet", "kuda"]

    # Root directory for SPG
    ROOT_DIR = Path("/root/spg")
    ###########################################################################################

    def __init__(self) -> None:
        # Get information of current user
        self.user = pwd.getpwuid(os.geteuid()).pw_name
        self._check_user()

    def _check_user(self) -> None:
        """
        Check if user is registered in SPG
        Return user's group name if user is registered in SPG
        Otherwise, save error message to handler and exit program
        """
        if self.user not in Default.USERS:
            raise SystemExit(
                f"ERROR: User '{self.user}' is not registerd in SPG\n"
                "Please contact to server administrator"
            )

    def get_group_file_dict(self) -> dict[str, Path]:
        """
        Return dictionary of machine group files
        Machine group files of each user group is at directory named after user group
        """
        return {
            group: Default.ROOT_DIR / f"machine/{group}.json" for group in Default.GROUP
        }


if __name__ == "__main__":
    print("This is module Default from SPG")
