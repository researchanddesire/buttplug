# AGENTS.md - Buttplug Compass

Guidance for agents working in this product repository.

## Documentation Ownership

- Assembly documentation lives in `assembly-docs/`.
- Developer documentation lives in `developer-docs/docs/`.
- End-user documentation lives in the separate `simple-docs` repository.
- BOM data lives in `hardware/bom.csv` and is human-owned.
- Hardware source folders are `hardware/cad/`, `hardware/pcb/`, and
  `hardware/cables/`.

Do not commit generated assembly-site output to this repo. The assembly docs
aggregator renders `hardware/bom.csv` into the copied `assembly-docs/bom.md`
page at build time.

## Ohai Assembly Package

An Ohai-eligible product repo must keep these files present and non-placeholder:

- `assembly-docs/site.yml`
- `assembly-docs/nav.yml`
- `assembly-docs/index.md`
- `assembly-docs/pcb-overview.md`
- `assembly-docs/cable-harnesses.md`
- `assembly-docs/bom.md`
- `assembly-docs/assembly-guide.md`

Only add the GitHub topic `ohai-assembly-docs` after replacing all template
placeholders and passing local assembly/build checks. Never add that topic to
the `rad-project-template` repo itself.

## BOM Rules

When editing any `hardware/**/bom.csv`, follow the RAD BOM standard:

- Use the fixed 12-column header exactly.
- Use only the canonical category codes.
- Use the en dash `–` for empty values; do not leave blank cells.
- Do not hand-edit `.github/workflows/scripts/bom.schema.json`.
- Run `python .github/workflows/scripts/bom_lint.py` after BOM changes.

Full reference: https://dev.researchanddesire.com/meta/bom-standard/

Product BOMs list cable harnesses as top-level assemblies. Detailed cable BOMs
belong to Wireviz output. Link generated `.bom.tsv` artifacts from assembly
docs; do not copy child cable BOM details into `hardware/bom.csv`.

## Docs Rules

- Update `developer-docs/docs/` with code, API, integration, state-machine, or
  behavior changes.
- Update `assembly-docs/` with build steps, assembly photos, tools, hardware
  source links, and BOM page prose.
- Update `assembly-docs/cable-harnesses.md` when `hardware/cables/` gains or
  changes Wireviz sources.
- Open a change in `simple-docs` for customer-facing quick starts,
  troubleshooting, FAQs, and support content.
- Keep the rendered BOM out of developer docs and simple docs.

## Workflow

- Do not auto-commit changes unless explicitly asked.
- Author and review the product as editable FreeCAD multi-body assemblies.
  Use component bodies and linked source geometry, including KiCad StepUp PCB
  models. STL is a derived print export. Replace bounding-box fit proxies with
  models of the selected parts, with manufacturer geometry/provenance recorded.
  Use the existing UTM FreeCAD Linux VM when native macOS FreeCAD is unstable.
- The dock must follow `developer-docs/docs/assets/overmold-cradle-concept.png`:
  rounded pocket-toy clamshell, orange upper shell, dark lower shell, cream
  inner chamber/scalloped bezel, blue three-button controls and a working screen.
  Screen/buttons and UV-C cleaning LEDs are required for this EVT. UV needs
  hardware lid/thermal cutoff, a qualified source-power budget and measured
  optical/cleaning validation; do not claim sterilization. Plastics target MJF
  or SLA; use multiaxis CNC-lathe or casting constraints for metal parts.
- Keep changes reviewable and scoped to the request.
- Advance the actual EVT PCB and FreeCAD assembly directly. Keep earlier
  fixture and routing studies as reference evidence.
- Use the existing Compass doc in the R+D project Drive folder for design
  reviews and physical bench results. Identify the Git commit and the specific
  native assembly or board revision in each entry.
- Bring physical geometry decisions to the owner in chat with labeled views,
  sections or motion overlays. When a clash or fit issue could drive a layout
  change, show the current geometry, the issue and the proposed options before
  changing the accepted direction. Continue unrelated verification meanwhile.
- Do not commit `.DS_Store`, `cable-export/`, or generated cable render outputs.
- Prefer existing project patterns over new abstractions.
- If you learn lasting project-specific context, add it here.

