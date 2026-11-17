# Wired lid Hall head

Both closure stations use the same editable 8.8 × 16 × 0.8 mm KiCad board and orientation. The two rear chamfers clear the existing liners in the saved closed pose. The board top remains at Z34.85 mm and the sensor package center stays at X±50.5, Y37.55 mm. The three tail lands are feed, signature and return. An independent loom restraint is still needed.

The nominal closed FreeCAD reference and 28 exact BRep comparisons are recorded in [geometry-check.json](geometry-check.json). The full-board top envelope is 1.50 mm, exceeding the 1.45 mm maximum of both TI SOT-23-6 components. The height and offset supplied for the Hall element are referenced to the package itself. [DRV5021 drawing](https://www.ti.com/lit/ds/symlink/drv5021.pdf) · [TPS3808 drawing](https://www.ti.com/lit/ds/symlink/tps3808.pdf) · [SN74LVC1G58 drawing](https://www.ti.com/lit/ds/symlink/sn74lvc1g58.pdf)

KiCad 10.0.8 reports zero routing violations, opens, schematic ERC or schematic-to-board parity issues across all 39 pads. The board uses 0.20 mm tracks with a 0.30 mm minimum copper-to-edge rule. Rebuild the checked copper and onboard placements with `build_board.py --routes routing.json` under KiCad's bundled Python.

C1 is the 220 nF 35 V X7R TDK C1005X7R1V224K050BC. It sits 2.86 mm center-to-center from U1. Both connections stay on the component side with 3.84 mm of feed and 1.95 mm of return copper. Verify at least 100 nF effective and the assembly power-up transient. [TDK characterization](https://product.tdk.com/system/files/dam/doc/product/capacitor/ceramic/mlcc/charasheet/c1005x7r1v224k050bc_210110.pdf)

Recheck with KiCad 10.0.8's bundled Python. Add `--save` to refresh the source-bound reports and `--require-clean` to enforce native routing completion.

```sh
python3 verify_native.py --kicad-cli /path/to/kicad-cli
```

The recorded A2 part is preliminary. A3 uses the same package and led prior modeled opening comparisons. Both stations still require measured magnetic release during opening, withdrawal/closing fault behavior, finished-unit UV-C leakage, thermal cutoff, cleaning efficacy and completed Main integration. Emitter authorization remains inhibited.

## Main receiver candidate

The DRV5021 specifies 2.3 mA typical and 2.8 mA maximum supply current. The
head's fitted 53.6 kΩ and 10 kΩ supervisor divider gives an independent
39.11 µA minimum feed signature once the head reaches 2.50 V. A Main-only
receiver can observe it and retain all 13 quoted head components.
[DRV5021 electrical characteristics](https://www.ti.com/lit/ds/symlink/drv5021.pdf#page=4) ·
[TPS3808 electrical characteristics](https://www.ti.com/lit/ds/symlink/tps3808.pdf#page=6)

- For each channel, route three independent series limiters to a local
  tap, then a dedicated 10 Ω Kelvin shunt, then the connector feed.
  The TPS3710 absolute feed witness takes its 57.6 kΩ / 9.76 kΩ divider from
  the upstream side of the shunt. The divider current stays off the measured
  conductor. Use Vishay TNPW060357K6BEEA and TNPW06039K76BEEA. The worst
  rising tap threshold is 2.811 V and the lowest falling threshold is
  2.649 V. With the intact limiter chain, worst feed/return harness drops
  put the remote head at or above 2.529 V while the witness remains
  permissive. With the independent return current guard, that floor
  rises to 2.553 V. One bypassed limiter reduces the voltage-only floor
  to 2.469 V, making the return guard and local cutoff necessary.
  The modeled feed-to-SIG bridge rejection margin is
  286 mV. [TPS3710 datasheet](https://www.ti.com/lit/ds/symlink/tps3710.pdf) ·
  [10 Ω shunt](https://www.yageogroup.com/component-documentation/download/specsheet/RC0603FR-0710RL)
- Use INA190A5IDCKR amplifiers on the 10 Ω feed shunt and a 1.5 Ω Kelvin
  shunt in the dedicated return. The return shunt is the sole route to
  system ground. Leave connector mounting tabs on system ground. Use a
  TLV9022DGKR and separate 39.2 kΩ / 1 kΩ dividers referenced to LOOP_5V.
  Calculated intact/open margins are 27/31 mV for feed and 20/75 mV for
  return, assuming at most 10 µA installed leakage for an open conductor.
  A LOOP-powered TLV6700 and 90.9 kΩ / 10 kΩ divider reject excessive
  return current and retain 442 mV of modeled upper margin. The previous
  2.2 Ω return shunt can saturate during the maximum modeled normal load.
  [INA190 datasheet](https://www.ti.com/lit/ds/symlink/ina190.pdf) ·
  [TLV9022 datasheet](https://www.ti.com/lit/ds/symlink/tlv9022.pdf) ·
  [TLV6700 datasheet](https://www.ti.com/lit/ds/symlink/tlv6700.pdf) ·
  [1.5 Ω shunt](https://www.yageogroup.com/component-documentation/download/specsheet/RC0603FR-071R5L)
- Keep the staged 10 kΩ SIG pull-up and TPS3701 window. The modeled intact
  closed voltage is 1.174–1.621 V with Q1 on. SIG opens above 2.43 V with
  net leakage limited to ±20 µA. Hard shorts below the low window or above
  the high window independently reject. Route all receiver qualifiers to
  the existing delayed hardware permit, one channel per side. Keep both
  430 Ω thermostat loops and existing hardware latches independent.
  [TPS3701 datasheet](https://www.ti.com/lit/ds/symlink/tps3701.pdf)

The lower-drop option uses three Panasonic ERA3AEB1240V resistors per feed
and changes Main R107 to Vishay TNPW060341K7BEEN at 41.7 kΩ, keeping R401/R501
at 4.22 Ω. Use `python3 check_receiver_feed.py` from this folder to recalculate
the margins from the live Main source allocation. The 1.5 A model leaves
0.98 mA with two shorted heads and 0.62 mA if one feed shunt is also bypassed.
One failed limiter plus its head short and a healthy second head leaves
4.06 mA. If both heads also short with that failed limiter, the model
exceeds 1.5 A by 5.68 mA. The highest calculated surviving limiter
dissipation is 52.4 mW. The model reserves 2 mA for both receiver channels
and has 3.75 mA of minimum UV input margin with the existing emitter setup.
[Panasonic 124 Ω](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB1240V) ·
[Vishay part notice](https://www.tti.com/content/dam/ttiinc/products/PCN/Vishay/Vishay-PCN-DBR-00012-2024-REV-0.pdf) ·
[Vishay stability limits](https://www.vishay.com/docs/28758/tnpw_e3.pdf) ·
[TI TPS2553 limit equations](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf)

The local cutoff option fits Panasonic ERA3AEB5492V and ERA3AEB1022V on
the head's existing R3 and R4 lands. The modeled aged minimum falling
threshold rises from 2.487 V with the quoted population to 2.513 V.
The worst release threshold is 2.738 V. At the assumed 4.10 mA load and
4.40 V supply, the head sees at least 2.771 V and the receiver witness has
about 30 mV of startup margin. The model budgets initial tolerance,
temperature change and published 1,000 h endurance drift. Establish
the actual startup, reset and rail current envelope with both heads
and their fitted capacitors. The logic gate's extra supply current is
specified with one input offset from the rail at VCC of at least 3 V.
Installed leakage over temperature, both thermal short peaks and the
complete pin-swap fault matrix remain open. Keep emitter authorization
inhibited. The editable PCB and quoted head population retain their
existing source bindings.
[Panasonic 54.9 kΩ](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB5492V) ·
[Panasonic 10.2 kΩ](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB1022V) ·
[Panasonic resistor endurance](https://industrial.panasonic.com/cdbs/www-data/pdf/RDM0000/AOA0000C307.pdf) ·
[SN74LVC1G58 supply-current conditions](https://www.ti.com/lit/ds/symlink/sn74lvc1g58.pdf#page=5) ·
[Yageo RT endurance conditions](https://yageogroup.com/content/datasheet/asset/file/PYU-RT_1-TO-0-01_ROHS_L) ·
[DMG1012T leakage conditions](https://www.diodes.com/datasheet/download/DMG1012T.pdf#page=2)

### Signature reversal and local gate

For a joint head and receiver revision, test a 4.99 kΩ Panasonic
ERA3AEB4991V bleeder across the head feed and return. Set the Main lower
return-current threshold with 10.7 kΩ / 1.00 kΩ (each ±0.451% including
temperature and endurance), leaving the existing 1.5 Ω shunt and upper
guard. The lower threshold is 0.367–0.458 V referred to the amplifier
output. With SIG and RET swapped, Main either rejects SIG above 2.133 V
or measures at most 0.329 V on the return amplifier. The latter bound is
500 × 1.005 × [1.545 Ω × (2.133 V / (5.62 kΩ × 0.98) + 10 µA) + 40 µV],
with the local switch treated as a short. It requires the only intentional
swapped return path to pass through the head's 5.62 kΩ resistor and at
most 10 µA bypass leakage. An intact closed head provides at least
0.518 V using the bleeder, supervisor divider and minimum SIG current.
[Panasonic 4.99 kΩ](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB4991V) ·
[INA190 datasheet](https://www.ti.com/lit/ds/symlink/ina190.pdf)

Evaluate TLV6700DDCR in place of U3 and TMUX2819DSGR in place of Q1.
Keep the Hall pull-up and feed a 100 kΩ / 47 kΩ divider into INB−. Tie
INA+ to the head feed. Connect both comparator outputs and the existing
supervisor RESET to the switch EN, with an 82 kΩ pull-up and 1 MΩ
pull-down. Select S_A to D, with S_A through the existing 5.62 kΩ resistor
and D at local return. Retain the revised supervisor divider. With these
assumptions the static feed model uses 3.045 mA plus 0.2394 mA per volt at
the head, giving at most 3.95 mA at the source high corner and at least
2.93 V at the head at the low corner. This fits the existing 4.10 mA
normal head allocation. The switch's published maximum supply draw uses
rail-level controls. Confirm the intermediate EN draw and power-up/off
behavior with the actual drive circuit, installed leakage, and all pin
faults. The 2 × 2 mm switch and three added resistors require an actual
courtyard and routing check inside the existing head outline. Both
thermostat loops, 4.22 Ω emitter resistors and the proposed hard-short
power allocation carry through this candidate.
[TLV6700 comparator](https://www.ti.com/lit/ds/symlink/tlv6700.pdf) ·
[TMUX2819 switch](https://www.ti.com/lit/ds/symlink/tmux2819.pdf)

The simplest way to cover the switch's partly powered state is to feed
TMUX2819 directly from the local rail that the existing receiver voltage and
return-current witnesses supervise. If installed drops and alternate feeds
are within the receiver model, a static permit then requires at least
2.553 V at the switch. The datasheet specifies 1.8–5.5 V operation and
isolation at 0 V. Keep a continuous copper connection from the Hall feed
to the switch supply and avoid an independently drooping switch rail.
This leaves the supply-current bound at intermediate logic levels and the
actual power-ramp, cutoff and latch timing to verify.
[TMUX2819 switch supply and leakage](https://www.ti.com/lit/ds/symlink/tmux2819.pdf)

For this direct-rail option, the 100 kΩ / 47 kΩ Hall divider sees at least
0.466 V with the Hall output released and at most 0.130 V with it asserted,
at a 2.5 V head supply. These limits include the fitted pull-up tolerance,
±0.451% for both new divider resistors and Hall/comparator input leakage.
The 82 kΩ and 1 MΩ EN network gives at least 2.167 V at a 2.553 V head
supply with 2.4 µA aggregate load. U2 asserts up to 0.4 V and U3 up to
0.25 V under their specified low-output conditions. Verify the switch at
these driven levels over the actual 2.553–5.25 V head rail range. The
datasheet's 140 µA maximum covers rail-level controls and its intermediate
control-current graph is typical at 25 °C. The coupled high-line startup
budget allows up to 369 µA switch current. This assumes the Hall sensor
uses at most 2.8 mA, the other active head circuits at most 46 µA, and the
retained passive feed. Use 350 µA as the maximum when obtaining a bound
for the applied control levels at temperature. Keep the total powered-off
and open-path signature leakage within the receiver's ±20 µA allocation.
With the existing receiver resistor tolerances, the static open signal
requires at least 70.9 µA total sink to reach the conservative 2.133 V
high reject threshold. Reserving the full existing 20.05 µA leakage
allowance leaves 50.9 µA of additional modeled static separation at that
threshold. The swapped-return proof still requires at most 10 µA bypass
around R5. Request separate switch leakage limits for powered-disabled and
unpowered states, including either analog terminal at either polarity
relative to the other. The calculation does not bound ramp transients.

The independent upper return-current guard bounds a static permitting
channel to 5.708 mA even if the head's internal supply draw increases. In
the modeled combination of one limiter bypassed, that channel hard-short,
and the other channel at 5.708 mA, the 1.5 A budget still has 2.45 mA before
dynamic effects. That result neither qualifies the startup budget nor
bounds simultaneous compound faults or current overshoot. Measure cutoff,
restart and source droop with both heads and the installed loom.

An alternative for joint review uses a positive signature sourced from
the switch supply through 15.0 kΩ. Main reads SIG against a 30.1 kΩ /
10.0 kΩ absolute lower threshold divider and uses a ratiometric upper
guard referenced to delivered feed after the Kelvin shunt. Example upper
divider pairs are 287 kΩ / 362 kΩ for SIG and 366 kΩ / 332 kΩ for feed. With
±0.451% dividers and ±6 mV comparison error the upper guard is
0.841–0.864 times feed at 2.55 V. The absolute disconnect/enable thresholds
are at least 1.580 V and at most 1.668 V, respectively. At 1.8 V switch
supply and ±10 µA external injection, a passively shorted switch path
can put at most 1.399 V on SIG. At an intact supply of at least 2.553 V it
provides at least 1.715 V. If the switch can source current through its
output independently in the unspecified supply region, that current
consumes the 26.9 µA total positive-injection allowance for the passive
short case. This alternative therefore still requires characterization
of ramp transients and any internal sourcing path.

For the positive code, a 4.22 kΩ head bleed and the existing aged divider
give 0.443 V minimum at Main's return amplifier. The swapped SIG and RET
bound is 0.301 V with the 15.0 kΩ source leg and up to 10 µA bypass
leakage. The Main threshold from 11.8 kΩ / 1.0 kΩ is 0.335–0.420 V. Only
the head bleed and supervisor divider count toward return current because
the SIG code current leaves the head. Confirm the real installed return
and re-run the source budget and threshold corners before changing either
editable board. Emitter authorization remains inhibited.
[TPS3701 falling and rising thresholds](https://www.ti.com/lit/ds/symlink/tps3701.pdf#page=5) ·
[TLV9022 differential comparator](https://www.ti.com/lit/ds/symlink/tlv9022.pdf)

### Main integration pin contract

The [editable Main integration](main-integration/README.md) maps the receiver,
independent thermostat paths and contact limiter onto both native Main roots.
Both emitter power gates are held low in that design revision.

A fresh KiCad 10 export of the [Main system schematic](../../case-telemetry-study/wired-main/dock-wired-system.kicad_sch)
confirmed these interception points on its [dock-safety sheet](../../case-telemetry-study/wired-main/sheets/dock-safety.kicad_sch).
The transport schematic shows the independent thermostats beyond J621/J622.

| Function | A, base | B, lid |
| --- | --- | --- |
| Existing thermostat send | `BASE_THERM_SEND` to J621.7 | `LID_THERM_SEND` to J622.7 |
| Existing thermostat return | J621.8 to R614 (430 Ω) and U613.1 | J622.8 to R615 (430 Ω) and U613.3 |
| Split at U613 output | U613.6 becomes `THERM_A_OK` | U613.4 becomes `THERM_B_OK` |
| Proposed thermal branch | U633 supervisor, U634 INA300, U635 TPS22918 and 2.00 Ω R645 to J621.7 | U653 supervisor, U654 INA300, U655 TPS22918 and 2.00 Ω R665 to J622.7 |
| Proposed Hall qualifier, held low | U632.3 takes `HALL_A_WINDOW`, .5 to ground, .1 `HALL_A_READY` through U637 | U652.3 takes `HALL_B_WINDOW`, .5 to ground, .1 `HALL_B_READY` through U657 |
| Proposed channel AND | U638.1 thermal sense, .3 thermal power good, .6 Hall good, .4 drives `LOOP_A` | U658.1 thermal sense, .3 thermal power good, .6 Hall good, .4 drives `LOOP_B` |
| Existing hardware cutoff | `LOOP_A` to U615.4, U615.6 `UV_GATE_A` to U610.8 | `LOOP_B` to U615.10, U615.8 `UV_GATE_B` to U611.8 |
| Existing common veto and reporting | `LOOP_A` also to U612.1, U201.2 | `LOOP_B` also to U612.2, U201.3 |

Replace S601/J601 and S602/J602 with separate thermal branches from
U602.5/.6 `LOOP_5V`. Each branch supervisor and overcurrent detector can
pull its enable low. The calculated thermostat contact current is
10.06–12.28 mA and the overcurrent trip is 13.41–15.61 mA. Confirm
the short-current peak and latched recovery. The INA300 LATCH input
stays high while `LOOP_5V` is present, so cycling the UV request cannot
clear this fault. The TPS22918 is a disconnect switch; the trip
threshold only describes when the detector requests cutoff.
U638 and U658 are separate
SN74LVC1G11DBVR devices with 47 kΩ output pulldowns. U612 and U616 still
qualify rearm. Preserve `CLEARn` to U609.1/.13 and U615.11 driver control
through J621.3/J622.3. Keep U632/U652 SENSE grounded during receiver
qualification. [INA300](https://www.ti.com/lit/ds/symlink/ina300.pdf#page=5) ·
[TPS22918](https://www.ti.com/lit/ds/symlink/tps22918.pdf#page=5) ·
[SN74LVC1G11](https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf) ·
[TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf)

J630/J650 are proposed receiver connector references. Pin 1 is feed,
pin 2 SIG and pin 3 the dedicated return. Keep mounting pads on system
ground. The TPS3710DDCR monitors the upstream 10 Ω shunt tap at pin 3
and drives the channel veto at pin 1. On both INA190A5IDCKR devices, tie
pins 1/2 to system ground, pin 3 to `LOOP_5V` and pin 6 to the comparator.
Connect pins 4/5 to the tap/feed for the feed shunt and to connector
return/system ground for the 1.5 Ω return shunt. Each low-current
comparator gets its amplifier on the noninverting input. Tie the
TLV9022 comparator outputs, TPS3701 window outputs and TLV6700 high
return output to that channel's `HALL_*_WINDOW` before the qualifier.
For TLV6700DDCR the high-return divider is at pin 4, OUTB is pin 6 and
the unused low side may monitor `LOOP_5V` on pin 3 with pin 1 also
on the veto. Confirm physical connector keying and PCB fit.
[TPS3710](https://www.ti.com/lit/ds/symlink/tps3710.pdf#page=3) ·
[INA190](https://www.ti.com/lit/ds/symlink/ina190.pdf#page=3) ·
[TLV9022](https://www.ti.com/lit/ds/symlink/tlv9022.pdf) ·
[TLV6700](https://www.ti.com/lit/ds/symlink/tlv6700.pdf#page=3)

The active 40.2 kΩ R107 misses the 1.5 A source limit by 22.59 mA in the
candidate model with both Hall feeds shorted, near-trip thermal loads and
the provisional 2 mA receiver allocation. The proposed 41.7 kΩ recovers
23.57 mA with the same 4.22 Ω emitter drive, leaving 3.75 mA at the low end
of the UV limiter range. The baseline 0.98 mA source margin with both
heads shorted assumes that 2 mA receiver allocation. A preliminary
two-channel parts screen with 39.2 kΩ / 1 kΩ feed, 10.7 kΩ / 1 kΩ return
and staged 24.9 kΩ pull-ups budgets roughly 3.35 mA in the two-head-short
state with thermal branches still enabled. Using approximately twice the
impedance at the same low-current divider ratios reduces that screen to
2.77 mA, leaving roughly 0.21 mA in the static model. Recheck input bias,
tolerance, logic load and transient current before selecting these values.
[Active source allocation](../../case-telemetry-study/wired-main/circuit-contract.json) ·
[Receiver calculation](check_receiver_feed.py)

### Recover source margin on the plug branch

Evaluate a second TPS2553QDBVRQ1 in series after U104.B2. Move U104.B2 to
an intermediate node and tie the new switch IN.1 and EN.3 to it. Keep
OUT.6 on `CONTACT_5V` so C106, J102.4 and the existing contact-voltage
monitor all stay downstream. Tie GND.2 to system ground and program ILIM.5
with Panasonic ERA3AEB1243V, 124 kΩ. Allow separate active-low FAULT.4
readback and a local input bypass meeting TI's 100 nF effective floor.
U104 retains reverse-current protection and its existing default-current
and qualified-source settings. Keep the original UV feed, R107 at 40.2 kΩ
and 4.22 Ω emitter drive. The proposed Hall and thermal vetoes stay on their
independent paths. [TPS2553-Q1](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf#page=13) ·
[TPS22950](https://www.ti.com/lit/ds/symlink/tps22950.pdf#page=6) ·
[124 kΩ program resistor](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB1243V)

| Program resistor | Calculated constant-current limit | Proposed static source allocation | 1.5 A headroom with active 40.2 kΩ R107 |
| --- | --- | --- | --- |
| 124 kΩ | 187.51–248.53 mA | 250 mA | 356.06 mA |
| 191 kΩ | 120.89–165.59 mA | 170 mA | 436.06 mA |
| 110 kΩ split network | 211.78–278.15 mA | 280 mA | 326.06 mA |

All rows use the more conservative 3.35 mA receiver load without doubling
the divider resistances. They cover shorted external Hall feeds, near-trip
thermal loops and a short downstream of the proposed switch. The reduced
allocation applies while the new limiter functions. A bypass, an upstream
short, or a resistor fault outside its programming range requires applying
the original 630 mA allocation. TI supplies process and temperature limits
for the current-limit equations. The calculation uses a ±0.451% resistor
allowance including initial tolerance, TCR over 100 K and 1,000 h endurance
drift. Full-load
5.25 V shorts before thermal shutdown can momentarily dissipate about 1.30 W
at 124 kΩ or 0.87 W at 191 kΩ. Check thermal cycling, nearby plastic
temperature and source droop. [191 kΩ program resistor](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB1913V) ·
[Resistor environmental ratings](https://industrial.panasonic.com/cdbs/www-data/pdf/RDM0000/AOA0000C307.pdf)

The split network is a secondary option if the Main layout can fit four
program resistors. Use two parallel strings of two Panasonic ERA3AEB114V
110 kΩ resistors in series. One resistor open leaves 220 kΩ and a
104.72–144.98 mA limit. One resistor short leaves 73.33 kΩ and a
319.73–407.20 mA limit. Both states stay within TI's programming range.
Allowing 410 mA for the one-resistor-short case still leaves 196.06 mA
of source margin under the same stacked external short model. The open
case has only 4.22 mA over the 100.5 mA sustained plug allowance, so check
cold recovery if required in that state. A bridge directly across the
switch or its programming network and a short internal switch still
require the original plug allocation. [110 kΩ program resistor](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB114V)

The fitted plug BQ24074 sets 90–100 mA with EN1/EN2 grounded. The
processor, radio and motor draw from the downstream `SYS` and the pack,
which supplements peaks above the charger input limit. Espressif lists up
to 350 mA Wi-Fi and 340 mA BLE transmit peaks at 3.3 V. A depleted pack or
open protector can therefore limit wake or radio use even with the original
630 mA dock allocation. Both new switch settings add up to 13.5 mV of DC
drop at 100 mA. At 4.50 V board input, this leaves 78.2 mV for existing dock
path drop and ripple up to the estimated 4.408 V contact release threshold.
The charger can throttle input at 4.35–4.63 V, and its input
is after the plug PTC and Schottky, so validate charge rate at low line.
The cap leaves the USB data mux and wired PC recovery routing intact.
The fixed USB100 pin straps do not put the charger into USB suspend.
Verify aggregate dock input against the applicable default-current and
suspend requirements separately. [Plug system schematic](../../single-flange-routing/system-native.xml) ·
[BQ24074 §§7, 8.5, 9.3](https://www.ti.com/lit/ds/symlink/bq24074.pdf) ·
[ESP32-C3-MINI-1 §6.4](https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html) ·
[USB-IF suspend guidance](https://compliance.usb.org/index.asp?UpdateFile=Electrical)

For the first capture, prefer 124 kΩ. Allowing 100.5 mA for sustained
plug current leaves 87.0 mA under its minimum current limit versus
20.4 mA at 191 kΩ. Known contact-side C1/C44/C106 can require about
32.5 µC over a full 5.25 V rise with initial and temperature allowances.
The ratios of that charge to the current headroom are about 0.37 ms and
1.60 ms. These are charge screens. TI specifies rise time for a 1 µF
load and gives a typical hard-short response, so measure actual contact
inrush, peak source current and voltage at `HOST_5V`, `CONTACT_5V`, plug
charger IN and `3V3`. Include cold attach with contact bounce, cold wake
with radio and USB activity, normal/depleted/open packs, source downgrade,
suspend/resume, and PC-lock ROM programming. Capture coincident Hall-head
startup and service activity, and capture late hot shorts as well as power-up
into shorts. Verify the source retains its hardware veto and the UV driver
rail meets the existing startup floor before qualifying any emitter run.

If an installed service mode needs more contact current, first identify
which load is ahead of USB100. Any proposed bypass must default open and
carry a separate hardware inhibit that prevents UV with the bypass active
or invalid. Evaluate stuck-on and interlock transition cases before giving
the reduced allocation credit. Keep emitter authorization inhibited pending
the receiver fault checks and measured power transients.

The [supplier quote package](assembly-quote/wired-hall-head-evt1-assembly-quote.zip) requests two units with A2 fitted and an optional separate A3 price.
