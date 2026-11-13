# Buttplug Compass

For AJ and other collaborators: start with [the checkpoint handoff](COLLABORATION.md).
It distinguishes the saved threaded-stub CAD from unresolved locking/tooling choices.

Current direction: **[manufacturing design proposal](developer-docs/docs/prototype-build-handoff.md)**
and **[native mechanical study](hardware/cad/manufacturing-layout/README.md)**.

Four main mechanical pieces: turned body with indexed collar flats, turned motor/thermistor cap,
flange tray and rear plastic half. The 15 mm neck remains. Both flange halves
close around the installed lower body before a continuous silicone overmold.
A separate [inert casting kit](hardware/cad/manufacturing-layout/overmold-trial/README.md)
now has native skin/split-tool CAD and three print STLs; contact/button tooling
and physical process trials remain open. Standard insulation/foam remain.
A protected-pack RFQ is defined; supplier approval and retention remain open. The product BOM stays human-owned.

![Current manufacturing layout](developer-docs/docs/assets/manufacturing-layout.png)

The cap has an integral motor pocket and a potted tip thermistor. The body
PCB is foam-supported in the cap as a prewired module; flange tails connect
only after it is threaded into the body. A short M18×1 rear stub and thin nut
clamp the flange tray against the body shoulder; collar flats resist twisting.
A bonded silicone cuff covers the wet-side joint. Nut locking remains open.
The [overmold and Pocket Neopet-style cradle concept](hardware/cad/manufacturing-layout/concepts/overmold-cradle/README.md)
covers assembly/tooling, USB storage-dock layout and an optional UV-C investigation.
The [dock/interface prototype](hardware/cad/manufacturing-layout/charging-dock/README.md)
now adds native clamshell/contact/mask CAD, routed cradle electronics and an
[unpowered print kit](hardware/cad/manufacturing-layout/charging-dock/Dock-Interface-Print-Kit.zip).
The separate [device-board fit checkpoint](hardware/cad/manufacturing-layout/evt1-integration/README.md)
fits actual PCB outlines and an integral compass mount. Sealed feedthrough
qualification and physical trials remain open.
The cover screws now close plastic only. See the [DFM review](hardware/cad/manufacturing-layout/DFM.md)
for machining sources, tool/setup candidates and tolerance budgets.

**Status:** mechanical DFM study, not a build/tooling release. The old P1 fit
kit is superseded. All five PCBs pass native DRC/pad parity and EVT1 NTC/compass
firmware builds pass. Exact PCB parts and assembly quotes are prepared. Supplier pack approval,
non-PCB hardware, cap thread/seal detail, nut lock, loom,
boot/buttons, factory compass calibration and physical qualification remain open.
No fabrication, powered operation, seal or wear result is claimed.

| Purpose | Source |
| --- | --- |
| Current design and remaining work | [Proposal](developer-docs/docs/prototype-build-handoff.md) |
| Native CAD, four main STEP parts, nut envelope and two plastic study STLs | [Manufacturing layout](hardware/cad/manufacturing-layout/README.md) |
| Actual three-board fit, integral compass bosses and updated plastic prints | [EVT1 device integration](hardware/cad/manufacturing-layout/evt1-integration/README.md) |
| Proposed assembly | [Assembly guide](assembly-docs/assembly-guide.md) |
| Prior circuit/routed-board reference | [R35F project](hardware/pcb/pack-pigtail-r35/candidate-f/system-r35.kicad_pro) |
| Current five routed PCBs, source-bound checks and fabrication quotes | [EVT1 electrical](hardware/pcb/evt1/README.md) |
| Existing bench code and compatibility limits | [Firmware](developer-docs/docs/firmware.md) |
| Requirements | [PRD](developer-docs/docs/prd.md) |
| Human-owned BOM | [hardware/bom.csv](hardware/bom.csv) |

Keep the seven current developer pages updated in place. Use Git history and
[targeted archived studies](developer-docs/docs/archive/index.md) for earlier work.
No auto-commit or publication. See [developer site setup](developer-docs/README.md).

Forked from [researchanddesire/rad-project-template](https://github.com/researchanddesire/rad-project-template).
Repository: `researchanddesire/buttplug`; the local folder keeps its earlier name.
Publication and licenses remain pending. See [LICENSE](LICENSE).