## Current Work

- Start with `developer-docs/docs/index.md`, then the current build proposal.
  Exact source paths are in `developer-docs/docs/hardware.md`.
- Current mechanical direction: `hardware/cad/manufacturing-layout/`. P1 and
  R35F are prior references; the old fit-kit recommendation is withdrawn.
- Use two CNC-turned metal pieces: body and cap. Preserve the 15 mm neck. The cap holds the motor on a
  metal stop beside an offset potted NTC, with a foam-supported body PCB.
  Prewire that rotating module; connect flange tails only after threading it.
- Target four main mechanical pieces plus silicone boot/standard soft goods.
  No rigid scaffold, separate motor clamp/tip carrier, pack lid or button plungers.
- Saved rear joint: short M18×1 threaded stub, 24 AF ×4 mm thin-nut envelope
  and Ø20 collar with 18.4 mm opposing flats in a keyed tray. The 2 mm tray pad
  is clamped against the Ø24 shoulder; no socket adhesive or compression limiter
  is credited. Collar flats require indexed milling after turning.
- Rear nut retention direction: specified tightening torque and Loctite on
  the M18×1 metal threads. No locking washer. Torque, grade/cure process and
  retention are unqualified; clamp preload, plastic creep, key engagement and
  pull-through are separate checks. Tighten before boards/pack/loom with a
  narrow axial driver. The unshifted nut envelope overlaps both pack NTC heads
  at some possible final angles; show the owner before moving any geometry.
  See current `DFM.md` and `review.json`.
- A separate `evt1-integration/rear-joint-trial/` now models stock ifmE10028
  and a native two-jaw service-driver proposal.143 nominal tool-loading poses
  and61 nut orientations pass against the frozen rigid Tray/body; five-body
  cold/BOP and STEP checks are separate from physical tooling qualification.
  The drawing's27mm corner value is not credited as a maximum: clearance uses
  a full24AF hex. The two wider failed driver studies are archived. No source
  body/Tray/BOM change, nut lock, tightening torque or tool strength is released.
- Flange outside stays 88×32 mm. Local nut well wall is about 1.25 mm; screw
  posts/PCB tabs move. The actual-board EVT integration replaces the old pack
  gauge with a requested protected-pack envelope. Molding/received-pack trials
  remain pending. Wet-side
  boot cuff is still bonded; cover screws close plastic only.
- Overmold sequence: secure the lower metal body/nut to the flange, close BOTH
  rigid plastic flange halves, then mold one continuous silicone skin over the
  closed assembly/root. Do not propose separately overmolded halves or an exposed
  rear service lid. `hardware/cad/manufacturing-layout/overmold-trial/` now holds
  separate native skin/split-tool CAD and three print STLs for an INERT casting
  trial. Its solid dummy represents the closed assembly only; it does not
  replace the two product halves. 90×38 skin, 1 mm nominal end coverage, ~24.2 mL
  fill network; contact/button tooling and real cavity seals are not implemented.
  No slicer, print, cast or material/process result. Cap-after-molding is an idea,
  not a demonstrated wiring sequence; current cap tails need connecting while
  the flange is open. EVT workshop battery service consumes/remakes the skin
  before opening the rigid halves; trial removal on an inert assembly first.
  No battery path through the Ø12 neck is introduced. Qualify molding on dummy assemblies before real
  electronics/battery; material, cure, pressure and sealing are not released.
- Read the current CAD `DFM.md` for sources, setup/tool candidates and fit limits.
  No supplier/handbook acceptance or physical manufacturing proof is claimed.
- Preliminary thermal study: `developer-docs/docs/thermal-presence-study.md`,
  `hardware/design/thermal-presence/` and `tools/study_thermal_presence.py`.
  Source-bound cap warm-up comparisons favor Grade2 titanium for response/mass,
  with316L as a bench baseline; no material is selected. Contact/installed-sensor
  parameters are assumed, not measured. Temperature alone is not qualified
  rectal-presence or removal evidence; exposed copper's antimicrobial benefit
  does not establish mucosal safety or replace cleaning.
