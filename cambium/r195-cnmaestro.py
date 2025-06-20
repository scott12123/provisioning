#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import re
import logging
import sys
sys.path.append('provisioningpi/common') #for common files/scripts

import functions
import gsheet

#from print_v1 import print_label
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
timeout = time.time() + 60*10

def Restart():
    with open('provisioningpi/cambium/rcp-mor-r195-rename.py') as file:
         exec(file.read())
devicename = "mor_F300-16SM_EXTXXXX_IP_Y_Z" #Edit this for each site
number, ip_address, formatted_devicename = functions.create_r195_extension(devicename)
print(Fore.GREEN + f"EXT: {number}")
print(Fore.GREEN + f"IP: {ip_address}")

start = time.time()

print (Fore.GREEN + f"Checking for R195 connected on {ip_address}")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + f"{ip_address} online")
		print ('\a')
		break
	print(Fore.RED + f"{ip_address} not responding...")
#print("Wait 10s for SNMP to be ready")
#time.sleep(10)
print (Fore.GREEN + "Update device name, SNMP Trap Community then save/apply.")

os.system(f"snmpset -v 2c -c SNMP-RW-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.11.1.0 s ACTIV8ME .1.3.6.1.4.1.41010.1.11.2.0 s sesame02") #update device name
time.sleep(2)

print("Saving config updates")
os.system(f"snmpset -v 2c -c SNMP-RW-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.7.1.0 i 1")
time.sleep(5)
os.system(f"snmpset -v 2c -c SNMP-RW-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.7.2.0 i 1")

while True:
        process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode != 0:
                print (Fore.GREEN + f"Reboot started")
                print ('\a')
                break
        print(Fore.RED + "Wait for reboot..")
        time.sleep(2)
#Check how long this process took..
end = time.time()
seconds = (end - start)
seconds = seconds % (24 * 3600)
hour = seconds // 3600
seconds %= 3600
minutes = seconds // 60
seconds %= 60
print (Fore.GREEN + "Configuration Duration: %d:%02d:%02d" % (hour, minutes, seconds))


#Finished
print (Fore.MAGENTA + "***********************************************Finished!***********************************************")
Restart()
