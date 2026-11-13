# UV thermal and sensor mounting trial

`UVModuleThermalTrial.FCStd` is an isolated editable assembly of the **actual two
frozen routed UV boards**, two machined heat spreaders, selected insulating pads,
Sensata67L045 cutoffs and dry VishayNTCLE413E2103F524A sensors with removable
retainers. It does not change either PCB or the dock master. STEP files are metal
quote geometry; the four STL files are derived MJFPA12/tough-SLA retainer trials.
The native source and generator control geometry.

Use `build_components(doc, side='Base', prefix=None, include_board=False)` from
`tools/build_evt1_dock_uv_modules.py` to add the new thermal parts to a master
document. It returns component bodies and `shell_shoulder_adds`, which the master
must fuse into its corresponding shell posts. It does not save or modify the
master's existing geometry. Set `include_board=True` only for the isolated trial;
the master already has source-linked StepUp boards. The lid uses a proper Ry180
rotation, exchanging left/right sites while preservingY. No mirror is used.

## Stack and retention

Each6061-T6 part has1.0 mm arms, Xabs36.6–49/Y86–135, and a lowered rear bridge at
Y128–135. In the base the arms occupy Z8–9 and the bridge Z6.5–7.5. In the lid
these become Z59.5–60.5 and Z61–62. The bridge clears the actual GH STEP body and
leaves0.35 mm nominal to the published4.35 mm mated-height budget. Received
connector, wire exit/bend and tolerance checks remain necessary.

Four5.8 mm wide rounded end notches clear existingØ5.2 plastic posts by0.3 mm
radially. The front notches open toY86 and rear notches toY135; these opposed
openings eliminate the0.1 mm ligaments that closed holes would leave at the
existing board-edge spacing. AddR3.8 capture
shoulders to those posts: base shoulder faces Z8 atY89 and Z6.5 atY132; lid faces
are their proper rigid transforms. Existing four board screws and fixed B-face
seats remain unchanged. The metal is captured between shoulders and the PCB;
pad compression provides preload. Do not rely on a floating pad's tack as
retention. Assemble spreader over posts, fit pads, lower the actual PCB, then
install the existing screws. The shoulders are provided as exact addition
solids, not yet merged into the master or physically tested.

