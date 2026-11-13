# Case/plug telemetry — electrical proposal

This new candidate addresses PRD-26/27 while preserving the existing body PCB architecture, all69 existing body footprint poses, the frozen routed flange, and the150-position dock Main source. It does not promote replacement schematics/artwork or change the human BOM. The shared thermal study remains its owner's source.

## Data topology

The four-contact PC USB path remains physically direct to the existing plug ESP32-C3 native USB. The case BLE module, its reset/clock/power state and its UART bridge have no D+/D− connection. Routine programming, generic PC commands/logs and physical Power/Mode ROM recovery remain independent of BLE availability.

A new case radio board uses NINA-B112-05B-00 (integrated antenna, u-connectXpress7.0), SC16IS750 with actual UART RTS/CTS, and the existing Main MON_I2C bus. The manufacturer's lifecycle table marks the provisional -04B as NRND and -05B as mass production. The AT manual supports the required GATT discovery/read/write/notification commands from NINA-B1 software2.0 onward, so these do not require newer7.4-only features. Sources: [NINA datasheet R19](https://content.u-blox.com/sites/default/files/NINA-B1_DataSheet_UBX-15019243.pdf), [AT manual R56](https://content.u-blox.com/sites/default/files/documents/u-connectXpress-ATCommands-Manual_UBX-14044127.pdf).

Proposed six-wire Main interface: qualified/current-limited radio5V, GND, MON_SDA, MON_SCL, PH0/IRQn and PH1/radio-enable. Physical MCU pins5/6 are the only available PH0/PH1 GPIOs; MSI remains the core clock and SWD stays primary. Power comes from existing SOURCE_OK-gated LOOP_5V through a new, independently limited branch. The small branch limiter belongs before the new header/harness so added wiring faults are bounded. All150 original placements can remain while the necessary added real parts/header receive a separate placement/routing study.

