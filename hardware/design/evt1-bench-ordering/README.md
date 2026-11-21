# EVT1 ordering and bench references

For the merged-board evaluation, start with the [Master Bench and Compact
ordering guide](master-bench-eval/README.md). The separate body/flange sources
below serve the earlier split-board EVT and the modular dock.

## Current EVT product boards

Use these files to quote the PCBs for one plug and one dock. The quantities
below are the fitted assemblies per set.

| Finished assembly | Qty | Supplier files and separate parts |
| --- | ---: | --- |
| Plug body PCB | 1 | [Body assembly quote ZIP](../../pcb/evt1/body/assembly-quote/body-evt1-assembly-quote.zip). Leave JP1 open for charge-guard commissioning. |
| Plug flange PCB | 1 | [Single-flange quote and exact target stock](../../pcb/evt1/single-flange-routing/assembly-quote/README.md). Confirm the finished diameter range for the four Ø1.02 mm nominal plated holes. Fit four Mill-Max 1946-0-00-15-00-00-03-0 targets after SMT. |
| Dock spring-pin PCB | 1 | [Pogo assembly quote ZIP](../../pcb/evt1/pins/assembly-quote/pins-evt1-assembly-quote.zip). Price the bare PCB and fixture-soldering separately. The board takes four fitted pins, with two loose spares for the first article. Leave J94 bare for the dock loom. |
| Dock screen and controls PCB | 1 | [JST lid assembly quote ZIP](../../pcb/evt1/dock-control/lcd-socket-candidate/assembly-bench-quote/JST-lid-populated-bench-quote.zip). Quote one Newhaven LCD per dock and confirm the factory 27-way tail geometry against J302 on a matched sample pair. [Display and hinge purchases](../../pcb/evt1/dock-control/lcd-socket-candidate/assembly-bench-quote/README.md#display-and-hinge-purchases) |
| Dock base and lid UV PCBs | 1 each | [Matched 4.22 Ω UV quote ZIPs](../../pcb/evt1/case-telemetry-study/wired-main/uv-assembly/README.md). Count one off-board thermistor and thermostat per UV PCB across the quote and harness lists. |
| Dock lid Hall sensor head | 2 | [Hall head assembly quote ZIP](../../pcb/evt1/dock-safety/wired-hall-head/assembly-quote/wired-hall-head-evt1-assembly-quote.zip). Quote both with the selected A2 sensor. Price the A3 alternate separately. Confirm magnetic release in the assembled dock before selecting the cutoff population. |

Use the [wired dock harness recipes](../../cables/evt1/dock-main/README.md)
and the [plug harness recipes](../../cables/evt1/single-flange-first-article/README.md)
for matched cable quantities. Keep each quote tied to the exact revision and
configuration in its package.

For the dock build, start with the [active FreeCAD assembly](../../cad/evt1-assembly/evt1-wired/DockAssembly.FCStd)
and the [active wired Main](../../pcb/evt1/case-telemetry-study/wired-main/README.md).
Use the [enclosure quote ZIP](dock-enclosure/Compass-EVT1-Dock-Enclosure-Quote.zip)
to price the saved clamshell, controls, hinge pin, and two each of the 6061-T6
UV heat spreaders and thermostat pressure bars. It includes the J401 pocket,
display-flex passages and both blind Hall recesses. Price the liners
separately. Their fabrication depends on the moving UV wire passages and
confirmation of the printable web at the Hall shoulders. Send the
[installed display-flex quote ZIP](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/display-flex-feasibility/Compass-EVT1-Display-Flex-Feasibility.zip)
for pricing on the 178.16 mm socket-mouth layout. Measure the loaded tail
height and mouth-to-tip insertion at each 20-way socket, J201 and J301,
before releasing the custom flex artwork.
Main routing and the fitted Hall cutoff gate Main artwork and the combined
dock order. Quote one empty 316L body/cap pair using the
[machining and inspection packet](metal-quote/Compass-EVT1-Body-Cap-Feasibility.zip).
Ask for the finished motor-bore schedule separately. Use the
[protected-pack drawing request](../../pcb/evt1/pack-lead-feasibility/README.md)
for the fitted pack. Final metal dimensions, pack retention, installed loom
and silicone tooling gate the product part order.

## Plug flange PCB hardware

Allow four **NBK SPA-M1.4-2-MC3** RENY screws per fitted flange PCB and one
shared **NBK SKCHB-M1.4** driver bit per assembly station. NBK supplies ten
screws per pack. The bench quote below for two populated boards and one
fitted bare board needs 12 screws, so allow two packs if all three are fitted.
Use the dedicated bit in a compatible bit holder to install the PCB from the
open dry side. The 1.00 mm PCB leaves 1.00 mm nominal screw insertion into each
Ø1.10 × 1.30 mm blind pilot. Check usable thread depth and confirm that all
four heads bear on the board before the screws reach the pilot floors.
Establish installation torque with the received printed cover and screws.
An axial Ø6.35 mm bit envelope clears the four open-cover screw stations in
the [saved assembly](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/SingleFlangeBoardTrial.FCStd)
by at least 0.23 mm nominally, with U6 nearest. Keep the holder out of the
cavity and confirm access during dry assembly.
[Selected flange hardware](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/selected-parts.json) · [NBK screw and pack](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/plasticscrew/SPA-MC3/SPA-M1.4-MC3/SPA-M1.4-2-MC3/?SelectedLanguage=en-US) · [NBK bit](https://www.nbk1560.com/en/products/specialscrew/nedzicom/plasticscrew/SKCHB/SKCHB-M1.4/?SelectedLanguage=en)

## Dock button and contact springs

Allow **five Lee Spring LC014B02S coils per assembled dock** and **two shared
spares for the first build**. Quote seven total for that build. Count the two
contact-module coils and spares here if that same module will go into the dock.

| Installed use | Quantity per dock | Seat-to-seat length in the saved closed assembly | Nominal force per coil |
| --- | ---: | ---: | ---: |
| Blue button caps, at rest | 3 | 4.50 mm | 2.30 N |
| Contact-carrier magnets | 2 | 3.80 mm | 2.76 N |

Lee Spring lists a 7.95 mm free length, 4.57 mm outside diameter and
0.666 N/mm spring rate for the exact stainless SKU. The table uses
free length minus installed length to estimate compression. During assembly,
measure cap preload and actuation force on all three buttons. At the contact
carrier, measure the installed seats, spring force and retainer load.
[Lee Spring LC 014B 02 S catalog row][dock-spring-vendor] ·
[Contact module assembly](contact-interface/README.md)

[dock-spring-vendor]: https://www.leespring.com/compression-springs/1?field_free_len_cm_value%5B0%5D=&field_free_len_cm_value%5B1%5D=&field_free_len_in_value%5B0%5D=&field_free_len_in_value%5B1%5D=&field_free_len_mm_value%5B0%5D=&field_free_len_mm_value%5B1%5D=&field_hole_dia_cm_value%5B0%5D=&field_hole_dia_cm_value%5B1%5D=&field_hole_dia_in_value%5B0%5D=&field_hole_dia_in_value%5B1%5D=&field_hole_dia_mm_value%5B0%5D=&field_hole_dia_mm_value%5B1%5D=&field_inside_dia_cm_value%5B0%5D=&field_inside_dia_cm_value%5B1%5D=&field_inside_dia_in_value%5B0%5D=&field_inside_dia_in_value%5B1%5D=&field_inside_dia_mm_value%5B0%5D=&field_inside_dia_mm_value%5B1%5D=&field_load_at_solid_height_gm_value%5B0%5D=&field_load_at_solid_height_gm_value%5B1%5D=&field_load_at_solid_height_kg_value%5B0%5D=&field_load_at_solid_height_kg_value%5B1%5D=&field_load_at_solid_height_lb_value%5B0%5D=&field_load_at_solid_height_lb_value%5B1%5D=&field_load_at_solid_height_n_value%5B0%5D=&field_load_at_solid_height_n_value%5B1%5D=&field_outside_dia_cm_value%5B0%5D=&field_outside_dia_cm_value%5B1%5D=&field_outside_dia_in_value%5B0%5D=&field_outside_dia_in_value%5B1%5D=&field_outside_dia_mm_value%5B0%5D=&field_outside_dia_mm_value%5B1%5D=&field_published_stock_code_value=&field_rate_gm_cm_value%5B0%5D=&field_rate_gm_cm_value%5B1%5D=&field_rate_gm_mm_value%5B0%5D=&field_rate_gm_mm_value%5B1%5D=&field_rate_kg_cm_value%5B0%5D=&field_rate_kg_cm_value%5B1%5D=&field_rate_kg_mm_value%5B0%5D=&field_rate_kg_mm_value%5B1%5D=&field_rate_lb_in_value%5B0%5D=&field_rate_lb_in_value%5B1%5D=&field_rate_n_cm_value%5B0%5D=&field_rate_n_cm_value%5B1%5D=&field_rate_n_mm_value%5B0%5D=&field_rate_n_mm_value%5B1%5D=&field_rod_dia_cm_value%5B0%5D=&field_rod_dia_cm_value%5B1%5D=&field_rod_dia_in_value%5B0%5D=&field_rod_dia_in_value%5B1%5D=&field_rod_dia_mm_value%5B0%5D=&field_rod_dia_mm_value%5B1%5D=&field_solid_height_cm_value%5B0%5D=&field_solid_height_cm_value%5B1%5D=&field_solid_height_in_value%5B0%5D=&field_solid_height_in_value%5B1%5D=&field_solid_height_mm_value%5B0%5D=&field_solid_height_mm_value%5B1%5D=&field_wire_dia_cm_value%5B0%5D=&field_wire_dia_cm_value%5B1%5D=&field_wire_dia_in_value%5B0%5D=&field_wire_dia_in_value%5B1%5D=&field_wire_dia_mm_value%5B0%5D=&field_wire_dia_mm_value%5B1%5D=&items_per_page=20&max=&min=&order=field_solid_height_cm&page=768&q=compression-springs%2F1&sort=desc

## Hall station hardware

One dock uses two lower Hall brackets and two captured lid magnets. The
[enclosure quote](dock-enclosure/Compass-EVT1-Dock-Enclosure-Quote.zip)
includes both brackets, both magnet carriers and backers, and four
machined PEEK bracket spacers. Source the loose hardware separately.

| Loose hardware | Installed per dock | Buying and fit |
| --- | ---: | --- |
| NBK **SPE-M2-8-C** | 4 | PEEK M2 × 0.4 × 8 socket-head screws, two per bracket. NBK lists 20 per pack. Pair each with one quoted Ø2.60 × Ø2.10 × 3.20 mm spacer. Check usable blind-thread depth and tool access. [NBK exact part](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/heatresistance/SPE-C/SPE-M2-C/SPE-M2-8-C/) |
| Supermagnete **S-01-01-N** | 2 | Axial N45 disc, Ø1 × 1 mm nominal with ±0.10 mm diameter and thickness tolerance. The maker lists 20 per unit of sale. Measure each disc and record its installed pole. [Supermagnete exact part](https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-1mm-1mm_S-01-01-N) |
| TiAl **Ti2-GS-M2x8-Si** and plain PET shims | 2 studs and 4 shim rings | Quote candidate for the two upper carriers. Each is an M2 × 0.4 × 8 flat-point Grade 2 titanium set screw. Two 0.0508 mm nominal plain PET rings give 0.1016 mm per carrier. Start at Ø3.80 OD × Ø2.20 ID and measure the seated stack. [TiAl DIN 913 series](https://www.titanschrauben.shop/m2-silver-socket-set-screws-allen-key-garde-2-din-913-iso-4026_1) · [CS Hyde plain PET](https://cshyde.com/viewitems/ecific-optically-clear-transparent-films-1/mylar-polyester-pet-film) |

Inspect the two 0.25 mm capture shoulders and check the backers against the
received discs. The M2 × 8 nominal stack gives 2.00 mm gross insertion into
the carrier and 5.90 mm into the lid post. The 2.00 mm carrier pilot includes
thread lead-in and runout. Verify usable thread, the fitted shim and
independent stud retention before using this hardware. Set the stud end and
backer together so the disc stays captive when the lid cycles.
[Carrier and backer fit](../../cad/evt1-assembly/lid-jst-integration/hall-probe-fixture/close-target-trial/README.md#fit-and-load)

The Hall boards seat directly on the lower supports under their integral lips.
Verify the printed 0.90 mm slots and the assembled PCB top at Z34.85 mm.
Restrain the wire independently to keep load off the three hand-soldered
pads on each head. For both looms, quote two JST GHR-03V-S housings, ten
SSHL-002T-P0.2 contacts including the four setup/spares, and 1.50 m of Allied
1371-26-7 before scrap. The two side-entry headers are Main PCB parts.
[Installed Hall stations](../../cad/evt1-assembly/evt1-wired/README.md#hall-board-fit) ·
[Hall harnesses and pin map](../../cables/evt1/dock-main/README.md#hall-heads-to-main)

## Existing bench sample packages

The remaining sample packs, fixtures and legacy boards are bench references.
Use them to look up existing evidence or answer a specific build question.
Confirm the exact part, pack quantity, availability and lead time when ordering.

### Bench quote references

The following requests can proceed independently. Each quantity covers one
bench build or its stated sample set.

| Supplier | Send | Request |
| --- | --- | --- |
| CNC metal shop | [Body/cap feasibility](metal-quote/Compass-EVT1-Body-Cap-Feasibility.zip), [motor bore coupons](metal-quote/motor-seat-witness/Compass-Motor-Seat-Witness-Quote.zip) and [rear torque coupon](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/torque-coupon/RearJointTorqueQuote.zip) | Separate prices for one body/cap pair, one coupon of each of the three motor bore sizes, and six short 316L rear coupons with one steel driver. The torque packet also specifies six matching PA12 trays for the print shop. Return achievable threads, finishes and tolerances before cutting a product pair. |
| MJF/SLA shop | [Inert pack fit](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/dry-retention-screen/Compass-EVT1-Inert-Pack-Fit-Quote.zip) and [four-contact fit](contact-interface/Compass-EVT1-Contact-Fit-Quote.zip) | One each of the three pack gauges, one contact carrier and one rear retainer. Price two optional open-tray fixtures separately. Route the six steel keeper samples in the contact packet to a metal shop. The closed pack restraint is under review. |
| PCB and harness shops | [Retained body PCB](../../pcb/evt1/body/assembly-quote/body-evt1-assembly-quote.zip), [single-flange PCB](../../pcb/evt1/single-flange-routing/assembly-quote/README.md), [pogo board](../../pcb/evt1/pins/assembly-quote/pins-evt1-assembly-quote.zip) and [loom first article](../../cables/evt1/single-flange-first-article/README.md) | Ask for two populated body boards, three flange boards total with two SMT-populated, one assembled pogo board and one unpowered loom fit set. Confirm finished board thicknesses and holes. Allow ten loose targets including two spares, or fourteen if fitting the inert bare board as well. Keep the J7 and body-side pack-disconnect terminals loose for dry fitting. |
| Display fixture and bare PCB shops | [Printed fit fixture](../../cad/evt1-assembly/vendor/lcd-socket-replacement/JST-Display-Fit-Review.zip), [JST lid bench quote](../../pcb/evt1/dock-control/lcd-socket-candidate/bench-quote/README.md) and [continuity breakout quote](../../pcb/evt1/dock-control/lcd-continuity-breakout/README.md) | One fixture set, three bare lid boards and three bare breakout boards. Fit a socket to one lid board and two breakouts for the unpowered trial. The display and socket stock is below. |
| Hall and magnetic-latch dry fit | [Matched Hall case-fit quote](hall-case-fit/Compass-EVT1-Hall-Case-Fit-Quote.zip) | One dry enclosure using the existing cutoff stations, two probe supports, two close target carriers and six bare probes. Reuse the shells, liners and hinge pin if the hinge mockup is already ordered. Confirm shell STEP import and the 0.25 mm target capture shoulder. |
| Protected pack supplier | [Horizontal-mate feasibility ZIP](../../pcb/evt1/pack-lead-feasibility/BC-PACK-EVT1-001-Feasibility.zip) | Price ten protected packs with 41.79 and 42.03 mm installed free lead paths. Quote one separate inert sample with the same wrapper, exit, strain relief and connector for a fit check before ordering the live lot. Request a controlled drawing for protection, lead exit, growth and strain relief. The two NTCs and four sensor leads are fitted in the device. |

The screw-closed tooling is a separate inert molding request below. If
combining that request with the rear torque trial, allow seven E10028 nuts
in total. Order four packs if the distributor confirms two nuts per pack,
and reserve the eighth for the body shop's dry fit. If quoting the body/cap
pair separately, reserve one nut from a two-nut pack for that check.
For the motor-seat work, quote five motors of the same construction and
five tip thermistors using the [exact samples](metal-feasibility.md#motor-and-tip-sensor-samples).

| Part | Proposed sample quantity | Bench use |
| --- | ---: | --- |
| ifm **E10028** | 3 packs × 2 nuts | Incoming dimensional checks and six fresh M18×1 joints. 316Ti stainless, nominal 24 mm AF × 4 mm. Verify how the distributor counts packs. [ifm Canada](https://www.ifm.com/ca/en/product/E10028) · [DigiKey 2330-E10028-ND](https://www.digikey.ca/en/products/detail/ifm-efector-inc/E10028/17866905) · [drawing and model record](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/selection.json) |
| Henkel **LOCTITE 243**, IDH **1330799**, 6 mL tube | 1 | Medium-strength threadlocker candidate for inert torque/cure trials. [Henkel product and technical data](https://next.henkel-adhesives.com/us/en/products/industrial-adhesives/central-pdp.html/loctite-243/BP000000316211/variation/1330799.html) |
| OneMonroe **32 X 1 S-70**, integration ID **133431** | 10, quote sample | 32 mm ID × 1 mm silicone nose seal for the empty metal pair. Obtain lot dimensions and compound data with the quote. [Exact sample and nose-only trial](nose-seal-trial.md) |
| Vishay **NTCLE413E2103F524A** | 4 | Two-board design only: two dry pack sensors for the fit gauge and two spares. The one-board pack (BC-PACK-EVT1-002) has its own NTC, so skip these for it. [Vishay 29078](https://www.vishay.com/docs/29078/ntcle413.pdf) · [DigiKey listing](https://www.digikey.ca/en/products/detail/vishay-beyschlag-draloric-bc-components/NTCLE413E2103F524A/16530174) · [pack specification](../../pcb/evt1/pack-spec.json) |
| 3M **5413**, part **7000050064** | 1 roll | 6.35 mm tape for the pack sensor head and lead coupons. [3M part](https://www.3m.com/3M/en_US/p/dc/v000091658/) · [DigiKey roll](https://www.digikey.ca/en/products/detail/3m/5413-AMBER-1-4-IN-X-36-Y/1819260) · [cut blanks](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/parts-and-cut-stock.json) |
| Newhaven **NHD-C12864B2Z-RN-FBW** | 2 | Reflective 128×64 LCD with integral 27-way flex. One for repeated fit checks, one for comparison and subsequent powered bring-up. [Newhaven product](https://newhavendisplay.com/128x64-graphic-cog-lcd-fstn-display-with-no-backlight/) · [DigiKey listing](https://www.digikey.ca/en/products/detail/newhaven-display-intl/NHD-C12864B2Z-RN-FBW/1885690) · [display geometry record](../../cad/evt1-assembly/vendor/display/source-manifest.json) |
| JST **27FLZ-RSM2-TB (LF)(SN)** | 5 | Bottom-contact socket samples for measurement, reflow and spares. [Newhaven listing](https://newhavendisplay.com/27-pin-surface-mount-right-angle-connector-with-0-5-mm-pitch/) · [DigiKey cut tape](https://www.digikey.ca/en/products/detail/jst-sales-america-inc/27FLZ-RSM2-TB/1634721) · [JST FLZ catalog](https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf) · [geometry record](../../cad/evt1-assembly/vendor/lcd-socket-replacement/provenance.json) |
| Molex **0150200966** | 2 | Passive 51 mm, 27-lane, 0.50 mm pitch test tail for the two breakouts. Measure the received mating ends for the JST width and thickness limits. [Molex part](https://www.molex.com/en-us/products/part-detail/150200966) · [DigiKey listing](https://www.digikey.ca/en/products/detail/molex/0150200966/2972888) |
| Molex **0151660220** | 2 | 203 mm, 20-way, 0.50 mm pitch, opposite-face jumper for the Main-to-lid bench connection. Map both ends before powering the populated lid. [Molex part](https://www.molex.com/en-us/products/part-detail/0151660220) |
| Molex **52437-2771** | 2, optional | Comparison with the saved Molex lid and its original footprint. [Molex 524372771](https://www.molex.com/en-us/products/part-detail/524372771) · [saved Molex fit study](../../cad/evt1-assembly/vendor/lcd-socket-replacement/negative-molex/review.json) |
| Rogers **4790-92-09030-04 P**, product **3036884** | 1 small sample sheet | Cut four 1.2 × 22 mm face pads per fixture, plus spares. Request a sample cut of the exact PET-supported grade. [LCD retention material record](../../cad/evt1-assembly/lcd-retention-trial/source-manifest.json) |
| CS Hyde **48-2F-1-100** | 1 roll | Plain 0.0508 mm nominal PET for registered glass-pad shims and four equal PCB shim stacks. [CS Hyde item](https://cshyde.com/item/ecific-optically-clear-transparent-films-1/mylar-polyester-pet-film/2mil-mylar-1in-100ft) · [cut profiles](../../cad/evt1-assembly/lcd-retention-trial/cut-patterns-1to1.svg) |
| NBK **SNSS-M2-6** | 1 pack of 10 | Four existing-design screws for the LCD retention coupon. Gauge the four separate PCB fixture screw seats and underside access during setup. [NBK part](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/socketheadcapscrew/SNSS/SNSS-M2/SNSS-M2-6/) · [coupon parts](../../cad/evt1-assembly/lcd-retention-trial/assembly-parts.json) |

## Integrated EVT dependencies

The packages below support quotes, independent bench builds and incoming
inspection. Supplier acceptance, physical fit and a matched product build
are still open. Use this table to choose the next specimen or supplier input.

| Workstream | Prepared input | Gate to an integrated build |
| --- | --- | --- |
| Turned body, cap and rear clamp | [Body/cap quote packet](metal-quote/Compass-EVT1-Body-Cap-Feasibility.zip), [three motor seat coupons](metal-quote/motor-seat-witness/README.md) and the [six-pair rear torque coupon](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/torque-coupon/README.md) | Review both thread stacks, indexed flats, sensor bore and seals with the shop. Measure received motor fit in the witness bores, plus clamp load, plastic creep and actual nut-to-NTC clearance. Establish alloy, finish, tolerances and threadlocker process before releasing product metal. |
| Rigid flange, buttons and silicone | [Screw-closed inert tool and insert quote](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/screw-closed-quote/README.md), [material order](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/INERT-MATERIALS.md) and [screw witness](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/SCREW-WITNESS.md) | Gauge both screw seats, all four soldered targets, mask shutoff and pocket leakage. Section an inert casting at screws/buttons and qualify bond, cure and sealing before introducing electronics or a pack. |
| Protected pack | [Inert pack fit quote ZIP](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/dry-retention-screen/Compass-EVT1-Inert-Pack-Fit-Quote.zip), [long-lead feasibility package](../../pcb/evt1/pack-lead-feasibility/README.md) and [closed-cover review](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/closed-tray-restraint/README.md) | Obtain a controlled drawing for the 33 × 21 × 6.3 mm maximum, 1.5 A continuous/2 A pulse protection and approximately 42 mm horizontal-mate leads. Check growth and strain relief with the supplier. The review shows a 1.20 mm internal cover-column trim to seat the restraint. Trial connected loom slack and stowage before releasing the cover and loom. |
| Device PCBs and wiring | Retained [body](../../pcb/evt1/body/assembly-quote/body-evt1-assembly-quote.zip), [single flange](../../pcb/evt1/single-flange-routing/assembly-quote/README.md) and [18-conductor loom first article](../../cables/evt1/single-flange-first-article/README.md) | Quote a Cooner CZ 1104 wire sample and the exact JST crimps. Confirm wire OD, fine-strand crimp results and routing bend before assembly. Check J2.2P/2S and both dry NTCs, cap threading with loose tails, connector pullback and restraint, and dry closure around the representative pack. |
| Fixed J6 closure fixture | [One insulating board support](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/j6-dry-support/Compass-EVT1-J6-Dry-Support.zip) | Reuse the shortened mold root and actual unpowered body PCB. Trial the existing drilled cover, pack gauge and untrimmed loom before specifying cut lengths. The short root omits cap rotation and the final bore taper. |
| Four-contact interface | [Mechanical quote ZIP](contact-interface/Compass-EVT1-Contact-Fit-Quote.zip) and [pin and target quotes, fasteners and magnet hardware](contact-interface/README.md) | Measure seated stroke, stop/head engagement, fit, holding force and USB across the physical contacts. The carrier covers both plug buttons. Test ROM entry off-dock followed by reseating. |
| Dock mechanics and wiring | [Product enclosure quote](dock-enclosure/Compass-EVT1-Dock-Enclosure-Quote.zip), [custom hinge flex feasibility](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/display-flex-feasibility/README.md) and [dock cable recipes](../../cables/evt1/dock-main/README.md). Use the [earlier hinge specimen](hinge-mockup/README.md) as a bench reference. | Check actual display ribbon fit, motion with both wire types and restraint, pin/contact seating and USB. Qualify UV hardware cutoff, enclosure leakage, optical coverage, dose and materials separately before powered UV. |
| Hall and latch fit | [Product dock assembly](../../cad/evt1-assembly/evt1-wired/README.md#hall-board-fit), [enclosure and mounts quote ZIP](dock-enclosure/Compass-EVT1-Dock-Enclosure-Quote.zip) and [optical acceptance](../../cad/evt1-assembly/lid-jst-integration/hall-lid-study.md) | Verify PCB and magnet retention on the received hardware. Measure release with latch and carrier magnets installed. Verify each hardware cutoff and measure finished-unit UV-C leakage around seam, ports and hinge. |
| Dock electronics | [Active wired Main project](../../pcb/evt1/case-telemetry-study/wired-main/README.md), [product Hall head](../../pcb/evt1/dock-safety/wired-hall-head/README.md) and [matched parts](#pcb-quote-scope) | Main schematic parity passes. KiCad reports 13 opens and zero other PCB design-rule findings. Both lid stations use the routed Hall head. Finish Main routing and integrate both receivers before generating Main supplier artwork. |

The earlier [five-board fit kit](../../cad/manufacturing-layout/evt1-integration/README.md)
covers its own PCB and housing baseline. Use the individual current files
above for quote requests. Ask the metal shop to return achievable feature
tolerances and gauging, and the pack supplier to return a controlled exit
and protection drawing. Those feasibility inputs can proceed while the
enclosure and loom proposals are in review.

## Rear joint trial

Use the [saved two-jaw driver](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/TwoJawDriver.step)
as the starting model for a machinist-reviewed steel tool. Verify driver
material, jaw strength and access with a torque transducer. Prepare six inert
stub/tray pairs using the [shortened coupon quote package](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/torque-coupon/README.md)
and the full single-board tray. The package gives the editable coupon, shop
datums, sample quantities and provisional 316L / MJF PA12 quote basis. Use the
intended production material and finish when qualifying torque. Fixture a dummy pack
at the [specified maximum envelope](../../pcb/evt1/pack-spec.json) and use the
saved dry head positions for clearance.

1. Gauge each nut's thread, thickness, bearing face, flats and corners.
   Record nut and coupon identity. Trial tool engagement with the tray empty.
2. Use three fresh pairs to characterize torque, clamp load and pad deformation
   during setup, and three to check repeatability with the chosen preparation
   and cure. Treat this as initial characterization. Derive the torque range
   from clamp-load and part limits, then qualify the process on further samples.
3. Photograph and record final nut clocking and minimum clearance to both
   heads with the dummy pack. Measure retained clamp load after conditioning
   and breakaway torque separately. Share any interference and the measured
   stack before changing the sensor or tray geometry.
   [DFM and qualification plan](../../cad/manufacturing-layout/DFM.md) ·
   [unshifted-nut clearance evidence](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/nut-lock-budget-review.json)

## Motor and cap witness

Use the [motor seat coupons](metal-quote/motor-seat-witness/README.md) to
check the received motor lot against the three candidate bore sizes. Use the
[first motor power procedure](motor-first-power.md) for the independent motor
and dummy-load tests, including startup and dock contact transitions.

## Inert flange tooling

Use the [screw-closed tooling quote packet](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/screw-closed-quote/SingleFlangeScrewClosedInertToolingQuote.zip)
for the two main tool halves, the rear contact insert, the pre-cured
diaphragm tool, three trays and matching drilled covers, and one shortened root.
Review the [closure trial](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/closure-review/README.md)
before sending the quote packet to the shop.
The [trial instructions](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/INERT-TRIAL.md)
cover the dry stop and pad checks before casting. The tooling shop quote
leaves the following stock to the bench.

| Item | Bench quantity | Use |
| --- | ---: | --- |
| Bare single-flange PCB | 1 per contact-equipped specimen | Keep one bare for the first dry setup. For each further cast that retains a carrier, add one bare board to the quantity quoted for populated builds. [Bare-board fabrication ZIP](../../pcb/evt1/single-flange-routing/assembly-quote/single-flange-evt1-fabrication-quote.zip) |
| Mill-Max **1946-0-00-15-00-00-03-0** | 4 per bare PCB | Seat all four shoulders on the board and measure the heads. [Exact order and positions](../../pcb/evt1/single-flange-routing/assembly-quote/single-flange-manual-targets.csv) |
| NBK **SPA-M1.4-2-MC3** | 4 per fitted bare PCB | Use the shared [flange PCB driver bit](#plug-flange-pcb-hardware). Verify the threads and engagement in the rear-cover seats. Count each fitted PCB once. |
| NBK **SNZS-M2-10** | 2 per rear half, 6 for three | M2 × 0.4, 10 mm under the low-profile PH0 head. NBK lists 50 per pack. Gauge screw length and usable tray pilot with the recessed trial cover before tightening. [NBK drawing](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNZS-M/SNZS-M2/SNZS-M2-10/) |
| ifm **E10028** | 1 for the shortened root | Allow one extra thin nut beyond the six rear-joint coupon nuts. Confirm the distributor's pack quantity. [ifm Canada](https://www.ifm.com/ca/en/product/E10028) |
| M4 × 65 through bolts and M4 nuts | 4 each | Clamp the tooling. Verify usable thread length with the actual 56 mm stack. [Tooling requirements](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/TOOLING-RFQ.md) |
| M4 flat washers | 8 | One under each bolt head and nut at the tooling clamp stack. [Tooling setup](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/INERT-TRIAL.md) |
| Ø4 × 10 mm removable straight dowels | 2 | Align the tool halves. [Tooling setup](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/INERT-TRIAL.md) |
| Smooth-On **Dragon Skin 20** | 1 × 2 lb trial kit | Pre-cured internal diaphragm and witness coupons. [Material and mass plan](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/INERT-MATERIALS.md) |
| Smooth-On **Ecoflex 00-45 Near Clear** | 1 × 2 lb trial kit | Translucent outer skin for three inert casts and material witnesses. [Material and mass plan](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/INERT-MATERIALS.md) |

Confirm the two M3 insert retainers with the tool shop against the blind
pilots. Check the rigid flange closure screw length and engagement with
the received deeper cover. Record target depth and tilt from the closed
tool’s rear stop using the [measurement worksheet](../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/measurement-review/README.md).

## Display and cutoff bench references

Use the [dock logic fixture](dock-logic-fixture.md) with the direct Main and
populated JST lid for the powered screen and three-button check. The
[Hall lid-cutoff study](../../cad/evt1-assembly/lid-jst-integration/hall-lid-study.md)
is the next cutoff candidate. Quote six identical
[Hall field-probe PCBs](../../pcb/evt1/dock-safety/hall-field-probe/Compass-EVT1-Hall-Field-Probe-Quote.zip)
to build one left/right pair for each threshold grade. Use the separate bench
supply and capture each lid-gap transition before wiring an interlock.
The [removable fixture shop quote](../../cad/evt1-assembly/lid-jst-integration/hall-probe-fixture/CompassHallProbeFixture-shop.zip)
uses the existing cutoff mounts. Confirm the supplier can make the 0.30 mm
cup wall and inspect the received fit before installing a magnet.
The [D2F-01L travel gauge](../../cad/evt1-assembly/vendor/lid-cutoff/TRAVEL-GAUGE.md)
documents the inherited mechanical cutoff. Use the Hall channels for the
product lid cutoff.
For the separate three-cap fit and force trial, quote one
[retained button coupon](../../cad/evt1-assembly/button-mechanics-trial/Compass-EVT1-Button-Coupon-Quote.zip).
The coupon uses three LC014B02S coils and seven printed parts. Add three coils
to the dock order only if stocking the coupon separately. Use the exact
manufacturer rate above for current force estimates. The instrumented anvil
checks the cap loads before fitting the lid PCB.

Use the [editable received-fit fixture](../../cad/evt1-assembly/vendor/lcd-socket-replacement/JSTSocketReceivedFit.FCStd)
and its [assembly and measurement instructions](../../cad/evt1-assembly/vendor/lcd-socket-replacement/README.md).
Print one roof and one set of retention carriers/receivers in the chosen
MJF/SLA process using the [fixture print package](../../cad/evt1-assembly/vendor/lcd-socket-replacement/JST-Display-Fit-Review.zip).
Use the [roof STEP](../../cad/evt1-assembly/vendor/lcd-socket-replacement/JSTDisplayFitRoof.step)
for a print quote if the shop accepts STEP. Use the [bare JST lid bench quote](../../pcb/evt1/dock-control/lcd-socket-candidate/bench-quote/README.md)
and reflow only J302 for the unpowered fit fixture. Provide a known-numbered
27-way test tail to map the terminal row. Contacts 13 and 23 share 3V3_UI.
Contact 14 and the two mechanical hold-downs share GND. The lid PCB gives 26
distinct nets for the 27 numbered contacts. For an independent one-to-one
continuity and isolation check, order three bare
[continuity breakout boards](../../pcb/evt1/dock-control/lcd-continuity-breakout/README.md)
and fit one JST socket to each of two boards. Keep the third bare as a spare.
[Native lid netlist](../../pcb/evt1/dock-control/lcd-socket-candidate/dock-lid-ui-native.xml)

Measure received tail thickness, width and exposed land length, and map the
marked end and all 27 paths before powering a display. Check isolation and
insertion to the physical stop. With glass supported at Z68.8, measure loaded
copper face height **H** above the PCB and solve the candidate equal shim
stack **t = H − 0.20 mm** for the current neutral flex route. The fixture
search range is 0.10–1.50 mm. If the received geometry falls outside it, bring
the measured stack to the next geometry review. Check the complete populated
lid, button travel, cable strain and lid motion before adopting the shim or
connector. [Saved dock interference report](../../cad/evt1-assembly/review-051/result.json)

## Unpowered dock hinge mockup

The [unpowered hinge quote packet](hinge-mockup/Compass-EVT1-Unpowered-Hinge-Quote.zip)
contains the revised upper liner, the other printed and machined parts,
three bare PCB fabrication sets and the one-specimen parts list. Use it
for review and quoting. Confirm print process and assembly access before
fabrication.

Prepare one UV-wire fit and cycling specimen after the owner reviews the
shifted outlet. Use the complete hinge, both stationary UV branches and an
inert device exterior. Keep the dock disconnected from USB and batteries.
Use header-only boards and populate neither UV emitters nor drivers.

| Item | Quantity per specimen | Source and preparation |
| --- | ---: | --- |
| Lower/upper shells and liners | 1 each | MJF or SLA using the [shells and lid keeper trial](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/lid-keeper-quote/README.md) for both shells and both lid keeper halves, the [repaired upper liner](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/lid-keeper-quote/upper-liner-repair/README.md) for the upper liner, and the [shifted trial](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/liner-preassembly/route-join/shared-base-review/shifted-motion-refit/README.md) for the lower liner. |
| Hinge pin and retainer | 1 each | Use the [pin STEP and machining notes](hinge-mockup/README.md#machined-pin) and have the shop review the turned Ø3 × 72.8 mm under-head shaft, Ø5.2 × 1 mm head and blind M2 × 0.4 tap with ≥4.3 mm full thread. Retain with one NBK **SNSS-M2-4** and one PTS **A12502A** plain washer. [Hinge source](../../../tools/build_evt1_native_dock.py) · [PTS washer drawing](https://www.pts-uk.com/products/washers/form-a-flat-washers/metric-a2/A12502A) |
| UV stack and mounting hardware | 2 spreader stacks, 8 UV board screws, 8 liner screws, 6 Main screws | Use the installed shell shoulders and the [mechanical UV stack](../../cad/evt1-assembly/uv-module-trial/assembly-parts.json), including the two spreaders and four 12 × 3 × 0.508 mm pads. Fit the two thermostats, pressure bars, guards, NTCs and clips using the listed mounting hardware and local tail geometry. Leave these leads electrically disconnected. Use eight NBK **SNSS-M2-6**, eight Accu **SIK-M2-6-A2** and six NBK **SNSS-M2-4**, respectively. |
| Bare boards and GH headers | 1 Main, 1 UV base, 1 UV lid, 4 headers | Use the [Main bare fabrication ZIP](../../pcb/evt1/dock-main/assembly-quote/dock-main-fabrication-quote.zip) and the Gerber/drill sets in the [UV base](../../pcb/evt1/dock-uv/base/pcb/fabrication-review/uv-base-supplier-review.zip) and [UV lid](../../pcb/evt1/dock-uv/lid/pcb/fabrication-review/uv-lid-supplier-review.zip) packages. Fit only JST **SM08B-GHS-TB(LF)(SN)** at Main J621/J622 and UV J401/J501. Check the linked component envelopes for any omitted part that bounds a wire corridor before using a bare board there. |
| Two GH8 looms | 4 housings, 32 installed contacts, 8 sample/spare contacts, 3.20 m starting wire + scrap | Use JST **GHR-08V-S**, **SSHL-002T-P0.2**, and Allied **1371-26-7**. Start with eight 175 mm base and eight 225 mm lid blanks for this unpowered setup. The latter leave trimming and handling allowance. Record the fitted length before cutting/crimping the second ends. Follow the [two straight-through pin maps](../../cables/evt1/dock-main/uv-harnesses/README.md). |
| Two split keepers | 4 halves, 4 nuts, 4 screws | Use the [keeper geometry and attachment](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/README.md): two NBK **SNSS-M1.6-5** for the recessed base, two Aspen **ME127-016035X6** for the lid, and four Accu **HPN-M1.6-A2** nuts. [Aspen drawing](https://www.aspenfasteners.com/content/2D_PDF/product64/ME127-016035X6.PDF) · [Accu nut](https://www.accu.co.uk/hexagon-nuts/7882-HPN-M1-6-A2) |
| Inert seated device exterior | 1 | Use the [seated exterior STEP and fixture notes](hinge-mockup/README.md#inert-seated-exterior). Keep the fixture's support clear of the moving row. |

The separate [shifted lower liner and keeper trial](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/liner-preassembly/route-join/shared-base-review/shifted-motion-refit/README.md)
contains the editable assembly and three checked STEP exports. Review the
shifted trial and lid keeper seats before fabricating the mockup. The repaired
upper liner passes the advanced FreeCAD check and independent STEP reimport.
Confirm the lower liner closes the original UV opening, preserves the display
passage and places the new base ear centers at X−16.90/−2.10, Y147.336 mm. The
[shifted keeper check](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/liner-preassembly/route-join/shared-base-review/shifted-motion-refit/keeper/README.md)
shows the geometry and access constraints. The initial specimen screens the
UV wiring. Fit the selected Molex **0151660220** display flex and its actual
mounting stack for a subsequent combined hinge test.

### Measurements and first motion test

1. **Gauge the incoming fit.** Record part revisions, print process/material,
   wire lot and pin diameter, the three hinge bore diameters and alignment,
   assembled axial endplay, keeper throat and outlet dimensions, liner wall
   thickness and screw engagement. Measure wire OD against JST's 0.76–1.00 mm
   range. Measure crimp width/height and pull-test samples with the actual
   wire and tooling. Record the clear throat when feeding the eighth lead
   and the actual conductor length within each terminal/housing.
2. **Assemble with access.** Install the inner base nut before dressing
   J401. With the dock empty, trial inner top drive at 0° and outer at 110°
   or fit the fasteners before dressing the bow. Follow the
   [lid thread-first sequence](../../cad/evt1-assembly/dock-harness-trial/shared-hinge-review/guard-review/uv-end-guide-review/split-keeper-review/liner-preassembly/PREASSEMBLY.md).
   Record wire pullback needed to seat the liners and whether each GH latch
   stays seated. Measure all 16 finished conductors end to end. For J622
   record pins 1/2 separately, including both crimp allowances. Keep
   ≤175 mm as the current powered limit. Compare a longer inert fit to
   the [185/190 mm electrical review](../../pcb/evt1/dock-safety/lid-wire-length-review/README.md)
   before using it in a powered build.
3. **Sweep continuously.** Record opening and closing with the inert
   exterior seated, then repeat empty. Log lid angle, opening/closing
   torque or force at a fixed lever arm against the pre-loom baseline,
   minimum bend radius and measured
   clearances to the liner, cap, fasteners and adjacent wires. Take close
   views at 0–18°, 45°, 60°, 75°, 90° and 110° and at each change in
   contact or force. Compare the wire centerline radius with the 4 mm
   routing target. Mark the jackets at the guides and housings to measure
   any axial migration or load transfer. Use an isolated, current-limited
   continuity fixture at the board pads to log all 16 wires during motion.
   Verify pin mapping and adjacent-lane isolation on the unplugged looms.
   Main intentionally ties J621/J622 pins 1, 2 and 3 number to number.
   Account for those ties in the moving continuity fixture. Record
   pin isolation at the stops and any suspected pinch with the relevant
   connectors isolated. Record logger event-detection limits and correlate
   each dropout or short with angle and direction.
4. **Screen wear before setting a life requirement.** Run 100 slow 0–110°
   cycles, then 1,000 total if clear. These are proposed bench checkpoints.
   Record cycle rate, environment, count, and continuous electrical events.
   At 0/100/1,000 cycles record mated end-to-end resistance per wire using
   Kelvin probes, hinge endplay, operating force, guide-to-jacket witness
   movement and close-up wear photos. Stop for a pinch, jacket damage,
   wire or keeper migration, loose retention, electrical intermittency or
   insulation failure. Set the service-life target, environment and sample
   count before a qualification run. The single UV-only specimen establishes
   assembly and early wear evidence.

## PCB quote scope

For the closed-shell PC recovery trial, allow one StarTech **USB2AC1M**
USB-A to USB-C data cable and a computer USB-A host. Verify default
Type-C current on the received setup. [Docked recovery checks](../../cad/evt1-assembly/dock-harness-trial/wired-main-space-review/recovery-access/README.md)

The [wired cradle UV quote pair](../../pcb/evt1/case-telemetry-study/wired-main/uv-assembly/README.md)
uses 4.22 Ω sense resistors and the separate wired firmware profile. For that
build, use the [complete wired Main parts selection](../../pcb/evt1/case-telemetry-study/wired-main/main-order-selection.json).
It includes 200 fitted positions and 19 copper-only features, with a
40.2 kΩ Main R107. Main routing, the assembly quote for that
board and installed testing remain open.

The original [53-line PCB order worksheet](../../pcb/evt1/pcb-ordering.csv)
and five assembly ZIP manifests cover **114 purchased positions**. The
66-position [body quote](../../pcb/evt1/body/assembly-quote/body-evt1-assembly-quote.zip)
matches the retained body artwork and can be evaluated separately. Leave
JP1 open during initial charge-guard commissioning. The [four-position pogo
PCB quote](../../pcb/evt1/pins/assembly-quote/pins-evt1-assembly-quote.zip)
is a separate subassembly source. The earlier flange, compass
daughterboard and USB board quotes describe the earlier architecture.
The [routed single flange](../../pcb/evt1/single-flange-routing/assembly-quote/README.md)
and the [populated JST lid](../../pcb/evt1/dock-control/lcd-socket-candidate/assembly-bench-quote/README.md)
have separate assembly quotes. The populated lid has 28 SMT positions across
eight exact MPNs. The LCD and Main-to-lid jumper are separate parts. Establish
tail fit and numbering with the bare J302 fixture before powering the lid.

For the direct USB pass-through bench, quote the [Main bare board](../../pcb/evt1/dock-main/assembly-quote/dock-main-fabrication-quote.zip)
or [assembled Main](../../pcb/evt1/dock-main/assembly-quote/dock-main-assembly-quote.zip).
The assembled Main covers 138 purchased placements across 45 MPNs. Pair it
with the separate [UV base](../../pcb/evt1/dock-uv/base/pcb/fabrication-review/uv-base-supplier-review.zip)
and [UV lid](../../pcb/evt1/dock-uv/lid/pcb/fabrication-review/uv-lid-supplier-review.zip)
quotes at 3.65 Ω. Use the saved UV header placements for the bench order.
The [dock fit comparison](../../cad/evt1-assembly/dock-harness-trial/uv-header-review/README.md)
shows why the inward and rotated layouts were set aside. A longer liner
pocket is still in mechanical review. The [liner assembly review](../../cad/evt1-assembly/dock-harness-trial/uv-liner-assembly-review/README.md)
gives the tool candidates and the unpowered fit sequence. See the [Main quote notes](../../pcb/evt1/dock-main/assembly-quote/README.md)
for the stackup, plating, connector pattern and process requirements. Use the
[wired dock wiring sources](../../cables/evt1/dock-main/README.md) for the
current spring pins, lid flex, UV branches and remote thermal parts. The
earlier direct-pass-through GH2 switch recipes are in the UV harness folder.
Use the [wired USB plan](../../pcb/evt1/case-telemetry-study/WIRED-USB.md) for
local telemetry development. The integrated order kit also depends on
connector fit and an accepted protected pack. The
[long-lead pack feasibility packet](../../pcb/evt1/pack-lead-feasibility/README.md)
is ready to send to a pack supplier for the current loom candidate.

For J202 programming, provision one STLINK-V3MINIE, one
TC2030-CTX-NL-STDC14 no-legs cable (SKU TC2030-CTX-NL-ST14), and one pack of
TC2030-CLIP-3PACK retainers, or check the equivalent equipment already on the
bench. Confirm clearance for the clip on the bare underside of Main.
[ST probe](https://www.st.com/en/development-tools/stlink-v3minie.html) ·
[STDC14 cable](https://www.tag-connect.com/product/tc2030-ctx-nl-stdc14-for-use-with-stm32-processors-with-stlink-v3) ·
[Retaining clips](https://www.tag-connect.com/product/tc2030-retaining-clip-board-3-pack)

For the two JST GH looms, verify access to the tooling for SSHL-002T-P0.2
before buying loose terminals. JST lists WC-GH2630 for loose contacts and
YRS-1590 for strip contacts. For a short run, a crimp service can quote
the same terminals on supplied wire, with dimension and pull-test samples.
[JST tooling table](https://www.jst.com/wp-content/uploads/2025/06/eCRIMPING_MACHINES_AND_TOOLS.pdf)

Use the [USB pass-through bring-up procedure](pre-radio-bringup.md) to inspect
and program the assembled boards with both UV modules disconnected. The
procedure then defines measured power and cutoff checks under independently
qualified UV-C containment. The [dock quote compatibility check](../../pcb/evt1/case-telemetry-study/DOCK-VARIANT-CHECK.md) binds those quotes to the standard `dock-evt1` firmware and current-setting parts.
