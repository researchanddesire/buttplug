# Compass EVT1 direct PC contact adapter

EVT1-EA1 is a 35 × 26 × 1.6 mm four-layer external bench adapter. It connects a USB-C data port to the same four plug contacts used by the dock. The plug continues to use its native USB device interface. Connect the adapter fixture or the dock to the plug, one at a time. Routine enumeration uses the plug’s existing USB firmware.

- [KiCad project](compass-direct-pc-adapter.kicad_pro)
- [Schematic](compass-direct-pc-adapter.kicad_sch)
- [Board](compass-direct-pc-adapter.kicad_pcb)
- [Gerber and drill ZIP](quote/compass-direct-pc-adapter-gerbers.zip), [BOM](quote/compass-direct-pc-adapter-bom.csv), [placement](quote/compass-direct-pc-adapter-cpl.csv), [native checks](quote/review.json)

## Connection

J1 uses the GCT USB4105-GF-A-120 from the bench board. Each CC line has its own 5.1 kΩ pull-down. Use a native USB-C data port or powered data hub rated to supply at least 500 mA at 5 V for the first evaluation. The adapter requests default 5 V using the CC resistors and has no USB PD controller. [Bench schematic source](../one-board-dev/build_schematic.py) · [GCT drawing](https://gct.co/files/drawings/usb4105.pdf)

J2 is a top-entry JST PH B4B-PH-K(LF)(SN). Mate it with a JST PHR-4 and SPH-002T-P0.5S crimp contacts rated for the selected wire. Use a short, strain-relieved harness with equal-length D− and D+ conductors. Have the harness assembler terminate the far end on the pin board’s J94 pads. The four-pin harness is a distinct assembly. The BOM covers all 25 populated positions on the adapter PCB. [JST PH series](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf) · [J94 harness source](../../../cables/evt1/dock-main/main-to-pins.yml)

| J2 to J94 | Pin signal |
| --- | --- |
| 1 to 1 | GND |
| 2 to 2 | USB D− |
| 3 to 3 | USB D+ |
| 4 to 4 | Protected 5 V |

Viewed from above with the USB connector facing the front edge, J2 pin 1 is on the right. Measured from the PCB’s front-left corner, the USB-C footprint origin is (17.5, 2.675) mm and its mating face is 1.0 mm proud. J2 pin 1 is (20.5, 21) mm and pin 4 is (14.5, 21) mm. The 2.2 mm nonplated mounting holes are at (3, 3), (32, 3), (3, 23), and (32, 23) mm. Allow wire exit above J2 and clearance for both connector tails under the board.

## Power and data

U1 limits forward contact power. The 191 kΩ, 0.5% R3 yields approximately 120–166 mA DC across the published limit equations, using a conservative ±1% resistor allowance for initial tolerance and temperature drift. The plug’s BQ24074 is strapped for USB100 with a 100 mA maximum input. The plug’s 10 kΩ and 11 kΩ branch pull-ups add up to about 1 mA at 5 V if both are pulled low. Adapter logic is supplied from J1 ahead of U1. Budget 1 mA additional upstream current for the adapter on first test and measure the actual configured and suspended current. [TPS2553-Q1 current limit](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf) · [BQ24074 USB100](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

U2 is wired as an ideal diode with its CE tied to its output. It blocks sustained current from J2 towards J1. U4 senses the limiter output ahead of that reverse block. The TPS3808G09DBVR uses a 41.2 kΩ/10.0 kΩ divider. The estimated LIMIT_5V trips are 4.31 V falling and 4.35 V rising, with a 12–28 ms release delay (20 ms typical) after a valid rise. U4 and the PI3USB42 switch share the adapter 3.3 V rail. The PI3USB42 uses the A pair only and is high impedance with its supply off. Ground-referenced ESD arrays sit on both sides. The inactive pair on U5 has open pads. [LM66100 reverse blocking](https://www.ti.com/lit/ds/symlink/lm66100.pdf) · [TPS3808 timing](https://www.ti.com/lit/ds/symlink/tps3808.pdf) · [TPS7A20 capacitance](https://www.ti.com/lit/ds/symlink/tps7a20.pdf) · [PI3USB42 power-off behavior](https://www.diodes.com/datasheet/download/PI3USB42.pdf)

The threshold estimate uses TI’s nominal 4 MΩ SENSE input and 0.84 V falling threshold. Across 0–60 °C, stacking resistor initial tolerance and drift, ±1.25% threshold accuracy and 2.5% maximum hysteresis gives a rising estimate of about 4.53 V with the nominal input model. As a sensitivity check, imposing 1.7 µA at the SENSE trip gives about 4.59 V with the same corners. TI specifies that current as typical at 6.5 V. Measure both thresholds on each evaluation board under load. The more conductive divider adds approximately 0.10 mA to the switched rail at 5 V. [TPS3808 electrical characteristics and input model](https://www.ti.com/lit/ds/symlink/tps3808.pdf)

The circuit senses supply validity even with no product in the fixture. Physical contact alignment and make/break order determine what happens at the mating interface. Cold mate and disconnect the USB-C cable before swapping fixtures during initial bring-up. Keep the dock and adapter physically separate.

## First article

1. Check continuity and pin order from J2 through all four contacts before applying power. With the plug absent, sweep the input with a current-limited lab source. Capture PC_5V, LIMIT_5V, CONTACT_5V, ADAPTER_3V3 and DATA_OEn. Confirm C4 provides at least 0.47 µF effective at 3.3 V, including bias and temperature. For the room-temperature evaluation, screen for a rising trip at or below 4.55 V on LIMIT_5V and verify repeatable release under the 100 mA load. Confirm that the data switch opens below the measured falling threshold and during power removal, brownout and contact-rail overload.
2. Verify at least 4.60 V at J2 under a 100 mA static electronic load with 4.75 V at J1. Sweep the limiter through onset, confirm the DC limit on the received board, and capture momentary short current and recovery. With J1 unpowered, force 5 V at J2 pin 4 against GND from a limited supply and record J1 voltage/current. Repeat the reverse-current pulse capture with both sides on protected lab supplies.
3. Measure VBUS inrush at the host connector with the fixture already mated. J1 has 3.2 µF nominal decoupling ahead of U1 and the path after U1 adds 2 µF local plus the plug’s 4.8 µF nominal charger-input bank. The regulator output, ceramic bias, soft start, contact bounce and host current limit affect the waveform. Compare charge exceeding 100 mA against the 50 µC USB 2.0 reference in TI’s charger datasheet and capture PC and plug rails. Inspect VBUS_CHG and PGOOD at the plug to detect its diode/fuse drop and any charger input regulation. [BQ24074 inrush and input DPM](https://www.ti.com/lit/ds/symlink/bq24074.pdf)
4. With a known-good protected pack, test both USB-C cable orientations, enumeration, normal update, forced ROM recovery, charge state and detach/replug. Repeat across the intended pack states, source and cable combinations before relying on depleted-pack recovery. Capture all four contact states during partial travel on the physical fixture before live swapping. A nominal PCB or dry mating study cannot establish contact order or bounce behavior.

## Quote inputs

Request standard assembly with J1 shell stakes and J2 through-hole pins assembled at the factory. Verify the USB4105 land pattern’s 0.15 mm locating-hole clearance, J1 stake solder method and J1/J2 orientation in the assembly preview. The BOM maps all 18 order lines to vendor catalog codes. The J2 placement uses the housing center from the KiCad fabrication outline. Confirm actual stock and assembly process support in the quote. The supervisor and both divider values are a matched set. [U4 JLC catalog](https://jlcpcb.com/partdetail/TexasInstruments-TPS3808G09DBVR/C24584) · [R4 JLC catalog](https://jlcpcb.com/partdetail/257347-R0603RXX4122F10LTS/C267584) · [R5 JLC catalog](https://jlcpcb.com/partdetail/YAGEO-RT0603BRD0710KL/C95204) The pin-board wiring is covered by the separate fixture harness.

The checked Copper In1 layer is the ground reference. The connector’s USB orientation merge is carried over from the bench launch. Full-speed signal and the routed harness still require bench qualification. The source, footprint tables and routing workspace are local to this project. To rebuild, run `build_schematic.py`, export a KiCad XML netlist and run `build_pcb.py --netlist <netlist.xml> --import-ses routing.ses --finish` with KiCad 7’s bundled Python. Refill with KiCad 10 `pcb drc --refill-zones --save-board --schematic-parity <board>`. The KiCad 10 saved native board is the review and fabrication master. Run `make_quote.py --kicad-cli <path>` after a board edit to regenerate and verify exports.
