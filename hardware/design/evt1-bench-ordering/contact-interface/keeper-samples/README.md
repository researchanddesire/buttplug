# Steel keeper samples for the four-contact dock

Quote **six identical Ø8 × 1 mm solid SAE 1018 low-carbon steel discs**,
using [the STEP exported from the device native](SteelKeeper-8x1.step).
Use two for the first contact article, two for a second set or spares and
two for material and force witnesses. The same part fits both pockets.
SAE 1018 is the proposed grade for these dry, unpowered bench samples.
[1018 stock reference](https://www.niagaralasalle.com/steel-grades/grade-1018)

| Quote detail | Proposed first-article request |
| --- | --- |
| Material | SAE 1018 cold-finished round stock with supplier grade and lot traceability. Quote a clean, bare sample with no adhesive or intentional magnetization. |
| Finished diameter and thickness | Ø8.00 ±0.05 mm and 1.00 ±0.05 mm over any finish. Supply measured dimensions by part or by sampled lot. |
| Faces and edges | Deburr both edges, with an edge break no larger than 0.10 mm. Keep both faces flat and parallel within 0.05 mm. Remove burrs, rust, particles and free oil before fitting. |
| Process | Quote faced and parted blanks with any required finishing. Return attainable size, edge, flatness and lead time before fabricating. |

The tolerances are a starting quote request. The CAD pocket is nominal
Ø8.20 mm × 1.10 mm, giving 0.075 mm nominal radial margin and 0.05 mm
nominal axial margin with the largest quoted disc. Its cold check also
shows 0.298 mm clearance to the PCB. Confirm pocket fit on
the actual printed cover and account for any retention material. The
physical retention method and dry-cavity inspection remain trial work.

The Magnet Baron lists a 50-piece pack of nominal Ø8 × 1 mm Q235 steel
discs with Ni/Cu/Ni finish. Use a received pack as a separate comparison
lot if available and if measured dimensions fit the pocket. Keep its
material and finish identified in the force records. Exact thickness and
coating tolerances are unpublished. [Commercial comparison pack](https://themagnetbaron.com/products/metal-discs-50pcs-8mm-x-1mm-approximately-5-16-x-1-32)

## Receiving and bench setup

The [native geometry report](keeper-review.json) compares both keeper
solids with the neutral supplier STEP and checks the drilled rear cover.
The two discs share the original shape and sit in the flange at
X/Z (−14.5, −8.0) and (+3.0, −10.5), with the pocket floor at Y−28.30 mm.
They bear on the saved cover without volume overlap. The closest saved
skin is 0.40 mm away through the rigid cover. The seated Rev051 frame aligns
both magnets and discs with a nominal **2.70 mm face-to-face gap**.

1. Measure disc OD, thickness and rocking on a flat reference. Check the
   pocket bores and usable depth in the received drilled cover. Seat each
   disc against the pocket floor on an inert article and confirm it cannot
   shift into the board cavity during handling. Check both rigid halves
   close. Record whether any retention material changes the axial stack.
2. Mount the existing **S-08-03-N** magnet and keeper in a nonmagnetic
   force fixture. Measure each pair's axial pull at 2.70 mm and at the
   smallest and largest gaps found on the received stack. Record whether
   the measured gap includes both housing walls and the skin. Use the
   catalog's force only as part identification. The small steel disc and
   millimeter-scale air gap change the result. [Magnet specification](https://www.supermagnete.de/eng/data_sheet_S-08-03-N.pdf)
3. Measure the complete mated contact stack with both magnet assemblies and
   then each side independently. Record seated pose and travel of all four
   pins, separation force along the normal slide path, and continuity
   during a light disturbance of the seated assembly. A comparison with the
   magnets removed gives the actual four-pogo spring reaction. The separate
   Lee springs seat the magnets in the carrier. Their catalog preload is a
   carrier load, so measure rather than subtract it from pull-off force.
   [Contact module procedure](../README.md) · [Mill-Max force and travel data](https://www.mill-max.com/sites/default/files/external/catalog/2021-02/023-028.pdf)
4. Keep the same pair identification for later compass testing. Measure
   undocked readings before docking and after repeated docking, comparing
   with the two keepers removed in a fixture. Record magnet orientation,
   movement, remanence symptoms and any corrosion before selecting a
   production material or finish.

Run `python check_keepers.py` in a PythonOCC environment to regenerate the
STEP and geometry report. This quote adds no changes to the cover, skin,
keeper location or dock. Physical holding force, positive retention and
compass performance remain open.
