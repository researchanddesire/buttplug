# Firmware

Three processors run code in the product:

| Processor | Where | Code | Job |
| --- | --- | --- | --- |
| ESP32-C3 | Device board | `firmware/` (ESP-IDF, PlatformIO) | Sensors, motor, buttons, USB console |
| STM32L071 | Dock Main | `dock-firmware/` | Screen, buttons, UV cycle, interlock monitoring |
| RP2040 | Dock Main | `dock-firmware/wired-main/` | USB host in local mode |

None of it has run on EVT1 hardware yet.

## Build

```sh
# Device (from the repository root)
python -m pip install -r firmware/requirements-build.txt
pio run -d firmware -e evt1-one-board

# Dock controller (STM32), host tests then the ARM build
make -C dock-firmware test
make -C dock-firmware PROFILE=wired CROSS=/path/to/arm-none-eabi-
```

The RP2040 host builds with the Pico SDK; see `dock-firmware/wired-main/README.md`.
`evt1-one-board` is the profile for the current device board. The `evt1` and
`prototype-r0` profiles are for earlier boards.

## Flash

The device is programmed over its own USB, through the dock contacts. Put the
dock in PC mode (the default), connect the computer to the dock's USB-C port
and flash the images from `firmware/.pio/build/evt1-one-board/` with esptool,
using the offsets in `flasher_args.json`. If the firmware is not responding,
enter the ROM bootloader: hold **Mode** while holding **Power** for 7.5 s to
reset. The full procedure is in `dock-firmware/wired-main/BRINGUP.md`.

The STM32 is programmed over SWD (Tag-Connect pads J202 on Main).

## What the device firmware does

- **Motor:** starts disarmed. It runs only when armed, within a duty and time
  limit, and never on the dock: the hardware interlock blocks it there.
- **Sensors:** tip temperature about once a second, motion about 10 times a
  second. Each reading carries its age, so stale data is reported as stale.
- **Compass:** heading uses the factory calibration and tilt compensation. It
  is suppressed while the motor runs and when the data is not valid.
- **USB:** attaches once dock power has been stable for 100 ms. The console
  works over USB Serial/JTAG.
- **History:** keeps the last 64 temperature readings and 16 dock power-loss
  events in RAM; they are lost on reset.

## Console commands

| Command | Does |
| --- | --- |
| `status`, `help` | Current readings and the command list |
| `thermal-status` | Temperature history and the latest dock power loss |
| `compass-cal <json>`, `compass-clear` | Store or clear the compass calibration ([how](evt1-electrical.md#factory-compass-calibration)) |
| `case-v1 …` | Framed protocol used by the dock |

## Tests

```sh
sh firmware/tests/run_host_tests.sh
sh firmware/tests/run_evt_console_tests.sh
make -C dock-firmware test
```

## Known gap

The `evt1-one-board` profile still reads the battery thermistor as the earlier
board's pulsed divider. On the current board the thermistor is shared with the
charger's TS pin, so it needs a new conversion. See [Project status](status.md).
