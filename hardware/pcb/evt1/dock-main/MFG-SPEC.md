# Main PCB fabrication quote candidate

This is a requested process candidate, with **supplier acceptance false**. It is not a fabrication or powered release. Use the frozen routed native board identified in `native-checks.json`; preserve its exact outline, pad/drill pattern and all six Ø2.3 mm mounting holes.

- Four layers, 1.00 mm nominal overall copper plus dielectric. Order: F.Cu signals/local power; In1.Cu ground reference; In2.Cu separated power and low-speed signals; B.Cu signals. The supplier must provide and obtain acceptance of the actual core/prepreg build.
- Requested finished copper: **outer ≥35 µm, inner ≥30 µm**. A nominal “1 oz” designation alone does not guarantee these minima. Do not substitute default 0.5 oz inner copper.
- Native ordinary through vias are Ø0.50 mm lands / Ø0.20 mm nominal finished bores. Requested minimum accepted finished bore is **0.15 mm**, with **wall plating ≥25 µm**. The supplier must confirm its actual drilling/plating tolerances and annular-ring capability.
- Ordinary track/clearance minima are 0.15/0.15 mm. Native minimum annular-ring capability is 0.10 mm, including the selected USB4105 plated-stake pattern. Global hole-to-copper clearance is 0.20 mm; only two J101-owned features use the documented 0.15 mm manufacturer-pattern rule (actual nominal separation about 0.1751 mm). Explicit supplier review is required for the **0.10/0.15 mm J101 features**. Global hole-to-hole minimum is 0.25 mm and copper-to-cut-edge minimum is 0.30 mm.

`power-study/final/resistance.json` evaluates the requested minimum corner at 85°C, with 20% surface-width-loss sensitivity and a 3 mΩ engineering modelling reserve. That reserve is not a proven bound on discretization, contact spreading or process error. The 18 µm wall case is diagnostic and is not the accepted process candidate.

Require an actual **hot/aged four-wire common PCB supply-plus-return result ≤50 mΩ** for each J101 VBUS/GND-land to J621/J622 supply/return-land path. Characterize the copper sections with an appropriate bare-board/isolated fixture; semiconductor on-resistance and the separately allocated GH contacts/crimps/wires/UV-board branches are excluded. Do not substitute typical semiconductor resistance for a copper measurement.

The 4.10 V driver floor, 70% efficiency assumption, complete UI/current-limit allocation, startup/inrush, USB suspend/source changes and transient behaviour still require physical qualification. UV optical leakage, temperature, material aging and cleaning efficacy are separate gates. No sterilization result is claimed.
