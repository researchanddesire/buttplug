# Radio add-on bench harness

This harness belongs to the archived radio study. The
[wired EVT](../../../../pcb/evt1/case-telemetry-study/WIRED-USB.md) uses the
[four-wire spring-pin loom](../main-to-pins.yml).

Use one six-way straight-through harness from Main J150 to radio J901. Both
headers are JST SM06B-GHS-TB(LF)(SN). Start with two **GHR-06V-S** housings,
twelve **SSHL-002T-P0.2** contacts and six 175 mm starting blanks of the
existing Allied **1371-26-7** 26 AWG stock. Allow extra contacts and wire for
crimp setup and pull tests. Gauge the received jacket against the contact's
0.76–1.00 mm range. [JST GH housing and contact drawings](https://www.jst.com/wp-content/uploads/2025/06/eGH.pdf)

Identify and mark pin 1 at both ends with the latch in view. Check each of the
six paths and adjacent-pin isolation with both boards unplugged. Use the loose
harness for bench bring-up. Pocket, feed-through, connector insertion path,
restraint, installed cut length and electrical limits for the final harness
remain to verify. [Dock placement review](../../../../cad/evt1-assembly/dock-harness-trial/radio-placement-review/README.md)

From this directory, generate the diagram and child BOM with WireViz 0.4.1.

```sh
mkdir -p /tmp/compass-radio-harness
wireviz -f hpst -o /tmp/compass-radio-harness main-to-radio.yml
python3 check_radio_harness.py --check --exports /tmp/compass-radio-harness
```

The [native audit](native-checks.json) checks both PCB pin contracts against
the schematic, all six WireViz connections and the three child BOM rows.
