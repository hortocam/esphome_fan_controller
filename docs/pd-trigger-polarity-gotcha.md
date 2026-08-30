# USB-C PD Trigger — Fritzing Part Polarity Gotcha

> Logged 2026-08-30 after a failed solder attempt. **The Fritzing part's pinout did NOT
> match the physical module, and the netlist could not catch it.**

## What happened

The fan-controller perfboard used a common Fritzing "usbc to 12V module" part. When
soldering, the **polarity of that part was backwards from the physical USB-C PD trigger
module** — the Fritzing part showed +12V where the real board had GND (and vice-versa).
Reconciling that on the fly at the board produced a short.

## Why the netlist verification didn't catch it

The `fritzing-netlist-verification` workflow parses the exported netlist and maps Fritzing's
positional pins to GPIOs. But the netlist only knows **what Fritzing thinks the pins are**.
If the part's footprint itself is wrong vs the physical module, the netlist verifies
"correct" — because it matches the (wrong) part. This is the one class of error netlist
verification cannot catch.

## Lesson

For **power parts** (PD trigger, buck converter, regulators), always cross-check the
physical module's **silkscreen / datasheet pinout** against the Fritzing part's pin labels
BEFORE trusting the netlist. A reversed polarity on a power rail is a short waiting to
happen.

## Action

- Cameron is searching for a **better / correct Fritzing part** for the USB-C PD trigger
  (one whose pinout matches the physical module).
- When a replacement part is found, re-verify the layout with the netlist workflow, and
  confirm the physical module's +12V / GND / CC pins against the part before soldering.
