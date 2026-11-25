# EVT1 cable harnesses

## One-board device

The compact one-board device (`hardware/pcb/evt1/one-board/`) has its own
generated set in `hardware/cables/evt1/one-board/`, written by
`build_harnesses.py` from the live netlist. The two-board looms below (interboard,
compass, flange contacts, two tape-on pack NTCs) do not apply to it.

| Harness | Editable source under `hardware/cables/evt1/one-board/` | Detailed child BOM |
| --- | --- | --- |
| 3-wire protected pack into J2 | `pack-one-board.yml`; pack's factory JST SH 3P plug into the SM03B header, nothing bought | [TSV](../hardware/pcb/evt1/one-board/build/cables/export/pack-one-board.bom.tsv) |
| Motor | `motor-one-board.yml`; J3 SH2 to the NFP-E1015 leads | [TSV](../hardware/pcb/evt1/one-board/build/cables/export/motor-one-board.bom.tsv) |
| Tip NTC | `tip-one-board.yml`; J5 SH2 to the TDK glass bead | [TSV](../hardware/pcb/evt1/one-board/build/cables/export/tip-one-board.bom.tsv) |
| Bench service | `service-one-board.yml`; J4 SH6 to the programming fixture, not a product part | [TSV](../hardware/pcb/evt1/one-board/build/cables/export/service-one-board.bom.tsv) |

Blanks are 120 mm (motor), 150 mm (tip, service) starting stock from the
modelled paths plus 20 mm; the pack leads are the pack's own. Child BOMs are
regenerated with `build_harnesses.py --render` and are not committed. Plug
the pack into J2 after the cap is threaded; check its pinout first. See the
[source README](../hardware/cables/evt1/one-board/README.md).

## Two-board EVT1 looms

Use `hardware/cables/evt1/` with the current EVT1 boards. The P1/R35F recipes
below are prior studies; the current product has a two-wire tip thermistor
and four-contact USB dock. No physical harness has been accepted.

| Harness | Editable source under `hardware/cables/evt1/` | Detailed child BOM |
| --- | --- | --- |
| Body J6 to flange J7 | `interboard-evt1.yml`; ten numeric1:1 wires | [TSV](/private/tmp/compass-evt1/cable-export/interboard-evt1.bom.tsv) |
| Body J81 to compass J82 | `compass-evt1.yml`; four independent wires | [TSV](/private/tmp/compass-evt1/cable-export/compass-evt1.bom.tsv) |
| Protected pack and two NTCs | `pack-evt1.yml`; ACH power disconnect and separate NTC returns | [TSV](/private/tmp/compass-evt1/cable-export/pack-evt1.bom.tsv) |
| Local motor | `motor-evt1.yml`; J3 to both bridge outputs | [TSV](/private/tmp/compass-evt1/cable-export/motor-evt1.bom.tsv) |
| Two-wire tip NTC | `tip-evt1.yml`; J5 to TDK NTC | [TSV](/private/tmp/compass-evt1/cable-export/tip-evt1.bom.tsv) |
| Four fixed targets | `contacts-evt1.yml`; GND/D−/D+/5V to flange J1 | [TSV](/private/tmp/compass-evt1/cable-export/contacts-evt1.bom.tsv) |
| Cradle USB to pins | `dock-evt1.yml`; J93 to J94, four numeric1:1 wires | [TSV](/private/tmp/compass-evt1/cable-export/dock-evt1.bom.tsv) |

`wire-stock.csv` lists starting blanks. The ten saved interboard forms pass
nominal bend/part/wire checks, with free paths62.865–63.788mm. Keep120mm blanks
for the first article. Other installed routes and all finished cut/strip
dimensions remain unfinished. Use received connector/crimp egress and fixtures
before fixing lengths. Wire STEP conversion is withdrawn; use the editable
native and checked preview. Interboard pin10 is TIP_EXC_EN. USB stays on the
flange; no USB pair passes through the neck.

Use the without-protrusions SH housings and specified contacts. Prewire the
rotating cap/body-board module with numbered free flange ends; insert the J7
housing only after threading. Connect pack power afterward. Keep both NTC
returns independent until J2's2S land; power return uses2P. Both are native
logical pin2. Do not pre-tin ordinary crimp strands or ordinary-crimp factory
thermistor leads. MOTOR_N is not ground.

The contact and cradle D−/D+ conductors stay paired with minimal end fanout;
no90ohm impedance or powered USB claim follows. Solder/clean/cool fixed posts
before fitting their inner rings. Complete strain relief and connected loading
trials before closing the rigid halves or molding a continuous skin.

