#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import datetime
import pathlib
import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import functools
import textwrap
import influxdb_client
import logging

from config import load_config
import logger

FLUX_QUERY = """
from(bucket: "{bucket}")
    |> range(start: -{period})
    |> filter(fn:(r) => r._measurement == "sensor.{measure}")
    |> filter(fn: (r) => r.hostname == "{hostname}")
    |> filter(fn: (r) => r["_field"] == "{param}")
    |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
    |> exponentialMovingAverage(n: 3)
    |> sort(columns: ["_time"], desc: true)
    |> limit(n: 1)
"""


def abs_path(path):
    return str(pathlib.Path(os.path.dirname(__file__), path))


def get_font(config, face):
    font_config = config["FONT"]
    face_config = config["LAYOUT"]["FACE"]

    font = PIL.ImageFont.truetype(
        abs_path(font_config["PATH"] + font_config["MAP"][face_config[face]["TYPE"]]),
        face_config[face]["SIZE"],
    )
    return font


def get_unit(config, name):
    param_list = config["SENSOR"]["PARAM_LIST"]
    param_list.append(config["POWER"]["DATA"]["PARAM"])

    for param in param_list:
        if param["NAME"] == name:
            return param["UNIT"]


def draw_text(img, text, pos, face, align=True, color="#000"):
    draw = PIL.ImageDraw.Draw(img)

    font = get_font(config, face)
    next_pos_y = pos[1] + font.getsize(text)[1]

    if align:
        # 右寄せ
        None
    else:
        # 左寄せ
        pos = (pos[0] - font.getsize(text)[0], pos[1])

    draw.text(pos, text, color, font, None, font.getsize(text)[1] * 0.4)

    return next_pos_y


