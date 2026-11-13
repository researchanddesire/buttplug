# Two-piece CNC metal / flange joint study

Open `ManufacturingLayout.FCStd`. Four custom rigid pieces remain: turned
`MetalBody.step`, turned `MotorThermistorCap.step`, `FlangeTray.step` and
`RearCover.step`. `ThinRearNut.step` is an additional generic hardware envelope.
The planned continuous silicone overmold, O-ring, fasteners,
insulation, foam and bonding materials are additional. This is **not a
manufacturing release**. No supplier, alloy, polymer or battery is selected.

## Metal machining intent

| Part | Operations and access |
| --- | --- |
| Body | Turn the outer profile/15 mm neck, rear shoulder, collar blank and short M18×1 stub. Mill two indexed collar flats. Bore the nose Ø28, with a conical transition to the Ø12 neck bore. Nose thread and face-seal gland open from the front; no bulb-shaped internal undercut. |
| Nose cap | Turn the rounded outside and male thread. Rear Ø24.5 counterbore exposes a flat-ended nominal Ø11.1 motor pocket and its metal stop. One offset Ø2.5 blind sensor drill is a **live-tool operation**, not pure two-axis turning. |

The cap seam moves to Y64; the external rounded silhouette is retained. The
cap's old deep annular chamber/keyway is removed. The sensor drill is offset
7.8 mm, with 12.5 mm cylindrical depth and a modeled 140° point. Its nominal
web to the motor bore is 1 mm. Thermistor sensing is now near the nose flank,
not on the exact apex; thermal response and motor bias need measurement.

**Thread callout:** provisional M30×1.5, body female/cap male, approximately
6 mm full male engagement (four pitches). CAD shows female Ø28.5 pilot / male basic Ø28.1597 root envelopes,
not thread teeth. Do not machine those envelopes as finished threads. Proposed fit is6H/6g. Lead-ins and2.25 mm runout/root-relief spaces are modeled;
confirm effective engagement, root radii, gaging, strength and torque with the machinist.

**Nose seal:** candidate 32×1 mm face O-ring; body gland ID31.6/OD34.8,
depth0.78 mm. Nominal cross-section squeeze22%, fill63%. These are starting
calculations, not tolerance analysis. The 0.8 mm inner land to the thread entrance, gland corner radii, elastomer swelling and assembly rubbing need review.
Metal shoulders set closure, independently of the seal and threadlocker.

Use the Ø12 bore as axis datum and rear shoulder Y−8 as axial datum. Plan
front/rear setups with soft jaws and explicit stock allowance; no invisible
one-setup claim. Supplier selects workholding and tooling. Polish contact
surfaces while protecting threads, seal lands and dimensions. Do not promise
that polishing makes the nose joint crevice-free.

## Rear metal-to-flange joint

- **Axial retention:** a short M18×1 stub and 24 AF ×4 mm thin-nut envelope
  clamp the tray's 2 mm root pad against the Ø24 shoulder. Shoulder-to-tip
  length is 6.25 mm. The Ø20 collar ends 0.5 mm short of the nut face so the
  nut bears on plastic. No separate compression limiter is selected.
- **Thread:** proposed 6g/6H, 3.5 mm full male length plus 0.5 mm tip lead and
  0.75 mm root relief. Male basic-root/female-pilot geometry has no thread
  teeth. Confirm actual nut dimensions, full engagement, gaging, strength and
  torque before machining; the generic nut is not manufacturer CAD.
- **Torque resistance:** two opposing 18.4 mm collar flats fit the matching
  Ø20.2/18.6 AF tray socket. No socket adhesive is credited. Collar-flat
  machining is additional to turning. Nut locking remains OPEN; a metal-keyed
  tab washer is still only a candidate. Creep, key bearing/engagement after
  preload loss, nut retention and plastic pull-through need separate tests.
- **Wet-side termination:** turned recessed Ø19.5 bond land, Y−7…−3. A silicone
  cuff overlaps it and meets the Ø21 upper shoulder flush. The modeled cuff
  includes its flare to the tray face. It is only the skin's root section;
  separate full-skin/split-tool CAD now exists for an inert trial. Final
  button/contact seals and tool/bond process are open.
- Tighten before PCB/pack/loom/cover installation. A narrow axial two-jaw
  driver reservation clears in sampled poses; normal socket access is not
  assumed. Actual tool stiffness, engagement and torque require a trial.
  The flange stays 88×32 mm; a local drafted nut well leaves about 1.25 mm wall.
  Screw/board posts and PCB tabs move; the pack reference shifts 1.5 mm rearward.
  Actual battery, board and molding integration remain open.

