#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import re
import logging
import sys
from datetime import datetime
#brother_path = os.path.join(os.path.expanduser('~'), 'brother')
sys.path.append('brother') #for label scripts
sys.path.append('common') #for common files/scripts

import functions
import gsheet
import print_v1

#from print_v1 import print_label
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)

if len(sys.argv) < 2:
    print("Missing parameters")
    sys.exit(1)

# Split the CSV line passed as a single string
fields = sys.argv[1].split(',')

try:
    community_name, device_name, ip_address = fields
except ValueError:
    print("Expected 3 fields: community_name,device_name,ip")
    sys.exit(1)

community_name = community_name.replace(" ", "_")

############Edit this bit only#################
config_file = "http://192.168.0.50/rcp3/RCP3-Generic-Force300-25-IP-10.255.0.216.json" #Shouldn't need changing
config_file_ip = "10.255.0.216" #Shouldnt need changing unless IP address in the config file changes.
firmware_file = "http://192.168.0.50/firmware/ePMP-AC-v4.7.0.1.img" #Shouldn't need changing
snmp_trap_community = f"SNMP_{community_name}" #Edit for each site
############Edit this bit only#################

os.system("sudo ip address add 192.168.0.1/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to default IP 192.168.0.2

#Run pings to see if any default f300-16 is connected
print (Fore.GREEN + "Checking for factory default F300 connected on 192.168.0.2")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', '192.168.0.2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "192.168.0.2 online")
		print ('\a')
		break
	print(Fore.RED + "192.168.0.2 not responding...")

#Set the temp admin password first == A8gs#TrPrVNet!
password = functions.passwd('192.168.0.2')
time.sleep(5) #Sleep briefly because without it often broke the next part

#SSH and set SNMP to custom prior to firmware upgrade (v4.7.0.1 forces complex new password)
print(Fore.GREEN + "Updating SNMP public and private community")
hostname = "192.168.0.2"
username = "admin"
password = "!2mzPg$HzMjdZ2"

client = paramiko.client.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
channel = client.invoke_shell()
stdin = channel.makefile('wb')
stdout = channel.makefile('rb')
channel.send('config set snmpReadOnlyCommunity publicreadonly\n')
time.sleep(2)
channel.send('config set snmpReadWriteCommunity privatereadwrite\n')
time.sleep(2)
channel.send('config set snmpRemoteAccess 1\n')
time.sleep(2)
channel.send('config save\n')
time.sleep(2)
channel.send('config apply\n')
time.sleep(2)
channel.send('exit\n')
RESULTS = channel.recv(8192)
stdout.close()
stdin.close()

print(Fore.GREEN + "Updated SNMP. Wait 5 seconds for changes to apply")
time.sleep(5)

#Hardware check - Make sure we're actually running a F300-16. We only check now in case the firmare is blocking SNMP access.
print (Fore.GREEN + "Checking Hardware")

stream = os.popen('snmpget -v 2c -c publicreadonly 192.168.0.2 .1.3.6.1.4.1.17713.21.1.1.2.0')
output = stream.read()

if '36' in output:
        print(Fore.GREEN + "Confirmed 5 GHz Force 300-25 Radio")
        hardware = "F300-25"
else:
        print(Fore.RED + "Not a Force300-25")
        functions.log(f"Device is not a F300-25","ERROR")
        print(Fore.RED + "Check hardware model and that you're running the right config file")
        quit()

#Fetch the MSN (SN)
snsnmpd = os.popen('snmpget -v 2c -c publicreadonly 192.168.0.2 .1.3.6.1.4.1.17713.21.1.1.31.0')
snsnmp = snsnmpd.read()
serial_number = re.findall(r'"(.*?)"', snsnmp)[0]

#Fetch the ESN (MAC)
macsnmpd = os.popen('snmpget -v 2c -c publicreadonly 192.168.0.2 .1.3.6.1.4.1.17713.21.1.1.30.0')
macsnmp = macsnmpd.read()
mac_address = re.findall(r'"(.*?)"', macsnmp)[0]

#Firmware - upgrade to 4.7.0.1 if necessary.

