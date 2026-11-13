# Hardware

## Open these files

- **Plug CAD.** Open `hardware/cad/manufacturing-layout/ManufacturingLayout.FCStd`
  for the turned body and cap. Open
  `hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/SingleFlangeBoardTrial.FCStd`
  for the single-board flange, pack fit and silicone barrier.
- **Plug PCBs.** Open `hardware/pcb/evt1/body/body-evt1.kicad_pro` for the retained
  body board and `hardware/pcb/evt1/single-flange-routing/single-flange.kicad_pro`
  for the routed flange. The combined schematic is `single-flange-system.kicad_pro`
  in the same folder.
- **Dock CAD.** Start with `hardware/cad/evt1-assembly/review-051/README.md`.
  Extract the entire review ZIP before opening `DockAssembly.FCStd`. That candidate has the
  recentered carrier and a known LCD/lid-board collision. The saved
  `hardware/cad/evt1-assembly/DockAssembly.FCStd` uses the earlier contact row.
- **Dock PCBs.** Open `hardware/pcb/evt1/dock-system/dock-system.kicad_pro` for
  the combined schematic and `hardware/pcb/evt1/dock-main/dock-main.kicad_pro`
  for the routed Main board. The JST lid remains a separate candidate at
  `hardware/pcb/evt1/dock-control/lcd-socket-candidate/dock-lid-jst-candidate.kicad_pro`.
- **Wiring and firmware.** Start with `hardware/cables/evt1/README.md` for the
  WireViz sources. Use `firmware/` for the plug and `dock-firmware/` for the case.

Record design reviews and physical bench results in the Compass doc in R+D
Drive with the Git revision and the specific assembly or board tested.

## Source details

