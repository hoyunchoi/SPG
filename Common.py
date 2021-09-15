import os
import subprocess

# User group
administrator = ['root']
kahngUser = ['hoyun', 'jongshin', 'ysl', 'jmj', 'bkjhun', 'esudoz2', 'arinaswing', 'dotoa', 'cookhyun', 'ckj']
baekUser = ['yunsik', 'yongjae', 'hojun', 'sanghoon']

# User who is running spg
currentUser = subprocess.check_output('whoami', text=True, shell=True).strip()

# Path where the spg is called
defaultPath = os.getcwd()

# Define SPG directory according to current user
rootDir = os.path.join('/root', 'spg')
rootDir = '.'
if currentUser in administrator:
    spgDir = os.path.join(rootDir, 'administrator')
elif currentUser in kahngUser:
    spgDir = os.path.join(rootDir, 'kahng')

elif currentUser in baekUser:
    spgDir = os.path.join(rootDir, 'baek')
else:
    raise SystemExit(f'ERROR: User \"{currentUser}\" is not registerd in SPG.\nPlease contact to administrator')

# Machine list for SPG
groupFileDict = {
    'tenet': os.path.join(spgDir, 'tenet.machine'),
    'xenet': os.path.join(spgDir, 'xenet.machine'),
    'kuda': os.path.join(spgDir, 'kuda.machine')
}


if __name__ == "__main__":
    print("This is module 'Common' from SPG")
