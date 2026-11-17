# Four-contact bench record

| Setup | Record |
| --- | --- |
| Specimen and revision | Date, operator, Git commit, carrier/retainer revision, both PCB revisions, and bare or overmolded target specimen ID |
| Received parts | Pogo, target, magnet, steel keeper and spring lots. Record the print process, finished board thickness, four finished CT1–CT4 plated diameters, keeper dimensions and magnet polarity. |
| Fixtures | Force gauge ID and zero check, measured seating datum, data lead length, bench source and firmware build hashes |

Use the pin shoulder's PCB seating plane as the common height datum.
Measure each pin's unloaded tip height and the location of its target face
with the flange seated. Where the tip is inaccessible, transfer the seated
target position through the measured stop ring and record the gauge setup.
Compare the difference with the usable pin stroke. A pin bottoming out or
a target missing its stop ring ends the seating test for that sample. The
model uses 0.60 mm travel. The pin's nominal midstroke is 0.699 mm and its
catalog maximum travel is 1.397 mm nominal. Ask Mill-Max for the exact
part's stroke tolerance or measure the available travel on the received
lot with a controlled fixture before setting an acceptance limit. The
1.270 mm value in the exchange report is a screening assumption. Establish
minimum reliable electrical travel by measuring resistance and interruptions
during loading and at the seated pose.
[Mill-Max 0906-2 data sheet](https://static6.arrow.com/aropdfconversion/adfa1bc04697174a4358693f99b5c90949307da3/0906-2-15-20-75-14-11-0.pdf)

Copy the four pre-cast flat-face measurements from the
[mold-stop worksheet](../../../cad/manufacturing-layout/overmold-interface-review/rear-insert-candidate/measurement-review/README.md).
Repeat the face and dry-side seating checks after demolding. Measure when
each ring first touches, then confirm all rings bear on exposed head metal
and the carrier still clears the skin. Record any gaps, tilt or flash that
change where the plug stops.

| Position | Signal | Dock X/Z (mm) | Free height (mm) | Travel (mm) | Target fully on ring? | Continuity through disturbance |
| --- | --- | --- | --- | --- | --- | --- |
| P91 / CT1 | GND | −16 / 42 | | | | |
| P92 / CT2 | D− | −10 / 42 | | | | |
| P93 / CT3 | D+ | −4 / 42 | | | | |
| P94 / CT4 | 5 V | +2 / 42 | | | | |

With the boards isolated and unpowered, record the open-circuit readings for
1–2, 1–3, 1–4, 2–3, 2–4 and 3–4. Record the meter range and test-lead
zero separately from contact readings.

| Force setup | Gap or seated pose | Peak force (N) | Notes |
| --- | --- | --- | --- |
| Each magnet and keeper pair | Nominal 2.70 mm and measured gap range | | Record the actual gap including material between faces. |
| Complete article, both magnets | Stop-ring seated pose | | Pull along the intended disengagement slide and record that direction. |
| Complete article, each magnet separately | Same pose and pull direction | | Record which magnet is installed. |
| Complete article, magnets removed | Approach to the same seated pose | | Record the force opposing seating from the four pogo pins. |

After the dry measurements, leave UV disconnected and follow the
[direct PC and Pico sequence](README.md#assemble-and-measure). Record
contact voltage at the plug, enumerations and failures by trial, visible
disconnects under disturbance, ROM recovery outcome and a capture filename.
If a fit issue changes the contact travel or force, include a photo showing
the affected stop and the seated orientation. Enter physical results in the
Compass review log with the exact tested revisions.
