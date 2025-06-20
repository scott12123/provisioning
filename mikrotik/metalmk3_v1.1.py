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
#logging.basicConfig(filename='mikrotik/metal.log', filemode='a', format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s', datefmt='%H:%M:%S', level=logging.INFO)

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
	try:
	 client = paramiko.client.SSHClient()
	 client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	 client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
	 stdin, stdout, stderr = client.exec_command(cmd)
	 output = stdout.read().decode()  # Decode bytes to string
	 return output
	except Exception as e:
         return f"Error: {e}"
	finally:
         client.close()

def command_noalert(hostname, password, cmd):
    username = "admin"
    try:
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password, banner_timeout=60, timeout=60, auth_timeout=60)
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode()  # Decode bytes to string
        return output
    except Exception as e:
        return f"Error: {e}"
    finally:
        client.close()


#Run pings to see if any microtik is connected
print (Fore.GREEN + "Checking if Mikrotik is connected on different IPs")
while True:
	process = subprocess.Popen(['ping','-c' ,'1', '192.168.88.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "192.168.88.1 online")
		break
	print(Fore.RED + "192.168.88.1 not responding...")
	process = subprocess.Popen(['ping','-c' ,'1', '10.255.0.20'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		print (Fore.GREEN + "10.255.0.20 online")
		print (Fore.CYAN + "Looks like this router is already configured..")

		output = command_noalert('10.255.0.20', 'yph546DKDUmsyCEJ', 'file print')
		if 'changelog_v1.1' in output:  # Compare with a string
			print("Currently on v1.1")
			print ('\a')
			time.sleep(1)
			print ('\a')
		else:
			print("Unsure of version. Likely v1.0")
			print ('\a')
			time.sleep(1)
			print ('\a')
		user_input = input(Fore.CYAN + 'Do you want to reset router? (y/n): ')
		if user_input.lower() == 'y':
			print(Fore.CYAN + 'Resetting the router!')
			output = command('10.255.0.20','yph546DKDUmsyCEJ','system reset-configuration')
			time.sleep(10)
			os.execl(sys.executable, sys.executable, *sys.argv)
		elif user_input.lower() == 'n':
			print(Fore.CYAN + 'Plug in a different router and start again')
			time.sleep(10)
			os.execl(sys.executable, sys.executable, *sys.argv)
		else:
    			print(Fore.CYAN + 'Type y or n')
		break
	print(Fore.RED + "10.255.0.20 not responding...")

####HARDWARE CHECK
print (Fore.GREEN + "Checking Hardware")
start = time.time()
output = command('192.168.88.1','','system resource print')
serial = (output[141:152])


if 'board-name: Metal 52 ac' in output:
        print("Mikrotik Metal 52 ac. Continuing upgrade")
else:
	print("Hardware/Config File Mismatch!!!")
	print("Check you're running the right config file")
	quit()

#Add changelog to /flash so we know what was loaded on previously
print (Fore.GREEN + "Adding config version changelog to /flash")
ftp_client=auth('192.168.88.1','').open_sftp()
ftp_client.put('mikrotik/metal-changelog_v1.1.txt','flash/metal-changelog_v1.1.txt')
print(Fore.GREEN + "Upload successful")
ftp_client.close()

#Check current package before upgrading
print (Fore.GREEN + "Checking Current Software Versions")
output = command('192.168.88.1','','system package print')

#### ROUTEROS FIRMWARE UPGRADE
if 'routeros  7.8' in output:
	print(Fore.GREEN + "RouterOS is already on 7.8")
else:
	#Connect SFTP and upload routerOS
	print (Fore.RED + "RouterOS needs an update to 7.8")
	print (Fore.GREEN + "Connecting via SFTP..")
	ftp_client=auth('192.168.88.1','').open_sftp()
	print (Fore.GREEN + "Connected via SFTP. Uploading RouterOS v7.8")
	ftp_client.put('mikrotik/routeros-7.8-mipsbe.npk','routeros-7.8-mipsbe.npk')
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


####ROUTERBOARD FIRMWARE UPGRADE
output = command_noalert('192.168.88.1','','system routerboard print')

if 'current-firmware: 7.8' in output:
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


print (Fore.GREEN + "Removing default configuration and adding new configuration")
configoutput = command('192.168.88.1','','/system logging set action=disk numbers=0; /system logging set action=disk numbers=1; /system logging set action=disk numbers=2; /ip pool remove 0; /ip dhcp-server remove 0; /ip dhcp-client remove 0; /ip dhcp-server network remove 0; /ip dns set allow-remote-requests=no; /ip dns static remove 0; /ip firewall filter remove 11; /ip firewall filter remove 8; /ip firewall filter remove 7; /ip firewall filter remove 6; /ip firewall filter remove 5; /ip firewall nat remove 0; /interface wireless set wlan1 band=2ghz-b/g/n channel-width=20/40mhz-XX mode=ap-bridge ssid="Activ8me Hotspot" country=australia frequency=auto; /interface bridge add name=bridge-vlan501; /ip firewall filter add action=drop chain=input comment="Disable Wireless Input" in-interface=bridge-vlan501; /ip firewall filter add action=accept chain=forward comment="Allow Forward"; /interface vlan add interface=ether1 name=eth1-vlan500 vlan-id=500; /interface vlan add interface=ether1 name=eth1-vlan501 vlan-id=501; /ip address add address=10.255.0.20/24 comment=defconf interface=eth1-vlan500 network=10.255.0.0; /interface bridge port add bridge=bridge-vlan501 interface=eth1-vlan501; /interface bridge port add bridge=bridge-vlan501 interface=wlan1; /ip dns set servers=8.8.8.8,8.8.4.4; /ip route add distance=1 gateway=10.255.0.1; /ip service set telnet disabled=yes; /ip service set ftp disabled=yes; /ip service set ssh address=10.255.0.0/24; /ip service set api disabled=yes; /ip service set winbox address=10.255.0.0/24; /ip service set api-ssl disabled=yes; /ip service set www-ssl disabled=no; /ip service set www disabled=no; /system clock set time-zone-name=Australia/Melbourne; /system identity set name=AP1; /system ntp client set enabled=yes server=10.255.0.1,139.180.160.82; /system routerboard settings set protected-routerboot=disabled')
print ("Error Log:"+ configoutput)
#print (output.decode('utf-8'))
time.sleep(2)

print (Fore.GREEN + "Removing IP 192.168.88.1")
command('10.255.0.20','','/ip address remove 0')
print (Fore.GREEN + "Now only accessible over VLAN500 at 10.255.0.20")
time.sleep(5)


#Checking ping on 10.255.0.20
print (Fore.CYAN + "Checking ping to 10.255.0.20")
while True:
	if os.system('ping 10.255.0.20 -c 1') == 0 or time.time() > timeout:
		print(Fore.GREEN + 'Mikrotik is connected... proceeding')
		break
	print(Fore.RED + "Still offline...trying again")

#Update password
print (Fore.GREEN + "Updating admin password")
output = command('10.255.0.20','','user set admin password=yph546DKDUmsyCEJ')
time.sleep(5)

print ("******************Final Checks******************")
if configoutput == "":
	print (Fore.GREEN + "No error while loading configuration")
else:
	print (Fore.RED + "Configuration Errors:"+ configoutput)
	quit()

output = command('10.255.0.20','yph546DKDUmsyCEJ','system package print')
if 'routeros  7.8' in output:
        print(Fore.GREEN + "RouterOS is already on 7.8")
else:
	print (Fore.RED + "RouterOS needs an update")
	print (f"{output}")
	quit()

output = command_noalert('10.255.0.20','yph546DKDUmsyCEJ','system routerboard print')
if 'current-firmware: 7.8' in output:
        print (Fore.GREEN + "RouterBoard V7.8")
else:
	print (Fore.RED + "Check Routerboard Version! Not V7.8")
	quit()

output = command_noalert('10.255.0.20','yph546DKDUmsyCEJ','interface wireless print')
if 'ssid="Activ8me Hotspot"' in output:
        print (Fore.GREEN + "SSID = Activ8me Hotspot")
else:
	print (Fore.RED + "SSID is incorrect!!")
	quit()

output = command_noalert('10.255.0.20','yph546DKDUmsyCEJ','interface vlan print')
if 'eth1-vlan500' in output:
	print (Fore.GREEN + "VLAN500 Configured")
else:
	print (Fore.RED + "No VLAN500!!")
	quit()

if 'eth1-vlan501' in output:
        print (Fore.GREEN + "VLAN501 Configured")
else:
	print (Fore.RED + "No VLAN501!!")
	quit()

output = command_noalert('10.255.0.20','yph546DKDUmsyCEJ','ip address print')
if '10.255.0.20/24' in output:
        print (Fore.GREEN + "10.255.0.20 Configured")
else:
	print (Fore.RED + "Check IP Configuration!!")
	quit()

if '192.168.88' in output:
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
time.sleep(1)
print ('\a')

print ('Restart? Plug in another Mikrotik Metal 52 with default IP')
print ('Or press Ctrl+Z to exit')
#while True:
#	if os.system('ping 192.168.88.1 -c 1') == 0:
#        	os.execl(sys.executable, sys.executable, *sys.argv)
#	print(Fore.MAGENTA + "Plug another router in or press ctrl+z .... checking again")


while True:
	process = subprocess.Popen(['ping','-c' ,'1', '192.168.88.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		os.execl(sys.executable, sys.executable, *sys.argv)
	print(Fore.RED + "192.168.88.1 not responding...")
	process = subprocess.Popen(['ping','-c' ,'1', '10.255.0.20'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	returncode = process.returncode
	if returncode == 0:
		os.execl(sys.executable, sys.executable, *sys.argv)
	print(Fore.MAGENTA + "Plug another router in or press ctrl+z .... checking again")
