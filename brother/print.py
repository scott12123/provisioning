#!/usr/bin/env python3
#Print on Brother QL-570
import brother_ql
from PIL import Image, ImageDraw, ImageFont


#export BROTHER_QL_PRINTER=tcp://192.168.1.21
#export BROTHER_QL_MODEL=QL-570

width = 956
height = 165
ext = "EXT1234"
ip = "10.255.3.4"

line1 = (f"{ext}   {ip}")
line2 = "PASS 21/12/2023"

img = Image.new('RGB', (width, height), color='white')

font_path = '/home/pi/provisioningpi/brother/Roboto-Regular.ttf'
font_size = 70  # You can change this to your desired font size
font = ImageFont.truetype(font_path, font_size)

imgDraw = ImageDraw.Draw(img)

imgDraw.text((10, 10), line1, font=font, fill=(0, 0, 0))
imgDraw.text((10, 70), line2, font=font, fill=(0, 0, 0))

image = img.save('result.png')

#brother_ql -b pyusb -p usb://0x04f9:0x2015/000M6Z401370 print -l 17x87 image



#https://github.com/pklaus/brother_ql
#https://stackoverflow.com/questions/49766192/printing-with-the-python-library-brother-ql-on-a-raspberry-pi
#https://plainenglish.io/blog/generating-text-on-image-with-python-eefe4430fe77
#https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html
#
#