| Area | Source / status |
| --- | --- |
| Saved dock master | `hardware/cad/evt1-assembly/DockAssembly.FCStd` and adjacent `README.md` document the editable bodies, StepUp links and earlier contact row. The separate 051 rebuild below uses the newer carrier. |
| Single flange PCB revision | `hardware/pcb/evt1/single-flange-routing/SingleFlangeRouting.FCStd` and adjacent KiCad source: one39-part flange board with contacts, switches and compass; body PCB retained. Native10 DRC0/0, ERC and163-pad parity pass with no ignored checks. Two bounded component moves clear the actual J7 mate;59 connector/tool poses pass. Matching rigid halves/skin/barrier native: `hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/`. Wire service/retention, full integration and fabrication acceptance remain open. Prior placement/source kits are preserved. |
| Local case telemetry study | `hardware/pcb/evt1/case-telemetry-study/PROPOSAL.md`: independent case/plug link and charge-observability candidates, preserving computer USB data/programming and ROM recovery. The case radio schematic passes native ERC and pin checks, including switched isolation of IRQ, SDA and SCL. Routing, coupled power, case runtime and physical operation remain open. |
| Display connector candidate | `hardware/pcb/evt1/dock-control/lcd-socket-candidate/`: JST 27FLZ-RSM2-TB routed lid candidate passes native DRC/ERC and 109-pad checks. Original lid artwork is preserved. `tools/build_evt1_dock_lcd_socket_replacement.py` authors the native received-fit fixture. Loaded contact height, cable tolerance/numbering and complete-case fit remain open; no invented internal socket cavity or full order release. |
| Bench ordering | `hardware/design/evt1-bench-ordering/` lists samples, incoming checks and the pre-radio Main, UV and populated JST lid quotes. The separate J302-only fabrication quote supports the unpowered fit fixture. |
| Single flange PCB quote | `hardware/pcb/evt1/single-flange-routing/assembly-quote/`: four-layer fabrication files, 35 SMT positions on 21 part lines and four separate through-hole targets. |
| Recentered dock interface | `hardware/cad/evt1-assembly/recentered-carrier-trial/RecenteredCarrierTrial.FCStd`: revised native carrier/retainer and pin board clear the supplied case/device context through 49 docking poses and two 12-angle sweeps. The spring C0 diagnostic remains explicit. The isolated full dock rebuild in `hardware/cad/evt1-assembly/review-051/` passed sampled loading; the LCD/lid PCB still overlaps. The dock master is unchanged. |
| Current mechanical study | `hardware/cad/manufacturing-layout/ManufacturingLayout.FCStd` |
| Part exchange | `MetalBody.step`, `MotorThermistorCap.step`, `FlangeTray.step`, `RearCover.step`; additional `ThinRearNut.step` envelope |
| Plastic study prints | `FlangeTray.stl`, `RearCover.stl`; slicer/physical trial pending |
| Detailed DFM / evidence | Adjacent `README.md`, `DFM.md` and `review.json`; prior stock-nut screen preserved under `archive/ring-lock-screen/` |
| Rear nut/tool trial | `hardware/cad/manufacturing-layout/evt1-integration/rear-joint-trial/`: selected ifmE10028 nut reconstruction and editable two-jaw axial-driver proposal;143 tool poses/61 nut orientations pass nominal checks. Separate from the product native; nut locking, received fit, material/torque and strength qualification remain open. |
| Overmold / clamshell proposal | `hardware/cad/manufacturing-layout/concepts/overmold-cradle/README.md`; process notes and generated illustration, not full skin/tool/dock CAD |
| Inert overmold trial | `hardware/cad/manufacturing-layout/overmold-trial/README.md`; editable `OvermoldTrial.FCStd`, skin/tool STEP and three print STLs. Closed solid dummy, no internals/feedthroughs/buttons; not physically built. |
| Dock / contact prototype | `hardware/cad/manufacturing-layout/charging-dock/README.md`; editable `ChargingDock.FCStd`, STEP and print kit. Clamshell/nest/pin carrier, fixed target posts/rear half/skin and removable face mask. Two routed cradle PCBs now drive the case/mount datums; no physical result. |
| Actual device-board integration | `hardware/cad/manufacturing-layout/evt1-integration/README.md`; editable `EVT1Product.FCStd`, four STEP parts and two dry-fit plastic STLs. Actual board outlines/component envelopes, integral sensor bosses and nominal loading checks; full package remains unfinished. |
| Rebuild / verify | `tools/build_manufacturing_layout.py`, `tools/verify_manufacturing_layout.py` |
| Earlier five-board baseline | `hardware/pcb/evt1/system-evt1.kicad_pro` and `pcb-ordering.csv` cover the retained body plus the earlier flange, separate compass sensor, USB and pin boards. Saved native DRC and pad/netlist checks cover those five boards. Use the single-flange and dock sources above for the revised integration. |
| Protected-pack request | `hardware/pcb/evt1/PACK-RFQ.md` / `pack-spec.json`: factory-protected1.5A pack,33×21×6.3mm maximum, six conductors including two dry NTC pairs. Requested pack/NTC/growth geometry fits; supplier acceptance and retention/lead process pending. |
| Prior electrical reference | `hardware/pcb/pack-pigtail-r35/candidate-f/system-r35.kicad_pro`; NTC/tabs not revised |
| Required compass sensing | LSM303AGR circuit/code is retained. The accepted single flange board replaces the earlier routed12×10mm daughterboard/two-boss mount; new rigid registration, package-axis transform, factory calibration, C83 effective capacitance and magnetic survey remain to qualify. |
| Required cradle interface | Four external contacts: 5V/GND/USB D+/D-; separate prototype CAD exists. Device circuit, routed cradle PCBs and wake/recovery code exist. Product PCB layouts, feedthrough sealing and physical USB qualification pending. |
| Firmware | `firmware/`, `evt1` for NTC/LSM303AGR and per-boot thermal history; `prototype-r0` for former TMP117/MC3635 hardware. Separate `dock-firmware/` STM32 target for the required LCD, controls and UV trial behavior. `firmware/thermal-history-validation/` binds the new history/USB checks. |
| Product BOM | `hardware/bom.csv`, human-owned and header-only |

