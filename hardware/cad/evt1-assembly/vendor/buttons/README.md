# Selected dock tactile switches

Three **B3FS-1002P** SMD switches, Omron electronic components family (current supplier branding: Aratas). Nominal force 1.47 N, minimum return force 0.49 N and nominal pretravel 0.25 mm. This is the 3.1 mm flat ivory-plunger version; the three external blue caps are custom dock parts.

The native builder `tools/build_evt1_dock_buttons.py` returns an `App::Part` containing the actual selected-family KiCad source geometry in a native PartDesign body, plus a fully constrained actuator-face datum. Its 165 faces retain four gull-wing leads, stepped housing, retaining lid and Ø3 plunger. It is **KiCad-authored CAD**, checked against the manufacturer's outline, rather than OEM CAD or a bounding-box substitute. License and source attribution accompany it.

Local origin: switch centre on the PCB seating plane, +Z toward the user's finger. Nominal source bounds X=−4..4, Y=−3.15..3.15, Z=0..3.1 mm. The released actuator face is Z=3.1; nominal contact operation occurs after 0.25 mm depression, at Z=2.85.

The manufacturer specifies pretravel of 0.15–0.45 mm. **Pretravel does not specify allowable total compression or overtravel.** The legacy manufacturer drawing explicitly gives free height 3.1±0.2 mm, yielding a 2.45–3.15 mm click-plane range before PCB, solder, cap and printing tolerances. The current 2024 drawing revision/received part height allowance must be confirmed before accepting a fixed stop. Use mounting adjustment and received-part trials to establish cap rest clearance, reliable operation, positive return and a stop that avoids overload; this component model does not qualify them.

These switches are SPST normally open, silver contacts, with a stated minimum applicable-load reference of 10 μA at 1 V. Bounce can reach 5 ms, so the centre switch requires its separate hardware debounce before clocking the UV permission latch. They are IP00 and cannot be washed; keep them in the dry electronics compartment behind the UV barrier.

Sources: [manufacturer datasheet](https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3fs.pdf), [current product page](https://components.omron.com/us-en/products/switches/B3FS), and the [official KiCad 3D library file](https://gitlab.com/kicad/libraries/kicad-packages3D/-/blob/master/Button_Switch_SMD.3dshapes/SW_SPST_Omron_B3FS-100xP.step). Details and hashes are in `source-manifest.json`. No manufacturer PDF/drawing is republished.
