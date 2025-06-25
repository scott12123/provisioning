#!/usr/bin/env python3

import argparse
import subprocess
import re

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--print-label', action='store_true', help='Print label after configuration')
args = parser.parse_args()

print("We configure the device...")

# Run esptool erase and capture output
erase_cmd = ["esptool.py", "--chip", "esp32s3", "--port", "/dev/ttyACM0", "erase_flash"]

try:
    # Capture output for MAC extraction
    result = subprocess.run(erase_cmd, text=True, capture_output=True, check=True)
    output = result.stdout

    # Extract MAC using regex
    match = re.search(r"MAC:\s*([0-9a-f:]{17})", output, re.IGNORECASE)
    if match:
        mac_address = match.group(1)
        print(f"Extracted MAC Address: {mac_address}")
    else:
        print("MAC Address not found in output")
        mac_address = None

except subprocess.CalledProcessError as e:
    print(f"Error running esptool: {e}")
    exit(1)

# Flash the firmware
subprocess.run(["esptool.py", "--chip", "esp32s3", "--port", "/dev/ttyACM0", "write_flash", "-z", "0x0", "victron/telemetry_v1.2.bin"], check=True)

# Optional file listing
subprocess.run(["ls"], check=True)

# Handle label printing
if args.print_label and mac_address:
    print(f"We fetch the MAC: {mac_address}")
    subprocess.run(["python3", "/home/pi/apn/brother/print_victron.py", mac_address], check=True)
    print("END")
else:
    print("We don't print labels")
    print("END")