The [source README](../hardware/cables/evt1/README.md) gives regeneration,
parts and assembly order. Generated diagrams/child BOMs live in the temporary
external folder above and are reproducible with WireViz0.4.1; do not commit
them or copy child rows into the human-owned `hardware/bom.csv`. Factory leads
and the pack socket are included with their assemblies, not extra loose buys.
Current logical and geometry status is in the source-folder review files.

# Earlier cable development notes

[R37 conditional pack adapter](pack-assembly-r37.md) extends the R36 sensor recipe with two power lap joints and a prewired mate candidate. Source: `hardware/cables/pack-adapter-r37/pack-adapter-r37.yml`. Five150 mm blanks plus two30 mm return legs total0.81 m; factory leads not double-counted. [Generated child BOM](/private/tmp/r37-wireviz/pack-adapter-r37.bom.tsv) is temporary candidate review output; regenerate from the source README. Product BOM unchanged, battery OPEN.


## R36 pack-sensor adapter development

The [R36 sequence](pack-sensor-r36.md) and
[editable fixture recipe](../hardware/cables/pack-sensor-r36/pack-sensor-r36.yml)
connect native R35F lands to both full factory-leaded NTCs. Four lap joints
and one sensor-return junction keep the external sensor and power returns
separate. Power ends remain parked; the protected-pack mate is unfinished.
`hardware/cables/pack-sensor-r36/logical-review.json` checks native nets and
child BOM counts. Five 120 mm and two 30 mm starting blanks are trimmed to a
fixture; factory leads are included with the sensors. Actual solder/insulation,
restraint and connected loading remain open.

| Local R36 generated artifact | Link |
| --- | --- |
| Wiring diagram | [SVG](/private/tmp/r36-wireviz/pack-sensor-r36.svg), [PNG](/private/tmp/r36-wireviz/pack-sensor-r36.png) |
| Detailed child BOM | [TSV](/private/tmp/r36-wireviz/pack-sensor-r36.bom.tsv) |

See the [source notes](../hardware/cables/pack-sensor-r36/README.md) to regenerate
temporary outputs. Do not commit renders or copy child rows to the human BOM.

## R31 interboard update

The current R31 button geometry revises the R29 interboard extension, rise
and flange loops; use `hardware/cad/buttons-r31/wire-review-d/wire-plan.json`
for those paths. The ten-net topology and 120 mm starting-blank recipe are
unchanged. See the [R31 button sequence](buttons-r31.md) for the keeper/cover
order and calibration.

## R30 anchor and assembly supplement

The [R30 target order](harness-support-r30.md) and [process proposal](../hardware/cables/harness-support-r30/README.md)
add two proposed overmolds around the unchanged R29 wires. Hubs close with
loose flange ends parked straight; the loop is formed and terminated later.
The existing hub/keeper joints capture the pads without extra screws. Cure,
wire-jacket adhesion, fixtures and actual mating/pull tests remain open. R29
electrical recipe and generated child BOM links below remain unchanged.

## Current R29 interboard candidate

The [editable ten-wire recipe](../hardware/cables/interboard-r29/interboard-r29.yml)
connects J6 to J7 numerically 1:1. Its pin labels match the current R28S
full-system native XML. See the [source and fixture notes](../hardware/cables/interboard-r29/README.md)
and `hardware/cables/interboard-r29/logical-review.json`.

Use two candidate **SHR-10V-S housings without protrusions**, twenty
SSH-003T-P0.2-H contacts and ten 120 mm starting blanks of the proposed
28 AWG wire. The 13 mm B-suffix housing does not fit the modeled 11 mm
allowance. Blanks are trimmed on a fixture; they are not finished cut lengths
or stored service slack. Native wire routes and supported loading remain a
separate mechanical review. No actual harness has been built or tested.

| R29 local generated review artifact | Link |
| --- | --- |
| Wiring diagram | [SVG](/private/tmp/r29-wireviz/interboard-r29.svg), [PNG](/private/tmp/r29-wireviz/interboard-r29.png) |
| Detailed child BOM | [TSV](/private/tmp/r29-wireviz/interboard-r29.bom.tsv) |

Generated outputs are temporary local files. Regenerate from the source
README when needed. The human-owned product BOM remains unchanged.

## Current R26 tip candidate

The [stationary tip target](tip-support-r26.md) uses four individual wire
allowances and a detachable sensor support. Its logical pin map remains the
same. The [editable WireViz source](../hardware/cables/tip-r26/tip-sensor-r26.yml)
and [source notes](../hardware/cables/tip-r26/README.md) specify four **80 mm
starting blanks**, trimmed to a fixture. They supersede R0's 160 mm blank
planning for this R26 tip candidate only. Installed insulated paths are about
50.4–51.2 mm plus a 1.1 mm bare-tail study; these are not finished cut/strip
dimensions or service slack.

