#!/usr/bin/env python3
import paramiko
from ping3 import ping, verbose_ping
import time
import os
import re
import logging
import sys
sys.path.append('provisioningpi/brother') #for label scripts
sys.path.append('provisioningpi/common') #for common files/scripts

import functions
import gsheet
import print_v1

#gsheet.latest_ext(site)
functions.log("message","info")
