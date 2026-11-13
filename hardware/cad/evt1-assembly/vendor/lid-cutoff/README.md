# D2F-01L lid cutoff component

This selected switch has a hinge lever, gold-alloy contacts and straight PCB
terminals. The native files are a dimensional reconstruction from Omron
B036-E1-12 pages 2–5. Manufacturer CAD currently requires a member login; no
account was created. The current product URL redirects to Aratas, formerly
Omron Components. The selected MPN and existing circuit contract stay unchanged.
`source-manifest.json` records the primary URL, PDF hash and dimensional scope;
the full PDF remains outside the repository.

Run `tools/build_evt1_dock_lid_cutoff.py` in FreeCAD, or call:

```python
switch = build(doc, name="LidSwitchA", pose="operating_reference")
```

Each root has five native component Bodies: `...Case`, `...Lever`, `...COM`,
`...NO`, `...NC`. The case uses two Pads and a Pocket for its actual mounting
hole profiles; the three separate straight terminals and lever use native
Sketches/Pads. Profiles are fully constrained. Reuse the builder with a different
root name for the independent second switch. The parent owns placement,
mounting hardware, loom and lid actuator.

The origin is the body centre on the mounting-hole centreline. Length +X runs
from the hinge/COM end toward NC, width is Y and actuator height is +Z. The case
nominal bounds are X±6.4/Y±2.9/Z−1.5..5 mm. Mounting centres are X±3.25. Terminal
centres are X−5.08 (COM), 0 (NO), +5.08 (NC); tips are Z−5.0. Functions are
manufacturer labels, not manufacturer pin numbers. The reference A force point
is X+7.55, from the drawing's 10.8 mm reference past the first mounting centre.
For length +Y in the dock, use a right-handed 90° Z rotation; width then maps
toward −X. No global shell location is frozen by these source files.

The case's small undimensioned reliefs, pin retention scallops, internal plunger,
hinge and bent lever root are omitted. The 12.8×3×0.3 mm straight blade is posed
using a derived root to meet nominal A(X7.55,Z6.8). This is a visible kinematic
reference, **not an OEM hinge or received-part model**. Its parameter can show
the published FP maximum of 10 mm; that is neither the nominal free position
nor an established total-travel limit. Do not credit clearance against omitted
details or internal case/lever geometry.

The hinge-lever operating table specifies OP6.8±1.5 mm, FP maximum10 mm,
OT minimum0.55 mm, MD maximum0.5 mm, operating force maximum0.78 N and release
force minimum0.05 N. There is **no PT specification** for this lever version.
The nearby pin-plunger PT0.5 mm does not apply. No separate absolute RP is
published; RP≤OP+MD≤8.8 mm is a conservative derived bound, and actual RP must
be measured separately. OT minimum means guaranteed available post-OP travel;
it is not a maximum total travel allowance.

Record each received switch's OP and RP independently. A fixed stop cannot
cover the full 3 mm OP tolerance while staying within the only guaranteed
0.55 mm overtravel. The parent is designing individual received-switch
adjustment/compliance. Verify the final setting, deflection, screw locking,
release, closed-lid current and lid-open cutoff on the actual assembly.

The D2F-01 gold-alloy model is rated 0.1 A at30 VDC, with a minimum-applicable-load
reference of1 mA at5 VDC and the datasheet's micro-load qualifications. The
standard selected MPN is not automatically a safety-approved variant. Omron
specifies M2 mounting screws with plain/spring washers and0.08–0.1 N·m torque;
the actual printed mount and hardware still need qualification.

`native-checks.json` records solid validity, exact bounds after coarse
tessellation, real through holes, reference blade-tip checks and saved native
readback for both poses. These checks do not establish received fit, actuator
overtravel, electrical contact performance or a build release.
