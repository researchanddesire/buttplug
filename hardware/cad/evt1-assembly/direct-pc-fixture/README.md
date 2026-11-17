# Direct PC contact fixture

This bench stand accepts the compact first-article plug on its approved four contact targets. It uses a separate copy of the [dock’s 28 × 10 × 1 mm pin PCB](../../../pcb/evt1/pins/assembly-quote/README.md) with four Mill-Max 0906 spring pins and a keyed [direct-PC adapter](../../../pcb/evt1/direct-pc-contact-adapter/) pigtail. The fixture physically occupies the same mating space as the installed dock carrier and liner. Transfer the plug out of the dock before fitting the bench stand. Install only one four-contact pigtail on the bench pin PCB.

| Position | Target and spring pin | J94 | Signal |
| --- | --- | --- | --- |
| X −16 mm | CT1 / P91 | 1 | GND |
| X −10 mm | CT2 / P92 | 2 | USB D− |
| X −4 mm | CT3 / P93 | 3 | USB D+ |
| X +2 mm | CT4 / P94 | 4 | Protected contact 5 V |

All four contact axes are at Z42 mm and seat at Y23.20 mm in dock coordinates, with 6 mm pitch and 0.60 mm nominal travel per pin. The rings have Ø2.4 mm outside and Ø1.8 mm inside diameters. The exact Ø3.175 mm target heads cover the stop rings with 0.3875 mm nominal radial margin. Use the same P91–P94 coil and shoulder geometry as the dock. [Mill-Max 0906 drawing](https://static6.arrow.com/aropdfconversion/adfa1bc04697174a4358693f99b5c90949307da3/0906-2-15-20-75-14-11-0.pdf) · [Mill-Max 1946 drawing](https://www.mill-max.com/sites/default/files/external/catalog/2020-01/202-246_3.pdf)

## Parts and dry fit

- Print the `BenchSaddle.step`, `PogoRetainer.step` and `PreloadBar.step` exports as insulating parts. Generate them from the fixture source as described below. Print the three parts in the same process for the first fit. Inspect the stop planes, board recess, spring-pin bores and all pilots. The Ø2.4/1.8 mm stop rings have a 0.30 mm radial web.
- Trial hardware is two M2 × 6 mm retainer screws, two M3 × 22 mm vertical preload-bar screws, and two M3 × 12 mm or longer flat-tip nylon push screws. Confirm the screw/head clearances, threads and gentle holding force on a printed witness. Cut two 15 × 16 × 0.5 mm flange pads and a 12 × 6 × 0.5 mm bulb rest from nonmetallic protective sheet. The bulb rest has 0.08 mm nominal headroom before load. Retain the printed bar, stock fasteners and pads as separate pieces.
- Have the assembly shop solder four spring pins to the existing pin PCB with their shoulders fully seated. Verify the finished hole diameter, unloaded tip height, pin return and solder fillets. Have the shop hand-solder the short pigtail at J94 and crimp the adapter end. Wire J94.1→J2.1 through J94.4→J2.4, following the pin numbers. Keep D− and D+ paired, mark both ends and take the bundle straight out of the window before making a broad external loop to a separate tie point on the right of the bench fixture and away from the two button approaches. Inspect egress with the retainer installed and relieve load at that anchor. Use Alpha Wire 3048 28 AWG and a JST PHR-4 housing with four SPH-002T-P0.5S terminals. The insulation OD is 1.19 mm nominal. Allow at least 10× the measured OD at each bend and reserve a 12.5 mm centerline radius for the specified maximum. Confirm the crimp and fit on the received loom. [Wire specification](https://www.alphawire.com/products/wire/hook-up-wire/premium/3048) · [JST PH catalog](https://order.jst-mfg.com/InternetShop/app/pdf_show.php?kbn=1&key=ePH.pdf)
- With both 5 V sources physically disconnected, remove the preload bar, lower the plug into the saddle 3 mm toward the tip side of its seated position and slide it 3 mm toward the pin rail. The molded arrow points to the fixture side opposite the anti-flip key. Install the bar only after the slide. Retract both nylon screws for installation, then adjust the two screws evenly to hold the flange on the four metal-face stops. Do not preload by bending the PCB or using the toggle buttons as stops. Loosen and remove the bar, slide 3 mm away from the pins, then lift the plug.
- Use the two short straight rear approaches below the pin rail for Power and Mode during manual ROM entry. Their centers are X −17 and −9 mm at Z32 mm. CAD verifies a clear Ø3 mm straight axial approach at each. The simultaneous two-tool press, force and overtravel need dry fitting.

Measure all four contact travels and stop seating with the unpowered plug. Verify each path from the keyed adapter connector to its target and all six pairwise isolation checks with the adapter unpowered. Verify protected 5 V polarity and voltage at the empty fixture before the digital attach checks. Continue with the direct-PC adapter procedure after the fixture passes. No fixture has been printed or powered.

## Evidence

[Editable FreeCAD assembly](Compass%20EVT1%20-%20Direct%20PC%20Contact%20Fixture.FCStd) · [Nominal fit](fixture-fit.json) · [Cold reopen and STEP comparison](cold-readback.json) · [Compact PCB contact parity](pcb-contact-parity.json) · [Geometry rebuild parity](rebuild-parity.json)

The rigid-source check covers 19 vertical drop samples and 25 axial seating samples, six inverted-roll samples, 13 preload-bar installation samples and both button approaches. The upright saddle overlaps the installed dock carrier by 3315.65 mm³ and the lower liner by 1312.41 mm³ in the common seated plug frame. The dock shell, pin module and compact plug remain unchanged. The print parts retain their native construction history. The builder reads the [active wired dock](../evt1-wired/DockAssembly.FCStd), its [pin board native](../evt1-wired/pcb/PinPCB.FCStd), and the [button witnesses](../../manufacturing-layout/evt1-integration/contact-module-trial/single-board/exterior/ButtonPressKeepouts.FCStd). [CompactFirstArticleMatingReference.FCStd](CompactFirstArticleMatingReference.FCStd) contains seven exact mating solids from an earlier compact first-article CAD snapshot. The original full snapshot lives outside the repo. Its [provenance](compact-reference.json) records the original native and PCB hashes. The [PCB contact check](pcb-contact-parity.json) separately matches those approved CT1–CT4 centers, footprint IDs, pad dimensions and nets to the active compact board. Compare the contact and exterior datums before using the fixture with a later hardware revision.

With a Python environment that can import FreeCAD and MeshPart, run these commands from this directory. Use a disposable output directory and keep the reviewed native at its saved path.

```sh
python build_pc_contact_fixture.py --output /tmp/compass-direct-pc-fixture
python verify_fixture.py --steps /tmp/compass-direct-pc-fixture
python check_pcb_contacts.py
```

Use `render_fixture.py /tmp/compass-direct-pc-fixture` to regenerate the labeled view with `rsvg-convert`. To compare a regenerated native with the reviewed geometry, run `verify_fixture.py --package /tmp/compass-direct-pc-fixture --compare-native 'Compass EVT1 - Direct PC Contact Fixture.FCStd'`.
