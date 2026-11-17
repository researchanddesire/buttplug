# One-board USB stack and route review

The routed product puts each 15.895 mm MCU-to-series-resistor span on F.Cu at 0.15 mm width and 0.20 mm minimum edge gap. The short module and resistor escapes remain on B.Cu. In1 provides the primary reference, with a stitched In2 ground reference under the B.Cu escapes. J4 still adds about 14.8 mm of open branch per pin with no service cable fitted. [Routed-pair geometry and checks](../one-board/usb-pair-review.json)

## Earlier trial readback

Readback of the 2026-11-16 17:25 EST trial board, SHA-256 `1d0044db4871c6214252d98787e9340c4fa58afb36c902d8bcd2f1435829a98e`. The values count all planar segments on each net, including service and protection branches.

| Net | F.Cu, mm | In2.Cu, mm | B.Cu, mm | Through vias |
| --- | ---: | ---: | ---: | ---: |
| `USB_DM` | 14.493 | 13.504 | 3.290 | 4 |
| `USB_DP` | 18.195 | 13.511 | 3.290 | 4 |
| `USB_DM_CONTACT` | 51.416 | 0 | 5.378 | 3 |
| `USB_DP_CONTACT` | 51.976 | 0 | 4.941 | 3 |

All four nets use 0.15 mm traces. The F.Cu contact run around x84–105 has parallel centerlines at y98.40/98.75, for 0.20 mm edge gap. The long J4 service-branch segments on In2.Cu around x74–85 run at y103.70/105.70, for 1.85 mm edge gap. This earlier snapshot had KiCad rule areas and ground tracks without In1 or In2 reference planes. [ESP32-C3 USB routing guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html)

## Proposed fab stack and stack sensitivity

Quote JLCPCB **JLC3313, four layers, 1.0 mm, ENIG**, with a 90 Ω ±10% differential target. The vendor's 1 mm table shows roughly 0.0994 mm 3313 dielectric, Dk 4.05, 0.7 mm central core, 35 µm outer and 15.2 µm inner copper. The vendor's older design note uses 3.5 mil effective outer dielectric for calculations. Confirm the pressed stack, finished copper and solder mask directly with the fab. The artwork's four nominal 35 µm layers describe a different material request. Check higher-current and thermal routes on the supplied inner copper, along with the finished thickness and interference envelopes. [JLCPCB stack table](https://cart.jlcpcb.com/client/template/placeOrder/impedance.html) · [JLCPCB current calculator notes](https://jlcpcb.com/help/article/user-guide-to-the-jlcpcb-impedance-calculator)

First-order uncoated edge-coupled outer microstrip estimates for 0.15 mm width and 0.20 mm edge gap are 86.7–93.1 Ω over the reported 3313 effective and nominal dielectric separations. The 7628 stack's 7.1 mil effective and 0.2104 mm nominal separations, with Dk 4.6, give about 115–120 Ω. The screen assumes a continuous plane immediately across the outer dielectric. It uses `Z0 = 87/sqrt(Dk + 1.41) × ln(5.98H/(0.8W + T))` and `Zdiff = 2Z0 × (1 − 0.48 × exp(−0.96S/H))`, with `T = 0.035 mm`. This makes 3313 the closer starting point for the existing contact geometry. Solder mask, etch, nearby copper, stack tolerances, pads and vias require the fabricator's solve and a coupon. These values do not apply to the current In2.Cu pair. [JLCPCB calculation inputs](https://cart.jlcpcb.com/client/template/placeOrder/impedance.html)

## Route and order checks

1. Verify the routed pair and its return paths after power routing, plane refill and any vendor-specified width or gap change. Check the CT/TVS/series/module route separately from the J4 service branch. Qualify the service branch in normal USB operation with the connector unloaded. Preserve the antenna's all-layer keepout and inspect the reference plane under both paths once the final stack is selected.
2. Align the KiCad differential constraints with the final vendor width, edge gap and stack.
3. Give JLCPCB the actual Gerbers, reference-layer assignments and permitted geometry adjustments before accepting the quote. Require a fabrication impedance coupon/TDR report for each controlled structure used. Check connector, dock and plug full-speed enumeration, programming/recovery and repeated transfers on assembled hardware. Coupon data alone do not test the actual transitions and the contact/harness path. [ESP32-C3 USB layout](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html) · [JLCPCB impedance guide](https://jlcpcb.com/help/article/user-guide-to-the-jlcpcb-impedance-calculator)

## J4 service branch

With the current placement and power copper held fixed, the product's open J4 branches measure 14.883 mm on D+ and 14.804 mm on D−, including their 1.30 mm B.Cu pad escapes. A bounded search connected the J4 vias to clearance-checked taps on the main pair. The best individual In2 trials measured 14.71 mm D+ and 13.84 mm D− before the B.Cu escapes, and none of the tested routes cleared as a pair. An F.Cu D− trial reached 8.02 mm, while the main D− trace blocked an F.Cu D+ path to the tested taps. The B.Cu routes were obstructed in the tested region. The routed J4 branches remain in the product.

Use the dock with J4 unloaded, then check J4 with the dock host absent. If the installed branch measurably degrades USB, a future board revision can put paired isolation links close to the trunk. Opening those links would remove J4 USB access until the links are fitted and would leave its other service pins available. Review both service workflows before implementing that option.
