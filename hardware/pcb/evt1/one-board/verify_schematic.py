"""Re-export both native netlists and verify the single-device circuit contract."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from build_schematic import OPTIONAL_SYS_BULK, SOURCE_SUBSTITUTIONS

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "single-flange-routing" / "single-flange-system.kicad_sch"
CANDIDATE = HERE / "compass-one-board.kicad_sch"
NEW_NETLIST = HERE / "compass-one-board-native.xml"
ERC_REPORT = HERE / "schematic-erc.json"
REMOVED = {"J6", "J7", "J81"}
ADDED = {"J8", "R88", "C88", "TH3"}
ADC_CHANGE = ("U7", "6")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(cli, *args, check=True):
    return subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True, check=check)


def export(cli, schematic, output):
    invoke(cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", output, schematic)


def read_network(netlist):
    tree = ET.parse(netlist)
    components = {}
    terminals = {}
    nets = defaultdict(set)
    for comp in tree.findall("components/comp"):
        ref = comp.get("ref")
        assert ref not in components, ref
        components[ref] = (
            comp.findtext("value"), comp.findtext("footprint"),
            comp.find("libsource").get("part"),
            tuple(sorted(p.get("name") for p in comp.findall("property") if p.get("name") in {"dnp", "exclude_from_board", "exclude_from_bom"})),
        )
    for row in tree.findall("nets/net"):
        net = row.get("name")
        for node in row.findall("node"):
            key = node.get("ref"), node.get("pin")
            assert key not in terminals, key
            terminals[key] = (net, node.get("pinfunction"), node.get("pintype"))
            nets[net].add(key)
    return components, terminals, nets


def verify_circuit(baseline, candidate):
    old_components, old_pins, _ = read_network(baseline)
    new_components, new_pins, nets = read_network(candidate)

    assert old_components.keys() - new_components.keys() == REMOVED
    assert new_components.keys() - old_components.keys() == ADDED
    for ref in old_components.keys() - REMOVED:
        old, new = old_components[ref], new_components[ref]
        if ref in SOURCE_SUBSTITUTIONS:
            selected = SOURCE_SUBSTITUTIONS[ref]
            assert old[0] == selected["replaces"], ref
            assert new == (selected.get("value", selected["mpn"]),
                           selected.get("footprint", old[1]), *old[2:]), ref
        elif ref == "JP1" or ref in OPTIONAL_SYS_BULK:
            assert new == (*old[:3], ("exclude_from_bom",)), ref
        else:
            assert old == new, ref

    retained = {pin: description for pin, description in old_pins.items() if pin[0] not in REMOVED}
    expected_new_pins = {
        ("J8", "1"): "PACK_MON_NTC", ("J8", "2"): "GND",
        ("R88", "1"): "TIP_EXC_EN", ("R88", "2"): "PACK_MON_NTC",
        ("C88", "1"): "PACK_MON_NTC", ("C88", "2"): "GND",
        ("TH3", "1"): "PACK_MON_NTC", ("TH3", "2"): "GND",
    }
    assert old_pins.keys() - new_pins.keys() == {pin for pin in old_pins if pin[0] in REMOVED}
    assert new_pins.keys() - old_pins.keys() == expected_new_pins.keys()
    assert {pin for pin in retained if retained[pin] != new_pins[pin]} == {ADC_CHANGE}
    for pin, expected_net in expected_new_pins.items():
        assert new_pins[pin][0] == expected_net, pin
        assert new_pins[pin][2] == "passive", pin
    assert nets["PACK_MON_NTC"] == {ADC_CHANGE, ("J8", "1"), ("R88", "2"), ("C88", "1"), ("TH3", "1")}
    assert old_pins[ADC_CHANGE][0] == "GND" and new_pins[ADC_CHANGE] == ("PACK_MON_NTC", *old_pins[ADC_CHANGE][1:])

    static_pin_contract = {
        ("U6", "16"): "TIP_EXC_EN", ("U7", "1"): "GND", ("U7", "4"): "TIP_NTC",
        ("U7", "5"): "TIP_EXC_HALF", ("U7", "7"): "GND", ("U7", "8"): "3V3",
        ("J2", "1"): "PACK_P", ("J2", "2"): "GND", ("J2", "3"): "PACK_NTC", ("J2", "4"): "PACK_GUARD",
        ("TH1", "1"): "PACK_NTC", ("TH2", "1"): "PACK_GUARD", ("U1", "1"): "PACK_NTC",
        ("U1", "4"): "CHARGE_CE_N", ("U1", "5"): "GND", ("U1", "6"): "GND",
        ("JP1", "1"): "CHARGE_TEMP_OK", ("JP1", "2"): "CHARGE_PERMIT",
        ("R3", "1"): "VBUS_CHG", ("R3", "2"): "CHARGE_CE_N",
        ("Q1", "3"): "CHARGE_CE_N", ("U4", "4"): "MOTOR_IN1",
        ("U9", "1"): "CHARGE_TEMP_OK", ("U9", "3"): "VBUS_CHG",
        ("U9", "5"): "3V3", ("U9", "6"): "VBUS_CHG",
        ("U5", "6"): "MOTOR_IN1", ("U5", "2"): "MOTOR_P", ("U5", "3"): "MOTOR_N",
        ("CT1", "1"): "GND", ("CT2", "1"): "USB_DM_CONTACT",
        ("CT3", "1"): "USB_DP_CONTACT", ("CT4", "1"): "DOCK_5V",
        ("U6", "26"): "USB_DM", ("U6", "27"): "USB_DP", ("U71", "1"): "MCU_EN",
        ("U81", "1"): "I2C_SCL", ("U81", "4"): "I2C_SDA",
    }
    for pin, expected_net in static_pin_contract.items():
        assert new_pins[pin][0] == expected_net, (pin, new_pins[pin][0], expected_net)
    assert "Open" in new_components["JP1"][1] and new_components["JP1"][3] == ("exclude_from_bom",)
    assert new_components["J8"][1] == new_components["J3"][1]
    assert all(new_components[ref][3] == () for ref in ADDED - {"TH3"})
    assert not new_components["TH3"][1] and "exclude_from_board" in new_components["TH3"][3]
    assert len([values for values in new_components.values() if values[1]]) == 108

    return {
        "retained_component_values_and_footprints": len(old_components) - len(REMOVED) - len(SOURCE_SUBSTITUTIONS),
        "same_footprint_MPN_substitutions": {ref: data["mpn"] for ref, data in SOURCE_SUBSTITUTIONS.items()},
        "unloaded_sys_bulk_footprints": sorted(OPTIONAL_SYS_BULK),
        "retained_pin_types_functions_and_net_bindings": len(retained) - 1,
        "only_existing_endpoint_changed": "U7.6 / AIN2 / GND -> PACK_MON_NTC",
        "retired_pin_count": len(old_pins.keys() - new_pins.keys()),
        "new_pin_count": len(expected_new_pins),
        "footprint_count": 108,
        "explicit_pin_contracts": {f"{ref}.{pin}": net for (ref, pin), net in static_pin_contract.items()},
        "power_and_fault_defaults": {
            "charge": "JP1 physical jumper remains open. U1 (~CE) is pulled high. Pack TS, guard sensor and gate wiring conserved.",
            "charger_input_limit": "Existing EN1=GND and EN2=GND USB100 straps conserved.",
            "telemetry": "R88/C88/J8 fitted. Open sensor reads excitation level; short reads GND; both invalidate telemetry only.",
            "source_loading": "0.33 mA nominal additional worst static pack-divider current at 3.3 V.",
        },
    }


def verify_erc(cli):
    command = invoke(cli, "sch", "erc", "--help", check=False)
    if "--format" not in command.stdout or "json" not in command.stdout.lower():
        return {"status": "unavailable in this CLI; native network export and pin contract checked"}
    invoke(cli, "sch", "erc", "--format", "json", "--severity-all", "-o", ERC_REPORT, CANDIDATE)
    report = json.loads(ERC_REPORT.read_text())
    violations = [v for sheet in report["sheets"] for v in sheet["violations"]]
    assert not violations, violations
    return {"status": "pass", "violations": len(violations), "report_sha256": sha(ERC_REPORT)}


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--kicad-cli", type=Path, required=True)
    cli = args.parse_args().kicad_cli
    with tempfile.TemporaryDirectory(prefix="compass-one-board-parity-") as temporary:
        baseline_xml = Path(temporary) / "baseline.xml"
        export(cli, BASELINE, baseline_xml)
        export(cli, CANDIDATE, NEW_NETLIST)
        report = verify_circuit(baseline_xml, NEW_NETLIST)
        report["baseline_export_sha256"] = sha(baseline_xml)
    report["kicad_version"] = invoke(cli, "version").stdout.strip()
    report["netlist_xml_sha256"] = sha(NEW_NETLIST)
    report["schematic_sources_sha256"] = {
        str(source.relative_to(HERE)): sha(source)
        for source in (CANDIDATE, *sorted((HERE / "sheets").glob("*.kicad_sch")))
    }
    report["native_erc"] = verify_erc(cli)
    (HERE / "schematic-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
