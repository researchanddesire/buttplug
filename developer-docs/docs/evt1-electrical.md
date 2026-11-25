# Compass calibration

LSM303AGR accelerometer and magnetometer axes must both register to the saved
flange arrow: **device −X, toward the button end**. Cap clocking is not the
heading reference. The [device overview](device.md) defines the
mechanical assembly; [electronics](electronics.md) defines the board.

## Factory compass calibration

Collect magnetic data away from the dock and use an independent orientation
fixture/reference. Fit the package transforms and assembled magnetic correction,
then upload the calibration over the engineering USB console.

`compass-cal JSON` accepts version 1 with:

| Field | Shape / meaning |
| --- | --- |
| `accel_to_flange` | 9 values; accelerometer-to-flange transform |
| `mag_to_flange` | 9 values; magnetometer-to-flange transform |
| `mag_offset_ut` | 3 values; magnetic offset in µT |
| `arrow` | 3 values; heading reference in the flange frame |

The command validates and stores one NVS blob. `compass-clear` removes it.
Verify the fitted result over yaw/tilt, motor and dock states. No wearer pose
calibration is introduced.

Firmware gates heading for invalid calibration, docking, motor/settling and
several age/range/tilt faults. Physical axes, magnetic range, settling and
accuracy still need measurement; [Project status](status.md) tracks that acceptance.
