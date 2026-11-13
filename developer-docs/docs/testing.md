# Validation

Current work is a two-piece CNC metal / flange-joint study, not a build release.
The old P1 scaffold fit-kit recommendation remains withdrawn.

## Evidence and limits

| Area | Evidence / remaining work |
| --- | --- |
| Geometry | Four main native solids plus a generic thin nut, STEP readbacks and closed plastic STLs. `review.json` records hashes, no hard-part overlaps, and unchanged neck/front/cap geometry against the ring-joint baseline. |
| Machining | Turned body plus two indexed collar flats; accessible cap bores and one offset sensor drill. CAD thread envelopes require callouts and supplier review. |
| Rear joint | M18×1 stub, keyed collar, thin nut and boot cuff section modeled. Nut lock, thread strength, clamp preload/creep, key bearing and pull-through are unqualified. |
| Motion | Finite cap-module, nut-loading, key-blocking and axial-driver samples are screens only. No full thread helix, flexible loom or physical hands/tool trial. |
| Tray/cover | Open drafted geometry and flat print poses; no slicer/physical print or molding approval. |
| Silicone overmold | Separate inert casting-trial native: continuous skin, two split tools and a solid closed-assembly dummy. Four valid solids, STEP readbacks, closed print meshes, connected skin/gate/vents and 22 sampled release poses pass. Minimum nominal end skin 1 mm; fill network 24.18 mL. No slicer/print/cast result. Real cavity sealing, contact/button tooling, cure/pressure/component exposure and bonds are untested; cap-last wiring unresolved; workshop service consumes/remakes the skin and needs an inert trial. |
| Electronics | EVT1 system/body ERC, all five PCB DRC checks and independent functional pin/pad contracts pass. `native-checks.json` binds reports/netlists to saved sources. Exact parts cover114 purchased positions/53 order lines; independent native/order and80 passive-MPN checks pass. Assembly quote ZIPs contain exact parts/native positions/fabrication. Stock, supplier acceptance, biased capacitance and powered behavior remain to qualify. |
| Device assembly | `evt1-integration/review.json`: 8,256 nominal hard-part pairs clear; selected maximum XY/component/mate/sleeve/foam and sensor-screw envelopes clear. 25 flange loading,25 sensor loading,29 requested-pack/NTC loading and108 cap-module poses pass. R39/seat clearance0.250mm; C83/requested-pack1.95mm. Requested growth space also clears hard parts. Two bed-oriented plastic STLs/four STEP readbacks pass. No tolerance, actual flexible wiring, supplied pack, thread/torque or physical result. |
| Battery | BC-PACK-EVT1-001 RFQ requests1.5A continuous/2A100ms,33×21×6.3mm maximum with28AWG/JST ACH power disconnect. CAD includes two dry NTC envelopes, a mated connector allowance and1.1mm extra thickness/0.25mm lateral growth space. Supplier/PCM approval, actual retention/lead routing and load/thermal tests remain pending. Published1A A25357 is a construction reference. Workshop service consumes/remakes the skin; no neck-extraction path or rear lid. |
| Interboard loom | Actual neck-facing J7 PCB passes native DRC/pad parity. Ten saved wire forms pass native BOP/closed-mesh/volume,1450 static part pairs and45 mutual pairs. Sampled minimum radius4.306mm; minimum wire gap0.047mm; nominal free paths62.865–63.788mm. Keep120mm starting blanks. Egress/crimps, forming/restraint, the other ten neck conductors and physical loading remain open. Wire STEP conversion is withdrawn with failed comparison archived. |
| Compass | The inert skin trial has a raised +X back-arrow proposal; LSM303AGR circuit/driver, NVS calibration and heading math exist. 1,680 host pose/calibration cases pass; physical axes, magnetic calibration and haptics remain unfinished. Flange fit is the assumed installation reference, with no wearer pose calibration planned. |
| Cradle | Separate native four-post/rear-half/skin/mask and clamshell/nest/pin-head prototype. `charging-dock/review.json` records STEP/mesh, static, hard-stop and finite motion checks. Two routed cradle PCBs pass native ERC/DRC and pad/netlist parity. CAD now includes PCB-driven case/mounts and rear wire exit. No physical fit, bond/seal, holding, powered contact/USB or wake/recovery result. |
| Contact inner-seal trial | Separate metal face glands/nominal2×0.5mm rings retain all contact/dock datums. Installed-space volume/gland exclusion checks pass. The six-solid single-contact fixture passes STEP/mesh readback,15static pairs and a clear water path; two print STLs, inert316L post RFQ and hydrostatic procedure are saved. No physical print/leak/cure result or material/torque qualification; button/full-cavity barriers remain open. |
| Clamshell / UV | Mechanical print candidate with opaque lid and prototype screw closure; controls/UV remain proposals. No source-power budget, UV dose/coverage, interlock/leakage, microbial efficacy or material-aging result. |
| Product | No fabrication, powered test, finished-material, leak, cleaning or wear result. |
| Dock thermal readiness | The plug now has host-tested RAM RAM history with actual NTC timestamps, last fresh docked baseline and first valid conversion started after observed source loss. Source loss is not confirmed removal; reset discards history. Local case link, charge sensing, ambient reference, durable logging and Charging / Charged — cooling / Ready UI remain integration work. See the [thermal study](thermal-presence-study.md#charging-case-baseline-and-cooldown). Qualify charge/UV/cooldown, early loss, stale data and warm ambient; fan/vent/power design is unselected. |

## Next checks

1. Machinist review: stock/workholding, straight bore, sensor drill/web/remaining
   wall, thread engagement/runouts, gland corners and polish allowances.
2. Trial the actual thin nut, body finish and printed tray. Qualify thread
   engagement, driver access, tightening torque and the Loctite cure/retention
   process. Measure sensor clearance with the nut at its torqued angle.
   Establish axial/bending/torsion loads; test bearing/creep, key engagement
   after preload loss and nut/pad pull-through independently of nut rotation.
3. Slice/dry-fit the [inert mold kit](hardware.md),
   run material cure/release coupons, then cast and inspect external fill,
   parting seam, root and 1 mm flange ends. This solid dummy cannot prove
   real cavity sealing or internal thermal exposure. Qualify cap/wiring and the skin-consuming workshop service process with the continuously overmolded flange.
   Develop split-tool release, contact/button barriers and fill/vent design.
   Test inhibition, cure/exotherm, pressure, shrink, flash and adhesion on dummy
   closed assemblies before real electronics/battery. Check nose O-ring/closure
   and finished root/contact seals; test cleaning/leaks.
4. Measure motor case/fit/press force and sensor response with motor off/on.
   Check the new metal volume/selected material weight before wear studies.
5. Qualify selected effective decoupling, supplier pack/PCM, retention/loom and factory axes.
   Trial the new integral sensor bosses, blind M1.4 tapping and nonmagnetic screws.
   Preserve existing circuit pin contracts and repeat source-bound native checks
   for those changes; cradle quote files require supplier capability review.
6. Slice and perform a complete unpowered assembly/service trial with the actual
   nut, driver, foam, wiring and pack before functional/endurance testing.
7. Compass: survey magnetic field/range at candidate sensor sites with assembled
   motor, magnets and metal; compare motor off/start/running and docked/undocked
   states. Verify sensor-to-flange axes and retention through cap service, fit
   magnetic calibration across three-dimensional bench orientations, then compare
   heading over yaw/tilt against an independent reference in a clean field.
   Set accuracy/availability limits and verify stale/disturbed/saturated/moving
   cases.
8. Cradle: verify contact alignment/polarization, sealed feedthroughs, protected
   power within the computer's USB budget and USB signal integrity. Exercise
   charging, enumeration, serial transfer and flashing from awake/asleep states,
   disconnect/interrupted-update recovery and hardware motor inhibition.
   Verify the EVT1 application pad gate before NVS/driver setup, 100 ms physical
   power-good qualification, immediate detach handling, brief detach/redock
   during partial or queued commands, and RX-install failure without repeated
   attempts. Run `sh firmware/tests/run_evt_console_tests.sh` for the stubbed
   console/LL/driver boundary; this does not measure interrupt latency or leakage.
   Measure all four contacts through cold boot, EN/watchdog/panic/brownout reset,
   ROM download, awake undocked operation, attach/detach, deep sleep/wake and any
   supported light sleep, including U75 steering toward the supply contact.
   Confirm normal docking restores enumeration/flashing and Mode/Power recovery
   works with GPIO8 high/GPIO9 low at reset. No firmware-only all-state isolation
   or exposed-contact current limit is established by these digital checks.
9. Required dock UV-C: qualify lid-open hardware power cut independent of firmware,
   thermal/current limits and leakage through seams/ports/vents. Map minimum
   dose and microbial reduction including shaded support/contact areas under
   intended cleaning conditions; repeat with aged emitters/materials. No timer
   duration, sterilization or efficacy claim follows from the concept image.

Build the developer site with `mkdocs build --strict -f developer-docs/mkdocs.yml`.
CAD, battery endurance and physical wear acceptance remain separate evidence.
