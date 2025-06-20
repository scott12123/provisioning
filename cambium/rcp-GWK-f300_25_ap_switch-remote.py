#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import re
import logging
import sys
import threading
from queue import Queue

#brother_path = os.path.join(os.path.expanduser('~'), 'brother')
sys.path.append('/home/pi/provisioningpi/brother') #for label scripts
sys.path.append('/home/pi/provisioningpi/common') #for common files/scripts

import functions
import gsheet
import print_v1

#from print_v1 import print_label
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
timeout = time.time() + 60*10

config_file = "http://192.168.0.50/rcp3/RCP3-Generic-Force300-25-IP-10.255.0.216.json" #Shouldn't need changing
config_file_ip = "10.255.0.216" #Shouldnt need changing unless IP address in the config file changes.
#firmware_file = "http://192.168.0.50/firmware/ePMP-AC-v4.6.2.img" #Shouldn't need changing
firmware_file = "http://192.168.0.50/firmware/ePMP-AC-v4.7.0.1.img" #Shouldn't need changing
devicename = "GWK_F300-25SM_APXXXX_IP_Y_Z" #Edit this for each site
snmp_trap_community = "SNMP_Galiwinku" #Edit for each site

#############################

def initial_snmp_config(ip_address):
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
    channel.send(f'config set networkBridgeIPAddr {ip_address}\n')
    time.sleep(2)
    channel.send('config save\n')
    time.sleep(2)
    channel.send('config apply\n')
    time.sleep(2)
    channel.send('exit\n')
    RESULTS = channel.recv(8192)
    stdout.close()
    stdin.close()

    print(Fore.GREEN + "Updated SNMP. Wait for changes to apply")


def is_device_available(ip_address):
    response = os.system(f"ping -c 1 {ip_address}")
    return response == 0


def f300_16(ext, temp_ip_address):
    print(f"Starting AP{ext}")
    site = devicename[:3]

    ip_address = f"10.255.3.{ap}1"
    formatted_devicename = devicename.replace("XXXX", f"{ap}").replace("Y", "3").replace("Z", f"{ap}1")

    initial_snmp_config(temp_ip_address)
    print(f'Setup with {temp_ip_address}')
    time.sleep(10)
    while True:
        if is_device_available(temp_ip_address):
#            print("ping success")
            time.sleep(3)
            break
        else:
#            print("waiting for ping")
            time.sleep(2)

    #Hardware check - Make sure we're actually running a F300-25. We only check now in case the firmare is blocking SNMP access.
    time.sleep(10)
#    print (Fore.GREEN + "Checking Hardware")

    stream = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.2.0')
    output = stream.read()

    if '36' in output:
#            print(Fore.GREEN + "Confirmed 5 GHz Force 300-25 Radio")
            hardware = "F300-25"
    else:
#            print(Fore.RED + "Not a Force300-25")
#            print(Fore.RED + "Check hardware model and that you're running the right config file")
            quit()

    #Fetch the MSN (SN)
    snsnmpd = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.31.0')
    snsnmp = snsnmpd.read()
    serial_number = re.findall(r'"(.*?)"', snsnmp)[0]

    #Fetch the ESN (MAC)
    macsnmpd = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.30.0')
    macsnmp = macsnmpd.read()
    mac_address = re.findall(r'"(.*?)"', macsnmp)[0]


    #Firmware - upgrade to 4.7.0.1 if necessary.

    while True:  # Outer loop to restart the process if necessary
#        print(Fore.GREEN + "Checking current firmware version...")
        firmware = functions.snmpget(temp_ip_address, ".1.3.6.1.4.1.17713.21.1.1.1.0")
    #    if '4.1.0.1' in firmware:
        if '4.7.0.1' in firmware:
            print(Fore.GREEN + "Currently on v4.7.0.1. No upgrade needed.")
            break  # Exit the loop if no upgrade needed
        else:
            print(Fore.RED + "Need to update to v4.7.0.1")
            setfirmware = os.system(f"snmpset -v 2c -c privatereadwrite {temp_ip_address} .1.3.6.1.4.1.17713.21.4.7.0 s {firmware_file} > /dev/null 2>&1")

            last_status = None
            status_zero_count = 0

            while True:
                current_status_value = functions.snmpget(temp_ip_address, ".1.3.6.1.4.1.17713.21.4.8.0")
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
 #                       print(Fore.GREEN + "Firmware Status:", status_message)
                        break  # Exit the inner loop as upgrade is complete
                    else:
                        status_message = current_status

                    if current_status != last_status:
