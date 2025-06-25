#!/usr/bin/env python3
import warnings
import logging
import datetime
from PIL import Image, ImageDraw, ImageFont
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends.helpers import send
from io import BytesIO
import qrcode

import sys

if len(sys.argv) != 2:
    print("Usage: print_victron.py <MAC>")
    exit(1)

mac_address = sys.argv[1]

# Silence all the warnings so they dont print to console..
logging.basicConfig(level=logging.ERROR)

def print_label(mac):
  try:
    printer = BrotherQLRaster('QL-700')
    label_type = '17x54'
    type = 'device'

    if type == 'device':
        line1 = f"MAC: {mac}"
        line2 = "Passed " + datetime.datetime.now().strftime("%d/%m/%Y")
        line3 = "V1.2"


    qr = qrcode.QRCode(version=1,
    	error_correction=qrcode.constants.ERROR_CORRECT_L,
    	box_size=6,
    	border=1,
    )
    qr.add_data(mac)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")

    img = Image.new('L', (566, 165), color=255)
    draw = ImageDraw.Draw(img)

    font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)
    mac_font = ImageFont.truetype(font_path, 35)
    text_position_line1 = (5, 5)
    text_position_line2 = (5, 40)
    text_position_line3 = (5, 80)
    draw.text(text_position_line1, line1, font=font, fill=0)
    draw.text(text_position_line2, line2, font=font, fill=0)
    draw.text(text_position_line3, line3, font=font, fill=0)
    qr_position = (435, 30)
    img.paste(qr_img, qr_position)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    create_label(printer, img_bytes, label_type, cut=True)

    printer_address = 'usb://04f9:2042'
    send(printer.data, printer_address)
  except Exception as e:
        print(f"An error occurred while printing: {e}")
        print("Please ensure that the printer is on and connected to the raspberry pi.")

print("Printing sticker")
print_label(mac_address)
