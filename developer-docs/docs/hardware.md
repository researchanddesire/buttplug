# Source files

Browse the [hardware development branch](https://github.com/researchanddesire/buttplug/tree/backplane/trial) for the checked-in design sources.

Paths are repository-relative. Use native CAD and KiCad sources for changes;
reports apply only to the revision they bind.

## Device

| Subsystem | Editable source | Evidence / specification |
| --- | --- | --- |
| Integrated PCB | `hardware/pcb/evt1/one-board/compass-one-board.kicad_pro` | Adjacent layout reports; refresh after edits |
| Full assembly | `hardware/pcb/evt1/one-board/mech/compass-device.FCStd` | `device-fit.json`, cutaway/open STEP exports |
| Named mechanical parts | Same `mech/` folder: `compass_datums.py` and one script/native per part | `README.md`, `body-profile.json`, `cap-seal-fit.json` |
| Pack support and wiring | `InternalCradle.FCStd`, `CradleWireGuide.FCStd`, `Internals.FCStd` in that folder | `cradle-fit.json`, `cradle-installation-fit.json`, `internals-fit.json` |
| Pack | `hardware/pcb/evt1/one-board/pack-spec.json` | Adjacent `PACK-RFQ.md`, BC-PACK-EVT1-002 |
| Harnesses | `hardware/pcb/evt1/one-board/build_harnesses.py` | Generated `hardware/cables/evt1/one-board/` |
| Plug firmware | `firmware/` | `platformio.ini`, `main/`, `tests/` |
| Metal drawings | `developer-docs/tools/figures/make_drawings.py` | Sheets in `developer-docs/docs/assets/drawings/` (SVG, PDF, PNG) |

## Dock

| Subsystem | Editable source | Evidence / specification |
| --- | --- | --- |
| Wired assembly | `hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd` | Adjacent `README.md`, linked `pcb/` and `sources/`, fit reports |
| Main PCB | `hardware/pcb/evt1/case-telemetry-study/wired-main/dock-wired-system.kicad_pro` | `active-routing.json`, package/parity records |
| System tracing | `dock-wired-transport.kicad_pro` in that same folder | Shared leaf sheets and system netlist |
| USB host and UI | `dock-firmware/wired-main/`, `dock-firmware/` | Target READMEs, `BRINGUP.md`, build reports |
| Compact dock fit studies | `hardware/pcb/evt1/one-board/mech/CompactDockFit.FCStd`, `CompactMagneticDock.FCStd`, `CompactFlushContactSection.FCStd` | Adjacent fit JSON files and STEP exports |
| Hall cutoff | `hardware/pcb/evt1/dock-safety/wired-hall-head/` | Head, Main receiver and fault-budget studies |
| UV modules | `hardware/pcb/evt1/dock-uv/` | Matched population and power-budget sources |
| Enclosure quote | `hardware/design/evt1-bench-ordering/dock-enclosure/` | Re-export after geometry changes |

## Shared records

- Assembly instructions: `assembly-docs/assembly-guide.md`, also shown in this site's [assembly guide](assembly-guide.md).
- Open questions and next steps: [Project status](status.md).
- Product BOM: `hardware/bom.csv`, human-owned.
- Reviews and physical bench records: existing Compass doc in R+D Drive; identify Git, board and native assembly revisions.
- Images: every render, drawing and diagram on this site is regenerated from the CAD by the scripts in `developer-docs/tools/figures/` (see its README).

Earlier manufacturing, split-board and single-flange studies remain references;
their fit counts and quote packages do not describe the compact device.
