# Shared-base source-power block

This is an editable native KiCad integration block for the **same base PCB** as
the controller and safety circuits. It is not a separate board or fabrication
release. The 48 circuit positions come from the frozen `dock-ui/source-native.xml`.
Four additional NPTH positions preserve existing shell bosses.

`source-block.kicad_pcb`, `placement.json` and `checks.json` are the handoff.
`placement.json` contains all 192 locked track/via records and frozen component
positions. `checks.json` independently binds the source XML, every original pad
and drill, saved copper, 12 physical connectivity groups, and native DRC.

Native KiCad 10.0.8 reports **zero violations, zero exclusions and 73 unconnected
groups**. Those groups include internal supply/control wiring and intersheet
endpoints. Complete them on the merged base, refill and rerun DRC/parity before
any fabrication export. The controller-only board must not be stacked with this
block. Neither candidate is orderable.

The common coordinates are `pcbX=100+dockX`, `pcbY=200-dockY`, F.Cu normal +Z.
The board is 1 mm with top Z6.4/bottom Z5.4. Four layers are F.Cu signals/local
power, **In1 continuous GND**, In2 power distribution, and B.Cu low-speed routing.
Preserve the In1 reference beneath both USB orientations and the downstream pair.
The two 8×8 carrier openings remain at dock(-43,19) and(-15,19). Existing shell
bosses at (-8,5.5), (8,5.5), (-8,23.5), (8,23.5) have Ø2.3 NPTHs and R3 hardware
reservations. No carrier cutout, boss or circuit changed.

The selected GCT USB4105-GF-A-120 has native origin **(100,201.325), angle0°**.
The manufacturer's 7.35 mm body length places the mating face at footprint
local +Y3.675, hence **dock(0,-5), facing -Y**. The PCB nose is dockY-4, 1 mm behind
the face. Body top is nominal Z9.71. The existing Z5.1 datum is the enclosure
window bottom. Selected `120` stakes extend 1.20 mm below the Z6.4 seating plane,
to Z5.2; the stock KiCad STEP instead has 0.95 mm stakes and must not be called an
exact `120` model. Preserve the package seating datum, rather than lowering it to
the window bottom. See `provenance.json` for primary drawing/model hashes.

Manual locked copper joins both USB orientations through the ESD package to J102,
CC1/CC2 to the source detector, HOST_5V to the device/UV limiters, CONTACT_5V to
J102, and UV_5V_LIMITED to J103 pad2 at dock(23.5,25). LDO and CC supply capacitor
loops, limiter capacitors, programming/fault branches and local ground vias are
explicit. U105 is adjacent to the future safety cuts near(28,28)/(31,28).
The USB paths are short Full-Speed candidates; no controlled impedance or signal
integrity measurement is claimed. CC vias under the connector require intact
solder-mask tenting and received-part/process inspection.

Default routing is 0.2 mm with 0.15 mm clearance; minimum track0.15 and through
via0.5/0.2. Preserve small package necks. Remaining broad power routes use:

| Net | Width mm |
| --- | ---: |
| HOST_5V | 0.6 |
| UV_5V_LIMITED | 0.8 |
| CONTACT_5V | 0.6 |
| 3V3 | 0.3 |

These classes are in `source-block.kicad_pro`; merge their intent into the final
project. Inner HOST copper reaches 1.0 mm. Copper weight/stackup, voltage drop,
source-current limits, temperature and USB operation still require qualification.

`SourceBlock.pretty` is a complete local copy of the source footprint library.
Only two drawing graphics differ: J101's outside-board silk ends are clipped to
the nose, and J102's manual-land courtyard is 1.0 mm rather than 1.5 mm. Every pad,
drill, fab outline and package datum is independently equal to the untouched
source library. Keep the local **DockUI** alias pointed at this derived library
when merging, or explicitly reproduce these cosmetic derivations in a final
shared library. Do not edit the frozen source library to achieve it.

Rebuild only after preserving any edited/routed candidate:

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
K10=/private/tmp/compass-kicad10/mount/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KPY build.py --restart
$KPY fill.py
$K10 pcb drc --format json --all-track-errors --output drc.json source-block.kicad_pcb
$KPY check.py
```

Each Python command uses one fresh native process. The checker is read-only and
checks physical copper connectivity, rather than trusting net names alone.
No board has been fabricated, powered, USB tested or physically fitted.