######################################################################
class SenseLargeHeaderPanel:
    def __init__(self, config, image, offset, width):
        self.config = config
        self.image = image
        self.offset = np.array(offset)
        self.width = width
        self.power_icon = PIL.Image.open(
            abs_path(self.config["ICON"]["PATH"] + self.config["ICON"]["MAP"]["POWER"]),
            "r",
        )

    def __get_temp_box_size(self):
        return get_font(config, "TEMP_LARGE").getsize("44.4")

    def __get_temp_unit_box_size(self):
        return get_font(config, "UNIT_LARGE").getsize(get_unit(self.config, "temp"))

    def __get_humi_box_size(self):
        return get_font(config, "HUMI_LARGE").getsize("100.0")

    def __get_humi_unit_box_size(self):
        return get_font(config, "UNIT_LARGE").getsize(get_unit(self.config, "humi"))

    def __get_power_box_size(self):
        # PIM が baseline を取得できないっぽいので，「,」ではなく「.」を使う
        return get_font(config, "POWER_LARGE").getsize("1.000")

    def __get_power_unit_box_size(self):
        size = get_font(config, "UNIT_LARGE").getsize(get_unit(self.config, "power"))
        return (int(size[0] * 1.2), size[1])

    def __get_power_10min_label_box_size(self):
        return get_font(config, "POWER_DETAIL_LABEL").getsize("10min")

    def __get_power_60min_label_box_size(self):
        return get_font(config, "POWER_DETAIL_LABEL").getsize("60min")

    def __get_power_180min_label_box_size(self):
        return get_font(config, "POWER_DETAIL_LABEL").getsize("180min")

    def __get_power_detail_value_box_size(self):
        return get_font(config, "POWER_DETAIL_VALUE").getsize(
            self.__get_power_str(2444).replace(",", ".")
        )

    def __get_power_str(self, value):
        if value is None:
            return "?  "
        else:
            return config["POWER"]["DATA"]["PARAM"]["FORMAT"].format(value)

    def offset_map(self, data):
        box_size = {
            "temp": self.__get_temp_box_size(),
            "temp_unit": self.__get_temp_unit_box_size(),
            "humi": self.__get_humi_box_size(),
            "humi_unit": self.__get_humi_unit_box_size(),
            "power": self.__get_power_box_size(),
            "power_unit": self.__get_power_unit_box_size(),
            "power_10min_label": self.__get_power_10min_label_box_size(),
            "power_60min_label": self.__get_power_60min_label_box_size(),
            "power_180min_label": self.__get_power_180min_label_box_size(),
            "power_detail_value": self.__get_power_detail_value_box_size(),
        }

        offset_map = {
            "power_icon_left": self.offset + np.array([0, 10]),
            "power_10min_value_right": self.offset + np.array([self.width, 0]),
            "power_60min_value_right": self.offset
            + np.array([self.width, box_size["power_detail_value"][1] + 35]),
            "power_180min_value_right": self.offset
            + np.array([self.width, 2 * (box_size["power_detail_value"][1] + 35)]),
        }

        offset_map["power_10min_label_left"] = offset_map[
            "power_10min_value_right"
        ] + np.array(
            [
                -box_size["power_detail_value"][0]
                - box_size["power_10min_label"][0]
                - 10,
                box_size["power_detail_value"][1] - box_size["power_10min_label"][1],
            ]
        )

        offset_map["power_60min_label_left"] = offset_map[
            "power_60min_value_right"
        ] + np.array(
            [
                -box_size["power_detail_value"][0]
                - box_size["power_60min_label"][0]
                - 10,
                box_size["power_detail_value"][1] - box_size["power_60min_label"][1],
            ]
        )

        offset_map["power_180min_label_left"] = offset_map[
            "power_180min_value_right"
        ] + np.array(
            [
                -box_size["power_detail_value"][0]
                - box_size["power_180min_label"][0]
                - 10,
                box_size["power_detail_value"][1] - box_size["power_180min_label"][1],
            ]
        )

        offset_map["power_unit_right"] = np.array(
            [
                offset_map["power_10min_label_left"][0] - 50,
                offset_map["power_10min_value_right"][1]
                + box_size["power"][1]
                - box_size["power_unit"][1],
            ]
        )
        offset_map["power_right"] = np.array(
            [
                offset_map["power_unit_right"][0] - box_size["power_unit"][1] - 10,
                offset_map["power_10min_value_right"][1],
            ]
        )

        return offset_map

    def draw(self, data):
        logging.info("draw header")

        offset_map = self.offset_map(data)
        next_draw_y_list = []

        ############################################################
        # 電力
        img.paste(self.power_icon, tuple(offset_map["power_icon_left"]))

        next_draw_y_list.append(
            draw_text(
                self.image,
                "10min",
                offset_map["power_10min_label_left"],
                "POWER_DETAIL_LABEL",
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                "60min",
                offset_map["power_60min_label_left"],
                "POWER_DETAIL_LABEL",
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                "180min",
                offset_map["power_180min_label_left"],
                "POWER_DETAIL_LABEL",
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                self.__get_power_str(data["power"]["10min"]),
                offset_map["power_10min_value_right"],
                "POWER_DETAIL_VALUE",
                False,
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                self.__get_power_str(data["power"]["60min"]),
                offset_map["power_60min_value_right"],
                "POWER_DETAIL_VALUE",
                False,
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                self.__get_power_str(data["power"]["180min"]),
                offset_map["power_180min_value_right"],
                "POWER_DETAIL_VALUE",
                False,
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                get_unit(config, "power"),
                offset_map["power_unit_right"],
                "UNIT_LARGE",
                False,
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                self.__get_power_str(data["power"]["3min"]),
                offset_map["power_right"],
                "POWER_LARGE",
                False,
            )
        )

        return int(max(next_draw_y_list) - 10)


