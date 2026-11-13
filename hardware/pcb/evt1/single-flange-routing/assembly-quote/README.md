# Single flange EVT1 PCB assembly quote

Request three bare boards and quote assembly of two. Keep the third board
bare for receiving measurements and the inert flange fit. This package
covers the routed single flange PCB with the original body PCB architecture.
Use the [assembly quote ZIP](single-flange-evt1-assembly-quote.zip) for the
complete package and the [fabrication ZIP](single-flange-evt1-fabrication-quote.zip)
for a bare board quote.

![KiCad front view showing the two switches and four target positions](preview-front.png)

![KiCad rear view showing the module, connectors and compass components](preview-back.png)

The board is 1.00 mm finished thickness with four copper layers and ENIG.
Quote the explicit copper/dielectric stack in `fabrication-request.json`.
Preserve In1 as the ground reference, the open antenna notch and all-layer
copper keepout. Review the requested stack, controlled impedance capability,
0.15 mm trace/clearance, 0.20 mm vias, 0.864 mm plated target holes in the drill
file and 1.60 mm unplated mounting holes before accepting a quote. Finished
target hole and received pin tolerances determine insertion and solder fit.
The Ø3.2 mm target copper land is a project dimension.

Use `single-flange-smt-parts.csv` and `single-flange-smt-positions.csv` together
for the 35 SMT placements. Two switches populate the front. Thirty-three
components populate the back. The KiCad position files use mm and the same
absolute origin as the Gerbers and drills. Preserve the exported side and
rotation. Reconcile orientation to the native Fab drawings and component
markings before programming placement. D1's cathode stripe goes at the
native cathode bar and pad 2. U6 and U81 require package orientation and
stencil review. C83 is TDK C2012X5R1E226M125AC and needs at least 10 µF
effective at 3.3 V over the intended temperature and aging conditions.

Purchase four Mill-Max **1946-0-00-15-00-00-03-0** fixed targets per board
separately. See `single-flange-manual-targets.csv` for CT1–CT4, their exact
nets and installed order. Leave the plated contact holes empty through SMT
assembly. Bench solder these with their shoulders seated against the front
lands and with a square, controlled face plane. Inspect shoulder seating,
stand-off, solder fill and fit to the dry-side reaction posts before loading
the board. The intended contact load travels from the shoulder through the
laminate to the rigid posts. Verify that path on inert parts. MH1–MH4 are
unplated mounting holes. Order mating housings and cable parts separately.

The manifest binds the saved PCB, project, component selection, native pad
and schematic audits and every delivered file. The export rechecks all 163
electrical pad instances against fresh IPC-D-356, all 155 logical terminals
against the schematic netlist, and all 43 native positions against the PCB.
KiCad 10.0.8 DRC and full-context ERC run at export. Supplier acceptance,
USB performance, fit, contact sealing and powered commissioning remain open.
