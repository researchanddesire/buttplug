# EVT1 interboard wire forms

`EVT1Loom.FCStd` contains ten interboard wire solids and centerlines between
the actual body J6 and neck-facing flange J7, with immutable copies of the
current product assembly. `review.json` binds the native, meshes, path code,
PCB MCAD and product sources; its `geometry_checks` field controls acceptance.
Wire forms are geometric references, not printable parts or finished cuts.

The flat row narrows and rotates into a vertical row inside the neck, turns
through a4.5mm bend, fans to J7's1mm pitch and uses an S bend ahead of the PCB.
The wire-center target1.4mm above the board mount face is a fixture allowance,
not an OEM egress tolerance. Reconcile it with received connectors and wire.
Keep120mm first-article starting blanks until terminal take-up, forming,
assembly and rework allowances have been qualified.

Twenty conductors must ultimately pass through the neck. These ten forms do
not qualify the compass, pack-power or four pack-NTC routes, complete flexible
loading, restraint, solder transitions, current/heat or physical fit. The seven
logical recipes under `hardware/cables/evt1/` are checked separately.

Wire STEP conversion is **withdrawn**: the saved comparison found a surface
mismatch despite near-equal volumes. The native FreeCAD model and closed view
meshes are the deliverables. `archive/Wire-STEP-Export-Study.zip` preserves the
failed comparison and exports; do not build or fabricate from them. The
mechanical product's separate checked STEP exports are unaffected.

The colliding away-facing study remains under `archive/away-facing-connector/`.
`neck-facing-j7-trial/` preserves the pre-route placement/geometry screen and
PCB acceptance evidence. Current builders consume the working PCB MCAD and
refuse the old connector orientation. No physical harness result exists.
