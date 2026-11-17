# Bulb battery and one-board EVT

The product PCB carries the retained charger, motor driver and independent
charge guard alongside the flange's USB contacts, ESP32, controls and compass.
The protected pack sits below the motor in the metal body, offset 1 mm through
its thickness. The editable PCB and its schematic are in the
[one-board KiCad project](https://github.com/researchanddesire/buttplug/blob/codex/project-setup/hardware/pcb/evt1/one-board/compass-one-board.kicad_pro).
The board uses the existing 82 × 26 mm outline and four contact datums.

The pack carries three dry thermistors. TH1 feeds the charger TS input and TH2
feeds the independent guard. TH3 reports pouch temperature through J8 and the
ADS1115 AIN2 channel. The tip sensor stays on AIN0, and AIN1 measures half the
shared pulsed excitation. Build the `evt1-one-board` firmware profile to read a
separate `pack_temperature_millic` and `pack_temperature_sampled_ms` in device
status. The motor enable and charge permission follow the hardware design.
JP1 ships open for bring-up.

The 12-conductor neck study keeps two pack power wires, two motor wires, two
tip wires and six pack thermistor wires. The pack monitor head sits on the
underside of the pack. The [FreeCAD fit check](https://github.com/researchanddesire/buttplug/blob/codex/project-setup/hardware/pcb/evt1/one-board/pack-monitor-pose-fit.json)
covers the sensor and tails to the neck exit in the assembled nominal and growth
poses. Insulation and restraint, actual motor lead geometry, connector dressing
and cap closure with the loom still require trial.
The [editable FreeCAD studies](https://github.com/researchanddesire/buttplug/tree/codex/project-setup/hardware/cad/manufacturing-layout/one-board-evt1)
include the bulb pack, original flange fit and current connector access.

The [master bench PCB](https://github.com/researchanddesire/buttplug/blob/codex/project-setup/hardware/pcb/evt1/one-board-dev/README.md) uses
the same core circuit with a larger outline. A single polarized J112 key
selects VBUS and both USB data lines from PC J110 or dock J111. Leave J112
empty for independent plug or dock bring-up. Change the key with all power
off. The board also exposes rail isolation, current measurement, thermistor
simulation and scope access.

The compact board reuses CT1–CT4 for either the dock or the direct PC contact
fixture. The two fixtures occupy the same seat, and only one can attach.
Move between them by fully removing the first mate, then attach the second
for a fresh USB session. Firmware disables the USB pads on source loss and
waits for 100 ms of continuous presence before reattaching. The fixture keeps
Power/Mode accessible for hardware ROM recovery. Use the [evaluation and
ordering guide](https://github.com/researchanddesire/buttplug/blob/codex/project-setup/hardware/design/evt1-bench-ordering/master-bench-eval/README.md)
for the sequence and vendor operations.

Both routed boards pass KiCad 10.0.8 ERC, DRC and parity with all checks
enabled. The prior Compact revision passed 9,432 nominal solid checks on the
flange and seated connectors. C12 and C22 stay empty for a 44.7 µF nominal SYS
bank. The seven shortage substitutions are specified in both native KiCad
projects. Both use the RESI recommended land pattern for R21/R43. Use fresh
Gerbers, BOM and placement files for this revision, and obtain assembler
acceptance of the custom contact/pigtail operations before release. The [source README](https://github.com/researchanddesire/buttplug/blob/codex/project-setup/hardware/pcb/evt1/one-board/README.md)
describes the CAM export. Verify installed wiring, retention and behavior on
the first article before applying the result to the sealed product.
