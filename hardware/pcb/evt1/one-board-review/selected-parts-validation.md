# Compass EVT1 first-article parts selection

The current product and debug schematics use these first-article selections. The native symbols carry the exact MPN, catalog identity, Datasheet and ReviewNote. The choices use the existing footprints and terminal assignments. C1–C3 now specify a 16 V capacitor, and R21 now specifies 360 kΩ. C33 uses a stocked TDK 35 V part in the same package. JLC codes identify parts even when JLC assembly stock is zero.

## Generator and board values

| Reference | Current native Value | Candidate native Value | Exact candidate / catalog code | Native land centers and pad size, mm |
| --- | --- | --- | --- | --- |
| C1 | `4.7uF 10V X7R` | `4.7uF 16V X7R` | Murata GRM21BR71C475KE51L / C408144 | ±0.95, 0.70 × 1.30 |
| C2 | `4.7uF 10V` | `4.7uF 16V X7R` | Murata GRM21BR71C475KE51L / C408144 | ±0.95, 0.70 × 1.30 |
| C3 | `10uF 10V` | `4.7uF 16V X7R` | Murata GRM21BR71C475KE51L / C408144 | ±0.95, 0.70 × 1.30 |
| C51, C52, C53, C54 | `10uF 10V X5R 0603 HF` | Same | Samsung CL10A106KP8NNNC / C19702 | ±0.675, 0.65 × 0.80 |
| C33 | `1uF` | Same | TDK C1608X7R1V105K080AC / C2172920 | ±0.675, 0.65 × 0.80 |
| R75, R76 | `22R` | Same | Yageo RC0402FR-0722RL / C114765 | ±0.51, 0.54 × 0.64 |
| R11 | `312k 0.1%` | Same | Yageo RT0603BRD07312KL / C861315 | ±0.725, 0.55 × 0.90 |
| R43 | `715k 0.1%` | Same | Panasonic ERA-6AEB7153V / C2087398 | ±0.875, 0.65 × 1.30 |
| R21 | `362k 0.1%` | `360k 0.1%` | Panasonic ERA-6AEB364V / C473324 | ±0.875, 0.65 × 1.30 |

Before the patch, all 12 positions lack explicit MPN and LCSC fields in native XML. The active ordering candidate fills these from earlier project selections. C51–C54 and R43 already have ReviewNote text referring to their prior MPNs. The other targeted ReviewNote and Datasheet fields are empty. The scratch selections replace those notes through the existing `SOURCE_SUBSTITUTIONS` mechanism. Regenerating product then dev preserves capture of the new values and metadata from one source. Synchronize C1, C2 and R21 values on the routed copies of both PCBs and rerun native schematic parity after any routing changes. The package families remain unchanged. Maintain the locked contact trunks during native board sync.

## Capacitance and bring-up

