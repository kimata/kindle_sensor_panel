FROM ubuntu:22.04

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y language-pack-ja
RUN apt-get install -y python3 python3-pip

RUN apt-get install -y python3-yaml python3-coloredlogs
RUN apt-get install -y python3-pil python3-numpy
RUN apt-get install -y python3-paramiko

WORKDIR /opt/kindle_sensor

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

CMD ["./src/display_image.py"]
