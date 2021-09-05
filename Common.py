import os
import subprocess

# User who is running spg
currentUser = subprocess.check_output('whoami', text=True, shell=True).strip()

# Path where the spg is called
defaultPath = os.getcwd()

# Machine list for SPG
spgDir = os.path.join('/root', 'spg')
spgDir = '.'
if currentUser in ['yunsik']:
    groupFileDict = {
        'tenet': os.path.join(spgDir, 'tenet_baek.machine'),
    }
else:
    groupFileDict = {
        'tenet': os.path.join(spgDir, 'tenet.machine'),
        'xenet': os.path.join(spgDir, 'xenet.machine'),
        'kuda': os.path.join(spgDir, 'kuda.machine')
    }

if __name__ == "__main__":
    print("This is module 'Common' from SPG")