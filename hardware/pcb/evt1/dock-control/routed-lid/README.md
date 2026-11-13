# Routed lid UI candidate

`dock-lid-routed.kicad_pcb` is the four-layer, 1 mm native lid PCB candidate.
It preserves the frozen circuit, 28 electrical references, 109 physical pad
instances, the three button centres, both socket centres/orientations and the
original flex keepout. The audited placement source in the parent folder stays
unchanged. Four additional mechanical footprints provide Ø2.3 mm NPTH mounting
holes at dock (−30,65), (30,65), (−32,115), (32,105), with R3 hardware reservations.

The local LCD bias bypasses, flying-capacitor loops, shared C1− return,
reservoir, VDD bypasses and button terminal straps are explicit authored copper.
`local-copper.json` records all 109 source objects; the final audit requires
every one to remain unchanged. Other connections used the pinned official
FreeRouting 1.9.0 offline tool with analytics disabled. In1.Cu remains the ground
reference plane; signal routing uses F.Cu, In2.Cu and B.Cu.

`native-checks.json` binds the PCB, project rules, native schematic XML,
libraries, route tooling and exchange artifacts to their hashes. The checker
requires native KiCad10 DRC with **zero violations and zero unconnected items**,
all checks enabled, no ignored checks and no DRC exclusions. It separately checks
actual pad/net parity, fixed controls/socket XY, flex keepout, mounting holes,
hardware-to-pad clearances and exact authored-copper preservation. The design
uses 0.15 mm minimum tracks, 0.10 mm clearance and Ø0.45/0.20 mm through vias;
the final supplier stackup/process remains to be accepted.

The eleven capacitors are on B.Cu. The selected TDK 1206 cases are 1.6±0.2 mm
high: reserve **1.95 mm below B.Cu** for case maximum plus a provisional 0.15 mm
assembly allowance. TDK 0603 cases are 0.8±0.1 mm; Murata 0402 is 0.5±0.05 mm.
`route-floorplan.json` records each location, actual side, manufacturer height
source and mounted allowance. These allowances require native assembly and
received-parts checks; nominal library models do not prove maximum-case fit.

J302 now uses the two exact Molex OEM solids, rigidly posed to the closed outer
envelope and registered to the real land-row datum. Its model is already in
physical board XYZ and uses identity KiCad offset/rotation. The front courtyard
has 0.25 mm margin to that closed envelope. `lcd-socket-model-binding.json`
binds this metadata change to the prior saved routed board; pads, copper,
placements and flex reservations remain unchanged. `lcd-socket-native-pose.json`
checks the actual KiCad10 component-only STEP export against both full OEM
solids and all 27 terminal centres. The original manufacturer CAD and native
shim trial are under `hardware/cad/evt1-assembly/vendor/lcd-socket/`.

The installed PCB has an adjustable trial starting position, but the loaded
contact-plane/tail mate remains unqualified. This routed board therefore remains
outside a full-product fabrication or powered-function release. USB/programming,
physical assembly, UV output, temperature, leakage and cleaning efficacy have
not been demonstrated by this digital routing result.

To verify, run `../check_routed_lid.py --kicad-cli PATH_TO_KICAD10` with KiCad7's
bundled Python. Native `wx.App(False)` is needed. The checker is read-only with
respect to the PCB/project and overwrites only its reports. Route construction
uses `../route_lid.py`: seed, authored local copper, fill, DSN export, offline
session import, explicit escape repair, final fill/ledger and final native rule
configuration. `first-pass.ses`, the final DSN/SES and the exact source ledger
remain available for review; `native-finalization.json` records the final
submicrometre track-to-via centring correction. Never overwrite edited routing
or the audited placement while rebuilding.
