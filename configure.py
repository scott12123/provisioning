import inspect
import os
import threading
import re
import sys
import subprocess
import concurrent.futures
import netifaces as ni
import colorama
from colorama import Fore,Back
colorama.init(autoreset=True)
import paramiko
from ping3 import ping, verbose_ping
import time
import logging




# Add new templates here - Will automatically get added to the list
def NBN_XV2_2T0_Outdoor_Configuration():
    with open('cambium/nbn-xv2-2t0-custom-config.py') as file:
         exec(file.read())

def NBN_XV2_22H_Indoor_Configuration():
    with open('cambium/nbn-xv2-22h-custom-config.py') as file:
         exec(file.read())

def NBN_F300_25_Remote_Configuration():
    with open('cambium/nbn-f300-25-remote.py') as file:
         exec(file.read())

def XV2_22H_Custom_Configuration():
    with open('cambium/xv2-22h-custom-config.py') as file:
         exec(file.read())

def RCP_XV2_2T0_Custom_Configuration():
    with open('cambium/rct-xv2-custom-config.py') as file:
         exec(file.read())

def RCT_XV2_Generic_213_Configuration():
    with open('cambium/rct-xv2-generic-213.py') as file:
         exec(file.read())

def RCP_Generic_f300_25_ap_switch_Configuration():
    with open('cambium/rcp-GEN-f300_25_ap_switch-remote.py') as file:
         exec(file.read())

def Telemetry_TinyS3_Configuration():
    with open('./victron/victron.sh') as file:
         exec(file.read())

def RCP_F300_16_Default_Configuration():
    with open('cambium/rcp-default-f300-16-remote-v2.py') as file:
         exec(file.read())

def WP_MK3_Metal_V1_1_Configuration():
    with open('/home/pi/mikrotik/metalmk3_v1.1.py') as file:
         exec(file.read())

def WP_MK3_450Gx4_V1_1_Configuration():
    with open('/home/pi/mikrotik/450gmk3_v1.1.py') as file:
         exec(file.read())

def ePMP_Scanner_and_Reset_Configuration():
    with open('cambium/ipscanner.py', 'r') as file:
         exec(file.read())

def Label_Printer_Configuration():
    with open('common/label.py', 'r') as file:
         exec(file.read())

def WiFi_Hub_Metal_Mikrotik_Remote_Hotspot_IP29_Configuration():
    with open('/home/pi/mikrotik/metal_wifi_hub_remote_hotspot_IP29_v1.1.py', 'r') as file:
         exec(file.read())

def Wizard_Configuration_Setup():
    os.system(f"sudo python3 wizard.py")

#def R195p_Update_CnMaestro_Configuration():
#    with open('cambium/r195-cnmaestro.py', 'r') as file:
#         exec(file.read())

#def RCP_Bidyadanga_R195_Rename_Configuration():
#    with open('provisioningpi/cambium/rcp-bid-r195-rename.py') as file:
#         exec(file.read())
#def RCP_Bidyadanga_F300_25_Configuration():
#    with open('provisioningpi/cambium/rcp-bid-f300-25-remote.py') as file:
#         exec(file.read())

#def RCP_Mornington_F300_16_Configuration_V1():
#    with open('provisioningpi/cambium/rcp-mor-f300-16-remote.py') as file:
#         exec(file.read())
#def RCP_Mornington_F300_16_Configuration_V2():
#    with open('provisioningpi/cambium/rcp-mor-f300-16-remote-v2.py') as file:
#         exec(file.read())
#def RCP_Mornington_F300_25_Configuration_V1():
#    with open('provisioningpi/cambium/rcp-mor-f300-25-remote.py') as file:
#         exec(file.read())
#def RCP_Mornington_F300_25_Configuration_V2():
#    with open('provisioningpi/cambium/rcp-mor-f300-25-remote-v2.py') as file:
#         exec(file.read())
#def RCP_Mornington_R195_Rename_Configuration():
#    with open('provisioningpi/cambium/rcp-mor-r195-rename.py') as file:
#         exec(file.read())

#def RCP_Burringurrah_f300_25_ap_switch_Configuration():
#    os.system(f"sudo python3 cambium/rcp-BUR-f300_25_ap_switch-remote.py")
#    with open('provisioningpi/cambium/rcp-BUR-f300_25_ap_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Burringurrah_F300_16_Configuration():
#   with open('cambium/rcp-bur-f300-16-remote.py') as file:
#         exec(file.read())

#def RCP_Burringurrah_F300_25_Configuration():
#    with open('cambium/rcp-bur-f300-25-remote.py') as file:
#         exec(file.read())

#def RCP_Bidyadanga_F300_16_Configuration():
#    with open('provisioningpi/cambium/rcp-bid-f300-16-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_25_Configuration():
#    with open('cambium/rcp-WUJ-f300_25-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_16_remote_switch_Configuration():
#    with open('cambium/rcp-WUJ-f300_16_remote_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_25_remote_switch_Configuration():
#    with open('cambium/rcp-WUJ-f300_25_remote_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_25_remote_switch_Configuration():
#    with open('cambium/rcp-WUJ-f300_25_remote_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_25_remote_switch_Configuration():
#    with open('cambium/rcp-WUJ-f300_25_remote_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_25_remote_switch_Configuration():
#    with open('cambium/rcp-WUJ-f300_25_remote_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Wujal_Wujal_f300_25_remote_switch_Configuration():
#    with open('cambium/rcp-WUJ-f300_25_remote_switch-remote.py') as file:
#         exec(file.read())

#def RCP_Galiwinku_f300_25_ap_switch_Configuration():
#    with open('cambium/rcp-GWK-f300_25_ap_switch-remote.py') as file:
#         exec(file.read())

###### DO NOT EDIT BELOW THIS LINE ######

def main():
    # Filter out the above functions that contain 'configuration' in their name
    configuration_functions = [func for name, func in sorted(globals().items()) if callable(func) and 'configuration' in name.lower()]
    configurations = {i: config for i, config in enumerate(configuration_functions, start=1)}

    # Display choices in a list
    for number, config in configurations.items():
        print(f"{number}: {config.__name__}")

    # Ask for user input
    try:
        choice = int(input("Enter the number of the configuration you want to run: "))
        if choice in configurations:
            configurations[choice]()
        else:
            print("Invalid choice. Please choose a valid configuration number.")
    except ValueError:
        print("Please enter a valid number.")

if __name__ == "__main__":
    main()
