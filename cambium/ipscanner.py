#!/usr/bin/env python3
import paramiko
import time
import os
import re
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
timeout = time.time() + 60*10
import concurrent.futures
import sys
import netifaces as ni
sys.path.append('provisioningpi/common') #for common files/scripts
import functions

os.system("sudo ip address add 192.168.0.1/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to default IP 192.168.0.2

def Configure():
    with open('configure.py') as file:
         exec(file.read())

def get_eth0_ips():
    try:
        # Retrieve all addresses for eth0
        addresses = ni.ifaddresses('eth0.500')
        # Extract IPv4 addresses
        ipv4_addresses = addresses[ni.AF_INET]
        # Extract just the IP addresses from the address info
        ip_list = [ip_info['addr'] for ip_info in ipv4_addresses]
        return ip_list
    except KeyError:
        print("eth0 not found or doesn't have any IPv4 addresses.")
        return []
    except ValueError:
        print("Error occurred while getting IP addresses.")
        return []

# Store eth0 IP addresses in a variable
eth0_ips = get_eth0_ips()

def scan_ip_range(start_ip, end_ip,excluded_ips=None):
    def is_ip_online(ip):
        response = subprocess.run(['ping', '-c', '1', '-W', '1', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ip if response.returncode == 0 else None

    if excluded_ips is None:
        excluded_ips = []

    start_last_octet = int(start_ip.split('.')[-1])
    end_last_octet = int(end_ip.split('.')[-1])
    base_ip = '.'.join(start_ip.split('.')[:-1])
    ips = [f"{base_ip}.{i}" for i in range(start_last_octet, end_last_octet + 1) if f"{base_ip}.{i}" not in excluded_ips]

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(is_ip_online, ip): ip for ip in ips}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                return result  # Return the first online IP found

    return None  # Return None if no online IP found


excluded = eth0_ips
print(f"eth0 IP Addresses: {eth0_ips}")
print("Make sure device is plugged in and had time to boot before running this script.")
print(f"Excluding IPs {excluded}")
input("Press Enter to start...")

ranges_to_scan = [
    ("169.254.1.1", "169.254.1.1"),
    ("192.168.0.2", "192.168.0.2"),
#    ("10.255.0.3", "10.255.0.9"),
    ("10.255.0.200", "10.255.0.254"),
    ("10.255.2.1", "10.255.2.254"),
    ("10.255.21.1", "10.255.21.199"),
    ("10.255.22.1", "10.255.22.199"),
    ("10.255.23.1", "10.255.23.199"),
    ("10.255.24.1", "10.255.24.199"),
    ("10.255.25.1", "10.255.25.199"),
    ("10.255.26.1", "10.255.26.199"),
    ("10.255.27.1", "10.255.27.199"),
    ("10.255.28.1", "10.255.28.199"),
    ("10.255.29.1", "10.255.29.199")
]

for start_ip, end_ip in ranges_to_scan:
    online_ip = scan_ip_range(start_ip, end_ip,excluded_ips=excluded)
    print (f"Scanning {start_ip}-{end_ip}")
    if online_ip:
        print(f"Online IP found: {online_ip}")
        break  # Stop scanning once an online IP is found

#Fetch the MSN (SN)
snsnmpd = os.popen(f"snmpget -v 2c -c SNMP-RO-ACT1v8me {online_ip} .1.3.6.1.4.1.17713.21.1.1.31.0")
snsnmp = snsnmpd.read()
serial_number = re.findall(r'"(.*?)"', snsnmp)
print(f"Confirm SN: {serial_number}")
functions.log(f"Found {online_ip}. SN: {serial_number}","IP_SCANNER")
input("Press Enter if you want to factory reset the device")
print("WARNING RESETTING DEVICE!!")
print("Press ctrl+c to cancel.")
time.sleep(5)
print("Beginning reset process!")
password = functions.passwd(online_ip)
time.sleep(5) #Sleep briefly because without it often broke the next part

#Overwriting SNMP because I dont know what config is in the device
print(Fore.GREEN + "Updating SNMP public and private community")
#username = "admin"
password = "!2mzPg$HzMjdZ2"

client = paramiko.client.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(online_ip, username="admin", password=password, banner_timeout=60, timeout=60, auth_timeout=60)
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

setfirmware = os.system(f"snmpset -v 2c -c privatereadwrite {online_ip} .1.3.6.1.4.1.17713.21.4.2.0 i 1 .1.3.6.1.4.1.17713.21.4.3.0 i 1 .1.3.6.1.4.1.17713.21.4.4.0 i 1 .1.3.6.1.4.1.17713.21.4.1.0 i 1 > /dev/null 2>&1")
functions.log(f"SN {serial_number} Factory Reset","IP_SCANNER")
print (Fore.GREEN + "Device reset, waiting for response on 192.168.0.2")
while True:
        process = subprocess.Popen(['ping','-c' ,'1', '192.168.0.2'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                print (Fore.GREEN + "192.168.0.2 online. Device confirmed reset.")
                print ('\a')
                break
        print(Fore.RED + "192.168.0.2 not responding...")
Configure() #open the configure automatically
