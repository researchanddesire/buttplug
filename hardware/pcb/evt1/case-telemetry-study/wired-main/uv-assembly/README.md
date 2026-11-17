# UV boards for wired Main

The native paths below reuse the UV emitter boards from the earlier radio
study. These boards contain the UV circuitry. The wired Main and its UV
boards require no cradle radio, antenna, or antenna pocket.

| Assembly | Editable KiCad PCB | Supplier pricing packet | Population |
| --- | --- | --- | --- |
| Base UV | [Native base PCB](../../../case-radio-uv/base/pcb/dock-uv-base.kicad_pcb) | [Base quote ZIP](wired-main-uv-base-supplier-quote.zip) | R401, 4.22 Ω |
| Lid UV | [Native lid PCB](../../../case-radio-uv/lid/pcb/dock-uv-lid.kicad_pcb) | [Lid quote ZIP](wired-main-uv-lid-supplier-quote.zip) | R501, 4.22 Ω |

For one product first article, quote one populated base board and one
populated lid board, 40 SMT placements across the pair. Allow two Vishay
**NTCLE413E2103F524A** dry thermistors and two Sensata **67L045** normally
closed thermostats in total. Count these remote parts once across the two
quote tables and the harness lists. Base TP401/TP402 take the NTC and
TP403/TP404 take the thermostat. The lid uses TP501/TP502 and TP503/TP504
respectively. Check the two GH8 cables independently with the power off.
During screen, button and USB bring-up, leave both UV branches unplugged at
Main J621/J622. [UV harnesses and remote thermal pin maps](../../../../../cables/evt1/dock-main/README.md) ·
[Wired bench bring-up](../../../../../../dock-firmware/wired-main/BRINGUP.md)

Fit Vishay **CRCW08054R22FKEA** in both UV sense positions. Pair these
boards with wired Main **R107 = 40.2 kΩ**, Yageo **RT0603BRD0740K2L**,
and STM32 firmware built with `make -C dock-firmware PROFILE=wired` for
the **4220 mΩ** sense conversion. Confirm all three resistor positions
and the programmed profile before applying power. The default direct USB
pass-through bench population uses 3.65 Ω and its own STM32 build.

The quoted native UV PCBs carry the selected sense resistors. The dock's
linked StepUp models match their outline, drills and package geometry,
including the two sense resistor footprints.
Each quote ZIP contains the same 13 fabrication files as the frozen UV
artwork, 20 PCB placements and a separate two-part remote thermal list.
Four test points are copper only. The electrical parity check permits the
native PCB's compact value label for each sense resistor and checks exact
MPN and manufacturer against the wired native schematic.

[Native validation](native-checks.json) binds the wired netlist, firmware
profile, UV native boards and both quote ZIPs. KiCad 10.0.8 reported zero
DRC violations or unconnected items per board under the inherited UV
rule set. The check compares all 61 physical electrical pads per board
and confirms the wired and direct makefile sense selections. Replay
without writing the archives with the following command from this folder.

```sh
python3 build_quotes.py --kicad-cli /path/to/kicad-cli --check
```

The [wired power calculation](../circuit-contract.json) reserves
104 mA for the host branch and added control loads. The UV LEDs run at
47.39 mA nominal per string, with 15.51 mA calculated source headroom
at the 1.5 A fault allocation. The quote scope is the two UV boards.
Main routing, supplier acceptance, and measured source, thermal, cutoff
and optical performance remain open.
