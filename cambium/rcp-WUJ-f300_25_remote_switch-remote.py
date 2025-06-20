#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
from datetime import datetime
import os
import re
import logging
import sys
import threading
from queue import Queue
import urwid
from urwid import SimpleFocusListWalker, ListBox, Text
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import json

sys.path.append('/home/pi/provisioningpi/brother') #for label scripts
sys.path.append('/home/pi/provisioningpi/common') #for common files/scripts

import functions
import gsheet
import print_v1

import subprocess
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
timeout = time.time() + 60*10

config_file = "http://192.168.0.50/rcp3/RCP3-Generic-Force300-25-IP-10.255.0.216.json" #Shouldn't need changing
config_file_ip = "10.255.0.216" #Shouldnt need changing unless IP address in the config file changes.
firmware_file = "http://192.168.0.50/firmware/ePMP-AC-v4.7.0.1.img"
devicename = "WUJ_F300-25SM_EXTXXXX_IP_Y_Z" #Edit this for each site
snmp_trap_community = "SNMP_Wujal_Wujal" #Edit for each site

#############################

chromedriver_path = '/usr/bin/chromedriver'
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

os.system("sudo ip address add 192.168.0.1/24 dev eth0 > /dev/null 2>&1") #Add IP for connectivity to range IP 192.168.0.X

skipped_exts = []
threads = []

def device_status(mac_address, status):
    file_path = "cambium/configure_logs.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "a") as file:
        file.write(f"{timestamp},{mac_address},{status}\n")

def initial_snmp_config(ip_address):
    password = functions.passwd('192.168.0.2')
    time.sleep(5) #Sleep briefly because without it often broke the next part

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

def is_device_available(ip_address):
    response = os.system(f"ping -c 1 {ip_address} > /dev/null 2>&1")
    return response == 0


