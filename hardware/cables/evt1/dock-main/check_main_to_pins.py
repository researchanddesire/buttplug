"""Verify the four-contact dock harness against the active PCB and WireViz BOM."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from xml.etree import ElementTree

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PCB = ROOT / "hardware/pcb/evt1"
WIRED = PCB / "case-telemetry-study/wired-main"
DOCK = ROOT / "hardware/cad/evt1-assembly/evt1-wired"

sys.path.insert(0, str(ROOT / "tools"))
from kicad_sexp import children, parse, prop, value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nets(path, ref):
    result = {}
    for net in ElementTree.parse(path).findall("./nets/net"):
        for node in net.findall("node"):
            if node.get("ref") != ref:
                continue
            number = node.get("pin")
            if not number.isdigit():
                continue
            pin = int(number)
            assert pin not in result
            result[pin] = net.get("name")
    return result


def wired_main_sources():
    board = WIRED / "dock-wired-system.kicad_pcb"
    netlist = WIRED / "native.xml"
    audit = WIRED / "active-routing.json"
    check = json.loads(audit.read_text())
    assert check["board_sha256"] == sha(board)
    assert check["native_xml_sha256"] == sha(netlist)
    return board, netlist, audit


def main_connector_nets(board, netlist, ref):
    footprint, = (item for item in children(parse(board.read_text()), "footprint")
                  if prop(item, "Reference") == ref)
    pads = [(int(pad[1].value), value(pad, "net")) for pad in children(footprint, "pad")
            if pad[1].value.isdigit()]
    terminals = dict(pads)
    assert len(terminals) == len(pads) and terminals == nets(netlist, ref), ref
    return terminals


def check_saved_route(pin_numbers):
    assembly = DOCK / "DockAssembly.FCStd"
    report_path = DOCK / "contact-harness-check.json"
    report = json.loads(report_path.read_text())
    assert report["save_readback"] and report["exact_obstacle_pairs"] > 0
    for pin in pin_numbers:
        wire = report["wires"][str(pin)]
        assert wire["link"] == f"J102.{pin} → J94.{pin}"
        assert not wire["overlaps"] and wire["sampled_min_radius_mm"] >= 4.0 - 1e-6
    assembly_hash = sha(assembly)
    evidence = [assembly, report_path]
    if report["output_assembly_sha256"] != assembly_hash:
        current = next((check for key, check in report.items()
                        if key.startswith("current_after_") and check["native_sha256"] == assembly_hash), None)
        assert current is not None, "No cold check matches the saved dock assembly"
        current_path = DOCK / current["record"]
        check = json.loads(current_path.read_text())
        fit = check["closed_fit"]
        assert assembly_hash == current["native_sha256"] == check["product_native"]["sha256"] == fit["native_sha256"]
        assert current["cold_reopened"] and fit["cold_reopened"]
        routes = {wire["wire"]: wire for wire in fit["wires"] if wire["wire"].startswith("J102.")}
        assert set(routes) == {f"J102.{pin}–J94.{pin}" for pin in pin_numbers}
        assert all(not wire["overlaps_mm3"] and wire["housing_overlap_mm3"] <= 1e-6 for wire in routes.values())
        assert sum(wire["exact_pairs"] for wire in routes.values()) == current["exact_obstacle_pairs"] > 0
        evidence.append(current_path)
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports", type=Path, required=True)
    args = parser.parse_args()
    recipe = HERE / "main-to-pins.yml"
    main_pcb, main_xml, main_report = wired_main_sources()
    pin_pcb = PCB / "pins/pins-evt1.kicad_pcb"
    pin_xml = PCB / "pins/pins-native.xml"
    pin_report = PCB / "pins/mcad.json"
    pin_check = json.loads(pin_report.read_text())
    assert pin_check["board_sha256"] == sha(pin_pcb)

    pin_numbers = [1, 2, 3, 4]
    route_evidence = check_saved_route(pin_numbers)
    terminals = {
        "J102": main_connector_nets(main_pcb, main_xml, "J102"),
        "J94": {
            int(row["number"]): row["net"]
            for row in pin_check["pads"] if row["ref"] == "J94" and row["back"]
        },
    }
    assert terminals["J94"] == nets(pin_xml, "J94")
    signals = [("GND", "GND"), ("PLUG_USB_DM", "DOCK_DM"), ("PLUG_USB_DP", "DOCK_DP"),
               ("CONTACT_5V", "DOCK_5V")]
    assert [(terminals["J102"][pin], terminals["J94"][pin]) for pin in pin_numbers] == signals
    springs = ["P91", "P92", "P93", "P94"]
    for spring, (_, expected) in zip(springs, signals):
        assert nets(pin_xml, spring) == {1: expected}

    wireviz = yaml.safe_load(recipe.read_text())
    assert list(wireviz["connectors"]) == ["J102", "J94"]
    for ref, connector in wireviz["connectors"].items():
        assert connector["pins"] == pin_numbers
        assert connector["pinlabels"] == [terminals[ref][pin] for pin in pin_numbers]
        assert connector["ignore_in_bom"]
    assert wireviz["connections"] == [[{ref: pin_numbers} for ref in ("J102", "DK", "J94")]]
    assert set(wireviz["cables"]) == {"DK"}
    bundle = wireviz["cables"]["DK"]
    assert bundle["wirecount"] == 4 and bundle["length"] == 0.15
    assert bundle["mpn"] == "100690" and bundle["gauge"] == 28
    bom = args.exports / "main-to-pins.bom.tsv"
    with bom.open(newline="") as file:
        lines = list(csv.DictReader(file, delimiter="\t"))
    assert len(lines) == 1
    assert lines[0]["MPN"] == bundle["mpn"] and float(lines[0]["Qty"]) == 0.60
    assert lines[0]["Unit"] == "m"
    rendered = [args.exports / ("main-to-pins" + suffix) for suffix in (".svg", ".png")]
    assert all(path.stat().st_size > 100 for path in rendered)

    report = {
        "pass": True,
        "scope": "J102 to J94 pinout, assembly stock and nominal closed-pose FreeCAD route",
        "conductors": [{"pin": n, "main": s[0], "pin_board": s[1], "spring": spring}
                       for n, s, spring in zip(pin_numbers, signals, springs)],
        "stock_m_per_harness": 0.60,
        "nominal_closed_pose_route_checked": True,
        "physical_validation": False,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          (recipe, main_pcb, pin_pcb, main_xml, pin_xml, main_report,
                           pin_report, *route_evidence, Path(__file__).resolve())},
        "export_sha256": {p.name: sha(p) for p in [bom, *rendered]},
    }
    (HERE / "native-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: four conductors match board, netlist and saved dock route. WireViz stocks 0.60 m.")


if __name__ == "__main__":
    main()