######################################################################
class SenseLargeFooterPanel:
    def __init__(self, config, image, offset, width):
        self.config = config
        self.image = image
        self.offset = np.array(offset)
        self.width = width
        self.calendar_icon = PIL.Image.open(
            abs_path(
                self.config["ICON"]["PATH"] + self.config["ICON"]["MAP"]["CALENDAR"]
            ),
            "r",
        )

    def __get_date_box_size(self, value):
        return get_font("date_large").getsize("12331")

    def __get_wday_box_size(self):
        return get_font("wday_large").getsize("(金)")

    def offset_map(self, data):
        box_size = {
            "date": self.__get_date_box_size(data["date"]),
            "wday": self.__get_wday_box_size(),
        }

        return {
            "calendar_icon_left": self.offset + np.array([0, 0]),
            "date_right": self.offset + np.array([self.width - box_size["wday"][0], 0]),
            "wday_right": self.offset
            + np.array([self.width, box_size["date"][1] - box_size["wday"][1]]),
        }

    def draw(self, data):
        logging.info("draw footer")

        data["date_str"] = "{0:%-m/%-d}".format(data["date"])
        data["wday_str"] = "(%s)" % (
            ["月", "火", "水", "木", "金", "土", "日"][data["date"].weekday()]
        )

        offset_map = self.offset_map(data)
        next_draw_y_list = []

        ############################################################
        # 日付
        # img.paste(self.calendar_icon, tuple(offset_map['calendar_icon_left']))
        next_draw_y_list.append(
            draw_text(
                self.image,
                data["date_str"],
                offset_map["date_right"],
                "date_large",
                False,
                "#666",
            )
        )
        next_draw_y_list.append(
            draw_text(
                self.image,
                data["wday_str"],
                offset_map["wday_right"],
                "wday_large",
                False,
                "#666",
            )
        )
        return int(max(next_draw_y_list))


######################################################################
class SenseDetailPanel:
    def __init__(self, config, image, offset, width):
        self.config = config
        self.image = image
        self.offset = np.array(offset)
        self.width = width

    def __get_place_box_size(self):
        font = get_font(config, "PLACE")
        max_size = np.array([0, 0])

        for room in self.config["SENSOR"]["ROOM_LIST"]:
            size = np.array(font.getsize(room["LABEL"]))
            max_size = np.maximum(max_size, size)

            return max_size + np.array([font.getsize(" ")[0], 0])

    def __get_temp_box_size(self):
        return get_font(self.config, "TEMP").getsize("44.4")

    def __get_temp_unit_box_size(self):
        size = get_font(self.config, "UNIT").getsize(get_unit(self.config, "temp"))
        return (int(size[0] * 1), size[1])

    def __get_humi_box_size(self):
        return get_font(config, "HUMI").getsize("888.8")

    def __get_humi_unit_box_size(self):
        size = get_font(self.config, "UNIT").getsize(get_unit(self.config, "humi"))
        return (int(size[0] * 1), size[1])

    def __get_co2_box_size(self):
        return (
            get_font(config, "CO2").getsize("2,888")[0],
            get_font(config, "CO2").getsize("4")[1],
        )

    def __get_co2_unit_box_size(self):
        # PIM が baseline を取得できないっぽいので，descent が無い「m」を使う
        size = get_font(self.config, "UNIT").getsize(
            "m" * len(get_unit(self.config, "co2"))
        )
        return (int(size[0] * 0.8), size[1])

    def offset_map(self):
        box_size = {
            "place": self.__get_place_box_size(),
            "temp": self.__get_temp_box_size(),
            "temp_unit": self.__get_temp_unit_box_size(),
            "humi": self.__get_humi_box_size(),
            "humi_unit": self.__get_humi_unit_box_size(),
            "co2": self.__get_co2_box_size(),
            "co2_unit": self.__get_co2_unit_box_size(),
        }

        col_gap = (
            self.width
            + box_size["place"][0]
            - functools.reduce(
                (lambda x, y: x + y), map(lambda x: x[0], box_size.values())
            )
        ) / 2

        max_height = max(map(lambda x: x[1], box_size.values()))

        offset_map = {
            "place-left": (0, 0),
            "temp-right": (box_size["temp"][0], box_size["place"][1] * 1.2),
        }

        offset_map["temp_unit-right"] = np.array(
            [offset_map["temp-right"][0], offset_map["temp-right"][1]]
        ) + np.array([box_size["temp_unit"][0], max_height - box_size["temp_unit"][1]])

        offset_map["humi-right"] = np.array(
            [offset_map["temp_unit-right"][0], offset_map["temp-right"][1]]
        ) + np.array([col_gap + box_size["humi"][0], max_height - box_size["humi"][1]])

        offset_map["humi_unit-right"] = np.array(
            [offset_map["humi-right"][0], offset_map["temp-right"][1]]
        ) + np.array([box_size["humi_unit"][0], max_height - box_size["humi_unit"][1]])

        offset_map["co2-right"] = np.array(
            [offset_map["humi_unit-right"][0], offset_map["temp-right"][1]]
        ) + np.array([col_gap + box_size["co2"][0], max_height - box_size["co2"][1]])

        offset_map["co2_unit-right"] = np.array(
            [offset_map["co2-right"][0], offset_map["temp-right"][1]]
        ) + np.array([box_size["co2_unit"][0], max_height - box_size["co2_unit"][1]])

        for key in offset_map.keys():
            offset_map[key] += self.offset

        offset_map["line_height"] = box_size["place"][1] + max_height * 1.40

        return offset_map

    def get_format(self, key):
        for param in self.config["SENSOR"]["PARAM_LIST"]:
            if param["NAME"] == key:
                return param["FORMAT"]
        return "{}"

    def get_formatted_value(self, data, key):
        if key in data:
            return self.get_format(key).format((data[key]))
        else:
            return "?  "

    def draw(self, data_list):
        logging.info("draw detail")

        offset_map = self.offset_map()
        next_draw_y_list = []

        i = 0
        for data in data_list:
            line_offset = np.array([0, (offset_map["line_height"] * i)])
            next_draw_y_list.append(
                draw_text(
                    self.image,
                    data["place"],
                    offset_map["place-left"] + line_offset,
                    "PLACE",
                )
            )

            next_draw_y_list.append(
                draw_text(
                    self.image,
                    self.get_formatted_value(data, "temp"),
                    offset_map["temp-right"] + line_offset,
                    "TEMP",
                    False,
                )
            )
            next_draw_y_list.append(
                draw_text(
                    self.image,
                    get_unit(self.config, "temp"),
                    offset_map["temp_unit-right"] + line_offset,
                    "UNIT",
                    False,
                )
            )
            next_draw_y_list.append(
                draw_text(
                    self.image,
                    self.get_formatted_value(data, "humi"),
                    offset_map["humi-right"] + line_offset,
                    "HUMI",
                    False,
                )
            )
            next_draw_y_list.append(
                draw_text(
                    self.image,
                    get_unit(self.config, "humi"),
                    offset_map["humi_unit-right"] + line_offset,
                    "UNIT",
                    False,
                )
            )
            if "co2" in data:
                next_draw_y_list.append(
                    draw_text(
                        self.image,
                        self.get_formatted_value(data, "co2"),
                        offset_map["co2-right"] + line_offset,
                        "CO2",
                        False,
                    )
                )
                next_draw_y_list.append(
                    draw_text(
                        self.image,
                        get_unit(self.config, "co2"),
                        offset_map["co2_unit-right"] + line_offset,
                        "UNIT",
                        False,
                    )
                )
            i += 1

        return int(max(next_draw_y_list)) + 30


