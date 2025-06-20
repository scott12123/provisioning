
#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import re
import logging
import sys
#brother_path = os.path.join(os.path.expanduser('~'), 'brother')
sys.path.append('provisioningpi/brother') #for label scripts
sys.path.append('provisioningpi/common') #for common files/scripts

import functions
import gsheet
import print_v1

#from print_v1 import print_label
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
timeout = time.time() + 60*10


############Edit this bit only#################
config_file = "http://192.168.0.50/rcp3/RCP3-Generic-Force300-16-IP-10.255.0.215.json" #Shouldn't need changing
config_file_ip = "10.255.0.29" #Shouldnt need changing unless IP address in the config file changes.
firmware_file = "http://192.168.0.50/firmware/ePMP-AC-v4.7.0.1.img" #Shouldn't need changing
devicename = "BID_F300-16SM_EXTXXXX_IP_Y_Z" #Edit this for each site
ip_address = "10.255.0.29"
############Edit this bit only#################


os.system("sudo ip address add 192.168.0.1/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to default IP 192.168.0.2

start = time.time() #Lets see how long this takes?

#Run pings to see if any default f300-16 is connected
print (Fore.GREEN + "Checking for factory default ePMP1000 connected on 192.168.0.2")
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

if '4' in output:
        print(Fore.GREEN + "Confirmed 2.4 GHz Connectorized Radio")
        hardware = "F300-16"
else:
        print(Fore.RED + f"{output}")
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
print (Fore.GREEN + "F300 back online. Loading default config")
print (Fore.GREEN + f"Uploading {config_file}")

while True:
    # Import JSON file and ignore errors
    importjsonconfig = os.system(f"snmpset -v 2c -c privatereadwrite 192.168.0.2 .1.3.6.1.4.1.17713.21.6.4.1.0 s {config_file} .1.3.6.1.4.1.17713.21.6.4.4.0 i 1  > /dev/null 2>&1")
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
                break  # Exit the inner loop as the process is complete
            else:
                status_message = current_status

            if current_status != last_status:
                print(Fore.GREEN + "Config Status:", status_message)
                last_status = current_status

        if status_zero_count > 8:
            print(Fore.YELLOW + "Restarting configuration import due to idle status...")
            break  # Exit the inner loop to restart the process

        time.sleep(1)  # Check for new status

    if 'rebooting' in status_message:
        break  # Exit the outer loop as the import process is complete




print(Fore.GREEN + f"Pinging {config_file_ip}...")
print("Reminder to turn printer on - make sure 'Editor Lite' LED is off")
time.sleep(10) #Wait for reboot to begin before starting ping
while True:
        process = subprocess.Popen(['ping','-c' ,'1', config_file_ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                print (Fore.GREEN + f"{config_file_ip} online")
                break
        print(Fore.RED + f"{config_file_ip} not responding...")
print(Fore.GREEN + f"Pinging {ip_address}...printing labels whilst we wait.")
time.sleep(2)

site = formatted_devicename[:3]

#Print labels for the devices
print(Fore.GREEN + "Printing label for F300 radio")
print_v1.print_label(number,ip_address,"device",site)
print(Fore.GREEN + "Printing label for F300 box")
print_v1.print_label(number,ip_address,"box",site)

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

#Play alert bell
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(1)
print ('\a')
