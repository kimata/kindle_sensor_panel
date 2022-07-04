FROM ubuntu:22.04

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y language-pack-ja
RUN apt-get install -y python3 python3-pip

RUN apt-get install -y python3-yaml
RUN apt-get install -y python3-influxdb
RUN apt-get install -y python3-pil python3-numpy
RUN apt-get install -y python3-paramiko

WORKDIR /opt/kindle_display
COPY . .

CMD ["./src/display_image.py"]