def f300_16(ext, temp_ip_address):
    site = devicename[:3]
    try:
      macsnmpd = os.popen(f'snmpget -v 2c -c public 192.168.0.2 .1.3.6.1.4.1.17713.21.1.1.30.0')
      macsnmp = macsnmpd.read()
      mac_address = re.findall(r'"(.*?)"', macsnmp)[0]

      wmacsnmpd = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.5.0')
      wmacsnmp = wmacsnmpd.read()
      wmac_address = re.findall(r'"(.*?)"', wmacsnmp)[0]
      wmac_address = wmac_address.replace(':', '')
      mac_address = (f"{mac_address} {wmac_address}")

      device_status(mac_address, "Starting")
    except:
      pass
    ip_address, formatted_devicename = functions.switch_create_f300_extension(devicename,ext)
    initial_snmp_config(temp_ip_address)
    time.sleep(10)
    while True:
        if is_device_available(temp_ip_address):
            time.sleep(3)
            break
        else:
            time.sleep(2)

    #Hardware check - Make sure we're actually running a F300-25. We only check now in case the firmare is blocking SNMP access.
    time.sleep(10)

    stream = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.2.0')
    output = stream.read()

    if '36' in output:
            hardware = "F300-25"
    else:
            quit()

    #Fetch the MSN (SN)
    snsnmpd = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.31.0')
    snsnmp = snsnmpd.read()
    serial_number = re.findall(r'"(.*?)"', snsnmp)[0]

    macsnmpd = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.30.0')
    macsnmp = macsnmpd.read()
    mac_address = re.findall(r'"(.*?)"', macsnmp)[0]

    wmacsnmpd = os.popen(f'snmpget -v 2c -c publicreadonly {temp_ip_address} .1.3.6.1.4.1.17713.21.1.1.5.0')
    wmacsnmp = wmacsnmpd.read()
    wmac_address = re.findall(r'"(.*?)"', wmacsnmp)[0]
    wmac_address = wmac_address.replace(':', '')
    mac_address = (f"{mac_address} {wmac_address}")
    device_status(mac_address, "Updated SNMP")

    #Firmware - upgrade to 4.7.0.1 if necessary.
    while True:  # Outer loop to restart the process if necessary
        firmware = functions.snmpget(ip_address, ".1.3.6.1.4.1.17713.21.1.1.1.0")
        if '4.7.0.1' in firmware:
            device_status(mac_address, "Firmware Up To Date")
            break  # Exit the loop if no upgrade needed
        else:
            device_status(mac_address, "Updating Firmware")
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
                        break  # Exit the inner loop as upgrade is complete
                    else:
                        status_message = current_status

                    if current_status != last_status:
                        last_status = current_status

                if status_zero_count > 3:
                    time.sleep(10) #Wait for reboot to begin before starting ping
                    break  # Exit the inner loop to restart the firmware update
                time.sleep(1)  # Check for new status

            if 'rebooting' in status_message:
                device_status(mac_address, "Firmware Updated")
                time.sleep(5)
                break  # Exit the outer loop as the upgrade process is complete

    time.sleep(10)
    while True:
        if is_device_available(temp_ip_address):
            device_status(mac_address, "Updating Configuration")
            time.sleep(10)
            break
        else:
            time.sleep(2)

    #Create custom config from base config file
    hostname = '192.168.0.50'
    username = 'pi'
    password = 'raspberry'
    current_time = int(time.time())
    source = '/mnt/usbstick/rcp3/RCP3-Generic-Force300-25-IP-10.255.0.216.json'
    dest = f"/mnt/usbstick/rcp3/RCP3-{site}-Force300-25_{ext}_{ip_address}_{current_time}.json"
    command = f"sudo cp {source} {dest} && sudo sed -i 's/10.255.0.216/{ip_address}/g' {dest} && sudo sed -i 's/GEN_300-25_EXTxxxx_IP_x_x/{formatted_devicename}/g' {dest} && sudo sed -i 's/SNMP_SiteName/{snmp_trap_community}/g' {dest}"
    index = dest.find("/usbstick/")
    dest_config = dest[index + len("/usbstick/"):]
    client = paramiko.SSHClient()


    try:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
    finally:
        client.close()

    custom_config = f"http://192.168.0.50/{dest_config}"
    while True:
        importjsonconfig = os.system(f"snmpset -v 2c -c privatereadwrite {temp_ip_address} .1.3.6.1.4.1.17713.21.6.4.1.0 s {custom_config} .1.3.6.1.4.1.17713.21.6.4.4.0 i 1  > /dev/null 2>&1")
        last_status = None
        status_zero_count = 0

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
                    break
                else:
                    status_message = current_status

                if current_status != last_status:
                    last_status = current_status

            if status_zero_count > 8:
                break  # Exit the inner loop to restart the process

            time.sleep(1)  # Check for new status

        if 'rebooting' in status_message:
            time.sleep(10)
            device_status(mac_address, "Configuration Updated")
            time.sleep(5)
            break  # Exit the outer loop as the import process is complete

    time.sleep(10)
    while True:
            process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode == 0:
                    break
    time.sleep(5)

    site = formatted_devicename[:3]
    device_status(mac_address, "Printing Labels")
    print_v1.print_label_switch(ext,ip_address,"device",site,mac_address)

    while True:
            process = subprocess.Popen(['ping','-c' ,'1', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode == 0:
                    break
            
    attempt_count = 0
    while attempt_count < 15:
        process = subprocess.Popen(['ping', '-c', '1', '10.255.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        returncode = process.returncode

        if returncode == 0:
            smc_ping = "Success"
            break

        attempt_count += 1

    if attempt_count == 15 and returncode != 0:
        smc_ping = "Fail"


    fw = functions.snmpgeta8(ip_address,".1.3.6.1.4.1.17713.21.1.1.1.0")
    fwv = re.findall(r'"(.*?)"', fw)[0]


    gsheet.add_to_sheet(serial_number, mac_address, formatted_devicename, ip_address, fwv, hardware, smc_ping)
    device_status(mac_address, f"Completed as {ext}")


base_url = "http://192.168.0.200"
username = "admin"
password = "@ctiv8me"

driver = None

def switch_login():
    global driver
    print("Logging into switch...")
    if driver:
        try:  # Check if we are still logged in
            driver.get(base_url + "/home.html")  
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "logout-btn")))
            return driver
        except TimeoutException:
            driver.quit()

    driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    try:
        driver.get(base_url)
        login_area = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "login-area"))
        )
        username_field = login_area.find_element(By.CSS_SELECTOR, "div[widget='textbox'] input[type='text']")
        username_field.send_keys(username)
        password_field = login_area.find_element(By.CSS_SELECTOR, "div[widget='password'] input[type='password']")
        password_field.send_keys(password)
        login_button = login_area.find_element(By.ID, "login-btn")
        login_button.click()
        print("Login successful.")
        return driver
    except TimeoutException:
        return None


def fetch_mac_address_table():
    global driver
    try:
        nav_menu = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "navigator"))
        )
        l2_features_link = nav_menu.find_element(By.CSS_SELECTOR, "li[data-index='1'] a")
        l2_features_link.click()
        menu_widget = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "menu-widget"))
        )
        switching_menu_item = menu_widget.find_element(By.CSS_SELECTOR, "a[module='switching']")
        switching_menu_item.click()
        submenu_switching = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "ul.mu2.nd"))
        )
        mac_address_submenu_item = submenu_switching.find_element(By.CSS_SELECTOR, "li[data-index='0,2'] a")
        mac_address_submenu_item.click()
        submenu_switching = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "table"))
        )

        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        address_table_section = soup.find('span', text='Address Table')
        if address_table_section:
            tables = soup.find_all('table')
            if len(tables) > 1:
                data_table = tables[1]
                rows = []
                for row in data_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) > 3:
                        mac_address = cells[1].text.strip()
                        mac_address = re.sub(r'[^a-fA-F0-9]', '', mac_address).upper()  # Remove non-hex characters and convert to uppercase
                        port_full = cells[3].text.strip()
                        port_number = port_full.split('/')[-1]  # Extract last number from port

