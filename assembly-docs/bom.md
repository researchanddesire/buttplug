---
hide:
  - toc
---
# Bill of Materials

The canonical product BOM is [`hardware/bom.csv`](../hardware/bom.csv). It currently contains the standard header only; no production parts or quantities have been approved.

The assembly-docs aggregator renders the CSV here at build time. Do not hand-edit the generated block or copy candidate ICs from the schematic review into the BOM without human confirmation.

<!-- BEGIN GENERATED BOM -->
<!-- END GENERATED BOM -->

## Assembly Tools and Shop Supplies

| Item | Used for | Status |
| --- | --- | --- |
| Two-jaw driver for the 24 AF × 4 mm thin nut | Rear nut, device step 1 | Proposal: `hardware/cad/manufacturing-layout/evt1-integration/rear-joint-trial/TwoJawDriver.step` |
| Loctite 243 | Rear nut thread | Candidate |
| JST SH crimp tool | Motor and tip-sensor plugs | Required |
| JST GH crimp tool | Dock UV and Hall harnesses | Required |
| Fine-tip soldering iron | Contact targets, splices, dock contact harness, Hall boards | Required |
| Multimeter | Every plug before it is connected | Required |
| Ø1.6 mm drill and M2 tap | Main board bosses in the dock lower shell | Required |
| Ø5.4 mm reamer | Button plunger bores, if a plunger binds | As needed |
| Potting compound | Tip thermistor in the nose cap | Not chosen |
| Silicone, primer, skin mould and contact mask | Device skin | Not chosen |
| ESD mat and wrist strap | Board handling | Required |
