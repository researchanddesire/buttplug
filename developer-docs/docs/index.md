# Buttplug Compass

Start with the [active hardware source list](hardware.md) or the
[manufacturing design proposal](prototype-build-handoff.md). The device has
four main mechanical pieces: turned body with indexed collar flats, turned
motor/thermistor cap, flange tray and rear plastic half. Both flange halves
close before the continuous silicone overmold. Contact and button sealing
and the molding process still need qualification.

| Page | Use it for |
| --- | --- |
| [Design proposal](prototype-build-handoff.md) | Current structure, assembly and unresolved interfaces |
| [Requirements](prd.md) | Lucy's feature and packaging constraints |
| [Architecture](architecture.md) | Mechanical, power and signal paths |
| [Hardware](hardware.md) | Current native CAD, exports and electrical references |
| [Thermal study](thermal-presence-study.md) | Modeled sensor warm-up, metal comparison and presence-detection limits |
| [Firmware](firmware.md) | EVT1 and legacy profiles, build and compatibility |
| [EVT1 electrical](evt1-electrical.md) | Four-contact circuit, thermistor, compass and USB recovery |
| [Bulb battery and one-board EVT](one-board.md) | Device PCB, bench board, pack telemetry and fabrication checks |
| [Validation](testing.md) | Evidence, limits and required next checks |

The previous P1 dry-fit kit is withdrawn as the recommended build. The metal CAD remains
a manufacturing study. All five EVT1 PCBs now pass native DRC and pad/netlist
parity. A separate actual-board assembly native adds the flange-fixed compass
mount and passes nominal loading/clearance checks. Thermistor/compass firmware
and hardware wake/recovery are implemented candidates. The complete orderable
product, accepted pack/retention, loom, rear nut torque and threadlocker
qualification, and final button/seal tooling remain unfinished.
Exact PCB parts and assembly quote ZIPs plus a protected-pack RFQ are prepared.
No physical build, powered operation or wear validation exists.

The next device revision keeps the existing body PCB and combines contacts,
Power/Mode switches and compass sensing on one flange PCB, with the battery
beneath it. Its selected-part placement/native candidate and matching
skin/barrier/dock studies are separate from the earlier routed fabrication kit;
see [hardware sources](hardware.md). The merged39-part routing now passes native
DRC/ERC/pad parity. Full integration, local case telemetry and the order kit
remain unfinished.

The current assembly revision must use editable FreeCAD component bodies,
StepUp-linked PCB models and selected-part geometry. The dock must match the
orange/cream pocket-toy concept with a working screen, three buttons and
UV-C cleaning LEDs. MJF/SLA plastics and multiaxis CNC/cast metal are the
manufacturing targets. The saved fit kits precede this expanded dock revision.

[Archived studies](archive/index.md) are for targeted historical lookup.
Update these current pages in place; use Git history rather than revision logs.