SC16IS750 address straps A1=A0=GND select seven-bit0x4D (the NXP table's0x9A includes R/W), avoiding the existing0x48 ADS. A14.7456MHz crystal gives115200baud with divisor8; exact crystal load/ESR and selected package still need primary verification. TX→moduleRX23, RX←TX22, RTS→CTS21 and CTS←RTS20 are four real wires. Local reset supervision and accessible module SWD11/15/UART/recovery pads are required. Default boot straps must prevent accidental factory reset. FIFO/autoflow configuration precedes data exchange; reset does not initialize every divisor register. [NXP SC16 datasheet Rev7.1](https://www.nxp.com/docs/en/data-sheet/SC16IS740_750_760.pdf).

TMUX1511 isolates SCL, SDA and IRQ when the radio is off. Its control inputs
follow hardware-gated radio enable. The radio IRQ and its 1 kΩ pull-up sit on
`SC16_IRQn`. The Main IRQ, header and host pull-up sit on `RADIO_IRQn`.
The [native netlist audit](case-radio/native-checks.json) verifies those two
nets on opposite sides of the switch, with zero ERC findings and 174
added terminal checks. Its powered-off protection applies through 3.6 V,
which must cover the measured Main 3.3 V maximum. Hardware SOURCE_OK gating
and default-low enable keep the branch off on legacy 100 mA USB. Local
telemetry requires a qualified supply. [TMUX1511](https://www.ti.com/lit/ds/symlink/tmux1511.pdf).

The NINA package is10×14×3.8mm. Its integration guidance requires5mm to casing and10mm to metal around/below its antenna, preferring a host-board corner. The exactNINA-B112 OEM STEP has now been extracted from the manufacturer-owned publicAltium library, with the original modelrecord/libraryhash and reuse-license evidence. Cold BRep, package-revision/dimension and installed-clearance checks remain open; no radio-board pose is guessed. [NINA integration manual, pp41–42](https://content.u-blox.com/sites/default/files/NINA-B1_SIM_UBX-15026175.pdf).

## Charge observations

Actual U7 ADS1115 AIN2/pin6 and AIN3/pin7 are currently GND. Existing CHG has a10k pullup to3V3 and reaches no MCU; PGOOD already reaches the C3. CE is pulled to charger-input5V through10k. Existing VBAT observation is retained.

CHG+ISET detects charge current, recharge despite inactiveCHG, and the approximate2Hz timer-fault pattern. It cannot distinguish termination from CE-disable, TS suspension or absent/open-protector battery when current is zero. CHGlow with zero current is also not completion. The mirror relation is V_ISET=Icharge×R_ISET/400 with±10% mirror accuracy. These are charger observations, not SOC. [BQ24074 RevN, sections9.3.5.1/9.3.5.4/9.3.5.7](https://www.ti.com/lit/ds/symlink/bq24074.pdf).

Recommended body instrumentation study adds a tiny TCA9536DTMR for CHG and actualCE, and uses AIN2/3 for buffered ISET/TS. Two OPA391DCKR buffers with two series10MΩ input resistors per tap isolate ADC loading/faults from the charger nodes. Each tap includes a1nF C0G input filter and each buffer drives a1k/100nF low-impedance ADC filter. Wait at least175ms after input/power transition before accepting the filtered observation; ADC MUX/conversion settling is additional. These are additional real positions; all69 original poses remain fixed pending actual packing. Normal/fault loading, leakage/contamination, settling and hardware trip margins must be calculated and measured before acceptance. The independent NTC guard, original RISET and hardware-grounded USB100 EN pins remain unchanged.

TCA9536 internal pullups default on: a direct5V CE input would feed current into3V3. Sense CE through22k into SN74LVC1G14DCKR, a5V-tolerant Schmitt inverter with specified partial-power-off protection; its output reaches the TCA through4.7k. Slow CE edges are allowed. A monitor-input short leaves CE at least2.527V for the stated3.8V source bound, above BQ VIH1.4V. The inverter supplies an inverted observation only and cannot drive chargerCE. CHG's4.7k series input bounds the default pullup case to0.875V, below the TCA0.970V low threshold at minimum3V3, and a wrongly driven TCAhigh loads CHG by at most1.164mA, below the BQ5mA test rating. Firmware verifies configuration and disables pullups before marking data valid; unused P2/P3 are configured low outputs after writing their output latch low. Driver readback masks documented bits0..3 (configuration/output) and6..7 (special function); unspecified upper bits are not compared as an entire byte. Primary: [TCA9536](https://www.ti.com/lit/ds/symlink/tca9536.pdf), [SN74LVC1G14](https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf), [OPA391, DCK electrical table](https://www.ti.com/lit/ds/symlink/opa391.pdf), [ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf).

`fault-loading.json` and its reproducible evaluator bound two10M taps, including a shorted tap resistor plus a downstream rail fault. TS threshold perturbation reaches10.363mV in the conservative combined corners; this is not zero loading or a qualified trip margin. Open/short NTCs cannot be hidden by the bounded resistive tap, but input saturation, contamination and power-sequence leakage remain acceptance gates. ISET resistance changes less than0.092% even with one tap resistor shorted; the original selected RISET, USB100 mode and independent guard stay unchanged. The buffered current estimate retains the BQ mirror's±10% uncertainty. USB100 default termination is2.7..4.0% of programmed current (nominal3.311mA with8.87k), not the10% default of other modes.

## State and history rules

| Observations | Report | Readiness effect |
|---|---|---|
| Missing/stale/reset/implausible measurement | Unknown | Invalidate readiness |
| PGOOD inactive | No valid charger input | Do not label physical removal |
| Repeated CHG fault pattern | Timer-fault indication | Latch fault; no Done |
| CE disabled or TS outside the qualified window | Charging inhibited | No Done/Ready |
| Positive ISET current | Charging, including refresh charge | Clear cooled-ready status |
| CHGlow with near-zero current | Suspended/current-limited/unknown | No Done |
| CHGhigh with near-zero current, using only two taps | Not charging; reason unresolved | No Done |
| Valid source/CE/TS, qualified taper/CHG history, credible pack presence and valid VBAT | Termination candidate | Done only after battery-detection/fault validation |

Battery absence/PCM-open and a fully charged pack are not universally separable from static signals. Bench validation must include the documented detection pulses, precharged/absent packs, open protector, thermal/input limiting, source bounce and reset during each phase. Never call bareCHGhigh/zeroISET Done. Poll CHG fast enough to retain the2Hz fault history locally, independently of slower BLE notifications. Serialize ADC MUX access with the existing pulsed tip measurement and wait a full conversion after each configuration.

The plug publishes raw status, calibrated tip/current/TS/VBAT values, sequence, boot/timebase identifiers and per-field validity/age; the case can request snapshots/time synchronization and baseline capture. `protocol-v1.json` defines separate20-byte thermal, charge and source-event notifications plus command/result characteristics without larger-MTU assumptions. Routine notifications target1Hz; each value carries original timing/validity, and the separate characteristics are not an atomic snapshot. A bounded RAM history plus persistent session/removal baselines can precede any optional external storage. Unknown source/contact/link loss preserves the last valid baseline with an explicit cause tag; it is not proof of physical removal. Ready additionally depends on the separately qualified thermal criteria/ambient reference and UV history. The radio's internal die sensor is not an ambient thermometer.

## Power candidate, not a budget mutation

Add a TPS22950 branch at its documented19.2k setting, allocating70mA including drift/current-limit reserve; require normal board load≤30mA over its intended conditions and qualify startup against its≈34mA minimum limit. SC16's6mA maximum excludes output loads; NINA's15mA supply-design peak excludes external I/O. IRQ's manufacturer-required1k pullup and both I2C pullup groups must be counted. No LEDs or fan are added.

A coupled candidate R107=39.2k and both UV RSET=4.22Ω keeps all four emitters. Retaining the existing PVT/TCR method,4.10V driver floor,70% efficiency assumption and resistance bounds gives UV limit604.78..732.98mA, normal UV563.63mA,41.15mA minimum-limiter margin, worst whole-source1467.65mA and32.35mA margin to1.5A. Conservative driver DC voltage is4.2604V with the full70mA radio allocation. LED nominal current becomes47.39mA. This is a candidate trade, not optical/thermal/transient qualification. The low-current radio switch's short-response overshoot, overall default/suspend/startup paths, hot voltage drop and UV optical efficacy remain to validate. Increasing UV RSET alone cannot lower the retained input-limiter fault bound. [TPS22950](https://www.ti.com/lit/ds/symlink/tps22950.pdf), [TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf).

The [schematic-bound power calculation](case-radio/power-screen.json)
allocates 2.98 mA for host-side loading and limiter overhead, leaving
0.79 mA inside the 70 mA radio allocation. It also accounts for radio current
through the shared U602 switch. At minimum input, the modeled switch loops
have 6.84 Ω left for contacts and wiring before either drops below the
10 mA wetting target. Measure both loops during radio startup and operation.
Reproduce with `python3 hardware/pcb/evt1/case-telemetry-study/check_case_radio_power.py`.

Next, route the body instrumentation and case radio candidates, then check
the received crystal startup, antenna location, power and UART timing.
