# Compass EVT1 device

The compact, four-layer device PCB is 52 × 20 × 1 mm and populated on
both sides. Open [the KiCad project](compass-one-board.kicad_pro) to view the
charger, motor driver, ESP32-C3, sensors, buttons and four dock contacts.
The [FreeCAD assembly](mech/compass-device.FCStd) puts the PCB in a
56 × 32 mm rigid flange and the pack in a removable cradle in the bulb.
Keep the linked parts in the [mechanical source directory](mech/README.md).

| Connector | Function |
| --- | --- |
| J2 | Three-wire protected pack, JST SH. Pins 1 P+, 2 P−, 3 NTC |
| J3 | Motor pair, side-entry JST SH |
| J4 | Bench service and recovery, JST SH |
| J5 | Tip NTC pair, side-entry JST SH |
| CT1–CT4 | Dock GND, D−, D+ and 5 V |

The [BC-PACK-EVT1-002 request](PACK-RFQ.md) calls for one internal 10 kΩ B3435
NTC returned to P−. It feeds the BQ24074 charge-temperature cutoff and U7 AIN2.
The `evt1-one-board` firmware target still uses the former pulsed-divider
acquisition and conversion for AIN2. The shared charger-biased reading
needs implementation and bench validation. The 1 A JST SH rating also needs
reconciliation with the requested 1.5 A continuous pack load.

The [harness sources](../../../cables/evt1/one-board/README.md) define the seven
installed conductors and a separate bench service cable. Their starting stock
lengths come from the CAD wire paths. Check bend radii, crimp retention and
fit on the trial build.

See the [developer and assembly site](https://researchanddesire.github.io/buttplug/)
for the construction drawings, seal sections, assembly sequence and bring-up
plan. Some FreeCAD generation scripts still assume the original checkout path.
The saved native can be opened with its relative part links in place.
The PCB STEP is the mechanical integration model from before the last layout
edits. The compact assembly, mating interface and charging path still need
physical qualification before a fabrication release.
