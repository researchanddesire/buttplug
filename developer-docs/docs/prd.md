# Product requirements

Requirements for the compact device and wired smart dock. Implementation and
build gaps belong in [Project status](status.md); dimensions and joins are in
[How the device works](device.md).

| ID | Requirement |
| --- | --- |
| PRD-01 | WiFi connectivity |
| PRD-02 | Bluetooth LE connectivity |
| PRD-03 | On/off control through the flange skin |
| PRD-04 | Separate Mode control through the skin |
| PRD-05 | Two-wire vibration motor connection |
| PRD-06 | PWM motor control with bounded operation and fault inhibition |
| PRD-07 | Single-cell charging and hardware pack-temperature cutoff |
| PRD-08 | Factory pack overcharge, overdischarge, overcurrent and short protection |
| PRD-09 | Internal plug-in battery connection and a defined workshop service process |
| PRD-10 | Separate wired tip-temperature sensor in the cap |
| PRD-11 | Accelerometer for motion and tilt compensation |
| PRD-12 | Four-contact magnetic charging/data interface: GND, D−, D+, 5 V |
| PRD-13 | Pelvis, coccyx and perineal clearance during standing, sitting and movement |
| PRD-14 | Smooth, low-profile contoured flange |
| PRD-15 | Effective flared stop and accessible removal grip under deformation |
| PRD-16 | Body/base angle and offset adjustable during design |
| PRD-17 | Thermal review of every contact region and internal heat source |
| PRD-18 | Finished-material, cleaning and lubricant compatibility review |
| PRD-19 | Tilt-compensated compass with assembled magnetic calibration |
| PRD-20 | Known sensor transform to the flange arrow; no wearer-specific pose calibration |
| PRD-21 | Included clamshell dock with working screen and three controls |
| PRD-22 | One continuous skin molded over both closed rigid flange halves/root |
| PRD-23 | Enclosed UV-C LEDs with independent hardware lid/thermal cutoff and measured cleaning performance |
| PRD-24 | Editable FreeCAD component bodies and linked PCB geometry |
| PRD-25 | MJF/SLA plastic candidates; supplier-reviewed metal process and finish |
| PRD-26 | Direct PC recovery plus standalone wired dock telemetry/history; one USB host owns the pair |
| PRD-27 | Confirmed Charging → Charged—cooling → Ready behavior, accounting for UV heat and stale data |

Target endurance is **24 hours with a defined light-motor-use profile**.
Long-duration wear is a design goal, not an established duration or acceptance.
The motor reference is NFP-E1015; the pack request is BC-PACK-EVT1-002.
Final anatomy, material, operating and endurance acceptance remain to establish.
