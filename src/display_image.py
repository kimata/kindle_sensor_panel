#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
電子ペーパ表示用の画像を表示します．

Usage:
  display_image.py [-f CONFIG] [-t HOSTNAME] [-s]

Options:
  -f CONFIG    : CONFIG を設定ファイルとして読み込んで実行します．[default: config.yaml]
  -t HOSTNAME  : 表示を行う Raspberry Pi のホスト名．
  -s           : 1回のみ表示
"""

from docopt import docopt

import paramiko
import datetime
import subprocess
import time
import sys
import os
import gc
import logging
import pathlib
import traceback

import logger
from config import load_config
import notify_slack

NOTIFY_THRESHOLD = 2
UPDATE_SEC = 60
REFRESH = 60
FAIL_MAX = 5

CREATE_IMAGE = os.path.dirname(os.path.abspath(__file__)) + "/create_image.py"


def notify_error(config):
    notify_slack.error(
        config["SLACK"]["BOT_TOKEN"],
        config["SLACK"]["ERROR"]["CHANNEL"]["NAME"],
        config["SLACK"]["FROM"],
        traceback.format_exc(),
        config["SLACK"]["ERROR"]["INTERVAL_MIN"],
    )


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


def display_image(ssh):
    ssh_stdin = ssh.exec_command(
        "cat - > draw.png && eips %s -g draw.png"
        % ("-f" if (i % REFRESH) == 0 else ""),
    )[0]

    proc = subprocess.Popen(["python3", CREATE_IMAGE], stdout=subprocess.PIPE)
    ssh_stdin.write(proc.communicate()[0])
    ssh_stdin.close()
    sys.stdout.flush()

    return proc


######################################################################
args = docopt(__doc__)

logger.init("panel.kindle.sensor", level=logging.INFO)

is_one_time = args["-s"]
kindle_hostname = os.environ.get("KINDLE_HOSTNAME", args["-t"])

logging.info("Kindle hostname: %s" % (kindle_hostname))

config = load_config(args["-f"])

try:
    ssh = ssh_connect(kindle_hostname)
    logging.info("put the kindle into signage mode")
    ssh.exec_command("initctl stop powerd")
    ssh.exec_command("initctl stop framework")
except:
    notify_error(config)
    logging.error(traceback.format_exc())
    sys.exit(-1)


i = 0
fail_count = 0
while True:
    ssh_stdin = None
    try:
        proc = display_image(ssh)

        if proc.returncode != 0:
            message = "Failed to create image. (code: {code})".format(
                code=proc.returncode
            )
            logging.error(message)
            raise message

        fail_count = 0

        logging.info("Finish.")
        pathlib.Path(config["LIVENESS"]["FILE"]).touch()

        if is_one_time:
            break
    except:
        fail_count += 1

        if is_one_time or (fail_count >= NOTIFY_THRESHOLD):
            notify_error(config)
            logging.error("エラーが続いたので終了します．")
            raise
        else:
            time.sleep(10)
            ssh = ssh_connect(kindle_hostname)
            pass

    # close だけだと，SSH 側がしばらく待っていることがあったので，念のため
    del ssh_stdin
    gc.collect()

    # 更新されていることが直感的に理解しやすくなるように，更新タイミングを 0 秒
    # に合わせる
    # (例えば，1分間隔更新だとして，1分40秒に更新されると，2分40秒まで更新されないので
    # 2分45秒くらいに表示を見た人は本当に1分間隔で更新されているのか心配になる)
    sleep_time = config["PANEL"]["UPDATE"]["INTERVAL"] - datetime.datetime.now().second
    logging.info("sleep {sleep_time} sec...".format(sleep_time=sleep_time))
    sys.stderr.flush()
    time.sleep(sleep_time)

    i += 1
