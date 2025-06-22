#!/usr/bin/env python3
import warnings
import logging
import datetime
from PIL import Image, ImageDraw, ImageFont
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends.helpers import send
from io import BytesIO

# Silence all the warnings so they dont print to console..
logging.basicConfig(level=logging.ERROR)

def print_label(ext,ip,type,site):
  try:  # Define printer and label type
    printer = BrotherQLRaster('QL-700')
    label_type = '17x54'  # Update this if you have a different label type

    if type == 'device':
        line1 = f"{site} EXT{ext}"
        line2 = "Passed " + datetime.datetime.now().strftime("%d/%m/%Y")
    elif type == 'box':
        line1 = f"{site} EXT{ext} {ip}"
        line2 = "Passed " + datetime.datetime.now().strftime("%d/%m/%Y")
    else:
        line1 = f"{site} EXT{ext}"
        line2 = "Passed: "

    # Create an image from the text
    img = Image.new('L', (566, 165), color=255)  # Note the swapped dimensions for landscape
    draw = ImageDraw.Draw(img)

    # Use a TrueType font
    font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'
    font_size = 35
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text position and rotation for landscape
    text_position_line1 = (5, 10)
    text_position_line2 = (5, 70)
    draw.text(text_position_line1, line1, font=font, fill=0)
    draw.text(text_position_line2, line2, font=font, fill=0)

    # Save image to a BytesIO object
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create label from the image
    create_label(printer, img_bytes, label_type, cut=True)

    # Send to printer with the correct printer address
    printer_address = 'usb://04f9:2042'
    send(printer.data, printer_address)
  except Exception as e:
        print(f"An error occurred while printing: {e}")
        print("Please ensure that the printer is on and connected to the raspberry pi.") 



def print_label_switch(ext,ip,type,site,mac):
  try:  # Define printer and label type
    printer = BrotherQLRaster('QL-700')
    label_type = '17x54'  # Update this if you have a different label type

    if type == 'device':
        line1 = f"{site} {ext}"
        line2 = "Passed " + datetime.datetime.now().strftime("%d/%m/%Y")
    elif type == 'box':
        line1 = f"{site} {ext} {ip}"
        line2 = "Passed " + datetime.datetime.now().strftime("%d/%m/%Y")
    else:
        line1 = f"{site} {ext}"
        line2 = "Passed: "

    line3 = mac
    # Create an image from the text
    img = Image.new('L', (566, 165), color=255)  # Note the swapped dimensions for landscape
    draw = ImageDraw.Draw(img)

    # Use a TrueType font
    font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'
    font_size = 50
    font = ImageFont.truetype(font_path, font_size)
    mac_font = ImageFont.truetype(font_path, 35)
    # Calculate text position and rotation for landscape
    text_position_line1 = (5, 10)
    text_position_line2 = (5, 70)
    text_position_line3 = (5, 120)
    draw.text(text_position_line1, line1, font=font, fill=0)
    draw.text(text_position_line2, line2, font=font, fill=0)
    draw.text(text_position_line3, line3, font=mac_font, fill=0)

    # Save image to a BytesIO object
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create label from the image
    create_label(printer, img_bytes, label_type, cut=False)

    # Send to printer with the correct printer address
    printer_address = 'usb://04f9:2042'
    send(printer.data, printer_address)
  except Exception as e:
        print(f"An error occurred while printing: {e}")
        print("Please ensure that the printer is on and connected to the raspberry pi.")

def pass_label(line1,line2,line3):
  try:  # Define printer and label type
    printer = BrotherQLRaster('QL-700')
    label_type = '17x54'  # Update this if you have a different label type

    # Create an image from the text
    img = Image.new('L', (566, 165), color=255)  # Note the swapped dimensions for landscape
    draw = ImageDraw.Draw(img)

    # Use a TrueType font
    font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text position and rotation for landscape
    text_position_line1 = (5, 10)
    text_position_line2 = (5, 65)
    text_position_line3 = (5, 120)
    draw.text(text_position_line1, line1, font=font, fill=0)
    draw.text(text_position_line2, line2, font=font, fill=0)
    draw.text(text_position_line3, line3, font=font, fill=0)

    # Save image to a BytesIO object
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create label from the image
    create_label(printer, img_bytes, label_type, cut=True)

    # Send to printer with the correct printer address
    printer_address = 'usb://04f9:2042'
    send(printer.data, printer_address)
  except Exception as e:
        print(f"An error occurred while printing: {e}")
        print("Please ensure that the printer is on and connected to the raspberry pi.") 
