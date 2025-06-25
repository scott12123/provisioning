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

    # Code128 labels dedicate the entire width to the barcode so no text is
    # drawn on the left. For all other cases the text is wrapped into a column
    # and drawn before rendering the barcode.
    if barcode != 'code128':
        text_area_width = 420
        barcode_x = 430
        max_height = img.height - 20
        available_width = img.width - barcode_x
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
    else:
        # Reserve most of the label for the barcode and its text
        max_height = int(img.height * 0.8)
        available_width = int(img.width * 0.6)
        barcode_x = (img.width - available_width) // 2

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
        bar_font = ImageFont.truetype(FONT_PATH, 20)
        text_h = bar_font.getbbox('Ag')[3] - bar_font.getbbox('Ag')[1]

        # Use the label height and width targets for the barcode.  We
        # determine an appropriate ``module_width`` by rendering the barcode
        # once with a width of 1 pixel and scaling the resulting width.
        bar_height = int(img.height * 0.8)
        target_width = int(img.width * 0.6)

        tmp_img = bc.render(
            writer_options={
                'module_width': 1,
                'module_height': bar_height,
                'write_text': False,
            }
        )
        if tmp_img.width == 0:
            module_width = 1
        else:
            module_width = target_width / tmp_img.width

        bc_img = bc.render(
            writer_options={
                'module_width': module_width,
                'module_height': bar_height,
                'write_text': False,
            }
        ).convert('L')

        bar_x = (img.width - bc_img.width) // 2
        text_w = draw.textlength(text, font=bar_font)
        text_x = (img.width - text_w) // 2

        # Position the barcode so the accompanying text sits at the bottom
        # of the label.  A small 2px gap is kept between the barcode and the
        # text for readability.
        text_y = img.height - text_h - 2
        bar_y = text_y - bc_img.height
        img.paste(bc_img, (bar_x, bar_y))

        draw.text((text_x, text_y), text, font=bar_font, fill=0)
        return img

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
