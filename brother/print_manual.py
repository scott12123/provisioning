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

def print_label(text):
    # Define printer and label type
    printer = BrotherQLRaster('QL-700')
    label_type = '17x87'  # Update this if you have a different label type

    line1 = f"{text}"

# Create an image from the text
    img = Image.new('L', (956, 165), color=255)  # Note the swapped dimensions for landscape
    draw = ImageDraw.Draw(img)

    # Use a TrueType font
    font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'
    font_size = 55
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text position and rotation for landscape
    text_position_line1 = (20, 20)
    draw.text(text_position_line1, line1, font=font, fill=0)

    # Save image to a BytesIO object
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create label from the image
    create_label(printer, img_bytes, label_type, cut=True)

    # Send to printer with the correct printer address
    printer_address = 'usb://04f9:2042'
    send(printer.data, printer_address)
