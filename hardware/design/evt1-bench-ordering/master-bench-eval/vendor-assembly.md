# Vendor assembly operations for the Compass evaluation

Quote both sides and supply fully populated PCBAs. Order each design with its
own Gerber ZIP, `jlc-bom.csv`, `jlc-cpl.csv` and `cam-request.txt`. Select
Standard assembly. The BOM lists the exact selected parts, with custom
contact and pigtail operations below. Return written acceptance and photos
before moving on from an assembly quote. Pin 1 marks, polarity and loaded
orientation need review in the vendor's placement viewer.

| Board | Operation to include in the quote |
| --- | --- |
| Both | Fit the specified MPNs. R21/R43 use the [RESI PTFR0805 land pattern](https://s.resistor.today/shop/products/epdf/PTFR.pdf#page=2): 4.00 mm overall span, 1.65 mm width and 1.20 mm gap. Keep C12/C22 unpopulated and JP1 open. Leave all test pads, mounting holes and the antenna keepout free of added parts. |
| Master Bench | Fit J111/J112/J120/J121/J122/J124/J125 through-hole headers (7 positions in the BOM and CPL). For J110 USB-C, solder all 16 SMT contacts and the four plated shell tabs. Confirm the slots, locating holes and the pin-1 orientation of both shrouded headers. Include two assembled J112 selector keys per bench station, one **PC** and one **DOCK**, as a separate cable shop line. Ship three 2.54 mm two-pin rail shunts loose; confirm their rating for each bench supply limit. |
| Compact | Fixture and solder four Mill-Max **1946-0-00-15-00-00-03-0** targets at CT1–CT4 after SMT. Seat all four shoulders square to the board and keep the contact faces free of solder and flux. Request two loose spares per prototype lot. Gauge finished holes for the specified contact fit (≥0.9144 mm); confirm the upper range/retention and shoulder seating on a sample. No substitution of heads or tails. |
| Both, J2 | Quote vendor soldering of the board-side pigtails after SMT. J2 is five bare copper lands, with no fitted header. Supply the boards with detached, terminated harness ends and no battery installed. Quote the simulator leads and real pack harness as separate detachable assemblies. |

If the standard portal cannot include an operation, price that work at the
same assembly vendor or a separate harness/box-build shop before ordering
assembled boards. An SMT quote alone does not include J2 or CT1–CT4.

## J2 pigtail joint map

Native KiCad XY coordinates are in mm, with positive Y downward in the top
view. B.Cu coordinates are given in the same board coordinate system. Inspect
the small 2P pad from the correct side. Never repurpose either GND land as
battery positive.

| Land | Function | Compact B.Cu XY | Master Bench F.Cu XY |
| --- | --- | --- | --- |
| 1 | Pack/simulator positive | 100.25, 105.00 | 98.015, 122.25 |
| 2P | Pack/simulator return, 0.50 × 0.50 mm | 101.10, 104.785 | 97.80, 123.10 |
| 2S | Separate charger/guard thermistor returns, 0.60 × 1.00 mm | 101.75, 105.00 | 98.015, 123.75 |
| 3 | TH1 charger NTC signal | 103.25, 105.00 | 98.015, 125.25 |
| 4 | TH2 independent hardware guard NTC signal | 104.75, 105.00 | 98.015, 126.75 |

For compact production-intent pigtails, follow the two-pin JST ACH polarity
used by the [existing pack loom](../../../cables/evt1/pack-evt1.yml): pin 1
positive, pin 2 return. Use separate sensor returns over the loom to 2S.
Limit pigtail bulk and heat-shrink to the dry cavity envelope; fit with the
inert pack before cutting the final lengths. On the Master Bench only, J124
can supply both simulator resistances, so keep J2.2S/3/4 empty on a
simulator-only lead set. Disconnect any actual sensors before substituting.
Inspect solder joints and provide independent restraint and continuity and
adjacent-net isolation results. The power and NTC returns share PCB GND.

## USB host feed at J111

J111 is JST **B4B-PH-K(LF)(SN)**. Quote the detachable **PHR-4** / four
**SPH-002T-P0.5S** contacts for the supplier-made lab cable. From J111.1–4,
wire GND, D−, D+, protected 5 V respectively. Use 28 AWG stranded Alpha Wire
3048 (Ø1.19 mm nominal) with D−/D+ matched and paired. Start with ≤150 mm and
add strain relief at the host; maintain 12 mm bend radius and verify egress.
[JST PH drawing](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf) ·
[Wire dimensions](https://www.alphawire.com/products/wire/hook-up-wire/premium/3048)
On a wired Main used in the eventual bench test, map
J111.1–4 1:1 to **J102.1–4** instead of the installed pogo board. Never tee
the output or drive an already powered host VBUS from another source.
For the Pico fixture, use its isolated data feed and separate contact supply.

The shop must prove cavity numbering and all four connections rather than
relying on wire colors. For receiving inspection, sample the finished
through-hole plugs for fit, mating orientation and strain relief.
