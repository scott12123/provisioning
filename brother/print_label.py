#!/usr/bin/env python3
"""Print a label on the Brother printer."""
import argparse
import os
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends.helpers import send
import qrcode

logging.basicConfig(level=logging.ERROR)

DEFAULT_MODEL = os.environ.get('BROTHER_QL_MODEL', 'QL-700')
DEFAULT_ADDRESS = os.environ.get('BROTHER_QL_PRINTER', 'usb://04f9:2042')
# Font file lives in the same directory as this script after moving
FONT_PATH = os.path.join(os.path.dirname(__file__), 'Roboto-Regular.ttf')
LABEL_TYPE = '17x54'


def build_image(text: str, qr: bool) -> Image.Image:
    """Generate label image with optional QR code."""
    img = Image.new('L', (566, 165), color=255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 40)
    draw.text((5, 60), text, font=font, fill=0)

    if qr:
        qr_img = qrcode.make(text).resize((120, 120))
        img.paste(qr_img, (430, 20))
    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a text label")
    parser.add_argument('--text', required=True, help='Text to print')
    parser.add_argument('--qr', action='store_true', help='Print text as QR code')
    args = parser.parse_args()

    printer = BrotherQLRaster(DEFAULT_MODEL)
    img = build_image(args.text, args.qr)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    create_label(printer, img_bytes, LABEL_TYPE, cut=True)
    send(printer.data, DEFAULT_ADDRESS)


if __name__ == '__main__':
    main()