## Proposed assembly

1. Slide the stub through the keyed tray socket, install the thin nut from the
   rear and clamp the root pad against the shoulder. Qualify torque, driver
   and nut locking before applying cap-closing torque or fitting electronics.
2. Pot the NTC in its separate offset drill. Its leads exit beside the motor;
   no lead crosses the motor stop. Measure motor fit/force before seating it on
   metal. The nominal11.1 mm bore is not approved press interference.
3. Prewire cap, motor/NTC and insulated body PCB as one module. Two foam pads
   extend into the cap counterbore; their adhesive/retention still need trials.
   Feed disconnected flange tails through the body, turn the whole module and
   seat the cap/seal with the specified process, then connect the tails while
   the flange is still open.
4. Fit the flange PCB, selected pack and wired four-contact inserts; inspect
   the loom, then close the second rigid plastic flange half
   with two proposed M2×6 screws into plastic pilots. Thread form/torque and
   creep/strip resistance remain to qualify. Mold the continuous silicone skin
   over the closed assembly/root after qualifying dummy-assembly trials.

The [overmold/cradle concept](concepts/overmold-cradle/README.md) defines the
proposed closed-insert molding sequence. The [inert casting kit](overmold-trial/README.md)
now provides native skin/split-tool CAD, three print STLs and an assembly sheet.
It uses a solid dummy only for external fill/demold trials; actual cavity,
button/contact tooling and molding qualification remain open. Cap-last
after molding needs a revised connection process; the current tails connect
while the flange is open. Battery service is unresolved because the pack cannot
pass the Ø12 neck and both plastic halves lie beneath the skin. Threadlocker
selection/cure is separate from sealing; no approved adhesive is specified.

The separate [charging-dock/interface prototype](charging-dock/README.md) now
models fixed grooved contact posts/M2 nuts, a revised rear half and skin,
removable contact-face mask and printable clamshell/nest/pin head. It preserves
this native as its source checkpoint. Contact/cavity/button sealing, electrical
integration and physical trials remain open; use the new four-contact kit's
coordinates rather than the old two-target references.

## Evidence and remaining gates

Read [the source-backed DFM review](DFM.md) for setup/tool candidates, thread
reliefs, tolerance budgets and supplier-specific limits. `review.json` records source hashes, part validity, STEP round-trips, closed
plastic STLs, overlap results and scoped motion/access checks. Those do not
prove cutting-tool access, mold release, printing, bond durability or wear fit.
Tray/cover retain 1.6 mm nominal walls, a local nut-well wall about 1.25 mm,
2° shell draft, thin ribs and front-cored posts. Root transitions, resin and
ejection need supplier work. Body/cap volume is about32.9 cm³ (about263 g at
an illustrative density8 g/cm³), excluding nut/electronics/pack. No alloy is
selected. Assess total weight before a wear prototype.

R35F/firmware still expect TMP117/I²C. New NTC analogue input, calibration/fault
handling, PCB tabs, actual loom, charger mate and full boot remain unintegrated.
Battery/BOM stay open. The old P1 fit kit remains superseded.

Rebuild with FreeCAD Python using `tools/build_manufacturing_layout.py SOURCE
OUTPUT`; run `tools/verify_manufacturing_layout.py OUTPUT` with FreeCAD Python.
Then normal Python `tools/configure_manufacturing_view.py OUTPUT`,
`tools/render_manufacturing_layout.py OUTPUT` and
`tools/render_manufacturing_sections.py OUTPUT`. Construction cutters are hidden
in the configured native file. View meshes are caches, not manufacturing parts.

Design references: [Protolabs turning](https://www.protolabs.com/en-gb/services/cnc-machining/cnc-turning/),
[live-tool feature guidance](https://www.protolabs.com/resources/design-tips/mastering-complex-features-on-machined-parts/),
[Festo M18×1 mounting-nut dimensions](https://www.festo.com/media/catalog/205036_documentation.pdf),
[ifm stainless M18×1 nut type](https://www.ifm.com/gb/en/product/E10028),
[Apple Rubber seal installation](https://www.applerubber.com/seal-design-guide/seal-types-and-gland-design/o-ring-installation/).
Supplier approval is still required for this particular design.
