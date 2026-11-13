# Off-dock device USB source audit

The current application does not electrically disconnect USB when undocked. Its receive-driver initialization enables the USB PHY without testing physical dock presence. Firmware can reduce active application bias, but application code cannot guarantee quiet contacts before it runs, during ROM download, or across every reset. No voltage, leakage current or human-contact suitability was measured or inferred.

This is a read-only audit. Firmware and PCBs remain unchanged. `evidence.json` binds the inspected sources and reports; ten installed SDK files match the official ESP-IDF `v5.5.3` tag byte-for-byte. PlatformIO selects `espressif32@6.13.0`; the installed framework reports `5.5.3`.

## Actual electrical contract

Saved `flange-native.xml` identifies U6 as ESP32-C3-MINI-1-N4X and the following connections:

| Role | Native path |
| --- | --- |
| USB D− | U6.26 / GPIO18 → USB_DM → R75,22Ω → USB_DM_CONTACT → J1.2 |
| USB D+ | U6.27 / GPIO19 → USB_DP → R76,22Ω → USB_DP_CONTACT → J1.3 |
| Contact return | J1.1 → GND |
| Contact supply | J1.4 → DOCK_5V; U75.5 also uses this net |
| Physical power-present input | Flange J7.7 → DOCK_PRESENT_N → U6.30 / GPIO20. Body U1.7,/PGOOD and J6.7 use the same logical interboard signal. This indicates valid charger input, not mechanical closure. |
| Mode / recovery | Mode is GPIO3/U6.6; D73 links MODE_N with BOOT_N/GPIO9/U6.23. R33 and R34 provide10k pullups for GPIO8/BOOT respectively. J4.4 exposes MCU_EN and J4.5 BOOT_N. |

This is saved netlist evidence, not received-wire continuity or a new routing/fabrication check. Contact order is GND/D−/D+/5V; changing to a PCB-mounted contact subassembly does not remove the electrical behavior described here.

U75 is USBLC6-2SC6. Its contact-side data nodes use rail-to-rail protection with VBUS tied to DOCK_5V. An enabled D+ pullup can plausibly forward-bias its upper steering path toward the supply contact. That is an electrical inference requiring measurement, not a predicted voltage/current. The datasheet's reverse-leakage specification is not a whole-product exposed-contact limit. [ST USBLC6-2, functional diagram and cell model](https://www.st.com/resource/en/datasheet/usblc6-2.pdf).

## Current application and SDK behavior

`main.c` configures GPIO20 as a pulled-up input, then calls `evt_console_init()` unconditionally. The initializer loads calibration and installs the interrupt-driven USB receive driver. `evt_console_poll()` runs every loop; only calibration-changing commands test the docked Boolean. These guards do not disconnect the pads. The configuration selects primary USB Serial/JTAG console and enables the module; power management is disabled.

The IDF driver enables the module clock and applies C3 PHY defaults during installation. Uninstallation frees its interrupt and buffers but deliberately preserves the clock and pad enable for stdout. The C3 startup clock code disables unused USB only when both USB-module and USB-console configurations are off; the present configuration takes neither condition. The host-connection monitor tracks USB SOF traffic, not the GPIO20 input, and does not electrically disconnect the pads. [Pinned driver](https://github.com/espressif/esp-idf/blob/v5.5.3/components/esp_driver_usb_serial_jtag/src/usb_serial_jtag.c), [startup](https://github.com/espressif/esp-idf/blob/v5.5.3/components/esp_system/port/soc/esp32c3/clk.c), [connection monitor](https://github.com/espressif/esp-idf/blob/v5.5.3/components/esp_driver_usb_serial_jtag/src/usb_serial_jtag_connection_monitor.c).

The C3 register header gives reset values USB_PAD_ENABLE=1, DP_PULLUP=1, DM_PULLUP=0 and PAD_PULL_OVERRIDE=0. The LL default initializer sets USB pad enable to1; its dedicated pad-enable function can clear it. These values do not specify a measured waveform for every reset cause or a contact-current limit. [Pinned register definitions](https://github.com/espressif/esp-idf/blob/v5.5.3/components/soc/esp32c3/register/soc/usb_serial_jtag_reg.h), [PHY LL](https://github.com/espressif/esp-idf/blob/v5.5.3/components/hal/esp32c3/include/hal/usb_serial_jtag_ll.h).

GPIO19's pullup-disable helper also changes the USB pull override, and choosing an IOMUX function on GPIO18/19 clears USB pad enable. A generic GPIO reconfiguration followed only by receive-driver reinstallation is therefore an incomplete restoration plan: the PHY default initializer does not restore those pull-override fields. [Pinned GPIO LL](https://github.com/espressif/esp-idf/blob/v5.5.3/components/hal/esp32c3/include/hal/gpio_ll.h).

## Boot and sleep boundaries

| State | Source-supported limit |
| --- | --- |
| Power-on / ROM / download | USB is enabled by default after power-on. The application's dock policy has not run. Do not claim off-dock isolation here. |
| Second-stage boot | The selected console routes output through ROM USB before application initialization. |
| Awake application, undocked | Current code enables the PHY. The proposed policy changes this state only. |
| Deep sleep | Espressif documents controller/PHY power-off and removal of the D+ pullup. Wake returns through startup; a firmware policy must run again. |
| Light sleep | The guide says D+ remains pulled up. In the exact5.5.3 implementation, C3's unsupported-light-sleep branch backs up and disables the pad/clock, then restores the prior state on wake. Record this documentation/source discrepancy and measure it; do not use light sleep as an isolation guarantee. Current app has no manual light-sleep call and PM_ENABLE is off. |
| Watchdog, panic, brownout or software reset | Peripheral retention and boot paths vary. No universal quiet-pad interval is established by this audit. |

The guide documents native USB flashing and manual GPIO9-low reset recovery; reliable download also requires GPIO8 high. The saved circuit supports the intended Mode/Power and service EN/BOOT paths, but received levels, reset timing, actual eFuses and recovery must be tested. Do not burn USB/download-disable eFuses as an off-dock workaround. [IDF5.5.3 console/sleep guide](https://docs.espressif.com/projects/esp-idf/en/v5.5.3/esp32c3/api-guides/usb-serial-jtag-console.html), [pinned sleep preparation](https://github.com/espressif/esp-idf/blob/v5.5.3/components/esp_hw_support/sleep_modes.c), [pad backup/restore](https://github.com/espressif/esp-idf/blob/v5.5.3/components/esp_hw_support/sleep_console.c), [boot console](https://github.com/espressif/esp-idf/blob/v5.5.3/components/bootloader_support/src/bootloader_console.c), [Espressif boot-mode guide](https://docs.espressif.com/projects/esptool/en/latest/esp32c3/advanced-topics/boot-mode-selection.html).

See `PRIVATE_PROPOSAL.md` for the bounded application mitigation and required measurements. It does not qualify the new contact module or make an all-states isolation claim.
