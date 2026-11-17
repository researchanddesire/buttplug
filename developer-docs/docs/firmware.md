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
| `evt1-one-board` | Bulb battery candidate and debug PCB. GPIO10 also excites the pack monitor NTC. ADS1115 AIN2 reports `pack_temperature_millic` with its own monotonic sample timestamp in device status. |

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
calibration uses the [assembled-device procedure](evt1-electrical.md#factory-compass-calibration).
The EVT1 status characteristic holds a consistent snapshot across BLE read
fragments and exposes the sensor acquisition time and accelerometer validity.
Physical calibration, magnetic settling/accuracy and full template application
remain open. The primary Rad UI is the [plug template editor](plug-templates.md);
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
audit is in `hardware/pcb/evt1/offdock-usb-audit/implementation/validation.json`.
The earlier case-link build binding is `firmware/case-link-validation/validation.json`.
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

The plug also serves framed case telemetry over its qualified USB console. Send
`case-v1 <40 hex digits>` followed by LF or CRLF, with the existing 20-byte
case command as the hex payload. The plug returns a bounded batch of
`case-v1 <kind> <8 hex nonce> <4 hex request ID> <40 hex digits>` lines.
Kind 5 is the final application result. An incomplete batch can be retried with
the same command and identity. The plug preserves each acquisition time and
clears its case peer on detected USB reset, host disconnect or loss of PGOOD.
The wired RP2040 retrieves the latest retained source-loss event after
reconnect and keeps its historical readings separate from the live tip value.
Replay uses plug boot-relative timestamps. The screen continues to show
only the fresh tip reading. See `dock-firmware/wired-main/README.md` for the
dock host behavior and build.
The existing console commands and native PC programming still use this CDC
interface.

The command set reads snapshots, exchanges timing and replays retained
source-loss records. The charge payload carries calibrated VBAT and stable PGOOD
from an actual acquisition group. ISET, TS, CHG and CE remain unavailable, so the
case cannot show confirmed charge completion from this producer. Post-loss
thermal attempts are available on USB after a same-boot reconnect. See the
[wired dock proposal listed in the hardware sources](hardware.md)
for the case host and switch work. Prior BLE case transport remains a separate
firmware study.

The [legacy R0 bench guide](archive/r0-bench-firmware.md) preserves detailed
radio protocol, bench commissioning and TMP117/MC3635 reference instructions.

The dock has a separate STM32L071CBT6 target in `dock-firmware/`. It drives the
selected ST7565R reflective LCD, three controls, interlock/fault display and
30/60/120-second **unqualified UV trial timers**. The default bench profile
uses direct USB pass-through. The wired Main profile adds standalone tip
telemetry. Charge-state sensing and programming progress remain open.

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

The wired telemetry receiver is in
`dock-firmware/case-link-candidate/WIRED-CDC.md`. It decodes tagged CDC
response batches using the existing temperature, charge and source-history
records. The RP2040 wired Main build in `dock-firmware/wired-main/` accepts a
time-limited local USB request on the isolated I²C control bus and clears live
values on detach or handoff. The separate STM32 `PROFILE=wired` target can
request local mode and show fresh tip temperature. Its EVT gesture is a
two-second Right hold with both lid/thermal loops open and the UV trial
stopped. This target requires the matching 4.22 Ω UV boards. Both processor
images build and the host checks exercise switching and stale data.
Powered screen, USB handoff and ROM-recovery checks remain open.