while True:  # Outer loop to restart the process if necessary
    print(Fore.GREEN + "Checking current firmware version...")
    firmware = functions.snmpget("192.168.0.2", ".1.3.6.1.4.1.17713.21.1.1.1.0")

    if '4.7.0.1' in firmware:
        print(Fore.GREEN + "Currently on v4.7.0.1. No upgrade needed.")
        break  # Exit the loop if no upgrade needed
    else:
        print(Fore.RED + "Need to update to v4.7.0.1")
        setfirmware = os.system(f"snmpset -v 2c -c privatereadwrite 192.168.0.2 .1.3.6.1.4.1.17713.21.4.7.0 s {firmware_file} > /dev/null 2>&1")

        last_status = None
        status_zero_count = 0

        while True:
            current_status_value = functions.snmpget("192.168.0.2", ".1.3.6.1.4.1.17713.21.4.8.0")
            int_value = re.search(r'\d+$', current_status_value)
            current_status = int_value.group() if int_value else None

            if current_status:
                if current_status == "0":
                    status_message = "Idle..."
                    status_zero_count += 1
                elif current_status == "1":
                    status_message = "Uploading image to device"
                elif current_status == "2":
                    status_message = "Verifying SHA2 signature"
                elif current_status == "3":
                    status_message = "Executing pre-update script"
                elif current_status == "4":
                    status_message = "Uploading image to flash"
                elif current_status == "5":
                    status_message = "Uploading u-boot to flash"
                elif current_status == "6":
                    status_message = "Executing post-update script"
                elif current_status == "10":
                    status_message = "Upgrade complete, rebooting"
                    print(Fore.GREEN + "Firmware Status:", status_message)
                    break  # Exit the inner loop as upgrade is complete
                else:
                    status_message = current_status
                if current_status != last_status:
                    print(Fore.GREEN + "Firmware Status:", status_message)
                    last_status = current_status

            if status_zero_count > 3:
                print(Fore.YELLOW + "Restarting firmware update due to idle status...")
                break  # Exit the inner loop to restart the firmware update

            time.sleep(1)  # Check for new status

        if 'rebooting' in status_message:
            break  # Exit the outer loop as the upgrade process is complete