- Case data-link/thermal direction: use the same four wired contacts for local
  dock-to-plug USB telemetry and direct PC-to-plug USB programming, recovery,
  configuration and diagnostics. The dock is a USB host in standalone mode.
  Give the plug's D+/D− pair to one host at a time and preserve a direct PC
  recovery mode. Study the Main PCB before changing enclosure geometry. The
  cradle has no radio or antenna. The case-radio and antenna-pocket studies are
  historical candidates.
  The active Main electrical source is `wired-main/dock-wired-system.kicad_pro`
  with the schematic and PCB in the same project. The active dock native is
  `hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd` with adjacent
  relative links. Continue these directly. Native PCB DRC has 13 opens and zero
  other rule findings. Main-only schematic parity is zero. The separate
  `dock-wired-transport` root shares the leaf sources and carries the lid/UV
  sheets for the system ERC and harness checks.
  The four J102–J94 wire sweeps are now installed in the product native and pass
  closed-pose nominal clearance. Measure trim, restraint and USB on the build.
  The approved 1.30 mm dry-side J401 pocket leaves 0.70 mm nominal liner wall
  and 0.25 mm housing clearance. Seat the lower liner over the fixed UV harness
  before final contact-wire dressing. Use the 1.50 mm loaded display PCB shim
  and two flex passages. The linked custom J201–J301 flex shows the closed
  route. A 59.119 mm moving span at R5 minimum clears 25 exact sampled poses.
  Verify cable guides, received fit, full hinge travel with UV wiring and UV-C
  leakage at both liner passages.
  `hardware/design/evt1-bench-ordering/dock-enclosure/` holds the enclosure
  STEP quote ZIP exported from the wired FreeCAD assembly, including the
  approved pair of blind Hall recesses, the J401 pocket and flex passages.
  Each Hall board has 0.312 mm nominal clearance and a 0.48 mm checked web
  under the cut. Both Hall brackets use the approved integral lip (0.75 mm
  capture, 0.90 mm slot for a 0.80 mm board). Slide the boards in before
  mounting the pairs. Confirm as-printed fit and withdrawal restraint.
  The native has both linked PCBs and captured magnets in the active base and
  lid modules. The quote includes their custom parts. Re-export changed bodies before
  using the packet after an enclosure geometry change.
  Hall Main positions are approved at dock X−44.50/Y39.00 (J630, 270°) and
  X40.50/Y19.00 (J650, 90°), both on F.Cu. Seat their plugs before installing
  the lower liner. Check wire dressing and liner installation on the build.
  The PCB retains
  the original enclosure and board datums, with the 62 added package models
  checked nominally and U158 at its reviewed position. The oscillator and
  MCU_STOPn, MON_I2C_SCL, SOURCE_OK and PC_LOCKn are routed at fixed footprints. In1
  remains continuous with the limiter fault readback, USB enable pull-down
  and host I²C clock/data networks routed. Finish the RP2040 power, run
  control and other I²C links. Prior routing checkpoints and
  rejected routes live under `layout-candidate/`. The lower shell blocks direct
  axial access to all seven underside service pads. An installed PC-lock
  access path is still open. The candidate also has
  matched 4.22 Ω UV board quotes and compiled RP2040/STM32 targets for fresh
  tip readings. The matched Main uses R107 at 40.2 kΩ. Complete host routing
  and installed USB/UV checks remain open.
  Record docked tip-temperature history and a fresh, timestamped removal baseline,
  even if removed early. Distinguish Charging / Charged — cooling / Ready using
  confirmed charge state and qualified thermal criteria, including UV heat.
  Current CHARGE_STATUS_N is only charger/pull-up, and the dock lacks plug telemetry;
  UV module NTCs are not plug or ambient measurements. A plug RAM-history
  candidate now exists (see firmware note below); the case data path, charge
  interpretation and Ready behavior remain unfinished. Fan/vent/source-budget
  design is a candidate, not selected.
  This thermal session is authorized to change the case for incorporation into
  the main integration; see the current handoff in `COLLABORATION.md`.
