"""Verify the UI jumper and remote thermal recipes against the native boards."""
import argparse
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from zipfile import ZipFile

import yaml

from check_main_to_pins import HERE, PCB, ROOT, WIRED, main_connector_nets, nets, sha, wired_main_sources


def read_json(path):
    return json.loads(path.read_text())


def check_bom(exports, stem, quantities):
    bom = exports / f"{stem}.bom.tsv"
    with bom.open(newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    assert len(rows) == len(quantities)
    assert {row["MPN"]: (float(row["Qty"]), row["Unit"]) for row in rows} == quantities
    paths = [bom, exports / f"{stem}.svg", exports / f"{stem}.png"]
    assert all(path.stat().st_size > 100 for path in paths)
    return {path.name: sha(path) for path in paths}


def check_loom(recipe, paths, connections):
    document = yaml.safe_load(recipe.read_text())
    assert document["connections"] == connections
    assert set(document["connectors"]) == set(paths)
    for ref, pin_map in paths.items():
        connector = document["connectors"][ref]
        assert connector["pins"] == list(pin_map)
        assert connector["pinlabels"] == list(pin_map.values())
    return document


def check_ui(exports):
    recipe = HERE / "hinge-flex/main-to-lid-ui.yml"
    contract = PCB / "dock-control/pin-contract.json"
    lid_dir = PCB / "dock-control/lcd-socket-candidate"
    main_board, main_xml, main_check_file = wired_main_sources()
    lid_board = lid_dir / "dock-lid-jst-candidate.kicad_pcb"
    lid_check_file = lid_dir / "native-checks.json"
    lid_xml = lid_dir / "dock-lid-ui-native.xml"
    lid_check = read_json(lid_check_file)
    assert lid_check["native_board_sha256"] == sha(lid_board)
    assert lid_check["source_sha256"][lid_xml.name] == sha(lid_xml)
    assert lid_check["native_DRC_violations"] == lid_check["native_DRC_unconnected"] == 0

    hinge = read_json(contract)["UI_hinge"]
    pin_numbers = list(range(1, 21))
    expected = {pin: hinge["conductor_pin_contract"][str(pin)] for pin in pin_numbers}
    assert main_connector_nets(main_board, main_xml, "J201") == expected
    assert nets(lid_xml, "J301") == expected
    physical = {int(pad["pin"]): pad["net"] for pad in lid_check["native_pin_net_checks"]
                if pad["ref"] == "J301" and pad["pin"].isdigit()}
    assert physical == expected
    connections = [[{ref: pin_numbers} for ref in ("J201", "UI_FFC", "J301")]]
    loom = check_loom(recipe, {"J201": expected, "J301": expected}, connections)
    assert loom["cables"]["UI_FFC"]["wirecount"] == hinge["positions"] == 20
    assert loom["cables"]["UI_FFC"]["length"] * 1000 == hinge["cable_length_mm"] == 203
    assert hinge["cable_mpn"] == "0151660220" and hinge["cable_layout_type"].startswith("D/")
    result = {"pin_signals": expected, "FFC_mpn": hinge["cable_mpn"],
              "installed_motion_checked": False,
              "exports": check_bom(exports, recipe.stem, {"0151660220": (1, "pcs")})}
    sources = [recipe, contract, main_board, lid_board, main_xml, lid_xml,
               main_check_file, lid_check_file]
    return result, sources


def check_thermal(exports, side, prefix, loop):
    recipe = HERE / f"remote-thermal/uv-{side}-remote.yml"
    board = PCB / "case-radio-uv" / side / "pcb" / f"dock-uv-{side}.kicad_pcb"
    xml = WIRED / "native.xml"
    packet = WIRED / "uv-assembly" / f"wired-main-uv-{side}-supplier-quote.zip"
    with ZipFile(packet) as archive:
        report = json.loads(archive.read("manifest.json"))
        parity_path = "checks/wired-pad-net-parity.json"
        parts_path = "remote-thermal-parts.csv"
        parity = archive.read(parity_path)
        parts = archive.read(parts_path)
    for name, contents in ((parity_path, parity), (parts_path, parts)):
        assert sha256(contents).hexdigest() == report["files_sha256"][name]
    assert report["board_sha256"] == sha(board)
    assert report["wired_native_netlist_sha256"] == sha(xml)
    assert report["native_drc_errors"] == report["native_drc_unconnected"] == 0

    lands = [f"TP{prefix}{n}" for n in range(1, 5)]
    thermistor, cutoff = f"TH{prefix}1", f"S{prefix}1"
    signals = [f"NTC_{side.upper()}", "GND", f"{side.upper()}_THERM_SEND", f"LOOP_{loop}_RAW"]
    pad_nets = json.loads(parity)
    for land, net in zip(lands, signals):
        assert pad_nets[f"{land}.1"] == [net]
        assert nets(xml, land) == {1: net}
    expected_thermistor = {1: signals[0], 2: signals[1]}
    expected_cutoff = {1: signals[2], 2: signals[3]}
    assert nets(xml, thermistor) == expected_thermistor and nets(xml, cutoff) == expected_cutoff

    connections = [[{"UV_LANDS": lands[:2]}, {"NTC_LEADS": [1, 2]}, {thermistor: [1, 2]}],
                   [{"UV_LANDS": lands[2:]}, {"CUTOFF": [1, 2]}, {cutoff: [1, 2]}]]
    loom = check_loom(recipe, {"UV_LANDS": dict(zip(lands, signals)), thermistor: expected_thermistor,
                               cutoff: expected_cutoff}, connections)
    remote = {row["Reference"]: row["MPN"] for row in csv.DictReader(StringIO(parts.decode()))}
    assert remote == {thermistor: "NTCLE413E2103F524A", cutoff: "67L045"}
    assert all(loom["connectors"][ref]["mpn"] == mpn for ref, mpn in remote.items())
    assert loom["cables"]["NTC_LEADS"]["ignore_in_bom"]
    assert loom["cables"]["CUTOFF"]["length"] == 0.10 and loom["cables"]["CUTOFF"]["wirecount"] == 2
    result = {"pcb_lands": dict(zip(lands, signals)), "remote_parts": remote,
              "stock_cutoff_wire_m": 0.20,
              "exports": check_bom(exports, recipe.stem,
                                   {"NTCLE413E2103F524A": (1, ""), "67L045": (1, ""),
                                    "100690": (0.20, "m")})}
    return result, [recipe, board, xml, packet]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports", type=Path, required=True)
    args = parser.parse_args()
    ui, ui_sources = check_ui(args.exports)
    base, base_sources = check_thermal(args.exports, "base", "40", "A")
    lid, lid_sources = check_thermal(args.exports, "lid", "50", "B")
    sources = [*ui_sources, *base_sources, *lid_sources, Path(__file__).resolve(), HERE / "check_main_to_pins.py"]
    result = {
        "pass": True, "scope": "Active wired Main hinge FFC and matched UV remote thermal wiring",
        "main_to_lid_UI": ui, "remote_thermal": {"base": base, "lid": lid},
        "physical_validation": False,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path)
                          for path in sources},
    }
    (HERE / "peripheral-native-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: 20 UI lanes, eight remote thermal legs and three generated WireViz BOMs")


if __name__ == "__main__":
    main()
