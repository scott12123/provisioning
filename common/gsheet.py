import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

def latest_ext(tab_name):
    sheet_name = 'RP3 Data'
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # Add credentials to the account
    creds = ServiceAccountCredentials.from_json_keyfile_name('/home/pi/provisioningpi/common/cambium-409022-08ac06545f3c.json', scope)

    # Authorize the client sheet
    client = gspread.authorize(creds)

    # Open the sheet and access the specified worksheet
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(tab_name)

    # Retrieve the last row from column 3 (Device Name column)
    device_names = worksheet.col_values(3)
    if not device_names:
        return None  # No data found

    most_recent_device_name = device_names[-1]

    # Use regular expression to find the 'XXXX' number
    match = re.search(r'EXT(\d+)_', most_recent_device_name)
    if match:
        extracted_number = match.group(1)  # This is the 'XXXX' number
        return extracted_number
    else:
        return None

def check_device_number_exists(number, device_name):
    # Sheet and tab details
    sheet_name = 'RP3 Data'
    tab_name = device_name[:3]

    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # Add credentials to the account
    creds = ServiceAccountCredentials.from_json_keyfile_name('/home/pi/provisioningpi/common/cambium-409022-08ac06545f3c.json', scope)

    # Authorize the client sheet
    client = gspread.authorize(creds)

    # Open the sheet
    sheet = client.open(sheet_name)

    try:
        # Access the specific worksheet
        worksheet = sheet.worksheet(tab_name)

        # Check for the number in the Device Name column
        device_names = worksheet.col_values(3)  # Assuming Device Name is in the 3rd column
        for device in device_names:
            if str(number) in device:
                return True

    except gspread.exceptions.WorksheetNotFound:
        # Skip if tab_name does not exist
        pass

    return False

def add_to_sheet(sn, mac, device_name, ip, firmware, hardware, smc_ping):
    # Sheet and tab details
    sheet_name = 'RP3 Data'
    tab_name = device_name[:3]

    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

    # Add credentials to the account
    creds = ServiceAccountCredentials.from_json_keyfile_name('/home/pi/provisioningpi/common/cambium-409022-08ac06545f3c.json', scope)

    # Authorize the clientsheet
    client = gspread.authorize(creds)

    # Open the sheet and check for the tab
    try:
        sheet = client.open(sheet_name).worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        # Create a new tab and add headers
        sheet = client.open(sheet_name).add_worksheet(title=tab_name, rows="1000", cols="20")
        headers = ["SN", "MAC", "Device Name", "IP", "Hardware", "Firmware", "SMC Ping", "Date/Time Configured and Tested","Testing Outcome"]
        sheet.append_row(headers)

    # Find the next empty row
    next_row = len(sheet.col_values(1)) + 1

    # Get current date and time
    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Add the data
    row_data = [sn, mac, device_name, ip, hardware, firmware, smc_ping,current_datetime,"PASS"]
    sheet.insert_row(row_data, next_row)
