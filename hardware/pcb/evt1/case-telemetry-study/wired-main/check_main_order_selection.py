"""Replay the wired Main component selection from the frozen quote and native schematic."""

import argparse
from collections import defaultdict
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
EVT = HERE.parents[1]
FROZEN = EVT / "dock-main"
QUOTE = FROZEN / "assembly-quote/dock-main-assembly-quote.zip"
OLD_NETLIST = EVT / "dock-system/native.xml"
MAIN_LEAVES = {"dock-ui-source", "dock-controller", "dock-safety"}
WIRED_LEAVES = {"wired-usb-data", "wired-usb-host", "wired-usb-passives"}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main_components(path, leaves):
    root = ET.parse(path)
    selected = {}
    for comp in root.findall("./components/comp"):
        leaf = comp.find("sheetpath").get("names").strip("/")
        footprint = comp.findtext("footprint")
        if leaf not in leaves or not footprint:
            continue
        ref = comp.get("ref")
        fields = {node.get("name"): node.get("value") for node in comp.findall("property")}
        assert ref not in selected
        selected[ref] = {
            "reference": ref,
            "schematic_value": comp.findtext("value"),
            "footprint": footprint,
            "manufacturer": fields.get("Manufacturer"),
            "mpn": fields.get("MPN"),
            "sheet": leaf,
            "dnp": comp.find("dnp") is not None or "dnp" in fields,
        }
    return selected


def frozen_quote():
    with ZipFile(QUOTE) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        file_hashes = manifest["files_sha256"]
        assert set(archive.namelist()) == set(file_hashes) | {"manifest.json"}
        assert len(archive.namelist()) == len(file_hashes) + 1
        assert all(sha256(archive.read(name)).hexdigest() == expected
                   for name, expected in file_hashes.items())
        board = FROZEN / "dock-main.kicad_pcb"
        assert digest(board) == manifest["board_sha256"] == file_hashes["native/dock-main.kicad_pcb"]
        native = json.loads(archive.read("checks/native-checks.json"))
        assert digest(OLD_NETLIST) == native["system_XML_sha256"]
        assert native["board_sha256"] == manifest["board_sha256"]
        assert manifest["pcb_drc_violations"] == manifest["pcb_drc_unconnected"] == 0
        ordered = list(csv.DictReader(io.StringIO(archive.read("dock-main-ordered-parts.csv").decode())))
        copper = list(csv.DictReader(io.StringIO(archive.read("dock-main-copper-only.csv").decode())))
        placed = list(csv.DictReader(io.StringIO(archive.read("dock-main-assembly-positions.csv").decode())))
        assert len(ordered) == manifest["manufacturer_part_lines"] == 45
        assert len(copper) == manifest["electrical_copper_only_references"] == 12
        assert len(placed) == manifest["purchased_positions"] == 138
        selected = {row["Ref"]: row for row in placed}
        assert len(selected) == len(placed)
    return ordered, copper, selected, manifest


def ref_key(reference):
    match = re.fullmatch(r"([A-Z]+)(\d+)", reference)
    assert match, reference
    return match[1], int(match[2])


