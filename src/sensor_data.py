#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import influxdb_client
import os
import traceback
import logging


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


def get_db_value(config, hostname, measure, param, period="1h", window="3m"):
    try:
        token = os.environ.get("INFLUXDB_TOKEN", config["INFLUXDB"]["TOKEN"])
        query = FLUX_QUERY.format(
            bucket=config["INFLUXDB"]["BUCKET"],
            measure=measure,
            hostname=hostname,
            param=param,
            period=period,
            window=window,
        )
        client = influxdb_client.InfluxDBClient(
            url=config["INFLUXDB"]["URL"],
            token=token,
            org=config["INFLUXDB"]["ORG"],
        )

        query_api = client.query_api()
        table_list = query_api.query(query=query)
        return table_list[0].records[0].get_value()
    except:
        logging.error("Flux query = {query}".format(query=query))
        logging.error(traceback.format_exc())
        return None
