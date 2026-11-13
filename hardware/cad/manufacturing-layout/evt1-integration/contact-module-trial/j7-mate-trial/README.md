# Selected SH10 mates and new interboard wire forms

This separate native trial uses the frozen single-board device geometry and preserves the existing body PCB, body J6 and the original 39-position study. It exposed an assembly obstruction that a bare-header fit check missed: the J7 mating housing could sit in the original placement, but straight removal hit U75 and U71.

The authorized repair is U75 at product X6.3/Z9 and U71 at X−1/Z−7, on the routing candidate only. All four OD4 contact-reaction posts remain. `combined-review.json` binds the exact disposable native and pad/material checks. The original study and the portable nine-body exterior are unchanged. Final routed-candidate MCAD must bind the current full product native separately.

- `SingleFlangeJ7MateTrial.FCStd`: public-drawing reconstruction of two JST SHR-10V-S housings and twenty SSH-003T-P0.2-H contacts, with immutable actual mechanical context. The original 0..6 mm sweep records the obstructions; it is deliberately not labeled a pass.
- `CombinedClearanceTrial.FCStd`: the two authorized internal moves. All 59 sampled poses pass: withdraw3.25 mm axially from J7, then8 mm along the PCB normal; reverse to mate. Native actual pads, selected models and manufacturer maximum-material profiles are tested. U75's maximum profile is0.800 mm from the Tray and its pad projection0.500 mm from the actual posts. U71's maximum profile has0.750 mm separation from the housing's nominal Z edge. Source placement DRC is independently checked by the PCB owner.
- `SingleFlangeLoomTrial.FCStd`: ten separate native circular wire sweeps, their editable centreline definitions and the selected mated connector geometry. Source numeric pins are1:1, including pin10 TIP_EXC_EN. No USB pair passes through this loom.

J7 uses the exact proper source transform: the ten circuits run along product Z; pin1 is Z+4.5 and pin10 is Z−4.5. Its wire-exit plane is X−2.525. J6 pin1 remains X−4.5 and pin10 X+4.5; the selected-model mate's exit plane is Y31.525. The wire-centre height1.51 mm is a first-article fixture parameter inferred from the drawing, not a controlled JST exit tolerance. Verify the received housing/contact seating before accepting a final form.

## Source and geometry limits

JST's public catalog specifies the housing11 mm width,5 mm length,2.8/2.1 mm stepped profile and6.25 mm total side-entry assembly. The actual selected header model has a socket mouth at local v−2.475 and stop at v+0.525. Thus3.00 mm nominal disengages the inserted body; the trial adds0.25 mm before the normal withdrawal. The same3.25 mm body-J6 disengagement passes. An unnecessary5.5..6 mm continuation would reach the body neck taper; do not substitute that longer motion.

The native housings have stepped profiles and separate ten-channel pockets. They are reconstructed from public manufacturer drawings, not OEM STEP. Undocumented channel/lance details, contact wall thickness and seated-terminal depth remain illustrative; they do not qualify internal contact mechanics. JST's OEM CAD link currently requires company/contact data and email delivery with restrictive redistribution terms. No form was submitted. `selected-parts.json` records exact orderable selections and source hashes.

The thin-tip access trial uses the primary Ideal-Tek2AE.SA.0 tip section1.50×0.13 mm with an8 mm access extension. The whole shank, jaw opening, grip force and safe connector handling are not qualified. Grip the housing; never use the wires as a pull handle. Verify the real tool and received part before loading electronics.

## Wires and assembly

Retain Accu-Glass100690 stranded28 AWG. The catalog nominal OD is0.508 mm; this form requires received OD0.40..0.60 mm. Its published bend figure is3.302 mm; the candidate uses4.5 mm circular turns and retains at least4 mm sampled centreline radius. Native paths are59.637..60.845 mm of exposed insulated wire. Ten120 mm blanks remain starting stock, **not finished cut lengths**; actual terminal take-up, strip/crimp dimensions, service slack and first-article trimming determine the final lengths.

All ten native solids and all45 wire pairs pass the fixed-geometry checks. The minimum nominal wire surface gap is only0.050 mm; this is not a tolerance or flexible-bundle proof. Independent cold readback checks32 valid single-solid Bodies, all wire volumes/lengths/bounds and the physical numeric endpoint order. Analytical circular-tube volume differs by at most0.0063% in the native volume integration; the independent sanity bound is0.01%, while saved source bounds/volume and endpoint comparisons remain separate strict checks.

Feed staggered, protected free flange terminals through the neck after the rotating body/cap module is threaded. The eleven-millimetre housing stays loose until then. Populate it in marked numeric order, verify continuity, mate while both rigid flange halves remain accessible, then close the rigid assembly before overall molding. A physical cap/thread/loom trial is still needed; no complete flexible motion or service-slack result is inferred from the static forms.

The old requested pack-disconnect reservation intersects eight of these wires. A separate−6X translation of that loose reservation clears both the wires and fixed parts in this trial. This is **not** a pack-specification or master-placement edit. The next bounded trial must replace the reservation with the selected ACHTP/ACHTR housings and contacts, then add both power leads, four dry NTC conductors, joints and restraint. Factory pack exit geometry and the0.95 mm passage behind the rear stub need actual bend/solid clearance, not a centreline-only claim. `wire-review.json` keeps those gates explicit.

No purchase, source PCB promotion, physical fit, crimp, molding, leak or powered release is claimed.
