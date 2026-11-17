# Bench USB host keys

Make one **PC** key and one **DOCK** key for each bench kit. Deliver fully crimped, loaded, dressed and continuity-tested. J112 is the board-mounted JST B10B-PHDSS(LF)(SN), a shrouded 10-way PHD header on a 2.00 mm grid. One stock polarized housing occupies the socket at a time. With the socket empty, the three common power and data contacts are open. An empty housing marked **OFF** may be supplied as a dust cover. [JST PHD connector and drawings](https://www.jst-mfg.com/product/index.php?lang=2&series=201)

## Cavity layout

The diagram looks down on the installed board, with the board's USB-C and dock connectors above J112. Use the JST cavity identifiers when loading contacts. The drawing and wire-entry views of a loose housing look different when the housing is turned over.

```text
                 J112 top view, F.Cu
             toward J110 and J111 edge

 Pin 1 cue →     1     3     5     7     9
                 2     4     6     8    10

       DEVICE = common side toward the circuit
```

| Pin | Function | Pin | Function |
| --- | --- | --- | --- |
| 1 | PC D− | 2 | Device D− |
| 3 | PC D+ | 4 | Device D+ |
| 5 | Board ground, empty cavity in both keys | 6 | Dock D− |
| 7 | PC 5 V | 8 | Dock D+ |
| 9 | Dock 5 V | 10 | Device 5 V |

| Key label | White D− loop | Green D+ loop | Red 5 V loop | Empty cavities |
| --- | --- | --- | --- | --- |
| **PC** | 1 ↔ 2 | 3 ↔ 4 | 7 ↔ 10 | 5, 6, 8, 9 |
| **DOCK** | 6 ↔ 2 | 8 ↔ 4 | 9 ↔ 10 | 1, 3, 5, 7 |
| **OFF** optional | Open | Open | Open | 1–10 |

## Harness parts and workmanship

| Item | Per PC or DOCK key |
| --- | ---: |
| JST PHDR-10VS, natural polarized housing | 1 |
| JST SPHD-002T-P0.5, genuine tin crimp contact | 6 |
| Alpha Wire 3049 white, green and red, 26 AWG 7/34 tinned copper with 1.30 mm nominal PVC OD | 1 length of each color |
| Durable label readable when installed | 1 |

Cut each wire to **34 ±1 mm** before stripping. Match the two data wires within **0.5 mm** per key. Keep the white and green wires adjacent along both sides of the loops and dress the red wire outside that pair. Form the loops without sharp folds, bare conductor outside the crimp or tension at the terminal backs. Use the manufacturer's crimp tooling and inspect conductor and insulation crimps separately. Verify that each contact locks into its cavity and the installed key can be lifted by its housing. [JST terminal drawing and manual](https://www.jst-mfg.com/product/index.php?lang=2&series=201) · [Alpha Wire 3049](https://www.alphawire.com/en/products/wire/hook-up-wire/premium/3049)

The board footprint uses 0.75 mm nominal plated drill artwork on 1.20 mm pads. Confirm the fabricator's finished hole size and the assembler's insertion and solder process for the exact header. Check mating and removal with the received header before closing any fixture. The stock header's body is 11.9 × 5.0 mm with a 6.5 mm height above the board. The closest checked top-side courtyard is J111, with a 0.77 mm nominal gap. Allow 25 mm above the board for the dressed harness and a clear vertical path to remove it. [JST PHD dimensions](https://www.jst.fr/core/file.get?path=doc%2Fjst%2Ffamily%2Fpdf%2FePHD.pdf) · [Native drill and courtyard check](host-key-geometry.json)

## Acceptance

1. With each key unmated and fixtures zeroed, verify ≤0.20 Ω across each specified loop. Verify ≥10 MΩ at 5 V on every other cavity pair. An **OFF** key has all cavities empty.
2. With the board, USB leads and battery deenergized, check J112's pin-1 orientation and verify the same three paths and the inactive host's open VBUS/D−/D+ through the installed key. Connector grounds are common on the board in every mode.
3. Use **PC** for direct programming at J110 and **DOCK** for the external dock interface at J111. The dock selects its own local host or PC pass-through. Use one host and remove both host power sources and the battery or simulator before swapping keys.
4. Check 12 Mb/s enumeration, repeated transfers and ROM recovery in both J110 cable orientations and both J111 dock modes. The selected approach has no added via transitions. Board data legs from J111 to J112 measure 15.54 mm and 14.87 mm. The J110 pair has as much as 6.30 mm of planar route mismatch before the key, so both cable orientations need bench verification. [Native route evidence](routing-status.json)

[Native PCB, schematic and key continuity audit](host-key-contract.json)
