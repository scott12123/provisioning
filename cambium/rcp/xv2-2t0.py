#!/usr/bin/env python3
import paramiko
#import pyautogui
from ping3 import ping, verbose_ping
import time
import keyboard
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
    device_name, ip_address = fields
except ValueError:
    print("Expected 3 fields: device_name, ip")
    sys.exit(1)

def handle_prompts(conn, command, watchers=None, timeout=600):
    """Run a command on ``conn`` and automatically handle interactive prompts."""
    result = conn.run(
        f"{command}", pty=True, hide=False, watchers=watchers,
        timeout=timeout, warn=True
    )
    return result

hostname = "192.168.0.1"
username = "admin"
password = "admin"
conn = Connection(host=hostname, user=username, connect_kwargs={"password": password})
    
os.system("sudo ip address add 192.168.0.100/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to default IP 192.168.0.1

print ("Checking for factory default XV2 connected on 192.168.0.1")
print ("To factory reset, hold reset button for 15 seconds then release. Green light will go off after a few seconds then should return to default configuration")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', '192.168.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print ("192.168.0.1 online")
		print ('\a')
		break
	print("192.168.0.1 not responding...")

print ("Checking Hardware")
stream = os.popen('snmpget -v 2c -c public 192.168.0.1 .1.3.6.1.4.1.17713.22.1.1.1.5.0')
output = stream.read()

if 'XV2-2T0' in output:
        print("Confirmed XV2-2T0")
        hardware = "XV2-2T0"
else:
        print("Not a XV2-2T0")
        print("Check hardware model and that you're running the right config file")
        quit()

#Fetch the MSN (SN)
snsnmpd = os.popen('snmpget -v 2c -c public 192.168.0.1 .1.3.6.1.4.1.17713.22.1.1.1.4.0')
snsnmp = snsnmpd.read()
serial_number = re.findall(r'"(.*?)"', snsnmp)[0]

#Fetch the ESN (MAC)
macsnmpd = os.popen('snmpget -v 2c -c public 192.168.0.1 .1.3.6.1.4.1.17713.22.1.1.1.1.0')
macsnmp = macsnmpd.read()
esn = re.findall(r'"(.*?)"', macsnmp)[0]

#Fetch the cambiumRadioMACAddress
cambiumRadioMACAddress = os.popen('snmpget -v 2c -c public 192.168.0.1 .1.3.6.1.4.1.17713.22.1.2.1.2.0')
cambiumRadioMACAddress_snmp = cambiumRadioMACAddress.read()
cambiumRadioMACAddress = re.findall(r'"(.*?)"', cambiumRadioMACAddress_snmp)[0]

#Create config file from base template
config_pi_ip = '192.168.0.50'
pi_username = 'pi'
pi_password = 'raspberry'
current_time = int(time.time())
source = '/mnt/usbstick/templates/RCP-Generic-XV2-IP-10.255.0.213.txt'
dest = f"/mnt/usbstick/rcp3/{device_name}-{ip_address}_{current_time}.txt"
command = f"sudo cp {source} {dest} && sudo sed -i 's/10.255.0.213/{ip_address}/g' {dest} && sudo sed -i 's/Generic_XV2_APX_IPX_X/{device_name}/g' {dest}"
index = dest.find("usbstick/")
dest_config = dest[index + len("usbstick/"):]
custom_config = f"tftp://192.168.0.50/{dest_config}"
client = paramiko.SSHClient()

try:
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(config_pi_ip, username=pi_username, password=pi_password)
    stdin, stdout, stderr = client.exec_command(command) #Create configuration file

finally:
    client.close()

while True:
    #Check if firmware needs an update
    firmware = functions.snmpgetpublic("192.168.0.1", ".1.3.6.1.4.1.17713.22.1.1.1.8.0")
    if '6.6.0.3-r9' in firmware:
        print("Currently on v6.6.0.3-r9. No upgrade needed.")
        # Update configuration
        second_command = f'import config {custom_config}'
        print("Updating configuration file")
        enter_responder = Responder(
            pattern=r"Please reboot the device to apply the imported configuration.*\(y/n\)",
            response="y\r",
        )
        handle_prompts(conn, second_command, watchers=[enter_responder])
        print("Updated Config")
        time.sleep(1) #Time delay to apply config before rebooting
        break
    else: #Update firmware
        print(Fore.GREEN + "Updating firmware to v6.6.0.3-r9")       
        first_command = 'upgrade http://192.168.0.50/firmware/xv22_xv22t0_xe34_xv22t1_xe34tn-6.6.0.3-r9.cimg verbose'
        handle_prompts(conn, first_command)

        # Update config
        second_command = f'import config {custom_config}'
        print("Updating configuration file")
        time.sleep(5)
        enter_responder = Responder(
            pattern=r"Please reboot the device to apply the imported configuration.*\(y/n\)",
            response="y\r",
        )
        config_response = handle_prompts(conn, second_command, watchers=[enter_responder])
        time.sleep(5) #Wait for reboot to begin before starting ping
        while 'Error' in config_response.stdout:
            print("Error uploading configuration!")
            print("Retrying in 1 second...")
            time.sleep(1)
            # Retry the command
            config_response = handle_prompts(conn, second_command, watchers=[enter_responder])
            print(config_response.stdout)

        print("Config upload successful! Rebooting..")
        time.sleep(5) #Time delay to apply config before checking ping
        print("Reminder to turn printer on - make sure 'Editor Lite' LED is off")
        time.sleep(15) #Wait for reboot to begin before starting ping
        while True:
                process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                returncode = process.returncode
                if returncode == 0:
                    #print (Fore.GREEN + f"{ip_address} online")
                    break
                print(Fore.RED + f"{ip_address} not responding...")
        break

#Print labels for the device and box
current_date = datetime.now()
date = current_date.strftime("%d/%m/%Y")
print_v1.pass_label(device_name,ip_address,f"PASS {date}")
print_v1.pass_label(device_name,ip_address,f"PASS {date}")


functions.append_to_last_record({
    "MSN": serial_number,
    "ESN": esn,
    "RadioMACAddress": cambiumRadioMACAddress,
})