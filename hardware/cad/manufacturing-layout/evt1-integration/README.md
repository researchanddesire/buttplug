# EVT1 device-board integration

`EVT1Product.FCStd` fits the actual saved body, flange and compass PCBs into
the four-part mechanical direction. The manufacturing and dock natives are
read-only inputs. This is a **nominal assembly checkpoint**, not the complete
EVT ordering/build release.

The native contains the turned body/cap, revised flange tray and four-contact
rear half. The tray adds two integral sensor bosses; no rigid board scaffold
or separate motor carrier is introduced. `FlangeTray.stl` and `RearHalf.stl`
are bed-oriented, closed dry-fit prints. Four STEP files provide exchange.
Files ending `-view.stl` are rendering caches, not print orientations.

The four contact posts now include trial metal face-seal glands and installed
ring-space references copied from the current dock native. This leaves the
external face/pitch/stop datums unchanged. The separate
`charging-dock/contact-seal-trial/` fixture tests one post against a representative
counterface. Ring/casting compatibility, finish, preload/creep and real leaks
remain unqualified; these glands do not implement permanent button barriers.

`review.json` binds the saved native, inputs, actual PCB hashes and exports.
Independent saved-native checks pass: 8,256 hard-part pairs, component/mate
clearance, sleeve/foam clearance, two sensor-screw envelopes, 25 flange-board
loading poses, 25 sensor-board poses, 29 requested-pack/NTC poses and 108 cap-module
insertion/rotation poses. R39 clears the drafted tray seat by0.250mm with the
selected maximum resistor case; sensor C83 clears the requested pack by1.95mm.
Selected part XY maxima supplement native Fab outlines. No tolerance stack,
actual wire/plug bends, material, casting or physical fit is proven.

The body PCB frame is product(x,y+5,z−0.5). J5 uses the JST6.3mm top-entry
mated height; side-entry socket projection is2.25mm. The motor reserves its
published maximumØ11.1×26.3mm case and a separateØ11.1×6mm rear lead-exit
allowance. Actual lead width/gauge/angle remain supplier acceptance items.
The insulating wrap has a J5 exit window and two rear upper-corner reliefs;
the PCB edge remains covered. Its cut/fold/retention process needs a trial.

## Battery interface

The requested BC-PACK-EVT1-001 protected pack occupies33×21×6.3mm, with its
PCM/lead exit toward the neck. Two dry Vishay NTCLE413E2103F524A head/transition
envelopes lie on the broad face. The reserved growth space adds1.1mm thickness
and0.25mm lateral clearance per side and clears the saved hard parts. These
are requested supplier bounds, not an approved pack or swelling guarantee.
See `hardware/pcb/evt1/PACK-RFQ.md` and `pack-spec.json` for the1.5A continuous
request, protection/lead requirements and separate sensor returns.

The pack maximum moved0.3mm rearward, leaving0.95mm nominal between its front
and the stub tip for sensor wires. Extra thickness is1.1mm, about20.8% of the
reference5.3mm cell; this is an engineering allowance requiring supplier
approval. The factory28AWG leads terminate in an ACHTR-02V-S socket; the body
mate is ACHTP-02V-S. A7×4×2.1mm mated budget is reserved beside the stub,
not an OEM connector model. Connect battery power after cap threading.

The pack module has six physical conductors. Keep the two sensor returns
separate from power return until their body-PCB lands. Tape-couple the NTCs
inside the dry cavity; do not directly overmold or hard-pot them. Retention,
support and actual lead routing still need design. EVT workshop battery service
consumes/remakes the continuous silicone skin before opening both rigid halves;
trial that process on an inert assembly. No rear service lid is introduced.

## Compass mount

The12×10×1mm sensor board hasØ1.6 holes on9mm centers. TwoØ4 integral tray
bosses locate it with its back at productY−10.8 and F surface atY−11.8.
BlindØ1.1 pilots reserve an M1.4×0.3 tapping process: at least1.5mm full thread,
2.2mm nominal pilot depth and0.6mm remaining front wall. Qualify drilling/tap
depth and strip/assembly torque on the selected printed plastic first.

Prototype screw selection: two
[NBK SPA-M1.4-2.5-MC3](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/highintensity/SPA-MC3/SPA-M1.4-MC3/SPA-M1.4-2.5-MC3/)
RENY screws, M1.4×0.3,2.5mm long,Ø2.5×0.8mm head; SKCHB-M1.4 bit. CAD budgets
Ø2.6×0.85mm. AØ3.2×15mm axial access reservation clears the open assembly before
the pack is installed; it is not a qualified bit/shank model. The manufacturer's
screw torsional value is not an allowable torque for the plastic boss.

Product+X is the molded tailbone/back arrow,+Y points toward the nose.
Sensor-board local+X maps to product+X, local+Y to−Z, and F normal to−Y.
This establishes mechanical registration. Derive the distinct accelerometer
and magnetometer package transforms from the ST drawing and confirm them
with a fixture; no wearer pose calibration is introduced.

## Assembly limits

Tighten/lock the rear nut before loading boards. Thread the prewired cap/body
module with free flange tails; connect those tails while the flange is open.
Load the flange board, fit the sensor and its screws, then install the pack.
J81 is a hand-solder sensor-loom land; its GND pad intentionally contains a
plated stitching via. Keep solder/strain relief within the reserved space.
The shortened open-ended sleeve covers the body board/mated-height envelope
and stops before the motor. Foam pads stay independent of motor retention.

Close both rigid flange halves before molding one continuous silicone skin.
The separate dock kit supplies contact/mask and inert split-tool trials. This
checkpoint does not implement permanent button barriers, cavity seals, actual
pack/loom, final nut locking, qualified machining callouts or a molding process.
Do not cast an electronics/battery assembly using dummy-trial instructions.

Rebuild with FreeCAD Python using `tools/build_evt1_product.py`, then
`tools/verify_evt1_product.py`. Render the verified mesh exports using
`tools/render_evt1_product.py`. All five routed PCBs have source-bound native
DRC and independent pad/netlist parity checks in `hardware/pcb/evt1/`.

No print, machining, cast, powered or wear result is claimed.

The actual flange PCB and this product native now turn J7 toward the neck,
move D71/U75/D73 and expand the west PCB body within its existing overall tabs.
Native DRC/pad parity and the complete saved product geometry/loading checks
pass. `loom/neck-facing-j7-trial/` preserves the prior geometry screen and
routing evidence. The current ten-wire native is `loom/EVT1Loom.FCStd`; its
`review.json` controls the independent wire-check status. Seven logical WireViz
recipes under `hardware/cables/evt1/` retain starting stock. First-article
crimps/egress, restraint, the other installed routes and physical assembly are
unfinished. The colliding away-facing study is preserved under `loom/archive/`.
