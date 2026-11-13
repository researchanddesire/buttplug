# EVT1 application USB dock gate

This implements the bounded application mitigation from the preserved parent audit/proposal. Those original files remain historical source snapshots. Current behavior and checks are bound in `validation.json`; no physical USB, contact-current or isolation result follows from a host test or cross-build.

The application calls `evt_console_transport_init()` immediately after GPIO20 input configuration, before NVS/calibration/driver work. It disables PHY pads first and registers a rising-edge GPIO20 handler. Calibration loading is separate. Attach needs100ms observed power-good; the receiver driver is attempted once per boot, after that qualification. The helper can enable pads even on failure, so policy closes the pads after the attempt and rechecks the physical input and detach generation. A failed RX allocation still permits qualified docked native USB/nonblocking stdout, without repeated allocation attempts.

The detach ISR performs only pad-disable, RX-interrupt masking and a generation increment under an ISR critical section. Hardware FIFO draining, software ring draining, parser clearing and driver APIs stay in task context. A short detach/redock remains visible through the generation even if GPIO20 is already low when the task resumes. No old partial line, queued command or local read buffer is admitted into the new session. Pads are also disabled before application-controlled deep sleep and by a shutdown hook. The USB bus clock and GPIO18/19 mux/pull-override fields are left unchanged.

The hardware/SDK boundary tests compile the real `evt_console.c` against controlled LL, GPIO, USB-driver and NVS stubs, with the real calibration math linked. They cover boot undocked/docked, qualification surviving ordinary polling, bounce/brief detach, partial and complete queued commands, detach during read, failed installation and redock without retry, detach inside successful/failed installation, hardware/software stale RX, healthy-session RX preservation, sleep/shutdown and detach at NVS entry. Existing control/compass/thermistor/wear host suites run separately with UBSan.

Generation checks reject stale commands and recheck before NVS calls. An already-issued NVS set/commit can finish after the edge; it cannot be retroactively cancelled. This is not a zero-after-edge flash-write claim.

Run:

```sh
sh firmware/tests/run_evt_console_tests.sh
sh firmware/tests/run_host_tests.sh
PLATFORMIO_BUILD_DIR=/private/tmp/compass-usb-gate-build pio run -d firmware -e evt1 -e prototype-r0
python3 hardware/pcb/evt1/offdock-usb-audit/implementation/record_validation.py
```

The evidence recorder checks the saved build logs, current source/SDK hashes, preserved baseline artifacts and linked ISR sections. It saves the selected ISR disassembly and symbol tables beside `validation.json`; it does not rerun the tests, rebuild or flash a device.

Both profiles cross-compile without warnings. In the EVT1 ELF, the normal detach path, GPIO dispatcher and critical-section helpers are in IRAM, the bit-scan helper is ROM, and state is DRAM. The pad-off helper contains only MMIO and no calls. The SDK's corrupted-critical-nesting assertion branch retains flash diagnostic strings; this check covers the normal balanced path and does not extend the policy to panic/corruption.

The isolated build path preserves the existing `.pio/build` artifacts. `baseline.json` records the old source hashes from the frozen audit and existing artifact hashes. One old prototype ELF was cloud-dataless and a read timed out; it is retained untouched and explicitly has no newly verified hash. Historical build reports are not substituted for a current byte check.

The policy is restricted to BOARD_EVT1 and the audited ESP32-C3 ESP-IDF5.5.3 LL. Legacy firmware remains outside this application gate. ROM, startup/reset, a hung CPU, physical ISR latency, ordinary pad state and all exposed-contact voltage/current still require measurement. Charger power-good is not mechanical seating or proof of dry contacts. The new PCB-mounted contact subassembly must retain these limits and be tested for U75 steering/backbias as well as enumeration, flashing and recovery.