#                       if cells[2].text.strip() == '1': #Dont return when on vlan500
                        rows.append({
                            'mac_address': mac_address,
                            'port_number': int(port_number)  # Convert port_number to int for sorting
                        })

                rows.sort(key=lambda x: x['port_number'])  # sort by port_number
                file_path = '/home/pi/provisioningpi/cambium/mac_address_table.txt'
                with open(file_path, 'w') as f:
                    json.dump(rows, f, indent=4)
                return rows
            else:
                return [("Less than two tables found on the page.", "")]
        else:
            return [("Address Table section not found.", "")]
    except TimeoutException:
        return [("Fetching data timed out.", "")]



def update_data(loop, user_data=None):
    try:
        global driver
        data_listbox = urwid.ListBox(urwid.SimpleFocusListWalker([]))

        if not driver:
            driver = switch_login()
            if not driver:
                return

        fetch_mac_address_table()

        mac_address_file = '/home/pi/provisioningpi/cambium/mac_address_table.txt'
        logs_file = '/home/pi/provisioningpi/cambium/configure_logs.txt'

        if not os.path.exists(mac_address_file):
            return

        if not os.path.exists(logs_file):
            return

        with open(mac_address_file, 'r') as f:
            mac_data = json.load(f)

        with open(logs_file, 'r') as f:
            log_data = f.readlines()

        data_listbox.body.clear()

        header = urwid.Text("PORT".ljust(7) + "MAC ADDRESS".ljust(20) + "STATUS".ljust(30) + "UPDATED TIMESTAMP")
        data_listbox.body.append(header)

        for entry in mac_data:
            mac_address = entry['mac_address']
            port_number = str(entry['port_number'])

            latest_log = None
            updated_timestamp = None
            for log_entry in log_data[::-1]:
                log_parts = log_entry.strip().split(',')
                if len(log_parts) == 3 and mac_address in log_parts[1].strip():
                    latest_log = log_parts[2].strip()
                    updated_timestamp = datetime.strptime(log_parts[0].strip(), '%Y-%m-%d %H:%M:%S')
                    break
            status_text = latest_log if latest_log else "No configure log found"
            timestamp_text = updated_timestamp.strftime('%Y-%m-%d %H:%M:%S') if updated_timestamp else "N/A"
            row_text = f"{port_number.ljust(7)}{mac_address.ljust(20)}{status_text.ljust(30)}{timestamp_text}"
            data_listbox.body.append(urwid.Text(row_text))

        loop.widget = data_listbox
        loop.set_alarm_in(3, update_data)

    except Exception as e:
        print(f"Error in update_data: {str(e)}")

def run_process(ext,ip_queue):
    ip_address = ip_queue.get()
    try:
        if gsheet.check_device_number_exists(ext, devicename):
           skipped_exts.append(ext)
        else:
            f300_16(ext, ip_address)
    finally:
        ip_queue.put(ip_address)

def loop_ext_configuration(ext_start, ext_end):
    global threads, skipped_exts
    # Set a pool of IP addresses to use
    ip_pool = [f"192.168.0.{i}" for i in range(201, 246)]
    ip_queue = Queue()
    for ip in ip_pool:
        ip_queue.put(ip)

    for ext in range(ext_start, ext_end + 1):
        while True:
            if is_device_available("192.168.0.2") and threading.active_count() <= 25:
                thread = threading.Thread(target=run_process, args=(ext,ip_queue))
                thread.start()
                threads.append(thread)  # Add thread to list for later join()
                break
            else:
                time.sleep(5)  # Wait 5 seconds before checking again
        time.sleep(60)  # Wait 60 seconds before starting the next device configuration

def main():
    global threads, skipped_exts
    try:
        ext_start = int(input("EXT Start: "))
        ext_end = int(input("EXT End: "))

        ext_thread = threading.Thread(target=loop_ext_configuration, args=(ext_start, ext_end,))
        ext_thread.start()

        update_data_loop = urwid.MainLoop(urwid.ListBox(urwid.SimpleFocusListWalker([])), palette=[('reversed', 'standout', '')])
        update_data(update_data_loop)
        update_data_loop.run()

    finally:
        if driver:
            driver.quit()

        for thread in threads:
            thread.join()

        print("\nSummary of Skipped EXTs:")
        for ext in skipped_exts:
            print(f"EXT {ext} was skipped.")

if __name__ == "__main__":
    main()