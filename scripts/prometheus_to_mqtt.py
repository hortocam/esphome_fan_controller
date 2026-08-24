#!/usr/bin/env python3
"""Prometheus -> MQTT temperature bridge for the UCG-Max fan controller.

Polls a Prometheus query for the router's temperature and publishes the result
to an MQTT topic that the ESPHome firmware subscribes to.

THIS IS THE ONLY PLACE A SPECIFIC METRIC / OID APPEARS IN THE WHOLE PROJECT.
The firmware just subscribes to `--topic`; change the data source by editing
`--query` here, never the device code.

Default query:
    lmTempSensorsValue{instance="172.16.10.1"}
This is the SNMP-exposed tsens temperature from the UniFi gateway, in
millidegrees. We take the MAX of the two sensors and divide by 1000 -> deg C.

Requirements: paho-mqtt, requests  (pip install paho-mqtt)

Example:
    python3 prometheus_to_mqtt.py \\
        --prometheus http://172.16.10.79:9090 \\
        --broker 172.16.10.x \\
        --topic homelab/ucgmax/temperature \\
        --interval 10
"""

import argparse
import json
import time
import urllib.parse
import urllib.request

try:
    import paho.mqtt.publish as mqtt_publish
except ImportError:
    mqtt_publish = None


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prometheus", default="http://172.16.10.79:9090",
                   help="Prometheus base URL")
    p.add_argument("--query", default='lmTempSensorsValue{instance="172.16.10.1"}',
                   help="PromQL query returning router temps in millidegrees")
    p.add_argument("--broker", required=True, help="MQTT broker host")
    p.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    p.add_argument("--username", default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--topic", default="homelab/ucgmax/temperature",
                   help="MQTT topic to publish to")
    p.add_argument("--interval", type=float, default=5.0,
                   help="poll/publish interval in seconds")
    p.add_argument("--retain", action="store_true",
                   help="retain the last temperature on the broker")
    return p.parse_args()


def query_prometheus(base, query):
    """Return list of float values from a Prometheus instant query."""
    url = base.rstrip("/") + "/api/v1/query?query=" + urllib.parse.quote(query)
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read().decode())
    if data.get("status") != "success":
        raise RuntimeError(f"Prometheus error: {data.get('error', data)}")
    out = []
    for res in data["data"]["result"]:
        try:
            out.append(float(res["value"][1]))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def temp_celsius(values, divisor=1000.0):
    """Max of the sensor values, millidegrees -> Celsius."""
    return max(values) / divisor if values else None


def publish(args, temp):
    if mqtt_publish is None:
        raise RuntimeError("paho-mqtt not installed. Run: pip install paho-mqtt")
    auth = {"username": args.username, "password": args.password} if args.username else None
    mqtt_publish.single(
        args.topic, payload=f"{temp:.1f}", qos=1, retain=args.retain,
        hostname=args.broker, port=args.port, auth=auth,
    )


def main():
    args = parse_args()
    while True:
        try:
            values = query_prometheus(args.prometheus, args.query)
            temp = temp_celsius(values)
            if temp is not None:
                publish(args, temp)
                print(f"{time.strftime('%H:%M:%S')} {temp:.1f} C -> {args.topic}", flush=True)
            else:
                print(f"{time.strftime('%H:%M:%S')} no values from query", flush=True)
        except Exception as e:  # keep the loop alive on transient errors
            print(f"error: {e}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
