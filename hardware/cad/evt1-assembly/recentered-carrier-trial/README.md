# Recentered dock carrier trial

This separate editable FreeCAD assembly moves the upper contact module for the one-flange-PCB study. It preserves the current two M3 feet/axes at X−43/−15,Y19, the wire hood/lacing at X−28 and the rear-retainer screw axes. A parent-approved collar-front exception resolves the actual skin collision described below. It does not alter the master dock, PCB artwork or earlier helpers.

`RecenteredCarrierTrial.FCStd` contains native sketch/pad/pocket carrier and retainer Bodies, selected Mill-Max0906-2 contacts, S-08-03-N magnets, LC014B02S spring reconstructions and selected M3/M2 screw profiles. The original `pcb/PinPCB.FCStd` is an external link, translated to(−6,18.7962,40.3) with Rx−90°. Its four pin axes are X−16/−10/−4/+2 atZ42; actual wire lands areZ43.8. The actual main PCB is used for checks.

The bridge spans X−46..12, rear/frontY16..23.1 andZ17..47. Each metal-face stop is OD2.4/ID1.8, raised0.1mm toY23.2. A separate1.8mm plunger passage connects the2.1mm barrel clearance to the front, retaining a0.5mm supporting web. This preserves0.6mm nominal pin compression; it is not a pin-force, stop-durability or received-tolerance result. Nominal radial head-to-stop margin is(3.175−2.4)/2=0.3875mm before any alignment/part/process error. The carrier face remains0.3mm behind the specified unpressed skin crowns.

The carrier covers both Power/Mode crowns while mated. The no-preload and pressed
keepout checks do not establish finger access, and no button-access holes are
added. Workshop ROM recovery must be qualified by entering download mode off
the dock with the battery supplying power, releasing the controls and then
mating USB. Holding Mode across the raw Power reset and attaching USB later
remain physical EVT tests. With an absent or flat battery, pre-mold J4 service
and its power/recovery procedure remain required release gates.

Magnet centres are(−14.5,24)/(3,21.5) in X/Z, withY19.2..22.2 and0.9mm front wall. Requested keeper fronts areY24.9: nominal magnet-to-keeper axial gap2.7mm. No holding-force or compass-interference result follows.

Install the lower liner and front plug first. Outside the case, prefeed the lacing, solder the actual board/pins and loom, seat the magnets/coils, and close the rear retainer. Lower this preassembled module vertically through the unchanged floor ports, then install the two underside M3 screws. Rear screw driver access is intentionally required before installation. The shifted upper wire lands still need an installed flexible-wire/tie route to the unchanged hood; no free-space line is substituted for that harness.

The unchanged left10×10 collar intersects the preceding liner model; `negative-prefix-findings.json` preserves that failing source-bound result. The approved correction is a local native liner Pocket, RR10.6×10.6,R0.8 centred(−43,19),Z13.0..37.1. It preserves the original floor material below its13.0mm top. The earlier13.1mm-bottom proposal left a0.2mm ledge gap; its measured result is preserved in `liner-relief-13p1-ledged-probe.json`. Final curved-wall, clearance and loading values come from the actual corrected native check.

`negative-skin-collar-findings.json` preserves a second real failure: the unchanged collar fronts atY24 intersected the revised bottom skin by5.2617mm³. The bounded exception trims both collar fronts toY23.2 and adds integral front return skirts, Xcentre±3.6,Y22.0..22.7,Z11.8..13.5. The7×7 feet, screw axes, MainPCB and existing floor apertures stay unchanged. The skirt is0.7mm thick and returns into the aperture; its nominal bottom is1.155mm above the actual MainPCB maximum10.645mm. Rounded-port clearance, actual skin/mating and loading are checked in the report.

Integration API in `tools/build_evt1_dock_recentered_carrier.py`:

```python
part = build(doc, prefix='Recentered')
# part.Carrier and part.Retainer identify the native Bodies.
# Selected hardware sources are a separate hidden group.
doc.saveAs('/absolute/output/path/Trial.FCStd')
pcb_link = add_pin_board(doc, part)  # unchanged source artwork
apply_lower_liner_relief(lower_liner_body)  # parent-owned future master only
```

Run the helper within FreeCAD's Python environment. Optional `--context` and `--device` arguments select explicit saved sources for the checks. `native-checks.json` records the actual source hashes, geometric checks and remaining limits. The shell-prefix context precedes final050 integration unless the report explicitly names a newer source.

The final audit uses `/private/tmp/compass-jobs/candidate050/DockAssembly.FCStd` as complete read-only context, excluding its superseded contact module/device. The early shell prefix ends before the M3 mount features and is unsuitable for the underside-driver check. The frozen nine-body `SingleFlangeExterior.FCStd` and separate `ButtonPressKeepouts.FCStd` provide the revised actual exterior and two pressed keepouts. Images `assembled-preview.png` and `exploded-rear-preview.png` are renders of the native physical parts; the rear view separates the retained back plate by14mm for illustration.

This is an MJF/SLA-oriented nominal design trial, not a manufacturing release. Received dimensions, thin-stop print durability/material creep, tapped plastic fastening, physical loading/tools, magnet/coil forces, installed wires, contact/electrical sealing and optical leakage remain open. No strength, holding, UV containment or physical-fit claim is made.

The inherited LC014B02S visual helix is topologically valid and closed but reports `BOPAlgo GeomAbs_C0` edge/face continuity findings. This is retained explicitly in `body_checks`, with `all_component_BOP_checks_pass=false`; it is not silently counted as clean OEM spring geometry. The new carrier and retainer require clean BOP results.

The exact earlier coil BRep is retained as `selected-coil-source.brp` with a strict import hash and source diagnostic. Saving through a Body may canonicalise its textual BRep representation; source import, topology, area/volume, exact bounds and sampled edge geometry are checked without claiming saved-byte identity. Actual helix bearing/radial distances remain separately measured. Case/motion checks additionally use a conservative annular ID2.0/OD5.2×3.8mm bound around the nominal ID3.85/OD4.57 source helix. This does not replace the native part or qualify a received spring.

The collar change invalidates any automatic transfer of prior floor/source-blocking evidence. The historical seam sweep's14 clear rays remain findings. The new skirt/liner steps are geometry only; fresh complete-assembly ray checks and measured optical leakage remain required. No optical containment or cleaning claim follows from a nominal overlap.
