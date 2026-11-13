"""Export the frozen pre-radio Main PCB for fabrication and assembly quotes."""

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

OUT = Path(__file__).resolve().parent
MAIN = OUT.parent
EVT = MAIN.parent
REPO = EVT.parents[2]
sys.path.insert(0, str(REPO / "tools"))
from kicad_sexp import child, children, parse, value

BOARD = MAIN / "dock-main.kicad_pcb"
BOARD_REVISION = "e10043f2fa456c4a88848a612f13ad501c49fdee64e4a509484fa86a7a5c674b"
VERSION = "10.0.8"
SYSTEM = EVT / "dock-system" / "dock-system.kicad_sch"
LEAVES = {"/dock-ui-source/", "/dock-controller/", "/dock-safety/"}
SELECTIONS = tuple(EVT / name for name in (
    "dock-ui/source-circuit-parts.json",
    "dock-control/parts-selection.json",
    "dock-safety/parts-selection.json",
))
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts"
FAB_FILES = (
    "dock-main-F_Cu.gtl", "dock-main-In1_Cu.g1", "dock-main-In2_Cu.g2", "dock-main-B_Cu.gbl",
    "dock-main-F_Mask.gts", "dock-main-B_Mask.gbs", "dock-main-F_Paste.gtp", "dock-main-B_Paste.gbp",
    "dock-main-F_Silkscreen.gto", "dock-main-B_Silkscreen.gbo", "dock-main-Edge_Cuts.gm1",
    "dock-main-job.gbrjob", "dock-main-PTH.drl", "dock-main-NPTH.drl", "dock-main.d356", "drill-report.txt",
)


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def footprint_text(footprint, kind):
    return next(row[2].value for row in children(footprint, "fp_text") if row[1].value == kind)


def write_csv(path, header, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def export(cli, work):
    def run(*args):
        subprocess.run([cli, *map(str, args)], check=True)

    run("pcb", "drc", "--severity-all", "--exit-code-violations", "--format", "json",
        "-o", work / "drc.json", BOARD)
    run("sch", "erc", "--severity-all", "--exit-code-violations", "--format", "json",
        "-o", work / "erc.json", SYSTEM)
    run("sch", "export", "netlist", "--format", "kicadxml",
        "-o", work / "dock-system-native.xml", SYSTEM)
    run("pcb", "export", "gerbers", "--check-zones", "--output", f"{work}/",
        "--layers", LAYERS, BOARD)
    run("pcb", "export", "drill", "--output", f"{work}/", "--excellon-separate-th",
        "--generate-report", "--report-path", work / "drill-report.txt", BOARD)
    run("pcb", "export", "ipcd356", "-o", work / "dock-main.d356", BOARD)
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
        "-o", work / "dock-main-all-positions.csv", BOARD)
    for side, layer in (("front", "F.Fab"), ("back", "B.Fab")):
        run("pcb", "export", "svg", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet",
            "--layers", f"{layer},Edge.Cuts", "--output", work / f"assembly-{side}.svg", BOARD)


