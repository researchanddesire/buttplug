# JST lid PCB for unpowered display fit

Quote three bare boards using [the Gerber and drill ZIP](JST-lid-bench-gerbers.zip).
Use a finished thickness of 1.00 mm and four copper layers in this order:
F.Cu, In1.Cu, In2.Cu, B.Cu. Ask the fabricator to confirm the proposed
stackup, 81 plated Ø0.20 mm vias and four unplated Ø2.30 mm mounting holes.
Measure the received PCB thickness before setting the fixture shims.

On the bench, populate J302 only with JST **27FLZ-RSM2-TB**. The saved PCB's
shared nets permit comparison with the intended circuit but cannot
independently isolate every socket pin. Map the marked end using a
known-numbered 27-way test tail and an isolated connector test fixture.
The [FreeCAD fixture and measurement procedure](../../../../../cad/evt1-assembly/vendor/lcd-socket-replacement/README.md)
cover the actual 65 mm Newhaven ribbon, insertion stop, loaded copper-face
height and PET shims. Keep the fit trial unpowered.

The ZIP contains four copper layers, solder masks, legends, board outline,
Gerber job and separate plated/unplated Excellon files at the same absolute
origin. [Source and file hashes](manifest.json), [KiCad 10.0.8 DRC](drc.json)
and [drill report](drill-report.txt) identify the exact export. Production
stackup, complete populated lid fit and powered display are pending.
