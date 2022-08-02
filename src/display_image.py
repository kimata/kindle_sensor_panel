#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import datetime
import subprocess
import time
import sys
import os
import gc
import pathlib
import logging

import logger
from config import load_config

UPDATE_SEC = 60
REFRESH = 60
FAIL_MAX = 5

CREATE_IMAGE = os.path.dirname(os.path.abspath(__file__)) + "/create_image.py"


def ssh_connect(hostname):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname,
        username="root",
        password="mario",
        allow_agent=False,
        look_for_keys=False,
    )

    return ssh


logger.init("Kindle Sensor Panel")

if len(sys.argv) == 1:
    kindle_hostname = os.environ["KINDLE_HOSTNAME"]
else:
    kindle_hostname = sys.argv[1]

logging.info("Kindle hostname: %s" % (kindle_hostname))

config = load_config()

ssh = ssh_connect(kindle_hostname)
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
        sys.stdout.flush()

        if proc.returncode != 0:
            logging.error(
                "Failed to create image. (code: {code})".format(code=proc.returncode)
            )
            sys.exit(proc.returncode)

        logging.info("Finish.")
        pathlib.Path(config["LIVENESS"]["FILE"]).touch()
    except:
        sys.stdout.flush()
        fail += 1
        time.sleep(10)
        ssh = ssh_connect(kindle_hostname)

    # close だけだと，SSH 側がしばらく待っていることがあったので，念のため
    del ssh_stdin
    gc.collect()

    if fail > FAIL_MAX:
        sys.stderr.write("接続エラーが続いたので終了します．\n")
        sys.exit(-1)

    # 更新されていることが直感的に理解しやすくなるように，更新タイミングを 0 秒
    # に合わせる
    # (例えば，1分間隔更新だとして，1分40秒に更新されると，2分40秒まで更新されないので
    # 2分45秒くらいに表示を見た人は本当に1分間隔で更新されているのか心配になる)
    sleep_time = config["PANEL"]["UPDATE"]["INTERVAL"] - datetime.datetime.now().second
    logging.info("sleep {sleep_time} sec...".format(sleep_time=sleep_time))
    sys.stderr.flush()
    time.sleep(sleep_time)

    i += 1