Use the candidate **SHR-04V-S without flange**, not the wider B-suffix variant.
Actual crimp, mated wire exit, supplied wire OD and bend basis still need
checking. The new recipe uses brown/amber wire with pin/function identification.
Load with free tip ends: feed them through the motor ring before seating it,
then fit/wire the tip module. Do not infer connected-harness travel from large
rigid CAD offsets. Apply final strain relief after wire dressing.

| R26 local generated review artifact | Link |
| --- | --- |
| Wiring diagram | [SVG](/private/tmp/r26-wireviz/tip-sensor-r26.svg), [PNG](/private/tmp/r26-wireviz/tip-sensor-r26.png) |
| Detailed child BOM | [TSV](/private/tmp/r26-wireviz/tip-sensor-r26.bom.tsv) |

These links are local generated outputs, not published repository assets.
Regenerate with WireViz 0.4.1 using the source README after temporary outputs
expire. Do not commit cable renders or copy child rows into `hardware/bom.csv`.
The child BOM is candidate starting material, not an approved purchase list.
The motor and pack/NTC harnesses below remain logical candidates requiring
their own actual routing/termination work.

## Preserved R0 / R2 harness studies

R2 is repacking the main board around the selected 15 mm neck. Preserve the
logical pin maps below; revise installed wire lengths and paths after the new
placements and actual mated bodies are checked. J1 remains the internal two-pin
dock interface; the exposed contact/feedthrough assembly is still being selected.

R0 has editable WireViz sources for the wired tip sensor, two-wire motor and protected-pack/dual-thermistor adapter. Their logical pin maps match the current R0 schematic. They are **candidate bench harnesses, not fabrication released**: Main PH4/SH2/SH4 candidates and tip direct-wire pads exist; mating contacts, wire gauge, insulation, strip lengths and installed routes remain open. No harness has been built or physically checked.

| Harness | Editable source | Review diagram | Detailed child BOM |
| --- | --- | --- | --- |
| Wired tip, W-TIP | [WireViz](../hardware/cables/prototype-r0/tip-sensor-r0.yml) | [SVG](../hardware/cables/prototype-r0/tip-sensor-r0.svg), [PNG](../hardware/cables/prototype-r0/tip-sensor-r0.png) | [TSV](../hardware/cables/prototype-r0/tip-sensor-r0.bom.tsv) |
| Pack and dual NTC, W-PACK/TS/GUARD | [WireViz](../hardware/cables/prototype-r0/pack-dual-ntc-r0.yml) | [SVG](../hardware/cables/prototype-r0/pack-dual-ntc-r0.svg), [PNG](../hardware/cables/prototype-r0/pack-dual-ntc-r0.png) | [TSV](../hardware/cables/prototype-r0/pack-dual-ntc-r0.bom.tsv) |
| Motor pair, W-MOTOR | [WireViz](../hardware/cables/prototype-r0/motor-r0.yml) | [SVG](../hardware/cables/prototype-r0/motor-r0.svg), [PNG](../hardware/cables/prototype-r0/motor-r0.png) | [TSV](../hardware/cables/prototype-r0/motor-r0.bom.tsv) |

## R0 logical pin map

| Main interface | Net / role | Proposed wire color | Far end |
| --- | --- | --- | --- |
| J5.1 | 3V3 | Red | J101.1, sensor VDD |
| J5.2 | GND | Black | J101.2, sensor GND |
| J5.3 | I2C_SDA | Blue | J101.3, sensor SDA |
| J5.4 | I2C_SCL | Yellow | J101.4, sensor SCL |
| J2.1 | Protected PACK_P | Red | Protected pack P+; retain PCM |
| J2.2 | GND | Black / function-labelled NTC return | Protected P− and two isolated sense returns via qualified splice |
| J2.3 | PACK_NTC | Function label | TH1 to GND, charger TS |
| J2.4 | PACK_GUARD | Function label | TH2 to GND, independent window |
| J3.1 | MOTOR_P / bridge OUT1 | Red | Motor P role, to verify on received motor |
| J3.2 | MOTOR_N / bridge OUT2 | Black | Motor N role, to verify on received motor |

**Black MOTOR_N is not system GND.** Both motor wires are bridge outputs. The diagrams identify logical pins; they do not establish a mating-face orientation. Check actual numbered PCB pads before wiring.

## Cut blanks and installation