![Turned metal and flange joint](assets/manufacturing-layout.png)

## Current interfaces

Two main custom metal parts: turned body with indexed collar flats, and cap.
Body features include Ø15 neck, Ø12 passage, straight Ø28 front bore and a
short M18×1 rear stub behind the shoulder.
Cap has rear-access bores, a metal motor stop and one offset sensor drill.
Motor pocket Ø11.1 is a nominal reference, with actual fit/force still open.

Nose joint: provisional M30×1.5 and a candidate 32×1 face O-ring. Thread teeth
are represented by pilot/root envelopes; supplier-reviewed callouts and
seal/closure tolerances must control machining.

Rear: Ø24 shoulder, Ø20/18.4 AF keyed collar and 6.25 mm shoulder-to-tip stub.
A 24 AF ×4 mm thin-nut envelope clamps the 2 mm tray pad. Retention uses a
qualified tightening torque and Loctite on the metal threads; qualification
and final-angle clearance to both pack thermistors remain open.
Threads are pilot/root envelopes, with 3.5 mm nominal full male length.
Boot cuff bonds to the unchanged Ø19.5 land and finishes at the Ø21 shoulder.
Separate skin/split-tool CAD now exists for an inert casting trial; final
contact/button tooling and process remain unfinished. Both plastic halves close before molding;
their screws close plastic only and lie beneath the continuous skin.
Nut well, shifted posts and revised PCB tabs are CAD-only proposals; local
wall is about 1.25 mm. The narrow axial driver is an unqualified reservation.

Cap-last wiring is unresolved with the flange closed: current tails connect
after threading while that flange is open. EVT workshop battery service consumes
and remakes the continuous skin before opening both rigid halves; practice on
an inert assembly first. No neck-extraction path or rear service opening is added.

Body PCB uses a sleeve/two foam pads, with no rigid cage. The actual-board
native uses the requested33×21×6.3mm protected-pack maximum, two dry NTC head
envelopes and reserved growth space; supplier acceptance and retention remain open.
The main manufacturing native still has the former two-contact targets.
The separate dock study replaces these with four Ø4 fixed spool-head posts,
GND/D−/D+/5V at X−38/−32/−26/−20, Z11.5 on6mm pitch; faces Y−26.8 are0.3mm proud.
M2 nuts retain them against the rear half. Silicone wraps their grooves;
an additional inner face-seal gland now holds a trial2×0.5mm NBR70 ring against
the flat rigid half. `charging-dock/contact-seal-trial/` has two fixture prints,
editable CAD, actual-post STEP/inert RFQ and a gravity water-column test. Gland
fit/space checks pass; compatibility, liquid-tight bonds, finish and retention
remain to qualify. A removable contact
mask pulls−Y before lateral tool opening. Permanent magnets are dock-only;
buried steel keepers still require compass-interference tests.

The earlier dock prototype shell is155×115×65mm,166mm long including hinge/latch.
Rigid annular stops touch the metal target faces to set0.6mm nominal pin
compression. Lower at+3mm axial offset, then slide to mate. The two EVT1 cradle PCBs are routed. The USB-C PCB has a narrow nose, four M2
mounts and a socket face flush with the case. The pin-board wire lands are on
the rear face beside the revised retainer opening. Their source hashes bind
the old CAD; its component bodies remain conservative envelopes. No powered result exists.

