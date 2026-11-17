# Compass EVT1 one-board connector fit

These editable FreeCAD studies contain the geometry used to check the revised
motor connector (J3) and pack-temperature connector (J8). Each native opens
with its geometry embedded. The reports identify the matching PCB revisions
by SHA-256 and record the saved solid readback.

- [Compact J3 and J8 rework](Compact%20J3%20and%20J8%20rework.FCStd) uses
  the first-article flange and the [Compact PCB](../../../pcb/evt1/one-board/compass-one-board.kicad_pcb).
  The [fit report](compact-fit.json) covers seated housings and 3 mm axial
  withdrawal with the other connector's leads dressed. The minimum modeled
  withdrawal gaps are 0.450 mm for J3 and 0.200 mm for J8. The [wire study](wire-geometry.json)
  records four nominal routes to the neck seam. J2 and J4 service reservations
  are visible in the `ServiceAndInsertionVolumes` group.
- [Master Bench J8 edge access](Master%20Bench%20-%20J8%20edge%20access.FCStd)
  uses the [Master Bench PCB](../../../pcb/evt1/one-board-dev/compass-one-board-dev.kicad_pcb).
  The [access report](bench-access-check.json) covers both seated cable housings,
  their 3 mm withdrawal and seated lead geometry. The closest housing gap is
  0.235 mm at the board. J112 and two inductors outside the checked region
  have no resolved bodies in this model.

Both models use nominal housing envelopes from the [JST SH catalog](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf).
Check contact engagement, loom handling, bend limits, connector retention,
extraction tool access and assembled tolerances on the received hardware.

The earlier [body pack study](one-board-cad/Compass%20EVT1%20-%20One%20Board%20Study.FCStd)
preserves the nominal and growth envelopes used for the [TH3 fit report](../../../pcb/evt1/one-board/pack-monitor-pose-fit.json).
The report can be rerun in a FreeCAD Python environment using
`check_pack_monitor_pose.py` in the Compact PCB directory, with the body pack
study as the first argument and a scratch report path as the second. The
[first-article assembly](first-article-cad/Compass%20EVT1%20-%20First%20Article.FCStd)
preserves the geometry for the [earlier flange fit report](../../../pcb/evt1/one-board/first-article-assembly-fit.json)
and the frozen reference for the updated Compact study above.
