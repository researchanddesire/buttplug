# Compass EVT1 integrated device board

Open [compass-one-board.kicad_pro](compass-one-board.kicad_pro) in KiCad. The
schematic derives from the routed EVT1 body and single-flange projects. It
replaces J6/J7 and the old compass interconnect with local nets, and fits the
charger, motor driver, sensors, ESP32, controls and four dock contacts on one
82 × 26 mm board. See [schematic-checks.json](schematic-checks.json) for the
retained terminal and hardware charge-gate checks.

The bulb pack uses the two independent hardware NTCs and a third dry NTC that
reports pouch temperature. J8 pin 1 is PACK_MON_NTC and pin 2 is GND. R88 and C88
condition the signal for U7 AIN2. The `evt1-one-board` firmware uses the two
AIN1 reference conversions around each AIN2 reading. It reports the pack
temperature separately from tip temperature. JP1 starts open for bench testing.

The four contacts carry GND, D−, D+ and 5 V from either the dock or the
direct PC contact fixture. The compact board uses one device USB path. The
fixtures are mutually exclusive at the plug; completely withdraw one before
attaching the other. The [evaluation guide](../../../design/evt1-bench-ordering/master-bench-eval/README.md)
defines recovery, source-change and contact acceptance tests. The catalog
substitutions retain the four dock contact datums and their USB routes.

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
