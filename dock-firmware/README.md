# EVT dock firmware candidate

This separate STM32L071CBT6 target implements the dock's LCD, three buttons,
interlock/fault display and UV trial timer. The existing device firmware stays
in `../firmware/`. Programming this controller uses SWD; computer USB D+/D− go
directly to the device ESP32-C3. The dock has no battery-state or programming-
progress data channel and displays neither value.

The code cross-compiles to ARM ELF/BIN/HEX with official Arm GNU13.3.Rel1.
`validation.json` binds the exact source, selected hardware GPIO contract,
vendor headers and binary hashes to host behavior tests. No board has been
flashed or powered. A completed timer is not cleaning validation.
`interface-review.json` independently checks actual controller, lid, source and
safety native XML endpoints against firmware and selected physical pin maps.
It includes each LCD series resistor, NTC filter chain, direct LCD socket
numbering, actual3.65ohm UV sense/divider circuits and hardware CENTER/watchdog/
latch paths. `placement-review.json` separately binds a read-only native KiCad
pad/net/library and connector-direction audit of the two placement candidates.
These are the44-reference controller subset and28-reference lid board, with
zero tracks/vias. Full base integration, routing/DRC and physical continuity
remain separate.

## Build and check

```sh
make test
make CROSS=/path/to/arm-none-eabi-
python3 tools/validate.py --cross /path/to/arm-none-eabi-
```

Run these inside `dock-firmware/`. `CROSS` is the executable prefix, including
the final hyphen. Artifacts are `build/dock-evt1.elf`, `.bin`, `.hex` and `.map`.
The linker targets128KiB Flash at0x08000000 and20KiB RAM, reserving at least2KiB
stack. Tests use the host C compiler and undefined-behavior sanitizer.
`SANITIZERS=address,undefined make test` also enables ASan on a supported host;
this macOS host's ASan runtime failed before entering the tests.

Official ST device headers and Arm CMSIS core headers are included with their
licenses and pinned source hashes in `vendor/sources.json`. The inspected Arm
compiler archive came from
[Arm's download](https://developer.arm.com/-/media/Files/downloads/gnu/13.3.rel1/binrel/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi.tar.xz).
Its SHA256 is `fb6921db95d345dc7e5e487dd43b745e3a5b4d5c0c7ca4f707347148760317b4`.
No toolchain installation or flash command runs automatically.

## Physical start and stop

Reset drives MCU_ARM and MCU_STOPn low before peripheral setup. Both have
hardware pull-downs. One second of valid, qualified inputs permits the initial
**press and release**. Firmware waits for the hardware RELEASE_SEEN latch,
then permits a subsequent fresh CENTER press to start through the hardware
UV_RUN latch. Firmware never generates that press clock. A held button,
recovered source, closed lid, cooled thermostat or reboot cannot resume UV.

CENTER stops an active trial. Timeout, an interrupted loop/source, a current-
limit flag, invalid/stale measurements, unexpected latch state or excessive
temperature removes permission and latches a stopped state. Recovery requires
the physical press/release sequence again. Boot, completion and fault states
keep ARM low. Hardware independently owns lid/thermal/power interruption.
After a fault, inputs must remain healthy500ms before a new acknowledgement
press counts. This exceeds the hardware UV release supervisor's420ms maximum
delay; a button held during that delay cannot count as a later fresh press.

LEFT/RIGHT choose30/60/120-second **unqualified trial timers**. Hold both for
two seconds to select LCD contrast; LEFT/RIGHT then adjust its0–63 setting.
CENTER retains its hardware start/stop role in both menu modes. Settings are
volatile. The LCD always identifies the cycle as an unqualified UV trial.

## Target implementation and limits

- MSI range6 provides nominal4.194304MHz, VOS Range3, zero Flash wait states.
  SWD pins retain their reset configuration. SysTick supplies nominal1ms time;
  oscillator accuracy and actual maximum trial duration require measurement.
- The ST7565R uses the selected Newhaven128×64 reflective LCD's8080 interface,
  1024-byte framebuffer, manufacturer bias/orientation/pump initialization and
  adjustable electronic volume. Atomic low-byte PA writes preserve STOPn/WDI.
  `/RD` is tied high; GPIO writes cannot confirm a connected/working display.
- PB0/PB1 ADC channels read the two10k Vishay NTCLE413E2103F524A sensors against
 10k0.1% VDDA pull-ups. The nominal conversion interpolates manufacturer R/T
 table3; `ntc-source.json` records the facts. Start range is10–35°C and the
 software trip is38°C. These trial thresholds and attachment/response time
 still need thermal qualification; hardware67L045 remains independent.
- I2C2 on PB10/11 AF6 reads ADS1115 address0x48 at approximately50kHz. A complete
 four-channel scan must be fresh within150ms. FB uses±0.512V range; divided
 output voltage uses±4.096V. Current conversion uses the selected3.65ohm
 R401/R501 sense resistors (nominal54.79mA at200mV). Configuration readback, ADC completion and bus
 operations have bounded timeouts. Small negative ADC codes within32counts
 are clamped to zero as an offset/noise allocation. Larger excursions fail.
- After300ms startup, both strings must measure45–75mA and7–19V. A value over
 42V fails immediately; after300ms off, residual measured current over3mA
 fails. PB2 also checks post-cut UV_5V_SW presence after that startup grace.
 Its100k/150k divider drives a digital input; this is not a numeric4.3V
 measurement or an input-voltage-floor qualification. These are electrical
 trial limits, with no surface-dose inference.
- WDI gets one falling-edge pulse only after a complete main-loop iteration: successful ADC/I2C,
 state/output update and scheduled display work within100ms. SysTick and
 error handlers never feed it. A bus/ADC failure, hard fault or overrun drops
 ARM/STOPn and stops feeding the external watchdog. Handled interlock faults
 remain visible while the working main loop continues its heartbeat.
 The pulse occurs every completed loop, keeping the nominal falling-edge
 interval below110ms including the10ms loop cadence, against the170ms watchdog minimum;
 toggling once per loop would double that worst-case interval.

## Bench bring-up still required

Use the source-bound revised dock boards and SWD header at3.3V reference.
Initial GPIO/default-off, actual clock, LCD orientation/contrast, I2C/ADC
readings, button/loop polarity, supervisor/latch timing, watchdog interruption,
timeout and source changes need board-level testing. First perform electrical
bring-up with the emitters isolated, then use the project's closed opaque
inert UV trial procedure. Optical shutdown, leakage, temperature, delivered
dose and cleaning remain separate measured acceptance work.
The hard-enabled external watchdog also runs while SWD halts the core.
Connect-under-reset programming and reset/loader timing need verification;
an ordinary prolonged debug halt will intentionally reset the MCU.

Primary references: [ST RM0377](https://www.st.com/resource/en/reference_manual/rm0377-ultralowpower-stm32l0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf),
[ST DS10690](https://www.st.com/resource/en/datasheet/stm32l071cb.pdf),
[Newhaven module](https://newhavendisplay.com/content/specs/NHD-C12864B2Z-RN-FBW.pdf),
[TI ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf),
[Vishay NTCLE413](https://www.vishay.com/docs/29078/ntcle413.pdf).
