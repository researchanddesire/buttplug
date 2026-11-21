# Collaboration checkpoint

Start with `developer-docs/docs/prototype-build-handoff.md` and the current
source table in `developer-docs/docs/hardware.md`. The accepted single-flange
candidate is `hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/SingleFlangeBoardTrial.FCStd`;
it retains the body PCB. The original `ManufacturingLayout.FCStd` remains the
metal/joint source. The active dock is
`hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd`. Its linked Main
matches the active KiCad project under `case-telemetry-study/wired-main/`.
The closed assembly has verified nominal rigid and four-contact wire clearance.
Final wire dressing, Main routing, the Hall cutoff and physical acceptance
still gate a build release. Main-only schematic parity passes. The active
lower liner has the approved 1.30 mm pocket. The seated J401 housing and
eight stationary UV wires clear the saved case at nominal dimensions. Seat
the lower liner before dressing the four contact wires, which otherwise
intersect its lift path.
The active assembly uses the selected 1.50 mm loaded lid PCB shim and two
liner passages. The fixed flex clears the UV backing by 0.1895 mm with the
glass at its original datum. The custom J201–J301 flex is linked at the closed
pose. Its constant-length model clears 25 exact geometry checks across
0–110°. Verify socket seating, guide retention and combined hinge motion on
received parts, then measure UV-C leakage on finished units.
The approved blind lower-liner pockets give 0.312 mm nominal clearance at
each front station. The revised enclosure quote includes both recesses.
Verify the pocket floors with the print shop. Both Hall boards, brackets
and captured targets are fitted in the current CAD at the inherited switch
stations. Check retention, stud fit and measured lid release on the received
parts. Complete both Main receivers before UV commissioning.

## Case data-link and thermal handoff

Lucy explicitly authorizes this thermal session to make case changes for
incorporation into the main case integration. The requirements were sent to
the active **Continue Buttplug Compass work** task (`01a1ccb7-22b0-7cf3-b73d-7d965c648e6d`).

- Keep a general bidirectional computer ↔ case ↔ plug USB connection through
  the four contacts: firmware updates/ROM recovery, configuration, diagnostics,
  log/telemetry access and future device commands. The dock hosts USB on the
  same pair for standalone temperature and charge observations. See the
  wired Main proposal in `hardware/pcb/evt1/case-telemetry-study/WIRED-USB.md`.
- Log tip temperature while docked and capture timestamped, validity-tagged
  pre/post-removal samples and trend, including removal before full charge.
  Source loss must not silently become confirmed physical removal.
- Distinguish Charging / Charged — cooling / Ready. Terminate charging normally;
  readiness additionally needs qualified thermal measurements, a settled baseline
  and sufficient warming contrast. Account for UV heat and stale/missing data.
- `CHARGE_STATUS_N` currently connects only U1 pin9/R5 pin2, with no MCU input.
  The wired RP2040 candidate reads plug telemetry through the contact USB pair.
  The STM32 wired profile shows fresh tip temperature. Base/lid NTCs monitor
  UV modules. Charge sensing and an ambient reference remain open.
- Plug firmware now keeps 64 actual NTC attempts/16 source-loss candidates in
  RAM. Original start/completion times, invalid attempts, last fresh docked
  sample/trend and first valid post-loss conversion are retained separately.
  Reconnection and boot/timebase gaps cannot silently become a valid baseline.
  `thermal-status` exposes the latest summary over qualified docked USB;
  `firmware/thermal-history-validation/validation.json` binds 50 source inputs,
  host tests, both warning-free builds and the linked normal USB ISR audit.
  History resets at boot/deep sleep. Full history retrieval over wired USB,
  durable storage, charge/UV state, Ready thresholds and physical validation
  remain open.
- A small fan is a candidate, not an adopted part. Compare passive/fan cooling
  with a real heat-rejection path, UV-opaque vents if needed, and source/startup
  budgeting. The current worst-case UV/device allocation leaves only15.56mA
  below1.5A before a fan; do not assume spare power or a measured cooldown time.

