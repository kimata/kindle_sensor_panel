#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import datetime
import subprocess
import time
import sys
import os
import gc

UPDATE_SEC = 60
REFRESH = 60
FAIL_MAX = 5

CREATE_IMAGE = os.path.dirname(os.path.abspath(__file__)) + "/create_image.py"


def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        kindle_hostname,
        username="root",
        password="mario",
        allow_agent=False,
        look_for_keys=False,
    )

    return ssh


if len(sys.argv) == 1:
    kindle_hostname = os.environ["KINDLE_HOSTNAME"]
else:
    kindle_hostname = sys.argv[1]

print("kindle hostname: %s" % (kindle_hostname))

ssh = ssh_connect()
ssh.exec_command("initctl stop powerd")
ssh.exec_command("initctl stop framework")

i = 0
fail = 0
while True:
    ssh_stdin = None
    try:
        ssh_stdin = ssh.exec_command(
            "cat - > draw.png && eips %s -g draw.png"
            % ("-f" if (i % REFRESH) == 0 else ""),
        )[0]

        proc = subprocess.Popen(["python3", CREATE_IMAGE], stdout=subprocess.PIPE)
        ssh_stdin.write(proc.communicate()[0])
        ssh_stdin.close()
        fail = 0
        print(".", end="")
        sys.stdout.flush()
    except:
        print("x", end="")
        sys.stdout.flush()
        fail += 1
        time.sleep(10)
        ssh = ssh_connect()

    # close だけだと，SSH 側がしばらく待っていることがあったので，念のため
    del ssh_stdin
    gc.collect()

    if fail > FAIL_MAX:
        sys.stderr.write("接続エラーが続いたので終了します．\n")
        sys.exit(-1)

    # 更新されていることが直感的に理解しやすくなるように，更新タイミングを 0 秒
    # に合わせる
    # (例えば，1分間隔更新だとして，1分59秒に更新されると，2分59秒まで更新されないので
    # 2分40秒くらいに表示を見た人は本当に1分感覚で更新されているのか心配になる)
    time.sleep(UPDATE_SEC - datetime.datetime.now().second)

    i += 1
