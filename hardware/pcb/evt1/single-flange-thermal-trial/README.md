# Compass EVT1 single flange / thermal isolation R1

This is a separate first-article variant of the 1.00 mm, four-layer single flange. It places two Vishay NTCS0402E3103FL1T on the battery side and provides four bench-solder lands for their signal and return wires. Each sensor has a local 7.50 × 7.50 mm no-pour window on all four copper layers and two 0.15 mm traces leading to its own wire lands. The laminate is continuous. The In2 3V3 branch moves around the lower window. The existing antenna exclusion, 43 footprint poses, four-contact pattern, board outline and hole centers follow the active PCB. See [source binding](source-binding.json) and [thermal screen](thermal-screen.md). The [standalone A/B coupon](../thermal-isolation-coupon/README.md) compares this type of copper clearance with an 8 mm routed neck.

## What to quote

Quote three PCBs from the trial fabrication files. Populate two and leave one bare for dry fit. Use the inherited four-layer ENIG stack and 1.00 mm finished thickness in the included fabrication request. Quote the same plated/unplated drills, including the four 1.02 mm nominal Mill-Max target drills. Ask the fabricator to report tool size, plating allowance, guaranteed finished hole range and annular ring. Review CAM openings and plot layers before fabrication. Keep the two clear windows on every copper layer. Route only the board perimeter indicated in Edge.Cuts. There are no sensor slots in this PCB.

The trial SMT list adds two Vishay NTCS0402E3103FL1T devices to the 35 original SMT positions. J83 and J84 are bare solder lands with no stencil apertures and no purchased connector. Leave CT1–CT4 empty during SMT. Handle and fixture the targets per the original flange quote and dry seating checks. The trial pads are laid out using Vishay's 0402 reflow dimensions. [Vishay 0402 mounting note](https://www.vishay.com/docs/29224/handlmount-ntcssmdntctherm.pdf)

| Flange site | Solder land 1 at lower native PCB Y | Solder land 2 | Pair |
| --- | --- | --- | --- |
| TH1, X17.75 / Z+5.75 | J83.1 to body J2.3 / PACK_NTC | J83.2 to body J2.2S | Charger TS |
| TH2, X17.75 / Z−5.75 | J84.1 to body J2.4 / PACK_GUARD | J84.2 to body J2.2S | Independent charge guard |

Run and identify two physically separate pairs. Their returns meet only at the body sensor return land. Keep them out of flange ground and the power return, and give each pair independent strain relief on the rigid tray. The new solder lands sit at X25.25 under the pack area. Dry-fit the actual solder heights and wire dress through closure and growth before assembly. J6/J7 pin assignments are unchanged. Use the standalone trial schematic with the wiring table above. The existing complete-system schematic still documents the taped-probe comparison build.

## Test sequence

1. Establish a repeatable measured gap with an inert pouch surrogate and a fixture carrying the pack restraint loads. Start near 3.35–3.52 mm with measured 4.064 mm stock. If trialling a relocated pouch, provide the intended growth travel on the opposite side and use the new lead paths. Record gap, chip height, pad bulge, contact witness, force and wire clearance. Follow Vishay's instruction to prevent compression stress on the sensor body. A relief or compliant interface changes the thermal path and must be part of the thermal measurement.
2. Compare the intact flange sites, the separate slotted coupon and the direct taped probe. Hold the pouch at 0°C while the warm PCB reference rises from 0°C to 20°C. Record both local board readings, both sensors and independent pouch temperatures. Target ≤1.5°C sensor error for that gradient (≤7.5% coupling). Repeat with hot pouch and cooler PCB and with representative assembled-board activity. Inspect whether pad bulge touches laminate outside the isolation area or bridges the coupon slot.
3. Commission charger TS and the independent guard separately with a protected battery simulator, including cold start, hot/cold cutoffs and electrical open/short. Log battery charge current. Repeat with one and both pads lifted while electrical connections stay intact. Require charging to stay within the confirmed pouch window and thermal budget. This artwork does not detect pad detachment by itself. Keep the baseline taped sensors for powered-pack work until the thermal and mechanical gates pass. Follow the [supplier's mounting limits](https://www.vishay.com/docs/29224/handlmount-ntcssmdntctherm.pdf) and the cutoff matrix in the thermal screen.

## Native verification and replay

The release audit compares the trial with the active routed file, verifies each schematic pad endpoint and saved copper-pour clearance, and checks the exported drill coordinates and original SMT placements. This machine uses KiCad 7.0.7. Its library comparator reports the same library warnings on the parent and trial. Use the project’s KiCad 10.0.8 validation runtime for final DRC and ERC before submitting the trial files for fabrication. A further commercial CAM check is required for the specified stack and finished target holes.

From the trial directory, `python3 build_trial.py` regenerates the unfilled board and editable schematic. Refill zones and save the PCB in KiCad before plotting. Run `check_and_export.py <kicad-cli> <output-dir>` with the bundled KiCad Python to reproduce the comparison and vendor review archive. The product BOM remains the separate human-owned BOM.
