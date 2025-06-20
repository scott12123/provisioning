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
    with open('provisioningpi/cambium/rcp-bid-r195-rename.py') as file:
         exec(file.read())

snmp_trap_community = "Bidyadanga" #Edit for each site
devicename = "BID_F300-16SM_EXTXXXX_IP_Y_Z" #Edit this for each site

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

#Fetch the MSN (SN)
snsnmpd = os.popen(f'snmpget -v 2c -c SNMP-RO-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.1.6.0')
snsnmp = snsnmpd.read()
serial_number = re.findall(r'"(.*?)"', snsnmp)[0]
#print(serial_number)

#Fetch the ESN (MAC)
macsnmpd = os.popen(f'snmpget -v 2c -c SNMP-RO-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.1.2.0')
macsnmp = macsnmpd.read()
mac_address = re.findall(r'"(.*?)"', macsnmp)[0]

#Fetch the Firmware Version
fwsnmpd = os.popen(f'snmpget -v 2c -c SNMP-RO-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.1.5.0')
fwsnmp = fwsnmpd.read()
fwv = re.findall(r'"(.*?)"', fwsnmp)[0]

device_name_snmp = f"BID-R195P-{number}"
os.system(f"snmpset -v 2c -c SNMP-RW-ACT1v8me {ip_address} .1.3.6.1.2.1.1.5.0 s {device_name_snmp} .1.3.6.1.4.1.41010.1.9.4.0 s {snmp_trap_community} .1.3.6.1.4.1.41010.1.11.1.0 s ACTIV8ME .1.3.6.1.4.1.41010.1.11.2.0 s sesame02") #update device name
time.sleep(2)

snmptrap = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.41010.1.9.4.0")
if 'Bidyadanga' in snmptrap:
      print (Fore.GREEN + f"SNMP Trap Community: {snmptrap}")
else:
      print (Fore.RED + "SNMP Trap Community is wrong!")
      quit()

device_name = functions.snmpgeta8(ip_address,".1.3.6.1.2.1.1.5.0")
if 'BID' in device_name:
      print (Fore.GREEN + f"Device Name: {device_name}")
else:
      print (Fore.RED + "device_name")
      quit()
print("Saving config updates")
os.system(f"snmpset -v 2c -c SNMP-RW-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.7.1.0 i 1")
time.sleep(5)
os.system(f"snmpset -v 2c -c SNMP-RW-ACT1v8me {ip_address} .1.3.6.1.4.1.41010.1.7.2.0 i 1")

print("Updating google spreadsheet RP3 Data")
gsheet.add_to_sheet(serial_number, mac_address, device_name_snmp, ip_address, fwv, "R195", "N/A")
print("Updated Google Sheet 'RP3 Data'")

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
