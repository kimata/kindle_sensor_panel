#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
import datetime
import subprocess
import time
import os
import gc

KINDLE_IP   = 'display-living'
UPDATE_SEC  = 60
REFRESH     = 60

CREATE_IMAGE = os.path.dirname(os.path.abspath(__file__)) + '/create_image.py'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(KINDLE_IP, username='root', password='mario', allow_agent=False, look_for_keys=False)
print('connect ok.')
ssh.exec_command('initctl stop powerd')
ssh.exec_command('initctl stop framework')

i = 0
while True:
  ssh_stdin = ssh.exec_command(
    'cat - > draw.png && eips %s -g draw.png' % (
      '-f' if (i % REFRESH) == 0 else ''
    ),
  )[0]
  proc = subprocess.Popen(['python' , CREATE_IMAGE], stdout=subprocess.PIPE)
  ssh_stdin.write(proc.communicate()[0])
  ssh_stdin.close()

  # close だけだと，SSH 側がしばらく待っていることがあったので，念のため
  del ssh_stdin
  gc.collect()

  # 更新されていることが直感的に理解しやすくなるように，更新タイミングを 0 秒
  # に合わせる
  # (例えば，1分間核更新だとして，1分59秒に更新されると，2分59秒まで更新されないので
  # 2分40秒くらいに表示を見た人は本当に1分感覚で更新されているのか心配になる)
  time.sleep(UPDATE_SEC - datetime.datetime.now().second)
  
  i += 1

  

