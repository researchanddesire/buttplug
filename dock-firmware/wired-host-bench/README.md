# RP2040 USB host bench fixture

Use a stock Raspberry Pi Pico as a separate USB full-speed host to exercise
the plug through the four-contact fixture. The firmware uses the native
RP2040 host controller and TinyUSB CDC-ACM. It prints over Pico UART0 at
115200 baud, with GP0 as TX and ground shared with the serial reader.
USB stdio is off so that the Pico's USB port is available to the host stack.
The [four-contact bench kit](../../hardware/design/evt1-bench-ordering/contact-interface/standalone-usb.md)
has the adapter parts, terminal map and verified stock Pico UF2 files.

## Connect the unpowered fixture

- Use a USB cable or breakout that exposes the Pico's D+/D− and common ground.
  Map D+ and D− to their actual spring-contact signals. Keep the pair short.
- Use the existing reviewed protected 5 V contact feed for the plug and an
  independently current-limited supply for Pico VSYS. Share ground and
  keep the two VBUS feeds isolated. Use a data cable/breakout with its VBUS
  disconnected for the Pico host path. The stock Pico port does not provide
  a downstream 5 V source. Verify continuity and polarity before power.
- Isolate the PC's D+/D− path before attaching the Pico host. Leave the dock's
  UV emitters disconnected during USB validation. Start with the plug
  disconnected and a known working protected contact stack.
- Program the Pico in BOOTSEL mode with the matching UF2 or over SWD with
  the ELF, then connect the UART reader.
  Use the smoke build first on the existing plug firmware. It sends
  `thermal-status` once per second and copies incoming serial output.
  The framed build uses the new plug firmware, reads the case records and
  prints request status and temperature quality. Both builds match the
  expected Espressif VID/PID and interface 0. Neither toggles DTR or RTS.

On each build, record descriptors, attach latency, repeated responses,
disconnect, reinsert and a missed-response timeout. Remove the Pico data
pair before reconnecting the PC. Verify direct programming and ROM recovery
separately on the same contact fixture. A successful framed reply alone does
not demonstrate a valid temperature, charge termination or Ready.

## Build

Use Raspberry Pi Pico SDK tag `2.2.0` and its pinned `lib/tinyusb` submodule.
These commands generate ELF, HEX and BIN for review or SWD programming.

```sh
git clone --depth 1 --branch 2.2.0 https://github.com/raspberrypi/pico-sdk.git
git -C pico-sdk submodule update --init lib/tinyusb
export PICO_SDK_PATH="$PWD/pico-sdk"
cmake -S dock-firmware/wired-host-bench -B /tmp/compass-pico-framed \
  -DPICO_BOARD=pico -DPICO_NO_PICOTOOL=1
cmake --build /tmp/compass-pico-framed
cmake -S dock-firmware/wired-host-bench -B /tmp/compass-pico-smoke \
  -DPICO_BOARD=pico -DPICO_NO_PICOTOOL=1 -DCOMPASS_USB_SMOKE=ON
cmake --build /tmp/compass-pico-smoke
```

For BOOTSEL images, use the Microsoft UF2 converter at revision
`70fdee51cf15a487526e88ada2d52346596f80af`. Convert each BIN with
`uf2conv.py -c -f RP2040 -b 0x10000000 -o <output.uf2> <input.bin>`.
The [build report](build-validation.json) gives tool revisions, image
hashes and UF2 readback results.

The [separate wired Main target](../wired-main/README.md) uses the control bus
and switch ownership signals. Timing, clock uncertainty, nonce nonreuse and
installed operation remain bench gates. [RP2040 USB controller](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf)
· [Espressif reference USB descriptors](https://github.com/espressif/openocd-esp32/blob/master/doc/usb_adapters/esp_usb_jtag/303a_1001_esp_usb_jtag.txt)
· [Wired data contract](../case-link-candidate/WIRED-CDC.md)