Detailed acceptance and evidence are in
`developer-docs/docs/thermal-presence-study.md#charging-case-baseline-and-cooldown`
and PRD-26/27. Preserve the thermal study and these requirements when updating
shared case/electrical/firmware sources. The wired Main and charge-instrumentation
studies are under `hardware/pcb/evt1/case-telemetry-study/`. That directory also
preserves the historical radio study. The frozen Main implements direct PC USB
pass-through. Powered standalone telemetry and fan trials remain open.

## Saved versus discussed

- **Saved CAD:** two CNC metal parts, 15 mm neck, cap-mounted motor and offset
  potted NTC, separate body/flange boards, plastic tray/cover and a boot-root section.
- **Saved rear joint:** user-approved short threaded-stub/thin-nut direction.
  M18×1 callout, 6.25 mm shoulder-to-tip stub, generic 24 AF ×4 mm nut; Ø20 collar
  with opposing 18.4 mm flats keys into the tray. Nut clamps its 2 mm root pad
  against the Ø24 shoulder. No socket adhesive or separate compression limiter
  is credited. Threads are pilot/root envelopes, not helical teeth or released fits.
- **Rear-joint direction:** specified torque and Loctite on the metal threads.
  The washer study is superseded. Qualify the torque, threadlocker process and
  actual nut's final-angle clearance before installing the pack/NTCs. Show any
  proposed geometry changes in chat for owner input. Check creep, key engagement
  and pull-through independently of nut rotation. A narrow axial
  two-jaw driver reservation clears before boards/pack/loom; actual tooling
  needs qualification. The nut well leaves about 1.25 mm local plastic wall.
  Flange outside is unchanged; posts/tabs move. The separate EVT integration
  now uses a requested protected-pack/NTC envelope. See current `DFM.md` and `review.json`.
- **Electrical candidate:** `hardware/pcb/evt1/` has five routed PCBs passing
  source-bound native DRC and pad/netlist parity. Full-system/body ERC passes.
  ADS1115/two-wire NTC, LSM303AGR and wake/recovery have matching EVT1 firmware;
  both EVT1 and legacy builds pass. R35F remains an older sensor/layout reference.
- **Actual-board fit:** `evt1-integration/` has editable assembly CAD, four STEP
  parts, two plastic dry-fit STLs and a separate board-fit/PCB-quote ZIP. Actual
  board/component/mate envelopes, integral two-boss compass mount, sleeve/foam
  and nominal loading poses pass. No physical/tolerance/loom result follows.
- **Overmold direction:** lower metal body installed/nut set,
  two rigid flange halves closed, then one continuous silicone overmold. The
  rear plastic cover lies beneath the skin; no separate overmolded service lid.
  Cap-last wiring remains open; current cap tails connect while the flange
  is open. EVT workshop battery service consumes/remakes the skin before
  opening both rigid halves; practice removal on an inert assembly. No battery
  path through the Ø12 neck or exposed rear service lid is added. Molding trials start with dummy closed assemblies and cure/pressure/
  material tests. See `hardware/cad/manufacturing-layout/concepts/overmold-cradle/`.
- **Inert casting kit:** `hardware/cad/manufacturing-layout/overmold-trial/` has
  separate native continuous-skin/split-tool CAD, STEP and three print STLs.
  A solid closed-assembly dummy tests external fill/demold only; no actual
  cavity/contact/button seals or internals. 90×38 skin, 1 mm nominal end
  coverage, ~24.2 mL fill; four valid solids, STEP/mesh checks and 22 sampled
  opening poses pass. No slicing, print, casting or process/material result.
- **Cradle requirement:** ship a smart USB cradle with four
  exposed conductive magnetic-interface contacts through the silicone: 5V, GND,
  D+ and D-. Routine charging/programming/data use the cradle. The original
  manufacturing native retains two-target references; the dock and actual-board
  natives use four. Native USB, RTC wake and external Power/Mode reset/ROM recovery
  have circuit/code; physical enumeration/flashing/timing remain to verify.
- **Separate dock/interface CAD:** `hardware/cad/manufacturing-layout/charging-dock/`
  has `ChargingDock.FCStd`, STEP and print STLs: revised rear half, fixed spool
  targets/M2 nuts, skin, retractable face mask, clamshell/nest/pin head and inert
  whole-device gauge. GND/D−/D+/5V follow increasing X at Z11.5. Dock-only
  magnets face buried steel keepers. Rigid target-face stops set nominal0.6mm
  stroke; lower at+3mm axial offset then slide to mate. First lid is opaque
  with a screw latch. The printed pin-board blank is a gauge; actual1mm FR4 pin
  and USB boards are routed and drive CAD datums/mounts. No power/USB/seal/material/holding or
  physical result. The earlier product and inert-trial natives are unchanged.
