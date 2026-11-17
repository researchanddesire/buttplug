# First-article motor driver and optional migration

## Exact-part bench lot

At approximately 17:29 EST on 2026-11-16, the canonical JLCPCB page for TI DRV8212DSGR showed seven physical units and four available to order. The earlier response showed seven and zero. LCSC independently listed seven for the same C2843766 with a one-piece minimum. These channels may draw from shared stock. TI and Arrow showed no immediate stock, and DigiKey Canada showed backorder. TI lists `.A` as identical and directs orders to the base SKU. No separate allocation to `.A` or current Canadian Mouser stock was verified. [JLCPCB](https://jlcpcb.com/partdetail/C2843766) · [LCSC](https://www.lcsc.com/product-detail/C2843766.html) · [TI exact part](https://www.ti.com/product/DRV8212/part-details/DRV8212DSGR) · [Arrow](https://www.arrow.com/en/products/drv8212dsgr/texas-instruments.html) · [DigiKey Canada](https://www.digikey.ca/en/products/detail/texas-instruments/DRV8212DSGR/14634148)

Use the previous build split as the starting lot. Populate two assemblies and keep one bare for dimensional, contact and passive fit work. That needs two working U5s plus the assembler's component-specific feed loss. Ask JLCPCB to confirm a single small placement lot with the exact U5 and the quantity it will reserve. If the stock is still only available through LCSC, ask for a consignment quantity before relying on it. If placement loss makes the seven-unit inventory unusable for factory assembly, a separately controlled alternative is to quote U5 excluded from factory placement and fit two exact WSON packages with a local reflow/rework process. Hold at least one spare from the same traceable lot in that case. Use the exposed-pad paste process and inspect the hidden joints. One populated board can perform the first dummy-load check. A second gives a repeat and a fallback for rework. No stock was reserved. [Previous EVT lot split](../single-flange-routing/assembly-quote/README.md) · [JLCPCB placement loss](https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2) · [Sourcing and consignment](https://jlcpcb.com/help/article/pcba-parts-sourcing-instruction)

## Same-package DRV8837 option

The exact DRV8212DSGR keeps U5.7 at GND to select PWM. DRV8837DSGR C39159 and DRV8212PDSGR C5208051 share the DSG 8-pin WSON pattern, but U5.7 becomes nSLEEP. The reviewed catalog snapshot showed 113,396/112,102 stock/available units for DRV8837 and 8/0 for DRV8212P. The drawings and contracts below support a separate board variant if the exact route fails. [DRV8837 listing](https://jlcpcb.com/partdetail/C39159) · [DRV8212P listing](https://jlcpcb.com/partdetail/C5208051) · [TI DRV8837](https://www.ti.com/lit/ds/symlink/drv8837.pdf) · [TI DRV8212P](https://www.ti.com/lit/ds/symlink/drv8212p.pdf)

| Interface | Alternate schematic contract |
| --- | --- |
| U5.1 VM | `MOTOR_3V7`, existing bypass and bulk capacitance maintained |
| U5.2 / U5.3 | `MOTOR_P` / `MOTOR_N` to existing J3, neither terminal grounded |
| U5.4 / exposed pad | GND, with local thermal return and the manufacturer's paste pattern |
| U5.5 IN2 | GND, to keep forward/coast PWM |
| U5.6 IN1 | Existing U4 output `MOTOR_PWM && MOTOR_ARM && DOCK_PRESENT_N` |
| U5.7 nSLEEP | `MOTOR_ARM && DOCK_PRESENT_N`, held steady during an authorized drive command |
| U5.8 VCC | `3V3`, existing local 100 nF bypass |

Use a 3V3 two-input AND such as TI SN74LVC1G08DBVR C7666 with an adjacent 100 nF bypass. Preserve the existing boot pulldowns, driver exposed pad and dock hardware gate. Keep nSLEEP low when either input is low. Retain U4 independent of the wake gate. Its PWM output cannot feed nSLEEP. If both driver families must share one layout, use assembly-specific, mutually exclusive pin-7 links and test population continuity before power. For a single first article, give the selected MPN a dedicated schematic value and pin-7 net. [Existing motor schematic](../one-board/sheets/02-motor.kicad_sch) · [TI AND gate](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf)

- DRV8837 supports VM at 0–11 V and VCC at 1.8–7 V. Its inputs tolerate the recommended levels with supplies absent and the rails can sequence either way. With nSLEEP low, OUT1/2 are Hi-Z regardless of inputs. With nSLEEP high and IN2 low, IN1 low is coast and high is forward. Its wake maximum is 30 µs at the 25 °C, VM 5 V, VCC 3 V, 20 Ω timing test. DRV8212P has a 100 µs maximum wake time. Keep the longer delay if the firmware covers both devices, and include actual motor rail startup. [TI DRV8837 sections 6–7](https://www.ti.com/lit/ds/symlink/drv8837.pdf) · [TI DRV8212P sections 7–8](https://www.ti.com/lit/ds/symlink/drv8212p.pdf)
- DRV8837's recommended peak is 1.8 A, with OCP 1.9–3.5 A and 1 ms typical retry. The 0.28 Ω typical bridge corresponds to about 126 mV and 57 mW at the published 0.45 A running maximum. TI's 0.33 Ω room-temperature bound is under its specified supply and load. Verify hot loss and the installed startup/fault peak against the 1.8 A operating limit. NFP's one approximately 0.71 A sample stall is a screen. Keep the device's pack, current and temperature protections independent of bridge OCP. [TI DRV8837 specifications](https://www.ti.com/lit/ds/symlink/drv8837.pdf) · [NFP motor drawing and sample curve](https://nfpshop.com/wp-content/uploads/2022/04/Encapsulated-Vibration-Motor-NFP-E1015-3.7V.pdf)

## Firmware operation for nSLEEP variant

| State or event | Required outputs and transition |
| --- | --- |
| Reset, shutdown, dock, fault or stop | Drive PWM and ARM low. Cancel pending startup and invalidate the earlier run request. Verify the reset-time hardware pulldowns enforce the same behavior before firmware configures GPIOs. |
| New allowed command | Load zero PWM, assert ARM once and start a monotonic deadline based on at least 100 µs and the measured worst-case rail settling time plus margin. Real VM power-good is an alternative if a later board routes and qualifies it. |
| Startup pending | Keep PWM low. Cancel if dock, stop, fault or command validity changes. Only enable PWM after the settle deadline and a fresh check of those inputs. |
| Running | Set duty while preserving ARM across normal updates. At zero requested duty, deassert ARM and return to the idle state. |
| Dock source dropout or contact bounce | A preceding dock event invalidates ARM permission. Verify the physical outputs with actual bounce, including open intervals longer than 100 µs. If hardware can re-enable before software revokes ARM, require an interlock that holds inhibit until a new allowed command. |

The existing `motor_apply()` path drops ARM before updating duty and calls it each control cycle. Replace that behavior for an nSLEEP variant and keep the motor disabled in the default bench profile. Exercise the sequencing and cancellation paths in host tests, then scope all physical states. [Current firmware](../../../../firmware/main/main.c) · [Motor commissioning procedure](../../../design/evt1-bench-ordering/motor-first-power.md)

## Bench acceptance

1. At current-limited power, inspect U5 exposed-pad soldering and continuity. Verify gate truth at U5.7/6, U5.5 low and both motor terminals inactive during reset, docked and stopped. Perform before attaching a live pack or motor.
2. With a differential measurement across a known dummy load, capture 3V3, dock input, ARM, U5 nSLEEP, PWM, VM and current at startup, run and stop. Repeat after sleep, fast stop/re-arm, brownout and repeated dock bounce. Confirm no actual load current after inhibit and before a new allowed command. Observe VM transients and settle time independently of driver wake.
3. Use the selected motor in the restrained off-body fixture and supplier-approved load and pulse limits. Sweep pack voltage and temperature through the intended EVT range and compare startup, running, locked/inhibited/fault and retry behavior. Measure differential motor voltage, peak current and driver/pack/metal temperatures. Proceed only with headroom to the bridge peak, measured pack limit and allowed contact-region temperatures. Confirm a separate successful repower and stop on the second assembly.
