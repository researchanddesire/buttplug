# Retained dock button trial

This is an **unpowered mechanical coupon**, separate from the dock master. The
native `ButtonMechanicsTrial.FCStd` contains the three original blue crowns,
integral retention skirts, compliant contact shoes and return fingers, selected
switch models, stock springs, and an actual printable roof/retainer/support
fixture. Only bodies whose names end in `FREE_PRINT` are printable caps. The
installed and pressed poses contain assembly deflection/contact and must not be
printed in that pose.

Run `tools/build_evt1_dock_button_mechanics.py` with the native FreeCAD Python
runtime. `--board-z` accepts 60.00–61.00 mm; the starting PCB front plane is
60.50 mm, matching the 1.00 mm shim trial on 61.50 mm roof seats. `--gap` accepts
0.15–0.25 mm. `--switch-height` and `--solder` take received actuator height and
solder stand-off; the exact source switch geometry remains nominal. Changing the
native spreadsheet's BoardZ/RestGap/MeasuredSwitchHeight expressions changes
the integral tip and selected switch height; rebuilding also changes the bench
support. The coupon has no replacement PCB slab: install the actual lid board
in the received-stack trial. Solder stand-off starts at 0.05 mm and must be
measured.

## Force path and geometry

Each crown remains one printed part. Its compliant shoe, small central tip,
serpentine tethers, preload seats, spring guides, retention ring and two return
fingers are integral. There is no loose plunger. A Lee Spring **LC014B02S** coil
sits between crown and shoe. At rest, the shoe bears on seats in its own cap;
the coil preload is reacted internally. The tip starts 0.20 mm above the nominal
released actuator. After engagement, the shoe can move relative to the crown,
limiting the extra force while the crown reaches the external downstop. The
fixed retainer captures the ring against the upstop; roof lands carry the
external downstop load. The return fingers are independent of the force-limiting
coil.

The cap centres are X−22/0/+22, Y54 mm. Visible crowns remain 14×10/16×9/14×10 mm,
Z70.3–73.0 mm at rest. Their four guide roots stay within each crown's projected
outline. Nominal crown travel is 1.00 mm. The ring is Xlocal±8.8,
Y49.5–56.8; the centre mechanism stays forward of Y57 below Z68.2. Fixed roof
pockets are20.8 mm wide, Y47.6–57.1, Z64–68, to clear the separate cream rails. The reserved
FFC volume is |X|≤7.5, Y≥57.4, Z61.5–68.2. The native check uses actual solids
against that volume. These coupon counterpart features are **not yet merged
into the dock roof/bezel** and do not establish final dock fit.

The saved27-body coupon checks all three variants against the roof and bezel
in both released and pressed poses:21 nominal intersection checks pass. This
does not establish received fit, guide strength or a permissible switch load.

The selected Omron **B3FS-1002P** has operating force 1.47±0.49 N and published
pretravel 0.25 +0.20/−0.10 mm. Pretravel is not an allowable total stroke or
post-click force rating. The detailed source is the existing KiCad community
family STEP, not an OEM motion model. Only the released selected switch is
shown; its body is never translated to imitate actuator depression.

## Selected spring and material