- EVT1 electrical source is now `hardware/pcb/evt1/`; R35F is preserved in
  `layout-seeds/` and is NOT synchronized fabrication artwork. System/body ERC
  and functional pin contracts pass. All five routed PCBs pass native10.0.8
  DRC with zero violations/unconnected items and native pad/netlist parity.
  `native-checks.json` binds reports and exported netlists to source/library
  hashes; run `tools/check_evt1_native.py` before the electrical verifier.
  Body is6-layer1mm, flange4-layer1mm and sensor2-layer12x10x1mm with two1.6mm
  holes on9mm centers. Exact PCB parts are selected in `parts-selection.json` /
  `pcb-ordering.csv`:114 purchased positions,53 order lines,8 copper/manual
  features; independent native/order and80 passive-MPN checks pass. Five
  `assembly-quote/` ZIPs include exact parts/native positions and fabrication
  files. C83 is TDK C2012X5R1E226M125AC22uF25V; require>=10uF effective at3.3V
  over intended temperature/age in incoming/process qualification. Pack, cap thread,
  flexible loom, final factory axes and seals still need integration.
  DFM study is not a build/tooling release. Battery and full BOM OPEN.
  Use `tools/build_evt1_device_pcbs.py` for working seeds/route imports and
  `preserved-control-routes.json` for unchanged-terminal source copper. Keep the
  native device candidates out of a full-product fabrication release. `place`
  now requires `--restart-layout` to replace an existing board; preserve routing
  outside the output directory first. KiCad7 loading a second live
  board can invalidate the first board's project settings; extract source data
  before loading the destination. Native SaveBoard then requires only one
  active board. Former internal SW3/SW4 are removed; J4 EN/BOOT and external
  Power/Mode recovery remain.
  Loose-end cleanup must preserve junctions in the middle of a track. Use the
  native DRC list, trim to connected anchors and rerun DRC between passes; do
  not recursively delete tracks using the in-memory dangling-end test.
- Actual device-board mechanics live in `hardware/cad/manufacturing-layout/evt1-integration/`.
  `EVT1Product.FCStd` uses the actual three PCB MCAD exports, four main parts,
  four-contact rear half, integral two-boss compass mount and shortened body
  sleeve. Original manufacturing/dock natives remain read-only sources.
  Independent nominal checks pass:8256 hard pairs, mates/softgoods/screw heads,
  25 flange loading,25 sensor loading,29 requested-pack/NTC loading and108 cap-module
  poses. R39 moved0.4mm and its selected maximum case clears the drafted seat0.250mm; R76 moved
  to permit U71 ground return. J81GND hand-solder land has a plated via.
  Two dry-fit plastic STLs/four STEP files pass saved-native readback checks.
  Sensor backY-10.8/FY-11.8; integralØ4 bosses/pilotØ1.1 reserve M1.4x0.3 taps.
  Prototype screws:NBK SPA-M1.4-2.5-MC3 RENY, actual headØ2.5x0.8 versusCAD
  Ø2.6x0.85 budget. Pilot/tap, strip/torque, received parts and actual bit need
  trial. Board local+X→product+X,+Y→-Z,Fnormal→-Y; distinct LSM package axes and
  measured factory calibration remain open. Body PCB maps to product(x,y+5,z-0.5);
  top-entry J5 reserves the JST6.3mm mated height. Motor case uses the published
  26.3x11.1mm maximum and a separate full-diameter6mm rear lead-exit allowance;
  actual lead shape/gauge still needs supplier confirmation. Sleeve rear upper
  corners are relieved with the PCB edge still covered. No flexible-wire, tolerance,
  physical fit, material, molding or complete-product release follows.
- Current wire sources are `hardware/cables/evt1/`: seven WireViz recipes,
  24 native pin contracts and36 logical diagram segments, with independent
  graph/child-BOM checks. Cut lengths remain starting stock; ten nominal
  interboard paths are independently checked, with the other installed routes OPEN.
  The colliding away-facing study is preserved under `evt1-integration/loom/archive/`.
  The working PCB and product native now adopt J7(-23.8,-15.8,-90deg),
  D71(-31.5,-15,0deg), U75(-23.3,-27.2,0deg), D73(-15.85,-17.6,0deg), opening J7
  toward the neck and keeping U75 beside the contact lands. The west
  PCB body extends toY-29/-9 within existing overall tabs/bounds; mounting holes
  and right-hand seats remain. Native DRC/pad parity and8256 saved product
  pairs/loading checks pass. The prior source-bound preflight/routing evidence
  lives in `loom/neck-facing-j7-trial/`; its source snapshot intentionally
  predates promotion. Current ten-wire forms are `loom/EVT1Loom.FCStd`.
  `loom/review.json` records ten native BOP/closed-mesh checks,1450 part pairs,
  45 wire pairs, sampled minimum radius4.306mm and minimum wire gap0.047mm.
  Wire STEP conversion is withdrawn; failed comparison/exports are archived
  and excluded from build kits. Other installed routes, egress/crimps, restraint
  and physical assembly remain open; path code requires the neck-facing J7.
