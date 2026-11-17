# EVT wired dock Main

The cradle uses its four existing contacts for PC programming and standalone telemetry, with no cradle radio or antenna. The ESP32-C3 remains the USB device in both modes. A full-speed host on a separate RP2040 handles local USB while the STM32L071 retains the screen, buttons, watchdog and UV controls. Both upstream choices use the existing `CONTACT_5V` and ground. The RP2040 has no VBUS source tied to either connector.

The first build should use deliberate local mode selection. A host PC can advertise 1.5 A or 3 A, so `SOURCE_OK` only qualifies available power. It does not authorize taking the USB pair from a computer. A separate hardware PC lock clamps the local-enable logic low even with the two processors stalled. The host rail currently starts whenever qualified power and the lock/reset permissives are present. That lets the STM32 request local mode over the isolated two-wire interface. An independent local power request could reduce PC-mode draw in a later revision. The prototype recovery fixture must make the two shorting pads accessible with the product on the dock and the lid open, then power-cycle the dock with the short held. An enclosure-level access solution is still open.

## Data and recovery

U151 is the onsemi FSUSB42MUX, MSOP-10. Its common D+ and D− go to J102.3/.2. The first channel goes to J101 through retained U121. The second goes to RP2040 pins 47/46 through individual 27 Ω resistors at the RP2040. The common contact side gets separate low-capacitance shunt protection near J102. Its clamp returns to ground. U121 remains on the PC side with its existing `HOST_5V` reference. The switch has an independent active-low enable, a published 2 ns minimum break-before-make under the datasheet fixture conditions, and ±2 µA per-port power-off leakage over the stated test range. The 2 ns prevents overlap under those conditions. Firmware uses a much longer open interval for a planned USB detach.

At reset, the RP2040 request and blank outputs are low. With valid Main power, the switch defaults to PC. On startup use the existing delayed `CC_ENABLE` as the Main rail qualifier. A hardware falling `SOURCE_OK`, `SAFE_RESETn`, rail-valid or PC-lock condition removes local selection regardless of firmware. A forced or brownout transition can end a transfer. Hold the hardware PC lock during a service power-cycle before plug ROM entry if the dock is unresponsive.

In normal service, keep PC selected until the user requests local mode, the new branch is healthy, and the RP2040 USB host is initialized. Assert `USB_BREAK` for an initial 100 ms fixture interval, switch select while open, then remove the break. Return to PC by the same sequence after stopping local I/O. Clear the locally cached current reading on detach or timeout. If qualified source power is unavailable, return an unavailable state and keep PC ownership. Local and PC data access are exclusive. A PC-driven read can supply its own measurements during programming or diagnostics.

The existing Espressif console implements CDC over the native USB Serial/JTAG composite function. Espressif documents VID/PID `303a:1001` for its development-board example. TinyUSB's RP2040 host controller and CDC-ACM class are available. Identify the actual plug descriptors and endpoint/interface numbers before binding code. Enable the ACM host path, whitelist the intended device using the enumerated descriptor, and leave the vendor JTAG interface for the PC. Leave TinyUSB `CFG_TUH_CDC_LINE_CONTROL_ON_ENUM` undefined and avoid automatic DTR/RTS changes during local mounting because the ESP32-C3 USB Serial/JTAG interprets control line transitions for reset. Confirm hardware Power/Mode ROM entry and direct PC flashing with both case MCU reset points held and the recovery lock applied.

