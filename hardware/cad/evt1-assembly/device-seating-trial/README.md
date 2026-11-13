# Device seating coupon

This is an editable FreeCAD candidate for supporting the actual device at its existing dock pose. It is an **inert mechanical trial**, with no print, received-material, force, powered or UV-cleaning result. The master assembly, electrical sources and BOM are unchanged.

Open `DeviceSeatingTrial.FCStd`. It contains the printable floor/support coupon, eight formed sheet/shim bodies and nine relative links to the actual selected exterior device components, including both steel keepers. STEP files preserve installed geometry. `SeatLinerCoupon.stl` is a derived print export. The coupon is a real bench receiver; it does not substitute for a selected purchased part.

## Correct source frame

The immutable host is `../DockAssembly.FCStd`, SHA `688c072ac989355187df894464c211c0e026bd0f2808f03d6ede89bcbbc055cd`. Its source is `../sources/ReadableEVT1Product.FCStd`, SHA `63da08fb57ef4bd5c0af9bbb872e5ec13d2163aa234433ed3da78c525ebb3833`. Device placement stays `(0,50,32)`, target faces Y23.2 and target centres Z43.5. The actual exterior silicone underside is **Z13.000**, already touching the old floor; Z16.206 is an inner skin intersection, not the support surface. The metal body's outer maximum-radius section is R18.6690854 about Z32, with bottom Z13.3309146. Cold host-link/source-pose parity is checked explicitly.

## Supports and retention

Three 6×4 mm sheet faces at `(−28,30)`, `(28,30)` and `(0,40)` support the flange. The liner has a rounded 92×28.5 mm relief, X±46/Y23..51.5, down to Z12.6. Three small lands finish at Z12.65. The default measured installed stack is two 0.0508 mm PET layers plus 0.2484 mm silicone: each face finishes at **Z13.000**. This is geometry, not a prediction that a nominal0.254 mm silicone sheet compresses0.0056 mm under the device.

A 7×4 mm body band lies at Y104.5..108.5. Its liner saddle uses the actual maximum rotational body radius plus the selected radial sheet/shim stack, so the constant-radius envelope clears the sampled +3 mm slide. The default central rigid face is Z12.9809146, covered by0.1016 mm PET plus0.2484 mm silicone. The shallow local relief finishes at Z12.5; the original Z11 liner bottom leaves **1.5 mm nominal minimum floor**. The broader flange relief leaves1.6 mm. Adjacent unchanged liner regions are included in the native check.

Every soft piece has an integral tail. Three flange catches are at X−28/0/+28,Y54, outside the full +3Y skin envelope. The body strap ends are captured at X±24,Y106.5, outside the metal body. Integral mushroom stems are Ø2 and heads Ø3.4, underhead Z13.9/top14.5. Silicone uses closed Ø2.2 holes; fitting over the larger head is an explicit elastic assembly trial. PET registration holes have an assembly slit, so PET is not assumed to stretch55%. The closed-hole silicone cover retains the slit PET layers; the PET alone has no independent retention credit. There is no adhesive or new purchased fastener. The tail ramp reaches its upper floor level before Y51.4, inside the relief edge, preventing hidden floor interference.

## Selected materials and cut parts

