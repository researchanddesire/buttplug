# LCD fit with the lid board lowered 0.50 mm

The [hinge flex study](../dock-harness-trial/shared-hinge-review/display-flex-feasibility/README.md)
found that a PCB top at Z60.00 mm cleared the modeled lid hardware with
the expanded hinge-flex envelope. A 1.50 mm equal shim stack gives that
position. This follow-up holds the screen at Z68.80 mm and checks whether
the display's separate 65 mm ribbon can still reach J302. The 1.00 mm shim
stack stays in the saved assembly. [Editable FreeCAD assembly](DockAssembly-JST-Review.zip)

At Z60.00 mm, let `H` be the measured copper-face height above the PCB
and `Ystop` the measured ribbon tip coordinate in the fully loaded socket.
The native tangent line–arc–line fold gives the following parameters in mm.

```text
R = (7.70 − H) / 2
lead-in = (130 − π × R − Ystop) / 2
```

The [native sweep](coupled-lid.json) checks 20 combinations of five trial
heights from 0.70 to 1.70 mm and four trial stops from Y110.575 to Y113.300.
All combinations clear the modeled static obstacles and four rigid center
button translations from 0.25 to 1.00 mm. Minimum center button gaps below
are across those four sampled translations. The distances are nominal.

![Center-button clearance by measured socket height and insertion stop](CoupledLidClearance.png)

| Loaded copper height | Bend radius | At Y110.575 | At Y111.575 | At Y112.575 | At Y113.300 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.70 | 3.50 | 0.435 | 0.935 | 1.435 | 1.798 |
| 0.95 | 3.375 | 0.364 | 0.864 | 1.364 | 1.726 |
| 1.20 | 3.25 | 0.293 | 0.793 | 1.293 | 1.655 |
| 1.45 | 3.125 | 0.221 | 0.721 | 1.221 | 1.584 |
| 1.70 | 3.00 | 0.150 | 0.650 | 1.150 | 1.512 |

For example, a measured `H` of 1.20 mm and `Ystop` of 112.575 mm would
set R3.25 and a 3.607 mm lead-in. The final position depends on both
measurements. Use the [received-fit fixture](../vendor/lcd-socket-replacement/README.md)
to establish the actual loaded plane, stop, exposed copper overlap and all
27 electrical paths.

1. Register the board plane and J302 footprint to the fixture before loading
   the tail. Photograph the PCB datum and a transverse witness mark on an
   unpowered test tail. Measure the distance from the mark to its physical tip.
2. Fully seat and latch the witness tail. Measure the board-to-copper-face
   height on the straight exposed tail next to the mouth, checking it at two
   points for bow. Determine `Ystop` by adding the measured mark-to-tip
   distance to the installed mark Y. Use a witness of matched thickness and
   repeat the measurements with the actual display tail where accessible.
3. Repeat the native check at the measured pair of dimensions and verify the
   neutral fold, actual button stroke and straight insertion on the dry
   assembly. Record all four shim stacks and check electrical continuity
   again after installation.

The 20 native samples do not validate the actual
socket interior, a continuous tolerance region, flex strain, moving button
mechanics or the combined hinge sweep. Confirm Newhaven's bend guidance
for the received display tail before setting the radius.
[JST FLZ catalog](https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf) ·
[Newhaven display specification](https://newhavendisplay.com/content/specs/NHD-C12864B2Z-RN-FBW.pdf)

Replay `check_coupled_lid.run(dock_path, output_path)` inside FreeCAD 1.1.4
with `tools/evt1_brep_checks.py` on the import path and beside the replay
script. Use a scratch extraction of the linked assembly.
