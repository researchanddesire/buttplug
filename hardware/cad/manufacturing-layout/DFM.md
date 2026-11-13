# Current turning DFM review

This is a review of the current candidate, not a supplier quote, CAM plan or
manufacturing approval. Dimensions are in mm. Battery, alloy and polymers remain open.

## Source application

| Reference actually checked | Applied to this design |
| --- | --- |
| [Protolabs turning guidelines](https://www.protolabs.com/services/cnc-machining/cnc-turning/design-guidelines/) | Separate turned features from offset drilling; do not hide material/service restrictions. Their published quick-turn service restricts off-axis holes to aluminum/brass, lists M2–M12 internal threads and excludes ID grooves. This M30 internally threaded design therefore needs a reviewed machining supplier/network route, not an assumed instant-service fit. |
| [Fictiv CNC guide](https://www.fictiv.com/articles/fictiv-cnc-machining-design-guide) | Provide chip/drill-point space, accessible profiles and ordinary tooling; avoid sharp internal transitions and thin unsupported clamping. General screw-engagement guidance is not a strength calculation for this large closure. |
| [HLH CNC guide](https://hlhrapid.com/wp-content/uploads/2022/07/CNC-Machining-Design-Guide.pdf) and [small-feature notes](https://www.hlhprototypes.com/design-tips-for-cnc-machining/) | Use a standard Ø2.5 sensor drill at5D cylindrical depth; make setup count and selective tolerances explicit. Their metal-wall guidance is a machining screen, not a body-load acceptance criterion. |
| [Sandvik turning application guide](https://www.sandvik.coromant.com/en-gb/tools/silent-tools/what-is-silent-tools/application-guide-silent-tools/turning-appl-guide) | Evaluate tool overhang against **bar diameter**, not bore diameter. Thread/groove operations need stiffer/shorter reach than ordinary boring. Actual holder, insert and chip evacuation are supplier decisions. |
| [Machinery's Handbook, publisher](https://books.industrialpress.com/9780831139322/machinerys-handbook-32-digital-edition/) | Relevant review areas: dimensioning/gaging, machining, fasteners, threads and machine elements. Publisher contents were accessible; its full technical tables/reader were not. No fit table, strength result or handbook compliance is claimed from inaccessible content. |
| [Festo SIED dimensions, p10](https://www.festo.com/media/catalog/205036_documentation.pdf) and [ifm E10028](https://www.ifm.com/gb/en/product/E10028) | Festo shows an M18×1, 24 AF, nominal 4 mm mounting nut. This supplies the compact envelope, not an assembly load rating or vendor CAD. ifm confirms a stainless M18×1 nut type; exact purchased geometry/material/fit remain to select and check. |
| [Apple Rubber seal guidance](https://www.applerubber.com/seal-design-guide/seal-types-and-gland-design/o-ring-installation/) | Account for squeeze/fill, tolerance and installation damage. A face seal avoids running a radially squeezed seal through several thread turns; final closure still rubs and requires a trial. |

Guide minima and service limits differ. They are not combined into a universal
“DFM passed” checkbox. No supplier is selected or contacted.

## Machining plan for supplier review

**Body, two-sided access:** rough from round bar with stock for gripping/parting.
Front-access operations are the Ø28 bore/conical transition, female closure
thread, ID runout and face gland. Reverse in supported soft workholding to
finish the rear shoulder, Ø20 collar blank, M18×1 stub/relief and Ø12 passage.
Mill two opposing collar flats in an indexed setup; the body is no longer purely
turned. Use the bore axis
and rear shoulder as inspection references; the supplier may change the setup
order. Do not clamp the Ø15/Ø12 neck as an unsupported thin tube.

**Cap, two-sided access:** turn the dome; reverse into a supported conformal nest
for the male spigot/thread, relief, rear counterbore and flat motor seat. Add one
parallel, offset sensor drill on a suitable live-tool machine or one indexed
secondary setup. Budget that secondary operation when material/machine requires
it. Preserve workholding allowance until critical bores/threads are finished.

**Reach screen:** the front mouth is Y64. The large-bore transition starts at
Y33 (31 mm reach), and its small end is Y26 (38 mm reach). A plausible allowance
of4 mm for the tool nose/approach gives42 mm overhang. A Ø12 steel bar is3.5D
for the large bore; the Ø12 throat needs a smaller head, provisionally an Ø8
carbide bar at5.25D. These are candidate envelopes, not selected holders/inserts.
Verify minimum cutting diameter and chip space; bore diameter alone is not the
bar diameter. Drill the neck passage from the rear and blend the intersection.
Female thread runout is10.5 mm below the mouth; cap Ø24.5 counterbore reaches
23.25 mm. The supplier must confirm these tools and workholding before CAM.

**Sensor access:** the hole's12.5 mm cylindrical cutting depth is5D, but the
counterbore adds23.25 mm of approach. Total rear-entry-to-drill-tip reach is
about36.2 mm. A concrete candidate is [Guhring6405, Ø2.5/4 mm shank/20 mm flute](https://guhring.com/Downloads/Item/9064050025000)
in a [Haimer77.160.04 extra-slim holder, Ø7 nose/3° taper](https://www.haimer.com/shop/catalog/downloads/files/Tool-holders/Tool-holders_US.pdf)
(page171). Proposed projection is25 mm. CAD checks a simplified holder taper
and drill at final depth against the cap; see the measured margin in `review.json`.
This is a tooling candidate, not a purchase or supplier-approved setup. Actual
grip depth, coolant delivery, spotting, fixture/live-holder and full swept path
must be confirmed. The counterbore was enlarged toØ24.5 to provide holder space.

## Functional features

| Feature | Current intent / inspection gate |
| --- | --- |
| Closure thread | M30×1.5, proposed6H/6g, standard available pitch; six mm nominal full male length/four pitches. Supplier confirms full effective engagement after chamfers/runout, gaging, stripping, galling and closing torque. No blanket bolt-length ratio is substituted. |
| Thread ends | Male lead-in plus Ø27.6×2.25 root relief; female Ø30.4×2.25 runout at its rear. These are explicit allowances, not a DIN76 compliance claim. Match tool radius/exit to the actual thread. |
| Nose gland | Candidate32×1 face ring; ID31.6/OD34.8, depth0.78. Metal faces set closure. Nominal22% squeeze and about63% cross-section fill; check final volume including corner radii, tolerances, swell and pressure direction. |
| Gland lands | Approximately0.8 inner ligament to entrance and0.86 outer ligament at the shoulder, before manufacturing/finish allowances. Protect these during polishing; inspect rather than infer them from a pretty section. |
| Motor seat | Ø11.1 nominal pocket, 15.3 mm cylindrical depth. Flat metal stop; actual motor case/edge radius, finished bore, seat corner relief, insertion force and retention remain an explicit hold. No approved interference tolerance. |
| Sensor drill | Ø2.5, 12.5 mm cylindrical depth plus140° drill point; offset7.8. Nominal1 mm web to motor bore. Current minimum distance to outside is measured in `review.json`; include drill wander, size/position and polishing before releasing remaining wall. |
| Root | Ø24 shoulder; Ø20 collar with 18.4 mm opposing flats and Ø12 passage. Collar length1.5; tray pad2; collar recessed0.5 from nut face. R0.3 root before flat cuts; flat terminations and socket entrance need supplier review. Boot land Ø19.5/upper shoulder Ø21 remain. |
| Rear thread/nut | M18×1 proposed6g/6H; stub6.25 shoulder-to-tip. Full male length3.5, lead0.5, relief0.75 at Ø16.4. Generic nut24 AF ×4, with Ø17 female pilot. Pilot/root envelopes contain no thread teeth; gaging, actual engagement, stripping/galling, material and torque OPEN. |

## Saved short-stub/thin-nut joint

The user selected this direction. Collar flats carry torque; the nut clamps
the tray pad against the metal shoulder. No socket adhesive or separate
compression limiter is credited. A drafted local nut well preserves the
88×32 mm outside but reduces local wall to about1.25 mm. Closure screw axes
move to X12; board seats/tabs to X−15.2. The unselected 33×8×20 pack reference
moves1.5 mm rearward, leaving nominal0.5 mm to the nut and0.25 mm to the stub.
These are CAD-only packaging changes, not a board/battery/molding release.

`review.json` records no hard-part overlap, a chamfer-aware all-angle nut
reservation at eight loading offsets, indexed body loading, and 24 angular
poses of a narrow axial two-jaw driver. Minimum nominal driver/tray distance
is about0.40 mm; the nut sweep/sidewall margin is about0.41 mm. Tightening is
before boards/pack/loom/cover. The driver is an unqualified envelope: ordinary
socket access, jaw stiffness, torque transfer and a physical trial remain open.
Key-blocking samples at ±3° and90° include an illustrative0.3 mm axial float;
that float is not an accepted creep allowance or a torsional strength result.

**Rear nut retention uses specified torque and Loctite on the metal threads.**
Keep the existing stack, with no locking washer. The grade, tightening torque
and cure schedule are not released. [Henkel Loctite 243](https://next.henkel-adhesives.com/us/en/products/industrial-adhesives/central-pdp.html/loctite-243/BP000000316211.html)
is a medium-strength trial candidate; Henkel's M10 steel breakaway result is
not a tightening torque for this M18×1 joint.

On inert assemblies, gauge the received thread engagement and tool fit. Use
the intended body/nut alloys and finishes and the actual printed tray
material/process. Establish the acceptable clamp-load window from the keyed
pad's load and creep tests; measure torque versus clamp load with the intended
threadlocker application, then confirm pad deformation and driver slip limits.
Record preparation, dose, cure time/temperature and keep excess off the plastic
and silicone bond surfaces. After cure and conditioning, measure breakaway
and retained clamp load separately. Also check collar bearing/key engagement
and nut/pad pull-through. Keep the threadlocker outside the sealing argument.

Torque the nut before installing the pack sensors. The unshifted nut clears
the sensor heads at the saved angle; the conservative sharp-corner envelope
across possible final angles overlaps both heads. Use the received nut and
torqued joint to check final-angle clearance across sample stacks. Do not back
off to align a flat. Review any sensor/loom relocation with the owner first.

The earlier KM3/MB3 screen and its source are preserved in
[`archive/ring-lock-screen/`](archive/ring-lock-screen/README.md). It applies
to the previous ring-joint native, not this revised assembly. Use
`tools/verify_manufacturing_layout.py OUTPUT` for the current study.

## Tolerances, assembly and finishing

Only functional dimensions should receive close tolerances. Proposed budgets,
**not approved drawing limits**, are:

- Collar Ø20±0.02/socket Ø20.2±0.05: diametrical clearance0.13–0.27.
  Collar flats18.4±0.03/socket flats18.6±0.05: across-flats clearance0.12–0.28.
  These are proposed machining/finished-socket budgets, not printer fit claims.
- Tray pad2±0.1/collar length1.5±0.05: collar setback0.35–0.65 before clamping.
  Nut bears on plastic. Preload/torque and post-creep capture are not qualified.
- Basic rear-thread root leaves nominal2.39 mm wall around the Ø12 passage;
  Ø16.4 relief leaves2.2 mm. These geometric walls are not load/fatigue ratings.
- Gland width1.6±0.05, depth0.78±0.02, assumed ring section1±0.08 and residual
  closure gap0–0.02: illustrative squeeze about11–30%, maximum simple fill
  about78% before the modeled R0.1 bottom corners. Actual purchased-ring tolerances/material and corner volumes control.
- Motor bore, thread pitch diameters, gland finish, collar/nut bearing faces and cuff-bond preparation
  need individual callouts/inspection. Do not apply loose cosmetic tolerances
  or a global mirror polish to them. Gage threads and fit the actual motor, nut and O-ring.

Deburr thread starts, bore intersections and wire passages. Ordinary bore
transitions include R0.4; face-gland bottom corners use R0.1. Collar flats,
thread relief, seal and motor-seat corners need functional callouts, not blanket rounding.
Polish/contact-finish and clean the assembled nose seam with critical dimensions
protected. Threadlocker does not replace the O-ring or prove a cleanable seam.

The factory root clamp needs torque/pull/bending tests, plastic bearing/creep,
key engagement and pull-through checks, cuff peel/leak tests and a real nut/driver
installation trial. Rigid loading/rotation/tool samples are finite screens.
Final overmold/tool, actual loom, metal weight, sensor thermal bias,
materials and human-use acceptance remain open. The current direction molds one
continuous skin over both closed plastic halves and the installed lower body;
separate [inert skin/split-tool CAD](overmold-trial/README.md) now exists with
three print STLs. Its solid closed-assembly dummy checks external fill/demold
only; final contact/button tooling, real cavity sealing and cap-last wiring
are unresolved. EVT workshop battery service consumes/remakes the continuous
skin; removal/recasting needs an inert trial. See the [overmold/cradle concept](concepts/overmold-cradle/README.md).
No physical trial exists.

The [separate dock/interface study](charging-dock/README.md) adds custom Ø4
spool-head contact targets, nominal M2 retention and a removable face-mask tool.
Those threads are root envelopes with callouts; target stock/finish, effective
engagement, nut locking, bearing/creep, pullout and metal/silicone sealing need
their own review. Stroke/position arithmetic is an unqualified inspection
budget, not supplier or printed-fit acceptance.

The contact study now models a separate inner face-seal trial: nominal2×0.5mm
NBR70 ring in an ID2.10/OD3.60/depth0.38mm metal gland. This0.75mm-wide face
groove leaves only0.20mm radial outer bearing land; confirm cutting-tool access,
edge integrity, Ra0.8µm finish and0.01mm local flatness before accepting a
machining quote. Ring inspection and machining budgets feed conditional
squeeze/fill arithmetic, not a seal-maker approval. The separate
[single-contact inert fixture](charging-dock/contact-seal-trial/README.md)
has two print STLs, post STEP/RFQ and a water-column procedure. NBR/casting
inhibition, preload/creep, received finish and real leaks remain unqualified;
printed rough counterfaces only check fit. Button and complete cavity seals
are still required before casting electronics/battery.

The plastic case/PCB posts have front-access drafted cores and closed webs,
avoiding tall solid columns. Both cores draw on the main mold axis. Short
threaded-stock regions, webs, root-pad transitions and resin still need a
molder review; proposed M2 closure screws have no qualified strip/creep rating.
