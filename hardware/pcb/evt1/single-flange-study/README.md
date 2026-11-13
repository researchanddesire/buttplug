# Single flange PCB study

This separate, unrouted candidate combines the existing flange electronics, fixed compass and four PCB-mounted charge/data targets on **one flange PCB**. The existing body PCB, charger, power rails, motor driver, tip-temperature sensing and protection circuits remain unchanged. It does not consolidate the body electronics into the flange.

`single-flange-placement.kicad_pcb` contains 35 retained source positions and four new Mill-Max1946 fixed targets. The 35 positions retain every selected pad/drill, Fab outline, courtyard, antenna keepout and schematic pad net. Only assembly silk is deferred and package models are linked locally. `J1` contact wire lands become four actual through-hole targets; sensor-only `J82` interboard lands are unnecessary after its circuit joins the flange. The existing body `J81` lands remain untouched. There are no tracks or vias and no new fabrication files.

## Physical arrangement

The editable KiCad outline is82×26×1mm, within the fixed88×32mm flange cross-section. Its left edge opens beneath the actual integrated antenna; two R2 edge reliefs preserve the existing case screw axes at X12/Z±13. Four provisionalØ1.6 mounts lie at (−30,−10), (−38,+10), (+38,−10), (+38,+10), in product X/Z millimetres.

The joint mechanical study adds3.2mm behind the original rigid rear face. The PCB F surface is productY−26.952 and B is−25.952. Parts face inward on B; only the two Omron B3U buttons and four fixed targets face outward on F. The requested battery growth envelope ends atY−22.6. Conservative selected heights leave at least1.902mm between the populated B-side parts above that envelope and the growth envelope, before unqualified solder stand-off and received tolerances; the tall J4/J7 headers are to its left. Received pack dimensions, tolerances, insulation and retention remain separate checks.

| Interface | Product X/Z centres | Detail |
| --- | --- | --- |
| Targets | (−16,10), (−10,10), (−4,10), (+2,10) | GND/D−/D+/5V;6mm pitch; Mill-Max1946-0-00-15-00-00-03-0 |
| Buttons | (−17,0), (−9,0) | Existing Power/Mode circuits and selected B3U-1000P retained |
| Compass | (33,0) | LSM303AGR on B; new proper rigid package-to-flange registration is required |
| Radio | (−30,0) footprint origin | Existing ESP32-C3-MINI-1-N4X with its integrated PCB antenna toward the left end |

Mounting screws are not part of the39 electrical package models. The left mounts are inside the antenna clearance region and require nonmetal hardware; the existing NBK RENY candidate still needs actual engagement/strength checks in the mechanical study. Do not describe that region as metal-clear while metallic screws are fitted.

The1946 has a nominal3.048mm face height and2.794mm tail below its seating shoulder; its target face isY−30.0. The manufacturer catalog gives length tolerance±0.127mm and diameter tolerance±0.0508mm. The recommendedØ0.8636 mounting hole is retained; theØ3.2 copper land is an engineering choice requiring supplier/assembly acceptance. The B-sideØ4 annular plastic bearing posts and four nominal tails must be included in mechanical checks. PCB/solder flex is not credited for docking force.

The joint mechanical candidate uses a permanent pre-cured common diaphragm/web between PCB and rear cover, covering F-side X−20.7..+4.7/Z−3.15..12.65, with two closed switch cups and four contact necks. No other F-side part is placed there. Molding barriers, compatible materials, force/travel, shaft tolerances and electrical/sealing processes remain unqualified.

## Electrical conservation and remaining work

`interface-contract.json` records the unchanged numeric1:1 J6/J7 body interface, preserved U81 nets, recovery and four-contact substitutions. TPS3422 hardware reset, Power/Mode/BOOT recovery, USBLC6,22Ω data resistors, input PTC/diode, pullups and decoupling remain present. The body-to-flange loom remains; the former separate sensor loom can be removed only when its assembly documentation and new merged schematic are implemented.

The board is a placement study. Native DRC has zero placement violations with every check enabled;120 unconnected items are expected. New merged schematic/ERC, intentional power and ground returns, USB routing/ESD, local decoupling, routing/DRC, stock/service access and fabrication outputs remain to do. The supplied39 package models include the actual103-solid Espressif OEM model, a primary-dimensioned1946 profile and KiCad nominal selected package families. Manufacturer maximum dimensions remain separate from nominal STEP geometry. Every model must pass the cold geometry/pose checks before mechanical acceptance.

The MINI-1 has no host coax/RF feed. Its antenna region X−41..−35.6/Z±6.6 is outside the host board and excludes all four copper layers. The pack is42.35mm away horizontally. The joint study moves steel keepers away from this end. Espressif's15mm all-direction housing-clearance guidance is **not fully met** by this current component arrangement; C31/C32 remain near the module's VDD edge, while avoidable22Ω and diode positions have been moved beyond15mm. C31's3V3 land is2.15mm and C32's3V3 land3.483mm from U6pad3; route short supply/return paths with adjacent ground vias. Resolve or explicitly qualify this near-pin RF tradeoff, enclosure/overmold loading, received module/pack and final range/throughput before claiming RF performance. Keep motor/charging current returns away from the compass; new assembly calibration and an actual magnetic survey remain required.

[Espressif module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3-mini-1_datasheet_en.pdf), [Espressif module positioning guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c3/pcb-layout-design.html), [Mill-Max catalog, printed page223.1](https://www.mill-max.com/sites/default/files/external/catalog/2020-01/202-246_3.pdf).

## Review and rebuild

`mcad.json` binds every model file/hash and proper model-to-product4×4 transform. `SingleFlangePlacement.FCStd` has an editable, fully constrained PCB outline/drill sketch and native1mm Pad, plus39 links to actual imported selected-part bodies. `SingleFlangePlacement.step` follows those explicit F/B planes. `NativeKiCadPlacement.step` is the independent raw KiCad export at origin100×100mm; its FR4 and solder/mask seating offsets differ, so do not apply a single rigid height correction to use it as finished-board clearance proof. `native-step-pose-checks.json` records those exact layer offsets. No model is reflected.

Run `build_study.py` with the installed KiCad Python only to deliberately regenerate this unrouted study. Run native KiCad10 DRC, export STEP at origin100×100mm, `export_mcad.py`, `check_study.py`, `check_oem_model.py` and `check_native_step.py` for the source,159+4 pad,61 module-contact and actual package-geometry audits. `source-inventory.json` binds all original device artwork/netlists/parts data. Original product natives, routed device/dock boards and the human-owned BOM remain unchanged. No print, assembly, power, radio, sealing or build release is claimed.
