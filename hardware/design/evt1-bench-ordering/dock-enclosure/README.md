# Compass EVT1 dock enclosure quote

Quote one set of the custom enclosure parts listed in `parts.csv`.
The three blue button caps have separate files. Each STEP is one solid
in its saved body frame, in millimetres. The source and STEP readback checks
are in `geometry-check.json`. Review fit and report any process-driven
geometry change before fabrication.

Price the liners from the saved geometry. Final liner fabrication depends on
the installed moving UV wires, their liner passages and retainers. Keep the
two liners separate on the quote so the remaining enclosure pieces can be
quoted independently.

## Additive parts

Price MJF PA12 as the baseline. List tough SLA separately with the exact
resin, post-cure, finish, dimensional tolerances and temperature limits.
Use dark for the lower shell, orange for the lid, cream for both liners and
the display bezel, and blue for the three caps. Quote opaque latch baffles.
State the substrate and finish for each color so the same material stack
can be checked for UV transmission and aging. Match the color references in
`dock-reference.png` after physical samples are approved. Keep coatings off
seats, guides, thread pilots and connector stops. Return room-temperature
inspection results before installing electronics.

- Inspect the lower liner's J401 pocket. It is 12.10 × 6.10 mm with R0.40
  corners, 1.30 mm nominal depth and 0.70 mm nominal wall to the chamber.
  Report the achievable wall thickness, warpage and pocket-depth tolerance.
- Inspect the two blind Hall clearances in the lower liner. Each pocket
  profile is 9.50 × 16.70 mm and removes 0.50 mm from the local shoulder.
  CAD shows a 0.48 mm solid web beneath the checked cut section. Return
  achievable pocket depth, remaining web thickness and warpage before
  printing. Preserve the blind floors and report any proposed process change.
- Quote the two keyed Hall PCB brackets in nonmagnetic plastic. Inspect the
  two Ø2.20 mm holes on 6.50 mm centers, the 1.50 mm upright and the
  1.65 mm PCB ledge. Each bracket has an integral 2.20 mm wide lip with
  0.75 mm nominal PCB overlap and a 0.90 mm slot for the 0.80 mm PCB.
  Report achievable slot height, lip thickness and cleanup for the
  undercut, as well as both PCB and shell seating surfaces.
- Gauge the display-flex passages in both liners against their assembled
  datums. Keep the edges smooth. Protect the scalloped bezel's LCD seats
  and the button sliding faces during finishing.
- Keep the shell hinge bores and screw pilots accessible. Confirm their as-built
  size and cleanup. Retain the shell seam return geometry and both lower
  and upper front latch baffles. Remove all loose powder or uncured resin.
- Inspect the pin carrier and its raised insulating stops against the four
  contact faces. Avoid tumbling or heavy paint where they seat. Check that
  the rear retainer closes and leaves room for the soldered wires.

[HP MJF design guidance](https://www.hp.com/us-en/printers/3d-printers/learning-center/how-to-design-3d-print-model.html) · [Formlabs SLA process guidance](https://formlabs.com/global/blog/minimum-wall-thickness-3d-printing/)

## Machined parts

Price `hinge-pin.step` separately in stainless steel. The turn is Ø3 mm ×
72.8 mm under the Ø5.2 × 1.0 mm head. Finish the opposite end with a blind
M2 × 0.4 tap and at least 4.3 mm full thread. The STEP includes a Ø1.60 mm
pilot. Confirm available tap runout, check the received hinge bore size and
report axial retention fit before cutting.

Source one NBK **SNSS-M2-4** screw and one PTS **A12502A** plain axial
retaining washer per hinge. The screw is M2 × 0.4 × 4 mm under the head.
The washer is Ø2.20 mm ID, Ø4.70–5.00 mm OD and 0.25–0.35 mm thick.
The 0.30 mm modeled washer leaves 3.70 mm gross insertion. Verify that the
screw seats on the washer without bottoming and that the eyes rotate freely.
[NBK screw](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/socketheadcapscrew/SNSS/) ·
[PTS washer](https://www.pts-uk.com/products/washers/form-a-flat-washers/metric-a2/A12502A)

Price two `uv-spreader-6061.step` and two
`uv-thermostat-pressure-bar-6061.step` parts in 6061-T6. Each file is in the
base mounting frame. The lid uses the same geometry in a rotated installation.
Inspect the nominal 1.40 mm sensor-bay web, stepped arms, rear bridge, LED
islands, V saddles and both bearing surfaces. Deburr and round LED island
edges R0.20 and quote Ra ≤1.6 µm on the island faces. Return machining,
flatness and cutter radius limits. Keep relief cutter radii ≤0.25 mm, or call
out any deviation for review. Quote the modeled thermostat-bar fixing pilot
as a finished M2 × 0.4 thread. Confirm usable engagement and remaining web
with the actual bar, screw and thermostat tab before cutting. Check that
the bar's modeled screw clearance and contact face stay intact.

Price both Hall magnet carriers and backers in unfilled PEEK or equivalent
nonmagnetic polymer. The carriers have a Ø1.20 mm loading bore, Ø0.70 mm
sensor-facing opening and 0.25 mm nominal capture shoulder. Gauge these
features and the Ø1.60 mm M2 tap pilot. Leave the backers at nominal blank
length for fitting to the received magnets and studs. Quote four Hall
bracket screw spacers at Ø2.60 OD × Ø2.10 ID × 3.20 mm in unfilled PEEK.
Use the existing magnet seats in the case. Confirm the finished carrier
shoulder and axial retention before closing the lid.

This packet covers the saved product enclosure pieces. Source it with the
current EVT ordering guide for the electronics, magnets, springs,
thermal pads and fasteners. Verify Hall PCB and magnet retention, moving
harness guides and finished liner wall on the received parts.
Assemble with the UV emitters isolated until independent lid-open and
thermal shutoff are verified. Inspect finished assembled units for UV-C
leakage at the seam, ports and hinge.
