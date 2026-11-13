# Compliant LCD retention coupon

This is a real printable **bench coupon**, separate from the dock master. It
holds the selected NewhavenNHD-C12864B2Z-RN-FBW using two printed carriers, four
soft face strips, screw-registered PET shims and the existing four inside-access
bezel screws. The native includes the actual six-body LCD/installed-FFC model.
Neither the LCD source nor the master is changed. No adhesive is credited.

The [manufacturer's COG guidance](https://newhavendisplay.com/lcd-displays/cog-lcd-displays/)
calls for even support and keeping pressure off glass edges and the exposed
controller. This candidate therefore uses aligned **front/rear border-face**
strips, without side-edge squeezing. The1.2×22 mm strips occupy|X|22.5–23.7,
Y76–98, outside the44.4×24.4 viewing opening and active area. The exposed lower
glass/COG region and central FFC route have no retainer crossing. There is no
published numeric allowable mounting force here; low nominal force is not
supplier approval or evidence of acceptable glass stress/mura.

## Stack and rigid stops

Keep the screen datum(0,87,68.8),48.6×36.6 glass opening centred(0,83), and existing
view opening. Two roof recesses accept carriers. At each existing screw the
orange bearing remains Z64–66; the carrier ear occupies Z66–67.7; bezel back is
Z67.7. Thus the unchanged NBKSNSS-M2-6 head still bears atZ64 and its shaft ends
atZ70, with nominal2.3 mm engagement in the bezel. The carriers are captured in
that rigid joint. Tightening closes rigid stops rather than continuing to
compress the display. No extra bezel bosses or visible front screws are used.

Carrier rear platforms sit atZ66. Plain PET shim profiles raise the soft-pad
seat for the **received local face depth**. Each shim has a narrow tail and a
rear-screw hole: every layer is retained by the existing screw, with its outer
portion enclosed beneath a1.0 mm carrier channel. The0.7 mm channel roof and
printed joint/thread strength still require received-process/creep trials.

Default0.75 mm foam is given0.5625 mm front clearance. Local pockets raise the
bezel gasket floor from69.1 to69.3625, leaving the view opening unchanged. For
nominal local depth1.8 mm, nine0.0508 mm PET layers give a0.4572 mm stack and
0.5428 mm rear gap:25% front and27.6% rear nominal compression. Equal linear
springs would let the glass settle approximately0.010 mm; that is an analytical
estimate, not a measured preload or installed position.
Those percentages describe the measured supported **total pad stack**. The PET
carrier does not compress like foam; family CFD data cannot convert these
geometric strains directly into actual force. Calibrate the received cuts.

## Selected soft interfaces and adjustment

- **Rogers4790-92-09030-04 P**, product3036884: nominal0.75 mm,9 lb/ft³, PET-supported
  PORON. [Primary product availability](https://www.rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/poron/english/product-availability/17-082-poron-polyurethanes-product-availability-brochure.pdf)
  and [material data](https://www.rogerscorp.com/elastomeric-material-solutions/poron-industrial-polyurethanes/poron-4790-92).
  The retrieved table does not resolve whether0.75 mm includes its2 mil PET
  carrier. **Measure total thickness**; do not add0.0508 mm by inference. The
  family's±10% thickness and typical1.70 kPa CFD at25% are not a part-specific
  force guarantee. The52.8 mm² paired face area gives a reference0.090 N at that
  typical CFD only. Put the supported/PET side against the rigid seat and the
  foam against the received glass face. Mechanically capture the cuts.
- **CS Hyde48-2F-1-100**, plain MylarTypeA PET,.002 inch nominal(0.0508 mm),1 inch×100 ft
  roll, listed in the [converter's primary film catalogue](https://cshyde.com/viewitems/films/mylar-polyester-pet-film).
  Measure the actual single-layer and assembled-stack thickness; tolerance is
  not assumed. Die cut one registered profile per layer from `cut-patterns-1to1.svg`.
  Do not substitute adhesive film or loose rectangular shim pieces.

Sheet supply/identity, die-cut quality and current availability need the
supplier quote; no order was placed. MJFPA12 is the first carrier/coupon process;
tough SLA requires its own print/post-cure and creep trial.

The existing OEM CAD contains overlapping graphical solids. They **do not
define a physical layer stack**. Current drawing allows2.1 mm module depth and
shows a1.4 mm main-glass reference. Measure front and rear faces at the actual
pad locations. `build_components(doc, measured_depth=..., foam_total=...,
film_layer=..., front_local_z=...)` regenerates the mounting parts. The study
range1.4–2.1 mm is a coupon range, not an invented manufacturer minimum. Local
front-plane adjustment68.5–68.8 is available while the purchased LCD datum stays
fixed; changed soft-pad poses may overlap the OEM's graphical border and must
be judged against received surfaces. A new coupon/bezel may be required after
measurement. The script prints layer count and compression; reject a stack
outside its channel or approved measured force.

## Master API

`build_components` returns `parts`, `received_stack` and `fixed_features`.
Apply `fixed_features['roof_cuts']` to the orange roof and
`fixed_features['bezel_gasket_cuts']` to the cream bezel. There are no bezel
addition solids. Reuse the four screws at(±34.5,69),(±13,105). The carrier/shim
assembly remains clear of|X|≤7.5 through the FFC span. New parts are checked
against the actual saved UI-board geometry at F planes60.0/60.5/61.0. The bench
receiver is not a replacement for the master's curved shell or populated-board
clearance assessment.

## Received coupon trial

1. Print roof, bezel and both carriers; clean all channels. Measure ear/pocket
   levels, flatness and retained bearing thickness. Finish the existing1 mm
   pilots by jig drilling/tapping for M2×0.4, and qualify the actual resin/torque
   and blind-depth stack before using received LCD glass.
2. Obtain the selected foam/film. Measure total foam and PET thickness with a
   controlled low-force method. Calibrate force versus gap for the actual cut
   strips on a calibrated low-range load cell; do not infer force from nominal
   thickness or typical CFD. Record temperature and supported-film orientation.
3. Measure local LCD faces, outline and COG/FFC exclusions. Regenerate/select
   the shim count. Fit front strips to bezel pockets, then the LCD face toward
   the bezel on a soft bench surface. Place registered PET stacks and rear
   strips on the carriers; align tails to the rear screw bores. Seat the roof
   and install four inside-access screws **before fitting the UI board**. Rigid
   ears must seat without trapping a PET layer or transferring screw torque to
   glass. Never force a glass edge into the receiver.
4. Check gap/preload, uniform contact on the two matched face strips, no static
   edge/COG pressure, no movement/rattle under intended handling, and no hard
   glass contact. Verify real FFC bend/insertion and clearances at all three
   intended UI-board heights. The OEM FFC fold is still unqualified.
5. After the unpowered force/fit trial passes, compare the same operating LCD
   free-seated and retained at equal bias, illumination, viewing angle and
   temperature. Use all-pixel/checkerboard patterns; reject new mura, contrast
   gradients, cracked glass, FFC distress or intermittent rows. Repeat force,
   seating and optical checks after dwell/thermal cycling and intended handling.
   Obtain/establish an acceptable glass-load envelope before a product release.

No received material, print, measured force, optical, fatigue, drop or powered
result is claimed. This does not qualify UV exposure resistance or a full
product fabrication release.
