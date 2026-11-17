# Compass EVT1 open bench board

This board reproduces the one-board plug circuit on a larger, open bench PCB. The 109 × 80.5 mm outline brings out power, recovery, motor and thermistor signals. The routed artwork is ready for engineering review before fabrication and electrical qualification.

Open `compass-one-board-dev.kicad_pro` in KiCad. The device sheets derive from the **[one-board product schematic](../one-board/compass-one-board.kicad_sch)**. The dev-specific source selection, rail links, simulators and test points appear on the **[bench sheet](sheets/09-bench.kicad_sch)**. The local component placement initially follows the existing discrete body and flange boards.

## Bench setup

With power disconnected, install the minimum links required for the test. The USB host key and the three isolation links are removable. Begin with the battery and motor unplugged and a current-limited source. Leave the paired motor outputs floating relative to ground for differential measurements.

| Interface | Use |
| --- | --- |
| **J110, J111** | J110 is a USB-C device receptacle for a PC. J111 is a keyed GND, D−, D+, 5 V input wired to a dock acting as USB host. Connect one host. |
| **J112** | Install the labeled **PC** or **DOCK** key to select 5 V, D− and D+ together. Leave J112 empty for battery-only operation. Remove USB power and disconnect the battery or simulator before swapping keys. See the [key assembly drawing and acceptance](selector-keys.md). |
| **J120** | Open 3.3 V between the converter output and logic rail for staged bring-up or a series meter. The regulator-side output capacitors and feedback remain coupled to the converter when open. |
| **J121** | Open VM between the motor converter and H-bridge. Retains local driver-side bypass. Motor ARM/PWM and charge inhibit remain in circuit. |
| **J122** | Open protected pack positive before the charger and voltage sense node. The pack ground stays common. Use the J2 pad markings for polarity and the two distinct NTC returns. |
| **J3** | Disconnectable motor outputs. Neither terminal is ground. Test the assembled load and current path before fitting a real pack. |
| **J124** | Two dry-resistance simulators, PACK_NTC/GND and PACK_GUARD/GND, for independent charger and guard tests. Disconnect the real pack sensors at J2 before substituting. |
| **J5 and J8** | Tip and pack telemetry thermistors. Substitute a passive decade box at either input with its real sensor unplugged. Use resistance values representing the selected thermistor's expected range. |
| **J4 and J125** | Retained ROM-recovery header and bench access to reset, boot, I²C, 3.3 V and ground. Follow the device's established recovery sequence. |
| **TP101–TP121** | Scope access to charger input/output, pack, both motor rails and outputs, USB presence, motor logic and all three classes of thermistor inputs. Ground pads are at both ends of the probe grid. |

The schematic's two **BENCH_LINK_SOURCE** markers represent external jumper-fed supplies at the isolated load sides. They carry no footprint. Product safety gates and protection parts stay in the functional path. Use the completed bench board for staged electronic bring-up. USB signal integrity, exact stackup, source selection, rail transients, current and temperature rise, compass calibration, and all physical and powered behavior need measurement.

J110 is a mixed-mount connector. The local footprint marks it through-hole for KiCad's pad-type check and retains all 22 original pads, paste apertures, and the placement centroid. The assembly position export includes J110 by reference. Have the assembler confirm pin-in-paste or a secondary soldering operation for all four shell tabs. The [vendor operation sheet](../../../design/evt1-bench-ordering/master-bench-eval/vendor-assembly.md) also covers the bench headers and J2 pigtail.

### Bring-up order

1. Inspect polarity, connector pin 1 and unpowered rail continuity with all shunts, battery and motor removed.
2. Fit the appropriate key at J112 with power off. With one current-limited 5 V source connected at J110 or J111, measure protected input at TP103, SYS at TP104, and the regulator side of J120. Install J120 with power disconnected after verifying the regulator output.
3. Test enumeration, ROM recovery, Power and Mode. Verify the motor remains inhibited with valid dock power before connecting a motor load. Use the [operating mode matrix](host-key-contract.json) to select the key for the hardware under test.
4. Test both hardware charge sensors independently at J124 and the tip and pack telemetry inputs at J5 and J8. A dry decade box can exercise plausible values, opens and shorts while the real pack stays disconnected.
5. For motor testing, disconnect USB and dock power. Use a current-limited battery simulator at the protected-pack input and reconnect the required shunts with power off. Check VM on both sides of J121 before attaching a suitable differential test load through J3. Measure startup current and voltage droop before testing with a real motor and approved pack.

## Routing verification

The six-layer, 1.6 mm candidate keeps In2 as its continuous ground reference. In4 uses ground fill with local low-speed routes by the power and sensor circuits. Ground pours and stitches on F and B connect local returns. The seed transfers 821 compatible copper objects from the two original layouts, including regulator switching loops and downstream USB fanout. KiCad 10.0.8 reports **0 ERC findings, 0 DRC findings, 0 unconnected items and 0 schematic parity findings**, with zero ignored checks. The PCB and reports are hash-bound in `routing-status.json`. The unmodified J110 locating-hole pattern uses a scoped 0.15 mm hole-to-copper rule. Obtain fabrication acceptance for this feature and the finished stackup, and complete the staged electrical tests before using powered hardware.

The native reports record the project's check severities. The independent `contract.json` ties 428 pad assignments and 352 retained product terminals to the saved native source. The 11 schematic endpoint changes split the logic, motor and pack rails at the removable links.

R21 and R43 use the RESI PTFR0805 recommended 1.40 × 1.65 mm pads on 2.60 mm centers. The placement and local routing changes are recorded in `routing-status.json`. Use a new Gerber ZIP and CPL for the next quote.

J8 opens toward the board's left edge at X 86.00 mm, Y 126.00 mm and −90°
on F.Cu. Insert the pack thermistor plug from the left edge, away from U7
and R61. Regenerate Gerber and component placement files before requesting
a quote for this revision.

## Source and reproduction

`build_schematic.py` copies the product leaves, changes the explicit rail endpoints and replaces the four contact targets with the bench interfaces. Export the XML netlist with KiCad before running `build_pcb.py place`. Placement and Specctra export/import use KiCad 7's bundled Python followed by DRC with the current KiCad CLI. The adjacent DSN and SES preserve the first offline routing pass with the former selector. Run placement only when intentionally recreating the initial artwork, because it replaces the current copper. Continue from the saved KiCad PCB for the current routes. `check_contract.py` audits the retained terminals and `check_host_keys.py` checks the two host keys against native pads and schematic nets.

Run `python tools/export_evt1_one_board_fab.py dev <new-output-directory>`
from the repository root with KiCad 10's CLI available. The export refills a
temporary board, checks ERC, DRC and schematic parity, and produces a bare
board CAM ZIP, native drill report and assembly CSVs for review. Confirm the
stackup, J110 fit and assembly angles with the fabricator.
