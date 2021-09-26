import os
import sys
import subprocess


class Default:
    """
        Default variables for SPG script
    """

    ################################### You May Change Here ###################################
    # Users
    USER = {
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
        ],
    }

    # Machine group names
    GROUP = ["tenet", "xenet", "kuda"]

    # Root directory for SPG
    ROOT_DIR = os.path.join("/root", "spg")
    ROOT_DIR = "."
    ###########################################################################################

    def __init__(self) -> None:
        self.user = subprocess.check_output("whoami",
                                            text=True,
                                            shell=True).strip()     # User who is running spg
        self.path = os.getcwd()                                     # Path where the spg is called

        self.user_group = self.__check_user()                       # Group where default user is in
        self.terminal_width = self.__check_terminal_width()         # Width of current terminal

    def __check_user(self) -> str:
        """
            Check if user is registered in SPG
            Return user's group name if user is registered in SPG
            Otherwise, save error message to handler and exit program
        """
        for user_group, user_list in Default.USER.items():
            if self.user in user_list:
                return user_group

        # Didn't find user name
        raise SystemExit(f'ERROR: User "{self.user}"" is not registerd in SPG' +
                         '\n' + 'Please contact to server administrator')

    def __check_terminal_width(self) -> int:
        """
            Check current terminal width
            If using non-conventional terminal, return infinite
        """
        # Get current terminal width
        try:
            return int(subprocess.check_output(["stty", "size"]).split()[-1])
        # Not running at normal terminal: choose maximum as terminal width
        except subprocess.CalledProcessError:
            return sys.maxsize

    def get_group_file_dict(self) -> dict[str, str]:
        """
            Return dictionary of machine group files
            Machine group files of each user group is at directory named after uesr group
        """
        return {group: os.path.join(Default.ROOT_DIR, self.user_group, group + ".json")
                for group in Default.GROUP}


##################################### Define instance #####################################
default = Default()

if __name__ == "__main__":
    print('This is module "Default" from SPG')