#                        print(Fore.GREEN + "Firmware Status:", status_message)
                        last_status = current_status

                if status_zero_count > 3:
#                    print(Fore.YELLOW + "Restarting firmware update due to idle status...")
#                    print(Fore.GREEN + "Waiting for device to come back online...")
                    time.sleep(10) #Wait for reboot to begin before starting ping
                    break  # Exit the inner loop to restart the firmware update
                time.sleep(1)  # Check for new status

            if 'rebooting' in status_message:
                time.sleep(5)
                break  # Exit the outer loop as the upgrade process is complete

#    print(Fore.GREEN + "Waiting for F300...")
    time.sleep(10)
    while True:
        if is_device_available(temp_ip_address):
#            print("ping success")
            time.sleep(2)
            break
        else:
#            print("waiting for ping")
            time.sleep(2)

#    print (Fore.GREEN + "F300 back online.")
#    print (Fore.GREEN + "Creating custom config")

    #Create custom config from base config file
    hostname = '192.168.0.50'
    username = 'pi'
    password = 'raspberry'
    current_time = int(time.time())
    source = '/mnt/usbstick/rcp3/RCP3-Generic-Force300-25-IP-10.255.0.216.json'
    dest = f"/mnt/usbstick/rcp3/RCP3-{site}-Force300-25_AP{ext}_{ip_address}_{current_time}.json"
    command = f"sudo cp {source} {dest} && sudo sed -i 's/10.255.0.216/{ip_address}/g' {dest} && sudo sed -i 's/GEN_300-25_EXTxxxx_IP_x_x/{formatted_devicename}/g' {dest} && sudo sed -i 's/SNMP_SiteName/{snmp_trap_community}/g' {dest}"
    index = dest.find("/usbstick/")
    dest_config = dest[index + len("/usbstick/"):]
    client = paramiko.SSHClient()


    try:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
#        print("Created config")

    finally:
        client.close()

    custom_config = f"http://192.168.0.50/{dest_config}"
    print (Fore.GREEN + f"Uploading {custom_config}")
    while True:
        importjsonconfig = os.system(f"snmpset -v 2c -c privatereadwrite {temp_ip_address} .1.3.6.1.4.1.17713.21.6.4.1.0 s {custom_config} .1.3.6.1.4.1.17713.21.6.4.4.0 i 1  > /dev/null 2>&1")
        last_status = None
        status_zero_count = 0  # Counter for the number of times status is 0

        while True:
            current_status_value = functions.snmpget(temp_ip_address, ".1.3.6.1.4.1.17713.21.6.4.2.0")
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
#                    print(Fore.GREEN + "Config Status:", status_message)
                    break  # Exit the inner loop as the process is complete
                else:
                    status_message = current_status

                if current_status != last_status:
#                    print(Fore.GREEN + "Config Status:", status_message)
                    last_status = current_status

            if status_zero_count > 8:
#                print(Fore.YELLOW + "Restarting configuration import due to idle status...")
                break  # Exit the inner loop to restart the process

            time.sleep(1)  # Check for new status

        if 'rebooting' in status_message:
            time.sleep(5)
            break  # Exit the outer loop as the import process is complete


#    print(Fore.GREEN + f"Pinging {ip_address}...")
#    print("Reminder to turn printer on - make sure 'Editor Lite' LED is off")
    time.sleep(10) #Wait for reboot to begin before starting ping
    while True:
            process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode == 0:
                    print (Fore.GREEN + f"{ip_address} online")
                    break
            print(Fore.RED + f"{ip_address} not responding...")
#    print (Fore.GREEN + f"F300 back online at {ip_address}.")
    time.sleep(5)

    site = formatted_devicename[:3]

    #Print labels for the devices
#    print(Fore.GREEN + "Printing label for F300 radio")
    print_v1.print_label_switch(ext,ip_address,"device",site,mac_address)
