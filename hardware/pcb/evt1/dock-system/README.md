# Functional EVT dock circuit candidate

Open `dock-system.kicad_pro` in KiCad10.0.8. This combines six source-bound
schematics: USB/source power, base controller, lid UI, independent safety and
base/lid UV drivers. `native-checks.json` records zero native ERC errors or
warnings,234 exported circuit positions and812 conserved terminal checks.
No ERC exclusions are used. This is a schematic milestone, not routed
fabrication artwork or a powered/optical release.

Edit the sibling projects, then regenerate this hierarchy. `sheets/` contains
derived leaf snapshots with the combined project-instance paths. Twelve
standalone supply flags and their wire/label stubs are removed because the
connected real drivers provide those rails/signals. Analog/UI flags behind
zero-ohm links remain. The manifest lists every removed annotation UUID;
the independent checker compares all functional components, properties,
terminal types and nets against the source leaves' native XML. Local library
tables resolve the source-owned, hash-bound symbols/footprints.

```sh
python3 hardware/pcb/evt1/dock-system/build_source.py
python3 hardware/pcb/evt1/dock-system/check_native.py --kicad-cli /path/to/kicad-cli
```

The controller is STM32L071CBT6 with ADS1115 monitoring. The lid has the actual
Newhaven NHD-C12864B2Z-RN-FBW charge-pump circuit and three Omron B3FS-1002P
switches. J302 maps LCD pinp to socket padp in the documented board frame;
the socket contact height, insertion mate and received-tail compatibility
remain unqualified. The four-layer lid board in
`../dock-control/routed-lid/` and both U-shaped UV boards in
`../dock-uv/{base,lid}/pcb/` pass native DRC with zero violations and
unconnected items. Their selected component geometry is available for StepUp
assembly integration. The complete source/controller/safety base PCB is being
routed in `../dock-main/`; it replaces the earlier USB board at the same
mounting plane. It is not a second board stacked there.

`../dock-safety/DESIGN.md` and `power-budget.json` control the independent
lid/thermal/watchdog/reset/latch and supply-cut design. Each UV driver has two
series Vishay LEDs, a3.65Ω sense resistor (~54.8mA nominal), local boost circuit
and cathode disconnect. Calculated normal UV input is650.6mA at the4.10V
driver-input floor under the stated efficiency assumptions; the minimum
limiter threshold leaves31.9mA normal-current margin. The50mΩ common PCB
allocation carries the full1.315A normal source current; the calculated
driver voltage is4.233V at the stated worst-case path allocations.
Maximum qualified-source fault allocation is
1484.4mA. The10mA UI allocation, path resistance, thermostat operation over
the actual supply range, inrush/suspend and all powered behavior need measured
acceptance. These figures establish neither optical dose nor cleaning efficacy.

The separate `dock-firmware/` target at repository root cross-compiles for the
selected MCU. Its source-bound reports cover25 host behavior scenarios,
410 independent schematic endpoint checks and274 native placement-board pads.
It implements display/control and unqualified trial timers; no controller has
been flashed or powered. `hardware/cad/evt1-assembly/` remains the mechanical
authoring source. New boards, switch retention, latch, hinge retention, UV
opaque backing/thermal joints, hardware actuators and installed looms must
be integrated and rechecked there.

The earlier five-board quote files do not include this revised dock. Their
preserved native report is a prior baseline; adding these candidate folders
changes the old runner's recursive source inventory. This new hierarchy uses
its own source/report bindings and does not refresh that baseline or release
any new PCB for fabrication. The human-owned product BOM is unchanged.
