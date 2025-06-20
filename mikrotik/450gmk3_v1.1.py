#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import logging
import sys
import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
logging.basicConfig(filename='mikrotik/450g.log', filemode='a', format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s', datefmt='%H:%M:%S', level=logging.INFO)

timeout = time.time() + 60*10

#Connect SSH and run command

def auth(hostname, password):
	print (Fore.CYAN + "brb.")
	username = "admin"
	client = paramiko.client.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
	return client

def command(hostname, password, cmd):
	print (Fore.CYAN + "brb.")
	username = "admin"
	client = paramiko.client.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
	stdin, stdout, stderr = client.exec_command(cmd)
	output = stdout.read()
	return output

def command_noalert(hostname, password, cmd):
	username = "admin"
	client = paramiko.client.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
	stdin, stdout, stderr = client.exec_command(cmd)
	output = stdout.read()
	return output

print(Fore.RED + "NOTE:")
print(Fore.RED + "Must be powered by power cable, not POE")
print(Fore.RED + "Ethernet must be plugged from Pi into ETHER5 (Port furthest from power plug)")

print (Fore.GREEN + "Checking if Mikrotik is connected on different IPs")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', '192.168.88.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "192.168.88.1 online")
		break
	print(Fore.RED + "192.168.88.1 not responding...")
	process = subprocess.Popen(['ping','-c' ,'1', '10.255.0.5'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "10.255.0.5 online")
		print (Fore.CYAN + "Looks like this router is already configured..")
		output = command('10.255.0.5','yph546DKDUmsyCEJ','file print')
		if 'changelog_v1.1' in output:
			print("Currently on v1.1")
			print ('\a')
			time.sleep(1)
			print ('\a')
		else:
			print ("Unsure of version. Likely v1.0")
			print ('\a')
			time.sleep(1)
			print ('\a')
		user_input = input(Fore.CYAN + 'Do you want to reset router? (y/n): ')
		if user_input.lower() == 'y':
			print(Fore.CYAN + 'Resetting router!')
			output = command('10.255.0.5','yph546DKDUmsyCEJ','system reset-configuration')
			time.sleep(10)
			os.execl(sys.executable, sys.executable, *sys.argv)
		elif user_input.lower() == 'n':
			print (Fore.CYAN + 'Plug in a different router and start again')
			time.sleep(10)
			os.execl(sys.executable, sys.executable, *sys.argv)
		else:
			print(Fore.CYAN + 'Type y or n')
		break
	print(Fore.RED + "10.255.0.5 not responding...")

#HARDWARE CHECK
print (Fore.GREEN + "Checking Hardware")
start = time.time()
output = command('192.168.88.1','','system resource print')
serial = (output[141:152])

if b'board-name: RB450Gx4' in output:
        print("Mikrotik RB450Gx4. Continuing upgrade")
else:
	print("Hardware/Config File Mismatch!!!")
	print("Check you're running the right config file")
	quit()

#Add changelog to /flash so we know what was loaded on previously
print (Fore.GREEN + "Adding config version changelog to /flash")
ftp_client=auth('192.168.88.1','').open_sftp()
ftp_client.put('mikrotik/450g-changelog_v1.1.txt','450g-changelog_v1.1.txt')
print(Fore.GREEN + "Upload successful")
ftp_client.close()

#Check current package before upgrading
print (Fore.GREEN + "Checking Current Software Versions")
output = command('192.168.88.1','','system package print')

#ROUTEROS FIRMWARE UPGRADE
if b'routeros  7.8' in output:
	print(Fore.GREEN + "RouterOS arm is already on 7.8")
else:
	#Connect SFTP and upload routerOS
	print (Fore.RED + "RouterOS needs an update")
	print (Fore.GREEN + "Connecting via SFTP..")
	ftp_client=auth('192.168.88.1','').open_sftp()
	print (Fore.GREEN + "Connected via SFTP. Uploading RouterOS arm v7.8")
	ftp_client.put('mikrotik/routeros-7.8-arm.npk','routeros-7.8-arm.npk')
	print(Fore.GREEN + "Upload successful")
	ftp_client.close()
	print (Fore.GREEN + "Closed SFTP Session")

	#Reboot to install RouterOS
	print (Fore.GREEN + "Rebooting for RouterOS upgrade..")
	command('192.168.88.1','','system reboot')
	#waiting for reboot
	time.sleep(5)

	while True:
		if os.system('ping 192.168.88.1 -c 1') == 0 or time.time() > timeout:
			print(Fore.GREEN + 'Mikrotik is connected... proceeding')
			break
		print(Fore.RED + "Still offline...trying again")

#ROUTERBOARD FIRMWARE UPGRADE
output = command_noalert('192.168.88.1','','system routerboard print')

if b'current-firmware: 7.8' in output:
        print(Fore.GREEN + "RouterBoard is already on 7.8")
else:
	#Upgrade RouterBoard then reboot
	print (Fore.RED + "RouterBoard needs an update")
	print (Fore.GREEN + "Upgrading RouterBoard")
	output = command('192.168.88.1','','system routerboard upgrade')
	print (Fore.GREEN + "Rebooting for RouterBoard upgrade.. standby")
	output = command('192.168.88.1','','system reboot')

	#waiting for reboot
	time.sleep(5)

	while True:
                if os.system('ping 192.168.88.1 -c 1') == 0 or time.time() > timeout:
                        print(Fore.GREEN + 'Mikrotik is connected... proceeding')
                        break
                print(Fore.RED + "Still offline...trying again")

print ("*********************************UPDATE CONFIGURATION V1.1*********************************")
print (Fore.GREEN + "CONFIGURATION PART 1 - Connecting on 192.168.88.1")
part1output = command('192.168.88.1','','/system logging set action=disk numbers=0; /system logging set action=disk numbers=1; /system logging set action=disk numbers=2; /ip pool remove 0; /ip dhcp-server remove 0; /ip dhcp-client remove 0; /ip dhcp-server network remove 0; /ip dns set allow-remote-requests=no; /ip dns static remove 0; /ip firewall filter remove 11; /ip firewall filter remove 10; /ip firewall filter remove 9; /ip firewall filter remove 8; /ip firewall filter remove 7; /ip firewall filter remove 6; /ip firewall filter remove 5; /ip firewall filter remove 4; /ip firewall filter remove 3; /ip firewall filter remove 2; /ip firewall filter remove 1; /ip firewall nat remove 0; /interface bridge add name=bridge-vlan500; /interface bridge add name=bridge-vlan501; /interface bridge add name=bridge-vlan521; /interface bridge add name=bridge-vlan522; /interface vlan add interface=ether1 name=eth1-vlan500 vlan-id=500; /interface vlan add interface=ether1 name=eth1-vlan501 vlan-id=501; /interface vlan add interface=ether1 name=eth1-vlan521 vlan-id=521; /interface vlan add interface=ether1 name=eth1-vlan522 vlan-id=522; /interface vlan add interface=ether5 name=eth5-vlan500 vlan-id=500; /interface vlan add interface=ether5 name=eth5-vlan501 vlan-id=501; /ip address add address=10.255.0.5/24 comment=defconf interface=bridge-vlan500 network=10.255.0.0; /interface bridge port add bridge=bridge-vlan500 interface=eth1-vlan500; /interface bridge port add bridge=bridge-vlan500 interface=eth5-vlan500; /interface ethernet set [ find default-name=ether1 ] mac-address=6C:3B:6B:53:F0:D5; /interface ethernet set [ find default-name=ether2 ] mac-address=6C:3B:6B:53:F0:D6; /interface ethernet set [ find default-name=ether3 ] mac-address=6C:3B:6B:53:F0:D7; /interface ethernet set [ find default-name=ether4 ] mac-address=6C:3B:6B:53:F0:D8; /interface ethernet set [ find default-name=ether5 ] mac-address=6C:3B:6B:53:F0:D9;')
print ("Error Log:"+ part1output.decode('utf-8'))
time.sleep(2)
if part1output.decode('utf-8') == "":
        print (Fore.GREEN + "No error while loading part 1 configuration")
else:
        print (Fore.RED + "Configuration Errors:"+ part1output.decode('utf-8'))
        quit()

print (Fore.GREEN + "CONFIGURATION PART 2 - Reconnecting on 10.255.0.5")

#Checking ping on 10.255.0.10
print (Fore.CYAN + "Checking ping to 10.255.0.5")
while True:
        if os.system('ping 10.255.0.5 -c 1') == 0 or time.time() > timeout:
                print(Fore.GREEN + 'Mikrotik is connected... proceeding')
                break
        print(Fore.RED + "Still offline...trying again")

part2output = command('10.255.0.5','','/interface bridge port remove 0; /interface bridge port remove 1; /interface bridge port remove 2; /interface bridge port remove 3; /interface bridge remove bridge; /ip address remove 0; /interface bridge port add bridge=bridge-vlan500 interface=ether4; /interface bridge port add bridge=bridge-vlan501 interface=eth1-vlan501; /interface bridge port add bridge=bridge-vlan501 interface=eth5-vlan501; /interface bridge port add bridge=bridge-vlan521 interface=ether1 hw=no; /interface bridge port add bridge=bridge-vlan521 interface=ether2 hw=no; /interface bridge port add bridge=bridge-vlan521 interface=eth1-vlan521; /interface bridge port add bridge=bridge-vlan522 interface=eth1-vlan522; /interface bridge port add bridge=bridge-vlan522 interface=ether3 hw=no; /ip dns set servers=8.8.8.8,8.8.4.4; /ip route add distance=1 gateway=10.255.0.1; /ip service set telnet disabled=yes; /ip service set ftp disabled=yes; /ip service set www-ssl disabled=no; /ip service set www disabled=no; /ip service set ssh address=10.255.0.0/24; /ip service set api disabled=yes; /ip service set winbox address=10.255.0.0/24; /ip service set api-ssl disabled=yes; /system clock set time-zone-name=Australia/Melbourne; /user set admin password=yph546DKDUmsyCEJ; /system identity set name=450Gx4; /system ntp client set enabled=yes server=10.255.0.1,139.180.160.82; /system routerboard settings set protected-routerboot=disabled; /tool mac-server set allowed-interface-list=all; /tool mac-server mac-winbox set allowed-interface-list=all; /interface ethernet poe set ether5 poe-out forced-on;')
print ("Error Log:"+ part2output.decode('utf-8'))
if part2output.decode('utf-8') == "":
        print (Fore.GREEN + "No error while loading part 2 configuration")
else:
        print (Fore.RED + "Configuration Errors:"+ part2output.decode('utf-8'))
        quit()
print("10s sleep")
time.sleep(10)

print ("******************Final Checks******************")
#Checking software
output = command_noalert('10.255.0.5','yph546DKDUmsyCEJ','system package print')

#### ROUTEROS FIRMWARE UPGRADE
if b'routeros  7.8' in output:
        print(Fore.GREEN + "RouterOS arm is already on 7.8")
else:
        #Connect SFTP and upload routerOS
	print (Fore.RED + "RouterOS needs an update")
	quit()

output = command_noalert('10.255.0.5','yph546DKDUmsyCEJ','system routerboard print')
if 'current-firmware: 7.8' in output:
        print (Fore.GREEN + "RouterBoard V7.8")
else:
	print (Fore.RED + "Check Routerboard Version! Not V7.8")
	quit()

#Checking timezone
output = command_noalert('10.255.0.5','yph546DKDUmsyCEJ','system clock print')
if b'time-zone-name: Australia/Melbourne' in output:
        print (Fore.GREEN + "Timezone = Australia/Melbourne")
else:
	print (Fore.RED + "Timezone not Melbourne")
	quit()

#Checking PoE Forced On
output = command_noalert('10.255.0.5','yph546DKDUmsyCEJ','interface ethernet poe print')
if b'ether5  forced-on' in output:
        print (Fore.GREEN + "PoE Forced-on Configured")
else:
	print (Fore.RED + "PoE Not Forced On")
	quit()

#Checking VLANS are correct
output = command_noalert('10.255.0.5','yph546DKDUmsyCEJ','interface vlan print')
if b'eth1-vlan500' in output:
        print (Fore.GREEN + "ETH1-VLAN500 Configured")
else:
	print (Fore.RED + "No ETH1-VLAN500!!")
	quit()
if b'eth1-vlan501' in output:
        print (Fore.GREEN + "ETH1-VLAN501 Configured")
else:
	print (Fore.RED + "No ETH1-VLAN501!!")
	quit()
if b'eth1-vlan521' in output:
        print (Fore.GREEN + "ETH1-VLAN521 Configured")
else:
	print (Fore.RED + "No ETH1-VLAN521!!")
	quit()
if b'eth1-vlan522' in output:
        print (Fore.GREEN + "ETH1-VLAN522 Configured")
else:
	print (Fore.RED + "No ETH1-VLAN522!!")
	quit()
if b'eth5-vlan500' in output:
        print (Fore.GREEN + "ETH5-VLAN500 Configured")
else:
	print (Fore.RED + "No ETH5-VLAN500!!")
	quit()
if b'eth5-vlan501' in output:
        print (Fore.GREEN + "ETH5-VLAN501 Configured")
else:
	print (Fore.RED + "No ETH5-VLAN501!!")
	quit()

#Checking IPs are correct
output = command_noalert('10.255.0.5','yph546DKDUmsyCEJ','ip address print')
if b'10.255.0.5/24' in output:
        print (Fore.GREEN + "10.255.0.5 Configured")
else:
	print (Fore.RED + "Check IP Configuration!!")
	quit()

if b'192.168.88' in output:
	print (Fore.RED + "192.168.88.1 Still Configured!")
	quit()
else:
	print (Fore.GREEN + "Default IP Removed")


print ("*****************************************************************************************************")
#Check how long this process took..
end = time.time()
seconds = (end - start)
seconds = seconds % (24 * 3600)
hour = seconds // 3600
seconds %= 3600
minutes = seconds // 60
seconds %= 60
print ("Configuration Duration: %d:%02d:%02d" % (hour, minutes, seconds))

logging.info('Configured %s',serial)

#Finished
print ("***********************************************Finished!***********************************************")
print ("******************************************Closing SSH Session******************************************")
#Play alert bell
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(1)
print ('\a')
time.sleep(20)
print ('Restart? Plug in another Mikrotik 450Gx4 with default IP')
print ('Or press Ctrl+Z to exit')

#while True:
#	if os.system('ping 192.168.88.1 -c 1') == 0:
#        	os.execl(sys.executable, sys.executable, *sys.argv)
#	print(Fore.MAGENTA + "Plug another router in or press ctrl+z .... checking again")

while True:
        process = subprocess.Popen(['ping','-c' ,'1', '192.168.88.1'], stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                os.execl(sys.executable, sys.executable, *sys.argv)
        print(Fore.RED + "192.168.88.1 not responding...")
        process = subprocess.Popen(['ping','-c' ,'1', '10.255.0.5'], stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode
        if returncode == 0:
                os.execl(sys.executable, sys.executable, *sys.argv)
        print(Fore.MAGENTA + "Plug another router in or press ctrl+z .... checking again")