#    print(Fore.GREEN + "Printing label for F300 box")
    print_v1.print_label_switch(ext,ip_address,"box",site,mac_address)

    #Continue the ping checks
    while True:
            process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode == 0:
#                    print (Fore.GREEN + f"{ip_address} online")
                    break
#            print(Fore.RED + f"{ip_address} not responding...")

#    print(Fore.GREEN + f"Now online at {ip_address}")

    # Ping SMC and try get a response
    attempt_count = 0

    # Loop up to 5 times

    while attempt_count < 15:
        process = subprocess.Popen(['ping', '-c', '1', '10.255.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode

        if returncode == 0:
#            print(Fore.GREEN + "10.255.0.1 online")
            smc_ping = "Success"
            break
       # else:
#            print(Fore.RED + "10.255.0.1 not responding...")

        # Increment the counter
        attempt_count += 1

    # If ping fails after 5 attempts
    if attempt_count == 15 and returncode != 0:
        smc_ping = "Fail"


#    print("Final Checks")

    snmptrap = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.5.6.0")
    if snmp_trap_community in snmptrap:
        print (Fore.GREEN + "SNMP Trap Community is correct")
    else:
        print (Fore.RED + "SNMP Trap Community is wrong!")
        quit()
    snmpname = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.5.3.0")
    if formatted_devicename in snmpname:
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
    device_name = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.3.6.1.2.0")
    if formatted_devicename in device_name:
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
    #gsheet.add_to_sheet(serial_number, mac_address, formatted_devicename, ip_address, fwv, hardware, smc_ping)
#    print("Updated Google Sheet 'RP3 Data'")
    configured_aps.append(ext)
    print(f'Finished AP{ext}')




######################################################################################################################################################################################
#START
######################################################################################################################################################################################
os.system("sudo ip address add 192.168.0.1/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to range IP 192.168.0.X

start = time.time() #Lets see how long this takes?

print("A F300-25 may not be needed for every AP.")
print("Enter the AP numbers (comma-separated) that require a Force300-25. For example: 1,2,4,6,8,11")
ap_input = input("Enter APs: ")
ap_list_str = ap_input.split(',')
ap_list = [int(num) for num in ap_list_str]

# Set a pool of IP addresses to use
ip_pool = [f"192.168.0.{i}" for i in range(201, 246)]
ip_queue = Queue()
for ip in ip_pool:
    ip_queue.put(ip)

# Define a function to run the script with threading and IP management
def run_process(ap, ip_queue):
    ip_address = ip_queue.get()  # Block if no IPs are available
    devicename = "GWK_F300-25SM_APXXXX_IP_Y_Z"
    new_devicename = devicename.replace("XXXX", f"{ap}").replace("Y", "3").replace("Z", f"{ap}1")
    try:
        #if gsheet.check_device_number_exists(f'AP{ap}', new_devicename):
        #    skipped_aps.append(ap)
        #    print(f"EXT {ap} already exists in Google Sheet. Skipping.")
        #else:
            f300_16(ap, ip_address)
    finally:
        ip_queue.put(ip_address)  # Return the IP to the pool

# Create a list to hold all skipped extensions
skipped_aps = []
threads = []
configured_aps = []

# Start the threads, ensuring no more than the number of IPs are running concurrently
for ap in ap_list:
    while True:
        if is_device_available("192.168.0.2") and threading.active_count() <= 25:
            thread = threading.Thread(target=run_process, args=(ap,ip_queue))
            thread.start()
            threads.append(thread)  # Add thread to list for later join()
            break
        else:
            if threading.active_count() > 25:
                print("Maximum concurrent configurations reached, waiting...")
            elif not is_device_available("192.168.0.2"):
                print("Device not available, retrying in 10 seconds...")
            time.sleep(5)  # Wait 5 seconds before checking again

    time.sleep(60)  # Wait 60 seconds before starting the next device configuration

# Wait for all threads to complete
for thread in threads:
    thread.join()

print("\nSuccessfully configured APs:")
for ap in configured_aps:
    print(f"AP{ap}")

print("\nSummary of Skipped APs:")
for ap in skipped_aps:
    print(f"EXT {ap} was skipped.")



######################################################################################################################################################################################
#END
######################################################################################################################################################################################









