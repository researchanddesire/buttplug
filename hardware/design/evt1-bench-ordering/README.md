# EVT1 bench samples and PCB quotes

These quantities cover two bench trials. Confirm exact part, pack quantity,
availability and lead time at ordering. Obtain small-quantity samples or cut
tape where offered. Keep the two trials separate from the full-device order.

| Part | Proposed sample quantity | Bench use |
| --- | ---: | --- |
| ifm **E10028** | 3 packs × 2 nuts | Incoming dimensional checks and six fresh M18×1 joints. 316Ti stainless, nominal 24 mm AF × 4 mm. Verify how the distributor counts packs. [ifm Canada](https://www.ifm.com/ca/en/product/E10028) · [DigiKey 2330-E10028-ND](https://www.digikey.ca/en/products/detail/ifm-efector-inc/E10028/17866905) · [drawing and model record](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/selection.json) |
| Henkel **LOCTITE 243**, IDH **1330799**, 6 mL tube | 1 | Medium-strength threadlocker candidate for inert torque/cure trials. [Henkel Canada](https://next.henkel-adhesives.com/ca/en/products/industrial-adhesives/central-pdp.html/loctite-243/BP000000316211/variation/1330799.html) |
| Vishay **NTCLE413E2103F524A** | 4 | Two dry pack sensors for the fit gauge and two spares. [Vishay 29078](https://www.vishay.com/docs/29078/ntcle413.pdf) · [DigiKey listing](https://www.digikey.ca/en/products/detail/vishay-beyschlag-draloric-bc-components/NTCLE413E2103F524A/16530174) · [pack specification](../../pcb/evt1/pack-spec.json) |
| 3M **5413**, part **7000050064** | 1 roll | 6.35 mm tape for the pack sensor head and lead coupons. [3M part](https://www.3m.com/3M/en_US/p/dc/v000091658/) · [DigiKey roll](https://www.digikey.ca/en/products/detail/3m/5413-AMBER-1-4-IN-X-36-Y/1819260) · [cut blanks](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/parts-and-cut-stock.json) |
| Newhaven **NHD-C12864B2Z-RN-FBW** | 2 | Reflective 128×64 LCD with integral 27-way flex. One for repeated fit checks, one for comparison and subsequent powered bring-up. [Newhaven product](https://newhavendisplay.com/128x64-graphic-cog-lcd-fstn-display-with-no-backlight/) · [DigiKey listing](https://www.digikey.ca/en/products/detail/newhaven-display-intl/NHD-C12864B2Z-RN-FBW/1885690) · [display geometry record](../../cad/evt1-assembly/vendor/display/source-manifest.json) |
| JST **27FLZ-RSM2-TB (LF)(SN)** | 5 | Bottom-contact socket samples for measurement, reflow and spares. [Newhaven listing](https://newhavendisplay.com/27-pin-surface-mount-right-angle-connector-with-0-5-mm-pitch/) · [DigiKey cut tape](https://www.digikey.ca/en/products/detail/jst-sales-america-inc/27FLZ-RSM2-TB/1634721) · [JST FLZ catalog](https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf) · [geometry record](../../cad/evt1-assembly/vendor/lcd-socket-replacement/provenance.json) |
| Molex **0150200966** | 2 | Passive 51 mm, 27-lane, 0.50 mm pitch test tail for the two breakouts. Measure the received mating ends for the JST width and thickness limits. [Molex part](https://www.molex.com/en-us/products/part-detail/150200966) · [DigiKey listing](https://www.digikey.ca/en/products/detail/molex/0150200966/2972888) |
| Molex **0151660220** | 2 | 203 mm, 20-way, 0.50 mm pitch, opposite-face jumper for the Main-to-lid bench connection. Map both ends before powering the populated lid. [Molex part](https://www.molex.com/en-us/products/part-detail/0151660220) |
| Molex **52437-2771** | 2, optional | Comparison with the saved Molex lid and its original footprint. [Molex 524372771](https://www.molex.com/en-us/products/part-detail/524372771) · [saved Molex fit study](../../cad/evt1-assembly/vendor/lcd-socket-replacement/negative-molex/review.json) |
| Rogers **4790-92-09030-04 P**, product **3036884** | 1 small sample sheet | Cut four 1.2 × 22 mm face pads per fixture, plus spares. Request a sample cut of the exact PET-supported grade. [LCD retention material record](../../cad/evt1-assembly/lcd-retention-trial/source-manifest.json) |
| CS Hyde **48-2F-1-100** | 1 roll | Plain 0.0508 mm nominal PET for registered glass-pad shims and four equal PCB shim stacks. [CS Hyde item](https://cshyde.com/item/ecific-optically-clear-transparent-films-1/mylar-polyester-pet-film/2mil-mylar-1in-100ft) · [cut profiles](../../cad/evt1-assembly/lcd-retention-trial/cut-patterns-1to1.svg) |
| NBK **SNSS-M2-6** | 1 pack of 10 | Four existing-design screws for the LCD retention coupon. Gauge the four separate PCB fixture screw seats and underside access during setup. [NBK part](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/socketheadcapscrew/SNSS/SNSS-M2/SNSS-M2-6/) · [coupon parts](../../cad/evt1-assembly/lcd-retention-trial/assembly-parts.json) |

## Rear joint trial

Use the [saved two-jaw driver](../../cad/manufacturing-layout/evt1-integration/rear-joint-trial/TwoJawDriver.step)
as the starting model for a machinist-reviewed steel tool. Verify driver
material, jaw strength and access with a torque transducer. Prepare six inert
stub/tray pairs from the [metal body](../../cad/manufacturing-layout/MetalBody.step)
and [single-board tray](../../cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/Tray.step)
datums. A shortened stub coupon needs the full thread, shoulder, key, pad and
nut/driver access geometry. Choose the body alloy and finish, print process
and material for the trial before commissioning coupons. Use the intended
production material and finish when qualifying torque. Fixture a dummy pack
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

## Display trial

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

## PCB quote scope

The original [53-line PCB order worksheet](../../pcb/evt1/pcb-ordering.csv)
and five assembly ZIP manifests cover **114 purchased positions**. The
66-position [body quote](../../pcb/evt1/body/assembly-quote/body-evt1-assembly-quote.zip)
matches the retained body artwork and can be evaluated separately. Leave
JP1 open during initial charge-guard commissioning. The four-position pogo
PCB quote is a separate subassembly source. The earlier flange, compass
daughterboard and USB board quotes describe the earlier architecture.
The [routed single flange](../../pcb/evt1/single-flange-routing/assembly-quote/README.md)
and the [populated JST lid](../../pcb/evt1/dock-control/lcd-socket-candidate/assembly-bench-quote/README.md)
have separate assembly quotes. The populated lid has 28 SMT positions across
eight exact MPNs. The LCD and Main-to-lid jumper are separate parts. Establish
tail fit and numbering with the bare J302 fixture before powering the lid.

For the pre-radio dock bench, quote the [Main bare board](../../pcb/evt1/dock-main/assembly-quote/dock-main-fabrication-quote.zip)
or [assembled Main](../../pcb/evt1/dock-main/assembly-quote/dock-main-assembly-quote.zip).
The assembled Main covers 138 purchased placements across 45 MPNs. Pair it
with the separate [UV base](../../pcb/evt1/dock-uv/base/pcb/fabrication-review/uv-base-supplier-review.zip)
and [UV lid](../../pcb/evt1/dock-uv/lid/pcb/fabrication-review/uv-lid-supplier-review.zip)
quotes at 3.65 Ω. See the [Main quote notes](../../pcb/evt1/dock-main/assembly-quote/README.md)
for the stackup, plating, connector pattern and process requirements. The
proposed radio circuit uses a different UV resistor pair and has no routed
order package yet. The integrated order kit still depends on connector fit
and the accepted [protected pack](../../pcb/evt1/PACK-RFQ.md).
