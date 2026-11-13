# Assembly direction

Use the current two-piece CNC metal study in `hardware/cad/manufacturing-layout/`.
Its `README.md` and `DFM.md` control the proposal and remaining manufacturing
questions. This is **not a released build**; the old P1 kit remains superseded.

## Parts and joints

- Turned body with15 mm neck, rear shoulder, keyed collar and short M18×1 stub.
- Turned nose cap with motor pocket/metal stop and one offset NTC drill.
- Open flange tray with root pad, board seats and pack ribs.
- Rear cover with two proposed M2×6 screws into plastic, independent of body retention.

A generic 24 AF ×4 mm thin nut clamps the tray's 2 mm root pad against the
metal shoulder. Opposing collar flats resist twisting. Specify tightening
torque and use Loctite on the metal threads. The torque and cure process are
unqualified; no compression limiter or socket adhesive is credited.
The silicone cuff bonds to the recessed metal land and meets its upper shoulder
flush. The planned continuous skin is molded over both closed plastic flange
halves and this root. O-ring, insulation/foam, adhesives and hardware are additional.

## Proposed order after electrical/manufacturing review

1. Slide the rear stub through the matching keyed socket. Install the thin nut
   through the open rear and clamp the tray pad against the shoulder before
   boards/pack/loom are present. A narrow axial two-jaw driver is reserved in
   CAD; qualify tooling, torque and threadlocker on inert assemblies first.
   Verify the final nut angle clears both pack sensor heads before loading them.
2. Pot/cure the offset NTC; leads exit beside the motor. Seat the motor on metal
   after actual case/bore/edge-fit and force checks. Potting and PCB carry no press load.
3. Prewire the cap, motor/NTC and insulated body PCB, with foam pads extending
   into the cap counterbore. Feed disconnected flange tails through the body;
   turn the whole module, seat its face O-ring/shoulders and connect tails last.
   Threadlocker is a separate qualified process, not the cavity seal.
4. Fit the flange board and fixed compass daughterboard before the pack.
   The actual-board CAD in `hardware/cad/manufacturing-layout/evt1-integration/`
   adds two integral sensor bosses. Trial their blindØ1.1 pilots/M1.4×0.3 taps
   and NBK SPA-M1.4-2.5-MC3 RENY screws before installing electronics. Do not
   use the screw's catalog torsional value as a plastic-boss torque allowance.
   J81's GND hand-solder land intentionally has a plated stitching via; inspect
   its joint and strain relief. Use the exact PCB parts/positions from each
   EVT1 `assembly-quote/`; C83 is TDK C2012X5R1E226M125AC22uF25V. Qualify at
   least10uF effective at3.3V over the intended temperature/age, plus regulator
   capacitance/reflow/orientation, during incoming/process commissioning.
   Fit the supplier-approved BC-PACK-EVT1-001 variant within the requested
   maximum and growth space. Tape-couple the two Vishay pack NTCs in the dry
   cavity; do not directly overmold, immerse or hard-pot them. Preserve six
   physical conductors: power pair and two independent NTC pairs. Join sensor
   returns only at bodyJ2 land2S, power return at2P. Retention/lead routing still
   need completion. Then fit the wired feedthroughs;
   inspect/test while open, then close the two rigid plastic flange halves.
5. Mold one continuous silicone skin over that closed assembly/root. Qualify
   the process on dummy assemblies first; control cure/exotherm/pressure, mask
   contact faces and metal functional surfaces, and prevent button/cavity flooding.
6. Demold, finish and inspect skin, contacts, root bond and electrical paths;
   test sealing and retention before a build release.

The cap-after-molding idea needs a revised connection process: step3 is the
current compatible wiring order and requires the flange open. EVT workshop
battery service consumes/remakes the continuous skin to open both rigid halves;
practice skin removal on an inert assembly first. No neck-extraction path or
rear service lid is introduced. External
Power/Mode and the USB cradle have independent recovery circuitry/code, with
physical flashing/timing still to verify; the rear half lies beneath the skin.

## Holds

