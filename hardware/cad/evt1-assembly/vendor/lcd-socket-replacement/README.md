# LCD socket replacement study

The preceding Molex 52437-2771 model remains frozen. Its manufacturer STEP is
open; moving the rigid actuator 1.6 mm established a closed outer envelope,
not a validated loaded pose. The actual dock audit found 8.338480603 mm³ of
FFC/socket interference at PCB front Z60.5. Raising the board clears the latch
while introducing rigid intercontact-guide interference. No tested height is
promoted as a valid mate.

`negative-molex/review.json` binds the exact saved dock, original OEM STEP and
probe outputs. `negative-molex/socket-sections.png` shows native sections through
a terminal and an intercontact guide. The modeled 0.200 mm ribbon/stiffener
stack encounters a 0.180 mm rigid guide/latch gap. This does not prove that a
received Molex connector is incompatible; it proves that this translated open
model cannot establish the loaded mating height. No geometry is suppressed.

The primary references are the [Molex drawing SD-52437-019 Rev F](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/524/52437/524373071_sd.pdf)
and [selected gold-family specification PS-52437-027](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/524/52437/PS-52437-027-001.pdf?inline=).
Neither supplies a loaded copper-face height. The specification also requires
full insertion to the actual housing stop and received FPC compatibility checks.

The separate candidate selects **JST 27FLZ-RSM2-TB**, the bottom-contact,
right-angle mate listed by [Newhaven](https://newhavendisplay.com/27-pin-surface-mount-right-angle-connector-with-0-5-mm-pitch/).
It preserves the selected display, its 65 mm FPC and every electrical terminal.
The original Molex board, display and old socket sources remain frozen.
The candidate board is in `hardware/pcb/evt1/dock-control/lcd-socket-candidate/`.

The [JST public catalog](https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf)
defines its solder pattern, nominal 19.4 mm width, 4.6 mm closed depth, 2 mm
mounting height and 0.30±0.03 mm FPC thickness. It does **not** define a loaded
contact-plane height, insertion stop, internal guides or a tolerance on that
overall height. The native `JSTSocketReceivedFit.FCStd` therefore contains
dimensioned drawing sketches, not an invented socket cavity or a solid box
used to claim fit. No socket solid is attached to the board's 3D model.
OEM STEP and the exact part drawing currently require JST's contact/license
form; no form, account, agreement or outbound message was submitted.

There are two additional compatibility limits. JST specifies ≥3 mm exposed
land and 0.35±0.04 mm conductors; the Newhaven drawing specifies 3±0.2 mm
exposure and nominal 0.30 mm lands. The Newhaven recommendation supports this
trial selection but does not prove every drawing-tolerance combination.
The JST catalog's marked-end triangle has no explicit “pin 1” legend. The
mounting-surface and reverse-type views support pin 1 at native −X and mouth
native +Y (dock −Y); that numbering remains a conventional inference until
received continuity establishes it. Do not apply power based on the drawing
inference alone.

`build(doc)` in `tools/build_evt1_dock_lcd_socket_replacement.py` returns
`JST27FLZDrawingDatums`, with fully constrained mounting/projection sketches.
`build_fixture(doc, stack_mm=1.0)` returns `JSTSocketReceivedFit`. Save the
owning document before adding its external links. Its real printable roof
copies the frozen LCD-retention coupon and adds a rear extension, four native
downward seats and M2 tap pilots. Four separate native annular shims use the
existing UI holes at (−30,65), (30,65), (−32,115), (32,105), OD5.2/ID2.3 mm.
Fourteen links retain the actual LCD, bezel, carriers, foam/PET and selected
bezel screws from the frozen retention trial; no new glass clamp is invented.
New fixture additions are checked against those linked parts. This is not a
populated-board or loaded-socket fit test.

The equal shim search interval is **0.10–1.50 mm**, giving PCB front
**Z61.40–60.00** from seats Z61.5. It is a measurement interval, not a proven
installed adjustment range. Print the rigid fixture in MJF/SLA; the thin
annular stack is cut from measured stock shim film, not printed as a 0.1 mm
washer. The retention trial already selects CS Hyde **48-2F-1-100** plain
Mylar Type A PET, nominal 0.0508 mm per layer, from the
[manufacturer film catalog](https://cshyde.com/viewitems/films/mylar-polyester-pet-film).
Die-cut OD5.2/ID2.3 rings and retain each equal stack on its mounting screw.
Measure total thickness: two through 29 nominal layers span 0.1016–1.4732 mm;
do not infer film tolerance or assembled compression from nominal layer count.
Set the native `Stack` parameter to the measured equal total.
Use `JSTDisplayFitRoof.step` for the MJF/SLA quote. The STEP readback matches
the native roof in volume, center of mass and bounds. The editable fixture
and retention pieces can be downloaded together as `JST-Display-Fit-Review.zip`.
The existing M2x6 underside screws and tapped
plastic scheme need inert assembly/strip trials. Clamp the broad outer coupon
flats in a bench support, leaving screw-driver access underneath. Use the
retention trial's measured glass depth and foam/PET stack; never press bare
glass edges, the active area or COG.

Received procedure, unpowered first:

1. Inspect the exact socket marking, latch and solder joints under magnification.
   Measure the actual FPC thickness, conductor width/exposure and soldered
   housing height. Reject damaged, bent or out-of-range tails; do not trim the
   selected FPC to force a match.
2. Use a separate unpowered 27-way test tail with known conductor numbering to
   identify every solder terminal and its marked end. Probe every intended
   path and neighboring-pair isolation. Record photographs and the numbering
   result before inserting the display.
3. Open the slider, insert the display tail without force to the **received
   physical stop**, close the slider and inspect square insertion and actual
   exposed-copper/contact overlap. Never treat Y112.575222 as proof of seating.
4. Hold the actual LCD at front Z68.8 using its retention coupon. Keep its
   existing 65 mm routed flex neutral; bend radius, flex strain and exact stop
   remain measured gates. Move the PCB with equal shims until the tail is
   neutral at the real socket's loaded plane. Do not pull the tail into place
   with the latch or screws.
5. Measure the loaded copper-face height **H** above PCB front. For the current
   fixed copper face Z61.70, the proposed board front is `F=61.70−H` and equal
   shim thickness is `t=61.5−F`. Measure the loaded FPC rather than assigning
   a height from an undimensioned catalog illustration. If the neutral route
   changes, update and independently check the native FPC pose first.
6. Verify all 27 display-tail/PCB terminal paths and adjacent-pair isolation
   with a display-safe, current-limited method and a known pinout; semiconductor
   paths can affect resistance readings. Confirm VDD/GND and signal mapping
   independently. Do not infer continuity from a powered display test.
7. Lock equal measured shims, then check complete native and received roof,
   all B-side components, screw heads/drivers, three unpressed/full-stroke
   buttons, FFC corridor, lid motion and strain relief. The parent assembly
   owns these whole-case checks. Repeat continuity after several latch/mate
   cycles before a current-limited powered trial.

No loaded contact plane, socket solid/case fit, button range, physical
continuity, powered display or complete product release is claimed here.
