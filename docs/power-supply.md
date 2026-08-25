# Power Supply Design — USB-C PD to Fan + Controller

A single surplus USB-C PD supply powers both the fan (12 V) and the controller
board (5 V). The key component is a **USB-C PD trigger module** (a PD *sink*)
that negotiates the 12 V PDO from the PSU, plus a buck converter to step that
down to 5 V for the NodeMCU.

## Block diagram

```
USB-C PD supply  (surplus, 5/9/12/20 V PDOs)
        │
        ▼
USB-C PD trigger module  (CH224K, strapped for 12 V)
        │   └── 12 V rail  ──┬──► Fan  (VCC +12 V, GND)
        │                    └──► Buck 12 V→5 V  (MP1584)  ──► NodeMCU 5V/VIN
```

- **12 V rail → fan directly.** The fan's PWM (GPIO25) and tach (GPIO34) logic
  lines are referenced to this rail's ground, so they stay under the 3.3 V logic
  domain of the ESP as long as everything shares a common ground.
- **Buck → NodeMCU 5V/VIN** (the on-board 3.3 V regulator then feeds the ESP +
  OLED). The buck only carries the board, not the fan, so it stays small.

## Parts (all ~$2–4 on AliExpress/Amazon)

| Component | Part | Notes |
|-----------|------|-------|
| PD trigger | **CH224K** breakout | Negotiates a requested PDO. Voltage-select straps (dip / solder) → set to 12 V. |
| Buck 12 V→5 V | **MP1587 / MP1584** or fixed-5 V mini buck | ~500 mA enough for ESP32 + OLED. Fixed 5 V simpler; adjustable trim to 5 V also fine. |

## Wiring / pinout

- **Common ground everywhere** — 12 V rail GND, buck GND, and NodeMCU GND all
  tied together. PWM/tach are referenced to the fan's ground, so one 0 V
  reference is mandatory.
- **NodeMCU 5V (VIN)** ← buck 5 V. No USB needed in the final mount.
- **PWM GPIO25 → fan PWM** (3.3 V logic, common-ground). Same as bench.
- **TACH GPIO34 ← fan tach**, with **10 kΩ pull-up to 3.3 V** (the ESP's 3.3 V,
  NOT the 12 V rail).

## PD supply requirements

- The surplus PSU must actually **advertise a 12 V PDO**. The list
  (5/9/12/20 V) is the standard PD set, so a 12 V PDO should be present — check
  the label for "12 V" in the output/POWER DELIVERY table.
- Use a **USB-C cable with the CC lines** (not a charge-only cable) so the
  CH224K can negotiate. A PD/e-marked cable is ideal.

## Failsafe (two layers)

1. **Software** — if MQTT data goes stale for `stale_timeout` (default 60 s),
   the ESP drives the fan to `fail_duty` (default 50 %). Covers bridge down /
   WiFi lost / topic renamed.
2. **Hardware (fail-open) — worth wiring now that we have a clean 5 V rail.**
   A **10 kΩ pull-up from the PWM line (GPIO25) to 5 V** holds the fan at
   ~100 % if the ESP32 dies or its GPIO floats, so the router stays cool even
   with a dead controller. Without this, a dead ESP32 leaves the fan stuck at
   whatever the last state was.

  **Pitfall:** this pull-up must be to the **5 V rail, NOT 3.3 V** and NOT to
  the 12 V rail — GPIO25 is a 3.3 V-tolerant pin; pulling it to 12 V would
  damage the ESP32.

## Bench verification checklist (before mounting)

- [ ] PD trigger outputs ~12 V (meter the 12 V rail to common GND).
- [ ] Buck outputs ~5 V (meter to common GND).
- [ ] NodeMCU boots from the buck 5 V (no USB).
- [ ] Fan spins at ~100 % when PWM pulled high (failsafe test: pull GPIO25 to 5 V).
- [ ] Tach reads a sane RPM at 100 % duty (~17 k RPM for the 17k fan).
- [ ] OLED on and readable.
