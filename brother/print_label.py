#!/usr/bin/env python3
"""Print a label on the Brother printer."""
import argparse
import os
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
from typing import Optional
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends.helpers import send
import qrcode
from pystrich.datamatrix import DataMatrixEncoder
from barcode import get_barcode_class
from barcode.writer import ImageWriter

logging.basicConfig(level=logging.ERROR)

DEFAULT_MODEL = os.environ.get('BROTHER_QL_MODEL', 'QL-700')
DEFAULT_ADDRESS = os.environ.get('BROTHER_QL_PRINTER', 'usb://04f9:2042')
# Font file lives in the same directory as this script after moving
FONT_PATH = os.path.join(os.path.dirname(__file__), 'Roboto-Regular.ttf')
LABEL_TYPE = '17x54'


def build_image(text: str, barcode: Optional[str]) -> Image.Image:
    """Generate label image with optional barcode."""
    img = Image.new('L', (566, 165), color=255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 40)

    text_area_width = 420
    lines = []
    for para in text.splitlines() or ['']:
        if not para:
            lines.append('')
            continue
        words = para.split()
        if not words:
            lines.append('')
            continue
        cur = words[0]
        for word in words[1:]:
            test = f"{cur} {word}"
            if draw.textlength(test, font=font) <= text_area_width:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)

    line_height = font.getbbox('Ag')[3] - font.getbbox('Ag')[1]
    total_height = line_height * len(lines)
    y = (img.height - total_height) // 2
    for line in lines:
        draw.text((5, y), line, font=font, fill=0)
        y += line_height

    max_height = img.height - 20
    barcode_x = 430
    available_width = img.width - barcode_x

    if barcode == 'qr':
        size = min(max_height, available_width)
        qr_img = qrcode.make(text)
        qr_img = qr_img.resize((size, size))
        img.paste(qr_img, (barcode_x + (available_width - size) // 2,
                          (img.height - size) // 2))
    elif barcode == 'data_matrix':
        encoder = DataMatrixEncoder(text)
        dm_img = Image.open(BytesIO(encoder.get_imagedata()))
        size = min(max_height, available_width)
        dm_img = dm_img.resize((size, size))
        img.paste(dm_img, (barcode_x + (available_width - size) // 2,
                           (img.height - size) // 2))
    elif barcode == 'code128':
        bc_cls = get_barcode_class('code128')
        bc = bc_cls(text, writer=ImageWriter())
        bc_img = bc.render(writer_options={'module_height': max_height})
        if bc_img.width > available_width:
            ratio = available_width / bc_img.width
            new_width = available_width
            new_height = int(bc_img.height * ratio)
        else:
            new_width = bc_img.width
            new_height = bc_img.height
        if new_height > max_height:
            ratio = max_height / new_height
            new_width = int(new_width * ratio)
            new_height = max_height
        bc_img = bc_img.resize((new_width, new_height), Image.LANCZOS).convert('L')
        img.paste(bc_img, (barcode_x + (available_width - new_width) // 2,
                          (img.height - new_height) // 2))

    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a text label")
    parser.add_argument('--text', required=True, help='Text to print')
    parser.add_argument('--barcode', choices=['qr', 'data_matrix', 'code128'], help='Barcode type to include')
    parser.add_argument('--qr', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()

    barcode = args.barcode
    if args.qr and not barcode:
        barcode = 'qr'

    printer = BrotherQLRaster(DEFAULT_MODEL)
    img = build_image(args.text, barcode)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    create_label(printer, img_bytes, LABEL_TYPE, cut=True)
    send(printer.data, DEFAULT_ADDRESS)


if __name__ == '__main__':
    main()
