# Standalone USB through the four-contact fixture

Use this bench setup to test the same contact pair that the finished cradle's
RP2040 will use. Start after the [direct PC contact test](README.md#assemble-and-measure)
passes on the same plug and fixture. Leave both UV modules disconnected.

| Item | Qty | Connection |
| --- | ---: | --- |
| Raspberry Pi Pico H **SC0917** | 1 | Stock RP2040 board with headers. Use the Micro-B port for BOOTSEL and, after recabling, for the host data pair. [Pico datasheet](https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf) |
| Adafruit **3972** Micro-B plug to terminals | 1 | B is D−, C is D+, E is ground. Leave A (VBUS) and D (ID) open. Use short 26 AWG pigtails in the terminals and insulate joints to the paired 28 AWG fixture wires. [Adapter pinout and wire size](https://www.adafruit.com/product/3972) |
| Adafruit **4364** USB-C to TTL serial cable | 1 | Connect yellow RXD to Pico GP0 (pin 1) and black GND to fixture ground. Leave the remaining cable sockets open. Read at 115200 baud, 8N1. [Cable pinout](https://www.adafruit.com/product/4364) |
| Regulated current-limited bench channel | 1 | Supply 5.0 V to Pico VSYS (pin 39), with return to Pico GND (pin 38) and fixture ground. Use a separate protected 5 V contact feed for the plug. [Pico power and pinout](https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf) |
| Known data-capable USB-A to Micro-B cable | 1 | Load the stock Pico UF2. Disconnect it before attaching the Micro-B terminal adapter or applying VSYS power. |

## Change from direct PC to Pico

1. Disconnect the plug and turn off both supplies. Remove the USB data wires
   from the direct Main's J102.2/.3. Keep Main J102.1 and its reviewed
   protected J102.4 feed connected to the pin board. Verify the Main still
   supplies valid contact voltage with no data device attached to the Main
   USB path. Use a qualified source at J101 and keep the UV outputs unloaded.
2. Connect adapter B to J94.2/P92 (D−), C to J94.3/P93 (D+), and E to
   J94.1/P91 (GND). J94.4/P94 keeps the protected contact 5 V. Pico VSYS
   and the contact feed share ground and have separate positive rails.
3. With both supplies off, verify the two signal paths end to end, both
   Main data pads are isolated from the Pico pair, and neither Pico adapter
   VBUS nor VSYS connects to the contact 5 V. With the plug absent, check
   rail polarity and voltage separately. Power down before changing hosts.

## Load firmware and record the test

Extract the [Pico UF2 pair](Compass-Pico-USB-Bench.zip). Hold BOOTSEL while
plugging the Pico into the computer and copy `compass-wired-smoke.uf2` to
`RPI-RP2`. Disconnect the programming cable before switching to the bench
wiring above. The smoke image issues `thermal-status` once per second. Log
enumeration, repeated replies, removal and reseat on UART. Repeat with
`compass-wired-host.uf2` and a plug running the `evt1` profile with
`case-v1` support for framed telemetry. Build that plug profile with
`pio run -d firmware -e evt1` from the same checkout. Keep the motor
uncommissioned for this USB test.
Capture reply status and whether the temperature was valid, then exercise
loss of contact and a response timeout. [Firmware source and build](../../../../dock-firmware/wired-host-bench/README.md)

Record the boards and image hashes, contact voltage at the plug, attachment
latency, and UART log. Successful runs establish communication through the
sampled fixture. The integrated Main's USB switch, source sequencing and
service override need their separate [installed test](../../../../dock-firmware/wired-main/BRINGUP.md).
