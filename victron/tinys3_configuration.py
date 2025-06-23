#!/usr/bin/env python3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--print-label', action='store_true', help='Print label after configuration')
args = parser.parse_args()

print("We configure the device...")

if args.print_label:
    print("We fetch the MAC")
    print("We print labels")
    print("END")
else:
    print("We don't print labels")
    print("END")