def positions(old, wired, ordered, placed, passive, contract, models, footprint_sources):
    result = {}
    replacement, = (entry for entry in passive["matched_power_population"] if entry["board"] == "Main")
    assert replacement["reference"] == "R107"
    for line in ordered:
        refs = line["References"].split()
        assert len(refs) == int(line["QtyPerBoard"])
        for ref in refs:
            previous = old[ref]
            assert previous["manufacturer"] == line["Manufacturer"] and previous["mpn"] == line["MPN"]
            assert previous["schematic_value"] in line["Values"].split(" | ")
            assert previous["footprint"] in line["Footprints"].split(" | ")
            assert previous["schematic_value"] == placed[ref]["Val"] and placed[ref]["Side"] == "top"
            assert previous["footprint"].split(":")[1] == placed[ref]["Package"]
            assert ref not in result and not wired[ref]["dnp"]
            if ref == replacement["reference"]:
                assert previous["footprint"] == replacement["footprint"]
                assert (wired[ref]["manufacturer"], wired[ref]["mpn"], wired[ref]["schematic_value"]) == (
                    replacement["manufacturer"], replacement["mpn"], replacement["schematic_value"])
                entry = {"selection": "wired power population",
                         "manufacturer_source": replacement["manufacturer_source"],
                         "replaces_frozen_mpn": previous["mpn"]}
            else:
                assert previous == wired[ref]
                entry = {"selection": "frozen Main quote"}
            result[ref] = {**wired[ref], **entry, "assembly_process": line["AssemblyProcess"]}
    assert set(result) == set(placed)
    for line in passive["added_passives"]:
        refs = line["references"]
        assert len(refs) == line["quantity_per_board"]
        for ref in refs:
            assert ref not in result and not wired[ref]["dnp"] and wired[ref]["mpn"] is None
            assert line["schematic_value"] == wired[ref]["schematic_value"] == contract["passives"][ref][0]
            assert line["footprint"] == wired[ref]["footprint"] == footprint_sources[ref]
            result[ref] = {**wired[ref], "manufacturer": line["manufacturer"], "mpn": line["mpn"],
                           "selection": "wired passive supplement", "assembly_process": "SMT",
                           "manufacturer_source": line["manufacturer_source"]}
    for ref, part in contract["devices"].items():
        expected = wired[ref]
        assert ref not in result and not expected["dnp"]
        assert part["manufacturer"] == expected["manufacturer"]
        assert part["mpn"] == expected["mpn"] == expected["schematic_value"] == models[ref]["mpn"]
        assert expected["footprint"] == footprint_sources[ref] == models[ref]["footprint"]
        result[ref] = {**expected, "selection": "wired circuit contract", "assembly_process": "SMT",
                       "manufacturer_source": part["source"],
                       "manufacturer_package_drawing": models[ref]["manufacturer_drawing"]}
    return result


def copper_positions(old, wired, copper, passive, footprint_sources, purchased):
    result = {}
    for row in copper:
        ref = row["Reference"]
        assert ref not in result and ref not in purchased and old[ref] == wired[ref]
        assert int(row["QtyPurchased"]) == 0
        assert row["Function"] == wired[ref]["schematic_value"] and row["Footprint"] == wired[ref]["footprint"]
        result[ref] = {"reference": ref, "function": row["Function"], "footprint": row["Footprint"],
                       "quantity_purchased": 0, "selection": "frozen Main quote"}
    for ref, name in passive["service_copper_no_purchased_parts"].items():
        assert ref not in result and ref not in purchased and wired[ref]["mpn"] is None
        assert wired[ref]["manufacturer"] == "manual copper"
        assert wired[ref]["schematic_value"] == name and wired[ref]["footprint"] == footprint_sources[ref]
        result[ref] = {"reference": ref, "function": name, "footprint": wired[ref]["footprint"],
                       "quantity_purchased": 0, "selection": "wired service pad"}
    return result


def ordering_lines(purchased):
    by_part = defaultdict(list)
    for ref, part in purchased.items():
        by_part[part["manufacturer"], part["mpn"]].append(ref)
    by_vendor = defaultdict(lambda: {"placements": 0, "manufacturer_part_lines": 0})
    lines = []
    for (vendor, mpn), refs in sorted(by_part.items(), key=lambda row: (row[0][0].casefold(), row[0][1])):
        lines.append({"manufacturer": vendor, "mpn": mpn, "quantity_per_main": len(refs),
                      "references": sorted(refs, key=ref_key)})
        by_vendor[vendor]["placements"] += len(refs)
        by_vendor[vendor]["manufacturer_part_lines"] += 1
    return lines, dict(by_vendor)