Two raised10×2 mm islands sit behind the LEDs at X±42/Y94. Their base top face is
Z11.8, leaving0.40 mm to the electrical B-plane Z12.2, approximately0.39 mm to
the nominal10 µm mask surface. Use2×12×3×0.508 mm cuts of
**Henkel/Bergquist GAP PAD TGP1500**, nominal21.3% compression. The cut overhangs
the metal by1 mm perX edge and0.5 mm perY edge. The sheet ordering candidate is
GP1500-0.020-02-0404; confirm current manufacturer sheet identity and thickness
when quoting. The [manufacturer material guide](https://dm.henkel-dam.com/is/content/henkel/lt-8116-brochure-thermal-interface-materials-selection-guide-1)
describes an electrically insulating1.5 W/mK silicone material. Its typical
dielectric and thermal results do not qualify the cut pad on this assembly.
Received thickness tolerance is not assumed. The installed rectangular CAD pad
is a clearance pose; lateral flow, pressure and actual contact area are untested.

Every LED terminal/via field remains a separate electrical net. Deburr and round
island edges R0.2 and target Ra≤1.6 µm. Inspect cut pads for tears/pinholes and
qualify actual insulation to the common metal after assembly and thermal aging.
Soldermask and anodizing are not credited as insulation. The FR4/via/spreader
stack does not inherit the LED datasheet's Al-MCPCB thermal resistance.

## Selected sensors

The [Sensata manufacturer drawing](https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf)
defines the actual67L045 TO-220 body, metal tab, hole and two leads. The native
reconstruction preserves those features. Nominal top-to-case-bottom15.24 mm is
derived from overall29.59 mm minus the14.35 mm reference lead dimension; it is
not a guaranteed body-height tolerance. The drawing's metric3.64 mm hole label
differs slightly from its0.145 inch label; measure the received part.
The existing4.5–5.25 V contact-load qualification remains open; the published
nominal5 V low-level rating does not establish the entire operating interval.

The bracket back face is at base(42,97,10.5), contacting an integral raised
ledge. Body faces outward through a machined bay, with a1.4 mm outer metal web
remaining. Body depth4.70±0.25 mm maps to upper case extent≤62.95 mm for that
depth allocation, beneath the64.1 mm roof datum. A custom6061 pressure bar8×5×1
and **NBK SNSS-M2-3** retain the tab. Nominal Al thread engagement is1.24 mm;
accept≥1.0 mm after measuring the real screw/bar/tab stack and maintain≥0.2 mm
clearance from screw tip to PCB copper. Bracket distortion, tightening torque,
retention and cutoff lag must be qualified. Do not infer allowable torque from
the screw alone.

Candidate terminal cutting retains6 mm after the case, beyond the5.49 mm lead
shoulder. Confirm supplier handling/solder constraints before cutting. Use
separate **TE RNF-100-1/16-0-SP** sleeves on both terminal/joint paths. The removable
PA12 guard has twoØ2.8 tunnels for sleeve OD≤2.4 mm, a front locator and one rear
**Accu SIK-M2-4-A2** screw. It includes lacing slots for **Panduit PLT.6SM-C**.
The actual tie/head/tail pose and wire joints are not installed CAD geometry;
route and retain them in the received assembly trial before claiming fit.

The [Vishay manufacturer's current datasheet](https://www.vishay.com/docs/29078/ntcle413.pdf)
permits a dry attached sensor and excludes hard potting, overmolding and fluid
immersion. This model reconstructs its maximumØ3×10 mm head as a capsule, not an
OEM surface profile. A machined90°V saddle on the left arm atX−42.8/Y108.5 receives
the head near the LED/boost region. A removable PA12 clip and small TGP1500
support retain it against both V faces. Two AccuSIK-M2-4-A2 screws enter printed
M2 pilots. Body clamp reaction target is0.05–0.20 N, to be measured on received
heads/pads; do not tighten a rigid cover onto the lacquered bead. Cable lacing
acts on insulated leads beyond the head. The52±5 mm factory leads need a
separately retained extension to reach the opposite-arm lands along the rear
route. Those installed extensions remain to integrate.

## Trial and acceptance

1. Quote the native metal geometry and specified finish. Inspect the1.4 mm web,
   flatness, burrs, holes, blind/through thread depths and the complete received
   pad stack. Allow internal cutter radii≤0.25 mm in the oversized reliefs;
   recheck supplier corner proposals against the retained parts. The rear wire
   slots extend0.5 mm beyond the guard to accommodate these cutter corners.
   Print the two retainer designs in MJFPA12 or tough SLA; remove all
   residue. Jig drill/tap pilots from received parts. Do not assume printed taps
   or tightening torque are qualified.
2. Assemble with unpowered boards and sensors. Measure pad compression/contact,
   PCB bow, shoulder seating and all actual clearances, including GH mating/wire
   exit and UI-board F planes60.0/60.5/61.0. Confirm no component case or solder
   joint touches the metal. The source-linked native checks are nominal only.
3. Verify dry head seating and soft reaction, then apply1 N to each insulated
   sensor tail with the lacing secured. Accept no load transfer to the bead/tab
   terminals, no visible coating damage and no electrical discontinuity. Record
   actual screw torque and pad/head/retainer dimensions. Establish supplier
   allowable bracket load and successful retention before powered operation.
4. Measure insulation between every distinct LED terminal field and common
   metal, plus between sleeved thermostat terminals and metal, before and after
   thermal cycling. Use a documented qualified test procedure for this39 V-OVP
   circuit; catalogue dielectric numbers alone are insufficient.
5. Instrument both LEDs, driver, metal contact regions, NTC and hardware cutoff.
   Find actual hottest regions and sensor lag in the closed dock under normal
   and credible fault conditions, then validate placement/thresholds. The left
   NTC and right cutoff locations are candidates, not proof of uniform metal
   temperature. Move mounts if the measured map requires it. Do not infer
   junction temperature, safe run time or thermal protection from nominal fit.

Optical leakage, dose, cleaning efficacy, material aging, installed wire routes
and finished UV containment remain unmeasured. This is an assembly/thermal
prototype, not a sterilization claim, order or full-product release.
