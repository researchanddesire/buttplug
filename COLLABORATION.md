# Collaboration checkpoint

Start with the [developer docs](developer-docs/docs/index.md) for the device,
dock and [project status](developer-docs/docs/status.md). The [source
map](developer-docs/docs/hardware.md) identifies the native projects and reports.

## Current sources

- [Compact device PCB](hardware/pcb/evt1/one-board/compass-one-board.kicad_pro)
  and [FreeCAD assembly](hardware/pcb/evt1/one-board/mech/compass-device.FCStd).
  The existing split-board and single-flange studies are design references.
- [Three-wire pack request](hardware/pcb/evt1/one-board/PACK-RFQ.md)
  BC-PACK-EVT1-002 and [device wiring](hardware/cables/evt1/one-board/README.md).
- [Wired dock assembly](hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd)
  and [compact fit studies](developer-docs/docs/charging-dock.md#compact-fit-studies).
  The wired seat needs a revised carrier and nest for this plug. The compact
  magnetic dock and flush-contact section are separate proposals.

## Next build

Use the [illustrated assembly guide](assembly-docs/assembly-guide.md) for the
unpowered device trial and dock bench sequence. Record the Git commit and
native revision with bench results. Review the [validation
plan](developer-docs/docs/testing.md) before powered bring-up.
