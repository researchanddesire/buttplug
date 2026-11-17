# Populated JST lid bench quote

Use [JST-lid-populated-bench-quote.zip](JST-lid-populated-bench-quote.zip) to
quote the lid PCB linked by the current wired dock assembly. It covers one
1.00 mm four-layer lid PCB with
28 SMT placements on eight exact manufacturer part lines. The assembly has
17 top placements and 11 bottom placements. Use both paste plots and the
centroid's Side column. Positions use the absolute KiCad origin in mm with Y
inverted. Check rotations against the front and mirrored back drawings.
On the front drawing, J302 is the centre socket outline at centroid
X100/Y−86. Its ribbon mouth faces increasing native PCB Y and its pad 1
is at native X93.5/Y86 on the lower-X side. Use the corresponding silk marker
and actual connector identification before assembly.

Include the saved 81 Ø0.20 mm plated vias and four Ø2.30 mm unplated mounts.
Return the finished stackup, thickness tolerance, copper, via plating, finish
and any proposed substitutions with the quote. J302 uses **JST
27FLZ-RSM2-TB** and J301 uses **Hirose FH12-20S-0.5SH(55)**. Preserve the
**Aratas/Omron B3FS-1002P** actuators at all three button positions.
Use a process that keeps liquid cleaning away from the switches.
[B3FS switch specifications](https://components.omron.com/us-en/products/switches/B3FS)

## Display and hinge purchases

Allow one Newhaven **NHD-C12864B2Z-RN-FBW** per dock. Its factory 65 mm,
27-way tail plugs directly into **J302**. For the first article, retain the
exact bottom-contact JST **27FLZ-RSM2-TB (LF)(SN)** and identify the LCD and
socket lots. Ask the supplier to confirm the tail fit in writing or provide
matched samples. Both drawings allow 0.30 ± 0.03 mm finished tail thickness.
Verify the other tail dimensions on the exact received pair.
[Newhaven LCD drawing, p. 4](https://newhavendisplay.com/content/specs/NHD-C12864B2Z-RN-FBW.pdf) · [JST FLZ catalog, pp. 1 and 4](https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf)

| J302 mating dimension | Newhaven LCD tail | JST FLZ lead drawing |
| --- | --- | --- |
| Finished width | 14.00 ± 0.20 mm (13.80–14.20 mm) | 14.00 ± 0.05 mm (13.95–14.05 mm) |
| Conductor width | 0.30 mm nominal | 0.35 ± 0.04 mm |
| Exposed conductor length | 3.00 ± 0.20 mm | 3.00 mm minimum |

If the supplied combination falls outside the JST drawing, obtain a written
mating exception for those dimensions before committing a larger lot. On the
unpowered first article, record loaded copper height and insertion stop,
verify the latched tail seats squarely, and map all 27 contacts using a known
test tail. Check continuity from J302 pins 13 (VDD) and 23 (read held high)
to the 3.3 V rail and from pin 14 to ground on the unpowered lid PCB before
inserting the LCD. [Received-fit method](../../../../../cad/evt1-assembly/vendor/lcd-socket-replacement/README.md) · [Installed fold and shim](../../../../../cad/evt1-assembly/evt1-wired/README.md#display-stack-and-hinge-flex)

The separate **20-way J201–J301** link uses Hirose FH12 sockets at both ends.
Use the 203 mm Molex **0151660220** jumper for exposed-board bring-up. For
the closed dock, request the custom opposite-face flex with a 25 mm lateral
offset. [Molex jumper](https://www.molex.com/en-us/products/part-detail/0151660220) · [Installed flex feasibility ZIP](../../../../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/display-flex-feasibility/Compass-EVT1-Display-Flex-Feasibility.zip)

Ask the assembler to confirm quote-time availability for all eight lines.
For low-quantity orders, DigiKey showed backorder on the TDK
**C1608X7R1E105K080AB** and Murata **GRM155R71C104KA88D** during the review.
Newark and Mouser listed the exact selections. Verify stock at checkout.
[Newark TDK](https://www.newark.com/tdk/c1608x7r1e105k080ab/cap-1-f-25v-10-x7r-0603/dp/05X9853) · [Mouser Murata](https://www.mouser.com/en/ProductDetail/Murata-Electronics/GRM155R71C104KA88D)

Use the separate [bare J302-only quote](../bench-quote/README.md) if a dedicated
socket fit sample is needed. The populated lid can be quoted independently.
The [wired Main](../../../case-telemetry-study/wired-main/README.md) has its own
layout and release work. Received connector fit, button travel, installed flex
and powered display checks are pending.

The archive contains the editable native board and local footprint/model
files, Gerbers/drills, IPC-D-356, the original absolute native centroid,
exact order table, both assembly drawings, and hash-bound evidence. The
native check covers 109 physical pads and 812 whole-system terminal
functions. The copper, mask, legend, outline and drill exports match the
bare-board quote's geometry. Regenerate with KiCad 10.0.8.

```sh
python3 export_quote.py --kicad-cli /path/to/kicad-cli
```
