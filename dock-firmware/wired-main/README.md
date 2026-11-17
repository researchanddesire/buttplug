# Wired Main RP2040 firmware

The wired cradle reuses the plug's D+/D− contacts. The computer owns the data
pair at reset. The RP2040 can take ownership on a valid request from the
STM32 while the host branch and contact rail are healthy. The hardware PC
lock retains direct recovery. The source and UV cutoffs remain independent
of this interface.

| RP2040 pin | Main signal | Direction |
| --- | --- | --- |
| GPIO0 | RP_SDA | I²C target data |
| GPIO1 | RP_SCL | I²C target clock |
| GPIO2 | RP_LOCAL_READY | Active-high local select |
| GPIO3 | RP_USB_BREAK | Active-high data disconnect |
| GPIO4 | RP_CONTACT_OK | Active-high contact supply voltage qualified |
| GPIO5 | RP_LIMIT_FAULTn | Active-low local branch fault |

Use separate I²C transactions with STOP at 7-bit address `0x38`. Write three
bytes `[1, mode, crc]` with mode 0 for PC or 1 for local. Renew a deliberate
local request faster than its 750 ms lease. Contact-rail loss or limiter
fault clears the lease. A planned change holds the data path open for
100 ms, changes select, holds it open for another 10 ms, then reconnects.
Hardware faults may override select immediately. The RP2040 host stays
initialized on the isolated side in PC mode. It polls CDC only in local mode.
The RP2040 runs at 48 MHz after startup to reduce branch current. A nominal
750 ms watchdog resets it to the PC defaults if the main loop stalls.
Measure startup current and worst-case enumeration time on the populated board.

If the CDC interface remains mounted after a malformed reply, timeout or
short write, the dock clears its cached telemetry and retries the protocol
after 250 ms. It clears the host FIFOs and terminates a possible partial
command before requesting a fresh snapshot and clock anchor. Request IDs
continue through those retries. When the 16-bit space is exhausted, the
host advances the session ID before sending another command.

After a local USB reconnect, the RP2040 takes a fresh snapshot and establishes
a clock anchor. If the plug reports a retained source-loss event, the RP2040
requests that exact event by sequence and checks its plug boot ID and loss
timestamp. Its RAM holds the latest matched replay with the original plug
timestamps and any retained last docked, first attempt and first valid
readings. Replay records bypass the live-sample age window and cannot refresh
the live temperature. Rapid redocking can yield an interrupted event with no
after-loss sample. A plug reboot clears its retained events. The RP2040 clears
its replay on disconnect and reacquires it when the local host next connects.
The current I²C reply still carries only the fresh tip reading and link
flags. The replay records a source-power observation. Physical removal and
thermal readiness remain unqualified.

Read eight bytes `[1, flags, sequence, tip_lo, tip_hi, 0, 0, crc]`. Flag bits
0 through 5 indicate local mode, switch transition, CDC attached, fresh tip
temperature, contact supply qualified and limiter fault. Temperature is a
signed little-endian centi-degree Celsius value, zero when invalid. CRC-8
uses polynomial `0x07`, zero initialization and no final XOR for both packet
types. The sequence increments on publish. The STM32 client should reject
stale or malformed replies. Contact supply and CDC attachment are electrical
observations. Neither certifies physical seating or removal.

Build the RP2040 image using the [Pico SDK setup](../wired-host-bench/README.md)
and these options. The bench images continue to use UART0. This target uses
those pins for I²C.

```sh
cmake -S dock-firmware/wired-host-bench -B /tmp/compass-wired-main \
  -DPICO_BOARD=pico -DPICO_NO_PICOTOOL=1 -DCOMPASS_WIRED_MAIN=ON
cmake --build /tmp/compass-wired-main
cc -std=c11 -Wall -Wextra -Werror dock-firmware/wired-main/host_control.c \
  dock-firmware/wired-main/test_host_control.c -o /tmp/compass-host-control
/tmp/compass-host-control
```

## STM32 control and display

Build with `make -C dock-firmware PROFILE=wired CROSS=<Arm GNU prefix>`.
The separate image lives at `dock-firmware/build/wired/dock-evt1.bin` and
requires R401 and R501 at 4.22 Ω. The default target retains 3.65 Ω for the
direct USB pass-through bench boards. Use the matched Main R107 and UV boards.

The proposed EVT control is to release the side buttons, then hold **Right**
for two seconds with the lid open and the UV trial stopped. The firmware
requires both lid/thermal loops open, LEFT and CENTER released and no UV
run or arm indication. Repeat to return to PC. On reset or source downgrade
the default is PC. A qualified USB-C source permits the explicit selection.
The screen shows the latest fresh tip value during local mode, plus the
existing UV trial state. The USB screen and controls do not indicate charge
completion or thermal readiness.

The STM32 uses open-drain U201 PH0/PH1 with the external pull-ups on the
isolated host bus. The 5 µs minimum data/clock delays are for Standard-mode.
The transaction has a 3 ms elapsed-time cutoff and the client schedules at
most one transaction per 100 ms. It rejects malformed packets and expires
unchanged status after 250 ms. The UV control outputs are updated before
host transactions. The UV monitor bus and the external watchdog stay
independent. [STM32L071 datasheet](https://www.st.com/resource/en/datasheet/stm32l071cb.pdf)
· [I²C bus timing](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)

The [build report](build-validation.json) records source hashes and linked
symbols. `check_builds.py --help` shows the paths for reproducing the check
against both wired images and the baseline fixture builds. The Pico board
profile is the compile-time starting point for
RP2040/SWD bring-up. Verify selected flash, startup/current, I²C timing,
the proposed button gesture and LCD, and both USB ownership paths on the
assembled Main. Confirm that the hardware PC lock and plug ROM recovery
work with the dock MCU held in reset.
Use the [wired bench procedure](BRINGUP.md) for the first assembled board.
