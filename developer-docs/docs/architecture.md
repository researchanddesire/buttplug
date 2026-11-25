# Design decisions

## Packaging before layout release

The device uses bulb volume for the battery and a thin flange for electronics.
One integrated PCB removes the neck interboard loom, while a separate cradle
and removable guide support the pack and dress seven conductors. The metal
body/cap, flange joint, buttons and skin are designed as an assembly rather
than as independent envelopes. See [How the device works](device.md).

## Power and sensing

The protected 1S pack feeds the charger/power path and separate logic/motor
rails. Dock 5 V supplies the charger; the pack's PCM provides discharge
protection. The motor driver retains hardware docking inhibition and firmware
arming/lease limits.

There are two temperature jobs. The cap NTC measures the tip beside the motor;
its pulsed ADC acquisition supports thermal history. The pack's built-in NTC
serves the charger TS hardware cutoff and ADC AIN2. Sharing that NTC reduces
cell-side wiring, but requires a different conversion from the old pulsed
pack divider. That firmware change remains open.

<span id="smart-cradle-and-four-contact-interface"></span>

## USB ownership

The same four contacts provide power and native ESP32-C3 USB in both dock modes.
Main switches the data pair between the PC and a local RP2040 host; the STM32
owns the dock UI and UV controls. PC is the reset default, with a hardware
recovery lock. This gives standalone telemetry without adding a dock radio.
The [dock page](charging-dock.md#usb-pc-mode-and-local-mode) explains the paths and switching.

## Compass mode

LSM303AGR accelerometer and magnetometer frames register to the flange's −X
arrow. Tilt compensation uses gravity; magnetic calibration corrects the
assembled device separately. Cap thread clocking is not the heading reference.
Motor current, metal and dock magnets require a field survey, not an assumed
software correction. Output is suppressed when known calibration, age, field,
motion or motor/settling conditions make heading unusable.

## Thermal history and readiness

Keep source loss, physical removal and thermal readiness as separate facts.
The plug's RAM history preserves timed NTC attempts and source-loss candidates;
the wired host can replay same-boot records. Reboot/deep sleep discards them.

The required Charging → Charged—cooling → Ready flow additionally needs
confirmed charge state, contact-region temperatures and qualified thermal
criteria that include UV heat. The current screen's UV-arm READY state is a
different state. Details are in the [dock page](charging-dock.md#screen-and-buttons)
and [thermal study](thermal-presence-study.md#charging-case-baseline-and-cooldown).

The [Rad template integration](plug-templates.md) controls the app-facing design.
No qualified wear classifier or live Lockbox credit follows from temperature,
motion or these source-loss records.
