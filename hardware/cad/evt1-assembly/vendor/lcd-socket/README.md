# Selected LCD socket and trial mounts

`Molex524372771OEMOpen.FCStd` contains the two exact manufacturer STEP solids,
including all 27 contact profiles. `Molex524372771ClosedEnvelope.FCStd` moves the
same slider 1.6 mm to the drawing's closed outer envelope. The original STEP is
unchanged. The slider pose is an editable native expression; new native features
can follow the imported Body base features. No bounding-box model is used.

The model came from the Farnell CAD archive linked by Newark's selected-part
page. Source URLs, hashes, drawing pages and limitations are recorded in
`source-manifest.json`. The CAD is dated 2013; the referenced drawing is Rev F,
released in 2018. Received-part matching remains necessary.

## Integration

Run `tools/build_evt1_dock_lcd_socket.py` in FreeCAD, or import it and call:

```python
socket = build(doc, name="DockLCDSocket", pose="closed_envelope")
socket.Placement.Base = App.Vector(0, 114, pcb_front_z)
shims = build_trial_shims(doc, stack_mm=1.0, roof_seat_z_mm=61.5)
```

The socket's local origin is the J302 signal-land-row centre, with pin 1 at
X−6.5, pin 27 at X+6.5, mouth toward −Y and height along +Z. The exact source
transform is `X=sX; Y=−sZ−0.6; Z=sY`. The 0.6 mm offset comes from the Rev F
page-2 land length (0.8/2) plus the 0.2 mm housing gap. The OEM H plane is local
Z0, while nominal solder tails extend to Z−0.04. Solder thickness and published
coplanarity tolerances are not hidden in the placement.

Native object names are `DockLCDSocket`, `DockLCDSocketHousingContacts`, and
`DockLCDSocketActuator`. Its separate `DockLCDSocketParameters.ActuatorSlide`
controls the rigid pose from 0 to 1.6 mm. The closed pose has 0.00407 mm³ of
internal common volume: manufacturer spring deflection is absent, so this pose
establishes an outer envelope, not a collision-free loaded connector.

`Molex524372771ClosedBoardFrame.step` exports those same two solids for identity
offset/rotation in the derived routed J302 footprint. `bind_routed_model.py`
preserves an exact pre-attachment native snapshot and compares all native tokens
except the model and front courtyard margin. `check_kicad_pose.py` compares both
full actual KiCad10-exported solids and 27 terminal faces against the OEM shapes.
KiCad10's exporter uses a separate software datum: its board body is Z0–0.91,
then 0.035 mm outer copper plus the hardcoded 0.05 mm `BOARD_OFFSET` place the
model H plane at Z0.995. That software offset is not a chosen physical solder
height. See [KiCad's exporter source](https://gitlab.com/kicad/code/kicad/-/raw/10.0.8/pcbnew/exporters/step/step_pcb_model.cpp)
(`getBoardBodyZPlacement`, `getModelLocation`). The parent must verify actual
StepUp component datums after importing into its board-front reference frame.

## Insertion evidence and remaining mating datum

The installed FPC tip is Y112.575222039; J302's land row is Y114 and the closed
OEM outer front is Y108.9. The fixed tip is therefore 3.675222 mm behind the
closed front, 0.675222 mm deeper than the drawing's reference 3 mm insertion.
It remains 0.324778 mm before the model's rear intercontact walls. Those walls
are geometry references, not a qualified cable stop.

Both actual terminal-arc rows lie inside the modeled exposed copper length.
At the minimum 2.8 mm Newhaven land length, the smaller axial coverlay margin
is 0.270778 mm. `geometry-datums.json` records the measured faces, normals and
calculation. This proves longitudinal overlap only. The Newhaven 3±0.2 mm
exposed land and 5±1 mm stiffener differ from Molex's recommended 4±0.5 and
6±0.5 mm. The fixed insertion depth, latch action and all 27 contact paths need
a received-part trial.

**No loaded copper contact height is assigned.** The OEM model is open. In
particular, actuator face 62 at source Y0.905 faces downward and is not a cable
support floor. The measured terminal arcs, housing guide lands and rigid closed
pose do not provide a unique loaded contact plane. Unmodeled spring deflection
is not credited as engagement or clearance.

## Equal-shim trial

`LCDSocketTrialShims.FCStd` has four fully constrained annular Sketch/Pad bodies:
`LCDSocketTrialShims301` through `LCDSocketTrialShims304`, at dock coordinates
(−30,65), (30,65), (−32,115), (32,105). Each is OD5.2/ID2.3 mm. The root is
`LCDSocketTrialShims`; its separate Parameters object controls all four equal
stacks together. Stacks of 0.5–1.5 mm under fixed roof seats Z61.5 give PCB front
Z61.0–60.0. The initial 1.0 mm stack gives Z60.5 solely as a fixture starting
position. The parent assembly owns roof bosses, NBK SNSS-M2-6 screws, access and
local recesses. Its actual endpoint collision checks must qualify this range.

Use measured insulating shim stock, in equal increments at all four holes;
do not bend the PCB with unequal stacks. With power disconnected and the
actuator open, support the natural FPC path, measure the actual soldered socket
and choose the equal stack that avoids forcing the flex. Record the PCB-front
height and shim thickness. Confirm latch action, insertion witness, all 27
continuity paths and neighboring shorts before energizing. Do not cycle through
every candidate height: the socket's stated mating life is limited. If a neutral
fit falls outside the fixture range, revise the mount rather than preload the
glass, FPC or connector. Keep button caps removable until the final height and
switch actuation are measured.

Native validity, exact bounds after coarse tessellation, 27 terminal locations,
saved-document readback and shim parameter edits are recorded in
`native-checks.json`. These are digital geometry checks, not received fit,
optical/cleaning validation or a build release.
