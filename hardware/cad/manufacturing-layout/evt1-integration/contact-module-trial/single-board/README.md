# Single flange PCB — inert mechanical candidate

The existing body PCB stays. One enlarged flange PCB carries the existing flange circuitry, Power/Mode switches, compass parts and four purchased fixed targets. Four individually nutted posts and the flange-to-contact/sensor looms are superseded in this study. Existing device PCB fabrication sources and the product/dock masters are unchanged.

This is a placement and inert casting/load coupon, not a complete fabrication or powered release. The new routed PCB candidate passes native DRC with zero violations/unconnected items; this remains a mechanical and casting candidate, not a complete fabrication release. Requested pack, RF performance, magnet holding, compass interference, shoulder bearing, silicone force, cure, sealing and molding remain unqualified.

## Concrete stack

- Product axes: the board F plane faces rearward, along −Y. StepUp Cartesian local X→product X, local Y→product Z, local +Z→product −Y, a proper Rx+90 rigid transform. KiCad's screen Y-down is a separate convention.
- PCB F/B = Y−26.952/−25.952, 1 mm finished thickness. Actual board outline/holes and selected models are bound from `hardware/pcb/evt1/single-flange-routing/mcad.json`; the earlier editable contour is retained as hidden construction.
- Rigid rear-cover front/inside planes = Y−28.7/−27.2, leaving 0.248 mm between the front board face and the cover. The rigid 88×32 mm XZ section and original body/neck/stub stay. The new rear extent is 3.2 mm beyond the old keeper-boss extreme; it is 4.2 mm beyond the old flat cover plate.
- Final skin rear datum = Y−29.7; four target faces nominally Y−30.0, 0.3 mm proud. A revised, source-derived continuous skin includes the original root and intended aperture fill around the permanent insert. Its closed dry cavity is design intent, not a casting result.
- Requested pack growth bounds remain X6.75..40.25, Y−22.6..−15.2, Z±10.75. There is 3.352 mm from board B to that growth allowance. A 2.95 mm part would leave 0.402 mm nominal; actual model checks determine which parts are over the pack. J7's wire/mate projection also needs installed-loom checks.
- Board mounts: (X,Z) = (−30,−10), (−38,+10), (+38,−10), (+38,+10). Four NBK SPA-M1.4-2-MC3 screws install from the open dry side into integral cover seats. Positive seats set the gap; torque, thread strip, creep and received PCB bearing are not assumed.
- Existing M2 case axes (12,±13) have R2 open PCB-edge reliefs. Longer case fasteners/head clearance for the deeper cover are still a parent integration task.

## Contacts and loading

Selected targets are Mill-Max **1946-0-00-15-00-00-03-0**, four purchased through-hole fixed targets. They have a nominal Ø3.175 flat head, 3.048 mm above-board height, Ø2.54 base shoulder and Ø0.762×2.794 mm solder tail. The manufacturer specifies a nominal Ø0.8636 mounting hole; the study's Ø3.2 copper land is a project proposal, not a manufacturer land recommendation. See `selected-parts.json` and the [primary catalog, printed223.1/PDF28](https://www.mill-max.com/sites/default/files/external/catalog/2020-01/202-246_3.pdf).

Generic published length/diameter/angle tolerances are ±0.127 mm, ±0.0508 mm and ±2°. The nominal face proud value is therefore not a received-stack guarantee. Finished cover apertures are proposed at Ø3.70..3.80, giving at least about0.076 mm radial clearance with maximum head diameter, maximum above-board length at2° and0.05 mm lateral offset. Actual part perpendicularity, PCB hole size, soldering fixture and finished aperture fit must be received and measured; nominal PTH clearance is not an all-tolerance assembly proof.

The targets are soldered to the PCB as one assembly. Their base shoulders must bear on the local board lands. Integral Tray posts support the laminate directly behind each land, with a bore clearing the full solder tail. The intended axial load path is target shoulder → local laminate compression → plastic post → Tray, with **no solder strength or PCB bending credit**. A solder stand-off or unsupported shoulder breaks that assumption. Do not level unequal target heights by floating their shoulders on solder and then claim bearing support.

Install the permanent soft insert over the target heads on the bench, then load the whole PCB/targets/insert assembly from the dry side toward −Y into the rear cover. The heads pass through the enlarged apertures. Install the four board screws, connect the body/pack loom while open, then close both rigid halves. The head faces, support flatness, board mounting and case closure need an inert received-part/load trial before live assembly.

