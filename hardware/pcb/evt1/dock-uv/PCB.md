# Routed local UV boards

The editable native boards are base/pcb/dock-uv-base.kicad_pcb and
lid/pcb/dock-uv-lid.kicad_pcb. Both independently pass native KiCad10.0.8 DRC
with zero violations and zero unconnected items. Each has24 source-bound
onboard positions,61 checked physical pads and four2.2mm NPTH mounting holes.
Their complete369 route objects and selected placements match after explicit
BASE/LID reference/net renaming. The original SW/COMP/feedback copper is
independently checked against its saved intentional layout.

Each board is a U: X−49..49,Y86..135mm, side arms outsideX±35 untilY128,
with1mm internal milling radii. Holes are(±45,89),(±45,132), each with both-side
3mm hardware clearance. LEDs stay at(±42,94) onF.Cu; the driver,passives and
rearward side-entry SM08B-GHS-TB connector are onB.Cu. Long traces around the
U carry DC LED-string/monitor signals. The switching node remains a short
local triangle. COMP and current feedback are locally authored first.

The nominal stack is1mm copper-plus-core:0.86mmFR4,70µmCu each side, ENIG,
with10µm mask coatings additional. Supplier stackup/etch/plating/stencil
acceptance remains open. The local PCB supply/return target is<=20mΩ hot,
including necks and vias; this has not been measured. Native pours reinforce
the power trunk and2.4mm return strap. The input-cap feed was shortened from
8.975mm/0.4mm to2.225mm/0.6mm. Complete source/connector/crimp/wire limits and
the4.25V driver floor are in ../dock-safety/power-budget.json. The copper
target is an acceptance requirement, not a guaranteed resistance result.

Each LED's two electrical lands connect to separate terminal-net pours and
six thermal stitches. They are never assigned to ground. B-side contact
regions near each emitter are recorded in assembly-models.json. A common
metal backing requires a qualified insulating thermal interface; soldermask
alone is not credited. Local cutouts must clear the back-side parts and the
remote sensors must follow the actual hottest heatspreader/driver region.
The FR4 assembly does not inherit the datasheet's Al-MCPCB thermal rating.
Backing geometry, pad selection, attachment pressure, sensor lag and opacity
are integration/physical-test work.

Actual source geometry is linked: OEM10-solid Vishay LED, selected KiCad
package models and a native3-body Bourns drawing reconstruction. Sources,
limits and cosmetic reconstruction choices live in models/source-manifest.json.
No generic rectangular fit component replaces a selected part. The C1210
model is nominal2.5mm high; selected capacitor maximum2.8mm still controls
clearance. Remote NTC and67L045 are wire-mounted, not fictitious PCB packages.

Each pcb/mcad.json binds the native PCB and exported STEP and records measured
planes. Standalone CLI STEP uses planar X/Y directly, coreZ0..0.86,
F.CuZ0.93 and B.CuZ−0.07; package mounting includes0.05mm solder standoff.
Its LED terminals startZ0.98 and optical topZ2.755. **Do not apply a centered
StepUp transform directly to this uncentered STEP.** Root integration uses
centered StepUpFplane0: base identity translatedY110.5/Z13.2; lid properRy180
translatedY110.5/Z55.3. That flipsX andZ, preservesY and intentionally exchanges
left/right LED references. Actual saved-native StepUp readback controls fit.

pcb-checks.json,pcb-identity.json,mcad.json and native-drc.json provide scoped
digital evidence. fabrication-review/ contains exact selected-part/placement
and Gerber/drill review artifacts for these two boards only. Nothing has been
ordered, flashed, powered or optically validated. Complete dock fabrication
release still requires integrated native CAD/loom, source-path measurements,
capacitance/loop tests, cutoff/thermal/optical/cleaning qualification and
supplier acceptance.

Verification uses KiCad's bundled Python for check_pcbs.py base/lid (each
invokes live native10.0.8 DRC and checks the saved board hash). Run
check_identity.py with ordinary Python, and check_exports.py with FreeCAD's
Python. Authoring order is build_pcbs.py place, route_pcbs.py critical,
local router session/import, bounded native-DRC repairs, fill, model/profile
finalization and the checks. Existing edited/routed boards are never replaced
by the placement command; preserve them before restarting. The installed
native GUI libraries require the approved process outside the sandbox.
