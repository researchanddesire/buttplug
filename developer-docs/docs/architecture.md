# Architecture

Two main metal parts—turned body with indexed collar flats, and nose cap—join a plastic flange tray,
rear plastic half and continuous silicone overmold. Preserve the 15 mm neck. The polymer flange
provides the antenna region. See the [proposal](prototype-build-handoff.md).

## Mechanical paths

- Vibration: motor case → cap pocket → threaded/shouldered metal body.
  The motor has a metal stop; the offset potted NTC and PCB carry no seating load.
- Axial body retention: rear shoulder → 2 mm tray root pad → thin nut on the
  short M18×1 stub. No compression limiter is selected. Cover screws close plastic only.
- Torque: opposing flats on the rear collar engage the keyed tray socket.
  Nut locking, clamp preload/creep and pull-through remain separate open checks.
- Wet boundary: cap face O-ring and a silicone cuff bonded to a recessed rear
  metal land, continuous with the skin molded over both closed flange halves.
  Full mold, contact feedthroughs and button membranes are unfinished.

The motor, NTC and insulated body PCB form a prewired cap module; foam pads
extend into the cap counterbore. Flange tails stay disconnected while that
module turns into the body. The rear nut tightens through the open tray before
flange electronics/pack/loom. Proposed PCB tabs/posts clear the nut and driver.
The requested protected-pack envelope sits beneath the flange board; supplier
acceptance, soft supports and installed leads remain open.

Secure the lower body to the flange, close its two rigid halves, then overmold
them together. Current cap wiring must be completed while the flange is open;
cap-last after molding needs a revised connection process. Battery service is
unresolved because the pack cannot pass the Ø12 neck and the rear half lies
beneath the skin. Actual molding, loom, clamp and wet-bond results remain unproven.
Separate inert skin/split-tool CAD and print STLs now provide an external
fill/demold trial. Its solid dummy does not test the real closed cavity,
contact/button seals or component exposure; see [hardware](hardware.md).

## EVT1 electrical candidate

| Function | Status |
| --- | --- |
| Controller/radio | ESP32-C3-MINI-1 reference; BLE/WiFi bench code exists, radio behavior untested. |
| Power/motor | Existing separate rails, driver and PWM/ARM/dock gate remain references. |
| Charging/pack | Single-cell charger/power path, protected-pack requirement and two pack-NTC channels; battery open. |
| Cradle / data | Five routed PCBs pass native DRC; USB protection/current limit and wake/reset circuit are saved. Physical USB/power qualification pending. |
| Tip sensing | Two-wire NTC and pulsed ADS1115 readout; routed body board, EVT1 driver and nominal curve/fault checks. Thermal calibration and physical wiring pending. |
| Motion | Move the LSM303AGR onto the single flange PCB. The previous separate routed sensor board remains a reference; new factory package axes and magnetic survey are pending. |
| Compass | LSM303AGR driver, tilt-compensated math and NVS assembly calibration exist. Magnetic survey, calibration workflow, axes and haptic mode unfinished. |
| Controls | Two flange switches under closed pre-cured silicone cups and the continuous outer skin; force, travel and molding/sealing trials pending. |

The [EVT1 electrical revision](evt1-electrical.md) is the current circuit/code
candidate. R35F layouts are preserved seeds. Actual device-board envelopes fit
the separate `evt1-integration/` native. Decoupling/component selection, actual
pack, flexible loom and factory axes still need work. No heating or
wear-duration claim is introduced.

The accepted revision keeps the existing body PCB and combines the flange
electronics, compass sensor and four PCB-mounted contacts on **one flange PCB**.
The original39-part placement study is preserved in
`hardware/pcb/evt1/single-flange-study/`. The separate
`hardware/pcb/evt1/single-flange-routing/` successor passes native DRC0/0,
full ERC and163-pad parity with no ignored checks, including two component
translations needed for the actual J7 mate. Its native1mm board and selected
component models remain separate from the earlier factory sources. The existing body circuit and
numeric J6/J7 interface are preserved. The integrated ESP32-C3-MINI-1 antenna
stays at the board edge, clear of the battery; housing/RF qualification is open.

## Smart cradle and four-contact interface

The product ships with a custom smart cradle/adapter connected to the computer
by USB-C. Four conductive contacts are exposed at the silicone flange, with sealed,
isolated feedthroughs and magnetic retention. These are logical functions;
the selected physical row is GND/D−/D+/5V, with finish and seals unqualified.

The housing concept is a rounded Pocket Neopet-style clamshell that holds the
washed, dry device in an asymmetric, open nest. A working exterior status
screen and three buttons are required for this EVT and report local dock states. Use transparent USB data
pass-through to the device and a local dock controller off that data pair;
a second dock USB peripheral would require a redesigned USB topology.

The case must also exchange data directly with the plug for temperature,
charging status and removal-baseline history without requiring a computer.
General bidirectional computer ↔ case ↔ plug USB communication remains mandatory
for firmware updates/ROM recovery, configuration, diagnostics, logs/telemetry
and future device commands. The existing pass-through does not yet give the
local case controller this telemetry; select a compatible
additional link or reviewed USB topology. Do not parallel a second controller
onto the USB pair. Case changes from the thermal session must be incorporated
into the main dock integration.