[Lee Spring's current manufacturer catalog](https://www.leespring.com/sites/default/files/2023-03/lee-spring-catalog-us.pdf),
PDF page70/printed68, selects LC014B02 plus S suffix: OD4.57, wire0.36,
free length7.95 and approximate solid height1.96 mm; closed/ground ends.
The catalog's music-wire rate 0.79 N/mm is multiplied by5/6 for stainless,
giving 0.6583 N/mm. S denotes302 stainless, with304 substitution permitted by
the manufacturer. Rate tolerance is±10%; solid reference is +5%. The catalog
does not establish a free-length tolerance for this selection here. The CAD
coil turn distribution is reconstructed, not OEM geometry or a spring analysis.

At installed length4.50 mm the nominal spring load is2.271 N. At3.60 mm it is
2.864 N; this uses72.6% of the nominal free-to-solid deflection capacity. It
leaves1.542 mm above the solid reference including+5%. Catalog tolerances alone
do not guarantee the desired minimum operating load. **Measure the assembled
preload**: accept2.20–2.35 N, tether reaction magnitude≤0.15 N, transmitted force
≤3.20 N over the entire1.05 mm maximum received cap stroke, and no coil binding.
The resulting minimum engagement force allocation is2.05 N, above the1.96 N
switch operating-force maximum. The switch supplier's permissible post-click
load still needs confirmation before powered-device use.

First coupon material is MJFPA12; tough SLA is an alternative with its own
print/post-cure and fatigue trial. The 0.4 mm XY /0.5 mm Z shoe tethers meet only
[HP's general minimum feature guidance](https://www.hp.com/us-en/printers/3d-printers/learning-center/how-to-design-3d-print-model.html).
That guidance does not qualify repeated flexure. Return beams are0.8×0.6 mm,
10.4 mm long; an assumed modulus1.2–2.0 GPa and elementary cantilever strain
estimate are screening calculations only. Powder/resin removal, separation,
creep and fatigue require the actual coupon.

## Received-stack and force trial

1. Print roof, retainer, support, probe puck and the three FREE caps. Record
   process, orientation, postprocessing, material batch and critical dimensions.
   Remove all residue from the shoe/tether gaps. Reject fused, cracked or
   permanently bent fingers. Measure1.00±0.05 mm crown stroke and guide friction;
   adjust the model from measured dimensions rather than forcing a cap through.
2. Use the selected springs. Check identity, OD, free length and solid clearance.
   Install each coil onto the lower guide and compress it beneath the crown's
   upper guide using a bench fixture. The free cap leaves a2.8 mm lateral
   insertion window between pilots; compress the coil to≤2.6 mm for insertion,
   then release onto both pilots. Check for insertion set/damage; this brief
   assembly compression is separate from the normal3.6 mm minimum working
   length. Do not pry on the thin shoe tethers. With
   the cap on its internal shoe stops, use a calibrated load cell and micrometer
   to measure shoe lift force and the entire extra-compression curve. Accept the
   bounds above. Log each spring/cap pairing; do not assume nominal free length
   gives the required preload.
3. Assemble cap/roof/retainer with **no electronics**. Candidate coupon hardware
   is4×[Accu SIK-M2-6-A2](https://www.accu.co.uk/phillips-countersunk-screws/65898-SIK-M2-6-A2)
   in M2 pilots and4×[SIK-M3-12-A2](https://www.accu.co.uk/phillips-countersunk-screws/65913-SIK-M3-12-A2)
   in M3 pilots; pilots require
   tapping/received-part torque trials. Support columns set the fixture datums.
   The lower plate's Ø4 probe ports admit the printed puck on an external load
   cell. The puck is a real test anvil, not a switch proxy.
4. At PCB front datums60.00/60.50/61.00 and measured stand-off, set an instrumented
   anvil to the **received** released-actuator height. Measure free gap0.15–0.25 mm,
   shoe force versus crown displacement, no rest preload, maximum force≤3.20 N,
   internal shoe travel and downstop engagement. Continue the finger load to20 N
   against the shell stop, confirming it does not increase anvil force above the
   accepted bound. Also apply a10 N inert pull to the crown and check upstop
   retention without escape. These are proposed coupon proof loads, not
   demonstrated product strength. Reject cracking, a permanent set, a slipped spring or any
   ring escape. Minimum final return force allocation is0.04 N; guide friction
   must be≤0.02 N, with full return after release and after off-axis presses.
5. After the permissible switch load is confirmed, install three **unpowered**
   received B3FS-1002P switches on the actual board and use a continuity logger.
   Confirm no rest closure, closure before the external downstop, clean release,
   and the same1.05 mm maximum travel at all three measured stack datums. Include
   edge/corner presses without rubbing or side loading. Check board bow, actual
   actuator height and supplier tolerances; adjust tip length for the chosen
   stack. Never infer safe overtravel from a successful continuity test.
6. Cycle a coupon1000times, then10000times if it passes, at intended dry-storage
   temperature endpoints. Repeat gap, return, load and20 N stop measurements;
   inspect fingers/tethers/spring seats for wear and permanent set. These counts
   are EVT screening targets, not a lifetime rating. Repeat on aged/cleaned
   material before selecting a production process.

No print, received hardware, force curve, fatigue, supplier load approval or
powered result is claimed. This directory does not authorize ordering or a full
product manufacturing release.