print(Fore.GREEN + "Waiting for device to come back online...")
time.sleep(10) #Wait for reboot to begin before starting ping
while True:
        process = subprocess.Popen(['ping','-c' ,'1', '192.168.0.2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                print (Fore.GREEN + "192.168.0.2 online")
                break
        print(Fore.RED + "192.168.0.2 not responding...")
#            time.sleep(2)  # Delay between pings
print (Fore.GREEN + "F300 back online")
print (Fore.GREEN + "Creating custom config")

#Create config file from base template
hostname = '192.168.0.50'
username = 'pi'
password = 'raspberry'
current_time = int(time.time())
source = '/mnt/usbstick/rcp3/RCP3-Generic-Force300-25-IP-10.255.0.216.json'
dest = f"/mnt/usbstick/rcp3/RCP3-{community_name}-Force300-25_{ip_address}_{current_time}.json"
command = f"sudo cp {source} {dest} && sudo sed -i 's/10.255.0.216/{ip_address}/g' {dest} && sudo sed -i 's/GEN_300-25_EXTxxxx_IP_x_x/{device_name}/g' {dest} && sudo sed -i 's/SNMP_SiteName/{snmp_trap_community}/g' {dest}"
index = dest.find("usbstick/")
dest_config = dest[index + len("usbstick/"):]
custom_config = f"http://192.168.0.50/{dest_config}"
client = paramiko.SSHClient()

# Enable detailed debugging
#paramiko.util.log_to_file('paramiko.log')

try:
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, username=username, password=password)
    stdin, stdout, stderr = client.exec_command(command)
    print("Created config")

finally:
    client.close()

print (Fore.GREEN + f"Uploading {custom_config}")

while True:
    importjsonconfig = os.system(f"snmpset -v 2c -c privatereadwrite 192.168.0.2 .1.3.6.1.4.1.17713.21.6.4.1.0 s {custom_config} .1.3.6.1.4.1.17713.21.6.4.4.0 i 1  > /dev/null 2>&1")
    last_status = None
    status_zero_count = 0  # Counter for the number of times status is 0

    while True:
        current_status_value = functions.snmpget("192.168.0.2", ".1.3.6.1.4.1.17713.21.6.4.2.0")
        int_value = re.search(r'\d+$', current_status_value)
        current_status = int_value.group() if int_value else None

        if current_status:
            if current_status == "0":
                status_message = "Idle."
                status_zero_count += 1
            elif current_status == "1":
                status_message = "Downloading config"
                status_zero_count += 1
            elif current_status == "2":
                status_message = "Importing config"
            elif current_status == "3":
                status_message = "Upgrade complete, rebooting"
                print(Fore.GREEN + "Config Status:", status_message)
                break
            else:
                status_message = current_status

            if current_status != last_status:
                print(Fore.GREEN + "Config Status:", status_message)
                last_status = current_status

        if status_zero_count > 8:
            process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode == 0:
                print (Fore.GREEN + f"{ip_address} online")
                break
            else:
                print(Fore.YELLOW + "Restarting configuration import due to idle status...")
                break  # Exit the inner loop to restart the process

        time.sleep(1)  # Check for new status

    if 'rebooting' in status_message:
        break  # Exit the outer loop as the import process is complete




print(Fore.GREEN + f"Pinging {ip_address}...")
print("Reminder to turn printer on - make sure 'Editor Lite' LED is off")
time.sleep(10) #Wait for reboot to begin before starting ping
while True:
        process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                print (Fore.GREEN + f"{ip_address} online")
                break
        print(Fore.RED + f"{ip_address} not responding...")
print (Fore.GREEN + f"F300 back online at {ip_address}. Waiting for SNMP to be ready...")
time.sleep(5)


#Print labels for the devices
current_date = datetime.now()
date = current_date.strftime("%d/%m/%Y")
print_v1.pass_label(device_name,ip_address,f"PASS {date}")
print_v1.pass_label(device_name,ip_address,f"PASS {date}")

#Continue the ping checks
while True:
        process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                print (Fore.GREEN + f"{ip_address} online")
                break
        print(Fore.RED + f"{ip_address} not responding...")

print(Fore.GREEN + f"Now online at {ip_address}")

# Ping SMC and try get a response
attempt_count = 0

# Loop up to 5 times

while attempt_count < 15:
    process = subprocess.Popen(['ping', '-c', '1', '10.255.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    returncode = process.returncode

    if returncode == 0:
        print(Fore.GREEN + "10.255.0.1 online")
        smc_ping = "Success"
        break
    else:
        print(Fore.RED + "10.255.0.1 not responding...")

    # Increment the counter
    attempt_count += 1

# If ping fails after 5 attempts
if attempt_count == 15 and returncode != 0:
    smc_ping = "Fail"
print("10s delay to trip stop SNMP Trap error")
time.sleep(10)
print("Final Checks")

snmptrap = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.5.6.0")
if snmp_trap_community in snmptrap:
      functions.log(f"SNMP Trap Community 1 is correct - {device_name}","SNMP_ERROR")
else:
      functions.log(f"SNMP Trap Community 1 is wrong - {device_name}","SNMP_ERROR")
#running this twice to see if it gives error both times
snmptrap = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.5.6.0")
if snmp_trap_community in snmptrap:
      print (Fore.GREEN + "SNMP Trap Community is correct")
      functions.log(f"SNMP Trap Community 2 is correct - {device_name}","SNMP_ERROR")
else:
      print (Fore.RED + "SNMP Trap Community is wrong!")
      functions.log(f"SNMP Trap Community 2 is wrong - {device_name}","SNMP_ERROR")
      quit()

snmpname = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.5.3.0")
if device_name in snmpname:
      print (Fore.GREEN + "SNMP name is correct")
else:
      print (Fore.RED + "SNMP name is wrong!")
      quit()
bridgeip = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.4.7.2.0")
if ip_address in bridgeip:
      print (Fore.GREEN + "Bridge IP address is correct")
else:
      print (Fore.RED + "Bridge IP is wrong!")
      quit()
device_n = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.6.1.2.0")
if device_name in device_n:
      print (Fore.GREEN + "F300 device name is correct")
else:
      print (Fore.RED + "F300 device name is wrong!")
      quit()
fw = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.1.1.1.0")
if '4.7.0.1' in fw:
      fwv = re.findall(r'"(.*?)"', fw)[0]
      print (Fore.GREEN + "Firmware correct")
else:
      print (Fore.RED + "Firmware should be v4.7.0.1")
      quit()
cnurl = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.20.2.0")
if 'cloud.cambiumnetworks.com' in cnurl:
      print (Fore.GREEN + "CNMaestro URL is correct")
else:
      print (Fore.RED + "CNMaestro URL is wrong!")
      quit()
cnmenabled = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.20.1.0")
if '1' in cnmenabled:
      print (Fore.GREEN + "CNMaestro is enabled")
else:
      print (Fore.RED + "CNMaestro is disabled!")
      quit()
#Updating google spreadsheet RP3 Data
gsheet.add_to_sheet(serial_number, mac_address, device_name, ip_address, fwv, hardware, smc_ping)
print("Updated Google Sheet 'RP3 Data'")
