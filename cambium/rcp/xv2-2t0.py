#!/usr/bin/env python3
import paramiko
#import pyautogui
from ping3 import ping, verbose_ping
import time
import keyboard
import os
import sys
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

def handle_prompts(conn, command, timeout=600):
    result = conn.run(f"{command}", pty=False, hide=False, timeout=timeout)
    return result

hostname = "192.168.0.1"
username = "admin"
password = "admin"
conn = Connection(host=hostname, user=username, connect_kwargs={"password": password})
    
os.system("sudo ip address add 192.168.0.100/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to default IP 192.168.0.1

print (Fore.GREEN + "Checking for factory default XV2 connected on 192.168.0.1")
print ("To factory reset, hold reset button for 15 seconds then release. Green light will go off after a few seconds then should return to default configuration")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', '192.168.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "192.168.0.1 online")
		print ('\a')
		break
	print(Fore.RED + "192.168.0.1 not responding...")

print (Fore.GREEN + "Checking Hardware")
stream = os.popen('snmpget -v 2c -c public 192.168.0.1 .1.3.6.1.4.1.17713.22.1.1.1.5.0')
output = stream.read()

if 'XV2-2T0' in output:
        print(Fore.GREEN + "Confirmed XV2-2T0")
        hardware = "XV2-2T0"
else:
        print(Fore.RED + "Not a XV2-2T0")
        print(Fore.RED + "Check hardware model and that you're running the right config file")
        quit()

#community_name = input("Enter Community Name: ")
#community_name = community_name.replace(" ", "_")
#device_name = input("Enter Device Name: ")
#ip_address = input("Enter IP Address: ")

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
    stdin, stdout, stderr = client.exec_command(command)
    print(f"Created config {custom_config}")

finally:
    client.close()

#Firmware - upgrade to 6.6.0.3-r9 if necessary.
while True:
    print(Fore.GREEN + "Checking current firmware version...")
    firmware = functions.snmpgetpublic("192.168.0.1", ".1.3.6.1.4.1.17713.22.1.1.1.8.0")

    if '6.6.0.3-r9' in firmware:
        print(Fore.GREEN + "Currently on v6.6.0.3-r9. No upgrade needed.")
        # Update config
        second_command = f'import config {custom_config}'
        print("Updating configuration file")
        # Automatically continue past the CLI prompt that normally requires
        # the user to press Enter. We spawn a dummy read command and send a
        # newline to it which simulates the key press.
        handle_prompts(conn, second_command)
        proc = subprocess.Popen(['bash', '-c', 'read -p "Press Enter to continue..."'], stdin=subprocess.PIPE)
        proc.stdin.write(b'\n')
        proc.stdin.flush()
  #      enter_responder = Responder(
  #          pattern=r"Press enter key to apply",
  #          response="\n"
  #      )
  #      print('\a')  # Play alert bell
  #      handle_prompts(conn, second_command, watchers=[enter_responder])
        time.sleep(1) #Time delay to apply config before rebooting
        break
    else:
        print(firmware)
        print(Fore.RED + "Need to update to v6.6.0.3-r9")
        print(Fore.GREEN + "Updating firmware to v6.6.0.3-r9")
        
        #Update firmware
        print("Updating firmware")
        first_command = 'upgrade http://192.168.0.50/firmware/xv22_xv22t0_xe34_xv22t1_xe34tn-6.6.0.3-r9.cimg verbose'
        handle_prompts(conn, first_command)

        # Update config
        second_command = f'import config {custom_config}'
        print("Waiting 5s before uploading config")
        time.sleep(5)
        print("Updating configuration file")
        config_response = handle_prompts(conn, second_command)
        proc = subprocess.Popen(['bash', '-c', 'read -p "Press Enter to continue..."'], stdin=subprocess.PIPE)
        proc.stdin.write(b'\n')
        proc.stdin.flush()
#        enter_responder = Responder(
#            pattern=r"Press enter key to apply",
#            response="\n"
#        )
#        config_response = handle_prompts(conn, second_command, watchers=[enter_responder])
        print(config_response.stdout)
        # Loop until 'Error' is not found in the output
        while 'Error' in config_response.stdout:
            print("Error uploading configuration!")
            print("Retrying in 1 second...")
            time.sleep(1)
            
            # Retry the command
            config_response = handle_prompts(conn, second_command)
            print(config_response.stdout)

        print("Config upload successful!")
        # if 'Error' in config_response.stdout:
        #         print("Error uploading configuration!")
        #         print("Waiting 10 seconds to see if this helps..")
        #         time.sleep(10)
        #         config_response = handle_prompts(conn, second_command)
        #         print(config_response.stdout)
        #         if 'Error' in config_response.stdout:
        #                print("Upload failed")
        #                quit()
        # print("Config upload successful!")
        time.sleep(1) #Time delay to apply config before rebooting
        # Reboot and apply firmware / config
        print("Rebooting")
        third_command = 'service boot backup-firmware'
        handle_prompts(conn, third_command)
        conn.close()
        time.sleep(3)
        print(Fore.GREEN + "Waiting for device to come back online...")
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
        print (Fore.GREEN + f"XV2 back online as {device_name} at {ip_address}")
        break

#Print labels for the devices
current_date = datetime.now()
date = current_date.strftime("%d/%m/%Y")
print(Fore.GREEN + "Printing label for XV2 radio")
print_v1.pass_label(device_name,ip_address,f"PASS {date}")
print_v1.pass_label(device_name,ip_address,f"PASS {date}")

print (Fore.MAGENTA + "***********************************************Finished!***********************************************")

""" #Play alert bell
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(1)
print ('\a')

print ('Restart? Plug in another Cambium XV2 in with default IP')
print ('Or press Ctrl+Z to exit')


while True:
    process = subprocess.Popen(['ping','-c' ,'1', '192.168.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    returncode = process.returncode
    if returncode == 0:
        quit()    
    print(Fore.RED + "192.168.0.1 not responding...")
    if returncode == 0:
        os.execl(sys.executable, sys.executable, *sys.argv)
    print(Fore.MAGENTA + "Plug another XV2 in or press ctrl+z to quit.... checking again") """