The contact row is X−16/−10/−4/+2, Z10, ordered GND / D− / D+ / 5V. In the dock, translation (0,53.2,32) restores faceY23.2 and puts the row atZ42. A separate recentered-carrier study moves its upper contact board; it preserves the old feet/main-PCB interface. Proposed stops are OD2.4/ID1.8, only0.1 mm raised from a broad face atY23.1. The old OD3 stops have inadequate margin on Ø3.175 targets.

## Permanent molding barrier and buttons

A **single pre-cured silicone insert** combines two closed button cups and four contact-neck sleeves. Its common flange is captured between the PCB and cover: nominal free thickness0.30 mm, nominal captured gap0.248 mm. This is geometric capture, not a calculated clamp force or seal pressure. The insert remains installed when both rigid halves close and the final continuous skin is molded over them.

- Trial material is Smooth-On **Dragon Skin20**, a primary-documented platinum-cure20A silicone, selected only for an **inert** coupon. Published tensile/elongation data do not qualify working strain, biocompatibility of this assembly, UV aging, cure against the printed parts, metal compatibility or the staged silicone bond. [Primary technical bulletin](https://www.smooth-on.com/tb/files/DRAGON_SKIN_SERIES_TB.pdf).
- Two closed0.4 mm cup faces cover the selected Omron B3U-1000P switches. Cup cavities4.4×3.1 mm clear the complete4.0 mm nominal SMT-lead span as well as the3×2.5 mm case. Outer cups are5.2×3.9 mm, with5.4×4.1 mm cover openings. Their dry faces atY−28.85 give0.298 mm nominal plunger gap and0.148 mm at the maximum1.75 mm switch height. No loose rigid plungers are added.
- Power/Mode centres are (−17,0)/(−9,0). Final-skin crowns have R2.5, frontY−29.8: in the dock their frontY23.4 is0.3 mm behind the proposed broad carrier face. The separate carrier study must check rest,0..0.7 mm pressed keepouts and the +3Y loading path against actual shapes. That sweep is **not an allowable switch stroke**.
- Omron pretravel0.15(+0.20/−0.12) mm is not a maximum overtravel rating. The silicone force/displacement curve and a qualified overload stop remain open. Measure bare-switch, insert-only and final-overmold force curves on an unpowered coupon before committing a populated board. No elastic modulus or protective finger load is inferred.
- Four proposed sleeve boresØ1.60 wrap the Ø1.7018 target necks. Stretching over Ø3.175 heads entails about98% diameter increase. The modeled neck interference is intentional and unvalidated; tear, installation damage, compression and leakage require the inert coupon. The common perimeter flange alone does **not** seal the four metal boundaries.
- Two native insert-tool halves are provided as an inert cavity/core candidate. They separate along Y; the open-neck cores withdraw+Y and the outside half−Y. Tool registration/clamping, vent/fill tuning, print compatibility and received thickness still need workshop qualification. The final four-face mask withdraws−Y before lateral opening of the main skin mold.

Closed cups and neck sleeves supply explicit bulk-flow barriers. Neither their nominal BRep contact nor the modeled final skin proves a water seal or a pressure-tight molding cavity. Do not cast live electronics or a battery until a complete inert closed-module casting/leak/cure trial passes.

## RF, keepers and current evidence

The actual selected ESP32-C3-MINI-1-N4X has an integrated antenna; no external coax feed is invented. The board has an open host edge beneath it. The keepers move+24X/−3.2Y to (−14.5,−8)/(+3,−10.5) in XZ. Matching dock magnets move+24X separately from the contact row. The nominal nearest horizontal antenna-to-keeper edge gap is17.1 mm. This geometric separation is not RF, holding-force or compass validation; nearby required decoupling, all copper/materials, the final loom and measured calibration remain part of qualification.

`review.json` records exact nominal BRep checks and sampled assembly poses. `cold-readback.json` independently reopens saved bodies and reads the actual STEP BReps. File existence alone is not model coverage: an earlier empty target STEP was caught, replaced by a recomputed Tip-shape export and independently cold checked. `native-sections.png` is generated from the saved native geometry for chat/phone review. `artifact-bindings.json` binds the final candidate sources and outputs; no source board/master/BOM is edited here.

The final routed-candidate integration moves only U75 to(X6.3,Z9) and U71 to(X−1,Z−7) for the selected SH10 mate. The original39-position mechanical source and exact reports are preserved under `archive/frozen-39-pre-mate-clearance/`. All39 actual models, native package pairs and33 loading/33 closing poses were rechecked after the change. The portable nine-body exterior remains byte-identical; the separate J7/pack loom studies contain mating, wire and remaining flexible-assembly checks.
