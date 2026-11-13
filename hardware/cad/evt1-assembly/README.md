# Native EVT dock assembly

Open `DockAssembly.FCStd` in FreeCAD 1.1.4. Keep the adjacent `pcb/` and
`sources/` folders beside it: these are real external assembly links. The
working revision is authored as Sketcher/PartDesign bodies, native assembly
components and a revolute hinge. No STL is the authoring source.

This is an integration candidate, **not an order/print or powered UV release**.
The accepted single-flange-board revision keeps the body PCB and now has a
separate selected-part native at
`../manufacturing-layout/evt1-integration/contact-module-trial/single-board/SingleFlangeBoardTrial.FCStd`.
Its39 package models and66 sampled populated-board/cover loading poses pass
nominal checks. This saved dock master still uses the earlier contact row;
the recentered carrier and new exterior source are being integrated separately.
Its earlier print/interface files are not the build kit for that new revision.
The current builder installs the recentered carrier, matching nine-part
exterior and shifted body seat. The isolated revision 051 rebuild and loading
checks completed. The LCD/socket overlap remains in the saved static check,
including the three UI stack offsets. See [revision 051](review-051/README.md)
for both views and the result. The saved master above is preserved.
Rebuilt candidates use `Motion.OpeningAngle`; the older saved master still
uses the spreadsheet driver described below. Source files before this change
are preserved under `archive/pre-single-flange-builder-7eb82305/`.
The new source/controller/safety/UV circuit integration is in
`hardware/pcb/evt1/dock-system/`, with its source projects beside it. The two
routed PCB models in this assembly are the earlier USB/interface boards;
they do not contain the new controller and complete UV safety circuit.

## Assembly structure

- `ComponentDesigns`: editable lofts, pads, pockets and selected component
  geometry; source bodies are hidden while their assembly instances are shown.
- `DockAssembly`: linked base/lid modules, grounded base and native rear hinge.
- `Parameters`: case profiles and hinge reference. Change `OpeningAngle`
  (cell B10) from 0 to 110 degrees to inspect the clamshell. The whole-placement
  expression keeps the hinge axis stable through repeated opening/closing.
- `pcb/DockUSB.FCStd` and `pcb/PinPCB.FCStd`: real StepUp imports of the
  existing routed KiCad boards. The USB import includes its socket and nine
  component positions; selected nominal package models replace the old boxes.
- `sources/ReadableEVT1Product.FCStd`: geometry-preserving working copy of the
  existing product source. Only its actual body, cap, continuous silicone skin
  and four target posts are linked into this dock. Its old electronics/pack fit
  proxies are not dock assembly components. The original source stays unchanged.

The source working copy omits the legacy hand-authored GUI XML that crashed
FreeCAD's GUI reader. Its document data and BRep geometry are preserved. The
new dock and StepUp files use FreeCAD-generated GUI data.

## Selected components and interfaces

The exterior follows the orange upper shell, dark lower shell, scalloped cream
bezel, blue controls and cream chamber of the pocket-toy concept. Plastics
target MJF/SLA; this revision does not impose FDM print constraints. Metal
parts may use multiaxis CNC turning/milling or a separately developed casting
process. Actual materials, tolerances, supports and finishing remain to qualify.

The Newhaven `NHD-C12864B2Z-RN-FBW` is a real reflective 128×64 LCD. Its native
bodies reconstruct the manufacturer model, with the current active-area
dimensions. The installed 65 mm FFC has a native sweep, stiffener and 27 lands;
its 3 mm bend radius is an **unqualified candidate**. The ribbon has actual
relief in both the lid and bezel. The current 2.1 mm maximum glass stack,
compliant seat, bottom-contact connector and cable restraint still need final
integration. See `vendor/display/`.

Four Mill-Max `0906-2-15-20-75-14-11-0` contacts use native revolved barrel/tail
and plunger bodies, not full-height cylinders. Nominal compression is 0.6 mm;
the manufacturer's nominal travel is 1.397 mm. Insulating annular carrier stops
touch the **metal target faces** at Y23.2. Silicone is not the contact load datum.
See `vendor/pogo/` for primary drawing dimensions and the model's limits.

The real pin board uses a right-handed frame: StepUp local `(x,y,z)` maps to
`(x−28, 18.7962+z, 41.8−y)`. This puts the rear J94 wire lands at **Z45.3**,
so the native carrier/retainer recess and wire window follow that location.
The earlier envelope drawing's Z41.7 wire location was mirrored. Pogo tails
have individual clearance bores. Mount the carrier from the underside;
the selected Accu SIK-M3-12-A2 screws are dimensioned native reconstructions,
with their head rims and cones represented. Resin taps, torque and received
hardware still need trials. Installed wiring/strain relief remain open.

The cream lower chamber has full-depth rear slots so it can pass the integral
hinge webs during installation. Four Accu SIK-M2-6-A2 screws fasten its floor
to integral lower-shell bosses. Their native profiles retain the head rim;
the holes include separate rim clearance and a90-degree countersink. See
`vendor/fasteners/selection.json` for manufacturer dimensions and omissions.
Thread-major cylinders intentionally overlap the tapped pilots only; the
saved-native verifier checks that no allowed overlap escapes those volumes.
Install the USB/contact module, liner and its screws, then UV modules and
device. UV module mounts, metal backing and installed wiring must still be
added and the sequence rechecked.

Four Vishay UV packages are linked from their manufacturer STEP at candidate
base/lid sites. This is real package geometry, **not a completed UV module**.
Metal heatspreaders/opaque backing, UV-compatible chamber surfaces, boards,
thermal joints, hardware lid cutoffs and thermostat actuators remain to integrate.
Manufacturer family-model differences are recorded in `vendor/uv/source.json`.
No irradiance, dose, cleaning efficacy or sterilization is claimed.

The selected Omron `B3FS-1002P` tactile-switch source is in `vendor/buttons/`.
The blue caps do not yet have their final retained travel/stops or switch-board
mounts; pretravel is not a maximum permitted overtravel specification.

## Rebuild and evidence

Use the existing UTM Linux FreeCAD VM. Work on its local disk; the shared 9p
folder returned transient file-lock errors during this revision. Copy complete
verified files back after saving. Do not overwrite the earlier source natives.

`tools/import_evt1_stepup.py` imports the two KiCad boards using the installed
StepUp workbench and the attributed local package STEP files. Close the assembly
before regenerating its PCB documents. `tools/build_evt1_native_dock.py` builds
the component bodies and native assembly in FreeCAD GUI. Source/vendor models
and the PCB natives must be present first. `tools/verify_evt1_native_dock.py`
reopens the saved native, checks link/hinge references, edits/restores a real
sketch dimension and tests assembled BRep intersections at six lid poses.
`tools/verify_evt1_dock_loading.py` checks66 sampled liner positions,49 device
loading/mating positions and four axial liner-driver reservations. These are
nominal sampled poses, not continuous swept-volume or tolerance/strength tests.

Read `review.json` for build scope, `native-check.json` for saved32-body/1,435-pair
results and `loading-check.json` for the119 loading/access poses. Cold reopen
after moving all four linked native documents passes in `portable-check.json`.
A source build, valid solid or native fit check does not establish
received-part fit, process strength, seals, USB operation or UV safety.
