# EVT1 protected battery request

Request samples of **BC-PACK-EVT1-001**, a factory-built protected 1S pack using
the EEMB LP502030HA high-rate cell. The editable requirements are in
`pack-spec.json`. This is a request ready for supplier review; it has not been
submitted or accepted.

| Requirement | Request |
| --- | --- |
| Capacity / voltage | 230 mAh nominal, at least 200 mAh; 3.7 V nominal, 4.2 V charge |
| Charge | Device sets about 100 mA; pack must support at least 200 mA |
| Discharge | At least 1.5 A continuous; 2.0 A for 100 ms, no faster than once per second |
| Finished maximum | 33.0 × 21.0 × 6.3 mm including cell, PCM, tabs and insulation |
| Output | Factory-terminated AWG28 stranded leads, insulation OD0.50–0.63mm; JST ACHTR-02V-S socket with two SACH-003G-P0.2 contacts; pin1 protectedP+,pin2 protectedP− |
| Lead exit | NegativeX short end beside PCM; requested centres(7,−17.7,7.5)/(7,−18.9,7.5)mm in product frame; provide controlled drawing/strain relief |
| Protection | Integrated overcharge, overdischarge, overcurrent and short-circuit protection; provide actual limits/delays, thermal and recovery data |
| Normal environment | 0–45 °C; sealed-device heat and actual application profile require review |

The [EEMB cell specification](https://www.eemb.com/product-248) supports the
high-rate starting point. EEMB drawing A25357 for LP502030HA-PCM-LD is a useful
construction/size reference, but its published **1 A continuous** rating is
below this request. Do not substitute that standard pack without revising and
revalidating the complete load budget. Please confirm the exact orderable
variant and provide a controlled drawing and cell/pack transport documentation.

The flange CAD reserves an additional 1.1 mm thickness and 0.25 mm lateral
clearance per side for growth. Please state the necessary growth allowance,
support/contact-pressure limits, life and storage recommendations. This space
reservation is not an assumed manufacturer swelling limit.

Two separately purchased Vishay NTCLE413E2103F524A sensors are tape-coupled to
the pack in the device assembly. The supplier may propose factory mounting
after reviewing the head positions and dry cavity. Preserve four independent
sensor leads in addition to the two protected power leads. The sensors must
not contact casting silicone, liquid or hard potting.

Provide sample price/quantity/lead time, exact PCM current and thermal limits,
short/overcurrent thresholds and delays, low-voltage recovery behavior and
finished dimensions including wire exits. Approval of a changed cell, PCM,
lead layout or larger envelope requires another electrical/CAD review.

The battery must disconnect inside the flange: the cap/body-PCB module threads
with free tails before the pack is connected. The compact
[JST ACH wire-to-wire](https://www.jst-mfg.com/product/pdf/eng/eACH1.pdf)
has a2A catalog rating with AWG28/30 and0.50–0.63mm insulation. This is not a
sealed-device current/thermal qualification; include the requested load and
lead/connector drop in the factory review. The body-side mate is ACHTP-02V-S
with SACHP-003G-P0.2 contacts. Do not substitute SH contacts or crimp26AWG into
the smaller ACH contact.

The mated CAD budget is2.1×4.0×7.0mm, long axisZ, bounds
X0.95..3.05/Y−20.3..−16.3/Z−4.5..2.5. Pack wires enter from+Z at(2,−17.7,2.5)
and(2,−18.9,2.5); verify marked circuit numbers and actual continuity. Each
wire has a1mm straight exit,4mm centreline quarter-bend and1mm straight at
the housing:8.283mm exposed insulated path, target±0.5mm. This is a finished
path between case/housing datums, not a raw cut length; supplier must derive
cut/strip from the actual crimp seat. Confirm this formed exit is feasible
before accepting a quote. The standard100mm tinned26AWG construction is not
the requested EVT termination. Keep the socket protected during handling.
