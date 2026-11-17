# Wired dock UV harnesses

Use both GH8 harnesses with the [wired Main](../../../../pcb/evt1/case-telemetry-study/wired-main/README.md)
and the [matched 4.22 Ω UV modules](../../../../pcb/evt1/case-telemetry-study/wired-main/uv-assembly/README.md). Match each
harness to the PCB reference, housing latch key and pin 1 before plugging it
in. Mark both ends with pin numbers. Check every conductor for continuity
and adjacent-pin isolation while unpowered.

| Harness | Main end | Other end | Connection |
| --- | --- | --- | --- |
| [Base UV](uv-base-gh8.yml) | J621 | J401 | GH8 pins 1 through 8 straight across |
| [Lid UV](uv-lid-gh8.yml) | J622 | J501 | GH8 pins 1 through 8 straight across |

The GH headers' grounded MP pads are mounting tabs. The GH2 D2F switch
recipes in this folder are for the earlier direct-pass-through dock. Use the
[Hall harness pin maps](../README.md#hall-heads-to-main) for the product lid cutoff.

The UV boards each also have a remote dry NTC and an independent NC
thermostat attached at solder lands on that board. The NTC reports temperature.
The thermostat opens its thermal safety loop at 45 ±5 °C. Those four remote parts
and their connections are separate from these GH harnesses. [UV circuit design](../../../../pcb/evt1/dock-uv/DESIGN.md)

## Stock and length

Use JST **GHR-08V-S** and **SSHL-002T-P0.2**. Verify the actual
wire against JST's 0.76–1.00 mm insulation range, use compatible tooling,
and inspect and pull-test crimp samples. Keep crimp-end strands untinned.
[GH connector catalog](https://www.jst.com/wp-content/uploads/2025/06/eGH.pdf)

The proposed single wire stock is Allied Wire and Cable **1371-26-7**,
26 AWG stranded silver-plated copper with PTFE insulation. Its published
maximum OD is 0.838 mm and maximum resistance is 0.127 Ω/m at 20 °C.
Verify the received minimum diameter and resistance. Cut eight 175 mm stock
blanks for the base and eight 225 mm stock blanks for the lid. The lid blanks
allow for handling and trimming at the second end. The two child BOMs call
for 3.20 m before crimp samples and scrap. Trim after fitting in the dock.
[Allied wire specification](https://www.awcwire.com/product/1371-26-7)

Each installed UV **pin 1 supply** and **pin 2 return** conductor must be
≤175 mm under the current powered electrical budget. Record the installed
power wire lengths including the conductor inside both terminals. The
[185/190 mm design check](../../../../pcb/evt1/dock-safety/lid-wire-length-review/README.md)
gives the measured-resistance gates to use if the fitted lid route needs more.
The incoming 20 °C wire limit is 0.135 Ω/m and the modeled
conductor ceiling is 80 °C. The branch limit is 0.290 Ω complete, including
both mated connectors, crimps, wire and UV board copper. Check both actual
branches and driver input voltage with the accepted source. Hinge travel,
bending life, wire retention, cutoff and powered behavior need a physical
trial. [Bench power budget](../../../../pcb/evt1/dock-safety/power-budget.json)

## Generate and verify

Run from the repository root with WireViz 0.4.1 and Graphviz.

```sh
uv_recipes=hardware/cables/evt1/dock-main/uv-harnesses
uv_exports=/private/tmp/compass-uv-harness-render
mkdir -p "$uv_exports"
wireviz -f pst -o "$uv_exports" "$uv_recipes"/uv-*-gh8.yml
python3 "$uv_recipes"/check_uv_harnesses.py --exports "$uv_exports"
```

The [native check](native-checks.json) binds the two wire graphs and child
BOMs to the active Main pads, schematic and matched UV quote revisions.