def check_native(work):
    existing = read_json(MAIN / "native-checks.json")
    assert digest(BOARD) == existing["board_sha256"] == BOARD_REVISION
    drc = read_json(work / "drc.json")
    erc = read_json(work / "erc.json")
    assert drc["kicad_version"] == erc["kicad_version"] == VERSION
    assert not (drc["violations"] or drc["unconnected_items"] or drc["schematic_parity"])
    assert all(not sheet["violations"] for sheet in erc["sheets"])
    project_rules = read_json(BOARD.with_suffix(".kicad_pro"))["board"]["design_settings"]
    assert not project_rules["drc_exclusions"]
    assert "ignore" not in project_rules["rule_severities"].values()

    tree = parse(BOARD.read_text())
    all_parts = {footprint_text(node, "reference"): node for node in children(tree, "footprint")}
    library_nets = {row[1].value: row[2].value for row in children(tree, "net")}
    electrical = {}
    xml = ET.parse(work / "dock-system-native.xml")
    for comp in xml.findall("components/comp"):
        if comp.find("sheetpath").get("names") in LEAVES and comp.findtext("footprint"):
            ref = comp.get("ref")
            assert ref not in electrical
            electrical[ref] = comp
    mounts = {item["ref"] for item in existing["mechanical_NPTH_holes"]}
    assert set(all_parts) == electrical.keys() | mounts and len(electrical) == 150
    native_nets = {}
    for net in xml.findall("nets/net"):
        for node in net.findall("node"):
            if node.get("ref") in electrical:
                key = (node.get("ref"), node.get("pin"))
                assert key not in native_nets
                native_nets[key] = net.get("name")

    physical = Counter()
    for ref, comp in electrical.items():
        part = all_parts[ref]
        assert part[1].value == comp.findtext("footprint")
        assert footprint_text(part, "value") == comp.findtext("value")
        for pad in children(part, "pad"):
            pin = pad[1].value
            if pin:
                physical[ref, pin, library_nets[value(pad, "net")]] += 1
    assert {(ref, pin): net for ref, pin, net in physical} == native_nets
    assert physical == Counter((row["ref"], row["pad"], row["net"]) for row in existing["native_pad_checks"])
    assert len(native_nets) == 534 and sum(physical.values()) == 546

    lines = (work / "dock-main.d356").read_text().splitlines()
    aliases = {line[8:14].strip(): line[14:].strip() for line in lines if line.startswith("P  NNAME")}
    ipc_pads = Counter()
    for line in lines:
        if line[:3] in {"317", "327", "367"}:
            ref, pin, net = line[20:26].strip(), line[27:31].strip(), line[3:17].strip()
            if ref in electrical and pin:
                ipc_pads[ref, pin, aliases.get(net, net).upper()] += 1
    # IPC-D-356 folds short net names to uppercase. Confirm this loses no distinct nets.
    assert len({net.upper() for net in native_nets.values()}) == len(set(native_nets.values()))
    assert ipc_pads == Counter({(r, p, n.upper()): count for (r, p, n), count in physical.items()})
    return all_parts, electrical, existing


def check_fabrication(work, all_parts, existing):
    drills = {}
    for plating in ("PTH", "NPTH"):
        content = (work / f"dock-main-{plating}.drl").read_text()
        tools = dict(re.findall(r"^(T\d+)C([.\d]+)$", content, flags=re.MULTILINE))
        events = defaultdict(list)
        for row in content.splitlines():
            if row in tools:
                selected = tools[row]
            elif row.startswith("X"):
                events[selected].append(row)
        drills[plating] = events
    pth, npth = drills["PTH"], drills["NPTH"]
    assert {size: len(rows) for size, rows in pth.items()} == {"0.200": 284, "0.600": 4}
    assert sum("G85" in row for rows in pth.values() for row in rows) == 4
    assert {size: len(rows) for size, rows in npth.items()} == {"0.650": 2, "0.991": 3, "2.300": 6}
    assert not any("G85" in row for rows in npth.values() for row in rows)
    mounts = set()
    for hole in existing["mechanical_NPTH_holes"]:
        part = all_parts[hole["ref"]]
        pad, = children(part, "pad")
        assert pad[2].value == "np_thru_hole" and float(value(pad, "drill")) == hole["NPTH_mm"] == 2.3
        x, y = (float(axis.value) for axis in child(part, "at")[1:3])
        mounts.add((x, -y))
    assert mounts == {
        tuple(map(float, re.fullmatch(r"X([.\d-]+)Y([.\d-]+)", row).groups()))
        for row in npth["2.300"]
    }

    job = read_json(work / "dock-main-job.gbrjob")
    assert job["GeneralSpecs"]["LayerNumber"] == 4
    assert job["GeneralSpecs"]["BoardThickness"] == 1.0
    # The copper outline strokes add 0.05 mm to KiCad's report of the plotted bounding box.
    assert job["GeneralSpecs"]["Size"] == {"X": 96.05, "Y": 72.05}
    for name in FAB_FILES:
        assert (work / name).stat().st_size > 0


