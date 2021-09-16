import os
import subprocess


class Default:
    """ Default variables for SPG script """
    ################################### You May Change Here ###################################
    # Users
    USER = {'administrator': ['root'],
            'kahng': ['hoyun', 'jongshin', 'ysl', 'jmj', 'bkjhun', 'esudoz2', 'arinaswing', 'dotoa', 'cookhyun', 'ckj'],
            'baek': ['yunsik', 'yongjae', 'hojun', 'sanghoon', 'euijoon', 'kiwon', 'ybaek', 'leorigon']}

    # Machine groups
    MACHINEGROUP = ['tenet', 'xenet', 'kuda']

    # Root directory for SPG
    ROOTDIR = os.path.join('/root', 'spg')
    ROOTDIR = '.'
    ###########################################################################################

    def __init__(self) -> None:
        self.user = subprocess.check_output('whoami',
                                            text=True,
                                            shell=True).strip()      # User who is running spg
        self.userGroup = self.__checkUser()                   # Group where default user is in

        self.path = os.getcwd()                                      # Path where the spg is called

    def __checkUser(self) -> str:
        """
            Check if user is registered in SPG
            Return user's group name if user is registered in SPG
            Otherwise, save error message to handler and exit program
        """
        for userGroup, userList in self.USER.items():
            if self.user in userList:
                return userGroup

        # Didn't find user name
        raise SystemExit(f"ERROR: User \'{self.user}\' is not registerd in SPG.\nPlease contact to server administrator")

    def getGroupFileDict(self) -> dict[str, str]:
        """
            Return dictionary of machine group files
            Machine group files of each user group is at directory named after uesr group
        """
        return {group: os.path.join(self.ROOTDIR, self.userGroup, group + '.machine')
                for group in self.MACHINEGROUP}


if __name__ == "__main__":
    print("This is module 'Default' from SPG")
