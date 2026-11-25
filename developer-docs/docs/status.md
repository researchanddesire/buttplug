# Project status

The next build is an **unpowered compact device trial** and a **wired-dock
bench build**. An earlier inert appearance mockup printed. The compact PCB
and complete device/dock assembly still need physical commissioning.

## Device

| Area | Where it is | What is next |
| --- | --- | --- |
| Mechanical CAD | Saved assembly and nominal hard-part checks | Trial cap threading, lead routing and rear-nut access with inert parts |
| Metal parts | [Drawings](drawings.md) ready; alloy and tolerances not agreed | Machinist review and quote |
| Board | 52 × 20 mm. Nov 23: zero opens or parity findings, one U6 library-footprint warning | Resolve antenna geometry and refresh the board STEP and fabrication outputs |
| Battery | Spec and RFQ written (BC-PACK-EVT1-002) | Find a supplier and get samples |
| Seals | O-ring, skin bond and button domes designed | Seal the contact window; develop the casting |
| Assembly | [Illustrated trial sequence](assembly-guide.md) | Verify the access and assembly dependencies on the first inert build |
| Firmware | `evt1-one-board` profile written; not yet run on hardware | Read the battery thermistor the new way |

### Open questions

- **Antenna clearance.** The Nov 23 `build/check/drc-final.json` flags a U6
  library-footprint mismatch. Verify the antenna clearance before release.
- **Contact interface.** The baseline target faces recess 1.77 mm below the
  skin and their cover openings remain unsealed. A separate [flush-contact
  section](seals.md#6-contact-window) proposes cover support and individual rings.
- **Battery connector rating.** JST SH contacts are rated 1 A; the battery spec
  asks for 1.5 A continuous. Measure the real current first.
- **Wire bends.** The CAD routes bend the motor and sensor wires at 1.5 mm
  radius; the harness spec asks for at least 4 mm and 2 mm.
- **Assembly order.** Trial the rear nut while the flange is empty, then check
  that the module and leads can feed through and the cap can turn. See
  [steps 1 and 5](assembly-guide.md#device-assembly).
- **Battery temperature firmware.** The firmware still reads the battery
  thermistor as the earlier pulsed divider; the new board shares it with the
  charger's TS pin and needs a different conversion.

## Charging dock

| Area | Where it is | What is next |
| --- | --- | --- |
| Main board | Schematic complete; 13 connections still to route | Finish routing and checks, then order |
| Lid sensors | Hall boards designed; their receivers are not on Main yet | Add the receivers and connectors J630 and J650 |
| UV-C | Boards designed; LEDs stay disabled until the lid sensors pass | Leakage, heat and light tests |
| Lid wiring | Display flex designed; lid UV harness route not finished | Liner passages and a bend test |
| Device seat | Saved wired seat interferes with the compact flange. A revised row clears the retained case in CAD | Design a matching carrier, retainer and seat |
| Compact magnetic concept | Separate CAD with integral nest and fixed side UV rails | Integrate contacts, rail PCBs, thermal paths and lid cutoffs |
| Firmware | STM32 UI/UV and RP2040 host code written; host tests pass | First power-up |

## After the first build

- Calibrate the tip and battery temperatures and the compass on the finished
  device.
- Measure how the motor, the steel and the dock magnets affect the compass.
- Run an endurance test of the motor and the buttons.
- Test sealing, cleaning and the materials for body contact.

Record physical results in the Compass review document in the R+D project
Drive folder, with the Git commit and the CAD or board revision used.