def order_tables(work, all_parts, electrical, existing):
    selected = {}
    for source in SELECTIONS:
        for item in read_json(source)["parts"]:
            ref = item["reference"]
            if ref in electrical:
                assert ref not in selected
                assert item["footprint"] == all_parts[ref][1].value
                assert item.get("value", footprint_text(all_parts[ref], "value")) == footprint_text(all_parts[ref], "value")
                selected[ref] = item
    assert selected.keys() == electrical.keys()
    coverage = read_json(MAIN / "model-coverage-final.json")["references"]
    assert {item["reference"] for item in coverage} == electrical.keys()
    copper = {item["reference"] for item in coverage if item["copper_only"]}
    assert copper == {"J102", "J103", "J104", "J202", "TP201", *(f"TP{i}" for i in range(601, 608))}
    assert selected["R107"]["mpn"] == "RT0603BRD0734K8L"
    assert selected["J101"]["mpn"] == "USB4105-GF-A-120"
    purchased = selected.keys() - copper
    groups = defaultdict(list)
    poses = {row["ref"]: row["dock_xy_native_angle"] for row in existing["selected_part_placements"]}
    with (work / "dock-main-all-positions.csv").open(newline="") as stream:
        native = {row["Ref"]: row for row in csv.DictReader(stream)}
    assert native.keys() == purchased | {"J102", "J103", "J104"}
    positions = []
    for ref in sorted(purchased):
        part, position = selected[ref], native[ref]
        manufacturer, mpn = part["manufacturer"], part["mpn"]
        assert manufacturer.strip() not in {"", "-", "–"} and mpn.strip() not in {"", "-", "–"}
        assert not part.get("offboard", False)
        assert position["Side"] == "top" and position["Val"] == footprint_text(all_parts[ref], "value")
        assert position["Package"] == part["footprint"].split(":")[1]
        x, y, angle = poses[ref]
        assert abs(float(position["PosX"]) - (100 + x)) < 0.00001
        assert abs(float(position["PosY"]) - (y - 200)) < 0.00001
        assert abs((float(position["Rot"]) - angle + 180) % 360 - 180) < 0.00001
        groups[manufacturer, mpn].append(ref)
        positions.append(position)
    assert len(positions) == 138 and len(groups) == 45
    orders = []
    for (manufacturer, mpn), refs in sorted(groups.items()):
        values = sorted({footprint_text(all_parts[ref], "value") for ref in refs})
        footprints = sorted({selected[ref]["footprint"] for ref in refs})
        orders.append({
            "Manufacturer": manufacturer, "MPN": mpn, "QtyPerBoard": len(refs),
            "References": " ".join(refs), "Values": " | ".join(values), "Footprints": " | ".join(footprints),
            "AssemblyProcess": "SMT with plated shell stakes" if refs == ["J101"] else "SMT",
        })
    manual = [{"Reference": ref, "Function": footprint_text(all_parts[ref], "value"),
               "Footprint": selected[ref]["footprint"], "QtyPurchased": 0} for ref in sorted(copper)]
    write_csv(work / "dock-main-ordered-parts.csv", tuple(orders[0]), orders)
    write_csv(work / "dock-main-assembly-positions.csv", tuple(positions[0]), positions)
    write_csv(work / "dock-main-copper-only.csv", tuple(manual[0]), manual)


def check_uv_quotes():
    budget = read_json(EVT / "dock-safety" / "power-budget.json")
    driver = next(item for item in budget.values() if isinstance(item, dict) and "RSET_ohm" in item)
    assert driver["RSET_ohm"] == 3.65 and driver["RSET_mpn"] == "CRCW08053R65FKEA"
    matched = {}
    for side, resistor in (("base", "R401"), ("lid", "R501")):
        uv = EVT / "dock-uv" / side / "pcb" / "fabrication-review"
        quote = uv / f"uv-{side}-supplier-review.zip"
        with ZipFile(quote) as archive:
            assert archive.testzip() is None
            lines = archive.read("onboard-selected-parts.csv").decode().splitlines()
            parts = {row["Reference"]: row for row in csv.DictReader(lines)}
            assert parts[resistor]["MPN"] == driver["RSET_mpn"]
            assert parts[resistor]["Value"].startswith("3.65R")
            uv_manifest = json.loads(archive.read("manifest.json"))
        matched[side] = {
            "relative_quote": str(quote.relative_to(EVT)),
            "archive_sha256": digest(quote),
            "board_sha256": uv_manifest["board_sha256"],
            "current_set_ref": resistor,
            "current_set_mpn": driver["RSET_mpn"],
            "current_set_ohm": driver["RSET_ohm"],
        }
    return matched


