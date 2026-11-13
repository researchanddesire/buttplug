# STM32L071 I²C2 adapter for the case radio

`stm32_sc16_i2c.c` is the SC16IS750 callback candidate for the dock's shared
I²C2 bus on PB10/PB11. It expects the current MSI range 6, unity APB1
prescaler and `TIMINGR=0x0042272B`, about 50 kHz at the nominal 4.194304 MHz
clock. It leaves that configuration in place and uses the free TIM2
counter for one deadline across the entire exchange and abort. It does not
touch dock outputs, UV control, watchdog, USB or charger state.

The read writes one subaddress byte in software-end mode, waits for TC,
then issues a repeated START with a read and automatic STOP. The write
sends subaddress and up to eight payload bytes in one automatic-STOP
transaction. A successful read publishes the bytes after STOP. A failed
transaction can have moved bytes at the SC16, so the higher-level radio
session must be discarded. The adapter clears the controller BERR flag
according to ES0292 §2.12.4, with byte and STOP completion still required.
Software timing replaces the SMBus timeout feature absent on I²C2.

## Scheduler handoff

1. After the existing board setup, reserve TIM2 and call
   `case_sc16_i2c_init` with sole ownership of the idle bus. Configure
   PH1 as a default-low GPIO output for the radio request. The adapter
   samples PH1 and hardware SOURCE_OK on PC15 before starting and while
   waiting for bytes. The gated enable and hardware reset still own radio
   power and isolation. Start the bridge only after qualified crystal and
   reset timing.
2. Bind `case_sc16_i2c_transfer` with a `case_sc16_i2c` context. Give ADS1115
   monitor work priority on the same serialized bus. Admit an individual
   bridge step only if at least 2.5 ms plus measured scheduler/IRQ overhead
   remains before the next control deadline. Budget against actual PVT bus
   timing. The adapter does not disable interrupts, and ISR latency is
   additional to the execution deadline.
3. On source loss stop the bridge and discard the radio session. A NACK
   normally terminates with the hardware STOP. On other faults the adapter
   requests STOP when it owns the bus. It reserves the last 100 µs of the
   2.5 ms budget for abort and final checks, and can release the controller
   through PE after a wedged transaction. It does not issue STOP after
   arbitration loss or pulse SCL to recover an external target. A busy bus,
   held line or PE reset latches `bus_needs_recovery`. Drop the radio request
   to isolate the branch and treat ADS measurements as unqualified until the
   Main bus and a fresh ADS scan are verified. Reinitialize only with the
   bus idle and both lines released, then reset the radio before restarting.

TIM2 counts APB1 clocks and rolls over every 65,536 ticks. The transfer
uses a 10,000-counter-tick budget per requested 2.5 ms. A second,
1,000-poll guard prevents endless waits if the counter stalls. The
conversion assumes a verified 4 MHz minimum kernel clock. ES0292 §2.12.3 also requires
that clock floor for a target at the 250 ns standard-mode data setup
minimum. Check the MSI floor over the intended voltage and temperature
range, or retune the shared bus clock and deadline in the integration
candidate. Confirm the exact 99-clock eight-byte read, rise/setup times,
NACK and source-loss recovery on the actual combined bus. Check ADS scan
cadence, I²C stalls and loaded loop/interrupt latency alongside the existing
UV stop and watchdog tests.

The host model exercises the register writes, wrap, read/write sequences,
NACK, arbitration, early STOP, source loss and stalls. The separate ARM
link fixture resolves the adapter against the bridge callback. It has no
startup vector table or board initialization and serves only as a link
check. The production dock build and hardware remain unchanged.

```sh
make -C dock-firmware/case-link-candidate -f adapter.mk adapter-test adapter-compile
```

[ST RM0377 §§23.3–23.7](https://www.st.com/resource/en/reference_manual/rm0377-ultralowpower-stm32l0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf) ·
[ST ES0292 §2.12](https://www.st.com/resource/en/errata_sheet/es0292-stm32l07xxxl08xxx-device-errata-stmicroelectronics.pdf) ·
[ST DS10690 MSI characteristics](https://www.st.com/resource/en/datasheet/stm32l071cb.pdf) ·
[SC16IS750 bridge and wire-time budget](SC16-BRIDGE.md)
