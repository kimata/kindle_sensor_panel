#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time

KINDLE_IP   = '192.168.2.193'
UPDATE_SEC  = 60
REFRESH     = 60

i = 0
while True:
    os.system('python create_image.py | ssh root@%s "cat - > draw.png && eips %s -g draw.png"' %
              (KINDLE_IP, '-f' if (i % REFRESH) == 0 else ''))
    time.sleep(UPDATE_SEC)
    i += 1


