# Compass EVT1 device mechanics

Every part of the device around the compact 52 x 20 mm one-board lives here, one
FreeCAD script per part. Shared datums (device frame, flange outline, board
plane, hole positions, KiCad-to-device mapping) are in `compass_datums.py`.

| Part | Script | Origin |
| --- | --- | --- |
| `FlangeTray` | `flange_tray.py` | New, 56 x 32 mm around the compact board, plan corners R 8; body-side edge rounded over R 10 on the ends, blending to R 1.6 on the long sides, dock-side edge R 3 on the ends (continuing across the cover); shallow bowl cavity (floor at Y -16, walls vertical only down to the board's B.Cu face, then a 4 mm quarter-round into the floor) with a capsule-shaped trough along the +Z wall for the J3/J5 tails |
| `RearCover` | `rear_cover.py` | New, dock-side cover carrying the end of the flange's dock-side round-over; bores, counterbores and an inner guide boss for the button plungers |
| `ButtonPlunger` | `button_plunger.py` | New, rigid button sliding in the cover under the silicone, onto the B3U-1000P switches (one part, two per device; modelled at SW1, the assembly places the second at SW2) |
| `FlangeSkin` | `flange_skin.py` | New, silicone skin reference: straight walls from the dock face, then one lofted hull whose long sides and ends turn through two tangent arcs into the neck (no flat body-side face), dock-side edge rounded over R 4.3 on the ends and R 5 on the long sides, two low domes over the buttons and a raised arrow on the dock face pointing +Z, device up, for magnetometer calibration (not ordered) |
| `Internals` | `internals.py` | 3-wire pack with built-in NTC (EEMB LP502030-PCM-NTC-LD class), motor, tip NTC and all wires from the board's connectors; envelopes from the body pack trial (not ordered) |
| `MetalBody` | `metal_body.py` | The DFM study body (`hardware/cad/manufacturing-layout/MetalBody.step`, unchanged there) with the 2026-11-18 shoulder: the neck flares from Y 8, tangent, through the sketched waypoints and rejoins the bulb at Y 42 with matching tangent and curvature; the bore's O12 to O28 transition follows the new outside at a 2.2 mm radial wall (study: short cone at Y 26..33). `body-profile.json` tabulates old and new radii and the internals' gaps |
| `MotorThermistorCap`, `ThinRearNut` | none | Copies of the turned-metal DFM study in `hardware/cad/manufacturing-layout/`; unchanged, alloy still open |
| `compass-one-board.step` | KiCad export | `kicad-cli pcb export step --subst-models --no-dnp` of the board |
| `compass-device` | `device_assembly.py` | Full assembly; `-open` leaves the skin and cover off; `-cutaway` halves the enclosure at Z = 0 to show the internals |

Device frame: Y is the body axis (+Y to the tip), Z up, X across the flange; the dock face
faces -Y. The board maps as X = kx - 100, Z = 100 - ky with its F.Cu face at Y -21.

Buttons: each plunger goes in from the cover's inner side before the cover is screwed on.
Its 6.6 mm flange seats in a 0.5 mm counterbore on the inner face (the switch spring holds it
there, so its position while the skin is cast is defined), its 5.0 mm head slides in the 5.4 mm
bore and stands 0.4 mm proud of the cover under 0.9 mm of silicone plus a 0.5 mm dome, and its
nose rests 0.1 mm above the switch actuator: 0.25 mm of finger travel to the click, the flange
still 0.46 mm clear of the switch body when pressed. Nothing of the mechanism opens to the
outside but the head, so the cast silicone can only wick into the 0.2 mm bore gap (it does not
bond to PA12 without primer, so keep primer off the cover within 2 mm of the bores). The 0.2 mm
radial clearance is for MJF; ream the bore if a plunger binds.

Rebuild (order matters: body, tray, cover, plunger, skin, internals, assembly):

```
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/metal_body.py
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/flange_tray.py
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/rear_cover.py
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/button_plunger.py
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/flange_skin.py
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/internals.py
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/device_assembly.py
```

Body-side round-over (2026-11-18): the tray's front edge is R 10 on the X ends and R 1.6 on the long sides
(the nut well and the cavity walls leave no room there), blended round the plan corners by a loft. The skin
over it is a single hull whose profiles are two tangent arcs per direction (`SKIN_SIDE_ARC`, `SKIN_END_ARC`
in the datums: a convex arc off the side wall running into a concave arc that lands on the neck; the concave
radius and the wall height follow), so its long sides and ends turn into the neck ramp in one gentle curve;
it keeps 1.3 mm over the O21 ring and at least 1.6 mm over the tray. To give that
round-over wall, the board cavity's floor moved from Y -9.6 to -16.0 (1.0 over J4), its plan corners
are R 7 (0.36 to the board's R 2 corners) and the nut well still reaches Y -10.

Bowl cavity (2026-11-18, Lucy: "it doesn't need flat sidewalls"): the cavity walls are vertical only
from the cover seat down to the board's B.Cu face (Y -20), then roll into the floor as one R 4 quarter-round
all the way round (`CAVITY_BOWL_R`); the board still slides in past the corner ledges. The plan cannot get
rounder: the 52 mm board's R 2 corners allow at most R 8 plan corners in the 56 mm flange, and the nut
well needs the full 28.8 mm in the middle. The J3/J5 tails leave their plugs toward +Z and loop over to
the neck above the bowl, so a capsule-shaped trough along the +Z wall (`WIRE_TROUGH`: cylinder X 3..20.6
with spherical ends, centre Y -17.8 / Z 10, r 4.4, tangent to the Z wall, top at Y -13.4) replaces the old
square pocket. Thinnest wall between the cavity and the outside is now the full 1.6 mm (was 1.37 behind
the end round-over).

Dock-side edge (2026-11-18, Lucy: the square edge where the back face meets the end wall is "way too hard,
should be like a 20 mm fillet"): the closed flange's envelope (`capped_slab2`) is now rounded over at both ends,
and the tray and cover are the two sides of the cut at the cover seat (Y -23). The dock side cannot take a
large radius with this board in this flange: the board slides in through the 52.8 mm rear opening and its
corner sits 2 mm inside the end wall and 3.6 mm under the cover face, so the hard parts get R 3 on the ends
(`DOCK_END_R`; cover seat 1.25 wide there) and only R 0.8 on the long sides, where the M2 screw heads reach
Z 15 (`DOCK_SIDE_R`). The silicone is concentric and carries the visible edge: R 4.3 on the ends, R 5 on the
long sides (`SKIN_DOCK_END_R`, `SKIN_DOCK_SIDE_R`; the arrow moved down to Z 4.5..14.5 to stay on the flat).
Plan corners went from R 6 to R 8, the most the board's R 2 corners allow in 56 x 32 (the skin's follow at R 12).
Anything rounder needs a longer flange or a board with bigger corner radii: R 10 plan corners need the board's
corners at R 4 (MH3 still fits), stadium ends (R 16) need a 62 mm flange, and a dock-side round-over of R 6 on
the ends needs 60 mm.

Connector plugs: `internals.py` models the mated JST SH crimp plugs as envelopes at the wire ends: SHR-02V-S
on J3 (motor) and J5 (tip NTC) and SHR-03V-S on J2 (the pack's factory plug), each standing 3 mm out of its
side-entry header toward +Z into the tray's wire trough. J5 was a vertical BM02B until 2026-11-20; its plug cut
into the tray and its leads could not reach the bore, so it became an SM02B like J3. `device-fit.json` checks a
straight 3 mm withdrawal for J2, J3, J4 and J5.

C30 recess (2026-11-20): C30, the 47 uF 1210 on F.Cu, stands 2.5 mm, more than the 2.0 mm cover gap allows. The
cover has a 0.9 mm deep recess over it (`C30_RECESS`, 0.3 mm clear all round, 0.7 mm web left).

Arrow (2026-11-20, Lucy): the raised arrow on the dock face now points -X, toward the flange end nearest the
buttons, which is "up" for the user (X -5..5, Z 7.3..11.7). Firmware magnetometer calibration must use that axis.

Logs go to `build/mech/`; `device-fit.json` records hard-part overlaps, connector
withdrawal, the buttons at full travel (must clear the cover and touch only their switch) and the clearances that matter; `internals-fit.json` records the internals
against the metal, tray and board, and wire crossings. Re-export the board STEP after any layout change.