- **Rogers BISCO HT-6240**, transparent solid silicone, plain/nonadhesive0.010in. Primary [datasheet](https://rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/bisco/english/data-sheets/180-093-bisco-ht-6240-transparent-solid-silicone-data-sheet.pdf) specifies0.254±0.051 mm and40±5 ShoreA. [Manufacturer availability](https://www.rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/bisco/english/product-availability/180-464-bisco-silicones-general-industrial-product-availability.pdf) lists the0.010in transparent sheet. This is a precise material/thickness definition for converter-cut parts, not an invented distributor MPN; quote/stock/received identity remain unverified. Remove shipping PET liners and let the silicone shrink/relax **before cutting**, per the datasheet. Those shipping liners are not retained as product layers.
- **CS Hyde48-2F-1-100**, plain Mylar TypeA PET,0.002in/0.0508 mm,1in×100ft roll. [Primary catalog](https://cshyde.com/viewitems/films/mylar-polyester-pet-film). Measure actual layer thickness; no tolerance is invented. Default: two registered layers at each of four support sites, eight cuts total.
- Printed liner/coupon: MJFPA12 or toughSLA, with received fit, creep, catch strength and cleaner compatibility still unqualified. No FDM assumptions.

The solid sheet was selected for a smooth removable interface instead of porous padding. This does not establish a cleaning protocol. Manufacturer generic UV/fluid resistance is **not a275nm lifetime, transmission, cleaning-agent or device-skin compatibility guarantee**. All sheet/support regions are treated as blocking UV.

`cut-patterns-1to1.svg` contains starting die-cut profiles with a10 mm scale check. Small developed-length corrections for the formed tails are explicit in `cut-patterns.json`; trim/received forming still require a coupon. Do not stretch PET to make misaligned holes fit.

## Integration API

Import `tools/build_evt1_dock_device_seats.py` in FreeCAD, then:

```python
seats = build_components(D)  # parts + fixed_features + received_stack + shadow_limits
apply_liner_reliefs(liner_body, prefix='DeviceSeat')
apply_liner_saddle(liner_body, loaded_silicone=.2484, pet_stack=.1016,
                   prefix='DeviceSeat')
```

All geometry is in the closed dock frame with identity placement. Add returned component bodies to the base module. The two liner helpers mutate only the supplied Body, using fully constrained native sketches, pockets and pads; they do not save the document. The saddle is a native XZ circular-arc profile extruded4 mm along+Y. Do not feed it through a Z-only extrusion converter. Call the helpers once, after existing liner cuts. The reference coupon demonstrates the same calls. Its overall rectangular/skeletal bench outline is not an integration cut.

`build_components` accepts measured loaded sheet thicknesses and0..4 shim layers. `apply_liner_saddle` must use the same body stack. At received conditions select shims against the **actual measured gap**, not nominal sheet thickness. If the permitted stack cannot achieve the fixed device/contact pose, rework/reprint the seat and rerun the native checks; do not lift the device to compensate. The source hashes intentionally fail on changed device geometry.

## Bench trial and acceptance record

1. Print the coupon in the intended liner process. Measure its bottom datum, relief floors, land heights, saddle contour and catches. Reject cracks, thin sections below the stated floor target, warped lands or catches that require force likely to tear the pad. Record received dimensions.
2. Verify material identity, remove silicone carrier liners, relax and measure sheet thickness at low force. Record the measurement force and temperature. Measure the PET layers independently. Cut the supplied starting profiles, assemble slit PET layers under the catch heads, then fit the closed-hole silicone over them. Reject tears, permanent set, wrinkled foil or a strap that needs PET stretching. The assembly has no validated minimum bend radius or tear force.
3. Use an unpowered mechanical exterior or a geometry-identical inert assembly with representative measured mass/centre of gravity. Keep batteries/electronics out of the first trial. Lower at+3Y, then slide toward the existing target stops. Measure target centre height against the coupon's Z11 bottom datum (nominal32.5 mm above the bench). The engineering trial target is Z43.5±0.05 mm in dock coordinates, with no rocking; this is not a released product tolerance.
4. Measure each support gap under representative weight. Adjust registered PET layers and repeat. A0.0508 mm layer gives at most0.0254 mm nearest-step quantization error before print/skin variation. No spring constant or silicone modulus is assumed. Set the body saddle as a light supporting contact; do not jack the flange away from its contact datum. Rework/reprint if the0..4 layer range cannot meet the pose.
5. Repeat the49 sampled device poses and the complete continuous lowering/±3 mm slide by hand. Check the outboard body-band edges, skin, keepers and contact-carrier clearances. Engineering coupon target: seat-only slide drag≤1 N, with no snagging or upward tilt; measure before adding magnetic/pogo forces. Record forces rather than infer friction. Actual docking force is a separate integrated test.
6. Exercise500 seat-only slide cycles, then apply0.5 N for10s to each tail in the slide direction as a prototype retention test. Reject migration, an escaping PET layer, tears, catch damage or a target-height change beyond the trial limit. These are chosen test targets, not supplier strength guarantees. Physical catch fitting/peel is required; native rigid BOP is not evidence of elastic assembly.
7. Trial the intended wipe agent and thermal/UV-C exposure on separate received coupons, recording actual time, temperature and fluence. Recheck tack, cracking, shrinkage, wear, residue transfer, tail retention and loaded height. No275nm life or permissible exposure dose has been established.

## UV limits and digital checks

The three flange faces cover up to72 mm², and the body band has a28 mm² contact envelope: **100 mm² maximum direct-contact envelope** before tails/catches and oblique ray shadows. Actual conforming contact is unmeasured. Transparent appearance gives no UV transmission credit. Supported contact patches and surrounding shadows are excluded from any closed-dock cleaning claim; remove the device and clean those surfaces separately. This trial establishes no dose, efficacy, sterilization or complete UV containment.

`check_native.py` cold-opens the saved coupon and frozen actual source; it checks valid solids, fully constrained profiles, contact-frame and host-link parity, static intersections, the49 prescribed lowering/mating poses, and retained-sheet loading samples. Head-passage samples explicitly require material flex; they are not waived as rigid clearances. The report distinguishes source-bound nominal CAD checks from physical fit. Final whole-dock integration and received tolerance remain separate checks.

Final local readback passes:9 valid native component bodies,6 fully constrained profiles,9 actual device links,7 cold host/source-pose conservation checks,44 static pair checks,49 device poses,48 sheet-loading samples and5 received-sheet stack calculations. `check_catch_loading.py` additionally bounds all48 assembly intersections to the five actual catch-head regions; every other rigid intersection is zero. The tail/head flex remains physically untested.

To regenerate in the FreeCAD Python environment, run the builder, `check_native.py`, `check_catch_loading.py`, `export_cut_patterns.py`, then `render_native_sections.py` with `QT_QPA_PLATFORM=offscreen`. The final renderer cold-reads checked native geometry and records separate source/hash bindings. `artifact-bindings.json` binds the delivered outputs; refresh it only after rerunning changed checks/exports.
