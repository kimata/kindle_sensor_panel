FROM ubuntu:22.04

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    language-pack-ja \
    python3 python3-pip \
    python3-docopt \
    python3-yaml python3-coloredlogs \
    python3-pil python3-numpy \
    python3-paramiko \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kindle_sensor

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

CMD ["./src/display_image.py"]
