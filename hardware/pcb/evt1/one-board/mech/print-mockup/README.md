# Compass full-size print mockup

Open **Compass-Mockup-P2S-0.4mm.3mf** in Bambu Studio. The plate contains
one Half A, one Half B and three alignment pins, already placed for printing.
Select your actual PLA/AMS slot, slice the plate and review it before printing.
The project uses the Bambu P2S **0.4 mm, Standard flow** printer profile,
Generic PLA and the textured PEI plate.

| Setting | Saved value |
| --- | --- |
| Layer height | 0.16 mm; first layer 0.20 mm |
| Walls | 3 |
| Infill | 15% gyroid |
| Top / bottom | 5 layers each |
| Supports | Off |
| Brim | Outer only, 3 mm |
| Scale | 100%, millimetres |

Bambu Studio 2.8.2.61 displayed **Slice ok** for all five objects on this plate:
125 layers, approximately **50.00 g PLA** and **2 h 22 min** including preparation.
These are slicer estimates. No print was sent and no physical print is verified.

The mockup is about **124.5 mm long**, with a **59.2 × 40.0 mm** outside flange.
It follows the current compact one-board exterior, including the button domes,
arrow, recessed logo and contact window. The window has a recessed solid floor;
separate conductive contacts are omitted. The body, flange and buttons form
one rigid appearance model when the halves are joined. It is an inert model for
dry handling and size comparison.

Print both halves on their broad, flat split faces. The individual STL files
already have that orientation; Half B is turned over relative to the assembly.
Print **three** copies of `MockupAlignmentPin.stl` if using the individual files.
Remove the brims, clean the flat faces and dry-fit the pins before gluing the
halves. Each pin is Ø3.0 × 8.0 mm with chamfered ends; each mating hole is
Ø3.3 mm × 4.3 mm deep. Check the fit before applying glue; printer tolerances
have not been measured.

`Compass-Mockup-Print-Kit.zip` includes the 3MF, STLs, checks, preview and
editable FreeCAD assembly in `CAD/MockupAssembly.FCStd`. Keep all four
FCStd files together: the assembly uses relative links to its component bodies.
Each half has an editable alignment-hole sketch and pocket; the pin has an
editable sketch and revolution. Matching STEP exports are included.

In the repository the native files and `mockup_*.py` generators are directly
in `mech/`. The production parts and PCB are unchanged. The filled interior is
specific to this mockup; no internal fit is implied. A 0.2 mm axial band at the
flange's cap/prism seam is replaced by a ruled loft to avoid a source-surface
meshing gap (about 0.20 mm³ volume difference). Mesh chord tolerance is
0.025 mm. Every STL is one closed component with no non-manifold edges.

Rebuild the parts with FreeCAD console, in order:

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(open('mech/mockup_half_a.py').read())"
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(open('mech/mockup_half_b.py').read())"
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(open('mech/mockup_alignment_pin.py').read())"
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(open('mech/mockup_assembly.py').read())"
QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/mockup_color_step.py
python3 mech/mockup_package.py
/Applications/BambuStudio.app/Contents/MacOS/BambuStudio \
  --load-settings 'build/mockup/machine.json;build/mockup/process.json' \
  --load-filaments build/mockup/filament.json --arrange 0 --orient 0 \
  --export-3mf "$PWD/mech/print-mockup/Compass-Mockup-P2S-0.4mm.3mf" \
  build/mockup/mockup-plate-input.3mf
```

The console avoids this macOS build's crash when creating live pocket view
providers offscreen. The last FreeCAD GUI script colours and validates the
saved STEP copies. Logs and intermediate geometry stay in `build/mockup/`.
After rebuilding, open the regenerated 3MF and repeat the Studio slice check.
