#!/usr/bin/env python3

import argparse
import subprocess
import sys

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--print-label', action='store_true', help='Print label after configuration')
args = parser.parse_args()

# Start configuration
print("We configure the device...")

# Erase flash
subprocess.run(["esptool.py", "--chip", "esp32s3", "--port", "/dev/ttyACM0", "erase_flash"], check=True)

# Write firmware
subprocess.run(["esptool.py", "--chip", "esp32s3", "--port", "/dev/ttyACM0", "write_flash", "-z", "0x0", "telemetry_v1.2.bin"], check=True)

# List files (optional, for debugging)
subprocess.run(["ls"], check=True)

# Handle label printing
if args.print_label:
    #print("We fetch the MAC")
    subprocess.run(["python3", "print_victron.py"], check=True)
else:
    print("")
