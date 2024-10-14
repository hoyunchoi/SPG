#!/usr/bin/python
import os
import subprocess
import sys
import pwd
import threading

machineInfos = [
	{ 'groupName':'tenet', 'machineFile':'/root/admin/spg/tenet.machine', 'machines':[] }
#	{ 'groupName':'kreat', 'machineFile':'/usr/local/etc/kreat_1.machine', 'machines':[] },
#	{ 'groupName':'kreat', 'machineFile':'/usr/local/etc/kreat_2.machine', 'machines':[] },
#	{ 'groupName':'kuda', 'machineFile':'/usr/local/etc/kuda.machine', 'machines':[] },
]

scanMode1 = ['R', 'R+', 'Rs', 'Rl', 'Rl+', 'RNl', 'D']
scanModeException1 = ['ps Haxo ruser', 'sshd:', '@notty', '[']
scanModeException2 = ['scala.tools.nsc.CompileServer']

userInfo = {}

ssh_options = '-o StrictHostKeyChecking=no -o ConnectTimeout=4 -o UpdateHostKeys=no'

scanErr = []

def getMachineInfoFromFile(machineFile):
	file = open(machineFile, "r")
	lines = file.readlines()
	file.close()

	machines = []
	nMachine = 0
	nCore = 0
	for line in lines:
		line = line.strip().split("|")
		if(line[0].find('#')==-1 and line[0]=='1'):
			#1.Use|#2.No|#3.Name|#4.CPU|#5.Clock|#6.Memory|#7.Core|#8.ToBeShutDown|#9.Priority
			mi = {
				'name':line[1],
				'cpu':line[2],
				'nCore':int(line[3]),
				'memory':line[4],
				'nCurJob':int(0),
				'nFree_core':int(0)
			}
			machines.append(mi)
			nMachine += 1
			nCore += mi['nCore']
	machines.sort(key=(lambda i: i['name']))
	machinesSummary = {'nMachine':nMachine, 'nCore':nCore}
	return nMachine, nCore, machines

def getJobLinesStr(machine, onlyMe=0):
	strJobLines = []
	for nthJob in range(0, machine["nCurJob"]):
		curData = machine["curJobs"][nthJob].strip().split()
		#['asitdepends', 'R', '2021', '67.0', '5.5', '449960', '00:08:48', '15:28', 'ForestFire', 'U', 'U', '/pds/pds121/asitdepends/Research/Data/StaticModel/Static-r2.1-N10000000-L20000000-1.bnet', '20000000000', '2000000000000', '262144']
		curStrJobLine = "| %-10s | %-15s | %-3s | %6s | %4s "%(machine["name"], curData[0], curData[1], curData[2], curData[3])
		#curStrJobLine+= "| %4s | %8s | %8s | %5s | "%(curData[4], curData[5], curData[6], curData[7])
		curStrJobLine+= "| %4s | %8s | %8s | %5s | "%(curData[4], "%dMB"%(int(curData[5])/1024), curData[6], curData[7])
		for cnt1 in range(8, len(curData)):
			curStrJobLine += "%s "%(curData[cnt1])
		strJobLines.append(curStrJobLine)
	return strJobLines

def printJobInfo(onlyMe=0):
	global machineInfos
	strLine = "+===================================================================================================="
	print (strLine)
	print("| %-10s | %-15s | %-3s | %6s | %4s | %4s | %8s | %8s | %5s | %s"%("Machine", "User", "ST", "PID", "%CPU", "%MEM", "MEM", "Time", "Start", "Command"))
	print (strLine)

	for nthGroup in range(0,len(machineInfos)):
		curGroup = machineInfos[nthGroup]
		curGroupName = curGroup["groupName"]
		curMachines = curGroup["machines"]
		if(curGroup["nCurJob"]>0):
			for curMachine in curMachines:
				curStr = getJobLinesStr(curMachine)
				if(len(curStr)>0):
					print( "\n".join(curStr) )
					print (strLine)

	for curGroup in machineInfos:
		if(curGroup["nMachine"]>0):
			print ("| %-10s | total %3d jobs "%(curGroup["groupName"], curGroup["nCurJob"]))
	print (strLine)
	return

def isInExceptionList(line, exceptionList):
	isIn = 0
	for curException in exceptionList:
		if(line.find(curException)!=-1):
			isIn = 1
			break
	return isIn

