# EVT1 electrical integration

Editable KiCad electrical revision for the current four-contact, two-wire NTC
and flange-fixed compass architecture. **The full product is not ready to
order.** All five routed PCBs pass source-bound native DRC and pad/netlist
parity. The three device boards fit the separate actual-board assembly CAD;
PCB parts are selected; non-PCB hardware, loom, factory axes and the full build package remain open. R35F boards in
`layout-seeds/` are preserved references and must not be fabricated as EVT1.

| Source | Saved state |
| --- | --- |
| `system-evt1.kicad_sch` | Full device hierarchy; native ERC passes. |
| `body/` | ADS1115 tip-NTC circuit replaces MC3635/TMP117 wiring. Charger EN1/EN2 select USB100. Routed6-layer1mm native; DRC zero. Actual component/mate envelopes fit the cap/body module. |
| `flange/` | Four targets, USB protection/22R series resistors, long-press reset and dock wake. Routed4-layer1mm native with locating tabs; DRC zero. R39 moved0.4mm to clear the tray seat; R76 moved to permit the U71 ground return. |
| `sensor/` | Routed12×10×1mm LSM303AGR board, twoØ1.6 holes on9mm centers; DRC zero. Two integral tray bosses/nonmagnetic screw envelopes register it. C83 part selected; effective capacitance and factory package axes require qualification. |
| `dock/` | Routed USB-C input board with independent CC pull-downs, USBLC6-2SC6 protection and TPS2553 current-limited power. |
| `pins/` | Routed 28×10×1mm pin board, four Mill-Max0906-2 footprints at6mm pitch. Rear wire pads at the lower edge. |
| `validation.json` | Independent native pad/netlist parity, functional pin contract and source hashes; full-product readiness remains false. |
| `native-checks.json` | Native ERC/DRC report hashes bound to exact schematics, libraries, boards, rules and exported netlists. |
| `parts-selection.json`, `pcb-ordering.csv` | Exact selections for114 purchased PCB positions/53 order lines. Eight copper-only interfaces/jumpers are assembly operations. Per-complete-device-and-dock quantities; not the human-owned product BOM. |
| `parts-validation.json` | All122 native PCB positions accounted for; independent passive MPN/case/value/rating/tolerance checks and ordering parity pass. |
| `pack-spec.json`, `PACK-RFQ.md` | BC-PACK-EVT1-001 protected-pack RFQ for the two-board EVT1:1.5A continuous,2A/100ms pulse,33×21×6.3mm maximum, two dry external NTCs. Superseded for the one-board device by `one-board/PACK-RFQ.md` (BC-PACK-EVT1-002, 3-wire pack with its own NTC and a JST SH 3P plug). |

All five PCBs pass KiCad10.0.8 DRC with zero violations/unconnected items.
Both cradle boards also pass ERC with zero errors/warnings.
The system and body schematics pass ERC. Standalone flange/sensor pages report
undriven external supplies; their supply source is included in the full system.
No ERC/DRC exclusions are used to close shorts or missing connections.

## Selected PCB parts and assembly quotes

Each board's `assembly-quote/` contains exact manufacturer part numbers,
native KiCad purchased-part positions, the saved native PCB and its matching
fabrication ZIP. The worksheets account for all122 schematic PCB positions:
114 are bought parts and eight are copper features/manual operations.
`tools/verify_evt1_parts.py` independently decodes80 passive part numbers and
checks case, nominal value, voltage/dielectric and tolerance against native
schematics. Supplier stock and acceptance are not implied.

L1/L2 select Coilcraft XFL4020-152MEC, the1.5uH family in TI's reference circuit.
Its4.3mm maximum XY envelope is included in CAD. C83 selects TDK
C2012X5R1E226M125AC,22uF/25V X5R in0805; the schematic10V marking is a minimum.
Require at least10uF effective at3.3V over the intended temperature/age before
accepting the assembled process. Nominal capacitance and a higher voltage
rating do not prove this. Effective regulator capacitance, paste/reflow,
polarized orientation and powered behavior remain commissioning checks.

Flange D1's custom footprint numbers its physical cathode as pad2; align the
stripe with the native cathode bar. Do not populate a connector on hand-solder
lands. Body JP1 stays open until charge-guard commissioning passes. The full
engineering ordering sheet does not include non-PCB hardware/loom parts.

The protected battery is specified separately for RFQ. The published EEMB
A25357 pack is rated1A continuous and is only a construction reference for the
1.5A request. CAD models the requested33×21×6.3mm maximum, two3mm×10mm NTC
head/transition envelopes and additional1.1mm thickness/0.25mm lateral growth
space. These are requested bounds, not a received/approved pack or a swelling
guarantee. Preserve six pack-module conductors and join sensor/power returns
only on the body PCB. The continuous skin is consumed/remade for EVT workshop
battery service; no rear service lid or battery path through the neck is added.
The request now uses factory28AWG power leads and a JST ACH wire-to-wire
disconnect so the battery is connected after cap threading. See the RFQ for
the two housing/contact types and factory lead datum; the CAD mated box is an
allowance. Seven current WireViz sources are in `hardware/cables/evt1/`.

