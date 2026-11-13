# Dock seam overlap trial

This editable FreeCAD trial adds an integral base upstand, a matching lid relief and two front return walls. The front returns work with the captured-magnet catch and its offset baffles. Small additions to the liners and the existing lower plug preserve installation without adding separate print parts.

The trial uses exact saved shell, liner and hinge-pin BReps plus the frozen front-closure source. It is a nominal geometric trial, with no UV containment, optical attenuation, cleaning, material-opacity, strength or received-fit qualification. Print tolerance, warpage, holding force, interlock response, leakage, reflections and thermal performance still require physical tests.

Native geometry checks pass: 66 liner insertion poses, 34 plug insertion poses, two driver corridors and nine opening poses with no cross-module overlap findings. The raw finite ray sweep tested 129,808 segments and retains **14 clear exterior lines** from three front-vestibule origins at X−10/0/+10, Y2, Z40.15. `ray-source-regions.json` preserves all 14 and shows exact rear-baffle intersections when those origins are probed toward the chamber. This explains their source region and does not establish all-rays containment. Measured optical leakage remains open.

## Native source and integration

`UVSeamTrial.FCStd` is the complete closed trial; `UVSeamOpening2deg.FCStd` shows the same parts at 2°. Each of its 13 components is a Body. The new features use fully constrained native sketches and Pads/Pockets. The upper module rotates around the existing X-axis hinge at Y164.4/Z40.15. A document-level parameter object is referenced with `App::PropertyLinkGlobal`.

In a fresh master build, after creating the frozen front catch and its liner slots:

```python
import build_evt1_dock_uv_labyrinth as seam
features = seam.add_labyrinth(lower_shell_body, upper_shell_body, prefix='UVSeam')
front_entries = seam.add_liner_entry_relief(upper_liner_body, prefix='UVSeam')
loading_slots = seam.add_lower_liner_loading_slots(lower_liner_body, prefix='UVSeam')
slot_baffles = seam.add_lower_slot_baffles(lower_captive_plug_body, prefix='UVSeam')
```

All input Bodies must have identity Body placements and use closed dock XYZ. They may belong to the existing moving App::Part modules. All four calls are required. They append features once and neither open nor save a source document.

The first call returns `base_upstand`, `base_return_cheeks` and `lid_entry_relief`. Named features use the prefix plus `BaseUpstand`, `BaseReturnCheeks`, `LidEntryRelief`, `UpperLinerEntryRelief`, `UpperLinerWebLoadingRelief`, `LowerLinerLoadingSlots`, `LowerSlotWallWings`, `LowerSlotCheekClearances` and `LowerSlotFloorWings`. The upper-liner function adds both the front entries and rear-web loading relief; its return value is the front-entry Pocket. The lower-plug function returns its wall/floor wing Pads and cheek-clearance Pocket.

`build(doc, name='UVSeam', master_path=...)` creates this independent trial without changing its master. The root links to `Lower`, `Upper`, `Parameters` and the named features.

## Nominal geometry

All values are millimetres. Rounded rectangles share centre Y77.5 unless stated otherwise.

| Feature | Nominal geometry |
| --- | --- |
| Base upstand | Outer127.5×162.5/R48.75; inner125.5×160.5/R47.75; Z40..43. Radial wall1.0. |
| Front interruption | X±9.5 where Y<0.8. |
| Lid entry relief |128.1×163.1/R49.05, Z40.2..43.4; exclude X±9.2 where Y<6.5. Radial/axial allowance0.3/0.4. Minimum nominal outside wall about0.95. |
| Base return cheeks | X−13.5..−12.5 and12.5..13.5; Y−3.75..10; Z39.6..43. Clear the original24mm baffle by0.5 per side. |
| Upper front entries | X−13.8..−12.2 and12.2..13.8; Y−4.05..10.3; Z40.2..43.3. Nominal cheek allowance0.3. |
| Lower loading slots | Same XY as upper entries; through the complete lower liner. |
| Lower plug wall wings | Extend to X±15.5; Y2.3..4.3; Z13.2..39.8. |
| Lower plug cheek pockets | Mirrored X12.0..13.8; Y2.0..4.6; open-top cuts down toZ39.3. The returns overlap the original central baffle vertically by0.4. |
| Lower plug floor wings | Z13.2..14.4; rear edge Y12.3, giving2.0 overlap beyond the slots. Narrow front tongues have0.1 nominal side gaps; floor allowance0.2; local cheek-pocket allowance0.3. |
| Upper rear-web notch |27.8×10.6/R0.4 at centre Y159.4, Z40.4..47.2. Intact tapered wall resumes0.3166 forward of the web. |

The lid relief cuts the forward hinge-web underside. The native checks require both modified shells to remain valid single solids. No hinge stiffness or minimum printable-wall acceptance is inferred.

The return cheeks block a demonstrated diagonal ray that passed the original ring interruption, 17mm grip and 24mm rear baffle. Integral cheeks also obstruct vertical lower-liner installation, so the through-slots are necessary. The existing lower captive plug receives wings to cover those slots afterward. The upper rear-web notch is extended because its original top46.2 allowed interference during liner insertion.

Install slotted liners first, then magnets and the combined captive plugs/baffles, then the preassembled contact module. The master owner must check later hardware and whole-product loading. The new floor-wing rear edge Y12.3 is1.7 ahead of the parent's new carrier collars at Y14; those new collars are not present in this source snapshot.

## Checks and derived sectors

`native-checks.json` binds the master, frozen closure files, builder, manifest, natives and exports by SHA256. Checks include exact BRep bounds after coarse tessellation, single-solid validity, changed-region intersections, liner/plug loading, driver corridors, nine opening poses and saved-native readback.

The closed ray screen assumes every included solid is perfectly opaque. It uses a0.02mm derived mesh with segment/triangle BVH acceleration and rechecks every apparent clear segment against exact BRep. Six mirrored/height-shifted front rays must be clear without the returns and blocked with them. Four shallow3D controls additionally reproduce the rejected reference and must block in the corrected model. An original side-seam control and48 other sampled segments are compared against exact BRep. Each sampled source-to-aperture direction continues500mm beyond its aperture, preserving steep slopes. Targets include the rim gap and free hinge-eye annulus/bore samples. This finite search is not an all-rays proof and does not model reflection or transmission.

The six `side-*`, `front-*` and `hinge-*-shell.step` files are exact cropped shell sectors for inert print trials. Cropping boxes define test boundaries only. Front shell sectors omit the separate baffles: use the updated lower plug/liner Bodies from this native and the upper plug from the frozen closure. The original lower plug lacks the new wings.

STEP checks use1e−5mm boundary and1e−7mm³ symmetric BRep-difference tolerances. A2ppm mass-property tolerance accommodates a measured1.414ppm integration difference in the curved hinge-sector loft; its symmetric BRep difference was zero and maximum sampled boundary error6e−7mm. The editable native remains the source of truth.

`rejected/UVSeamShallowGapRejected.FCStd` is retained only to reproduce the shallow-ray regression. It is a rejected reference, excluded from build candidates. The main check verifies its hash and actual clear segments before confirming that the corrected native blocks them.