def pack(work, name, files, summary):
    manifest = dict(summary, files_sha256={entry: digest(source) for entry, source in sorted(files.items())})
    payload = json.dumps(manifest, indent=2) + "\n"
    path = work / name
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for entry, source in sorted(files.items()):
            archive.write(source, entry)
        archive.writestr("manifest.json", payload)
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == files.keys() | {"manifest.json"}
        assert json.loads(archive.read("manifest.json")) == manifest
        assert all(sha256(archive.read(entry)).hexdigest() == expected
                   for entry, expected in manifest["files_sha256"].items())
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kicad-cli", default="kicad-cli")
    args = parser.parse_args()
    assert digest(BOARD) == BOARD_REVISION
    with TemporaryDirectory() as temp:
        work = Path(temp)
        export(args.kicad_cli, work)
        all_parts, electrical, existing = check_native(work)
        check_fabrication(work, all_parts, existing)
        order_tables(work, all_parts, electrical, existing)
        assert digest(BOARD) == BOARD_REVISION
        uv_quotes = check_uv_quotes()
        summary = {
            "candidate": "Pre-radio dock Main bench quote with pre-radio 3.65 ohm UV boards",
            "board_sha256": BOARD_REVISION,
            "kicad_version": VERSION,
            "matched_uv_quotes": uv_quotes,
            "pcb_drc_violations": 0,
            "pcb_drc_unconnected": 0,
            "schematic_erc_violations": 0,
            "schematic_terminals_matched": 534,
            "board_and_ipc_physical_electrical_pads_matched": 546,
            "purchased_positions": 138,
            "manufacturer_part_lines": 45,
            "electrical_copper_only_references": 12,
            "supplier_acceptance": False,
            "powered_result": False,
            "fabrication_release": False,
        }
        audit = {
            "checks/drc.json": work / "drc.json",
            "checks/native-checks.json": MAIN / "native-checks.json",
            "checks/native-board-binding.json": MAIN / "drc-board-binding.json",
            "MFG-SPEC.md": MAIN / "MFG-SPEC.md",
            "build-constraints.json": MAIN / "build-constraints.json",
        }
        fab = {"fab/" + name: work / name for name in FAB_FILES}
        bare = pack(work, "dock-main-fabrication-quote.zip", fab | audit, summary)
        assembly = {
            name: work / name for name in (
                "dock-main-ordered-parts.csv", "dock-main-assembly-positions.csv", "dock-main-copper-only.csv",
                "assembly-front.svg", "assembly-back.svg",
            )
        }
        native_files = [BOARD, BOARD.with_suffix(".kicad_dru"), BOARD.with_suffix(".kicad_pro"),
                        MAIN / "fp-lib-table", MAIN / "footprint-provenance.json"]
        native_files += sorted(MAIN.glob("*.pretty/*.kicad_mod"))
        native_files += sorted(path for path in (MAIN / "DockMain.3dshapes").iterdir()
                               if path.suffix in {".step", ".json", ".md"})
        assembly |= {f"native/{path.relative_to(MAIN)}": path for path in native_files}
        assembly |= {
            "README.md": OUT / "README.md",
            "checks/erc.json": work / "erc.json",
            "checks/dock-system-native.xml": work / "dock-system-native.xml",
            "checks/dock-main-all-positions.csv": work / "dock-main-all-positions.csv",
            "checks/model-coverage-final.json": MAIN / "model-coverage-final.json",
            "checks/pre-radio-power-budget.json": EVT / "dock-safety" / "power-budget.json",
            **{f"checks/part-sources/{path.parent.name}-{path.name}": path for path in SELECTIONS},
        }
        full = pack(work, "dock-main-assembly-quote.zip", fab | audit | assembly, summary)
        for archive in (bare, full):
            (OUT / archive.name).write_bytes(archive.read_bytes())
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
