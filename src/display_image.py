#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
import datetime
import subprocess
import time
import gc

KINDLE_IP   = '192.168.2.193'
UPDATE_SEC  = 60
REFRESH     = 60

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(KINDLE_IP, username='root', password='mario', allow_agent=False, look_for_keys=False)

ssh.exec_command('initctl stop powerd')
ssh.exec_command('initctl stop framework')

i = 0
while True:
  ssh_stdin = ssh.exec_command(
    'cat - > draw.png && eips %s -g draw.png' % (
      '-f' if (i % REFRESH) == 0 else ''
    ),
  )[0]
  proc = subprocess.Popen(['python' , 'create_image.py'], stdout=subprocess.PIPE)
  ssh_stdin.write(proc.communicate()[0])
  ssh_stdin.close()

  # close だけだと，SSH 側がしばらく待っていることがあったので，念のため
  del ssh_stdin
  gc.collect()

  # 0 秒になるまで待ったうえで，指定時間待つ
  time.sleep(UPDATE_SEC - datetime.datetime.now().second)
  
  i += 1

  

