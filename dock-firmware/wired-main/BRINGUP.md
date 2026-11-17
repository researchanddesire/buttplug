# Wired USB bench acceptance

Use the completed wired Main route and both firmware images listed in the
[build report](build-validation.json). Record board revision, resistor
population, STM32/RP2040/plug firmware hashes, contact fixture revision,
cable, supply and instruments. The three matched resistor positions are
Main R107 **40.2 kΩ**, base R401 **4.22 Ω** and lid R501 **4.22 Ω**. The
STM32 image must be built with `PROFILE=wired`. For the USB tests below,
keep the UV LED connections isolated and verify the disabled state at
power-on. Use the reviewed protected 5 V feed and common ground through
the four contacts.

Program the EVT1 plug with the matching 4 MB ESP32-C3 bootloader,
partition table and application. Use `flasher_args.json` from the
same PlatformIO build to confirm the flash settings and addresses.
For a blank board, use the pre-mold J4 service connection and the
protected supply described in the recovery procedure below. An
assembled plug can enter ROM off-dock by holding Mode across the
hardware Power reset before reseating. Confirm the selected serial
port and target before writing, then verify normal boot and PC
enumeration. Leave the plug's motor bench-enable option off for USB
and sensor commissioning.
[EVT1 build instructions](../../firmware/README.md)

Program the RP2040 on an exposed Main board fixture. The installed lower
shell blocks direct underside probe access to TP151–TP157. For assembled
recovery first test a verified default-current USB-A to USB-C data cable.
For the hardware lock use the exposed Main contact fixture.
See the [docked recovery study](../../hardware/cad/evt1-assembly/dock-harness-trial/wired-main-space-review/recovery-access/README.md).

## Main programming access

The STM32 uses the top-side J202 footprint with a TC2030-CTX-NL cable.
Use J202 pins 1 VTREF, 2 SWDIO, 3 NRST, 4 SWCLK and 5 GND. Pin 6 is
unused. The external watchdog stays active while the MCU is halted.
Verify connect-under-reset before relying on extended debug access.

The RP2040 has individual underside pads. Use the PCB's coordinate
view to identify each pad on the exposed board. Turn on the board's
qualified local host supply and measure VTREF before connecting a
target-referenced probe. Use address-bearing ELF or HEX for both MCUs.

| RP2040 service function | Main pad | KiCad center X, Y in mm |
| --- | --- | --- |
| Ground | TP152 | 71.2, 163.6 |
| SWDIO | TP153 | 77.2, 150.6 |
| SWCLK | TP154 | 76.6, 143.4 |
| RUN | TP155 | 88.8, 145.8 |
| VTREF, USB host 3.3 V | TP156 | 87.6, 143.0 |

Wait for Main routing completion and verify continuity from each pad
on the fabricated board before connecting the probe.

## Power and control first

1. With the plug absent, confirm 5 V contact and host-rail polarity,
   no feed from the local host into J101, and the default PC switch state.
   Capture J101 current and local supply/enable at default, 1.5 A and
   3 A Type-C advertisements. At default USB power the local host rail
   stays disabled. For the host-enabled tests, compare the incremental
   active branch current at J101 with the **40 mA** design target, verify
   U154 input stays at or above **3.60 V** and measure at least **3.135 V**
   at RP2040 USB_VDD during local attachment. Record startup and transient
   captures separately from steady readings.
2. Capture host 3.3 V, the 1.1 V core rail, RP2040 RUN and a firmware-visible
   clock or boot marker on cold power-up, brownout and reattach. Repeat
   with the final oscillator placement and at the intended temperature
   limits. If probing the crystal, use a low-capacitance active probe and
   record its loading. Keep the USB selection in PC mode until host startup
   is confirmed. [Clock layout review](../../hardware/pcb/evt1/case-telemetry-study/wired-main/layout-candidate/oscillator-review/README.md)
3. Verify the STM32 PH0/SCL and PH1/SDA bus at the RP2040 side of the
   isolator using a high-impedance probe. Capture START/STOP, the 7-bit
   address 0x38, the write/read lengths, ACK, rise time and any clock
   stretching. Compare with the [wire format](README.md). Confirm the UV
   monitor bus on PB10/PB11 still runs while the host bus is disconnected.
   With UV isolated, repeat with host-side SCL stuck low through a
   current-limited fixture. Verify bus failure clears the screen reading
   and the UV controller still updates its separate interlocks/watchdog.

## Verify both USB owners

| Case | Evidence to capture |
| --- | --- |
| PC pass-through | Capture full-speed CDC and JTAG enumeration on a computer through the actual dock and contact stack. Read the plug console, then program and verify a known test image. |
| Hardware PC recovery | Assert TP151 to TP152 before powering up. Verify PC enumeration with the dock controllers held in reset. Use Power and Mode off-dock with a charged pack, then reseat and verify ROM download. Restore the intended plug firmware after recovery. |
| Default-current recovery | With a verified USB-A to USB-C data cable, confirm the local host remains off. Enter ROM off-dock with Power and Mode, then verify the PC completes recovery through the seated contacts. Repeat with a charged and a near-depleted pack. Use the pre-mold J4 service fixture to test open-protector recovery. |
| Standalone | Use a 1.5 A or 3 A qualified source. Open the lid, release buttons, then hold Right for two seconds. Capture mux break/select and enumerate the plug from RP2040. Compare fresh LCD tip data with the recorded CDC reading. Record time from the gesture to first valid sample. |
| Switch back | Repeat the open-lid gesture to return to PC. Observe the switch's open interval, loss of live LCD data and fresh PC enumeration. Repeat in both directions with a computer that advertises at least 1.5 A. |
| Partial mate and loss | Exercise partial contact, removal, source downgrade and redocking during enumeration and a CDC reply. Record contact 5 V, mux state, CDC attach and the screen. With the interface still mounted, interrupt a CDC reply and confirm the host clears the stale display status and obtains a new snapshot and timing anchor without physical reseating. Treat source and USB loss as electrical observations. |
| CDC recovery while seated | Delay a tagged reply beyond its timeout, then restore it while the interface remains mounted. Confirm the reading clears during the interruption and refreshes after a new snapshot and clock anchor. Check that replies from the abandoned request are ignored. |
| Reset and stalled client | Interrupt each processor individually in standalone mode. Verify STM32 command loss expires the RP2040 lease, RP2040 reset restores its default outputs, and the hardware PC lock works independently. Record timing at the mux pins. |

Capture the switch pins and both D+/D− branches when possible. Compare the
100 ms planned break and 10 ms select settling interval with the firmware
timing and verify the old host is isolated before the new host signals.
Record contact polarity/continuity and full-speed signal quality on the
actual spring-contact assembly. Repeat at USB suspend/resume and power
downgrade. Report unsuccessful cases with traces and the exact setup.

Repeat the common PCB supply/return resistance check on the final Main fill
before the powered UV phase. Use the existing closed-fixture UV procedure
for interlock, current, thermal, leakage and optical checks. The USB test
matrix establishes communications and recovery only.
