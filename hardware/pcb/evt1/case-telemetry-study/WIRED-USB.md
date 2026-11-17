# Wired dock-to-plug telemetry

The four contacts already carry GND, D−, D+ and protected 5 V. Use the
ESP32-C3's existing USB Serial/JTAG CDC-ACM interface for both dock telemetry
and computer access. The wired dock has two data owners and selects one at
a time on the Main PCB. The cradle needs no radio or antenna.

| Mode | D+/D− owner | Use |
| --- | --- | --- |
| PC / recovery | The computer at J101 | Direct access to the existing CDC and JTAG interfaces, including ROM recovery and flashing |
| Standalone | The dock's full-speed USB host | Poll the plug over CDC for temperature, status and history while powered from a qualified source |

Keep USB-C sink/CC detection and the existing protected 5 V contact path.
The data switch belongs between the connector-side protection and J102, with
the plug-side pair on the switch common port. A local host controller sources
USB bus signaling. It must use the existing dock-supplied contact VBUS path
and must never feed 5 V back into J101. Confirm the actual rail is valid
before host attach. Keep the hardware lid, thermal and current cutoffs
independent of telemetry and USB ownership.

Use a hardware default to PC/recovery after reset, with a deliberate request
for standalone during the first EVT. A PC/recovery override must work even
with a stalled dock MCU. Before changing owners, open both channels, stop
the old local host session if active, then connect the new owner and let it
enumerate. Switch selection must not be inferred from Type-C current
advertisement, since that is a power capability. Qualify PC attach/detach,
brownout, source changes, reset, partial contact and both switch directions.
The first prototype can validate explicit ownership before selecting an
automatic handoff policy.

## Main implementation candidates

The [wired Main circuit study](wired-main/README.md) carries the RP2040
host and USB switch as the working PCB candidate. The existing STM32
continues to run the display, buttons and UV controls.

The STM32L071CB has no USB host controller. An SPI full-speed host
controller such as MAX3421E could retain the current dock controller and
safety firmware, but the saved 48-pin allocation has just PH0 and PH1
available. The MAX3421E needs SCLK, MOSI, MISO and CS, and its active
supply budget exceeds the existing 15.56 mA margin. A separate host MCU
with a two-wire control interface or a native-host replacement avoids the
SPI pin conflict. A native-host MCU such as
STM32G0B1 is a second Main-only option. Its USB uses PA11/PA12, which the
current board assigns to the two limiter fault inputs, so this option needs
a pin-map and firmware port. The host clock and fault inputs need explicit
design review. A USB 2.0 2:1 switch with an open state is required in either
case. Qualify power-off isolation, hardware default, pin polarity, signal
quality and ESD before selecting a part. No radio pocket or shell change is
needed for the topology study.
[STM32L071 datasheet](https://www.st.com/resource/en/datasheet/stm32l071cb.pdf)
· [STM32G0B1 datasheet](https://www.st.com/resource/en/datasheet/stm32g0b1cb.pdf)
· [MAX3421E datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/max3421e.pdf)
· [USB switch example](https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf)

The [Main space review](../../../cad/evt1-assembly/dock-harness-trial/wired-main-space-review/README.md)
reserves a 20 × 20 mm area under the existing PCB, with 0.90 mm nominal
floor clearance for a 1.5 mm component envelope. The top-side switch
courtyard clears existing footprints at dock X2/Y17, where the limiter-return
via still needs rerouting. The review uses the shifted lower liner and
repaired upper liner.

## Bench path

1. With UV disconnected, use the existing direct USB path to read the
   ESP32-C3 CDC console on a computer. Capture descriptors, endpoint addresses,
   attach timing, and the response to `thermal-status`. Exercise disconnect,
   reinsert and hardware Power/Mode ROM entry. Use a current-limited fixture
   and a reviewed contact stack for the first test.
2. Repeat with a temporary full-speed USB host and the same plug endpoint.
   Confirm enumeration, bounded transfer/timeouts and a clean disconnect on
   contact loss. The existing console command is a smoke test. Use versioned,
   bounded request/response framing with request correlation and validity
   for dock firmware. Reuse the existing 20-byte case telemetry records.
   Keep logs and computer service commands functional. Check CDC DTR/RTS
   handling so the dock does not reset the plug or invoke its bootloader.
   The [framed receiver and host tests](../../../../dock-firmware/case-link-candidate/WIRED-CDC.md)
   exercise the protocol using the real C3 record producer.
   The [Pico bench firmware](../../../../dock-firmware/wired-host-bench/README.md)
   has a smoke image for the existing console and a framed telemetry image.
   The [wired Main RP2040 target](../../../../dock-firmware/wired-main/README.md)
   adds the mux GPIOs and a time-limited local-mode command on I²C.
3. Exercise both paths through the switch with the plug hardware and actual
   dock contact path. Confirm direct PC flashing and ROM recovery with dock
   control held in reset. Verify the idle host branch does not disturb either
   path and that a disconnect clears stale UI data.
4. Retain the existing charge sensing study for later integration. The
   current C3 firmware has tip history and source-loss candidates. Confirmed
   charge completion still needs separate charger observations and fault
   tests. The dock can retain its last fresh attached reading. The plug
   disables USB on source loss, so the first post-loss reading is available
   over USB only after reconnecting within the same boot. Treat ownership
   changes as link events. The wired Main candidate has 15.51 mA of calculated
   margin at the 1.5 A fault allocation with the matching UV sense resistors.
   Qualify startup and cutoff behavior before a powered UV build.
   [Power baseline](../dock-safety/power-budget.json)

The frozen direct-pass-through Main and its matching UV boards remain the
bench baseline. The [merged wired Main layout check](wired-main/layout-candidate/host-local-routing/merged-native-checks.json)
has 120 connections left and one deliberate switch-enable escape warning.
The [active Main project](wired-main/dock-wired-system.kicad_pro) routes the
RP2040 oscillator in its accepted position and connects the PC recovery lock
pull-up, logic input and test pad. Native KiCad reports 26 open connections,
zero other board-rule findings and zero schematic parity findings. The
RP2040 reset, SWD clock, rail and host-bus connections still need work. Use the
[transport schematic](wired-main/dock-wired-transport.kicad_sch) to trace the
display lid and both UV boards.
Use the [four-contact first article](../../../design/evt1-bench-ordering/contact-interface/README.md)
to verify the physical interface before full integration. USB performance
through the received hardware remains to measure.
[ESP32-C3 USB Serial/JTAG](https://docs.espressif.com/projects/esp-idf/en/v5.5.3/esp32c3/api-guides/usb-serial-jtag-console.html)
