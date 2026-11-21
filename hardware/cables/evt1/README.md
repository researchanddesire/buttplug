# EVT1 looms

> These seven sources describe the two-board EVT1 device (body and flange PCBs,
> two tape-on pack NTCs). The compact one-board device uses the generated set in
> [one-board/](one-board/README.md) instead.

These sources use `hardware/pcb/evt1/` native netlists, not the older R35F/P1
recipes. Seven WireViz diagrams separate the device, contact and cradle looms.
Generated diagrams and detailed child BOMs stay outside Git. The human-owned
`hardware/bom.csv` is unchanged.

| Source | Interface | Length status |
| --- | --- | --- |
| `interboard-evt1.yml` | Body J6 to flange J7, ten numeric1:1 wires | 120mm starting blanks; nominal free paths62.865–63.788mm |
| `compass-evt1.yml` | Body J81 to fixed compass J82, four wires | 150mm starting blanks; installed route unfinished |
| `pack-evt1.yml` | J2 power disconnect and two independent NTC pairs | 150mm body/NTC starting blanks; factory pack leads specified separately |
| `motor-evt1.yml` | J3 to both motor bridge terminals | 80mm pigtail blanks plus included OEM leads |
| `tip-evt1.yml` | J5 to the two-wire tip NTC | 80mm pigtail blanks plus included OEM leads |
| `contacts-evt1.yml` | Four fixed targets to flange J1 | 80mm starting blanks; installed route unfinished |
| `dock-evt1.yml` | Cradle USB J93 to pin PCB J94 | 150mm starting blanks; installed route unfinished |

The saved CAD is `hardware/cad/manufacturing-layout/evt1-integration/loom/`.
Its `review.json` controls the exact geometry-check status. `routing-plan.json`
is a derived fixture reference. Wire forms are not print parts. Received wire,
actual connector egress, crimp take-up, restraint and connected loading still
need first-article trials; these files do not release the complete product.
The ten native interboard forms pass independent solid/closed-mesh, sampled
bend and static part/wire checks. Wire STEP conversion is withdrawn and its
failed comparison is archived; use the editable native and checked preview.

## Parts and pin identification

Use Accu-Glass100690 stranded28AWG for interboard, power, motor and contact
pigtails;113094 stranded32AWG for compass and NTC extensions. The design
requires maximum insulated OD0.60/0.55mm and centreline bend radius4/2mm
respectively. The manufacturer's nominal diameters and bend figures are not
received tolerances. Inspect the stock against these limits before forming.
Both are amber/brown wire: number every end and verify continuity rather than
using color as function identification. `source-review.json` records primary
drawings and reviewed dimensional facts.

SH sockets are SHR-10V-S or SHR-02V-S, without the wider B-suffix protrusions.
Use SSH-003T-P0.2-H contacts with controlled JST-compatible tooling and a
qualified strip/crimp/pull process. Do not tin ordinary strands before crimping.
OEM thermistor leads receive individually insulated solder transitions to
ordinary stranded pigtails; do not assume their factory-tinned leads qualify
for the ordinary crimp. MOTOR_N is a bridge output, not system ground.

J6/J7 pin10 is **TIP_EXC_EN**. No USB pair passes through the neck. The ESP32-C3
and USB interface are on the flange. Twenty individual conductors pass through
the neck: ten interboard, four compass, two pack power and four pack-NTC.

The requested protected pack includes its ACHTR-02V-S socket and two
SACH-003G-P0.2 contacts. Buy only the separate body ACHTP-02V-S plug and two
SACHP-003G-P0.2 contacts for this loom. Pin1 is protected P+, pin2 is protected
P−. The CAD uses a mated allowance, not OEM connector geometry. Confirm pin
marks and polarity before mating. See `hardware/pcb/evt1/PACK-RFQ.md`.

On body J2, native logical pin2 has separate physical2P and2S lands. Power
return goes to2P. Both independent32AWG NTC returns join only at2S; do not
share a pack-side sensor return or force multiple wires into a crimp. Inspect
the two-wire solder joint and relief on that small land before accepting it.

## Assembly order

1. Tighten and lock the metal body/nut before loading boards or wires.
2. Prewire the rotating cap/body-board module, including local motor/tip
   transitions. Keep all flange ends free. The J7 housing remains loose;
   finished numbered terminals may be inserted after the module is threaded.
   Do not force the11mm SH10 housing beside the other neck wires.
3. Thread the module, dress the wires and terminate/mate them with the flange
   open. Connect the battery only after rotation is complete. Prove the actual
   wire passages and restraint; static wire-form checks do not prove this step.
4. Keep D−/D+ together in both contact and cradle looms, with minimal fanout.
   The logical diagrams establish no90ohm impedance or USB signal-integrity
   result. Solder, clean and cool fixed posts before fitting their inner rings.
5. Close both rigid halves before a continuous overmold. Complete cavity/button
   barriers and process qualification remain separate work. Start molding on
   inert assemblies, not a live battery/electronics assembly.

Workshop battery replacement consumes/remakes the silicone skin. Unplug the
power disconnect and rework the four separately insulated NTC extension joints
after opening the rigid halves. There is no neck battery-extraction path.

## Regeneration

Use FreeCAD Python for `tools/build_evt1_loom_cad.py`, then
`tools/verify_evt1_loom_cad.py`. With Python/PyYAML, run
`tools/build_evt1_looms.py`. Generate each `.yml` with WireViz0.4.1, for example:

```sh
wireviz -f spt -o /private/tmp/compass-evt1/cable-export hardware/cables/evt1/interboard-evt1.yml
```

Generate all seven, then run `tools/verify_evt1_looms.py --exports` with that
output directory. `logical-review.json` records the independent graph/BOM result.
`wire-stock.csv` is engineering starting stock,
not a finished-cut drawing or a product BOM. Factory-included leads and the
pack socket must not be purchased twice. No physical harness result is claimed.
