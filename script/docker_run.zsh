#!/usr/bin/env zsh

APP_NAME="kindle-display"

set -e

cd $(dirname $(dirname $0))

docker build --quiet . -t ${APP_NAME}
docker run --rm -e KINDLE_HOSTNAME=$1 ${APP_NAME}
