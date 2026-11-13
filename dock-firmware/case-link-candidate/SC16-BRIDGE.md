# SC16IS750 case UART bridge

`sc16_bridge.c` implements the candidate radio board's I2C UART transport.
It uses address `0x4d`, channel 0 and the 14.7456 MHz oscillator to configure
115200 baud, 8N1 and hardware RTS/CTS. Register setup verifies scratch,
divisor, FIFO mode, IRQ enable and flow thresholds. Auto RTS allows the NINA
to send after setup and then pauses it at 48 RX bytes, with resume at 24.
The bridge leaves GPIO0 as an input and the board pull-up holds the NINA
`UART_DSR` input high. GPIO1 remains an input for NINA `UART_DTR`. The case
transport must establish AT command mode and verify the received module's
UART profile during bring-up.

- [NXP data sheet Rev. 7.1](https://www.nxp.com/docs/en/data-sheet/SC16IS740_750_760.pdf),
  sections 7.2, 7.4, 7.5, 8.3, 8.5, 8.11–8.21 and 10.
- [u-blox NINA integration manual R16](https://content.u-blox.com/sites/default/files/NINA-B1_SIM_UBX-15026175.pdf),
  section 1.7.1, and [u-connectXpress AT manual R56](https://content.u-blox.com/sites/default/files/documents/u-connectXpress-ATCommands-Manual_UBX-14044127.pdf),
  sections 4.4 and 4.15.
- [Project hardware contract](../../hardware/pcb/evt1/case-telemetry-study/hardware-contract.json).

## Integration

1. Supply a shared-bus adapter with one complete transfer deadline. Reads use
   a subaddress write and repeated START. Writes send the subaddress and data
   in the same transaction. Include abort/STOP handling in the deadline. The
   current ADS helper needs adaptation for this transaction shape. Queue I2C
   work under a single owner and give the ADS its existing service budget.
2. After qualified radio enable, wait for the shared hardware reset and
   oscillator startup. Then call `sc16_start_after_reset` and advance one
   transfer at a time until ready. Set up PH0/IRQ as an active-low wake hint.
   Service a pending low level even if an edge was missed, and poll on a
   bounded schedule to cover short RX and TX progress. The bridge needs an
   opportunity to advance between the existing 10 ms case loop deadlines.
3. Call `sc16_send` to queue a complete byte sequence. A full queue returns
   false before it enqueues anything. `sc16_receive` delivers bytes from a
   confirmed burst. Buffer complete NINA replies outside this bridge and
   apply AT/GATT timeouts using the case timebase.
4. On source loss, stop bridge work and discard the radio session. On a bus
   fault, malformed FIFO level or UART line fault, the driver discards both
   software queues and stops bus requests. Abort the higher-level radio
   session and reset the radio before starting again. A failed TX may already
   have delivered a prefix, so retrying the original byte sequence can
   concatenate partial commands.

Each step issues at most one transfer of at most eight data bytes with a
2.5 ms adapter deadline. At 50 kHz an eight-byte repeated-start read uses
99 SCL pulses, about 1.98 ms of ideal wire time. Four transactions surround
one RX burst and take about 4.14 ms total wire time. A TX burst adds two
transactions and takes about 2.52 ms. These are scheduling inputs. Measure
full loaded times with both boards, including CPU overhead, ADS traffic,
clock stretching, rail drop, stuck-bus recovery, and watchdog and UV state
deadlines. Verify that actual NINA CTS honors the FIFO pause and that a
full software RX queue does not exhaust buffering in the module.

## Verification

```sh
make -C dock-firmware/case-link-candidate -f bridge.mk bridge-test bridge-compile
```

The host register/FIFO model checks alternate bank ordering and exact
subaddresses, control readbacks and scratch retention, fixed transfer caps,
short RX, RX/TX backpressure and order through queue wrap, line errors,
ambiguous partial transfers and power-stop/restart. The Cortex-M0+ target
compiles the driver object. Powered bridge/AT tests and integration with the
STM32 I2C driver and case application remain open.
