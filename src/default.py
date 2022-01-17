import os
import pwd
from pathlib import Path

from .singleton import Singleton


class Default(metaclass=Singleton):
    """ Default variables for SPG script """
    ################################### You May Change Here ###################################
    # Users
    USER: dict[str, list[str]] = {
        "administrator": ["root"],
        "kahng": [
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
        ],
        "baek": [
            "yunsik",
            "yongjae",
            "hojun",
            "sanghoon",
            "euijoon",
            "kiwon",
            "ybaek",
            "leorigon",
        ]
    }

    # Machine group names
    GROUP: list[str] = ["tenet", "xenet", "kuda"]

    # Root directory for SPG
    ROOT_DIR = Path("/root/spg")
    ###########################################################################################

    def __init__(self) -> None:
        # Get information of current user
        self.user = pwd.getpwuid(os.geteuid()).pw_name
        self.user_group = self._check_user()

    def _check_user(self) -> str:
        """
            Check if user is registered in SPG
            Return user's group name if user is registered in SPG
            Otherwise, save error message to handler and exit program
        """
        for user_group, user_list in Default.USER.items():
            if self.user in user_list:
                return user_group

        # Couldn"t find user name
        raise SystemExit(f"ERROR: User '{self.user}' is not registerd in SPG\n"
                         "Please contact to server administrator")

    def get_group_file_dict(self) -> dict[str, Path]:
        """
            Return dictionary of machine group files
            Machine group files of each user group is at directory named after user group
        """
        return {group: Default.ROOT_DIR / self.user_group / f"{group}.json"
                for group in Default.GROUP}


if __name__ == "__main__":
    print("This is module Default from SPG")
