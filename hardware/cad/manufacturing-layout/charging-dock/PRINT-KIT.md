# Dock and contact-interface print kit

Start with an **unpowered fit trial**. The archive includes the editable
`ChargingDock.FCStd`, thirteen closed STL meshes, CAD views and fabrication
quote ZIPs for the two cradle PCBs. No slicer profile, physical print, cast,
powered contact or USB result exists.

## First nine prints

Print one each of `DockBase`, `DockLid`, `DockNest`, `PogoCarrier`,
`PogoRetainer`, `DockDeviceGauge`, `PinPCBBlank`, `MagnetBackSpacer0` and
`MagnetBackSpacer1`. STL bed orientations are already set; inspect supports
around the hinge, carrier interior and gauge underside before slicing.

The solid gauge represents the device outside. Its printed contact faces
cannot conduct. The plastic pin-board blank is a spacer/drill template; use
the actual **1mm FR4 pin board** for soldering and electrical work.

Trial hardware: M3×60 hinge bolt/locknut; M3×10 closure screw; six M3×8 nest/head
screws; two M2×6 countersunk retainer screws; four M2×4 USB-board screws.
Candidate pins are four Mill-Max0906-2-15-20-75-14-11-0. Dock magnets are two
Ø8×3mm pieces, captured behind the retainer with the printed spacers. Qualify
plastic pilots, screw heads/engagement, received pin/magnet sizes and shim fit.

Dry-fit the carrier and spacer, then the nest and hinge. Overall case space is
115×166×65mm, including hinge/latch. Lower the gauge **3mm away** from the
contact head, then slide it3mm to mate. Slide away before lifting. The insulating
stops register against the fixed metal targets in the real assembly; silicone
does not set spring compression.

The USB board's narrow nose places the socket face flush with the case. Its
four mounting screws require pre-tapped/tested Ø1.6 plastic pilots. The pin
board's J94 wire lands face rearward near its lower edge; solder and inspect
those wires before fitting the retainer. Conductor bends/strain relief,
spring load, magnetic holding and USB performance still need physical trials.

## Four additional interface/tool prints

`FourContactRearHalf`, `ContactFaceMask`, `ContactMoldHalfA` and
`ContactMoldHalfB` support an inert contact/casting trial. The product uses two
closed rigid flange halves beneath one continuous silicone skin. Fit the fixed
metal posts before closing them. Their faces are GND/D−/D+/5V along increasing
product X, on6mm pitch; moving pins and magnets stay in the dock.

After curing an inert trial, withdraw the contact-face mask along−Y **before**
opening the main tools along±Z. The mask uses two M3×10 screws; split tools use
four M4×65 bolts, eight washers/four nuts and twoØ4×10 alignment dowels.
Button barriers and real closed-cavity seals are unfinished: use dummy
assemblies for this tooling, with no battery/electronics inside.

The revised rear half hasØ2.10 contact bores. Its metal posts now include a
trial inner face-seal gland, ID2.10/OD3.60/depth0.38mm, for a nominal2×0.5mm
ring against the flat rigid plastic. This preserves all contact-face/dock-stop
datums. `engineering/contact-seal-spec.json` records requested finish and ring
inspection/compatibility limits. The nested `Contact-Seal-Trial-Kit.zip`
contains two additional fixture prints, editable CAD and an inert316L post RFQ
for a one-contact water-column trial. It has no physical seal result and does
not qualify printed counterfaces, NBR/casting compatibility or complete cavity
sealing. Follow its own README before any molding trial.

Metal contact stock/finish, M2 retention and silicone bonding are unqualified.
The native model's thread-root envelopes are references, not finished thread
surfaces or machining drawings. Material/cure/pressure and functional seals
remain to qualify. UV hardware and a sterilization claim are not included.

## PCB quote files and source

Both cradle boards pass native ERC/DRC and independent pad/netlist checks.
Their Gerber/drill ZIPs are quote files: request2-layer1mm FR4,1oz copper,
ENIG and supplier acceptance of the USB footprint's0.15mm hole-to-copper
clearance. They have not been ordered or supplier-approved. Match the native
board outlines; a thicker pin board changes spring compression.

Repository sources live in `hardware/pcb/evt1/` and
`hardware/cad/manufacturing-layout/charging-dock/`. The complete device still
has five routed PCBs passing native DRC and a separate actual-board fit native.
It still needs supplier pack approval/retention, non-PCB parts, factory axes/calibration, nut
locking, loom, button/seal tooling and commissioning. Device sources and their
quote files are kept in the separate board-fit checkpoint, outside this dock kit.
