# Firmware

Use the `evt1` profile with the new four-contact electrical revision. It adds
pulsed thermistor/ADS1115 readout, fixed LSM303AGR sensing, USB telemetry and
assembly calibration, dock-wake button handling and hardware-reset recovery.
The five PCBs pass native DRC; the full product still needs selected pack/parts,
loom, final seals and complete compass behavior.

| Profile | Hardware |
| --- | --- |
| `evt1` | `hardware/pcb/evt1/`: two-wire NTC, ADS1115, fixed LSM303AGR, four contacts and independent reset circuit. |
| `prototype-r0` | Former TMP117 and MC3635 hardware. GPIO10 is an interrupt input; this profile does not operate the EVT1 thermistor circuit. |

```sh
pio run -d firmware -e evt1
sh firmware/tests/run_host_tests.sh
sh firmware/tests/run_evt_console_tests.sh
sh firmware/tests/run_case_radio_tests.sh
```

The [EVT1 electrical/firmware guide](evt1-electrical.md) describes pin changes,
USB commands, calibration format, checks and limits. Both profiles pass clean builds with explicit version `0.1.0-dev`;
host tests cover control faults, thermistor fixtures and 1,680 known compass
pose/calibration cases. No hardware flash, USB enumeration, sensor-bus, wireless,
power, thermal or wear result exists.

Motor output is disabled by default until pack, motor and thermal limits are
configured from measurements. Local arming, bounded duty/lease, sensor validity,
watchdog and the hardware dock inhibit remain. A direction-pulse candidate and
configurable mapping/wear-accounting helpers now have host tests. Factory
calibration, measured magnetic settling/accuracy and full template application
remain unfinished. The primary Rad UI is the [plug template editor](plug-templates.md);
its wear-credit boundary is not connected to an actual Lockbox timer.

On EVT1, hold Power for at least7.5s to request an independent hardware reset;
hold Mode during reset for ROM USB download. The four-contact dock provides
power and native ESP32-C3 USB. The circuit and code are implemented candidates;
button mechanics, reset timing and recovery must be tested after assembly.

EVT1 holds USB PHY pads off until physical GPIO20 (`DOCK_PRESENT_N`, charger
power-good) remains low for 100 ms. The application installs the pad gate directly
after configuring that input, before NVS/calibration and receive-driver setup.
A rising-edge ISR disables pads first and records a detach generation; the main
task then clears parser state and hardware/software RX. A brief detach/redock
therefore invalidates an old partial or queued command even when the input is
already low again. The RX driver is attempted once per boot after qualification;
failure leaves the same dock gate active and still permits docked native USB
programming/nonblocking stdout. Calibration loading does not start USB.
Generation checks reject stale commands and check presence before NVS work;
an already-started NVS set/commit can still finish after detach and cannot be
cancelled retroactively.

The pad gate uses the audited ESP32-C3 ESP-IDF 5.5.3 LL, retains the console bus
clock, and changes no GPIO18/19 pull overrides or eFuses. Host boundary tests
exercise startup, bounce, partial/queued commands, detach during driver/read/NVS
entry, failed installation, redocking and sleep/shutdown. The preserved USB
audit is in `hardware/pcb/evt1/offdock-usb-audit/implementation/validation.json`;
the current EVT1 and legacy build binding is
`firmware/case-link-validation/validation.json`.
ROM, early boot/reset, a hung CPU and actual exposed-contact voltage/current
remain outside this application-only result; USB enumeration/flashing and
received contact-module leakage still require bench measurements.

EVT1 now retains 64 distinct tip-NTC attempts and 16 source-loss candidates in
RAM. Each attempt keeps its actual start/completion times and validity; cached
10 Hz motion polls do not refresh the 1 Hz temperature age. A loss records the
last fresh docked sample, its age and a contiguous valid trend, then captures
the first valid conversion begun after the observed loss. Conversion straddles,
sensor faults and reconnection before that conversion cannot supply a fresh
removal baseline. The raw ISR edge count also exposes losses that reconnect
between polls; individual unobserved edge times are not invented.

Read `thermal-status` over qualified docked USB for the latest timestamped
snapshot. Its `physical_removal_confirmed` is always false; charge and UV state
remain unknown pending their separate hardware/data integration. The bounded
history has a per-boot ID and monotonic timestamps, no UTC or flash persistence;
reset/deep sleep discards it. Host tests cover timing, faults, early loss,
reconnection and ring limits. This does not implement a wear classifier or
thermal Ready threshold. See `firmware/main/thermal_history.h` and the case
telemetry proposal listed in [hardware sources](hardware.md).

The EVT1 candidate adds an authenticated BLE case service for timestamped
temperature, measured battery voltage, power-good and retained source-loss
records. It leaves uninstrumented charger fields unavailable. Its commands
read snapshots, exchange timing and retrieve history; the case service has no
actuator or charger commands. The plug builds and C3-to-STM32 decoder roundtrip
pass digitally. The case radio circuit/transport, pairing and powered
interoperability remain open. Computer USB programming uses the separate native
USB path.

The alternate dock radio runtime (`dock-firmware/case-link-candidate/RADIO-RUNTIME.md`)
services the monitor and control outputs before scheduling the LCD and UART
bridge in 10 ms target frames. It links for the STM32L071 and verifies the
NINA command channel and UART profile in host tests. It expects the 4.22 Ω UV
resistors of the radio schematic. The separate GATT transport now passes a
host UART roundtrip with the actual plug sender for service discovery,
subscriptions, snapshot and time sync. See
`dock-firmware/case-link-candidate/NINA-GATT.md`. Peer commissioning, runtime
integration, board timing and powered verification remain open.

The [legacy R0 bench guide](archive/r0-bench-firmware.md) preserves detailed
radio protocol, bench commissioning and TMP117/MC3635 reference instructions.

The dock has a separate STM32L071CBT6 target in `dock-firmware/`. It drives the
selected ST7565R reflective LCD, three controls, interlock/fault display and
30/60/120-second **unqualified UV trial timers**. USB data passes directly to
the device ESP32-C3; the dock displays neither battery state nor programming
progress because it has no corresponding data channel.

```sh
make -C dock-firmware test
make -C dock-firmware CROSS=/path/to/arm-none-eabi-
```

The dock target cross-compiles with official Arm GNU13.3.Rel1 and includes
source-bound host behavior checks. Reset/fault/timeout remove ARM and STOP
permission. Starting requires a physical press/release followed by a fresh
press; firmware cannot generate the hardware latch's press clock. Lid/thermal
loops, source qualification, reset/watchdog and power cuts remain independent
hardware functions. A heartbeat pulse follows a completed healthy main loop.
Read `dock-firmware/README.md` and `validation.json` for the exact GPIO/ADC/LCD
contract, binaries, tests and limits. No dock board has been flashed or powered,
and completing a timer establishes no optical dose or cleaning result.