- `hardware/pcb/evt1/pack-spec.json` / `PACK-RFQ.md` define the requested
  BC-PACK-EVT1-001 factory-protected EEMB LP502030HA pack:1.5A continuous,
  2A/100ms pulse,33x21x6.3mm maximum, PCM/lead exit toward the neck. Published
  A25357 is only1A continuous and is a construction reference, not this selection.
  EVT CAD includes the requested maximum plus1.1mm thickness/0.25mm lateral
  growth space and two dry Vishay NTCLE413E2103F524A head envelopes. No supplied
  pack, swelling guarantee or accepted PCM is claimed. Six physical conductors:
  power+/return and two independent NTC pairs; join returns only at bodyPCB.
  Pack factory leads are requested28AWG with JST ACHTR-02V-S/SACH contacts;
  separate body mate is ACHTP-02V-S/SACHP. CAD reserves7x4x2.1mm mated budget,
  not OEM geometry. Connect power after cap threading. Pack maximum moved
  0.3mm rearward, leaving0.95mm nominal passage behind the stub for sensor wires.
  Do not directly overmold/immerse/hard-pot the NTCs. Retention, soft supports
  and actual lead routing remain to design; RFQ has not been sent or accepted.
- The first-article device direction combines the former body and flange
  circuitry on one PCB in `hardware/pcb/evt1/one-board/`. The low, offset
  protected pack goes in the bulb. TH1 and TH2 retain independent hardware
  charge-temperature paths, and TH3 reports separate pack temperature through
  J8 and the ADS1115. Build `evt1-one-board` for this PCB. The larger
  `hardware/pcb/evt1/one-board-dev/` retains the circuit and adds rail
  isolation, thermistor simulation and probe access. Both use 44.7 µF
  nominal SYS population, with C12 and C22 left empty.
  The master bench J112 uses one polarized PC or DOCK key for VBUS, D− and
  D+; remove all power to swap keys. J111 takes the external dock host.
  Compact changes hosts by physically withdrawing the first mate; the direct
  PC saddle shares the dock seat and retains button access. The `direct-pc-fixture/`
  FreeCAD assembly and `direct-pc-contact-adapter/` KiCad project are eval
  sources. Check physical contact sequencing and USB before live insertion.
  Quote CT1–CT4 and J2 as vendor operations; see `master-bench-eval/` under
  `hardware/design/evt1-bench-ordering/` for the acceptance and upload files.
  Preserve the U6 integrated antenna keepout, 88×32 outside flange, Ø15 neck,
  rear joint and the four dock datums. CT1–CT4 keep Ø1.02 mm nominal plated
  artwork on Ø3.2 mm lands. Check the finished hole range and fixture the
  shoulders square to the laminate before soldering. The separate body
  and `single-flange-routing/` boards are source references. See
  `developer-docs/docs/one-board.md` for native checks and first-article limits.
  Provide positive local load support, whole-board loading/halves closure,
  silicone/cavity sealing and molding-mask removal. Solder/PCB flex is not
  credited as a docking-load stop, nor PCB encapsulation as a proven liquid seal.
