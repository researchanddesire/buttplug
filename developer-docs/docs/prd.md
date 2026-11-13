# Product requirements

Current requirements, 12 November 2026. Lucy's latest instructions supersede
older specifications and archived design studies.

## Features

| ID | Requirement | Current design / acceptance still needed |
| --- | --- | --- |
| PRD-01 | WiFi | ESP32-C3; bench interface implemented, radio behavior untested. |
| PRD-02 | Bluetooth | Bluetooth LE interface implemented; pairing/range untested. |
| PRD-03 | On/off control | Press through silicone at flange. Current circuit uses momentary input/software off; no hard battery disconnect is selected. |
| PRD-04 | Mode control | Second silicone-covered switch; working press/return and final product modes need validation. |
| PRD-05 | Two-pin vibration motor connection | NFP-E1015 candidate; confirm actual capsule, lead exits, polarity and limits. |
| PRD-06 | PWM motor control | Separate motor rail/driver; startup, running and stall behavior need bench measurement. |
| PRD-07 | Lithium battery charging | Single-cell charger/power path; verify charge limits, input path and faults. |
| PRD-08 | Lithium battery discharge protection | Require a suitable protected pack; charger alone is not discharge protection. |
| PRD-09 | Internal battery connection | Protected pack; battery choice OPEN. Reconcile the prior removability goal with continuous flange overmolding: the current pack gauge cannot pass the Ø12 neck, and no post-mold service route is established. |
| PRD-10 | Wired tip temperature sensor | Two-wire thermistor potted in the dome cap. ADS1115 circuit/routed board and matching firmware exist; calibration, actual wiring and motor-heat bias tests remain. |
| PRD-11 | Accelerometer | LSM303AGR supplies motion telemetry/compass tilt compensation. Board mounts directly to flange bosses; factory package axes and physical checks remain. MC3635 is the prior reference. |
| PRD-12 | Four-contact magnetic charging/data interface | Four conductive contacts through sealed silicone feedthroughs. Separate CAD proposes fixed spool targets in GND/D−/D+/5V order along the flange edge, moving dock pins, rigid target-face stops and dock-only magnets/buried steel keepers. Finish, seals, holding and PCB integration pending. |
| PRD-13 | Pelvis, coccyx and perineal clearance | Assess standing, seated and moving geometry; no anatomical fit is validated. |
| PRD-14 | Smooth, low-profile contoured flange | Follow the anatomy; do not widen it to preserve an inconvenient board layout. |
| PRD-15 | Effective flared stop and accessible removal grip | Preserve retention and access under deformation; physical loads remain to define/test. |
| PRD-16 | Adjustable body/base alignment during design | Angle/offset are study parameters, not a required user adjustment mechanism. |
| PRD-17 | Thermal review of every contact region | Measure motor, battery and electronics hot spots separately from tip sensing. |
| PRD-18 | Finished contact-material review | Evaluate alloy, polymer, silicone/cure, finish, seams, cleaning and lubricant compatibility. |
| PRD-19 | Magnetometer / compass mode | LSM303AGR circuit/routed board, driver, heading math and calibration upload exist. Fixed mechanical registration is modeled; factory package axes/calibration, measured accuracy and haptic mode remain open. |
| PRD-20 | Flange installation reference | Rely on flange fit to constrain installation to one or two adequately aligned orientations. Molded tactile/visual arrow points toward the tailbone/back and resolves front/back reversal. Use a known sensor-to-flange transform; no wearer-specific pose calibration is required. |
| PRD-21 | Included smart USB cradle with working screen and three buttons | Follow the orange/cream/dark Pocket Neopet concept, including a tactile latch and blue controls. Existing USB/pin PCBs are a prior functional baseline; the display/controller circuit, firmware and integrated native assembly must be completed and tested. |
| PRD-22 | Continuous flange overmold | Secure lower metal body, close both plastic flange halves, then overmold one continuous silicone skin/root. Contact masks, button barriers, mold/fill/cure, component exposure, bonds and cap-last wiring remain to design. |
| PRD-23 | Working enclosed UV-C cleaning LEDs | Required in this EVT. Include independent hardware lid/thermal cutoff, fault shutdown/restart control and qualified source-power budgeting. Dose, coverage, efficacy, leakage and repeated material exposure require measurement; no sterilization claim. |
| PRD-24 | Editable FreeCAD multi-body assemblies | Component bodies and linked PCB models through KiCad StepUp; use models of selected parts rather than bounding-box proxies. STL is a derived print export. Use the existing Linux VM if native FreeCAD is unstable. |
| PRD-25 | Manufacturing process | Plastics target MJF or SLA, with vendor material/process/tolerance selection. Metal parts may use multiaxis CNC-lathe operations or casting plus finishing; do not constrain the design to FDM or simple two-axis turning. |
| PRD-26 | Case data link and temperature history | Preserve general bidirectional computer ↔ case ↔ plug USB communication through the four contacts for firmware updates/ROM recovery, configuration, diagnostics, logs/telemetry and future commands; also provide local case-controller/plug communication. Record tip temperature while docked and a timestamped, validity-tagged removal baseline, including early removal. Local case telemetry, charge-status sensing and history remain to implement. |
| PRD-27 | Charge completion and thermal readiness | Show Charging → Charged — cooling → Ready using confirmed charge state and qualified thermal criteria; include UV heat and loss/staleness of measurements. Numerical limits/dwell remain to qualify. Evaluate passive cooling and a small fan; no fan is selected or budgeted. See the [thermal study](thermal-presence-study.md#charging-case-baseline-and-cooldown). |

Flange fit and the arrow establish the assumed body reference. Gravity comes from
the accelerometer and changes relative to the flange with posture. Device magnetic
calibration is separate. See [compass architecture](architecture.md#compass-mode).

## Packaging decisions

- Two CNC-turned metal pieces: a hollow polished body and threaded nose cap;
  electronics load from the nose. No longitudinal clamshell seam.
- Fuller rounded nose, without the inward scoop; **15 mm neck**.
- Motor pressed/retained directly in the nose-cap pocket; a metal shoulder carries its load independently of the thermistor and PCB. Actual fit remains to select.
- Separate body and flange PCBs with flexible wiring. Semi-flex is allowed;
  rotating the flange PCB 90° is allowed if it keeps the flange narrow.
- The cap owns the motor, offset potted thermistor and foam-supported body PCB. Thread this prewired module with its flange tails disconnected; connect them last.
- Short threaded rear stub and thin nut clamp the flange tray against the metal
  shoulder; opposing collar flats resist twisting. Nut locking remains open,
  with no separate compression limiter. A continuous silicone overmold covers
  both closed flange halves and bonds at the metal root; cover screws close
  plastic only and lie beneath the skin. Cap-after-mold timing needs a wiring solution.
- Whole polymer/silicone flange provides the nonmetal antenna region. Metal is
  intended to improve temperature sensing and cleaning, with no active heating.
- Use four main rigid mechanical pieces, a continuous silicone overmold and standard insulation/foam; avoid the former internal scaffold. Prefer ordinary fasteners and accessible wiring during assembly.
  R38 joint combs/return plugs and R39 connector cages are not selected.
- Use multiaxis CNC turning/milling or casting plus finish machining for the metal; keep stock, tooling, fits and finishing open to supplier feedback. One offset cap sensor drill is explicit.

Flange packaging target remains90 ×38 mm; the current tray is88 ×32 mm and
an inert 90×38 skin/tool trial exists; final contact/button seals and process
remain unfinished. Maximum body/cap diameter is aboutØ37.3 mm.
These are study dimensions, not a comfort result.
The screenshot's old ≤25 mm PCB note is not a fixed envelope for this architecture.

## Endurance and wear goals

Target **24 hours of battery life with light motor use**. Define motor/PWM,
radio duty cycle, sensor sampling and usable capacity, then measure that profile.
The displayed 350 mAh /33 ×8 ×20 mm pack reference is not a selected battery.

Long-duration wear and sleep use are design aspirations. No wear duration,
break schedule, anatomical fit, removal performance or clinical/material
acceptance has been established. Electrical endurance does not establish safe
continuous wear. Finished materials, contact conditions and the evaluation plan
need qualified review before a human evaluation.

## Motor reference

Lucy supplied the [NFP-E1015 listing](https://nfpshop.com/product/nfp-e1015-encapsulated-vibration-motor-with-metal-cover-7g-vibration-force).
It is a candidate, not a confirmed received part. Resolve the earlier “N20
bullet” description and verify voltage, startup/stall current, dimensions and
wire exits before finalizing the driver/pack and mechanical fits.
