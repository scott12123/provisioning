#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import logging
import sys
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)

timeout = time.time() + 60*10

#Connect SSH and run command

def auth(hostname, password):
	print (Fore.CYAN + "brb.")
	username = "admin"
	client = paramiko.client.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
	return client

def command(hostname, password, cmd):
	print (Fore.CYAN + "brb.")
	username = "admin"
	client = paramiko.client.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
	stdin, stdout, stderr = client.exec_command(cmd)
	output = stdout.read()
	return output

#Run pings to see if any microtik is connected
print (Fore.GREEN + "Checking if Mikrotik is connected on different IPs")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', '10.255.0.20'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "10.255.0.20 online")
		break
	print(Fore.RED + "10.255.0.20 not responding...")



####HARDWARE CHECK
print (Fore.GREEN + "Checking Hardware")
start = time.time()
output = command('10.255.0.20','yph546DKDUmsyCEJ','system resource print')


if b'board-name: Metal 52 ac' in output:
        print("Mikrotik Metal 52 ac. Continuing upgrade")
else:
	print("Hardware/Config File Mismatch!!!")
	print("Check you're running the right config file")
	quit()

#Remove incorrect changelog
print (Fore.GREEN + "Remove old changelog")
output = command('10.255.0.20','yph546DKDUmsyCEJ','file remove /flash/metal-changelog_v1.1.txt')
print (Fore.GREEN + "Removed")


#Add correct changelog
print (Fore.GREEN + "Adding config version changelog to /flash")
ftp_client=auth('10.255.0.20','yph546DKDUmsyCEJ').open_sftp()
ftp_client.put('mikrotik/metal-changelog_v1.1.txt','flash/metal-changelog_v1.1.txt')
print(Fore.GREEN + "Upload successful")
ftp_client.close()

print (Fore.GREEN + "Closed SFTP Session")



print ("*****************************************************************************************************")

#Check how long this process took..
end = time.time()
seconds = (end - start)
seconds = seconds % (24 * 3600)
hour = seconds // 3600
seconds %= 3600
minutes = seconds // 60
seconds %= 60
print ("Configuration Duration: %d:%02d:%02d" % (hour, minutes, seconds))


#Finished
print ("***********************************************Finished!***********************************************")
print ("******************************************Closing SSH Session******************************************")
#Play alert bell
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(1)

quit()
