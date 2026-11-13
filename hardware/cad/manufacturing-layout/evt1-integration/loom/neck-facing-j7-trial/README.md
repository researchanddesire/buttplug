# Neck-facing flange connector

The working flange PCB now adopts these placements and the expanded west
outline. `routing-acceptance.json` records zero native DRC violations, zero
unconnected items, unchanged pad/net contracts and unchanged project rules.
This directory preserves the geometry preflight that preceded PCB promotion;
its source snapshot refers to the prior board/product checkpoint.

| Reference | PCB mechanical X/Y, mm | Native rotation |
| --- | --- | --- |
| J7 | −23.8 / −15.8 | −90°; socket opens toward the neck |
| D71 | −31.5 / −15.0 | 0° |
| U75 | −23.3 / −27.2 | 0°; beside the contact lands |
| D73 | −15.85 / −17.6 | 0°; additional wire clearance |

The PCB frame is native(x,y)=(100+X,130−Y)mm. The west body extends to
Y−29/−9 within the existing overall tab bounds. Mounting holes and right-hand
mounting seats remain. Every moved pad, including mounting pads, has at least
0.4mm bounding-box clearance to the proposed edge. Part numbers and numeric
pin contracts are unchanged.

`NeckFacingJ7Preflight.FCStd` replaces four component envelopes, the J7 mate
and PCB outline in the prior product assembly and adds ten wire forms. Its
source-bound nominal check passes882 part pairs, static wire/part checks and
mutual wire checks. Minimum sampled bend radius is4.306mm, wire surface gap
0.047mm and wire-to-D73 gap0.330mm. This is geometry evidence, not flexible
assembly or tolerance qualification. Wire centers1.4mm from the board face are
fixture targets, not controlled OEM egress dimensions. No finished cut lengths
or complete twenty-wire neck loom are released by this preflight.

The row rotates inside the neck, turns through a4.5mm bend, fans to the
connector's1mm pitch and uses an S bend ahead of the PCB. The official product
and loom builders consume current PCB MCAD; their independent saved-native
checks are the current integration evidence after regeneration.

`placement-proposal.json`, `source-snapshot.json`, `preflight.py` and
`geometry-preflight.json` preserve the pre-route screen. The preflight's hash
guards deliberately stop against the changed working sources. The prior
uncommitted board/product checkpoint is `../../archive/Pre-Neck-Facing-J7.zip`.
`archive/accepted-routing-evidence.zip` retains isolated routing inputs,
cleanup code/reports and native DRC iterations. Other ZIPs in `archive/` are
rejected or superseded experiments; do not use them as fabrication files.

The rejected away-facing native remains under `../archive/`. First-article
crimps/egress, restraint, loading, the other installed looms and physical fit
still need qualification. No PCB order, print or physical result exists.
