# Contactless lid cutoff study

Use two Hall channels as the next lid-cutoff candidate. Use the same
left/right front stations as the first placement reference on the
[saved JST lid assembly](README.md), with a sensor fixed to the base and
a mechanically captured, polarized target in the lid at each station.
The mechanical reference stations are X ±50.5 mm, Y 30–37.55 mm, on the
JST review native (`DockAssembly.FCStd`, SHA-256 `45ed53494d0d…`). Those
coordinates locate the initial test region. The compact, same-polarity
latch magnets include a fixed base pair, so screen their background field
with the lid open as well as closed. Include a trial with opposite target
polarities and matching sensor orientations to check response to a common
external field. The D2F-01L travel gauge belongs to the mechanical fallback.

## Hardware behavior

Both stations must sense seated before the existing UV sequence can arm.
Each station controls one of the two hardware paths. Preserve the separate
normally closed thermostats, hardware clear/stop, source qualification,
watchdog and fresh user start action. Opening either lid channel must cut
emitter power in hardware without waiting for a firmware poll. Sensor power
loss or a disconnected harness must remove its enable. A stuck-active output
is a separate fault. The opposite channel must still stop a run when the lid
opens. If a shared magnetic or electrical fault can assert both channels,
revise the architecture or add a diverse cutoff before enabling the emitters.
[Existing independent loops](../../../pcb/evt1/dock-safety/DESIGN.md)

The TI DRV5021 family is a bench candidate for threshold screening. It is
a fast unipolar, active-low open-drain device. Evaluate its full operate
and release thresholds over temperature against the actual magnet and sensor
stack. At each station require the lowest fully seated axial field to exceed
the maximum operate threshold. By the last optically safe opening position,
require the highest axial field to fall below the minimum release threshold
with time reserved for the rail cutoff and emitter tail. Keep the threshold
grade open until field data are available. A
sensor output cannot substitute directly for the present two-wire normally
open dry contact. The powered interface needs default-off translation to
the existing hardware permissives, including unpowered leakage and short-to-
rail tests. Add both sensor supplies, the interface and their fault draw to
the matched wired source budgets before selecting hardware. Test a supply
derived from qualified `LOOP_5V` and verify shutdown on its loss. The current
wired Main has about 15.5 mA of modeled fault-allocation margin at 1.5 A.
Two DRV5021s at the specified 2.8 mA maximum operating current leave about
9.9 mA on that model before pull-ups, gate circuitry and fault cases.
[TI Hall switch datasheet](https://www.ti.com/lit/ds/symlink/drv5021.pdf) ·
[Current wired budget](../../../pcb/evt1/case-telemetry-study/wired-main/circuit-contract.json)

## Test before changing the shell

Use the [bench worksheet](hall-lid-bench-worksheet.md) to record the wired
Main loop pinout, measured field and optical timing for each build.
The [standalone Hall probe](../../../pcb/evt1/dock-safety/hall-field-probe/README.md)
has routed KiCad source, a populated STEP and a six-board quote for screening
all three threshold grades on a separate bench supply.

The [mount envelope screen](hall-probe-mount-screen.json) uses the saved
shell and liner BReps at the existing screw holes, actuator posts and wire
openings. Two stations, three carrier heights and fourteen lid angles give
84 sampled carrier poses. The closed probe board envelope clears the lower
liner by 0.158 mm nominal. Check the received fixture and lead bend at
assembly.

The [editable probe fixture](hall-probe-fixture/CompassHallProbeFixture.FCStd)
adds two support and two target-cup bodies and the populated KiCad STEP.
At the saved middle cup height, the [FreeCAD readback](hall-probe-fixture/editable-report.json)
clears 14 sampled poses per station. The cup holds a replaceable target
insert. Measure the pilot, captured magnet and wire fit on the received
fixture before running the seated-lid field test.

The [close target](hall-probe-fixture/close-target-trial/README.md) puts the
1 mm disc in a dedicated top-loaded bore at the closest setting. The
[matched case-fit quote](../../../design/evt1-bench-ordering/hall-case-fit/README.md)
pairs it with the existing latch and Hall mount geometry for an inert build.
The [driver-free loop adapter](../../../pcb/evt1/dock-safety/hall-loop-bench/README.md)
gives the next electrical test with both UV driver boards physically removed.
It uses a three-level signal to distinguish closure from opens and hard rail
shorts at the receiver. Its series resistor reduces thermostat current for
this test. Use the measured contact loading, faults and cutoff timing to
inform the installed circuit.

The [isolated magnetic screen](hall-target-screen.json) compares the three
target diameters using the nominal hinge motion, disc tolerances and Hall
element depth. Start with the Ø1 × 1 mm S-01-01-N and A3 at the closest
setting, then compare the other grades and targets in the same fixture.
This combination is the only one in the sampled model to both operate
when fully seated and fall below the minimum release field by the 1°
sample. The prior sample at 0.5° still allows late release. Measure actual
gaps and fields with the surrounding magnets, plug and latch in place. Use
the measured optical limit to decide how early release must occur.
[TI Hall element and magnetic limits](https://www.ti.com/lit/ds/symlink/drv5021.pdf) ·
[Target size and magnetic grade](https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-1mm-1mm_S-01-01-N) ·
[Disc field model](https://www.supermagnete.de/eng/faq/How-do-you-calculate-the-magnetic-flux-density)

1. Fixture both sensor/target pairs reversibly on the inert dock. Record
   each channel's operate and release gap at the real lid seam for normal
   opening and corner lift or twist. Keep the emitters disconnected. Include
   target offset and loose/missing/reversed targets, material and finish
   tolerances, and the intended temperature range. Repeat with the plug
   installed and removed, with the latch and contact magnets in place, and
   under foreseeable nearby magnetic interference. Screen the plug's compass
   at the same time.
2. Pick seam locations and set the latest permissible opening gap from the
   containment characterization. With either channel held active, the other
   channel must remove permission in time for the optical output to fall
   below the acceptance limit before the earliest accessible leak position
   on every tested opening path. Check whether corner lift exposes a gap
   while the sensor at the opposite corner still reads closed. Include
   startup, brownout, cable disconnect,
   a stuck-active output, a line short and a held Start after a fault. Verify
   raw loop invalidation and source cutoff with the existing non-emitting
   setup. Record the time from sensor release to actual rail cutoff.
3. Use a qualified optical containment fixture for powered first articles.
   Use a calibrated detector suitable for the selected UV-C LED spectrum
   and the applicable exposure assessment. Measure worst-case closed and
   opening leakage around the seam, hinge, ports and other apertures, plus
   the optical tail after cutoff. Set a repeatable finished-unit acceptance
   procedure and limit from the qualified design, with a detector response
   check and unit traceability. Repeat after enclosure material or process
   changes. Do not use visible-light inspection as the UV-C measurement.
   [IEC UV lamp product optical safety scope](https://webstore.iec.ch/en/publication/59543)

The existing switch stations give a reversible setup reference. Final Hall
positions, exact part grades, magnets, circuitry and installed thresholds
remain to choose from the fixture results.
