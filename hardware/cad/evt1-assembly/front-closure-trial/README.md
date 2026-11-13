# Captured magnetic front closure trial

Two K&J D31 axial magnet pairs close across the shell split. Four magnets load
from inside and two shaped rear plugs capture them. Each rear plug also forms
the cream liner baffle, so the product gains two separate printed parts plus the
selected magnets and two screws. Normal opening removes no parts. Holding,
print/tap strength, magnetic interference and UV containment remain unqualified.

The visible cream grip keeps its 17×9 mm rounded silhouette, face Y−7.8 and
Z35.5–44.5. Its lower back is relieved to Y−6.6, leaving 1.2 mm material and
0.2 mm nominal clearance to the base catch. Catch cups occupy X±8.5,
Y−6.4..0.4, lower Z35.5..40 and upper Z40.3..44.5. A concealed lower central
thread boss reaches Z33.2 inside the existing dark front wall. Finish the grip
cream, upper shell orange and lower shell dark; a cream finishing zone can be
used on an integrated lid. The front USB opening stays below these features.

The D31 geometry is Ø4.7625×1.5875 mm, with the manufacturer's ±0.004 in
(0.1016 mm) tolerance. Native circles/Pads model the selected discs. Channels
are 5.05 mm wide and 1.8 mm high, with 0.8 mm plastic face walls. The shell's
0.3 mm split gives 1.9 mm between floor-seated magnet faces. The steel-plate
catalog pull value is not an installed holding-force rating. See
`source-manifest.json` for primary hardware links and dimensional assumptions.

## Native sources and integration

`FrontClosureTrial.FCStd` is closed; `FrontClosureReleased.FCStd` is a 2°
geometric opening reference. Both contain twelve editable Bodies under
`FrontClosureLower` and `FrontClosureUpper`: Housing, Retainer, Liner, Magnet1,
Magnet2 and RetainerScrew. The Liner and Housing wall seeds are exact read-only
BRep crops from the saved master. Crop boxes define test-piece boundaries;
they are not fit proxies. The master remains unchanged.

`FrontClosureParameters.OpeningAngle` moves the upper group about the real
hinge at Y164.4/Z40.15. The helper is
`tools/build_evt1_dock_front_closure.py`. Use `build(doc)` for the coupon. The
parent must remove the decorative LatchCover/obsolete seat and apply:

```python
add_catch(existing_shell_body, side="upper", prefix="FrontUpper")
add_catch(existing_base_body, side="lower", prefix="FrontLower")
add_liner_clearance(existing_upper_liner, side="upper")
add_liner_clearance(existing_lower_liner, side="lower")
```

Bodies must use the dock's global geometry with identity Body placement.
Named features include Cup, CreamGrip/LowerGripBackRelief, MagnetPockets,
SideLoadingChannels, RearM2TapPilot, ThroughSlot and UpperFinalSeatBay.
`build_retainer`, `build_magnet` and `build_screw` create the separate components
under their matching base/lid group. Do not import cropped coupon walls into
the master. The parent owns complete integration, colors, loading, UV seams and
release.

## Liner clearance and assembly

The lower liner needs a full-depth front slot through its floor and rim;
a shallow final notch cannot pass the integral catch during vertical loading.
Both liners use X±8.9/Y−2.5..0.8/Z10..58 loading relief. The upper liner also
has a local final-seat bay to Y6.4 at Z40.3..44.9 for its retained plug.

Install relieved liners **before** rear plugs, baffles and their screws. Lower
the base liner from above; lift the upper liner from below. Then insert the
magnet discs from +Y toward −Y with the rear plugs absent. Verify polarity first:
north toward dock +Z on all four discs gives attracting facing poles.

Insert each combined plug/baffle from +Y. The lower offset wall is
X±12/Y2.3..4.3/Z13.2..40. Its shaped toe clears the original side walls, stands
0.2 mm above the floor and overlaps the floor behind the slot by 3.5 mm. Side
wings overlap the slot by 3.1 mm. The upper baffle follows the sloping liner
front, offset 4 mm rearward, and ends at Z51.5. Its rear lip at
Y4.5..5.7/Z37..40.6 overlaps the lower baffle by 3 mm with 0.2 mm nominal gap.
The original rounded external grip is not credited as the UV baffle.

Use NBK SNSS-M2-6 on the lower plug and SNSS-M2-8 above. Their axes are
X0/Z34.8 and X0/Z42, pointing toward −Y. Head bearing planes are respectively
Y4.3 and Y6.0. Nominal thread engagements are 2.1 and 2.4 mm; Ø1.6 pilots
provide a further 1.2 mm candidate allowance for blind tapping/runout. This
allowance is not a qualified tap profile or approved installation torque.

The 1.5 mm hex driver approaches from +Y. Nominal Ø4.6×18 mm corridors start at
Y6.3 below and Y8 above. Fit and inspect these screws before the device/UV
hardware obstructs access. Complete received tool/shank/handle fit remains open.
No separate through-baffle driver hole is needed after the screws are installed.

Print/finish and clean with all side channels open. Remove MJF powder or wash,
drain and fully cure SLA channels before hardware installation. Qualify the
actual material, channel dimensions and tapping process on the coupon. Inspect
seating and verify poles before fitting magnets; do not force a press fit or
credit adhesive retention.

Measure actual front opening force with real magnets and final lid mass, then
set the storage/handling acceptance window. Repeat opening and transport/shake
trials; inspect magnet capture, screw loosening and cracked or stripped material.
Check the final dock's sensor behavior in the added magnetic field. The two
independent cutoff switches and measured dose/leakage validation remain separate.
The catch and geometric baffle overlap do not establish UV safety or sterilization.

`native-checks.json` records saved readback, coarse-mesh exact bounds, opening
pairs, OEM-maximum magnet loading, plug insertion, liner loading, driver approach
and thread-major overlaps. Six individual STEP files are derived coupon pieces,
with exchange precision recorded. No physical print, holding or powered result
follows from these checks.
