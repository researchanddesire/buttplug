# Compass EVT1 integrated device board

Open [compass-one-board.kicad_pro](compass-one-board.kicad_pro) in KiCad. The
schematic derives from the routed EVT1 body and single-flange projects. It
replaces J6/J7 and the old compass interconnect with local nets, and fits the
charger, motor driver, sensors, ESP32, controls and four dock contacts on one
82 × 26 mm board. See [schematic-checks.json](schematic-checks.json) for the
retained terminal and hardware charge-gate checks.

The pack is a 3-wire protected 1S LiPo (EEMB LP502030-PCM-NTC-LD class,
decided 2026-11-18): red P+, black P- and one internal NTC lead (10 kΩ at
25 °C, B 3435 typical; confirm from the chosen part). J2 is the three-land
PACK_P / GND / PACK_NTC interface (a JST SH 3-pin header since 2026-11-19, below). The pack NTC drives the BQ24074 TS pin
(the hardware charge-temperature cutoff, 0.3 V hot / 2.1 V cold at its
72..78 µA bias) and is read by the firmware on U7 AIN2 through R88 (series
10 k) and C88. R42 (470 k to 3V3) adds about 5 µA so the node can be read off
the dock as well; the firmware computes R = AIN2 / (I_TS + (3V3 − AIN2) / 470 k)
with I_TS = 75 µA while charging and 0 otherwise (AIN2 below about 0.28 V means
no charger bias; use the ±256 mV range off dock). The former second NTC
(PACK_GUARD, U8 window comparator with R43/R44/R45) and the dry pouch NTC
(J8, TH3) are gone: U8, R43, R44 and R45 are DNP, J8 and TH3 are removed,
and U9 plus JP1 remain the charge-permission chain. The pack request is
[PACK-RFQ.md](PACK-RFQ.md) with [pack-spec.json](pack-spec.json)
(BC-PACK-EVT1-002, 2026-11-21): a protected high-rate pack with its own 10 k
B 3435 NTC bonded to the cell and returned to P−, and a JST SH 3P plug wired
1 P+, 2 P−, 3 NTC. The JST SH contacts are rated 1 A, below the 1.5 A
continuous load the earlier pack request carried, so measure the real battery
current before ordering. JP1 starts open for bench testing.

Since 2026-11-19 J2 is a JST SM03B-SRSS-TB 1.0 mm 3-pin side-entry header
on B.Cu at the top edge, next to J3, so a stock 3-wire pack with a JST SH 3P
plug plugs in and nobody solders the battery. J3 moved 0.2 mm and J5
0.15 mm to make room; the old solder lands are gone. Pinout 1 PACK_P,
2 GND, 3 PACK_NTC. Since 2026-11-20 J5 (tip NTC) is a side-entry SM02B,
the same part as J3, instead of the vertical BM02B, whose mated plug hit
the flange tray; all three plugs now lie in the tray's wire trough. The
board passes DRC with schematic parity (0 errors, 0 unconnected).

The four contacts carry GND, D−, D+ and 5 V from either the dock or the
direct PC contact fixture. The compact board uses one device USB path. The
fixtures are mutually exclusive at the plug; completely withdraw one before
attaching the other. The [evaluation guide](../../../design/evt1-bench-ordering/master-bench-eval/README.md)
defines recovery, source-change and contact acceptance tests. The catalog
substitutions retain the four dock contact datums and their USB routes.

## Compact relayout (2026-11-18)

The board is now 52 × 20 mm, four layers, 1.0 mm, assembled on both sides
(regulators, inductors, the ESP32-C3 module and all connectors on the back;
the dock contacts, buttons, charger, sensors and logic on the front). The
82 × 26 mm first article is kept in git (commit e274ccb) and in
`backup/compass-one-board-82x26-20261118.kicad_pcb`; its mechanical fit
reports, the quote kit and the sha-bound review files above describe that
board and are stale for this one. The dock contact pitch, the antenna keepout
and the J3/J8 facing are unchanged; MH2 and MH4 were dropped (two provisional
M1.4 holes remain), and the flange tray has to be redesigned around the new
outline. Design rules were tightened to the fab's base-price limits: 0.1 mm
clearance and minimum track, 0.45/0.2 mm vias, one thermal spoke accepted.

`compact_layout.py` rebuilds the placement from the backup and the table in
`build/plan.py`; `build/finish.sh` imports a Freerouting session, closes the
leftovers with the grid router in `build/mini_route.py`, stitches ground and
runs DRC. The saved board passes DRC with schematic parity (0 errors, 0
unconnected); remaining warnings are short dangling stubs from the router.
The USB pair is routed single-ended at 0.15 mm (D+ 44.6 mm, D− 35.6 mm
total over their three-pin nets); review it before relying on the interface.

## Cable harnesses

