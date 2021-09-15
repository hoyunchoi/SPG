import argparse


class Job:
    """ Job informations """

    def __init__(self, machineName: str, jobInfo: str) -> None:
        """
            Change string of job information to job object
            Args
                machineName: Name of machine where this job is running
                jobInfo: Contain information with order of following, space seperated string
                        'user', 'state', 'pid', 'cpu%', 'mem%', 'mem', 'time', 'start time', 'cmd'
                        Viable command to optaion such information: use ps
                        ex) 'ps -format ruser:15,stat,pid,pcpu,pmem,rss:10,time:15,start_time,args'
        """
        self.machineName = machineName                          # Name of machine where this job is running
        jobInfo = jobInfo.strip().split()
        self.userName = jobInfo[0]                              # Name of user who is reponsible for the job
        self.state = jobInfo[1]                                 # Current state of job. Ex) R, S, D, ...
        self.pid = jobInfo[2]                                   # Process ID of job
        self.sid = jobInfo[3]                                   # Process ID of session leader
        self.cpuPercent = jobInfo[4]                            # Single core utilization percentage
        self.memPercent = jobInfo[5]                            # Memory utilization percentage
        self.mem = str(round(int(jobInfo[6]) / 1024)) + 'MB'    # Absolute value of memory utilization in 'MB'
        self.time = jobInfo[7]                                  # Time since the job started
        self.start = jobInfo[8]                                 # Time when the job started
        self.cmd = ' '.join(jobInfo[9:])                        # Command of the job

    ########################## Get Line Format Information for Print ##########################
    def __format__(self, format_spec: str) -> str:
        return f'| {self.machineName:<10} | {self.userName:<15} | {self.state:<2} | {self.pid:>7} | {self.cpuPercent:>6} | {self.memPercent:>6} | {self.mem:>6} | {self.time:>11} | {self.start:>5} | {self.cmd}'

    ###################################### Basic Utility ######################################
    def getTimeWindow(self) -> int:
        """
            Return self.time as second
            self.time has format follwing
            day-hour:minute:second  when it is over 24 hours
            hour:minute:second      when is is less 24 hours
        """
        timeList = self.time.replace('-', ':').split(':')

        toSecondList = [1, 60, 3600, 62400] # second, minute, hour, day
        second = sum(int(time) * toSecond for time, toSecond in zip(reversed(timeList), toSecondList))
        return second

    ################################## Check job information ##################################
    def isImportant(self, scanLevel: int) -> bool:
        """
            Check if the job is important or not with following rules
            1. Whether the state of job is 'R': Running or 'D': waiting for IO
            1-1 when job state is 'R', it should have either 5+(%) cpu usage or 1+(sec) running time
            2. Whether the fraction of commands is in exception list
            Args
                job: target job to be determined
                scanLevel: level of exception list. 2: more strict
            Return
                True: It is important job. Should be counted
                False: It is not important job. Should be skipped
        """
        scanModeException = ['ps H --user',     # From SPG scanning process
                             'sshd',            # SSH daemon process
                             '@notty',          # Login which does not require a terminal
                             '[']               # Not sure what this is
        if scanLevel >= 2:
            scanModeException += ['scala.tools.nsc.CompileServer']  # Not sure what this is

        # Filter job by exception
        for exception in scanModeException:
            if exception in self.cmd:
                return False

        # State is 'R'
        if 'R' in self.state:
            # Filter job by cpu usage and running time
            if (float(self.cpuPercent) < 5.0) and (self.getTimeWindow() < 1):
                return False
            else:
                return True
        # State is 'D'
        elif 'D' in self.state:
            return True
        # State is not either R and D
        else:
            return False

    def checkKill(self, args: argparse.Namespace) -> bool:
        """
            Check if this job should be killed
        """
        # When pid list is given, job's pid should be one of them
        if (args.pidList is not None) and (self.pid not in args.pidList):
            return False

        # When command pattern is given, job's command should include the pattern
        if (args.command is not None) and (args.command not in self.cmd):
            return False

        # When time is given, job's time should be less than the time
        if (args.time is not None) and (self.getTimeWindow() >= args.time):
            return False

        # When start is given, job's start should be same as the argument
        if (args.start is not None) and (self.start != args.start):
            return False

        # Every options are considered. When passed, the job should be killed
        return True


if __name__ == "__main__":
    print("This is moudel 'Job' from SPG")
