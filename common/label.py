#!/usr/bin/env python3
import warnings
import logging
warnings.filterwarnings("ignore")  # Suppress warnings

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends.helpers import send
import os
font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'

print("Font file path:", font_path)
print("File exists:", os.path.exists(font_path))

# Silence all the warnings so they dont print to console..
logging.basicConfig(level=logging.ERROR)

def split_text(text, max_length):
    if len(text) <= max_length:
        return [text]
    # Find the nearest space to the max_length
    split_index = text.rfind(' ', 0, max_length)
    if split_index == -1:  # No spaces, force split
        return [text[:max_length], text[max_length:]]
    # Split the text and strip to avoid leading/trailing spaces
    return [text[:split_index].strip(), text[split_index:].strip()]

# Main part of the script
text = input("Enter the text for the label: ")

try:
    num_copies = int(input("How many copies do you need? "))
except ValueError:
    print("Please enter a valid number.")
    exit(1)

for _ in range(num_copies):
    # Define printer and label type
    printer = BrotherQLRaster('QL-700')
    label_type = '17x54'  # Adjust for different label types

    # Create an image from the text
    img = Image.new('L', (566, 165), color=255)  # Landscape dimensions
    draw = ImageDraw.Draw(img)

    # Load font
    font = ImageFont.truetype(font_path, 50)

    # Split text if necessary
    lines = split_text(text, 19)

    # Add text
    y_pos = 20
    for line in lines:
        draw.text((5, y_pos), line, font=font, fill=0)
        y_pos += 60  # Adjust this value if needed for line spacing

    # Save image
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create and send label
    create_label(printer, img_bytes, label_type, cut=True)
    send(printer.data, 'usb://04f9:2042')  # Printer address