[RP2040 datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) · [Raspberry Pi hardware design](https://pip-assets.raspberrypi.com/categories/814-rp2040/documents/RP-008279-DS-2-hardware-design-with-rp2040.pdf) · [onsemi FSUSB42](https://www.onsemi.com/pdf/datasheet/fsusb42-d.pdf) · [TinyUSB CDC host source](https://github.com/hathach/tinyusb/blob/master/src/class/cdc/cdc_host.c) · [Espressif USB console](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-guides/usb-serial-jtag-console.html) · [Espressif descriptor example](https://docs.espressif.com/projects/rust/no_std-training/02_1_hardware.html) · [Espressif reset behavior](https://docs.espressif.com/projects/esptool/en/latest/esp32c3/esptool/advanced-options.html)

## Power

The existing hardware-qualified Type-C gate controls the separate `USB_HOST_5V` branch from the existing `HOST_5V` input. TPS2553QDBVRQ1 ILIM is tied directly to IN, the datasheet's 50/75/100 mA DC setting. The host target is at most 40 mA measured at J101 as a branch increment, giving 10 mA against the published minimum limit. This is a test limit. Raspberry Pi's BOOTSEL device-mode measurements give 21 mA at the sum of listed maximum average chip-rail values. The vendor's other workload exceeds 50 mA summed and neither workload represents local host traffic. Qualify actual clock speed, boot, QSPI flash, attach/reset, CDC traffic, SWD servicing, temperature and inrush. In particular, firmware does not write external flash during normal local service.

Reserve 104 mA for the new branch and all added control loads when qualified. At default USB100, the host branch is physically disabled and the existing 70 mA device and 10 mA UI allocations remain. A separate 1 mA allowance covers always-on additions in that mode. The 81 mA steady-state sum is separate from suspend, inrush, dynamic source downgrade, and recovery at a depleted plug battery. The existing device hardware limit can be as low as 34 mA in that mode. The existing PC bypass cannot guarantee standards compliance across USB suspend merely by meeting 100 mA while active.

To retain local USB during UV on a 1.5 A source, the proposed matching population is Main R107 40.2 kΩ 0.1% and UV R401/R501 both 4.22 Ω 1%. The new study computes both the fault ceiling and regulated UV operating point using the same physical path boundaries as the frozen source budget. The source limit and UV LED current must be considered as one assembly choice. The reduced drive requires fresh optical, leakage and thermal validation. Firmware must use the same 4.22 Ω conversion. Never fit a 104 mA branch alongside the frozen 34.8 kΩ and 3.65 Ω configuration for 1.5 A operation.

A separate TPS7A2033PDBVR LDO supplies the RP2040 and flash. Its 3.3 V output tolerance is ±1.5% in regulation. Verify at least 3.60 V at LDO IN and 3.135 V at RP2040 USB_VDD over load, transients and temperature. A local supervisor with a separate rail-valid output holds RUN low through bring-up. Decouple each IOVDD pin, both DVDD pins, USB_VDD and ADC_AVDD. Retain the Raspberry Pi 1 µF regulator input and output capacitors; use at least 1 µF effective local LDO input/output capacitance as the assembly acceptance. Reserve 10 µF nominal at the 3.3 V host regulator output and keep the bulk and startup profile in the inrush test. A contact-side rail monitor qualifies host attachment from J102.4. Its calculated falling threshold is 4.058–4.282 V, and the estimated rising upper corner is 4.408 V. Continuity and voltage at the actual plug contacts remain independent bench checks.

[TPS2553-Q1 datasheet](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf) · [TPS7A20 datasheet](https://www.ti.com/lit/ds/symlink/tps7a20.pdf) · [Frozen power budget](../../dock-safety/power-budget.json)

## Placement and bring-up

The mechanical read-only probe found a candidate B.Cu 20 × 20 × 1.5 mm volume centered at dock X−21/Y43. Its nominal floor clearance is 0.9 mm. Keep RP2040, ABM8-272-T3 crystal, 15 pF loads and 1 kΩ damping resistor on the same face and immediately adjacent to XIN/XOUT. The exact 6.3 × 3.6 mm mux courtyard passes at F.Cu X2/Y17 with 1.35 mm to the nearest rigid component. The central X0/Y17 site fails the 0.30 mm U114 courtyard margin. The X2 site still crosses the limiter return via. Both host and mux need routing and checks against the final populated native model, including ground reference continuity and the existing VBUS/cutoff routing. See the [package models and provenance](PACKAGE-MODELS.md).

Expose RP2040 SWDIO, SWCLK, RUN, GND and local VTREF as service pads for a target-powered probe. Fit the 10 kΩ external flash CS pull-up and expose BOOTSEL on the flash CS through 1 kΩ; the primary assembly programming plan is SWD while the local branch is qualified. A local BOOTSEL pad is not a second exposed USB programming connector. Keep the existing STM32 SWD and plug physical Power/Mode paths.

## Native KiCad source

Open [the transport schematic](dock-wired-transport.kicad_sch) with its
[project](dock-wired-transport.kicad_pro) to trace the connections across
Main, the display lid and the two UV boards. The transport and Main views
share six sheet files. [Native checks](native-checks.json) record zero KiCad
10.0.8 ERC findings in both views and verify that every Main terminal agrees
with the transport netlist. The combined `native.xml` retains all 303
components and 1,077 terminals for firmware, harness and UV checks. The
[wired firmware targets](../../../../../dock-firmware/wired-main/README.md)
add I²C mode selection and fresh temperature on the display. Winbond stencil
review, PCB routing, installed access and powered USB/UV tests remain open.

Open [the working EVT Main project](dock-wired-system.kicad_pro) for the
[six-sheet schematic](dock-wired-system.kicad_sch) and
[active PCB](dock-wired-system.kicad_pcb). Finish routing and fit on this
board. It incorporates the fixed-position
oscillator and crossing routes, contact-voltage valid, limiter-fault
readback, ground stitching and the latest 3.3 V supply branches. The host
I²C clock, the qualified USB enable branch from U153.3 to U157 and the
always-on reset control from U157.13 to U163.6 are routed.
R163.1 joins the USB enable net. Host I²C data joins U201.6, U162.2 and
pull-up R165.1. TP156 joins the USB host 3.3 V rail for probing. C155.1
joins the Main 3.3 V rail. The adjacent MCU_STOPn and USB_HOST_3V3 traces
retain their widths and layers through local detours. U155.2 connects to
ground and C153.2 has a dedicated return stitch. The LID_FB detour retains
both C172.2 thermal spokes. R156.1 reaches C159.1 on 3V3 through 1.346 mm
of 0.20 mm copper. The adjacent MCU_ARM detour retains its 0.20 mm width.
C161.2 connects to an existing ground via on B.Cu, closing the last ground
open. C161.1 joins 3V3 through the rerouted R165.2 branch.
The RP2040 RUN pad U160.26 joins U155.6. The adjacent monitor clock now uses
a 0.324 mm bridge on F.Cu to its existing plane transition. The translator
RUN leg remains open. The [native routing audit](active-routing.json)
records 13 opens and zero other
PCB design-rule findings. The new 1.1 V branch connects C177.1 to U160.23. The monitor
I²C clock detours on B.Cu. R155.1 and the U155 reset supervisor supply
join 3.3 V. R165.2 reaches the 3.3 V pull-up supply with U162's ground
preserved by a new return trace to the existing stitch. R157.2 joins the
local run net at U163.1. The PC recovery test pad TP151, U157.4 and pull-up
R156.2 now share `PC_LOCKn`. The adjacent Type-C sense trace detours around
this connection. Check installed access and cold-start recovery on the bench.
U160.19 now connects to the existing B.Cu ground fill through a 1.15 mm trace.
The inner ground plane remains continuous with the same fill within 1 mm
of the oscillator traces. U160.50 still needs a local 100 nF core bypass.
C178.1 is 6.14 mm away in a straight line, and the clearance-clean route
would add 14.28 mm of copper plus layer transitions. Keep the oscillator
positions and review the core bypass placement before closing this branch.
Finish the remaining core rail, run, host enable, I²C and other unconnected
nets before generating supplier artwork.
[RP2040 hardware design guide](https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf)

The [editable Hall receiver integration](../../dock-safety/wired-hall-head/main-integration/README.md)
replays on the Main and transport schematics. It adds the two receiver
channels and their independent thermostat inputs, plus the contact branch
limiter. Native ERC passes in both views. The overlay grounds both emitter
enable inputs during integration. Incorporate it into the Main PCB layout
and verify the actual cutoff paths and measurements before powering the UV
modules.

The native audit verifies 799 unique Main pad-to-net assignments and zero
schematic parity findings. The mounting holes are board-only mechanical
features. The 14 bare-copper test points remain connected and are excluded
from the parts BOM. Use the Main project for PCB updates and the transport
project for cross-board tracing.

The [Main parts selection](main-order-selection.json) covers 200 fitted parts
across 70 manufacturer part lines. See the
[passive part evidence](passive-parts-selection.json) and the
[matched UV base and lid supplier quotes](uv-assembly/README.md). The quote
packages bind Main R107 at 40.2 kΩ, R401/R501 at 4.22 Ω and the wired
firmware profile as one configuration.

The [native package fit study](../../../../cad/evt1-assembly/dock-harness-trial/wired-main-space-review/README.md#native-package-fit)
checks the 62 selected package models against the saved dock. The lowest
nominal shell clearance is 0.765 mm. The moved U158 clears the shell and
other package models in its own check. The [docked recovery study](../../../../cad/evt1-assembly/dock-harness-trial/wired-main-space-review/recovery-access/README.md)
details the default-source cable and optional hardware-lock access.

Replay from this directory with `python3 contract.py`, `python3 build_source.py --stock-footprints <KiCad 10 footprint library directory>` and `python3 check_native.py --kicad-cli <KiCad 10.0.8 executable>`.

## Product lid cutoff

The [Hall head project](../../dock-safety/wired-hall-head/wired-hall-head.kicad_pro)
uses the same chamfered 8.8 × 16 mm PCB at both stations. The substrate and
component-height envelopes clear the closed shells, liners and reference
mounts. The head is routed and the [two-board quote](../../dock-safety/wired-hall-head/assembly-quote/README.md)
is ready. Finish mount retention and tail strain relief before fitting it to
the dock.

Integrate two supervised Hall closure channels in the wired-specific
`dock-safety` sheet. Retain the thermostats on J621/J622 pins 7–8, the
430 Ω returns and U613 sensing. Feed the thermostats from separately
protected, low-drop branches of qualified `LOOP_5V` to preserve contact
current. Combine each thermal result with its corresponding Hall permit
in a separate fail-low hardware gate. Keep `LOOP_A` and `LOOP_B` as the
outputs to the existing UV cutoff logic. The fitted gate, its fault behavior
and the sensor/target mounts still need integration. Verify cutoff during
opening and check finished units for UV-C leakage around the seam, hinge
and ports.

The two Hall supplies and thermal branch limits must fit within the 1.5 A
source budget during faults. At the existing 40.2 kΩ R107 value, 15.51 mA
remains ahead of Hall integration. Evaluating 41.2 kΩ with the existing
4.22 Ω UV resistors raises that allowance to 31.85 mA. The same calculated
UV load is 563.63 mA, with an 11.33 mA margin to the low end of the new
limiter range. A bounded feed design uses three 182 Ω resistors in series
per Hall head and budgets up to 3.0 mA steady-state per head. The 41.2 kΩ
case leaves 2.93 mA of modeled source margin with both head feeds shorted.
Verify source and driver startup, connector faults and head placement before
changing the active circuit or R107 value.
[TI TPS2553 limit equations](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf)

The staged receiver used 2.3 mA as the low end of the intact signature.
TI specifies 2.3 mA typical and 2.8 mA maximum for the DRV5021, without a
guaranteed minimum. The receiver needs a bounded intact signature across
supply and temperature. The staged receiver stays held low until its
electrical and installed cutoff checks pass.
[TI DRV5021 electrical characteristics](https://www.ti.com/lit/ds/symlink/drv5021.pdf#page=4)