`build_harnesses.py` generates the WireViz sources for everything that leaves
this board: the pack's factory JST SH 3P plug into J2, the J3 motor and
J5 tip pigtails, and a bench service cable on J4. It exports the native
netlist, checks each off-board pin against it and writes the sources, a
wire-stock worksheet and `logical-source.json` to
[hardware/cables/evt1/one-board/](../../../cables/evt1/one-board/README.md);
`--render` compiles them with WireViz 0.4.1 into `build/cables/export/` and
checks the child BOMs. Nominal wire paths come from `mech/internals-fit.json`.

## Reproduce the design checks

- Run `build_schematic.py` and export the native XML using the procedure in
  `verify_schematic.py`. The saved [ERC report](schematic-erc.json) and
  [source bindings](schematic-source-bindings.json) record the tool and inputs.
- `place_product_pcb.py` creates a placement seed from the active flange PCB
  and the FreeCAD placement report. It refuses to replace an existing board.
  `route_product_pcb.py` prepares a local Specctra exchange and imports the
  copper from a session without importing router placements.
- `build_order_parts.py` maps the native schematic to exact selected MPNs
  and separates the hand-installed targets and copper-only interfaces. Check
  availability against the intended JLCPCB quantity.
- `check_pack_monitor_pose.py` takes the saved one-board FreeCAD study and a
  report path. The checked sensor and tail geometry is recorded in
  [pack-monitor-pose-fit.json](pack-monitor-pose-fit.json).

The [JLCPCB review](../one-board-review/jlc-and-pack-temperature.md) covers
current availability, thickness, copper, plated holes and the pack bring-up
checks. The [bench PCB](../one-board-dev/README.md) has debug and isolation
interfaces for the same circuit. Complete layout and native copper checks
before packaging fabrication files.

## Routing checkpoint

The product board has a continuous In1 ground reference and ground pours on
In2 and B.Cu. A local 0.50 mm SYS crossover at the right regulator uses
In1. The [refilled ground comparison](in1-reference-review.json) checks the
USB return copper with that crossover installed. The routed MCU-side USB
legs are each 15.895 mm long on F.Cu,
with 0.15 mm track width and 0.20 mm minimum edge-to-edge spacing. The dock
contact route and its datums are preserved. Check the chosen impedance
stackup and installed USB behavior before relying on the interface. The
[USB geometry audit](usb-pair-review.json) records the route, ground coverage
and source binding.

The PCB uses compact U2 and U3 switch paths on B.Cu without vias, with local
high-frequency bypasses. U5 sits near the motor connector and its local
bypasses. The two motor outputs retain the short U5 pad escapes and use
0.40 mm tracks across B.Cu, F.Cu and In2.Cu.
The [current native DRC](routed-drc.json) records zero opens, rule findings,
ignored checks and schematic parity findings. The [pad audit](pcb-contract.json)
checks 356 logical assignments. The moved C1/C2/C3 charger capacitors have
local power and ground routes. C88 has a 5.14 mm B.Cu run to U7, and C61 is
closer to the ADC supply pin. The [prior revision's FreeCAD check](first-article-assembly-fit.json)
covered 9,432 rigid pairs with 68 populated transferred placements and three
installed connector mates. The [local fit check](resi-land-pattern-fit.json)
screens the revised R21, R43 and C43 poses against the saved flange geometry.
J3 now faces the neck and has moved 2.00 mm left and 0.30 mm toward the
neck in PCB coordinates. J8 also faces the neck and has moved 0.55 mm
inward and 2.05 mm to the right. R36 and R2 move to clear the connector
paths. The [connector routing audit](connector-reroute-review.json) binds
the new PCB, confirms the fixed contact and USB artwork, and compares its
In1 ground coverage along the USB routes against the previous quote board.
The revised connector positions clear a nominal 3 mm straight mating
sweep in the flange model. Verify both keyed plugs, four installed leads,
minimum bend radius, service slack and tool access on the received parts.
The existing Compact quote uses the prior PCB, so regenerate its fabrication
and assembly files from this source before sending a revised quote.

The first article fits C1–C3 at 4.7 µF and leaves C12 and C22 empty, for
44.7 µF nominal on SYS. The [selected BOM](assembly-parts-candidate.csv)
maps all 100 populated SMT positions. R21 and R43 use the vendor's recommended
1.40 × 1.65 mm pads on 2.60 mm centers ([RESI PTFR datasheet](https://s.resistor.today/shop/products/epdf/PTFR.pdf#page=2)).
Use the matching Gerbers and CPL when refreshing the JLCPCB quote. Confirm
CAM, exact allocation and orientation before ordering.
Keep JP1 open for initial
power and exercise the independent hardware guards and pack telemetry on
the simulator.

Run `python tools/export_evt1_one_board_fab.py product <new-output-directory>`
from the repository root with KiCad 10's CLI available to regenerate the
refilled CAM and assembly review files. Send the generated CAM request
with the bare-board ZIP and retain the native manifest for audit.