Log tip temperature while docked and a fresh, timestamped removal baseline even
on early removal. Keep battery charge completion separate from thermal
readiness: Charging → Charged — cooling → Ready. Readiness must account for
charging/UV heat, measurement validity and sufficient warming contrast; thresholds
remain to qualify. Case ambient sensing, charge-status readout, local data
exchange and history/display behavior remain unimplemented. A fan is an optional
cooling study requiring heat rejection, UV containment and a revised source
budget. See the [thermal baseline and cooldown contract](thermal-presence-study.md#charging-case-baseline-and-cooldown).

| Contact function | Product path |
| --- | --- |
| 5V | Protected dock input and charger/power path |
| GND | Common power and USB reference |
| USB D+ | Flange MCU GPIO19 / USB_DP |
| USB D- | Flange MCU GPIO18 / USB_DM |

Use ESP32-C3 native USB Serial/JTAG for routine programming and serial data.
The cradle provides USB connectivity and protected power/contact management;
two routed cradle boards now implement that path. System current, inrush, USB
suspend and actual port behavior remain to qualify. Native USB
avoids a USB-UART bridge for this path. See
[Espressif USB guidance](https://docs.espressif.com/projects/esp-idf/en/v5.5.3/esp32c3/api-guides/usb-serial-jtag-console.html).

EVT1 J1 carries all four contact functions. Its data pair reaches native USB
through protection and22R resistors. Dock presence wakes RTC GPIO1 through a
diode OR; firmware discards the resulting button gesture. TPS3422 watches the
separate raw Power switch and resets EN after7.5s. Holding Mode during that
reset pulls BOOT low for ROM USB recovery through the same four contacts.
Internal J4 remains for pre-mold service. Button membranes, timing and actual
recovery/flash behavior need hardware tests. The hardware dock motor inhibit
is preserved.

Enclosed UV-C cleaning LEDs are required for this EVT. Their implementation needs emitter
coverage above/below the device, a hardwired lid-open power cut independent of
firmware, hardware thermal/current limits, fault/restart control and leakage/efficacy/material-aging validation.
USB/charging is the default mode; concurrent UV/flashing and available source
power are not qualified. UV does not replace washing or establish sterilization;
shadowed areas and soil limit performance. See [CDC UV guidance](https://www.cdc.gov/infection-control/hcp/disinfection-sterilization/miscellaneous-inactivating-ingredients.html)
and the detailed concept listed in [Hardware](hardware.md).

The new [dock/interface study](hardware.md) uses four Mill-Max1946 fixed targets
mounted with the switches and compass on the single flange PCB. Integral tray
posts support the target bases through the laminate; no docking-load credit is
taken for solder strength or board bending. Their faces stand0.3mm proud;
sealing, finish and received assembly tolerances remain unqualified. A common
pre-cured silicone web has four contact sleeves and two closed switch cups,
clamped between board and rear half before the continuous outer skin is molded.
It is a proposed molding barrier, with no physical leak/cure/tear result.
Spring pins stay in the dock, with insulating annular stops on the metal
target faces setting0.6mm nominal compression. Permanent magnets are dock-only,
acting on buried steel keepers. Lower at+3mm axial offset, then slide to mate;
reverse the slide before lifting. A removable contact-face molding mask pulls
out before the lateral split tool opens. The routed pin and USB-C boards now
drive CAD datums, case opening, mounts and the rear solder-wire window. The
single-board study grows the rigid flange rear extent3.2mm and moves the target
row/keepers; matching dock carrier and device-support integration is in progress.
The earlier individually nuttedØ4 posts and their ring-gland fixture remain
separate historical trials and are not the selected single-board interface.

## Compass mode

The molded tactile/visual flange arrow points **toward the tailbone/back**.
The design assumes flange fit naturally constrains installation to one or two
orientations with adequate alignment for compass mode. The arrow resolves the
possible front/back reversal. Use the flange frame and a fixed heading-axis
offset from that mark; no wearer-specific pose calibration is required.

A three-axis magnetometer and accelerometer provide the baseline tilt-compensated
compass; a gyroscope is not required for that baseline. Output is magnetic heading,
with availability limited when motion prevents a reliable gravity estimate.
See [NXP AN4248](https://www.nxp.com/docs/en/application-note/AN4248.pdf).

Both sensors need a fixed, known transform to the flange arrow. EVT1 removes
the rotating body-board MC3635 and places the LSM303AGR on the flange. The
accepted single-board revision replaces the earlier daughterboard/two-boss mount.
Supply/return routing, new rigid registration, distinct
package-axis transforms and factory calibration remain open. Final thread clocking and foam
support of the cap module are not the heading reference.

Keep assembly magnetic calibration separate from the flange installation reference.
Measure and correct fixed magnetic offsets and material distortion in the assembled
device; recheck after relevant material, assembly or service changes. See
[NXP AN4246](https://www.nxp.com/docs/en/application-note/AN4246.pdf).

Charging magnets, the motor, metal parts and power currents are placement and
measurement constraints. Survey the proposed sensor site before layout release; calibration cannot be assumed to recover a saturated or changing field.
See [NXP AN4247](https://www.nxp.com/docs/en/application-note/AN4247.pdf).
Firmware must expose invalid/stale/disturbed heading rather than a plausible
bearing when calibration, sensor range, tilt estimate or heading-axis projection
is unusable. Compass availability during motor operation remains to establish.
