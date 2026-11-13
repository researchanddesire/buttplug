# EVT dock UI and UV electrical design

This is the selected architecture for the rounded FreeCAD dock revision. It is
**not routed fabrication artwork or a tested UV cleaning system**. The existing
`../dock/` USB board predates this circuitry. Replace that board in the next
revision; do not wire a CC controller in parallel with its two discrete Rd
resistors or treat the old quote ZIP as the revised dock.

The design calls for a real reflective LCD and three physical buttons. Its local
controller displays source mode, lid/thermal faults and the UV trial timer. It
has no device battery-SOC or programming-progress channel; those values must not
be invented on the screen. USB D+/D− still run directly from the computer to
the device's native ESP32-C3 USB through ESD protection and the four-contact
interface. The dock controller uses SWD for workshop programming and is not
attached in parallel to those data lines.

## Selected circuit

- **TLV70033DDCR** supplies 3.3 V using a 1 µF nominal output capacitor
  (≥0.1 µF effective). This supports the input-capacitance budget with the
  selected 0603 capacitors; it replaces the initial TPS709 candidate.
  [TI TLV700 specification](https://www.ti.com/lit/ds/symlink/tlv700.pdf).
- **STM32L071CBT6** at 4.2 MHz MSI/Range 3, 3.3 V, internal oscillator. LCD
  framebuffer needs 1024 bytes. Keep SWDIO/SWCLK, NRST and BOOT0 accessible.
  The manufacturer gives 0.770 mA maximum for the core running the specified
  Flash workload at this clock; the budget reserves 2 mA for core/peripherals.
  [ST DS10690, pp.65 and 75](https://www.st.com/resource/en/datasheet/stm32l071cb.pdf).
- **Newhaven NHD-C12864B2Z-RN-FBW**, 128×64 reflective, no backlight, ST7565R
  8080 parallel. Use the exact pin/capacitor contract in
  [the display manifest](../../../cad/evt1-assembly/vendor/display/source-manifest.json).
  `/RD` is tied high for write-only operation. Twelve MCU signals and the three
  button returns go to the lid UI board; the LCD's 27-way connector stays on
  that board. Display contrast charge-pump capacitors are not optional.
- **TUSB320HAIRWBR**, hard-strapped UFP (`PORT=GND`), GPIO mode (`ADDR=NC`),
  with active-high enable controlled by the power sequence below. Replace the
  old CC pull-down resistors with its CC pins.
  Its open-drain OUT1/OUT2 truth table is H/H unattached, H/L default attached,
  L/H 1.5 A, L/L 3 A. Invert OUT1 to make `SOURCE_REQUEST`; only the qualified
  sequence passes this to `SOURCE_OK`. No MCU or I2C write
  grants additional source current. This is Type-C Rp detection, **not USB PD
  negotiation or BC1.2 detection**.
  [TI SLLSEQ8D, pp.3 and 12](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf).
- **SN74LVC2G14DCKR** provides Schmitt inversion for CC OUT1 and the debounced
  CENTER signal. Its hysteresis accepts the slow rise from the 100 kΩ CC
  pull-up. Pin 1→6 and pin 3→4 provide `SOURCE_REQUEST=NOT OUT1` and the
  press-edge inversion, with ground on pin 2 and 3.3 V on pin 5. **R127 10 kΩ**
  pulls pin 3 / J104.8 high when the UI harness is absent, keeping the press
  output low. The normal CMOS SN74LVC2G04 is unsuitable for this slow input.
  [TI SCES200O, pp.3–5 and 9](https://www.ti.com/lit/ds/symlink/sn74lvc2g14.pdf).
- **TPS22950YBHR** in the device 5 V path. Permanent 19.1 kΩ + 100 Ω series resistors set
  the documented 34/50/66 mA limit; reserve 70 mA for the resistor/drift and
  implementation budget. A 2.52 kΩ resistor in parallel through a normally-off
  MOSFET is enabled **only by hardware `SOURCE_OK`**. Its effective 2.2276 kΩ
  is slightly above the documented 2.21 kΩ setting (380/500/620 mA). Loss of
  qualification returns to the low setting. The protected device's BQ24074
  remains in USB100 mode; battery supplement covers device peaks and Vin-DPM
  reduces charging when the upstream path limits.
  [TI SLVSFJ2B, pp.4,6,12,14](https://www.ti.com/lit/ds/symlink/tps22950.pdf).
  Use **YBHR**, not TPS22950C/L: their low-current ranges differ.
- **TPS2553DBVR**, 34.8 kΩ/0.1%, on the entire qualified UV branch. Its
  calculated DC range is 682.5–819.8 mA, including initial resistor tolerance
  and 25 ppm/K TCR over a conservative 100 K departure of film temperature from
  25°C. Together with a 630 mA device-path allocation and 10 mA dock allocation,
  the upper sum is 1.460 A, below the
  1.5 A advertised minimum. The normal conversion budget is in
  `power-budget.json`. This branch is hardware-disabled for a default source.
  [TI SLVS841G, pp.16–20](https://www.ti.com/lit/ds/symlink/tps2553.pdf).
- Four **VLMU35CB20-275-120** LEDs, two in series on each of two local UV
  modules. A **TPS61165DBVR** per module uses a **CRCW08053R32FKEA** 3.32 Ω
  sense resistor, nominal 60.24 mA. The calculated range is 57.88–62.70 mA
  including the specified 196–204 mV feedback limits, 1% initial resistance
  tolerance and 100 ppm/K TCR over a conservative 100 K film-temperature
  departure. Long-term resistor drift remains an acceptance gate.
  [Vishay resistor specification, pp.1–3](https://www.vishay.com/docs/20035/dcrcwe3.pdf).
  Use static CTRL; do not use EasyScale. A 220 nF COMP capacitor is
  required. This replaces the earlier TPS61169 candidate, whose specified
  feedback limits have a narrower temperature condition. The selected driver
  has a 39 V maximum open-LED threshold: output capacitors and local wiring
  must be rated for that state. Use 50 V output capacitors and a 60 V diode.
  [TI SLVS790E, pp.3–5,20](https://www.ti.com/lit/ds/symlink/tps61165.pdf).
  The LED's 19 mW typical figure is at 120 mA; **it is not the guaranteed output
  at this lower current or a delivered surface dose**.
  [Vishay 80232, pp.1–2](https://www.vishay.com/docs/80232/vlmu35cb2x-275-120.pdf).

Put the boost drivers and high-voltage output loops on the corresponding UV
modules. Do not route their approximately 15 V operating / 39 V open-LED rails
through the LCD hinge FFC. Each LED needs a real thermally coupled PCB and metal
heat spreader; an LED soldered to ordinary sparse FR4 is not credited with the
manufacturer's Al-MCPCB thermal result. The proposed module placement/count is
for optical trials, not evidence that shadows under supports are cleaned.

## Source startup and brownout sequence

U120 and U123 are **TPS3808G33DBVR** supervisors powered from **HOST_5V**,
with SENSE on 3.3 V and CT pulled to HOST_5V through separate 100 kΩ resistors.
The falling threshold is 3.07 V ±1.5% (minimum 3.024 V, above the CC IC's
2.7 V minimum). Each supervisor RESET has its own 10 kΩ pull-up to 3.3 V.
U120's MR is tied to HOST_5V. Its delayed release enables the active-high HAI
controller after 180–420 ms, exceeding the specified 50 ms initial EN-low time.

U124 is a **TS5A3159DBVR** SPDT powered from HOST_5V. Its select is
`CC_ENABLE`; it switches U123 MR between ground and HOST_5V. This level
translation matters because a 5 V-powered supervisor requires MR high to reach
0.7×VDD. U123 therefore starts its own 180–420 ms delay after the CC controller
is enabled, giving at least 180 ms before the source-current path can change.
U122, another HOST_5V-powered SPDT, selects `SOURCE_REQUEST` only after U123
releases `CC_STATUS_READY`. Otherwise it connects `SOURCE_OK` to ground through
R133 100 Ω. The default state is an active ground connection, with no credit
given to a diode clamp or the MOSFET's low gate threshold.
[TI supervisor, pp.4–7 and 11](https://www.ti.com/lit/ds/symlink/tps3808.pdf),
[TI SPDT, pp.3–5](https://www.ti.com/lit/ds/symlink/ts5a3159.pdf),
[TI CC power and enable requirements, pp.3,6,28](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf).

R132 2.52 kΩ and C114 100 nF damp switch charge injection, with a nominal
0.252 ms charging time constant. R133 limits capacitor discharge current while
providing a nominal 10 µs discharge time constant. The existing two 100 kΩ
pull-downs remain. Full safety logic uses **SN74HCS21PWR** and
**SN74HCS08PWR** Schmitt AND gates so the filtered signal does not enter
slow-input-intolerant CMOS. These full safety gates are selected but not yet
implemented in this source sheet.
[HCS21](https://www.ti.com/lit/ds/symlink/sn74hcs21.pdf),
[HCS08](https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf).

The original raw inversion left a datasheet sequencing gap; no powered failure
was observed. This revised circuit defines the intended hardware sequence.
Measure the CC VDD rise (≤25 ms), enable/status timing, short brownout behavior,
SPDT injection and source-current response before qualifying it. The SPDT's
charge injection is typical-only, and supervisor propagation/deglitch delay is
finite. Native ERC does not establish these waveforms.

## Hardware interruption and fresh-start behavior

Use two independent dry contact loops at approximately 1 mA each:

1. `VBUS → lid switch A NO → base thermostat NC → LOOP_A_RAW → 4.3k → GND`.
2. `VBUS → lid switch B NO → lid thermostat NC → LOOP_B_RAW → 4.3k → GND`.

Both **Omron D2F-01L** switches close only with the lid fully shut. Use distinct
actuators. The NO topology makes a disconnected loop prevent UV. The gold
microload switch has a 1 mA at 5 V reference minimum; maintain that wetting load
when designing the final loop voltage/drop. Its actuation and overtravel must
be checked against the actual hinge/latch CAD.
[Omron B036-E1](https://components.omron.com/us-en/system/files/2023-01/datasheet_pdf/B036-E1.pdf).
Each **Sensata 67L045** opens on rising temperature at 45±5°C and is mounted
against its heat spreader. It automatically resets after cooling; the hardware
latches below prevent that reset from restarting UV.
[Sensata 6700 specification, pp.2–4](https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf).

Buffer both raw loops through 5 V-tolerant **SN74LVC2G17DCKR** Schmitt inputs
powered at 3.3 V. `SAFE_RESETn` is the wired-AND of the open-drain outputs of a
**TPS3808G33DBVR** supply supervisor and **TPS3431SDRBR** external watchdog.
The supervisor has its 3.07 V threshold and CT left open for the specified
20 ms nominal delay. Configure watchdog EN and SET1 high, CWD through 10 kΩ to
3.3 V for 170–230 ms timeout. No firmware-disable path is provided. Firmware
updates its heartbeat only after one complete healthy main-loop iteration.
A separate **TPS3808G33DBVR** supervises UV release: SENSE=3.3 V,
MR=`LOOP_A & LOOP_B & SOURCE_OK`, CT pulled to 3.3 V through 100 kΩ. Its `UV_DELAYn` output
releases after 180–420 ms (300 ms nominal) of healthy interlocks. This exceeds
the CENTER debouncer maximum 80 ms pending transition. It never resets the
MCU when the lid opens; only the UV latches are held clear.
[supervisor](https://www.ti.com/lit/ds/symlink/tps3808.pdf),
[watchdog](https://www.ti.com/lit/ds/symlink/tps3431.pdf).

```
RAW_SAFE = LOOP_A & LOOP_B & SOURCE_OK & SAFE_RESETn
CLEARn = RAW_SAFE & MCU_STOPn & UV_DELAYn
RELEASE_SEEN: D=1; CLK=debounced CENTER release; /CLR=CLEARn
UV_RUN:       D=RELEASE_SEEN & MCU_ARM;
              CLK=debounced CENTER press; /CLR=CLEARn
UV_GATE_A = LOOP_A & SOURCE_OK
UV_GATE_B = UV_RUN & LOOP_B
UV_CTRL   = UV_RUN & CLEARn
```

Implement the two flip-flops in **SN74LVC74APWR**; tie both `/PRE` high.
`MCU_ARM` and `MCU_STOPn` have external 100 kΩ pull-downs. Two cascaded
**TPS22919DCKR** switches interrupt UV input power, with separate enables
`UV_GATE_A` and `UV_GATE_B`. Their output discharge connections are populated.
A **DMN62D2U-7** per UV module interrupts the LED cathode between the LED string
and the FB/sense resistor node; gate=`UV_CTRL`, 10 kΩ gate pull-down. This
prevents the output capacitor from keeping the LED current path closed while
boost input power is removed. Keep 39 V clear of its FB/logic nodes.
[dual flip-flop](https://www.ti.com/lit/ds/symlink/sn74lvc74a.pdf),
[load switch](https://www.ti.com/lit/ds/symlink/tps22919.pdf),
[MOSFET](https://www.diodes.com/datasheet/download/DMN62D2U.pdf).

Use **MAX6816EUS+T** for CENTER hardware debounce (20–80 ms stable time, 50 ms
nominal), then invert its output for press-edge clocking. Both press and release
must be debounced. The second flip-flop matters: a press still being qualified
by the debouncer when a fault occurs cannot restart UV after recovery, because
`RELEASE_SEEN` was cleared. After power-up, interruption or completion, require a
press/release to arm and a subsequent fresh press to start. A held button,
reclosed lid, returned source, cooled thermostat or MCU reboot cannot supply
that sequence. Left/right use 10 kΩ pullups and ordinary firmware debounce. Their switch
microload reference is 10 µA at 1 V, so no 1 mA wetting requirement is introduced.
[ADI MAX6816 Rev.8, pp.2,5](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX6816-MAX6818.pdf).

## Interfaces for the next PCB revision

`pin-contract.json` assigns physical MCU/package pins and the 20-way UI hinge
link. The lid UV module has a separate 8-way flexible loom: switched 5 V,
return, UV_CTRL, FB monitor, divided VOUT monitor, NTC signal, thermal-loop send
and return. The base controller reads both NTCs with its ADC and an
**ADS1115IDGSR** reads both UV-module FB and divided-output voltages at local
I2C address 0x48. A disconnected NTC, missing LED current, implausible output
voltage, ADC timeout, current-limit fault or unexpected latch state clears
`MCU_STOPn`. Current/voltage measurement provides electrical feedback only.

UV trial controls must show **unqualified trial timer** until a specific
cycle/load/cleaning protocol is optically and microbiologically validated.
A complete timer is not a passed cleaning result. Housing opacity, seams,
USB/display openings, interlock-before-unmasking travel, shutdown optical tail,
heat, resin aging and fouling/shadows need measured acceptance. Do not claim
sterilization. Workshop testing starts with an inert assembly and closed,
qualified opaque chamber.

## What remains before ordering this revision

- `dock-ui-source.kicad_sch` now implements the USB/CC, low/default device
  current path, qualified parallel resistor, limited UV branch and 3.3 V supply.
  It exports through native KiCad 10.0.8 with exact selected pins/parts, a
  checked netlist and **zero native ERC errors or warnings**. The source/library
  hashes and reports are bound by `native-checks.json`; rerun `check_native.py
  --kicad-cli /path/to/kicad-cli`, then `check_source.py` after changes. No ERC
  exclusions are configured. This check covers only the source sheet; the
  complete UI/safety/UV sheets, board routing/DRC and linked StepUp boards still
  remain. No revised
  PCB or full dock order list exists in this folder yet.
- Confirm 10 mA dock overhead, source-mode changes, USB suspend/inrush, device
  operation/charging from the limited source, and empty/depleted pack recovery.
  The LCD's published 0.75 mA maximum is at 25°C and the Type-C IC's published
  current is typical; the budget labels those allocations explicitly.
- Circuit timing/thermal and single-fault tests, then optical leakage/dose and
  cleaning trials. `analysis.json` is arithmetic and a Boolean latch-model
  check, not native electrical verification or a powered safety result.
