#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
import subprocess
import time

KINDLE_IP   = '192.168.2.193'
UPDATE_SEC  = 60
REFRESH     = 60

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(KINDLE_IP, username='root', password='mario', allow_agent=False, look_for_keys=False)

i = 0
while True:
  ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
    'cat - > draw.png && eips %s -g draw.png' % (
      '-f' if (i % REFRESH) == 0 else ''
    )
  )
  proc = subprocess.Popen(['python' , 'create_image.py'], stdout=subprocess.PIPE)

  ssh_stdin.write(proc.communicate()[0])
  ssh_stdin.close()

 
  time.sleep(UPDATE_SEC)
  i += 1

