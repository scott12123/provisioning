#!/bin/bash
esptool.py --chip esp32s3 --port /dev/ttyACM0 erase_flash
esptool.py --chip esp32s3 --port /dev/ttyACM0 write_flash -z 0x0 telemetry_v1.2.bin
ls
python3 /home/pi/apn/brother/print_victron.py