- **Inner contact-seal trial:** the dock/product natives now include metal
  face glands and nominal2×0.5mm ring envelopes under the contact heads.
  Contact pitch/face/stop datums stay fixed. A separate two-print hydrostatic
  fixture, actual-post STEP, inert316L RFQ and build/test sheet live under
  `charging-dock/contact-seal-trial/`. Saved geometry/exports pass; no physical
  leak, finish, ring/casting compatibility or complete cavity/button result.
- **Cradle target:** Pocket Neopet-style clamshell with keyed four-contact
  nest, required working exterior screen/three buttons and enclosed UV-C LEDs.
  Current authoring is `hardware/cad/evt1-assembly/`; see `hardware.md` for the
  selected circuit/CAD sources and outstanding integration. Computer USB goes
  to the plug for programming/data; local case/plug communication is also
  required as described above. Its topology is not implemented by paralleling
  a controller on that pair. No physical fit, dose or sterilization result is
  claimed; the concept art remains illustrative.
- **Compass candidate:** LSM303AGR circuit/driver, tilt-compensated heading math
  and NVS calibration upload exist. The molded flange arrow identifies the tailbone/back.
  Flange fit is the accepted installation reference; no wearer pose calibration
  is planned. The arrow resolves the possible front/back reversal.
  Integral tray bosses register the board; factory package-axis/calibration
  workflow, compass-driven haptics and assembled magnetic testing remain open.
- Exact PCB parts/positions and five assembly quote ZIPs are prepared:
  114 purchased positions/53 order lines. BC-PACK-EVT1-001 is a defined1.5A
  protected-pack RFQ for the two-board design (the one-board uses the 3-wire
  BC-PACK-EVT1-002 in `hardware/pcb/evt1/one-board/PACK-RFQ.md`); requested pack/two dry NTC/growth geometry fits, but supplier
  acceptance and retention remain pending.
- Finished materials, full boot/seals, actual loom and
  motor fit remain open. The human-owned BOM stays header-only.

## What is included

Current mechanical native/STEP/STL files and review figures; the verified P1
native/review used as builder input; R35F native schematics/boards and their
custom library dependencies; bench firmware; cable recipes; development tools;
and current/archived documentation. The prior stock KM3/MB3 packaging screen
and its source are preserved under the CAD folder's `archive/ring-lock-screen/`;
its ring-joint native is recoverable from Git. The older manufacturing native
in that archive is also superseded.

Local intermediate CAD/PCB iterations, rendering caches, withdrawn P1 print-kit
exports, downloaded reference PDFs and generated cable outputs are not part of
this focused checkpoint. Historical docs/scripts may refer to those local-only
artifacts; use the current paths above for an editable starting point.

## Checks and rebuilding

- Developer site: `mkdocs build --strict -f developer-docs/mkdocs.yml`
  after installing `developer-docs/requirements.txt`.
- Firmware host tests: `sh firmware/tests/run_host_tests.sh`. No flashing.
- BOM: `python3 .github/workflows/scripts/bom_lint.py`.
- Mechanical builder: run `tools/build_manufacturing_layout.py` with FreeCAD's
  Python, the included P1 native as argument1 and a scratch output folder as
  argument2. Then run `tools/verify_manufacturing_layout.py OUTPUT` with that
  runtime. Configure visibility with `tools/configure_manufacturing_view.py`.
  Renderers require NumPy/Pillow, plus PyMuPDF for the section sheet. Scripts
  currently assume the macOS FreeCAD library path; other hosts need that path
  adapted. The advanced verifier also needs PythonOCC in the FreeCAD runtime.

Native hashes and scoped checks are in `review.json`. A fresh rebuild produces
new file hashes; do not overwrite original provenance to imply a new physical
result. KiCad footprint tables resolve repository-local libraries; standard
3D models still require an installed KiCad library/model path.

License selection remains pending. This branch is shared development progress;
no product release or external documentation-site publication is implied.
