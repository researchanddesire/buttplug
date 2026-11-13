# Separate JST LCD connector candidate

`dock-lid-jst-candidate.kicad_pcb` replaces only J302 with JST 27FLZ-RSM2-TB.
All 28 electrical references, 109 physical pad instances and 128 logical lid
terminals retain their native nets/functions. The complete derived hierarchy
retains all 234 references and 812 terminal functions. Native KiCad10 checks
have zero DRC violations/unconnected items and zero complete-system ERC
findings, with the normally ignored diagnostics enabled and no exclusions.

The five fixed button/socket/hinge XY placements, four Ø2.3 mounting holes,
outline, R3 hardware zones and central FPC corridor are unchanged. The JST
27×0.35×1.10 mm signal lands retain their original 0.5 mm-pitch centres.
Two 2.1×2.1 mm mounting lands move to native (±8.75,+1.25). To clear the
longer signal lands, one existing 3V3 via moves from dock (6.8,114.825) to
(6.9,114.825), with its five incident track endpoints; all other copper
objects remain unchanged. Existing zones were refilled. No general reroute,
passive relocation, circuit change or power flag was introduced.

`native-checks.json` binds saved board, XML, full-system ERC and libraries.
`check_candidate.py` independently verifies every actual pad/net, fixed
placement, keepout, unchanged copper object and both XML terminal graphs.
The full-system snapshot derives from the frozen dock hierarchy; only J302
part/symbol/footprint metadata changes. The standalone lid retains the same
two un-driven supply diagnostics as its original leaf; the complete source
hierarchy supplies those rails and is the ERC acceptance context.

The original routed-lid and its Molex model remain read-only. The preserved
negative Molex section/height audit and the new native received-fit fixture
are in `hardware/cad/evt1-assembly/vendor/lcd-socket-replacement/`.

**Mechanical gate remains open.** JST's public catalog does not supply a
loaded contact plane, internal geometry or an explicit number-1 legend.
Newhaven lists this exact bottom-contact mate, but received tail dimensions,
marked-end numbering, full insertion and all 27 path/no-short checks are
required before power. No fabricated cavity/box model is attached to J302.
Other selected package model paths remain based on the parent 3dshapes folder.
The native fixture's 0.10–1.50 mm equal shims are a measurement search range,
not a validated whole-case range. This candidate is not promoted into the
master, does not replace the frozen source schematic, and is not an order or
full MCAD/physical fit release.

The [bare-board bench quote](bench-quote/README.md) uses the saved four-layer
artwork with only J302 populated for the unpowered fit trial.
