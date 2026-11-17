"""Check the rendered UV harness graphs and child BOMs against native endpoints."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from zipfile import ZipFile

from wireviz.wireviz import parse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from check_main_to_pins import PCB, ROOT, WIRED, main_connector_nets, sha, wired_main_sources

WIRE = ("Allied Wire and Cable", "1371-26-7", "m")
CONTACT = ("JST", "SSHL-002T-P0.2", "")
GH8 = ("JST", "GHR-08V-S", "")


def check_wireviz(stem, cable, wiring, labels, length, expected_bom, exports):
    recipe = HERE / f"{stem}.yml"
    diagram = parse(recipe, return_types="harness")
    assert set(diagram.cables) == {cable}
    bundle = diagram.cables[cable]
    assert (bundle.manufacturer, bundle.mpn, bundle.length_unit) == WIRE
    assert bundle.category == "bundle" and bundle.gauge == 26 and bundle.gauge_unit == "AWG"
    assert bundle.length == length and bundle.wirecount == len(wiring)
    assert bundle.wirelabels == labels
    assert not bundle.ignore_in_bom
    actual = [(c.from_name, c.from_pin, c.via_port, c.to_name, c.to_pin)
              for c in bundle.connections]
    assert actual == wiring

    output = [exports / f"{stem}{suffix}" for suffix in (".bom.tsv", ".svg", ".png")]
    with output[0].open(newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    found = {}
    for row in rows:
        key = (row["Manufacturer"], row["MPN"], row["Unit"])
        assert row["Description"] and key not in found
        found[key] = float(row["Qty"])
    assert found == expected_bom
    assert all(path.stat().st_size > 100 for path in output)
    return recipe, output, diagram


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, required=True)
    args = parser.parse_args()
    main_board, main_xml, main_checks = wired_main_sources()
    uv_quotes = WIRED / "uv-assembly"
    budget = PCB / "dock-safety/power-budget.json"
    uv_limits = json.loads(budget.read_text())["UV_path_resistance"]
    wire = uv_limits["wire"]
    limit_mm = wire["power_wire_each_leg_max_mm"]
    assert limit_mm == 175 and wire["supply_plus_return_max_length_mm"] == 2 * limit_mm
    awc_ohm_per_m = 38.7 / 304.8
    awc_hot_loop_ohm = awc_ohm_per_m * (2 * limit_mm / 1000) * (
        1 + wire["copper_TCR_per_K"] * (wire["conductor_max_C"] - 20))
    assert awc_ohm_per_m <= wire["incoming_max_resistance_ohm_per_m_at20C"]
    assert awc_hot_loop_ohm <= uv_limits["branch_resistance_allocations_ohm"]["wire_supply_and_return_attemperature"]
    assert math.isclose(sum(uv_limits["branch_resistance_allocations_ohm"].values()),
                        uv_limits["each_branch_supply_plus_return_max_ohm"])
    safety_parts = PCB / "dock-safety/parts-selection.json"
    safety = {p["reference"]: p for p in json.loads(safety_parts.read_text())["parts"]}

    sources = [main_xml, main_checks, main_board, budget, safety_parts, Path(__file__)]
    exports = []
    harnesses = []
    for side, loop, main_uv, local_uv, blank_mm in (
        ("base", "A", "J621", "J401", 175),
        ("lid", "B", "J622", "J501", 225),
    ):
        side_name = side.upper()
        signals = ["UV_5V_SW", "GND", "UV_CTRL", f"{side_name}_FB",
                   f"{side_name}_VOUT_DIV", f"NTC_{side_name}",
                   f"{side_name}_THERM_SEND", f"LOOP_{loop}_RAW"]
        uv_pins = list(range(1, 9))
        expected_uv = dict(zip(uv_pins, signals))
        assert main_connector_nets(main_board, main_xml, main_uv) == expected_uv
        assert safety[main_uv]["mpn"] == "SM08B-GHS-TB(LF)(SN)"

        uv_board = PCB / "case-radio-uv" / side / "pcb" / f"dock-uv-{side}.kicad_pcb"
        packet = uv_quotes / f"wired-main-uv-{side}-supplier-quote.zip"
        with ZipFile(packet) as archive:
            report = json.loads(archive.read("manifest.json"))
            parity_path = "checks/wired-pad-net-parity.json"
            parity = archive.read(parity_path)
        assert hashlib.sha256(parity).hexdigest() == report["files_sha256"][parity_path]
        assert report["wired_native_netlist_sha256"] == sha(main_xml)
        assert report["board_sha256"] == sha(uv_board)
        assert report["native_drc_errors"] == report["native_drc_unconnected"] == 0
        local_pads = {pad.split(".")[1]: values for pad, values in json.loads(parity).items()
                      if pad.startswith(local_uv + ".")}
        assert local_pads == {**{str(pin): [net] for pin, net in expected_uv.items()}, "MP": ["GND", "GND"]}
        sources.extend([uv_board, packet])

        wiring = [(main_uv, pin, pin, local_uv, pin) for pin in uv_pins]
        blank_length = blank_mm / 1000
        stock_metres = len(wiring) * blank_mm / 1000
        recipe, rendered, diagram = check_wireviz(f"uv-{side}-gh8", "UV", wiring, signals, blank_length,
                                                  {GH8: 2, CONTACT: 16, WIRE: stock_metres}, args.exports)
        for ref in (main_uv, local_uv):
            assert diagram.connectors[ref].pins == uv_pins
            assert diagram.connectors[ref].pinlabels == signals
        sources.append(recipe)
        exports.extend(rendered)
        harnesses.append({"recipe": recipe.name, "conductors": wiring, "signals": signals,
                          "starting_blank_mm": blank_mm, "finished_power_leg_max_mm": limit_mm})

    result = {
        "pass": True,
        "scope": "Active wired Main to matched 4.22-ohm UV modules",
        "installed_route_checked": False,
        "physical_validation": False,
        "harnesses": harnesses,
        "incoming_wire_max_ohm_per_m_at20C": wire["incoming_max_resistance_ohm_per_m_at20C"],
        "allied_wire_published_max_ohm_per_m_at20C": awc_ohm_per_m,
        "allied_wire_published_max_OD_mm": 0.033 * 25.4,
        "modeled_allied_supply_return_hot_ohm": awc_hot_loop_ohm,
        "complete_branch_resistance_max_ohm": uv_limits["each_branch_supply_plus_return_max_ohm"],
        "source_sha256": {str(p.resolve().relative_to(ROOT)): sha(p) for p in sources},
        "export_sha256": {p.name: sha(p) for p in exports},
    }
    (HERE / "native-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: 16 conductors match active native endpoints across both UV harnesses; child BOMs match")


if __name__ == "__main__":
    main()