The first article leaves C12 and C22 empty and uses the same 4.7 µF part at
C3 as at C1 and C2. Retain C11 and C21 along with the direct C51 and C53
regulator bypasses. The shared SYS bank is **44.7 µF nominal**, with about
29.3 µF typical at 3.0 V and 21.9 µF at 4.4 V on the vendor curves. Each
converter's local pair screens at about 7.0 µF at 4.4 V after the simple
tolerance and temperature factors and before aging. Check USB100 inrush and
SYS startup near zero as well as loaded bias and the first motor pulse. The
initial ±10% part tolerances alone allow 49.17 µF near zero, so the nominal
bank sum does not establish a worst-case startup margin. [Circuits and population](../one-board/schematic-source-bindings.json) · [Murata models](https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR71C475KE51%22%2C%22GRM21BR61A106KE19%22%5D) · [Samsung characteristics](https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL10A106KP8NNN) · [TI BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [TI TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf)

- C1 is BQ24074 IN, behind D1, and C2 is BQ24074 BAT. Murata lists 1.40 mm maximum for both legacy and candidate device families. An old DigiKey feed lists 1.35 mm maximum for the original exact MPN. Use the 1.40 mm manufacturer value for the candidate fit. The candidate preserves 4.7 µF ±10%, X7R and 0805, and raises rating from 10 V to 16 V. Confirm local biased capacitance and inrush across 5 V contact tolerances at C1, and output or battery simulator response across 3.0–4.2 V at C2. TI lists 1–10 µF at IN and 4.7–47 µF at BAT, and requires less than 10 µF input capacitance for its USB inrush example. Keep JP1 open during initial gate verification. [Murata device families](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/dynamic-model/component-list-d-mlcc-2506.ashx?cvid=20250805040419000000&la=en-sg) · [Murata candidate model](https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR71C475KE51%22%5D) · [TI BQ24074, §§7–9](https://www.ti.com/lit/ds/symlink/bq24074.pdf)
- C51/C53 bypass SYS inputs and C52/C54 bypass 3V3 and MOTOR_3V7 outputs. Samsung specifies the same 1.60 ±0.10 × 0.80 ±0.10 × 0.80 ±0.10 mm envelope as the original TDK, X5R, 10 µF ±10%, 10 V. Interpolating the official Samsung chart at 25 °C gives 4.89 µF at 3.0 V, 4.43 µF at 3.3 V, 3.97 µF at 3.68 V, 3.81 µF at 3.83 V, 3.46 µF at 4.2 V and 3.28 µF at 4.4 V. These are typical curve values based on 10 µF nominal. A simple 0.90 × 0.85 tolerance/temperature screen gives 3.39, 3.03 and 2.51 µF at 3.3, 3.68 and 4.4 V before aging, with no worst-case bias guarantee. The short pin-to-cap paths matter for high-frequency bypass. Verify the combined input/output capacitor banks over temperature and bias. With a nominal 1.5 µH inductor at +20%, TI's output rule calls for at least 18 µF effective when that L value applies. Measure 3V3 startup/USB transfer and both converters' first-load-step response at low and high SYS. [Samsung specifications](https://product.samsungsem.com/cn/mlcc/CL10A106KP8NNN.do) · [Samsung characteristic data](https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL10A106KP8NNN) · [TDK original characteristics](https://product.tdk.com/en/system/files/dam/doc/product/capacitor/ceramic/mlcc/charasheet/c1608x5r1a106k080ac.pdf) · [TI TPS63070, §§7.3, 9.2 and 11](https://www.ti.com/lit/ds/symlink/tps63070.pdf)
- C33 uses TDK C1608X7R1V105K080AC, 1 µF ±10%, 35 V X7R, 0.90 mm maximum, on MCU_EN with the existing R31 pull-up. DigiKey Canada listed 320,952 for this alternate and zero for the earlier 25 V exact part. JLCPCB listed four of the 35 V alternate. DigiKey lists the previously considered Murata GRM188R71E105KA12D as obsolete. TDK’s typical curve stays close to nominal from 3–4 V, about 0.99 µF near 3.3 V when normalized to 1 µF at zero bias. Verify biased capacitance and capture EN rise, hardware reset pulse and ROM recovery timing on the assembled board. [TDK 35 V characterization](https://product.tdk.com/system/files/dam/doc/product/capacitor/ceramic/mlcc/charasheet/c1608x7r1v105k080ac.pdf) · [DigiKey exact and replacement](https://www.digikey.ca/en/products/detail/tdk-corporation/C1608X7R1E105K080AB/2443997) · [JLCPCB](https://jlcpcb.com/partdetail/C2172920)

## Resistors and motor rail

- R11 keeps 312 kΩ ±0.1% and ±25 ppm/°C, with 0.55 mm maximum seated height. Exact nominal regulator setpoint and divider current remain 3.296 V and 8 µA. The part is 0.10 W rated, with divider dissipation approximately 20 µW. [DigiKey exact alternate](https://www.digikey.ca/en/products/detail/yageo/RT0603BRD07312KL/5927923) · [JLCPCB](https://jlcpcb.com/partdetail/C861315)
- R43 preserves 715 kΩ ±0.1%, ±25 ppm/°C and 0805. Panasonic ERA-6AEB7153V is 0.60 mm maximum seated. The nominal thermal guard threshold remains unchanged. Bench the installed hot and cold hardware guard trips with pack simulation before closing JP1. [Panasonic](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA6AEB7153V) · [DigiKey](https://www.digikey.com/en/products/detail/panasonic-electronic-components/ERA-6AEB7153V/2025921)
- R75/R76 use both positions of one exact Yageo MPN, 22 Ω ±1%, 0.40 mm maximum. The existing drawing calls these 22R and the prior ±0.1% TNPW MPN is outside Vishay's listed e3 0402 ±0.1%, ±25 ppm/°C range. The initial resistor mismatch is at most 0.44 Ω from individual tolerance. Qualify USB full-speed enumeration, transfer and recovery through the assembled dock and J4 service configurations with one host attached. [Yageo part data](https://yageogroup.com/component-documentation/download/specsheet/RC0402FR-0722RL) · [Vishay range](https://www.vishay.com/docs/28758/tnpw_e3.pdf) · [Espressif PCB layout](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html)
- R21 uses Panasonic ERA-6AEB364V, maximum 0.60 mm seated, 360 kΩ ±0.1%, ±25 ppm/°C. The 100 kΩ R22 stays. DigiKey listed cut tape. The +16 mV correction back toward the original setpoint would be smaller than normal converter and feedback tolerances. The single-value change keeps both pads and leaves divider current at 8 µA. Review actual output enable, first-pulse and loaded motor-terminal results before considering a second-value change. [Panasonic](https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA6AEB364V) · [DigiKey](https://www.digikey.com/en/products/detail/panasonic-industry/ERA-6AEB364V/1466008)

U3.1 PS/SYNC is pulled to SYS by R26, so the applicable DC accuracy is the PFM-enabled −1%/+3% specification for SYS ≥3.0 V. TI's PWM-only ±1% numbers are useful for comparison. With VOUT = VFB × (1 + R21/R22) plus signed R21 × IFB, the bounds below use independent ±0.1% resistor ratios and a conservative ±100 nA feedback allowance at the datasheet's 0.8 V leakage condition.

| R21 selection | Nominal | Forced PWM comparison | PFM-enabled, SYS ≥3.0 V |
| --- | ---: | ---: | ---: |
| 362 kΩ existing | 3.696 V | 3.617–3.775 V | 3.617–3.849 V |
| 360 kΩ candidate | 3.680 V | 3.602–3.759 V | 3.602–3.832 V |

With a further illustrative independent ±25 ppm/°C × 100 °C resistor drift, the 360 kΩ PFM screen is 3.587–3.847 V. The intervals are static feedback screens. Below SYS 3.0 V the published PFM accuracy does not apply. Check received motor behavior at low pack SYS, cold start and assembled hot conditions, including bridge/wire drop, overshoot and the first enabled pulse. NFP lists 3.7 V nominal, 450 mA maximum rated running current and a sample stall measurement around 0.71 A. NFP's publication does not give a qualified continuous-voltage band or allowed startup and stall time. Use 3.7 V as the vendor baseline and seek a sample-specific operating limit for release. The prototype bench checks must establish the actual motor-terminal result. [TI TPS63070, §§7.5 and 9.2.2.1](https://www.ti.com/lit/ds/symlink/tps63070.pdf) · [NFP public drawing and sample test](https://nfpshop.com/wp-content/uploads/2022/04/Encapsulated-Vibration-Motor-NFP-E1015-3.7V.pdf)

## Scratch verification

KiCad 10.0.8 native ERC reported zero product and dev findings after the matching EVT1 footprint library was included. The product circuit verifier preserved 355 retained endpoint connections, and the dev board/schematic contract passed its existing bench connectivity checks. The two routed board files in the scratch source were never written. `first-article-selection.patch` applies to the one-board generator only. `selections.json` contains exact field strings. SHA-256 and native field conservation are recorded in `verification.json`.
