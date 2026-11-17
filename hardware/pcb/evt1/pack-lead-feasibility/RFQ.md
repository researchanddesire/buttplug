# BC-PACK-EVT1-001 protected battery pack

Please review feasibility and quote **10 engineering samples**, including
your minimum order quantity and lead time for a repeat order. The request
covers a factory-protected 1S pack built around the EEMB LP502030HA cell.

| Item | Requested design |
| --- | --- |
| Reference cell | LP502030HA, 3.7 V nominal, 4.2 V charge. The cell's 230 mAh nominal and 200 mAh minimum figures use EEMB's 0.2C rating. |
| Finished body | 33.0 × 21.0 × 6.3 mm maximum including PCM, welded tabs, wrapper, insulation and strain relief within the body envelope. The separately shown lead exit is subject to drawing review. |
| Charge | 100 mA nominal application current. Support at least 200 mA. |
| Discharge | The complete protected pack must support 1.5 A continuous and repeated excursions to 2.0 A total output for 100 ms, with at least 1 s between pulse starts. Confirm the complete pack, wires and contacts over the intended temperature range. |
| Temperature | 0–45 °C intended operating range. Give the applicable limits for charge, discharge and storage. |
| Protection | Integrated overcharge, overdischarge, overcurrent and short-circuit protection. Proposed overcharge detection 4.25–4.33 V and overdischarge detection 2.80–3.00 V. Provide tolerances, delays, current thresholds, recovery and temperature rise at load. |
| Leads | Two insulated stranded copper 28 AWG leads, OD 0.50–0.63 mm. Factory crimp with two JST SACH-003G-P0.2 contacts into ACHTR-02V-S. Pin 1 protected P+, pin 2 protected P−. The customer supplies the opposing ACHTP-02V-S plug with two SACHP-003G-P0.2 contacts. |
| Documentation | Controlled pack drawing, complete protection data, load/temperature evidence, pack-specific UN 38.3 test summary and applicable transport documents. |

Please quote the custom protected assembly for the specified load. EEMB's
LP502030HA bare-cell specification lists maximums of 2.3 A discharge and
230 mA charge. The A25357 reference pack lists 1 A continuous discharge,
which is below this request. Identify the exact cell, protection circuit
and connector used to meet the requested load. Include only the two
protected power leads on the pack. The device builder fits the temperature
sensors. [EEMB bare-cell specification, p. 3](https://eemb.oss-accelerate.aliyuncs.com/uploads/20230902/c75cb3cfcc973ee0b427f096b4dbd894.pdf) · [EEMB A25357 reference drawing](https://www.radiomag.com.de/datasheets/A25357-LP502030HA-PCM-LD.pdf)

## Lead and exit feasibility

[Pack and proposed installed route STEP](PackLeadEnvelope.step) ·
[Route view](PackLeadInterface.png) · [JST ACH mating drawing](https://www.jst.com/wp-content/uploads/2021/03/eACH1.pdf)

The packet includes the JST drawing as `eACH1.pdf`.

The attached STEP has four geometry roots for the pack maximum body,
reconstructed socket housing and two insulated lead envelopes. It describes
the customer-side installation. Leads may ship unformed if your proposed
wire construction and strain relief allow the assembly to be dressed into
this route without damage.

All coordinates below are millimetres in the supplied STEP frame. The
pack spans X7 to 40, Y−21.5 to −15.2 and Z−10.5 to 10.5. The two wires
exit toward −X on the X7 face beside the PCM.

| ACH circuit | Polarity | Case exit XYZ | Socket rear wire datum XYZ | Installed free length |
| --- | --- | --- | --- | --- |
| 1 | Protected P+ | 7, −17.7, 7.5 | −10.9, −17.5, −1.7 | 41.79 mm |
| 2 | Protected P− | 7, −18.9, 7.5 | −10.9, −17.5, −0.5 | 42.03 mm |

The pack socket mates toward +X. The circuit row runs along Z with the
marked circuit 1 at the lower Z position. The nominal mated reconstruction
spans X−10.90 to −4.10, Y−18.40 to −16.55 and Z−3.00 to 0.80. The
STEP includes the socket only. Show the connector as viewed into the mating
face, with the molded circuit 1 mark, both wire identifiers, and both
housing wire planes in the mated section. Verify polarity at the marked
cavities on each delivered pack.

The length targets run along the insulated centerline from the X7 exit
plane to the socket's rear wire plane at X−10.90. Please propose cut and
strip lengths and a measurable finished length tolerance for each circuit
using the actual crimp seat. Dimension the case/wrapper plane, strain-relief
tip and first allowable bend point separately. Show where the free wire
starts if a sleeve or exit feature extends beyond X7. Confirm room for the
2 mm straight lead exit toward −X and the 4.0 mm installed centerline bend
radius with the actual wire and strain relief.

The enclosure's current space budget adds 1.1 mm in thickness toward −Y
and 0.25 mm on each lateral side. The wires pass through that 0.25 mm
growth region at the designated X7 exit. Please provide a section through
the actual exit and strain relief, the local growth envelope there, and
any required support/contact-pressure limit for the pouch. If you need a
different exit or larger envelope, show it in the drawing so we can check
the assembly before accepting samples.

## Quote response

| Item | Information requested |
| --- | --- |
| Configuration | Manufacturer part number and revision for the complete pack, the controlled drawing revision and any deviations from this request |
| Samples | Unit price for 10, separate tooling or NRE, sample lead time, and production MOQ and lead time |
| Optional inert fit sample | Separate price and lead time for one factory-made dummy using an inert body, actual wrapper and strain relief, representative PCM/lead-exit envelope, and the quoted two leads and ACH socket. Use the same mechanical drawing as the pack. Identify any differences in thickness, stiffness, end details or lead form. This sample should contain no electrochemical cell or stored energy. |
| Protection and load | Minimum/maximum protection thresholds and delays, connector voltage drop, temperature rise, loaded terminal voltage and usable capacity to the applicable cutoff. State the ambient temperature, starting state of charge and load profile for each result. Include charger-assisted recovery from undervoltage. |
| Mechanical | Maximum wrapped body and exit dimensions, dimensioned exit section with the first allowable bend and both lead-length datums, minimum/maximum finished lead lengths, applicable crimp pull-force limit, and an oriented mating-face view with both circuit numbers |
| Handling | Permitted pouch support and contact pressure, growth allowance, and exact-pack transport documentation |

We will review the drawing and tolerances before ordering the fit sample or
protected packs. If the dummy is available separately, please quote its
delivery before the 10-pack lot.

[EEMB LP502030HA cell](https://www.eemb.com/product-248) ·
[JST ACH series](https://www.jst-mfg.com/product/pdf/eng/eACH1.pdf)
