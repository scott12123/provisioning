#!/usr/bin/env python3
"""Print a label on the Brother printer."""
import argparse
import os
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
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
    draw.text((5, 60), text, font=font, fill=0)

    max_height = img.height - 20

    if barcode == 'qr':
        qr_img = qrcode.make(text)
        qr_img = qr_img.resize((max_height, max_height))
        img.paste(qr_img, (430, (img.height - qr_img.height) // 2))
    elif barcode == 'data_matrix':
        encoder = DataMatrixEncoder(text)
        dm_img = Image.open(BytesIO(encoder.get_imagedata()))
        dm_img = dm_img.resize((max_height, max_height))
        img.paste(dm_img, (430, (img.height - dm_img.height) // 2))
    elif barcode == 'code128':
        bc_cls = get_barcode_class('code128')
        bc = bc_cls(text, writer=ImageWriter())
        bc_img = bc.render(writer_options={'module_height': max_height})
        ratio = max_height / bc_img.height
        width = int(bc_img.width * ratio)
        bc_img = bc_img.resize((width, max_height), Image.ANTIALIAS).convert('L')
        img.paste(bc_img, (430, (img.height - max_height) // 2))

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