def getMachineJob(nthGroup, nthMachine, machineName, onlyMe):
	global machineInfos, scanMode1, userInfo, scanErr
	global scanModeException1, scanModeException2

	proc = subprocess.Popen('ssh %s %s "ps Haxo ruser:15,stat,pid,pcpu,pmem,rss:10,time:15,start_time,args -e && (free -h --si | awk \'(NR==2){print \$7}\')"'%(ssh_options, machineName), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	#ret = proc.wait()
	s = []
	for line in proc.stdout:
		s.append(str(line.rstrip().decode('utf-8')))
	for line in proc.stderr:
		scanErr.append('ERROR: %-10s: %s' % (machineName, str(line.rstrip().decode('utf-8'))))

	sys.stdout.write('.')
	sys.stdout.flush()

	nCurJob = 0
	if(len(s) == 0):
		machineInfos[nthGroup]["machines"][nthMachine]["nCurJob"] = 0
	else:
		jobs = []
		for line in(s[:-1]):
			curData = line.strip().split()
			#['asitdepends', 'R', '2021', '67.0', '5.5', '449960', '00:08:48', '15:28', 'ForestFire', 'U', 'U', '/pds/pds121/asitdepends/Research/Data/StaticModel/Static-r2.1-N10000000-L20000000-1.bnet', '20000000000', '2000000000000', '262144']

			if(len(curData)>1):
				if(curData[1] in scanMode1):

					if(isInExceptionList(line, scanModeException1)==0 and isInExceptionList(line, scanModeException2)==0):
						#print(line)
						if(onlyMe == 0 or ( onlyMe==1 and curData[0]==userInfo['id'] )):
							nCurJob += 1
							jobs.append(line)

		machineInfos[nthGroup]["machines"][nthMachine]["nCurJob"] = nCurJob
		machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"] = machineInfos[nthGroup]["machines"][nthMachine]["nCore"] - nCurJob
		machineInfos[nthGroup]["machines"][nthMachine]["curJobs"] = jobs
		machineInfos[nthGroup]["machines"][nthMachine]["freeMem"] = s[-1].strip()
		#print(machineInfos[nthGroup]["machines"][nthMachine]["nCurJob"], machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"])

	return

def scanAllJob(onlyMe=0):
	global machineInfos, scanErr

	del scanErr[:]

	for nthGroup in range(0,len(machineInfos)):
		curGroup = machineInfos[nthGroup]
		curGroupName = curGroup["groupName"]
		curMachines = curGroup["machines"]
		#print(curGroupName)
		threads = []
		#for curMachine in curMachines :
		for nthMachine in range(0,len(curMachines)) :
			machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"] = 0
			curMachine = curMachines[nthMachine]
			t = threading.Thread(target=getMachineJob, args=(nthGroup, nthMachine, curMachine['name'], onlyMe))
			threads.append(t)

		for i in range(0, curGroup["nMachine"]):
			threads[i].start()

		for i in range(0, curGroup["nMachine"]):
			threads[i].join()

		nFreeMachine = 0
		nFreeCore = 0
		nCurJob = 0
		for nthMachine in range(0,len(curMachines)) :
			curMachine = curMachines[nthMachine]

			#print(machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"])

			#if(curMachine['will_be_shutdown']==1):
			#	machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"] = 0

			if (machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"] < 0):
				machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"] = 0

			if (machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"] > 0):
				nFreeMachine += 1
				nFreeCore += machineInfos[nthGroup]["machines"][nthMachine]["nFreeCore"]

			nCurJob += machineInfos[nthGroup]["machines"][nthMachine]["nCurJob"]

		curGroup["nFreeMachine"] = nFreeMachine
		curGroup["nFreeCore"] = nFreeCore
		curGroup["nCurJob"] = nCurJob

	print()
	for e in scanErr:
		print(e, file=sys.stderr)
	return

def killMachineJob(machineName, onlyMe):
	global ssh_options, userInfo
	global scanModeException1
	f = os.popen('ssh %s %s ps Haxo ruser:15,stat,pid,pcpu,pmem,rss:10,time:15,start_time,args -e'%(ssh_options, machineName))
	s = f.readlines()
	sys.stdout.write('.')
	sys.stdout.flush()
	processIds = {}
	for line in(s):
		curData = line.strip().split()
		if(isInExceptionList(line, scanModeException1)==0):
			if(onlyMe == 0 or ( onlyMe==1 and curData[0]==userInfo['id'] )):
				processIds[curData[2]] = 1
	for pid in processIds:
		f = os.popen('/usr/bin/ssh %s %s kill -9 %s'%(ssh_options, machineName, pid))
		print('\n(%s) kill -9 %s'%(machineName, pid))
	return

def killMachineThisJob(machineName, onlyMe):
	global ssh_options, userInfo
	global scanModeException1
	arg = sys.argv
	f = os.popen('ssh %s %s ps Haxo ruser:15,stat,pid,pcpu,pmem,rss:10,time:15,start_time,args -e'%(ssh_options, machineName))
	s = f.readlines()
	sys.stdout.write('.')
	sys.stdout.flush()
	processIds = {}
	for line in(s):
		curData = line.strip().split()
		if (line.find(arg[2])!=-1):
			if(onlyMe == 0 or ( onlyMe==1 and curData[0]==userInfo['id'] )):
				processIds[curData[2]] = 1
	for pid in processIds:
		f = os.popen('/usr/bin/ssh %s %s kill -9 %s'%(ssh_options, machineName, pid))
		print('\n(%s) kill -9 %s'%(machineName, pid))
	return

def isGoodArg(arg):
	arg_list = ['all', 'me', 'machine', 'free', 'run', 'kill', 'killall', 'killthis', 'killmachine', 'help']
	isGood = 0
	num_arg = len(arg)
	if num_arg >= 2:
		if arg[1] in arg_list:
			isGood = 1
	return isGood

def printUsage():
	#print "Usage : %s [all|me|machine|free|run|kill] (machine name) ..."%(arg[0])
	print ("Usage : spg [all|me|machine|free|run|kill|killall|killthis|killmachine] (machine name) ...")
	print ("    all     : print current status of all the jobs")
	print ("    me      : print current status of my jobs")
	print ("    machine : print information of all the machines")
	print ("    free    : print information of avaiable machines")
	print ("    run     : run a job")
	print ("              usage - spg run [machine name] [program name] (arguments)")
	print ("              CAUTION!")
	print ("              1. Invoke the job in the directory where you want the program to run")
	print ("              2. Don't append \"&\" character at the tail of commands")
	print ("              3. If you want to use redirection symbols < or >, type them in quote, such as \"<\" or \">\".")
	print ("    kill    : kill my job")
	print ("              usage - spg kill [machine name] [pid]")
	print ("    killall : kill my all jobs")
	print ("    killthis: kill my jobs whose filename includes specific word(needle)")
	print ("              usage - spg killthis [needle in running file]")
	print ("    killmachine : kill my all jobs in a given machine")
	return

def setMachineInfo():
	global machineInfos
	for cnt1 in range(0,len(machineInfos)) :
		curGroup = machineInfos[cnt1]["groupName"]
		#print(curGroup)
		machineInfos[cnt1]["nMachine"], machineInfos[cnt1]["nCore"], machineInfos[cnt1]["machines"] = getMachineInfoFromFile(machineInfos[cnt1]["machineFile"])
	#print(machineInfos)
	return

def setUserInfo():
	global userInfo
	f = os.popen('whoami')
	user_id = f.readline().strip()
	f.close()
	user_info = pwd.getpwnam(user_id)
	userInfo = {
		'id':user_id,
		'uid':'%s'%(user_info[2]),
		'home':user_info[5],
		'shell':user_info[6],
		'cur_dir':'%s'%(os.getcwd())
	}
	return

def printMachineInfo():
	global machineInfos
	strLine = "+============================================="
	print (strLine)
	print ("| SPG Machine Information :: Total")
	for curGroup in machineInfos:
		if(curGroup["nMachine"]>0):
			print (strLine)
			curMachines = curGroup["machines"]
			for curMachine in curMachines:
				print( getMachineLineStr(curMachine) )
	print (strLine)
	for curGroup in machineInfos:
		if(curGroup["nMachine"]>0):
			print ("| %-10s | total %3d machines & %4d cores "%(curGroup["groupName"], curGroup["nMachine"], curGroup["nCore"]))
	print (strLine)
	return

def getMachineLineStr(machine, onlyFree=0):
	if(onlyFree):
		strMachineLine = '| %-10s | %3s | %4s | %2d cores | %4s free'%(machine['name'],machine['cpu'],machine['memory'],machine['nFreeCore'],machine['freeMem'])
	else:
		strMachineLine = '| %-10s | %3s | %4s | %2d cores'%(machine['name'],machine['cpu'],machine['memory'],machine['nCore'])
#	if(machine['will_be_shutdown']==1):
#		strMachineLine = '%s | This machine will be shutdown.'%(strMachineLine)
	return strMachineLine

def printFreeMachineInfo():
	global machineInfos
	arg = sys.argv
	scanAllJob()
	strLine = "+========================================================="
	print (strLine)
	print ("| SPG Machine Information :: Free Cores")
	for curGroup in machineInfos:
		if(curGroup["nFreeMachine"]>0):
			print (strLine)
			curMachines = curGroup["machines"]
			for curMachine in curMachines:
				if(curMachine["nFreeCore"]>0):
					print( getMachineLineStr(curMachine, 1) )
	print (strLine)
	for curGroup in machineInfos:
		if(curGroup["nMachine"]>0):
			print ("| %-10s | total %3d machines & %3d cores "%(curGroup["groupName"], curGroup["nFreeMachine"], curGroup["nFreeCore"]))
	print (strLine)

	if(len(arg)==3 and arg[2]=='l'):
		print("\ncom = [", end="")
		for curMachine in machineInfos[0]["machines"]:
			for i in range(0, curMachine["nFreeCore"]) :
				print ("'%s',"%(curMachine["name"]), end=" ")
		print("]")

	return

	#print ("|  \033[1m%d free machine(s) & %d free CPU(s)\033[0m"%(ri['nFreeMachine'], ri['nFreeCore']))
	print (strLine)

	return

def printAllJob():
	scanAllJob()
	printJobInfo()
	return

def printMyAllJob():
	scanAllJob(1)
	printJobInfo(1)
	return

def runJob():
	global ssh_options, userInfo
	arg = sys.argv
	if(len(arg)>=4):
		run_str = "/usr/bin/ssh %s %s cd %s \";\" \"%s"%(ssh_options, arg[2], userInfo['cur_dir'], arg[3])
		for i in range(4,len(arg)):
			run_str = "%s %s"%(run_str, arg[i])
		run_str = "%s\" &"%(run_str)
		#print(run_str)
		os.system(run_str)
	else:
		printUsage()
	return

def killJob():
	global ssh_options, userInfo
	arg = sys.argv
	if(len(arg)==4):
		run_str = "/usr/bin/ssh %s %s kill -9 %s"%(ssh_options, arg[2], arg[3])
		os.system(run_str)
	else:
		printUsage()
	return

def killAllJob():
	global ssh_options, userInfo, machineInfos
	arg = sys.argv

	for nthGroup in range(0,len(machineInfos)):
		curGroup = machineInfos[nthGroup]
		curGroupName = curGroup["groupName"]
		curMachines = curGroup["machines"]

		threads = []
		for nthMachine in range(0, len(curMachines)):
			t = threading.Thread(target=killMachineJob, args=(curMachines[nthMachine]['name'], 1))
			threads.append(t)
		for i in range(0, curGroup["nMachine"]):
			threads[i].start()
		for i in range(0, curGroup["nMachine"]):
			threads[i].join()
	return

def killThisJob():
	global ssh_options, userInfo, machineInfos
	arg = sys.argv

	for nthGroup in range(0,len(machineInfos)):
		curGroup = machineInfos[nthGroup]
		curGroupName = curGroup["groupName"]
		curMachines = curGroup["machines"]

		threads = []
		for nthMachine in range(0, len(curMachines)):
			t = threading.Thread(target=killMachineThisJob, args=(curMachines[nthMachine]['name'], 1))
			threads.append(t)
		for i in range(0, curGroup["nMachine"]):
			threads[i].start()
		for i in range(0, curGroup["nMachine"]):
			threads[i].join()
	return

def killAllJobInMachine():
	global ssh_options, userInfo, machineInfos
	arg = sys.argv

	killMachineJob(arg[2], 1)
	return

def main():
	arg = sys.argv
	if(isGoodArg(arg)!=1):
		printUsage()
		exit()

	setMachineInfo()
	setUserInfo()

	options = {
    	'help': printUsage,
    	'machine': printMachineInfo,
    	'free': printFreeMachineInfo,
    	'all': printAllJob,
    	'me': printMyAllJob,
    	'run': runJob,
    	'kill': killJob,
    	'killall': killAllJob,
    	'killthis': killThisJob,
    	'killmachine': killAllJobInMachine,
    }

	options.get(arg[1],printUsage)()

if __name__ == "__main__":
    main()
