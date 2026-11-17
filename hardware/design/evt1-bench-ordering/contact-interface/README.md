# Four-contact cradle first article

The [mechanical quote packet](Compass-EVT1-Contact-Fit-Quote.zip) combines
the two printed parts, six machined steel keeper samples and the
[shop instructions](CONTACT-RFQ.md). Board quotes and loose hardware are
listed below for separate purchase.

Print the [carrier](ContactCarrier.step) and [rear retainer](ContactRetainer.step)
in MJF PA12 or SLA. The STEP surfaces match the active wired product dock.
The [editable carrier and hardware](../../../cad/evt1-assembly/recentered-carrier-trial/RecenteredCarrierTrial.FCStd)
use the relative `../pcb/PinPCB.FCStd` link. The two supplier STEP files were
reimported and checked against both the product dock and the editable carrier.
The [exchange report](exchange-check.json) ties the four stop faces to the
seated target and spring-pin shapes and verifies the current PCB quotes.
To replay the check, run `check_interface.py <output-directory>` with
FreeCAD's Python. It reads the saved assembly and reimports both supplier
STEP files.

| Item | One article | Quote and inspection notes |
| --- | ---: | --- |
| Carrier and retainer | 1 each | Ask for measured pin bores, the four stop faces and the PCB recess. Inspect the 0.5 mm local web and the Ø2.4/1.8 mm stop rings for damage and process residue. Do not sand the stop faces to fit. |
| Pogo PCB, 1.00 mm FR4 ENIG | 1 | Ask for separate prices for the bare PCB and fixture soldering in the [pin assembly quote](../../../pcb/evt1/pins/assembly-quote/pins-evt1-assembly-quote.zip). If the shop only handles SMT, buy the [bare PCB](../../../pcb/evt1/pins/fabrication-quote/pins-evt1-fabrication-quote.zip) with loose pins. For P91–P94, ask for the guaranteed finished range, with a minimum of Ø0.5842 mm using the Mill-Max general tail tolerance. The nominal artwork is Ø0.600 mm. |
| Mill-Max **0906-2-15-20-75-14-11-0** | 4 installed + 2 spares | Allow two loose spares if buying the assembly, or six loose pins if soldering in-house. Solder with shoulders seated and measure unloaded tip height from the same PCB plane, nominal 5.0038 mm. Full stroke is nominally 1.397 mm. [Mill-Max data sheet](https://static6.arrow.com/aropdfconversion/adfa1bc04697174a4358693f99b5c90949307da3/0906-2-15-20-75-14-11-0.pdf) · [DigiKey ED8182-ND](https://www.digikey.ca/en/products/detail/mill-max-manufacturing-corp/0906-2-15-20-75-14-11-0/1147050) |
| Mill-Max **1946-0-00-15-00-00-03-0** | 4 installed + 2 spares | Solder separately after SMT on the [single flange quote](../../../pcb/evt1/single-flange-routing/assembly-quote/README.md). Add four more for each fitted bare gauge board. The artwork specifies Ø1.02 mm nominal for the four plated holes. Confirm the finished range using the quote's CAM note, then inspect the seated heads for tilt and flash. [Mill-Max 1946 drawing](https://www.mill-max.com/sites/default/files/external/catalog/2020-01/202-246_3.pdf) · [DigiKey ED1360-ND](https://www.digikey.ca/en/products/detail/mill-max-manufacturing-corp/1946-0-00-15-00-00-03-0/5176096) |
| supermagnete **S-08-03-N** | 2 installed + 2 spares | Ø8 × 3 mm ±0.1 mm, axial N45, Ni-Cu-Ni plated. Supermagnete sells them in packs of 10 and limits direct deliveries to Europe. Confirm a source that delivers to the bench address. [Exact magnet](https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-8mm-3mm_S-08-03-N) · [Delivery limits](https://www.supermagnete.de/eng/faq/Questions-and-answers-about-shipping-delivery) |
| Lee Spring **LC014B02S** | 2 installed + 2 shared spares | The saved bearing faces set 3.80 mm installed length. The catalog lists 7.95 mm free length, 1.96 mm solid height and 0.666 N/mm. At the nominal seat the estimate is 2.76 N per coil, with 1.84 mm to catalog solid height. Measure spring seating and retainer loads. Count the pair and its spares in the dock total if reusing this module. [Dock spring order and vendor source](../README.md#dock-button-and-contact-springs) |
| Accu **SIK-M3-12-A2**, NBK **SNSS-M2-6** | 2 each | PH1 drives the M3 carrier screws from underneath. A 1.50 mm hex drives the M2 retainer screws before installation. Accu lists one M3 per pack and NBK lists ten M2 per pack. Confirm printed pilot, depth, thread preparation and a usable tightening limit on a spare or printed witness. [Accu M3](https://www.accu.co.uk/phillips-countersunk-screws/65913-SIK-M3-12-A2) · [NBK M2](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/socketheadcapscrew/SNSS/SNSS-M2/SNSS-M2-6/?SelectedLanguage=en-US) |
| Accu-Glass **100690** | Four 150 mm starting blanks + scrap | Hand-solder the [J102–J94 loom](../../../cables/evt1/dock-main/README.md#main-to-spring-pin-board). Keep the USB pair together, mark both ends and trim to the measured installed route. |
| Breyden **205-3 LOG** lacing tape | 150 mm starting sample | Candidate for the two 2 × 2.2 mm native slots. The flat tape is 1.14–1.40 mm wide before knotting. Check knot placement, bundle restraint and the retainer closing path on the dry article. [Breyden dimensions](https://www.breydenproducts.com/shop/aerospace-low-outgassing-tapes/205-3-log) |

The [inert screw-closed flange trial](../../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/SCREW-WITNESS.md)
supplies the device-side overmold witness. Retention measurements need both
buried keepers at the saved position. The [keeper sample quote](keeper-samples/README.md)
specifies six Ø8 × 1 mm SAE 1018 discs for the bench and includes the checked
STEP. Record the received grade and measure force before selecting the
production keeper.

If the selected magnets cannot be sourced locally, ALB Materials
**D8x3mm-N45** is a quote alternative with the same published size, dimensional
tolerance, grade and axial magnetization. Its public listing says nickel
plated. Ask for the coating stack, lot data, small-quantity availability and
Canadian delivery before selecting it. ALB lists a US$300 inquiry minimum.
Measure magnet dimensions, poles and holding force against the received
keeper at the actual gap before accepting any supplier change.
[ALB product drawing and specifications](https://www.albmaterials.com/disc-magnets/6690-neodymium-disc-magnets-nd45-3111n.html) · [ALB order minimum](https://www.albmaterials.com/contact-us)

Use the Y15.40 mm retainer face and Y19.20 mm magnet rear face as the spring
datums. The reconstructed coil extends about 0.18 mm beyond the magnet
plane because it has approximate ends. The bearing faces determine the
nominal installed length.

## Assemble and measure

Use the [measurement record](MEASUREMENTS.md) for the four positions,
isolation checks, pull-off force and USB observations.

1. With everything unpowered, seat the four pogos, solder J94 and pass
   the marked loom through the rear lacing before trapping the pin board
   under the retainer. Assemble the two magnets and springs against their
   seats and close the retainer outside the case. Hold the retainer square
   during closure. Check the solder fillets, board lift and pin return.
2. Using the physical dock frame, align P91/CT1 through P94/CT4 at
   X −16/−10/−4/+2 mm, Z 42 mm, in the order GND / D− / D+ / 5 V.
   The target faces stop at Y 23.20 mm. Lower the flange at the existing
   +3 mm offset and slide toward the stops. If evaluating outside the case,
   support the device and carrier at the same relative position with a
   rigid bench fixture. Do not use the pins to support or lever the parts.
3. Measure free height and travel at all four stations and record whether
   each target lands fully on its ring, without rocking. Nominal travel is
   0.60 mm. CAD has a 0.30 mm hard clearance from carrier to silicone.
   The component-only screen gives 0.194–0.752 mm if the first planar target
   to touch sets seating and the target height spread reaches 0.254 mm.
   Board, print, mask, angular error and deformation still need measurement.
   Check total seating/pull-off force at the actual gap, repeat with each magnet
   omitted to diagnose a weak side, and log any intermittent contact.
   Check pin-to-target continuity and all six adjacent or cross-row pairs
   for shorts with the boards isolated. Gauge both bare pads and final
   overmolded heads, including any silicone flash above the contact plane.
4. With the emitters disconnected, use the protected 5 V feed and the
   [direct PC bench](../pre-radio-bringup.md) to verify USB enumeration,
   console, flashing, attach/disconnect and voltage drop through the
   contact stack. Reuse the same contact stack with the
   [Pico USB host fixture](standalone-usb.md)
   for standalone telemetry. Keep the data hosts isolated from one another.
   The integrated owner switch has its own
   [wired Main bring-up](../../../../dock-firmware/wired-main/BRINGUP.md).

The carrier covers both plug buttons when seated. A straight Ø3 mm tool
aimed at either button from the rear crosses the lower shell, liner,
carrier and retainer in the saved CAD. A normal USB update and manual
ROM entry are separate checks. Use the [ROM-entry sequence and power
cases](../../../cad/evt1-assembly/dock-harness-trial/wired-main-space-review/recovery-access/README.md#verify-with-a-seated-plug).
Record receipt and fit, contact/force measurements and captures against the
exact part and board revisions. This is a contact-module build packet.
Installed strain relief, full-dock fit, sealing and compass checks remain
open.
