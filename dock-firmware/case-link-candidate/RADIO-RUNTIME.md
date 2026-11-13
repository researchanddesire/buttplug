# Scheduled radio bring-up

The alternate STM32 image uses the routed dock controller's control pins with
the [case radio schematic](../../hardware/pcb/evt1/case-telemetry-study/PROPOSAL.md).
The radio additions to the Main board and the radio board are at schematic
stage. Use the standard dock image for the frozen 3.65 Ω UV boards. The
alternate image expects 4.22 Ω at both UV monitor inputs.

Each 10 ms target frame starts with ADS and NTC sampling, interlock state and
outputs. An LCD update renders the buffer in one frame and transmits one page
per eligible frame thereafter. The watchdog pulse follows that frame's
control and scheduled LCD work. After the pulse, the scheduler checks for
four ticks of apparent slack before each SC16 operation and allows up to
three operations per frame. The I²C adapter reserves up to 2.5 ms for a
transfer and its abort. The timing allowances need measurement on the board.
The LCD can skip a slice when control runs long.

PH1 requests radio power only with a qualified 1.5 A or higher source. Allow
150 ms off before a new request and 150 ms after enabling before bridge
setup. A radio startup fault drops the request and holds it off until source
loss. A failed monitor sample, control frame over 100 ms or bus that remains
busy after abort drops radio power before fail-stop.
The hardware source, lid and thermal cutoffs remain in the circuit.

Run from the repository root with the Arm GNU toolchain available.

```sh
make -C dock-firmware/case-link-candidate -f radio-runtime.mk radio-runtime-test radio-runtime
make -C dock-firmware/case-link-candidate -f nina-startup.mk nina-startup-test
```

The linked image is `build/dock-radio-schedule.elf`. SWD can inspect
`dock_radio_at_state`, `dock_radio_at_fault` and `dock_radio_bridge_fault`.
[UART startup](NINA-STARTUP.md) ends after the command channel and profile
readback. The diagnostic retains that result and polling stops until source
loss. BLE discovery, pairing, GATT and the case telemetry display remain future
integration.

For board bring-up, measure frame duration, watchdog pulse intervals, ADS
scan freshness, I²C idle after abort, rail/reset timing and SC16 UART
traffic with concurrent LCD updates and source loss. Verify the 45–75 mA
software window on received 4.22 Ω hardware across source, temperature and
measurement tolerance. A nominal 200 mV sense voltage is 47.393 mA. At
196 mV and a +2% resistor corner, 45.53 mA leaves about 0.53 mA above the
software floor before measurement error. Qualification also requires powered
interlock and UV measurements.
