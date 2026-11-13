# Selected dock spring contact

`0906-2-15-20-75-14-11-0` is reconstructed from Mill-Max's dimensioned
external drawing using two editable FreeCAD PartDesign bodies. The module is
`tools/build_evt1_dock_pogo.py`; `build(doc, compression_mm=0.6)` returns an
`App::Part`. `validate(part)` checks native bodies and contact/tail datums.
Edit `part.Parameters.Compression` and recompute the document to change its
compression. The parameter object is a sibling outside the component's part,
avoiding a child-to-parent expression cycle; the part's dimensions are
read-only mirrors for inspection.

`Pogo0906-2.FCStd` is a saved native component at 0.6 mm compression.
`native-check.json` binds it to its builder and source manifest. Native
FreeCAD 1.1.4 checks pass at zero, 0.6 mm, midstroke and nominal maximum
stroke, including saved-file reopen at 0.6 mm.
Extents use `optimalBoundingBox(False, False)` so GUI display triangulation
cannot shrink the measured diameter; the same 1e-6 mm checks also pass after
coarse display tessellation.

Local Z=0 is the underside of the seating flange against the PCB. Contact is
toward +Z; the solder tail reaches Z=-1.7526 mm. The free contact is Z=5.0038 mm;
at 0.6 mm compression it is Z=4.4038 mm. Maximum outside diameter is 1.8288 mm.
The barrel has the drawn flange and two diameter steps rather than a single
cylindrical fit envelope. The internal spring is not modeled.

The [Mill-Max catalog](https://www.mill-max.com/sites/default/files/external/catalog/2021-02/023-028.pdf)
printed page 25 and the
[exact-part 2025 data sheet](https://static6.arrow.com/aropdfconversion/adfa1bc04697174a4358693f99b5c90949307da3/0906-2-15-20-75-14-11-0.pdf)
give 0.055 inch maximum stroke and 0.0275 inch midstroke for this part. The
0.039 inch callout belongs to short-stroke 0906-0 and 0906-8. `source.json`
records dimensions, inspected source hash and unmodeled details. The model is
our dimensional reconstruction, not a manufacturer STEP file or physical fit
qualification. Purchased pin, board, carrier and metal-face-stop tolerances
still need an installed compression check.
