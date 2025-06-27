#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import sys
import re
from fabric import Connection
from invoke import Responder
sys.path.append('brother') #for label scripts
sys.path.append('common') #for common files/scripts
from datetime import datetime
import functions
import print_v1
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


def handle_prompts(conn, command, timeout=600):
            result = conn.run(f"{command}", pty=False, hide=False, timeout=timeout)
            return result

firmware_file = "http://192.168.0.50/firmware/ePMP-AC-v4.7.0.1.img" #Shouldn't need changing

hostname = "192.168.0.1"
username = "admin"
password = "admin"
conn = Connection(host=hostname, user=username, connect_kwargs={"password": password})
    
os.system("sudo ip address add 192.168.0.100/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to default IP 192.168.0.1

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

if '39' in output:
        print(Fore.GREEN + "Confirmed 5 GHz Force 300-16 Radio")
        hardware = "F300-16"
else:
        print(Fore.RED + "Not a Force300-16")
        functions.log(f"Device is not a F300-16","ERROR")
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

#community_name = "NBN_SPARE"
#device_name = "NBN_SPARE_F30016_0_215"
#ip_address = "10.255.0.215"

#Create config file from base template
config_pi_ip = '192.168.0.50'
pi_username = 'pi'
pi_password = 'raspberry'
current_time = int(time.time())
source = '/mnt/usbstick/templates/RCP3-Generic-Force300-16-IP-10.255.0.215-v2.0.json'
dest = f"/mnt/usbstick/universal/universal_F30016_{current_time}.txt"
command = f"sudo cp {source} {dest} && sudo sed -i 's/SNMP-RO-ACT1v8me/CdZbUUcp3f/g' {dest} && sudo sed -i 's/SNMP-RW-ACT1v8me/cNmpF9wusE/g' {dest} && sudo sed -i 's/GEN_300-16_EXTxxxx_IP_x_x/{device_name}/g' {dest} && sudo sed -i 's/SNMP_Sitename/{community_name}/g' {dest}"
index = dest.find("usbstick/")
dest_config = dest[index + len("usbstick/"):]
custom_config = f"http://192.168.0.50/{dest_config}"
client = paramiko.SSHClient()

try:
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(config_pi_ip, username=pi_username, password=pi_password)
    stdin, stdout, stderr = client.exec_command(command)
    print(f"Created config {custom_config}")

finally:
    client.close()

#Firmware - upgrade to 4.7.0.1 if necessary.

while True:  # Outer loop to restart the process if necessary
    print(Fore.GREEN + "Checking current firmware version...")
    firmware = functions.snmpget("192.168.0.2", ".1.3.6.1.4.1.17713.21.1.1.1.0")

    if '4.7.0.1' in firmware:
        print(Fore.GREEN + "Currently on v4.7.0.1. No upgrade needed.")
        functions.log(f"Firmware already v4.7.0.1 for {device_name} - {serial_number}","INFO")
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
                    functions.log(f"Firmware Upgraded for {device_name} - {serial_number}","INFO")
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
                functions.log(f"Configuration upload failed but ping responded on {ip_address} - {device_name}","ERROR")
                print (Fore.GREEN + f"{ip_address} online")
                break
            else:
                print(Fore.YELLOW + "Restarting configuration import due to idle status...")
                break  # Exit the inner loop to restart the process

        time.sleep(1)  # Check for new status

    if 'rebooting' in status_message:
        functions.log(f"Configuration uploaded successfully - {device_name}","INFO")
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
print(Fore.GREEN + "Printing label for XV2 radio")
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

functions.log(f"Configuration completed for {device_name}","INFO")

#Finished
