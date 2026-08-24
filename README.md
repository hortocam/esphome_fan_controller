# UCG-Max Fan Controller

ESPHome-based, MQTT-driven PWM fan controller for a UniFi **UCG-Max** router, with
an SSD1306 OLED showing router temp, fan duty, and RPM.

The firmware itself is **agnostic about the temperature source**. It only
subscribes to MQTT topics; a small Prometheus→MQTT bridge publishes the current
router temperature. Point the bridge at any metric / router / data source
without ever touching the device firmware — swap the bridge, not the board.

## Why this exists

The UCG-Max sits on a custom stand with a Noctua 4-wire 12 V fan driven by a
temp-probe PWM controller. That controller's surface probe reads **~17–18 °C
below** the router's actual SoC/SNMP temperature, so it lags badly on load
spikes (a 3 °C jump while the fan is still spinning at idle speed). This project
replaces the probe controller with an ESP32 that reads the *real* temperature
and drives the fan from a proper curve.

## Architecture

```
+----------------+   SNMP / PromQL   +----------------------+
|  UCG-Max       |  ->  Prometheus  | prometheus_to_mqtt.py |
|  (SNMP exporter)                |  (bridge, e.g. on a CT) |
+----------------+                   +----------+-----------+
                                                | MQTT publish
                                                | homelab/ucgmax/temperature
                                                v
                                     +----------------------+
                                     |  ESP32 (ESPHome)     |
                                     |  - subscribes MQTT  |
                                     |  - fan curve + fail-|
                                     |    safe             |
                                     |  - drives 4-wire PWM|
                                     |  - OLED display     |
                                     +----------------------+
```

**The one line that ties a specific source to the fan is the MQTT topic the
bridge publishes to.** Point the bridge at any metric (SNMP OID, PromQL query,
a different router, a weather API...) and the ESP32 behaves identically.

## Repository layout

```
esphome/
  fan_controller.yaml   # ESPHome device config (pins, curve, MQTT, OLED)
  secrets.yaml          # LOCAL-ONLY, gitignored - fill in, never commit
scripts/
  prometheus_to_mqtt.py # Prometheus -> MQTT bridge (the only SNMP/PromQL spot)
firmware/               # (future) raw PlatformIO fallback if ESPHome is dropped
README.md
LICENSE                 # MIT
```

## MQTT topics

| Topic | Direction | Payload | Purpose |
|-------|-----------|---------|---------|
| `homelab/ucgmax/temperature` | bridge → ESP32 | float, °C | router temp driving the curve |
| `homelab/ucgmax/#` | bridge → ESP32 | any | keeps failsafe armed (heartbeat) |

The ESP32 also exposes ESPHome-native sensors (`Fan Duty`, `Fan RPM`, `Router
Temperature`, `Status`) over its own MQTT discovery topics, so it can appear as
a normal device in Home Assistant if you want.

## Fan curve

Tuned to **SNMP/tsens** temperatures (the real SoC temp):

| Temp (°C) | Duty |
|-----------|------|
| < 45 | 20 % |
| 45–65 | linear 20 → 100 % |
| > 65 | 100 % |

## Failsafe

If no MQTT message arrives for `stale_timeout` (default 60 s) — bridge down,
WiFi lost, topic renamed — the fan drives to `fail_duty` (default 50 %) so the
router stays cool rather than going silent. Two layers are intended: this
software failsafe **plus** a 10 kΩ pull-up on the PWM line to 5 V that drives
the fan to 100 % if the ESP32 dies entirely.

## Wiring (pending — verify against your board)

Pin assignments in `fan_controller.yaml` are **placeholders** until the board
silkscreen is read. 4-wire fan header:

| Fan wire | Colour (typical) | ESP32 GPIO |
|----------|------------------|-----------|
| Ground   | black            | GND        |
| +12 V    | yellow           | 12 V (level-shifted / via fan supply) |
| Tach     | green            | GPIO_NC (pulse_counter) |
| PWM      | blue             | GPIO_NC (ledc 25 kHz) |

> **12 V warning:** do NOT feed 12 V into a bare ESP32 GPIO. Either drive the
> fan's PWM input directly (it accepts a 3.3 V signal on many Noctua fans) or
> use a level shifter (e.g. BSS138/2N7000) if the fan requires a 5 V PWM.

OLED (SSD1306 128×64) on I2C (SDA/SCL), address 0x3C.

## Setup

```bash
# 1. Install ESPHome (any host - Mac or a Python venv on the Pi)
pip install esphome   # or: uv tool install esphome

# 2. Set your secrets
cp esphome/secrets.yaml.example esphome/secrets.yaml
$EDITOR esphome/secrets.yaml      # wifi, mqtt broker/user/pass

# 3. Set the real pin numbers in esphome/fan_controller.yaml

# 4. Validate + build + flash
esphome compile esphome/fan_controller.yaml
esphome run esphome/fan_controller.yaml   # or upload via serial / OTA
```

## The bridge

`scripts/prometheus_to_mqtt.py` polls a Prometheus query (default
`lmTempSensorsValue{instance="172.16.10.1"}`, the SNMP-exposed router temps) and
publishes the max of the two sensors (millidegrees ÷ 1000 → °C) to MQTT. Run it
as a service or cron. Edit the PromQL in the `--query` flag to change the source
without touching firmware. See the script header for full options.

## Status

- [x] Repo scaffold, ESPHome layout, bridge
- [ ] Verify wiring / set pins
- [ ] First flash + serial boot log
- [ ] OLED layout pass on real hardware
- [ ] Failsafe E2E (kill MQTT, watch fan)
- [ ] Enclosure + install

MIT Licensed — see `LICENSE`.
