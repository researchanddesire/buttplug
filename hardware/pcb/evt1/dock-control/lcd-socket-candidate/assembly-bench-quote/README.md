# Populated JST lid bench quote

Use [JST-lid-populated-bench-quote.zip](JST-lid-populated-bench-quote.zip) for
pre-radio dock bench pricing. It covers one 1.00 mm four-layer lid PCB with
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

The Newhaven **NHD-C12864B2Z-RN-FBW** display with its integral 27-way tail
and the Molex **0151660220** 20-way opposite-face hinge jumper are separate
buys. The Molex is 203 mm stock for the Main J201 to lid J301 bench link.
Confirm pin-to-pin continuity and mark both ends before connecting it.
[Newhaven LCD](https://newhavendisplay.com/128x64-graphic-cog-lcd-fstn-display-with-no-backlight/) · [Molex jumper](https://www.molex.com/en-us/products/part-detail/0151660220)

Ask the assembler to confirm quote-time availability for all eight lines.
For low-quantity orders, DigiKey showed backorder on the TDK
**C1608X7R1E105K080AB** and Murata **GRM155R71C104KA88D** during the review.
Newark and Mouser listed the exact selections. Verify stock at checkout.
[Newark TDK](https://www.newark.com/tdk/c1608x7r1e105k080ab/cap-1-f-25v-10-x7r-0603/dp/05X9853) · [Mouser Murata](https://www.mouser.com/en/ProductDetail/Murata-Electronics/GRM155R71C104KA88D)

Use the separate [bare J302-only quote](../bench-quote/README.md) and [received
fit fixture](../../../../../cad/evt1-assembly/vendor/lcd-socket-replacement/README.md)
to establish display tail numbering, insertion and loaded contact height
before power. The populated lid remains a bench candidate pending received
connector fit, button travel, installed flex and powered display checks.
The [pre-radio Main](../../../dock-main/assembly-quote/README.md) is quoted
separately.

The archive contains the editable native board and local footprint/model
files, Gerbers/drills, IPC-D-356, the original absolute native centroid,
exact order table, both assembly drawings, and hash-bound evidence. The
native check covers 109 physical pads and 812 whole-system terminal
functions. The copper, mask, legend, outline and drill exports match the
bare-board quote's geometry. Regenerate with KiCad 10.0.8.

```sh
python3 export_quote.py --kicad-cli /path/to/kicad-cli
```