- The product includes a smart USB cradle. Its magnetic interface has four
  conductive contacts exposed through sealed silicone feedthroughs: 5V, GND,
  USB D+ and D-. Use native ESP32-C3 USB for routine programming/data. Separate
  dock/interface prototype CAD now lives in `hardware/cad/manufacturing-layout/charging-dock/`;
  the main manufacturing native still retains its old two-contact references.
  `ChargingDock.FCStd` includes a revised rear half, continuous skin, four fixed
  Ø4 spool-head targets, a removable molding face mask and a printable clamshell.
  Row X−38/−32/−26/−20 at Z11.5 is GND/D−/D+/5V on6mm pitch; faces at Y−26.8 are
  0.3 mm proud. M2 nut retention/thread/finish/seals are unqualified. Moving pins
  are in the dock; 0.6 mm nominal compression uses insulating stops on the METAL
  target faces. Candidate Mill-Max 0906-2 has simplified envelopes, not OEM CAD.
  Dock-only Ø8×3 magnets act on buried Ø8×1 steel keepers; holding and compass
  interference remain untested. Case shell155×115×65, overall166×115×65 with
  hinge/screw latch. Load at +3 mm axial offset, then slide to mate; slide away
  before lifting. Face mask must withdraw along−Y before lateral mold opening;
  its slot is open to the parting edge to avoid trapping the proud heads.
  Two EVT1 cradle PCBs are routed and pass native ERC/DRC plus pad/netlist parity.
  USB board has a narrow PCB nose, flush GCT USB4105 face at X-57.5, four M2x4
  mounting screws, board bottom/top Z5.4/6.4 and port bottomZ5.1. Pin board remains
  28x10x1mm, with rear B.Cu J94 wire pads at local y8.5/dockZ41.7; retainer/window
  clears those pads through its raised pressure pad. PCB-derived `mcad.json`
  hashes bind the dock native.39 STEP solids/13 print meshes and nominal fits
  pass. Component bodies are fab-outline/height budgets, not OEM models.
  Gerber/drill ZIPs are quote files;0.15mm USB locating-hole-to-copper clearance
  needs supplier acceptance. No slicing, physical assembly, USB or powered result.
- The dock native now includes trial inner contact face-seal glands in the
  metal posts:ID2.10/OD3.60/depth0.38mm, nominal2x0.5NBR70 ring against the flat
  rigid rear half; boresØ2.10. Contact faces/pitch/dock stops are unchanged.
  `charging-dock/contact-seal-spec.json` controls requested finish/inspection
  budgets. Elliptical rings preserve volume only, not force/deformation/sealing.
  `contact-seal-trial/` has separate native/two print STLs, actual-post STEP,
  inert316L RFQ and water-column procedure; six solids/15static pairs pass.
  No physical leak/cure result; NBR/platinum-cure compatibility, received
  tolerances, preload/creep and finished contact material remain unqualified.
  This trial does not implement permanent button or complete cavity seals.
- `firmware` has separate `evt1` and legacy `prototype-r0` profiles. EVT1 uses
  ADS1115/TDK B57540G1103F000 two-wire NTC, GPIO10 pulsed excitation and fixed
  LSM303AGR. Native bus names are I2C_SDA/I2C_SCL; verify the pin contract.
  R75/R76+USBLC6 protect data; BQ24074 selects USB100. Dock wake diode-ORs into
  RTC GPIO1; independent raw Power drives TPS3422 7.5s/400ms EN reset. Mode also
  straps BOOT for ROM recovery. Circuit/code are digitally checked, not hardware
  proven. Heading math/NVS assembly calibration exists; factory registration,
  magnetic qualification, full compass haptics and contact/button seals remain open.
- EVT1 thermal history now keeps 64 distinct NTC attempts and 16 source-loss candidates
  in RAM, using actual start/completion times and per-boot identity. USB
  `thermal-status` reports the latest baseline/trend and first valid conversion
  begun after observed loss. Raw PGOOD edges may coalesce; source loss is not
  confirmed removal. Reboot/deep sleep discards history. Installed wired USB,
  charge/UV state, durable logging and qualified Ready criteria remain open. Host timing,
  invalid/stale, straddle, reconnection and ring-limit tests pass.
