# EVT1 electrical and firmware

The current electrical candidate is `hardware/pcb/evt1/system-evt1.kicad_pro`.
It preserves R35F as a reference and changes the interfaces required by the
current mechanical design. The full product is not an order/build release.

| Interface | Implementation |
| --- | --- |
| External contacts | GND/D−/D+/5V, fixed targets in the device. USBLC6 protection and22R series resistors lead to ESP32-C3 GPIO18/19. |
| Dock power | TPS2553 input switch; R210k current limit. Device BQ24074 selects USB100, reducing charge current when system demand consumes its input budget. Whole-source budget, inrush and suspend remain physical checks. |
| Wake | Dock presence and the physical switch diode-OR into RTC GPIO1. Firmware discards dock-induced button gestures and avoids deep sleep while docked. |
| Recovery | TPS3422 watches the independent raw power switch. Hold Power≥7.5s for a400ms reset; hold Mode during reset to strap BOOT low for ROM USB programming. Release before retrying. Circuit timing, buttons and flashing need hardware checks. |
| Tip temperature | TDK B57540G1103F000, two leads, ADS1115 at0x48. Pulsed10k divider plus excitation/2 reference; manufacturer curve8307, open/short/rail/drift rejection. |
| Compass | Fixed LSM303AGR daughterboard: accel0x19, magnetometer0x1e. Separate package-to-flange transforms and magnetic correction are stored in NVS. The12×10×1mm layout passes DRC and fits integral tray bosses. C83 selects TDK C2012X5R1E226M125AC22uF25V; effective capacitance, factory package axes and magnetic survey require qualification. |

GPIO4/5 remain I2C. GPIO10/interboard pin10 becomes `TIP_EXC_EN`; it is no longer
the MC3635 interrupt. The NTC is pulsed about once per second and excitation
is removed on all conversion-error paths and before sleep. Motion is polled
at10Hz. The ADS1115 gain is±4.096V and conversion rate128SPS; two bracketing
reference conversions reject excitation changes. Reported temperature is a
nominal thermistor conversion, not a calibrated cap/motor thermal measurement.

Build `pio run -d firmware -e evt1`. The legacy `prototype-r0` profile still
expects TMP117/MC3635. Python3.12, PlatformIO6.1.19 and ESP-IDF5.5.3 were used;
`firmware/requirements-build.txt` includes the required `intelhex` dependency.
Run `sh firmware/tests/run_host_tests.sh` for control and sensor-math checks.
The motor remains disabled by default pending selected pack/motor/thermal
limits; a successful build is not evidence of powered hardware operation.

USB telemetry identifies `hardware:"evt1"` and adds raw magnetometer data,
calibration/heading validity and magnetic heading in millidegrees. Heading is
suppressed without valid assembly calibration, while docked/running the motor,
for a one-second settling interval, stale/saturated data, unsuitable field
magnitude, nonstatic acceleration, weak horizontal field or near-vertical arrow.
The math gate does not detect every magnetic or motion disturbance. The new
direction-pulse candidate blanks the bearing while pulsing/settling and retains
the independent motor gates. Its actual settling and accuracy remain untested.
See [plug templates](plug-templates.md) for the primary UI, mapping helpers,
wear-counter contract and unimplemented Lockbox-credit bindings.

Send newline-terminated `status` or `help` over USB. While docked, the
engineering command `compass-cal JSON` accepts version1 with arrays
`accel_to_flange[9]`, `mag_to_flange[9]`, `mag_offset_ut[3]` and `arrow[3]`.
It validates and commits a single NVS blob. `compass-clear` erases it.
This is assembly calibration against a fixture/reference; no wearer pose
calibration is introduced. Acquire magnetic data away from the dock's field,
then upload/validate the fitted calibration. A fitting/qualification workflow
and final axes must accompany the completed sensor layout.

Full-system/body ERC, all five PCB DRC checks and independent pad/netlist/pin
contracts pass. Host checks cover twelve thermistor resistor/rail fixtures,
fault/monotonic behavior and1,680 known compass pose/calibration cases. Firmware
builds pass for both profiles. No sensor-bus, radio, reset, USB, flash, charging,
thermal or human-use test has been performed on the hardware.

All three device boards match their schematic pad nets and pass source-bound
native DRC. Their actual outlines/component envelopes fit the separate device
assembly native, including a flange-fixed compass mount. Physical axes,
effective capacitance, loom and powered checks remain open. Internal SW3/SW4 are removed; service EN/BOOT
remain on J4 and the external Power/Mode recovery chord.

See [hardware](hardware.md), [validation](testing.md), and the source-specific
`hardware/pcb/evt1/README.md` for files and remaining integration.
