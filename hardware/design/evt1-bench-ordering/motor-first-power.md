# First motor power on the bench

Use the selected NFP-E1015 3.7 V motor and the retained body PCB. Keep the
device off-body and the motor secured in a nonconductive bench fixture.
Check the fit separately using the [motor seat witnesses](metal-quote/motor-seat-witness/README.md).
Leave the default motor-disabled plug firmware in place while checking
the motor and the PCB separately.

The [J3 loom](../../cables/evt1/motor-evt1.yml) uses two 80 mm Cooner CZ 1104
starting blanks. At 0.085 Ω/ft, those two untrimmed wires add about 45 mΩ,
20 mV and 9 mW at 0.45 A. Measure the complete installed path, including the
JST contacts, solder transitions and OEM leads, during motor startup.
[Cooner wire data](https://www.coonerwire.com/FEP-hookup-wire/)

| Stage | Connections and observations |
| --- | --- |
| Motor by itself | Use a current-limited bench supply at the rated 3.7 V reference and capture terminal voltage, startup peak, running current and time to speed. Ask NFP for allowable startup and stall current/time and capsule temperature limits for the shipped variant. If current limiting clips a startup, record that condition before interpreting the waveform. NFP lists 450 mA maximum rated current. [NFP motor data](https://nfpshop.com/product/nfp-e1015-encapsulated-vibration-motor-with-metal-cover-7g-vibration-force) |
| Body PCB with dummy load | At J3, pin 1 is MOTOR_P and pin 2 is MOTOR_N. Use a resistor across the pair and differential or isolated voltage sensing. An 8.2 Ω, 5 W resistor is a proposed steady-state load witness, about 0.45 A and 1.67 W at 3.70 V. Start with a higher resistance and a current-limited supply. The 8.2 Ω load represents a DC demand. Capture actual motor startup separately. [Native motor schematic](../../pcb/evt1/body/02-motor.kicad_sch) |
| Rail and hardware inhibit | Scope U3 EN, MOTOR_3V7, U5 IN1 and differential J3. Confirm zero commanded motor output during reset, on dock insertion, and when either arm or PWM is low. Use the existing body hardware gate and default pulldowns. Measure rail startup, drop and ripple through the intended pack range before attaching the motor. [Body native netlist](../../pcb/evt1/body/body-native.xml) |
| Powered cap | After motor lot, body rail and mechanical fit pass, capture the same waveforms in the assembled cap. Record measured case and tip temperature, speed or acceleration, rail reset and source-loss behavior. Set operating and fault limits from the measured assembly and supplier limits. |

## Capture the first pulse after idle

The current PWM frequency is 20 kHz. At the firmware's 25% bench ceiling,
an ordinary high interval is about **12.5 µs**. The DRV8212's PWM mode
can enter autosleep with both inputs low. TI specifies a **100 µs**
turn-on interval and describes holding an input high through that interval
before ordinary PWM. The TPS63070 rail also starts on MOTOR_ARM. The
converter's PG pin has no connection on this revision. Capture the delay
from the first arm edge to regulated VM and the first valid output pulse.
Repeat after long idle and between compass pulses. The existing logic
sets PWM before asserting ARM, then briefly deasserts ARM on each output
update. Scope this behavior before choosing a startup sequence. If the
first command is missed or the rail drops during updates, resolve the
driver wake and rail timing before enabling the motor profile.
[DRV8212 timing and modes](https://www.ti.com/lit/ds/symlink/drv8212.pdf) ·
[TPS63070 startup](https://www.ti.com/lit/ds/symlink/tps63070.pdf) ·
[Firmware outputs](../../../firmware/main/main.c)

For the dummy-load timing comparison, use the normal hardware gate with
the dock disconnected. Hold PWM low while asserting ARM and measure when
VM settles. Then compare ordinary PWM against a bounded continuous input
pulse through the driver's wake interval. The pulse can drive the bridge
forward once awake. Record the differential output and current, including
the pulse, before selecting any firmware behavior. Keep the normal gate
active for stop, dock insertion and reset tests.

Trigger separately on ARM falling and on the charger's PGOOD changing while
the connector makes or breaks contact. Record the delay to U5 IN1 going low,
when J3 current ceases and how long VM takes to decay. The TPS63070 on the
board has no active output discharge, so a residual VM reading is possible
after the bridge command is inhibited. During contact bounce, check whether
J3 resumes output before the firmware observes the dock event. Repeat with
the dummy load and after the maximum intended idle interval.
[TPS63070 variant comparison and shutdown](https://www.ti.com/lit/ds/symlink/tps63070.pdf)