Sources: [TI TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf),
[Coilcraft XFL4020](https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xfl/xfl4020/),
[TDK C83](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X5R1E226M125AC),
[EEMB cell](https://www.eemb.com/product-248),
[Vishay pack NTC](https://www.vishay.com/docs/29078/ntcle413.pdf).

Each board's `fabrication-quote/` contains Gerbers,
separate plated/nonplated Excellon drills, routed slots, ZIPs and hash manifests.
They are **quote files**, with no supplier acceptance or purchase recorded.
The archive includes a fabrication request: body6-layer/flange4-layer/sensor,
dock and pins2-layer, all1mm FR4 and ENIG. Outer copper is1oz, proposed inner
copper0.5oz. Supplier review must reconcile the actual stackup and finished
thickness; no controlled-impedance agreement is claimed. Device boards use
0.15mm tracks,0.1mm copper clearance and0.25mm hole-to-copper clearance, with
Ø0.5/0.2mm body/sensor vias andØ0.6/0.3mm flange vias. The USB4105 locating-peg land pattern
requires acceptance of0.15mm hole-to-copper clearance; routing/copper clearance
is0.2mm minimum on the cradle boards, viasØ0.6/0.3mm and edge clearance0.3mm. Do not silently substitute
a thicker pin board: its thickness sets spring compression.

The dock board has a narrow front nose so the socket reaches the case wall.
PCB local(x,y) maps to dock(X=x−54,Y=y+42,Z=5.4..6.4). The USB socket face is
X−57.5. Four M2 mounts are at local(7,3),(7,19),(25,3),(25,19).
Pin-board local(x,y) maps to dock(X=x−42,Y=8.7962,Z=50.2−y) on its front face.
P91..P94 are GND/D−/D+/5V. J94 solder lands are on **B.Cu**, at y8.5;
the revised carrier/retainer opens behind those lands. `mcad.json` is extracted
from each actual board and bound to its SHA256, not a separately guessed board.

Use the matching `evt1` firmware profile; `prototype-r0` expects different
sensors and treats GPIO10 as an input. GPIO10 is now NTC excitation.
The power switch and dock presence diode-OR into RTC GPIO1. A separate raw
power-switch net drives TPS3422's7.5s hardware reset. Mode also pulls BOOT low
through a diode, allowing ROM USB recovery without extra external contacts.
Electrical checks do not prove wake/recovery timing or successful flashing.
The two former internal reset/boot switches are removed; J4 still exposes
service EN/BOOT. External Power/Mode provide the independent recovery chord.

Sources: [TPS3422](https://www.ti.com/lit/ds/symlink/tps3422.pdf),
[ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf),
[LSM303AGR](https://www.st.com/resource/en/datasheet/lsm303agr.pdf),
[USB4105](https://gct.co/connector/usb4105),
[TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf),
[USBLC6-2](https://www.st.com/resource/en/datasheet/usblc6-2.pdf).

Rebuild with `tools/build_evt1_electrical.py` (schematics/local libraries),
`tools/build_evt1_dock_pcbs.py` (placement/offline-router exchange/MCAD data),
then native ERC/DRC and `tools/verify_evt1_electrical.py`.
The placement/router tool uses KiCad7's bundled Python; electrical/rule checks
use KiCad10.0.8. Freerouting2.0.1/Java21 was used offline with analytics disabled.
Revalidate after regeneration; the schematic builder does not synchronize PCB
layouts automatically. `tools/export_evt1_cradle.py` refuses stale validation;
`--domains body flange sensor dock pins` exports all five quote archives and
also requires current actual-board assembly checks for device boards.
Device routing work uses `tools/build_evt1_device_pcbs.py`; `placement.kicad_pcb`
files are working seeds. `place` refuses to replace a saved board unless
`--restart-layout` is explicit; preserve routing outside the output before restarting.
`preserved-control-routes.json` records source copper
for interfaces whose terminal geometry is unchanged. KiCad7 can invalidate a
live board's project settings when a second board is loaded; extract source
records as data before loading the destination. Do not use the working device
boards as a full-product fabrication release. Local repairs are recorded in
`routing-adjustments.json`. U6 zero-radius rounded pads are normalized to
rectangles in both board/library, preserving their copper geometry. J81's
GND hand-solder land intentionally includes a plated stitching via.

Run `tools/check_evt1_native.py --kicad-cli PATH` before
`tools/verify_evt1_electrical.py`; stale source/report/netlist hashes fail.
The device assembly lives in `hardware/cad/manufacturing-layout/evt1-integration/`.
Component bodies are Fab-outline/height budgets and mates are allowances,
not OEM geometry. Nominal CAD fit does not establish flexible loom access,
supplier stackups, powered operation or physical assembly.

Assembly and commissioning belong in `assembly-docs/`; the human-owned product
BOM has not been changed. Physical USB power/enumeration/suspend, thermal,
spring load, loom, sealing and complete product operation remain EVT tests.
