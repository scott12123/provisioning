#!/usr/bin/env python3
import paramiko
import os
import time
import datetime
import json

# Path to configured.json relative to this file
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configured.json')

#common functions for ongoing use

def switch_create_f300_extension(devicename,ext):
    valid_ranges = {
        (1001, 1199): 21,
        (2001, 2199): 22,
        (3001, 3199): 23,
        (4001, 4199): 24,
        (5001, 5199): 25,
        (6001, 6199): 26,
        (7001, 7199): 27,
        (8001, 8199): 28,
        (9001, 9199): 29
    }

    while True:
        ext_str = str(ext)
        if len(ext_str) == 4 and ext_str.isdigit():
            num = int(ext_str)
            third_octet = None
            # Make sure EXT is within ranges
            for range_tuple, octet_value in valid_ranges.items():
                if range_tuple[0] <= num <= range_tuple[1]:
                    third_octet = octet_value
                    break

            if third_octet is not None:
                # Valid EXT, get IP in correct subnet
                fourth_octet = str(int(ext_str[-3:]))  # Drop anyz eros 
                ip_address = f"10.255.{third_octet}.{fourth_octet}"

                formatted_devicename = devicename.replace('XXXX', str(num)) \
                                  .replace('Y', str(third_octet)) \
                                  .replace('Z', fourth_octet)

                return ip_address, formatted_devicename
            else:
                print("Number is not within the valid ranges.")
        else:
            print("Invalid input. Please enter a 4-digit number.")


def create_f300_extension(devicename):
    valid_ranges = {
        (1001, 1199): 21,
        (2001, 2199): 22,
        (3001, 3199): 23,
        (4001, 4199): 24,
        (5001, 5199): 25,
        (6001, 6199): 26,
        (7001, 7199): 27,
        (8001, 8199): 28,
        (9001, 9199): 29
    }

    while True:
        print("Extension must be within the range of 1001-1199, 2001-2199, 3001-3199 and so on, up to 9199.")
        number = input("Enter EXT: ")

        if len(number) == 4 and number.isdigit():
            num = int(number)
            third_octet = None
            # Make sure EXT is within ranges
            for range_tuple, octet_value in valid_ranges.items():
                if range_tuple[0] <= num <= range_tuple[1]:
                    third_octet = octet_value
                    break

            if third_octet is not None:
                # Valid EXT, get IP in correct subnet
                fourth_octet = str(int(number[-3:]))  # Drop anyz eros
                ip_address = f"10.255.{third_octet}.{fourth_octet}"

                formatted_devicename = devicename.replace('XXXX', str(number)) \
                                  .replace('Y', str(third_octet)) \
                                  .replace('Z', fourth_octet)

                return number, ip_address, formatted_devicename
            else:
                print("Number is not within the valid ranges.")
        else:
            print("Invalid input. Please enter a 4-digit number.")


def create_r195_extension(devicename):
    # Define valid ranges and corresponding third octet values
    valid_ranges = {
        (1001, 1199): 11,
        (2001, 2199): 12,
        (3001, 3199): 13,
        (4001, 4199): 14,
        (5001, 5199): 15,
        (6001, 6199): 16,
        (7001, 7199): 17,
        (8001, 8199): 18,
        (9001, 9199): 19
    }

    while True:
        print("Extension must be within the range of 1001-1199, 2001-2199, 3001-3199 and so on, up to 9199.")
        number = input("Enter EXT: ")

        if len(number) == 4 and number.isdigit():
            num = int(number)
            third_octet = None
            # Make sure EXT is within ranges
            for range_tuple, octet_value in valid_ranges.items():
                if range_tuple[0] <= num <= range_tuple[1]:
                    third_octet = octet_value
                    break

            if third_octet is not None:
                # Valid EXT, get IP in correct subnet
                fourth_octet = str(int(number[-3:]))  # Drop anyz eros
                ip_address = f"10.255.{third_octet}.{fourth_octet}"

                formatted_devicename = devicename.replace('XXXX', str(number)) \
                                  .replace('Y', str(third_octet)) \
                                  .replace('Z', fourth_octet)

                return number, ip_address, formatted_devicename
            else:
                print("Number is not within the valid ranges.")
        else:
            print("Invalid input. Please enter a 4-digit number.")



def passwd(hostname):
#    print("Updating Password")
    username = "admin"
    passwords = ['!2mzPg$HzMjdZ2', 'admin', 'A8gs#TrPrVNet!', 'NimdA']
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    attempt_count = 0  # Counter for password attempts

    for password in passwords:
        try:
            client.connect(hostname, username=username, password=password)
 #           print("Authentication successful with password:", password)

            if '!2mzPg$HzMjdZ2' in password:
  #              print("Password already updated for builds")
                return "!2mzPg$HzMjdZ2"

            else:
                stdin, stdout, stderr = client.exec_command('passwd')
                stdin.write(password + '\n')
                stdin.write('!2mzPg$HzMjdZ2\n')
                stdin.write('!2mzPg$HzMjdZ2\n')
                stdin.flush()
                stdout.channel.set_combine_stderr(True)
   #             print("Password Updated")
                return "!2mzPg$HzMjdZ2"
                time.sleep(2)

        except paramiko.AuthenticationException:
    #        print("Authentication failed with password:", password)
            attempt_count += 1  # Increment attempt count

            if attempt_count == 3:
     #           print("Waiting 60 seconds after 3 failed attempts...")
                time.sleep(60)  # Wait for 60 seconds
                attempt_count = 0  # Reset the attempt counter

    return None

def snmpgetpublic(device_ip, oid):
    command = f'snmpget -v 2c -c public {device_ip} {oid}'
    stream = os.popen(command)
    output = stream.read()
    return output

def snmpget(device_ip, oid):
    command = f'snmpget -v 2c -c publicreadonly {device_ip} {oid}'
    stream = os.popen(command)
    output = stream.read()
    return output

def snmpgeta8(device_ip, oid):
    command = f'snmpget -v 2c -c SNMP-RO-ACT1v8me {device_ip} {oid}'
    stream = os.popen(command)
    output = stream.read()
    return output

def snmpset(device_ip, oid, value):
    command = f'snmpset -v 2c -c privatereadwrite {device_ip} {oid} {value}'
    stream = os.popen(command)
    output = stream.read()
    return output

def log(content, log_type):
    log_file_path = "common/logs/log.txt"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - [{log_type.upper()}]: {content}\n"
    try:
        with open(log_file_path, "a") as log_file:
            log_file.write(message)
#        print(f"Log updated successfully. {message}")
    except PermissionError:
        print("PermissionError: [Errno 13] Permission denied. Check file permissions.")
    except Exception as e:
        print(f"An error occurred: {e}")


def insert_data(field_or_dict, value=None):
    """Append custom fields to configured.json.

    Examples:
        insert_data("serial_number", "abcd1234")
        insert_data(serial_number="abcd1234", mac="00:11:22")

    Each field is stored as a separate JSON object with a timestamp.
    """
    timestamp = int(datetime.datetime.utcnow().timestamp())
    if isinstance(field_or_dict, dict):
        fields = field_or_dict
    else:
        fields = {field_or_dict: value}

    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                data = json.load(f)
        else:
            data = []
    except Exception:
        data = []

    for key, val in fields.items():
        data.append({"timestamp": timestamp, key: val})

    try:
        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

