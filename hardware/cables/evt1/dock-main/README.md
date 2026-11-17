# EVT1 wired dock harnesses

Use these recipes with the [active wired Main](../../../pcb/evt1/case-telemetry-study/wired-main/README.md),
spring-pin board, populated JST lid and [matched 4.22 Ω UV modules](../../../pcb/evt1/case-telemetry-study/wired-main/uv-assembly/README.md).
Lay the wires into the dock before trimming or fitting strain relief. Final
trim lengths and wire restraint still need an assembled fit check.

| Interface | WireViz source |
| --- | --- |
| Main J102 to spring-pin J94 | [Four hand-soldered USB and power wires](main-to-pins.yml) |
| Main J201 to lid J301, exposed boards | [20-way Molex 0151660220 Type D flex](hinge-flex/main-to-lid-ui.yml) |
| Main J201 to lid J301, installed | [20-way offset flex supplier drawing](../../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/display-flex-feasibility/README.md) |
| Main J621 to base J401 and Main J622 to lid J501 | [GH8 branches](uv-harnesses/README.md) |
| Main J630 to left Hall J1 and Main J650 to right Hall J1 | [Left Hall](hall-left.yml) · [Right Hall](hall-right.yml) |
| UV base rear lands TP401–TP404 | [Thermistor and thermostat](remote-thermal/uv-base-remote.yml) |
| UV lid rear lands TP501–TP504 | [Thermistor and thermostat](remote-thermal/uv-lid-remote.yml) |

