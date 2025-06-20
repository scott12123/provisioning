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
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)

def Restart_Configuration():
    with open('cambium/nbn-f300-25-remote-config-file-gen.py') as file:
         exec(file.read())

#site = "Pormpuraaw"
site = input("Enter Community: ")
print(f"Setup for {site}")
community_name = site
device_name = input("Enter Device Name: ")
ip_address = input("Enter IP Address: ")

#Create config file from base template
config_pi_ip = '192.168.0.50'
pi_username = 'pi'
pi_password = 'raspberry'
current_time = int(time.time())
source = '/mnt/usbstick/nbn/NBN-Generic-Force300-25-IP-10.255.0.216-v2.0.json'
dest = f"/mnt/usbstick/nbn/{device_name}-{ip_address}_{current_time}.txt"
command = f"sudo cp {source} {dest} && sudo sed -i 's/10.255.0.216/{ip_address}/g' {dest} && sudo sed -i 's/GEN_300-25_EXTxxxx_IP_x_x/{device_name}/g' {dest} && sudo sed -i 's/SNMP_SiteName/{community_name}/g' {dest}"
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

print(f"Config created for {community_name}, {device_name},{ip_address}")
print("Restarting script...")

Restart_Configuration()