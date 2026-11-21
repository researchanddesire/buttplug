# One-board device harnesses

WireViz sources for the compact 52 × 20 mm one-board device in
`hardware/pcb/evt1/one-board/`. They are **generated**: run
`hardware/pcb/evt1/one-board/build_harnesses.py`, which exports the native
netlist of `compass-one-board.kicad_sch`, checks every off-board pin against
it and writes the `.yml` files, `wire-stock.csv` and `logical-source.json`
here. Edit the generator, not the YAML. The seven sources one level up
describe the earlier two-board device (interboard loom, two tape-on pack NTCs,
flange contacts) and do not apply to this board.

| Source | Interface | Conductors | Stock |
| --- | --- | --- | --- |
| `pack-one-board.yml` | Pack's factory JST SH 3P plug into the J2 SM03B header | 3 factory leads (red P+, black P−, white/yellow NTC) | none bought; nominal paths about 70 mm |
| `motor-one-board.yml` | J3 (SH2 side entry) to the NFP-E1015 motor | 2 × 28 AWG pigtails to the OEM leads | 120 mm blanks; nominal path 98.8 mm |
| `tip-one-board.yml` | J5 (SH2 side entry, like J3) to the TDK B57540G1103F000 bead | 2 × 32 AWG pigtails to the OEM leads | 150 mm blanks; nominal paths about 130 mm |
| `service-one-board.yml` | J4 (SH6 side entry) to the bench programming fixture | 6 × 28 AWG, bench only | 150 mm blanks; no installed route |

Nominal paths are centreline lengths from the mechanical internals model
(`one-board/mech/internals-fit.json`, bound by hash in `logical-source.json`).
Blanks are the path plus 20 mm, rounded up to 10 mm; they are starting stock,
not finished cut lengths. The service harness is a bench cable and is not part
of the product.

## Pack

The pack is a 3-wire protected 1S LiPo with its own NTC (502030 class,
chosen 2026-11-18), bought with its leads already crimped into a JST SH
1.0 mm 3-pin plug (SHR-03V-S). Since 2026-11-19 the board has a matching
JST SM03B-SRSS-TB side-entry header as J2 on B.Cu, beside J3 on the top
edge. It is assembled by the fab, so nobody solders the battery: plug it in
after the cap is threaded. Pin 1 is PACK_P (red), 2 GND (black) and 3
PACK_NTC (white or yellow). There is no polarity standard for 3-pin battery
plugs, so order that pinout and check it with a meter before the first mate.
The leads follow the motor wires through the wire trough to the neck; the
modelled path is about 70 mm, so order leads of at least 90 mm. SH contacts
are rated 1 A (see the open item below). The pack and its plug are
a human-owned BOM/RFQ line and the child BOM buys nothing.
The pack request is `hardware/pcb/evt1/one-board/PACK-RFQ.md` (BC-PACK-EVT1-002). The SH contacts are rated 1 A, below the 1.5 A continuous load carried over from the earlier request, so measure the real battery current before ordering.

## Motor, tip and service

Use Accu-Glass 100690 stranded 28 AWG for the motor and service pigtails and
113094 stranded 32 AWG for the tip. Maximum insulated OD is 0.60 / 0.55 mm and
centreline bend radius at least 4 / 2 mm. Both are amber wire: number every
end and verify continuity rather than reading colour as function. SH sockets
are SHR-02V-S and SHR-06V-S (no B-suffix protrusions) with SSH-003T-P0.2-H
contacts and controlled JST-compatible tooling. Crimp the pigtail first, then
solder it to the OEM motor or thermistor lead with an individually insulated
lap; do not ordinary-crimp the thermistor's leads and do not pre-tin strands
before crimping. MOTOR_N is a bridge output, not system ground. The service
harness supplies no VBUS; the board is powered from its pack or the dock
contacts while flashing.

## Regeneration and checks

From the repository root, with KiCad 10's CLI and WireViz 0.4.1 available to
`python3`:

```sh
python3 hardware/pcb/evt1/one-board/build_harnesses.py --render
```

`--render` compiles each source to SVG, PNG and a child BOM TSV in
`hardware/pcb/evt1/one-board/build/cables/export/` (outside Git), checks that
each child BOM matches the source's purchased items and records the output
hashes in `logical-source.json`. `--kicad-cli PATH` selects the KiCad CLI,
`--netlist FILE` reuses a saved native XML, and `--wireviz CMD...` overrides
the WireViz command. The report also binds the schematic sheets, the J2
header footprint and the internals model. No physical harness, crimp, current or
fit result is claimed; the human-owned `hardware/bom.csv` is unchanged.
