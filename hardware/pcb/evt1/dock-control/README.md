# Dock controller and lid UI — EVT candidate

Open `dock-control.kicad_sch` for the two-sheet native circuit. The source,
hardware safety and UV circuits are sibling folders; the merged review circuit
is in `../dock-system/`. These files are not fabrication artwork.

- STM32L071CBT6: all 48 physical pins, internal 4.2 MHz MSI, SWD/BOOT recovery,
  hardware reset/watchdog interfaces, analog NTC inputs and ADS1115 monitors.
- Newhaven NHD-C12864B2Z-RN-FBW: actual 27-pin 8080 interface and charge-pump
  circuit, write-only `/RD`, twelve source resistors, internal contrast commands.
- Three Omron B3FS-1002P switches. CENTER goes to the independent safety
  debouncer; the MCU reads its output and cannot create the hardware start edge.
- Hirose FH12-20S-0.5SH(55) hinge sockets and Molex 0151660220 opposite-face
  ultra-flex cable. UV power uses its separate harness, not this 20-way cable.
- Molex 52437-2771 LCD socket is an **EVT mating-trial selection**. The LCD's
  exposed/stiffened tail lengths differ from the socket recommendation.

`pin-contract.json` binds physical MCU/LCD/connector pins and signal roles.
`parts-selection.json` lists selected positions and source links; it does not
replace the human-owned product BOM. `native-checks.json` binds native ERC and
exported terminal checks to source hashes. Standalone lid ERC has two visible
external-supply context findings; the two-sheet hierarchy has zero errors and
warnings without exclusions. Full dock integration and powered tests remain open.

## Placement sources

`dock-controller-placement.kicad_pcb` is only the 44-reference controller subset
on a **shared** source/controller/safety base outline. It reserves the source
zone at Y0..25 and the safety zone X15..45/Y30..60. Source and safety components
must be placed on this same board; do not stack three complete boards. Two
8×8 mm contact-carrier openings contain a full 7×7 mm clear square, with 0.5 mm
corner chamfers. The front USB nose and final mounting/port details remain DFM work.

`dock-lid-placement.kicad_pcb` places 28 references with the switches at dock
X−22/0/+22, Y54. A native keepout protects the central flex return corridor.
J302's X/Y position is a candidate pad-row location, **not the LCD tip** or a
solved connector mate. The board's installed Z is deliberately unresolved.
Both candidates have zero tracks/vias and remain unrouted.

Native saved-board checks cover 274 physical pad instances. Native KiCad 10.0.8
placement DRC reports zero geometry/library violations, with 99 base and 80 lid
unconnected groups expected before routing. This is not a completed DRC or
fabrication release. The independent firmware folder has a separate PCB audit.

## Coordinate and connector conventions

The native board frame is `dockX = pcbX − 100`, `dockY = 200 − pcbY`.
For StepUp `pcb_placement=2`, the outline-centred MCAD frame is right handed:
F.Cu is local Z0, B.Cu Z−1, and MCAD Y already reflects KiCad's down-page Y.
The rigid FreeCAD placement is an identity rotation plus the translations in
each `*-placement.json`: base `(0,32,6.4)`; lid `(0,84.5,Z_UNRESOLVED)`.
The actual import must be checked against these datums before assembly fit.

- J302 at native 0°: mouth dock−Y, pin1 dock−X. The installed LCD's fold about
  X preserves pin1 at−X; **LCD pin p connects directly to socket pad p**.
  Manufacturer SD-52437-019 Rev F top view and mounting-side land pattern,
  plus an independent audit, support this mapping. No 180° Z rotation applies.
- J201/J301 at native 180°: both mouths dock+Y and both pin1 sides dock+X.
  The intended opposite-face cable route preserves conductor p→p. Actual
  closed/open routing, continuity and hinge life remain to be tested.

The installed LCD tip centre is `(0,112.575222039,61.85)`; its actual contact
face is Z61.70, normal−Z. Copper spans Z61.70..61.80, flex Z61.80..61.90 and
stiffener Z61.90..62.00. Molex's sectional reference dimensions show 3 mm
insertion depth and 1.7 mm from the **inserted tip** to the contact point.
The drawing's 0.82 mm exterior side-feature datum is not a qualified contact
plane. No socket height or insertion mate is inferred from it. Manufacturer
STEP retrieval failed; J302 has no substitute box model and remains an explicit
missing 3D reference. Its contact height, actual seating and tail compatibility
need manufacturer geometry/acceptance or a received-parts trial before power.

## Rebuild and check

Use ordinary Python for `build_source.py`, then `check_native.py --kicad-cli
PATH_TO_KICAD10`. Exports/ERC run sequentially. Source construction refreshes
the native circuit and local selected footprint/model snapshots.

Use KiCad7's bundled Python with `wx.App(False)` for each placement operation:

```sh
python build_placement.py controller
python build_placement.py lid
python check_placement.py controller
python check_placement.py lid
```

Run one board per process. `--restart-placement` permits replacement only of
this builder's unchanged, unrouted candidate; preserve edited/routed work first.
`check_models.py` runs in FreeCAD Python and checks native BRep validity and
exact bounds after coarse tessellation. The nine local library STEP models
describe actual standard external cases, terminals and actuators, not component
maximum-tolerance proofs. `model-provenance.json` and the local KiCad license
record their origins. No physical fit, USB/programming, UV output, dose,
cleaning efficacy, thermal/leakage result or full-product order release follows.
