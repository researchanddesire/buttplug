# Selected dock display

`NHD-C12864B2Z-RN-FBW`, Newhaven, reflective FSTN positive 128×64 LCD. This is a **parallel** ST7565R display with no backlight; its 27-way FFC is part of the purchased module.

`NHD-C12864B2Z-RN.STEP` is the manufacturer's 2018 model, downloaded from the official [3D model ZIP](https://newhavendisplay.com/content/3D/NHD-C12864B2Z-RN.zip). It stays as the dimensional reference rather than an authored product part. Manufacturer CAD/rights remain with Newhaven; publication permission has not been established.

`tools/build_evt1_dock_display.py` in its default `ffc_pose="flat"` reconstructs the five source solids as editable Sketcher/PartDesign pad bodies, including the factory flat FFC, stiffener and all 27 contact lands. Four shapes match the OEM solids to numerical precision. The active-area graphic uses the current drawing's 19.8 mm height, replacing the 2018 model's 19.6 mm height. The optical layers overlap inside the purchased component, as they do in the OEM model; do not run product collision checks between those internal graphic solids.

The returned `App::Part` has its 44×24 viewing-area centre at local XY=0 and the front face at Z=0. The LCD outline spans X=−24..24, Y=−22..14. Its factory flat FFC extends toward −Y to Y=−87. Pin 1 is at X=−6.5 and pin 27 at X=+6.5, on 0.5 mm pitch; exposed lands face +Z.

The current drawing allows 2.1 mm maximum module thickness, whereas the old STEP spans 1.8 mm. The seat must account for **the current 2.1 mm limit**, glass/seat tolerances and compliant support. Nominal source agreement does not qualify a connector, strain relief or received-part fit. The optional installed route below is a candidate geometry study, with bend material limits and full assembly fit still open.

See `source-manifest.json` for dimensions, source revision, pin contract and unresolved manufacturing details. The manufacturer PDF/drawing is not republished.

## Installed FFC candidate

Use `build(doc, ffc_pose="installed", bend_radius_mm=3.0, straight_before_bend_mm=4.0)`. This separates the rear-glass body from the FFC, then builds a fully constrained line–arc–line path and native PartDesign ribbon sweep. Native pockets/pads retain the two 0.3 mm terminal-end corner radii, 5 mm stiffener and all 27 contact lands. No mesh or flat bounding solid stands in for the installed flex.

The 65 mm nominal centreline consists of a 4 mm lead-in toward −Y, a 180° bend of 3 mm centreline radius, and a 51.575222 mm return toward +Y under the display. The inner fibre radius is 2.95 mm. **These radii are design candidates, not manufacturer-qualified bend limits.** The source drawing does not specify installed flex minimum radius or copper stack; supplier and received-part trials must qualify the fold, retention and strain.

The end centre is at local `(0,25.575222,−6.95)` mm. With the assembly window centre `(0,87,68.8)`, the end is `(0,112.575222,61.85)` mm. Contact lands face −Z, the stiffener faces +Z and connector insertion points +Y; a matching bottom-contact 27-way/0.5 mm FFC receptacle is still to select and place. The complete ribbon/terminal bounds are local `X−7..7,Y−29.05..25.575222,Z−7.1..−0.9` mm.

The returned part links an external non-geometric `FFCParameters` object, which keeps editable path drivers outside the component to avoid a FreeCAD parent/child expression cycle. Its `FFCBendCentrelineRadius` and `FFCLeadInLength` drive the native path, rounded tip, stiffener and contacts. `validate_installed(part)` checks the current native BOP validity, 65 mm path, preserved source volume and actual end/bounds. Run it after edits; `InstalledFFCChecks` is a build-time snapshot. Native save/reopen and a 3→3.2→3 mm radius edit have passed batch FreeCAD checks. Final VM assembly collision checks remain separate.
