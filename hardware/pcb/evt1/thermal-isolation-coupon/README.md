# Compass EVT1 thermal isolation comparison coupon

This 48 × 30 mm standalone coupon compares two 6 × 6 mm pad sites. Site A keeps the laminate intact with a local copper-pour keepout. Site B uses the same keepout and a routed 1.2 mm-wide cavity around the sensor head and most of its neck. The neck is nominally 1.2 mm wide and 8.0 mm from the head shoulder to the end of the route. Inside corners have 0.5 mm nominal radius. The 7.2 × 8.0 mm head supports the nominal pad footprint. Both sensors and their equal-length 0.15 mm routes sit on B.Cu. The part is Vishay NTCS0402E3103FL1T. The land pattern matches Vishay's reflow dimensions. [Vishay part data](https://www.vishay.com/docs/29003/ntcs0402e3t.pdf) · [Mounting and solder pads](https://www.vishay.com/docs/29224/handlmount-ntcssmdntctherm.pdf)

| Site | Sensor center, PCB coordinates | Manual lands | Population |
|---|---|---|---|
| A, intact laminate | (12.0, 11.5) mm | J901.1 sense and J901.2 return | TH901 on B.Cu |
| B, routed | (36.0, 11.5) mm | J902.1 sense and J902.2 return | TH902 on B.Cu |

The pins are electrically independent. TP901 anchors In1, In2 and B ground pours through one plated via. It can float during resistance measurements. Each sensor has its own return and neither return connects to TP901. The fixture holes are 2.2 mm nominal at (3.0, 27.0) and (45.0, 27.0) mm. Fixture loads belong at the base of the board.

## Fabrication input

Submit `thermal-isolation-coupon-fabrication.zip` as the Gerber and drill archive. Specify four-layer FR4, **1.0 mm finished thickness**, ENIG and **35 µm nominal finished copper on all four layers**, matching the active flange stack request. The nominal dielectrics are 0.10 mm / 0.64 mm / 0.10 mm. Ask the board shop to confirm the stack and the 1.2 mm isolation cavity with the 0.5 mm corner radii before releasing fabrication. The interior closed shape is unplated through routing from the Edge.Cuts Gerber. The separate NPTH drill contains two fixture holes. Keep the two thin traces at least 0.25 mm from the routed edges. CAM must preserve the neck and cavity as drawn. An example board shop lists a 1.0 mm minimum non-plated slot width. [Fabrication capability reference](https://jlcpcb.com/capabilities/Capabilities)

For SMT assembly provide `assembly-parts.csv` and `placements.csv`. Populate TH901 and TH902 only. The position file follows the native KiCad bottom-placement convention, with negative Y coordinates relative to the Gerber origin. J901/J902 are hand-wired lands and TP901 is a bare plane anchor. Use a supporting carrier during assembly and handling. Receive one bare witness board to inspect routed width, the neck and the mask openings before handling an assembled coupon.

## Measurement

Use the two sites with the same dry inert pouch surrogate, pad material, actual gap and pack-facing surface temperature. Clamp the common base against the same temperature-controlled fixture. Measure the PCB temperature beside each neck root and the pouch surface under each site. Compare settled resistance-derived temperatures and transient response while holding the surrogate at 0 °C and heating the board base to 20 °C. Include the reverse gradient with a warmer pouch surrogate. The preliminary signed error allocation is 1.5 °C, so 7.5% PCB coupling alone would consume that budget in the 20 °C gradient. Record contact footprint, drift, lifted-pad behavior and neck deflection. Prevent pad material from bridging the routed gap to the surrounding board. Use fixture stops to carry the closure load. Measure pad contact force and neck deflection. Keep compression off the thermistor body. If the head needs a backing support, use the same support at both sites and characterize the extra heat path it introduces.

The test can compare isolation in a controlled fixture. The actual flange still needs its own thermal and electrical cutoff checks with the seated stack, including the pack-to-PCB gradient and possible pad contact loss. [Vishay mounting load guidance](https://www.vishay.com/docs/29224/handlmount-ntcssmdntctherm.pdf)

## Verification

The saved board passed the KiCad 7.0.7 Python DRC with zero violations, zero unconnected pads and zero footprint errors. Gerbers, separate PTH and NPTH Excellon, and the bottom placement CSV were exported from that board with KiCad 7.0.7. A saved-board readback verified a closed routed loop, the four separate sensor nets and no GND fill at the sampled locations across either pad footprint. Supplier CAM, assembly and thermal performance remain unverified. The local `ThermalCoupon.pretty` library is bound through `fp-lib-table`.