The current `evt1-assembly/` revision uses the rounded pocket-toy exterior,
cream chamber and scalloped bezel, three blue caps and the selected reflective
LCD with a native folded FFC. The case, chamber, carrier and retainer are editable
PartDesign bodies. Both existing cradle boards are real StepUp imports with
package geometry, linked as separate native documents. The physical pin-board
frame puts its rear wire lands at Z45.3; the carrier/retainer follow that frame.
The earlier Z41.7 envelope drawing was mirrored. MJF/SLA plastics and multiaxis
CNC/cast metal are the targets. The lower chamber has four screw mounts and
full-depth hinge-web slots;119 sampled loading/driver positions pass alongside
1,435 nominal assembled pairs. Received fit, tap/torque and strength remain
unqualified. Full switch travel/retention, latch/pin hardware, UV
metal/thermal/optical containment and installed wiring remain open.

The new full dock schematic is
`hardware/pcb/evt1/dock-system/dock-system.kicad_pro`. Its six source-bound
leaves cover direct computer USB/source qualification, STM32 controller,
actual LCD/buttons, independent lid/thermal/watchdog/latch/cuts and two UV
drivers. Native combined ERC passes with zero errors/warnings and812 conserved
terminals. The routed shared Main board combines source, controller and safety.
The UV module boards are under `hardware/pcb/evt1/dock-uv/`. The 051 CAD rebuild
uses the Main board placement snapshot and the earlier Molex lid. The routed JST
lid candidate and its received-fit fixture are separate. Dock firmware has ARM
build and host-test evidence. Integrated case fit, supplier acceptance, powered
operation and optical/cleaning validation remain open.

## Compatibility

EVT1 replaces the old split dock/service interface with protected external USB
and a hardware wake/reset circuit. Full-system and body ERC pass. Both cradle
boards pass native ERC/DRC and independent pad/netlist parity; fabrication quote
ZIPs are saved beside their sources, with supplier acceptance still pending.
R35F layout seeds are preserved and are not EVT1 fabrication files.

The ADS1115/two-wire thermistor and flange-fixed LSM303AGR have matching firmware.
The body/flange/sensor boards now pass native DRC and fit the separate
`evt1-integration/` assembly. The tray's sensor bosses use two NBK RENY M1.4×2.5
screw candidates; tap/torque and actual bit access need a trial. Saved-native
static and finite loading checks pass, including the shortened insulating sleeve.
Selected parts have native/order parity checks; effective capacitance, supplier pack,
actual retention/loom and factory axes still need qualification. Magnetic
calibration must be qualified with the assembled metal/motor and dock away.
The full EVT product is not ready to order. See [electrical details](evt1-electrical.md).

Current loom sources live in `hardware/cables/evt1/`. They replace the old
P1/R35F recipes for the current boards. J6/J7 remains numeric1:1 with
TIP_EXC_EN on pin10. Native wire-form work lives in `evt1-integration/loom/`;
the colliding prior study is archived. The working flange PCB and product
native now turn J7 toward the neck, move D71/U75/D73 and expand the west PCB
body inside its existing overall bounds. Native DRC/pad parity and saved
product geometry/loading checks pass. `loom/neck-facing-j7-trial/` preserves
the pre-route screen and acceptance evidence. The current ten-wire native's
`loom/review.json` passes native solid/closed-mesh, sampled bend and static
clearance checks. Wire STEP conversion is withdrawn with the failed comparison
archived. Other installed routes, first-article crimps/egress and restraint remain unfinished. Logical
recipes retain starting stock.

![Actual device boards and integral compass mount](assets/evt1-product.png)

![Native ten-wire route and neck-facing flange connector](assets/evt1-loom.png)

The current source-backed DFM review covers Protolabs/Fictiv/HLH guidance,
Sandvik tooling, source-access limits, setup candidates and tolerance budgets.
Body/cap metal volume is about32.9cm³, excluding the nut; material and total weight remain open.

The [thermal study](thermal-presence-study.md) compares316L, Grade2 titanium and
copper against the current cap geometry. Grade2 is the strongest thermal/mass
candidate to test; neither modeled warming nor a material name qualifies rectal
presence, cleaning or tissue-contact safety. Product material selection remains open.

![Native sections and sensor tool reservation](assets/manufacturing-sections.png)