- Cradle styling: rounded Pocket Neopet-like clamshell for dry storage, charging
  and computer USB. Working screen, three buttons and UV-C cleaning LEDs are
  required for this EVT. The new authoring source is `hardware/cad/evt1-assembly/`;
  the prior box-shaped dock remains a reference. UV is not a sterilization claim: opaque
  enclosure, hardware lid-open cutoff, dose/efficacy, leakage, heat and material
  aging need validation. Study two contactless Hall cutoff channels with
  independent hardware and thermal paths at the existing left/right stations.
  Qualify release during opening and measure finished-unit UV-C leakage.
  Standalone probe and removable fixture quotes cover the initial magnet
  and threshold measurements on a separate bench supply. The routed probe
  has zero native rule findings; measurements and installed cutoff remain open.
  The Hall case-fit quote joins the hinge shell and liner set to the close
  1 mm captured target. A separate driver-free adapter has an audited window
  calculation; actual contact loading and fault/shutdown timing remain open.
  The selected display/contact/LED geometry and UI power
  design remain integration work, not a powered release. Current native dock
  readback has32bodies/1435nominalpairs and119sampled loading/access poses;
  relative source links also pass cold relocation/reopen. Four liner mounts
  and full-depth hinge slots are modeled; latch, pin retention, actual switch
  mechanics and UV backing/thermal joints remain open.
  `hardware/pcb/evt1/dock-system/` combines six source-bound new dock leaves:
  native10.0.8 ERC0/0 and812terminal conservation. `dock-control/` holds unrouted
  controller/lid placement candidates; ONE base PCB must combine source,
  controller and safety and replace the old USB model. New UV sense is3.65ohm,
  ~54.8mA nominal; aggregate budget lives in `dock-safety/power-budget.json`.
  Separate `dock-firmware/` has actual ARM builds,25host scenarios and native
  endpoint/pad audits, no flash/powered result. Old five-board report/quote kit
  excludes this new circuitry; its recursive source inventory needs refresh
  before a complete fabrication release. See the concept under
  `hardware/cad/manufacturing-layout/concepts/overmold-cradle/`.
- Rad's primary plug UI is template-based, with independently chosen sensory
  inputs/outputs and configurable range/threshold/trigger responses. Compass is
  secondary. See `developer-docs/docs/plug-templates.md`. The local Rad checkout
  is `/Users/lucianchapar/Github/RAD/rad-app-compass`, branch `codex/project-setup`.
  `firmware/main/plug_runtime.c` has tested mapping/wear helpers; full template
  application remains open. Wear telemetry explicitly stays unqualified/zero
  confirmed time. Actual Lockbox reductions remain disabled pending device
  proof, qualified wear detection and an atomic approved-session ledger.
  A keyholder may require plug use for a wearer's release. Treat assigned
  requirements as session-owned rule snapshots: the wearer sees instructions
  and progress but cannot edit targets/mappings/rates. Personal template saves
  cannot change an assignment. The assigned wearer view is currently a UI
  preview; assignment persistence, session authority and release enforcement
  remain open.
  `/app/plug/preview` is the authenticated full-dashboard walkthrough, enabled
  only by `PLUG_INTEGRATION_PREVIEW_ENABLED=true`. It uses fictional personas,
  browser-only draft assignments and simulated wear/countdown changes. Its
  role switcher does not change the real signed-in/selected account. Local
  staging-code preview is not a shared staging deployment.
  Wear-only countdown is an assignment mode: verified wear counts 1:1;
  unknown/removed/paused wear requests its own hold, and bonus time-credit
  mappings are inactive. Confirmed allowed breaks keep the existing provider
  lifecycle and wall-clock hygiene deadlines. Never clear Chaster/keyholder/
  approval holds to resume wear. Pure policy and a non-mutating Chaster plan
  exist; the live wear adapter/ledger/watchdog remain unbound. Do not reuse or
  broaden the approval-only freeze coordinator for wear cycles.
- Compass mode requires a three-axis magnetometer plus accelerometer tilt
  compensation. The molded flange arrow points toward the tailbone/back.
  Assume flange fit constrains installation to one or two orientations with
  adequate alignment; do not require wearer-specific pose calibration.
  Sensor axes must register to that flange reference despite cap-module rotation;
  LSM303AGR circuit/driver exists; placement, supply decoupling, physical axes,
  magnetic interference/calibration and final compass behavior remain open.
- Keep current developer docs short and update them in place. Do not append
  revision logs or duplicate history. Use `developer-docs/docs/archive/` only
  for a specific historical question; do not load the whole archive for context.
- Preserve unique uncommitted research when archiving. Use Git history for
  subsequent changes; do not auto-commit. Publication and licenses remain pending.