For one dock, these recipes total **4.30 m of Allied 1371-26-7** and **1.00 m
of Accu-Glass 100690** starting stock before scrap. Allow four JST GHR-08V-S
and two GHR-03V-S housings, plus 38 SSHL-002T-P0.2 fitted crimp contacts
across the UV and Hall looms. Use one
Molex 0151660220 flex for the exposed-board check. Order one Vishay NTCLE413E2103F524A
and one Sensata 67L045 per UV board. Those four thermal parts also appear in
the UV board quote manifests as separate purchases. Count them once.
[Allied wire](https://www.awcwire.com/product/1371-26-7) ·
[JST GH](https://www.jst.com/wp-content/uploads/2025/06/eGH.pdf) ·
[Molex flex](https://www.molex.com/en-us/products/part-detail/0151660220)

## Main to spring-pin board

Use this loom between the wired Main and the existing spring-pin
board. Both boards have four Ø1.8 mm solder lands at 2.5 mm pitch. The Main
lands are on F.Cu and the spring-pin lands are on B.Cu. Identify pad 1 from
the artwork and mark each wire at both ends before soldering.

| Pin at both ends | Main J102 | Spring-pin J94 | Spring contact |
| --- | --- | --- | --- |
| 1 | GND | GND | P91 |
| 2 | PLUG_USB_DM | DOCK_DM | P92 |
| 3 | PLUG_USB_DP | DOCK_DP | P93 |
| 4 | CONTACT_5V | DOCK_5V | P94 |

Prepare four 150 mm starting blanks of Accu-Glass **100690**, 28 AWG
stranded wire. This carries forward the earlier cradle's stock for bench
assembly. Verify insulation OD ≤0.60 mm and use at least 4 mm centerline bend
radius. Keep the USB wires paired with short exposed ends. Check all four
end-to-end connections and adjacent-pad isolation before power. The 150 mm
stock length is a trimming allowance. Check solder-joint egress, restraint,
received route length and USB behavior with the assembled dock.

The [wired dock CAD](../../../cad/evt1-assembly/evt1-wired/README.md#main-to-spring-pin-harness) now includes the four installed paths through the existing hood. Nominal pad-to-pad centerlines for 1/GND, 2/D−, 3/D+ and 4/5 V measure **91.12, 94.33, 98.30 and 101.71 mm** respectively. Closed-position CAD shows a 4.00 mm minimum sampled bend radius and 0.142 mm minimum mutual gap. Keep the WireViz starting blanks at 150 mm until a real build fixes stripping, egress, restraint and trim.
[Accu-Glass catalog](https://www.accuglassproducts.com/sites/default/files/catalog/kapton_insulated_uhv_wire.pdf)

Run from this directory using WireViz 0.4.1 with PyYAML.

```sh
mkdir -p /tmp/compass-wired-dock-loom
wireviz -f hpst -o /tmp/compass-wired-dock-loom main-to-pins.yml
python3 check_main_to_pins.py --exports /tmp/compass-wired-dock-loom
```

The generated [child BOM](/private/tmp/compass-wired-dock-loom/main-to-pins.bom.tsv)
covers 0.60 m of wire per bench harness. The
[native checks](native-checks.json) bind both boards, the netlists, the saved
closed-pose route and the diagram/BOM outputs. The stock and electrical pinout
are ready to quote.
Physical fit, strain relief, finished cut lengths and powered USB qualification remain open.

## Hall heads to Main

Both Hall heads mount in the lower dock. The two looms stay in the base.
Label the identical GH3 housings **A / LEFT / J630** and **B / RIGHT / J650**
before they enter the case. Verify each pin number at both ends. The receiver
design uses two outward-facing JST **SM03B-GHS-TB(LF)(SN)** headers at the
[approved Main locations](../../../cad/evt1-assembly/evt1-wired/README.md#main-side-connector-access).

| Pin at both ends | Left / channel A | Right / channel B | Hall head J1 pad |
| --- | --- | --- | --- |
| 1 | J630 feed | J650 feed | HEAD_FEED |
| 2 | J630 signature | J650 signature | SIG |
| 3 | J630 dedicated return | J650 dedicated return | Local GND |

Keep the two head returns separate back to their own Main return shunts.
Leave Main header mounting tabs on system ground. Neither return conductor
gets a connection to those tabs, another channel or the chassis.
[Receiver contract and fault assumptions](../../../pcb/evt1/dock-safety/wired-hall-head/README.md#main-receiver-candidate)

For both looms together, buy two JST **GHR-03V-S** housings, six installed
**SSHL-002T-P0.2** contacts plus four for crimp samples and spares, and
**1.50 m** of Allied **1371-26-7** before scrap. The six 250 mm starting
blanks are trim stock. Buy the two SMT headers with Main, and count them
once. Use the JST WC-GH2630 tool for loose contacts or specify the exact
wire and contact to a crimp shop. At receipt check jacket OD against
0.76–1.00 mm, inspect crimp geometry and pull-test samples. Keep the
crimp-end strands untinned. [JST GH](https://www.jst.com/wp-content/uploads/2025/06/eGH.pdf) ·
[JST crimp tools](https://www.jst.com/wp-content/uploads/2025/06/eCRIMPING_MACHINES_AND_TOOLS.pdf) ·
[Allied wire](https://www.awcwire.com/product/1371-26-7)

1. Crimp and load both labeled GH3 harnesses, leaving the head ends
   unsoldered and at their starting stock length. Mate both GH3 plugs
   while the lower liner is off and the latch faces are accessible.
2. Form each lower bundle using the
   [native Hall lead paths](../../../cad/evt1-assembly/evt1-wired/HallLeadRoutes.FCStd).
   Left feed, signal and return use liner passage positions Y26.60, 28.00
   and 25.20 mm, respectively. Right feed, signal and return use Y25.20,
   26.60 and 28.00 mm. Keep the upper ends straight, thread them through
   the corresponding openings, and seat the liner. The
   [loading check](../../../cad/evt1-assembly/evt1-wired/README.md#main-side-connector-access)
   covers nominal vertical liner travel with the loose ends straight.
3. With the liner seated, park the three loose ends ahead of each head
   at about dock Y22.70 mm to clear bracket insertion. Slide each
   populated head component-side up toward the hinge (+Y) under its
   bracket lip before offering the pair outward from the chamber. Fit the
   two spacers and screws into the liner. Form the head ends, then check
   withdrawal slack and the planned restraint before trimming. Solder the
   three numbered leads to their 0.80 × 1.80 mm J1 top lands, with the
   jackets exiting flat toward dock −Y. Verify actual solder and tool access
   before building this sequence. Remove or release the fitted wire ends
   before lifting the liner for service.
4. With UV disconnected, verify each assembled loom end to end and check
   isolation for neighboring pins, both channels, and chassis. The receiver
   model allows up to 3 Ω in the fitted feed path and 2 Ω in the fitted
   return path beyond its Main shunt. Verify each with the assembled
   contacts. Check open-wire leakage against the 10 µA feed/return
   allowances and capture startup and fault response on the completed Main.

Generate the diagrams and child BOMs with WireViz 0.4.1.

```sh
mkdir -p /tmp/compass-wired-dock-loom
wireviz -f hpst -o /tmp/compass-wired-dock-loom hall-left.yml hall-right.yml
```

[Left Hall BOM](/private/tmp/compass-wired-dock-loom/hall-left.bom.tsv) ·
[Right Hall BOM](/private/tmp/compass-wired-dock-loom/hall-right.bom.tsv)

## Lid flex and UV thermal parts

The 203 mm Type D bench flex has contacts on opposite faces. J201 and J301
use bottom-contact sockets. Check the received jumper in the intended
orientation with all 20 lanes connected number to number and isolated from
adjacent lanes. The installed flex needs the 25 mm offset in the supplier
drawing and must clear the UV wiring throughout lid travel.
[Hirose FH12](https://www.hirose.com/en/product/p/CL0586-0524-9-55) ·
[Molex flex drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/151/15166/151660097_sd.pdf)

On each UV board, the first two back lands connect the NTC monitor. The
second two connect the normally closed thermostat in the hardware cutoff
loop. Use the NTC's factory leads if they reach with strain relief. The
thermostat uses two 100 mm 28 AWG starting blanks per board. Protect the
individual solder joints and verify each part by continuity and response
before heatspreader attachment. Keep the NTC dry and qualify the installed
thermal response and electrical isolation on the actual heatspreader.
[Vishay thermistor](https://www.vishay.com/docs/29078/ntcle413.pdf) ·
[Sensata 6700](https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf)

Generate the peripheral BOMs and verify all 20 UI lanes and eight thermal
legs from this directory.

```sh
mkdir -p /tmp/compass-wired-dock-loom
wireviz -f hpst -o /tmp/compass-wired-dock-loom hinge-flex/*.yml remote-thermal/*.yml
python3 check_peripherals.py --exports /tmp/compass-wired-dock-loom
```

[UI flex BOM](/private/tmp/compass-wired-dock-loom/main-to-lid-ui.bom.tsv) ·
[Base thermal BOM](/private/tmp/compass-wired-dock-loom/uv-base-remote.bom.tsv) ·
[Lid thermal BOM](/private/tmp/compass-wired-dock-loom/uv-lid-remote.bom.tsv) ·
[Native checks](peripheral-native-checks.json)