For the dock/contact plastic fit, use the separate
[charging-dock print kit](../hardware/cad/manufacturing-layout/charging-dock/README.md).
It includes a clamshell, nest, serviceable pin carrier and a solid whole-device
gauge. Lower the gauge at+3mm axial offset, then slide to the contact stops;
slide away before lifting. Printed gauge contacts are for mechanical trials only.
The same source proposes fixed grooved metal posts/M2 retention, buried keepers,
a revised rear half/skin and a removable face mask. Fit those before closing
both halves; withdraw the face mask first when demolding. Material, contact
seals, permanent button barriers and real closed-cavity trials remain open.

The current contact posts add a trial inner face seal against the flat rear
half: ID2.10/OD3.60/depth0.38mm metal gland and nominal2×0.5mm NBR70 ring.
The contact bores areØ2.10; all face/stop datums are preserved. Inspect/solder/
clean/cool the post before fitting its ring, fixture the faces while retaining
the M2 nuts, then qualify actual seating/torque/strain relief. No seal claim
follows from the space model. Start with the separate
[single-contact inert trial](../hardware/cad/manufacturing-layout/charging-dock/contact-seal-trial/README.md),
which supplies two fixture STLs, a316L post RFQ and gravity water-column
procedure. Printed rough faces only check fit. NBR/casting cure compatibility,
machined counterface finish and actual leak/aging tests precede electronics.

The first physical molding build can use the separate
[inert overmold kit](../hardware/cad/manufacturing-layout/overmold-trial/README.md):
two printed tool halves, a solid closed-assembly gauge, four M4×65 clamp bolts
with washers/nuts and two Ø4×10 dowels. Its assembly sheet covers dry fitting,
material coupons, bottom filling, side opening and inspection. This tests
external fill/demold only; it has no real cavity, battery, electronics, buttons
or contact feedthroughs. Print/slicer, material compatibility and actual casting
results are pending. The two product flange halves still close before molding.

M30×1.5 fit/gaging, six mm effective male engagement, reliefs, gland tolerances,
actual motor fit, rear nut/driver/lock, cuff bond aging, plastic bearing/creep,
key retention, pull-through, local 1.25 mm nut-well wall, full overmold/tool and
service process require review/trials. Actual routed boards and requested
pack/NTC/growth envelopes fit the separate integration native. Supplier pack
approval, retention, flexible loom and physical fit remain open. Current
body/cap volume is32.9 cm³, excluding the nut; material/weight remain open.

Use EVT1 circuit/firmware for the ADS1115/two-wire tip NTC and fixed LSM303AGR;
R35F/legacy firmware expect the former sensors. Complete non-PCB hardware selection,
loom, seals and powered commissioning before a full build release. The BOM stays human-owned.
No actual machining, print, assembly, leak, cleaning or wear result exists.


The current dock also has two routed FR4 boards in
[`hardware/pcb/evt1/`](../hardware/pcb/evt1/README.md). Their fabrication ZIPs
are quote files pending supplier capability review. The full product is still
missing selected non-PCB hardware, accepted pack/retention/loom and final seals. All
five routed boards pass native DRC; that does not qualify powered operation.
The plastic `PinPCBBlank` is a dry-fit gauge; use the actual1mm board for wiring.

For the electrical cradle assembly, solder the four spring pins square to the
pin board and verify its6mm pitch in the carrier before closing the retainer.
J94's GND/D−/D+/5V wire lands are on B.Cu beside its lower edge. Solder and inspect
them from the rear; the revised retainer window clears their solder/bend space.
Route the paired D+/D− conductors through the downward channel. Actual wire
length, strain relief and USB performance still need a hands-on trial.
Use the current [EVT1 cable sources](../hardware/cables/evt1/README.md) and
[harness table](cable-harnesses.md), not the old two-contact P1 map. The contact
and dock diagrams identify numeric pins; their blanks are starting stock.

Fit the USB-C PCB to the four base bosses with M2×4 pan screws after pre-tapping
itsØ1.6 pilots; qualify screw force rather than crushing the board. The socket
face is flush with the case; its narrow PCB nose passes through the wall window.
Then install the removable nest. Check cable insertion and retention before
connecting a computer or the device. Initial current-limited bench tests must
verify contact order, shorts/reverse paths and the dock's current limit before
USB enumeration, charging or flashing tests. Device-board and sealing work
remain required before a complete functional product build.
