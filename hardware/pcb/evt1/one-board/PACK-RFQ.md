# One-board protected battery request

Request samples of **BC-PACK-EVT1-002**: a factory-built protected 1S
high-rate LiPo pack with its own 10 kΩ NTC and three leads ending in a JST SH
3-pin plug. The editable requirements are in [pack-spec.json](pack-spec.json).
This request has not been submitted, and no supplier has accepted it.

It replaces BC-PACK-EVT1-001 for the one-board device. That earlier pack had
two leads, a JST ACH disconnect and two separately bought thermistors taped to
the cell. Its RFQ stays in `../PACK-RFQ.md` as the two-board EVT1 record.

## Why three wires

The pack's own NTC is the device's only battery temperature sensor:

- **Hardware charge cutoff:** it drives the BQ24074 charger's TS pin. The
  charger biases it with about 75 µA and stops charging above 0.3 V (hot) or
  2.1 V (cold). With the curve below that is about 0 °C to 51 °C, with no
  firmware involved.
- **Firmware reading:** the firmware reads the same node on the ADS1115 (U7
  AIN2, through R88 and C88), on and off the dock.

So the NTC has to sit on the cell, use a known curve, and return to the pack's
protected negative.

## Requirements

| Item | Request |
| --- | --- |
| Cell | EEMB LP502030HA high-rate class, or equivalent |
| Capacity, voltage | 230 mAh nominal, at least 200 mAh; 3.7 V nominal, 4.2 V charge |
| Charge | Device charges at about 100 mA; the pack must accept at least 200 mA |
| Discharge | At least 1.5 A continuous; 2.0 A for 100 ms, at most once per second |
| Finished size | 33.0 × 21.0 × 6.3 mm maximum, including cell, PCM, tabs and wrap |
| Protection | Integrated overcharge, overdischarge, overcurrent and short-circuit protection |
| NTC | 10 kΩ ±1 % at 25 °C, B25/85 = 3435 K ±1 % (103AT-2 class) |
| NTC mounting | Bonded to the cell's broad face under the wrap, away from the PCM |
| NTC wiring | Between the NTC lead and P− (protected output negative), not cell B−; not shared with the PCM |
| Leads | Three, from the PCM short end: red P+, black P− (AWG 28), white or yellow NTC (AWG 28 or 30) |
| Lead length | At least 90 mm from the pack case to the back of the plug |
| Plug | JST SHR-03V-S housing, SSH-003T-P0.2-H contacts crimped with JST tooling |
| Pinout | Pin 1 P+, pin 2 P−, pin 3 NTC (mandatory; mates with the board's JST SM03B-SRSS-TB) |
| Environment | 0–45 °C in normal use |

The EEMB LP502030-PCM-NTC-LD shows the wanted size and 3-wire construction.
Its continuous rating must be checked against the 1.5 A request before it is
offered. Please give the exact orderable part, a controlled drawing showing the
NTC position, its wiring and the plug pinout, and the protection thresholds,
delays and recovery behaviour. Include sample price, quantity, lead time and
transport documents (UN 38.3 summary).

## Assembly

The cap and body module threads into place with the pack leads free. The pack
is then plugged into J2 on the board. Nobody solders the pack. There is no
polarity standard for 3-pin battery plugs, so check every sample's pinout with
a meter before its first mate.

## Open before ordering

- **Connector current.** JST SH contacts are rated 1 A, below the 1.5 A
  continuous request carried over from BC-PACK-EVT1-001. Measure the real
  continuous battery current with the motor running and the radio active. If
  it can exceed 1 A, J2 and this plug need a higher-rated connector that still
  fits the 4 mm cavity behind the board.
- **NTC confirmation.** The supplier's drawing must confirm the NTC part, its
  curve, where it is bonded and that it returns to P−.

Sources: [EEMB LP502030](https://www.eemb.com/product-248),
[JST SH](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf),
[TI BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf).