######################################################################
class UpdateTimePanel:
    def __init__(self, config, image, offset, width):
        self.config = config
        self.image = image
        self.offset = np.array(offset)
        self.width = width

    def __get_time_box_size(self):
        return get_font(self.config, "TIME").getsize(
            "{0:%Y-%m-%d %H:%M} 更新".format(datetime.datetime.now())
        )

    def offset_map(self, data):
        box_size = {
            "time": self.__get_time_box_size(),
        }

        return {
            "time_right": self.offset + np.array([self.width, -20]),
        }

    def draw(self, data):
        logging.info("draw update time")

        offset_map = self.offset_map(data)
        next_draw_y_list = []

        next_draw_y_list.append(
            draw_text(
                self.image,
                "{0:%Y-%m-%d %H:%M} 更新".format(data["date"]),
                offset_map["time_right"],
                "TIME",
                False,
                "#666",
            )
        )

        return int(max(next_draw_y_list)) + 40


######################################################################
# InfluxDB にアクセスしてセンサーデータを取得
def get_db_value(config, hostname, measure, param, period="1h", window="3m"):
    token = os.environ.get("INFFLUXDB_TOKEN") or config["INFLUXDB"]["TOKEN"]

    client = influxdb_client.InfluxDBClient(
        url=config["INFLUXDB"]["URL"],
        token=token,
        org=config["INFLUXDB"]["ORG"],
    )

    query_api = client.query_api()
    table_list = query_api.query(
        query=FLUX_QUERY.format(
            bucket=config["INFLUXDB"]["BUCKET"],
            measure=measure,
            hostname=hostname,
            param=param,
            period=period,
            window=window,
        )
    )

    return table_list[0].records[0].get_value()