def review():
    ordered, copper, placed, quote = frozen_quote()
    passive_path = HERE / "passive-parts-selection.json"
    contract_path = HERE / "circuit-contract.json"
    model_path = HERE / "package-models.json"
    source_manifest_path = HERE / "source-manifest.json"
    audit_path = HERE / "native-checks.json"
    netlist = HERE / "native.xml"
    passive = load(passive_path)
    assert all(digest(EVT / path) == checksum for path, checksum in passive["source_sha256"].items())
    assert passive["dnp_added_passive_references"] == []
    contract = load(contract_path)
    models = load(model_path)["selected_devices"]
    footprint_sources = load(source_manifest_path)["new_reference_footprints"]
    audit = load(audit_path)
    assert audit["kicad_version"] == "10.0.8" and audit["ERC_errors"] == audit["ERC_warnings"] == 0
    assert digest(netlist) == audit["native_report_hashes"]["native.xml"]
    assert all(digest(HERE / path) == checksum for path, checksum in audit["source_hashes"].items())
    old = main_components(OLD_NETLIST, MAIN_LEAVES)
    wired = main_components(netlist, MAIN_LEAVES | WIRED_LEAVES)
    purchased = positions(old, wired, ordered, placed, passive, contract, models, footprint_sources)
    manual = copper_positions(old, wired, copper, passive, footprint_sources, purchased)
    assert set(old) == set(placed) | {row["Reference"] for row in copper}
    assert set(wired) == set(purchased) | set(manual)
    assert set(purchased).isdisjoint(manual)
    assert (len(old), len(wired), len(purchased), len(manual)) == (150, 219, 200, 19)
    assert set(wired) - set(old) == set(footprint_sources)
    lines, vendors = ordering_lines(purchased)
    assert sum(line["quantity_per_main"] for line in lines) == len(purchased)
    paths = (QUOTE, FROZEN / "dock-main.kicad_pcb", OLD_NETLIST, passive_path, contract_path,
             model_path, source_manifest_path, audit_path)
    return {
        "scope": "Wired Main component selection for procurement review. Quantities are fitted units before assembler attrition or reel minimums.",
        "frozen_quote_board_sha256": quote["board_sha256"],
        "input_sha256": {str(path.relative_to(EVT)): digest(path) for path in paths},
        "wired_native_netlist_parity": "Native XML and all schematic source hashes checked against KiCad 10.0.8 ERC/netlist audit.",
        "counts": {"frozen_purchased": len(placed), "added_passives": len(contract["passives"]),
                   "added_active_or_crystal": len(contract["devices"]), "purchased_positions": len(purchased),
                   "manual_copper_positions": len(manual), "unique_purchase_lines": len(lines),
                   "manufacturers": len(vendors), "main_native_references": len(wired), "purchased_DNP": 0},
        "manufacturer_totals": vendors,
        "purchase_lines": lines,
        "purchased_positions": [purchased[ref] for ref in sorted(purchased, key=ref_key)],
        "manual_copper_positions": [manual[ref] for ref in sorted(manual, key=ref_key)],
        "separate_matched_UV_population": [row for row in passive["matched_power_population"] if row["board"] != "Main"],
        "quantity_and_release_notes": [
            "Counts apply to one wired Main PCB. The UV boards, lid controller, harnesses and programming fixtures are separate.",
            "Keep the specified wired Main R107 and matching UV R401/R501 values together.",
            "Confirm supplier price, stock, small-quantity packaging, assembly attrition and any substitutes separately.",
            "Placement, complete PCB routing, assembler acceptance and powered tests are outside this selection.",
        ],
        "fabrication_release": False,
        "stock_or_price_verified": False,
        "powered_validation": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update the reviewed selection file.")
    args = parser.parse_args()
    path = HERE / "main-order-selection.json"
    result = review()
    if args.write:
        path.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == load(path), "Reviewed Main selection differs from current inputs."
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