- Tip: four proposed **160 mm cut blanks**. This is stock planning, not a measured installed length or an instruction to cut a fitted assembly. Set final length and end preparation after the actual J5/J101 positions, carrier route and service access are checked.
- Motor: initially retain the received **nominal 100 mm integral leads** from the candidate NFP motor. Do not shorten them until the route is measured. Gauge, received colors, polarity behavior and termination still need checking; no extension is selected.
- Anchor tip wires to the carrier near both ends, leaving slack at the small tip island. Anchor the motor leads near their exit and J3 while supporting the motor capsule separately.
- Keep harnesses out of shell edges, the common male nose thread/female cap, rear bolt, seals and cover compression surfaces. Check the current R2 board/carrier loading and removal paths before final trimming. The earlier split-retainer/threaded-nut proposal is historical; actual R2 joint tolerances and supplier process remain open.
- Route the tip harness separately from the motor pair and verify the sensor bus with the motor operating on the bench. The drawing establishes no noise, current-capability, insulation or strain-relief result.

The [harness source README](../hardware/cables/prototype-r0/README.md) records endpoint details, unresolved interfaces and reproduction commands. WireViz renders provide a visual and child-parts reference; the TSVs are not approved order lists. OEM motor leads are included with the motor, not a separate wire purchase. Logical PCB interfaces are excluded from the cable BOMs.

The pack adapter diagram is a logical topology. TH1 and TH2 are separate Vishay NTCLE413E2103F524A heads, each physically coupled to the cell. Preserve their factory 52±5 mm leads initially. The shared GND needs a qualified insulated splice; do not force three wires into a single PH crimp. Mate selection, extensions, attachment, insulation and strain relief remain open. Keep JP1 open pending charge qualification.

The magnetic charging-contact harness remains to define after its actual contact and mechanical choices. The human-owned product BOM should eventually list approved harnesses as top-level assemblies. Keep detailed wire/termination rows in the WireViz child BOMs; do not copy them into `hardware/bom.csv`.

## R2 termination and fanout study

`hardware/design/wire-termination-screen-r2.json` records the primary-source
contact/wire ranges and dimensional examples. It does not select a wire,
tooling, current rating or finished harness.

- Reserve the flat wire row at each plug before converging into the round
  bundle. At the small-contact catalog maximum wire diameters, SH4 spans
  3.8 mm and PH4 spans 6.9 mm. Those rows are wider than the current round
  corridors at the connector face. [JST SH](https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf),
  [JST PH](https://www.jst.com/wp-content/uploads/2025/06/ePH.pdf).
- The existing Vishay NTCLE413E2 sensor has overall-tinned stranded leads.
  Use a documented insulated solder-to-stranded-pigtail transition before
  ordinary PH crimps; direct crimping of those factory leads is not assumed.
  Preserve the two existing sensor choices and their circuit interfaces.
  [Vishay mounting guidance](https://www.vishay.com/docs/29078/ntcle413.pdf).
- Choose real wire and bend geometry together. The Alpha2841/7 dimensional
  example specifies a 10 × diameter bend radius; the CAD corner spheres do
  not demonstrate that bend. Splice insulation, slack, retention and actual
  current/drop remain open. [Alpha Wire specification](https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=2841%2F7).

The newer [Full05 tip-bend review](../hardware/design/tip-wire-bend-r1.json)
binds the saved route's ten cylinder segments and nine corner spheres to the
native source. An 8.3 mm leg between two 90° turns limits uniform circular
fillets at those fixed vertices to 4.15 mm radius. The existing documented
wire example fails that screen under the separately stated radius-basis
interpretations. This does not rule out a different smooth route or select a
wire. Route real conductors, exits, slack and restraints, then check surrounding
parts. The measured 153.931 mm polyline is not an accepted cut length or a
lower bound; keep the 160 mm blanks as planning inputs only.

## Protected-pack mate lead candidate

The [Bitcraze spare battery cable, SKU 100046015](https://store.bitcraze.io/products/spare-battery-cable)
is a concrete OEM Molex 51006 mating-lead candidate. Its
[Rev1 drawing](https://www.bitcraze.io/documentation/hardware/battery_cable/battery_cable-datasheet.pdf)
separates a 33 mm overall text specification from 22±1 mm between the lead-exit
face and free ends, with 2±0.5 mm stripped ends. The connector body is drawn but
not dimensioned. Verify the received pair, polarity, maximum body/boot envelope,
wire/contact ratings and route before using it in a PH4/dual-NTC adapter.
This lead is not purchased or added to the product BOM; the logical adapter
source does not yet specify its final splice/extension construction.