def get_sensor_data_map(config):
    logging.info("fetch sensor data")

    data = []
    for room in config["SENSOR"]["ROOM_LIST"]:
        value = {"place": room["LABEL"]}
        for param in ["temp", "humi", "co2"]:
            try:
                value[param] = get_db_value(
                    config,
                    room["HOST"]["NAME"],
                    room["HOST"]["TYPE"],
                    param,
                    period="1h",
                    window="3m",
                )
            except:
                pass
        data.append(value)

    return data


def get_power_data(config, window):
    try:
        return get_db_value(
            config,
            config["POWER"]["DATA"]["HOST"]["NAME"],
            config["POWER"]["DATA"]["HOST"]["TYPE"],
            "power",
            period="6h",
            window=window,
        )
    except:
        return None


def get_power_data_map(config):
    logging.info("fetch power data")

    power_data = {
        "3min": get_power_data(config, "3m"),
        "10min": get_power_data(config, "10m"),
        "60min": get_power_data(config, "60m"),
        "180min": get_power_data(config, "180m"),
    }
    if power_data["3min"] is None:
        power_data["3min"] = power_data["10min"]

    return power_data


# @retry(stop_max_attempt_number=10, wait_fixed=2000)
def draw_panel(config, img):
    sense_data = get_sensor_data_map(config)

    next_draw_y = 0
    panel_margin = [
        config["LAYOUT"]["MARGIN"]["WIDTH"],
        config["LAYOUT"]["MARGIN"]["HEIGHT"],
    ]
    sense_header_panel = SenseLargeHeaderPanel(
        config,
        img,
        np.array(panel_margin) + np.array([0, next_draw_y]),
        config["PANEL"]["DEVICE"]["WIDTH"] - config["LAYOUT"]["MARGIN"]["WIDTH"] * 2,
    )

    next_draw_y = sense_header_panel.draw(
        {
            "power": get_power_data_map(config),
        }
    )

    sense_detail_panel = SenseDetailPanel(
        config,
        img,
        np.array(panel_margin) + np.array([0, next_draw_y]),
        config["PANEL"]["DEVICE"]["WIDTH"] - config["LAYOUT"]["MARGIN"]["WIDTH"] * 2,
    )
    next_draw_y = sense_detail_panel.draw(sense_data)

    update_time_panel = UpdateTimePanel(
        config,
        img,
        np.array(panel_margin) + np.array([0, next_draw_y]),
        config["PANEL"]["DEVICE"]["WIDTH"] - config["LAYOUT"]["MARGIN"]["WIDTH"] * 2,
    )

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9), "JST"))
    next_draw_y = update_time_panel.draw({"date": now})


######################################################################
logger.init("Kindle Sensor Panel")

logging.info("start to create image")

config = load_config()
img = PIL.Image.new(
    "L",
    (config["PANEL"]["DEVICE"]["WIDTH"], config["PANEL"]["DEVICE"]["HEIGHT"]),
    "#FFF",
)

try:
    draw_panel(config, img)
except Exception:
    import traceback

    draw = PIL.ImageDraw.Draw(img)
    draw.rectangle(
        (0, 0, config["PANEL"]["DEVICE"]["WIDTH"], config["PANEL"]["DEVICE"]["HEIGHT"]),
        fill=(255),
    )

    title_offset = get_font(config, "ERROR_TITLE").getsize("ERROR")
    draw_text(img, "ERROR", (20, 20), "ERROR_TITLE")
    draw_text(
        img,
        "\n".join(textwrap.wrap(traceback.format_exc(), 45)),
        (20, 20 + title_offset[1] + 40),
        "ERROR_DETAIL",
    )

    print(traceback.format_exc(), file=sys.stderr)

img.save(sys.stdout.buffer, "PNG")

exit(0)
