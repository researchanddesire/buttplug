# Selected rear nut and service-tool trial

This separate editable native selects **ifm E10028** as the stock-nut candidate
for the saved M18x1 rear joint. It does not modify the metal body, flange,
electronics, human-owned BOM or current product native. The retention direction
is a qualified tightening torque and Loctite on the metal threads.

The manufacturer drawing specifies 24 mm across flats, 4 mm thickness,
M18x1 and stainless 316Ti/1.4571, supplied in packs of two. It also labels
27 mm across corners without specifying tolerances or corner construction.
The reconstruction retains the full regular 24 AF hex corner span of 27.713 mm
for clearance. It takes no clearance credit for that unresolved 27 mm value,
chamfers or thread flanks. Obtain and gauge actual nuts before fixing thread
fit, tightening torque, preload, material pairing or final driver dimensions.

Sources: [ifm product page](https://www.ifm.com/gb/en/product/E10028),
[manufacturer-authored drawing mirror](https://selectumllc.com/attachments/ifm/E10028-datasheet.pdf).
The downloaded drawing is preserved unchanged in `vendor/ifm-E10028.pdf`.

## Native files

`RearJointServiceTrial.FCStd` has two authoring component Bodies and three
immutable context snapshots. Nut and tool use fully constrained native sketches,
Pads and Pockets. STEP files are derived from those Bodies. The current flange
context has the same rigid Tray geometry as the frozen pre-mate-clearance study;
later U71/U75 moves do not change that Tray.

The custom **TwoJawDriver** reaches opposite nut flats through the open Tray.
Its two 18.6 mm arms have 2.5 mm tangential width, a 24.25 mm opening and a
28.2 mm outer circular limit. The rear hub stays behind the Tray. Align to the
opposed flat pair within 30 degrees of product X, then insert axially. The
0.4 mm tip setback from the bare nut front is retained in this saved tool trial.
There is no locking washer in the build direction. The 10 AF shank needs a
separate workshop drive.

Use the tool **before the rear half, electronics, pack and loom**. Enter the
body/Tray joint, tighten with an independently qualified torque procedure,
remove the tool, and only then load those parts. The native loading study checks
143 aligned tool poses and 61 nut orientations against actual body/Tray geometry.
It does not establish continuous clearance, received-part fit or usable torque.

This is a machined-steel tool proposal, not a print release. Root fillets,
edge breaks, material/heat treatment, manufacturing tolerances, jaw flex,
engagement/slip and torque calibration require an inert trial. Do not apply an
invented clamp torque based on the nominal CAD result. Locking, plastic creep,
key engagement and pull-through remain separate joint checks.

## Evidence

`review.json` binds nominal checks to the exact native and builder. The cold
readback report checks valid Bodies, constrained sketches and STEP parity.
`selection.json` records manufacturer provenance and unresolved dimensions.
The two failed wider-driver studies are preserved in `archive/`; their loading
findings drove the narrow two-jaw design. They are not build parts.

Rebuild with `tools/build_evt1_rear_joint_trial.py` in FreeCAD Python. Its source
guards intentionally require the archived, frozen context. Revalidate explicitly
when changing that context. There is no physical or full-product order release.
