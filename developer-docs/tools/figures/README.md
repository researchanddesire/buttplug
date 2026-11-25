# Docs figures

Run the figure commands from this folder. They read CAD from the repository
root unless `COMPASS_DESIGN_ROOT` points to a separate design checkout. Intermediate files go to
`developer-docs/.cache/figures/` (ignored by Git); finished images go to
`developer-docs/docs/assets/`. Assembly steps and PCB figures live in
`assembly-docs/assets/` and are also available in the developer site.

Requirements: FreeCAD 1.1 (`/Applications/FreeCAD.app`), Blender 3.5+
(`blender` on the PATH), Inkscape 1.2, KiCad CLI, and macOS `sips` for JPEG.

| Step | Command | Output |
| --- | --- | --- |
| Device meshes | `QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD export_device.py` | `.cache/figures/device.glb`, `device-cutaway.glb`, `screws.glb` |
| Dock meshes | `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(compile(open('export_dock.py').read(), 'export_dock.py', 'exec'), {'__file__': 'export_dock.py'})"` | `.cache/figures/dock.obj`, `dock-parts.json` |
| Device renders | `./render_all_device.sh`, or `blender -b --python render_device.py -- <shot>` | `.cache/figures/raw/<shot>.png` + anchor JSON |
| Dock renders | `./render_all_dock.sh` | `.cache/figures/raw/dock-<shot>.png` |
| Labels | `python3 make_device_figures.py`, `python3 make_dock_figures.py` | `docs/assets/device/`, `docs/assets/dock/`, `assembly-docs/assets/assembly/` |
| PCB | `python3 make_pcb_figures.py` | `assembly-docs/assets/pcb/pcb-*.jpg` |
| Sections | `freecadcmd -c "exec(compile(open('extract_sections.py').read(), 'extract_sections.py', 'exec'), {'__file__': 'extract_sections.py'})"` | `.cache/figures/drawings/geom.json` |
| Drawings | `python3 make_drawings.py` | `docs/assets/drawings/*.svg`, `.pdf`, `.png` |
| Seal diagrams | `python3 make_seal_figures.py` | `docs/assets/seals/*.png` |
| Block diagram | `python3 make_block_diagram.py` | `docs/assets/device/device-blocks.svg` |

Add `preview` after a shot name for a quick low-resolution render. Shots,
camera directions, part offsets and label anchors are defined in
`render_device.py` and `render_dock.py`; label text is in the `make_*_figures.py`
files. Re-run the meshes, renders and labels after any CAD change.
