# Goal
Compass EVT1 device board: charger, two regulators, motor driver, sensors, ESP32-C3 and four dock contacts on one small four-layer board, in a turned metal plug body with a plastic flange under a silicone skin. Lucy asked on 2026-11-18 to make it much smaller and narrower than the 82 x 26 mm first article, and then to model the plug the board goes into.

# Parts
- compass-one-board (this folder): the device PCB, 52 x 20 mm, 4 layers, two-sided assembly, to be ordered.
- FlangeTray (mech/): printed flange tray, 56 x 32 mm, plan corners R 8, body-side edge rounded over (R 10 ends), dock-side edge R 3 at the ends (the skin R 4.3 / R 5 over it), bowl-shaped board cavity (no flat walls above the board), clamps to the metal body's M18 stub with the thin nut and seats the board; to be ordered (MJF PA12).
- RearCover (mech/): printed dock-side cover with the board bosses, contact openings and the sliding-button bores; to be ordered (MJF PA12).
- ButtonPlunger (mech/): printed rigid button that slides in the cover and is pressed through the silicone onto the tactile switch, two per device; to be ordered (MJF PA12).
- FlangeSkin (mech/): silicone skin reference over the flange, ramping smoothly up the metal neck, with a window for the dock contacts, a low dome over each button and a raised up-arrow and a recessed R+D icon in the lower corner of the dock face; process reference, not ordered.
- InternalCradle and CradleWireGuide (mech/): printed lower battery frame with motor rear stop and removable open wire guide, four provisional M1.4 screws; editable FreeCAD parts linked into compass-device. MJF PA12 candidates, not ordered.
- Internals (mech/): the 3-wire battery pack, motor, tip NTC and the wires from the board, as reference envelopes; not ordered.
- MetalBody (mech/): the turned body from the hardware/cad/manufacturing-layout study with the 2026-11-18 smooth neck-to-bulb shoulder (metal_body.py); alloy still open, not yet to be ordered.
- MotorThermistorCap, ThinRearNut (mech/): nose cap and M18 thin nut, copied unchanged from the study; not yet to be ordered.
- CapFaceSeal (mech/): rubber face O-ring between the metal body and nose cap, in the existing nose gland; nominal 32 mm ID x 1 mm section, shown at installed squeeze. Stock/material and sealing remain unqualified; not ordered.
- compass-device (mech/): the assembly STEP of all of the above with the board.

# Notes
- Create a full-scale inert exterior mockup for Lucy's Bambu P2S with a 0.4 mm nozzle. Keep the current product geometry; use two flat-print halves and loose alignment pins for dry size/handling checks.
- Width is no longer tied to the 88 x 32 mm flange tray; the flange is redesigned around the new board. Its 32 mm height is set by the 24 AF thin nut's rotation well, not the board.
- Dock contact pitch (6 mm), ESP32 antenna keepout and the J3/J8 connector facing are kept from the first article.
- The nose cap, M18x1 stub, thin nut and the keyed collar socket are unchanged from the manufacturing-layout study. On 2026-11-18 Lucy asked for the body's neck to flow into the bulb without the shoulder crease (tangent contour, revolved 360); the bore transition now follows that outside at 2.2 mm wall, the pack keeps 1.2 mm of room. The study folder is untouched.
- Flange comfort (2026-11-18): the silicone's body side is one continuous hull: from the side walls it curves in and runs tangent into the neck ramp on the long sides (for the crack) and on the ends; the printed tray under it has an R 10 round-over at the ends and only a small one on the long sides because of the nut well.
- The dock face carries a raised arrow, the magnetometer calibration reference the first article had. Since 2026-11-20 (Lucy) it points toward the flange end nearest the buttons (-X), which is "up".
- Battery pack lives in the body bulb, not the flange; its leads come through the 12 mm neck bore to the board's B.Cu connectors.
- Lucy chose on 2026-11-18 a 3-wire protected 502030-class pack with its own NTC (EEMB LP502030-PCM-NTC-LD class) instead of the 2-wire pack plus two tape-on NTCs. The board's J2 is a JST SH 1.0 mm 3-pin header (PACK_P, GND, PACK_NTC; since 2026-11-19 instead of solder lands, so a stock pack with a JST SH 3P plug plugs in and nobody solders it); J8, TH2, TH3 and the PACK_GUARD land are gone, U8/R43-R45 are DNP, and pack temperature is read on AIN2 from the charger's TS node. The 3-wire pack is specified as BC-PACK-EVT1-002 in one-board/PACK-RFQ.md (2026-11-21); its own NTC is the battery temperature sensor (charger TS cutoff and firmware reading). Open: the JST SH contacts are rated 1 A against the 1.5 A load request.
- Lucy wants the silicone base to ramp smoothly into the metal for comfort (2026-11-18); the skin is 4 mm thick on the flange's long sides to make room for that ramp.
- Buttons (2026-11-18): rigid plungers that slide in the printed cover under the continuous silicone, for better tactility than pressing the switch through the skin alone. Inserted from inside, retained by a flange in a counterbore, nothing open to the outside but the head.
- Board sits with F.Cu (contacts, buttons) toward the dock and B.Cu (connectors, ESP32, regulators) toward the body; F.Cu face at Y -21 in the device frame.
- 0201 passives and other package changes are acceptable if space needs them (not used yet; BOM unchanged).
- Pack: a factory-protected 3-wire pack with its own internal NTC is mandatory for any chemistry considered (Lucy, 2026-11-21). Current baseline is 1S LiPo; the second pack NTC and the dry pouch NTC are gone.
- Dense rules: 0.1 mm clearance and track, 0.45/0.2 mm vias, within the fab's base-price limits.

- Interior support (2026-11-21, Lucy): design a 3D printed cradle to locate the battery, guide the cables and retain the motor in its existing bore. Preserve the accepted metal/flange geometry and show any clash-driven geometry change before adopting it.
- Interior cradle candidate: battery loads into the lower frame before the four-screw wire guide is fitted. Two soft support-pad envelopes fill the nominal 1.2 mm shelf gap. Body taper and motor stop capture the frame with about 0.49 mm combined nominal axial play; no preload is credited. Seven guided wire paths clear nominally. Printed fit, soft goods, screw retention, cap/free-tail assembly and motor terminals remain to qualify.
