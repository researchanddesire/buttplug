"""Export and verify the current single-flange PCB bench quote."""

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent
EVT = SOURCE.parent
ROOT = EVT.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import kicad_sexp as sexp

BOARD = SOURCE / "single-flange.kicad_pcb"
PROJECT = BOARD.with_suffix(".kicad_pro")
PARTS = EVT / "parts-selection.json"
TARGETS = ROOT / "hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/selected-parts.json"
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")
PLOT_LAYERS = LAYERS + ("F.Mask", "B.Mask", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "Edge.Cuts")
CONTACTS = dict(zip(("CT1", "CT2", "CT3", "CT4"), ("GND", "USB_DM_CONTACT", "USB_DP_CONTACT", "DOCK_5V")))
MOUNTS = {"MH1", "MH2", "MH3", "MH4"}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_csv(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)


def pack(path, files):
    hashes = {name: digest(file) for name, file in files.items()}
    with ZipFile(path, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for name, file in sorted(files.items()):
            archive.write(file, name)
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(hashes)
        for name, expected in hashes.items():
            assert sha256(archive.read(name)).hexdigest() == expected, name
    return hashes


def export(cli, work):
    with (work / "export.log").open("w") as log:
        def run(*args):
            subprocess.run([cli, *map(str, args)], stdout=log, stderr=log, check=True)

        run("pcb", "drc", "--severity-all", "--exit-code-violations", "--format", "json", "-o", work / "drc.json", BOARD)
        run("sch", "erc", "--severity-all", "--exit-code-violations", "--format", "json", "-o", work / "erc.json", SOURCE / "single-flange-system.kicad_sch")
        run("pcb", "export", "gerbers", "--check-zones", "--output", str(work) + "/", "--layers", ",".join(PLOT_LAYERS), BOARD)
        run("pcb", "export", "drill", "--output", str(work) + "/", "--excellon-separate-th", "--generate-report", "--report-path", work / "drill-report.txt", BOARD)
        run("pcb", "export", "ipcd356", "-o", work / "single-flange.d356", BOARD)
        run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", work / "single-flange-native-all-positions.csv", BOARD)
        for layer, side in (("F.Fab", "front"), ("B.Fab", "back")):
            run("pcb", "export", "svg", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "--layers", layer + ",Edge.Cuts", "--output", work / f"assembly-{side}.svg", BOARD)
        for view, side in (("front", "top"), ("back", "bottom")):
            run("pcb", "render", "--width", 1100, "--height", 490, "--zoom", 1.42, "--background", "opaque", "--side", side, "--output", work / f"preview-{view}.png", BOARD)


def read_artwork():
    tree = sexp.parse(BOARD.read_text())
    footprints = {}
    for fp in sexp.children(tree, "footprint"):
        fields = {node[1].value: node[2].value for node in sexp.children(fp, "fp_text")}
        footprints[fields["reference"]] = (fp, fields["value"])
    assert len(footprints) == 43
    return tree, footprints


def check_positions(path, footprints):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        assert fields == ["Ref", "Val", "Package", "PosX", "PosY", "Rot", "Side"]
        rows = [tuple(row[f] for f in fields) for row in reader]
    assert len(rows) == 43 and {row[0] for row in rows} == set(footprints)
    for ref, value, package, x, y, rot, side in rows:
        fp, native_value = footprints[ref]
        at = sexp.child(fp, "at")
        theta = Decimal(at[3].value) if len(at) > 3 else Decimal(0)
        assert value == native_value
        assert package == fp[1].value.split(":")[-1]
        assert (Decimal(x), Decimal(y)) == (Decimal(at[1].value), -Decimal(at[2].value))
        assert (Decimal(rot) - theta) % 360 == 0
        assert side == {"F.Cu": "top", "B.Cu": "bottom"}[sexp.value(fp, "layer")]
    return fields, rows


def compare_electrical(footprints, native, d356):
    root = ET.parse(SOURCE / "single-flange-native.xml").getroot()
    parts = {part.get("ref"): part for part in root.findall("./components/comp")}
    terminal = {
        (node.get("ref"), node.get("pin")): net.get("name")
        for net in root.findall("./nets/net")
        for node in net.findall("node")
    }
    assert set(parts) == set(footprints) - MOUNTS
    assert len(parts) == 39 and len(terminal) == 155
    pads = Counter()
    hold_down = Counter()
    for ref, (fp, value) in footprints.items():
        if ref in MOUNTS:
            continue
        assert fp[1].value == parts[ref].findtext("footprint")
        assert value == parts[ref].findtext("value")
        for pad in sexp.children(fp, "pad"):
            pin = pad[1].value
            net = sexp.child(pad, "net")
            if pin == "MP":
                assert net is None
                hold_down[ref, pin, "N/C"] += 1
                continue
            assert pin and net is not None
            name = net[2].value
            assert name == terminal[ref, pin]
            pads[ref, pin, name] += 1
    assert sum(pads.values()) == 163
    assert {(ref, pin): net for ref, pin, net in pads} == terminal
    assert pads == Counter((p["ref"], p["pad"], p["net"]) for p in native["native_pad_contracts"])
    assert hold_down == Counter({("J4", "MP", "N/C"): 2, ("J7", "MP", "N/C"): 2})

    aliases = {}
    exported = Counter()
    mounts = Counter()
    vias = 0
    for line in d356.read_text().splitlines():
        if line.startswith("P  NNAME"):
            alias, net = line[8:].split(None, 1)
            aliases[alias] = net.strip()
        if line.startswith(("317", "327", "367")):
            ref, pin, net = line[20:26].strip(), line[27:31].strip(), line[3:17].strip()
            if ref == "VIA":
                vias += 1
            elif ref in MOUNTS:
                assert line.startswith("367") and net == "N/C"
                mounts[ref] += 1
            else:
                exported[ref, pin, aliases.get(net, net)] += 1
    assert pads + hold_down == exported
    assert mounts == Counter(MOUNTS) and vias == native["vias"] == 91
    return parts


def check_drill(path):
    text = path.read_text()
    assert "absolute / metric / decimal" in text and text.rstrip().endswith("M30")
    diameters = {}
    hits = defaultdict(list)
    tool = None
    for line in text.splitlines():
        if match := re.fullmatch(r"(T\d+)C([.\d]+)", line):
            diameters[match[1]] = Decimal(match[2])
        elif line in diameters:
            tool = diameters[line]
        elif match := re.fullmatch(r"X(-?[.\d]+)Y(-?[.\d]+)", line):
            assert tool is not None
            hits[tool].append(tuple(map(Decimal, match.groups())))
    return hits


def make_quote(work):
    before = digest(BOARD)
    native = load_json(SOURCE / "native-checks.json")
    assert native["board_sha256"] == before
    for name, expected in native["reports_sha256"].items():
        assert digest(SOURCE / name) == expected, name
    for name, expected in native["source_invariant_sha256"].items():
        assert digest(EVT / name) == expected, name
    assert digest(PROJECT) == native["all_local_source_sha256"][PROJECT.name]
    frozen_erc = load_json(SOURCE / "system-erc.json")
    new_drc = load_json(work / "drc.json")
    new_erc = load_json(work / "erc.json")
    assert new_drc["kicad_version"] == new_erc["kicad_version"] == frozen_erc["kicad_version"] == "10.0.8"
    assert not any(new_drc[key] for key in ("ignored_checks", "unconnected_items", "violations", "schematic_parity"))
    assert new_erc["ignored_checks"] == [] and all(not sheet["violations"] for sheet in new_erc["sheets"])
    design = load_json(PROJECT)["board"]["design_settings"]
    assert not design["drc_exclusions"] and "ignore" not in design["rule_severities"].values()

    tree, footprints = read_artwork()
    fields, positions = check_positions(work / "single-flange-native-all-positions.csv", footprints)
    parts = compare_electrical(footprints, native, work / "single-flange.d356")
    parts_selection = load_json(PARTS)
    selected = {
        row["ref"]: row for row in parts_selection["components"]
        if row["domain"] in ("flange", "sensor") and row["purchase"]
    }
    assert set(selected) == set(parts) - CONTACTS.keys() and len(selected) == 35
    groups = defaultdict(list)
    for ref, row in selected.items():
        part = parts[ref]
        assert row["manufacturer"] and row["mpn"] and row["manufacturer_source"]
        assert row["schematic_value"] == part.findtext("value")
        assert row["footprint"].split(":")[-1] == part.findtext("footprint").split(":")[-1]
        assert "smd" in [item.value for item in sexp.child(footprints[ref][0], "attr")[1:]]
        groups[row["manufacturer"], row["mpn"]].append(ref)
    assert len(groups) == 21
    smt_rows = [row for row in positions if row[0] in selected]
    assert Counter(row[-1] for row in smt_rows) == {"top": 2, "bottom": 33}
    write_csv(work / "single-flange-smt-positions.csv", fields, smt_rows)
    order_rows = []
    for (maker, mpn), refs in sorted(groups.items()):
        notes = sorted({selected[r]["assembly_note"] for r in refs if selected[r].get("assembly_note")})
        sources = {selected[r]["manufacturer_source"] for r in refs}
        assert len(sources) == 1
        order_rows.append([
            maker, mpn, len(refs), " ".join(sorted(refs)),
            " / ".join(sorted({parts[r].findtext("value") for r in refs})),
            " / ".join(sorted({parts[r].findtext("footprint") for r in refs})),
            " ".join(notes), sources.pop(),
        ])
    write_csv(work / "single-flange-smt-parts.csv", [
        "Manufacturer", "MPN", "Quantity_per_board", "References", "Schematic_value", "Footprint", "Assembly_note", "Manufacturer_source",
    ], order_rows)

    target = load_json(TARGETS)["selected_targets"]
    assert target["qty"] == len(CONTACTS) == 4
    target_rows = []
    for ref, value, _, x, y, _, side in positions:
        if ref not in CONTACTS:
            continue
        assert value == target["mpn"] and side == "top"
        pad, = sexp.children(footprints[ref][0], "pad")
        assert pad[2].value == "thru_hole"
        assert float(sexp.value(pad, "drill")) == target["recommended_mounting_hole_mm"]
        assert [float(i.value) for i in sexp.child(pad, "size")[1:]] == [target["proposed_copper_land_mm"]] * 2
        target_rows.append([ref, target["manufacturer"], target["mpn"], 1, CONTACTS[ref], x, y, side, target["primary_catalog"]])
    write_csv(work / "single-flange-manual-targets.csv", [
        "Reference", "Manufacturer", "MPN", "Quantity_per_board", "Net", "Native_PosX_mm", "Native_PosY_mm", "Side", "Manufacturer_source",
    ], target_rows)

    pth = check_drill(work / "single-flange-PTH.drl")
    npth = check_drill(work / "single-flange-NPTH.drl")
    assert {k: len(v) for k, v in pth.items()} == {Decimal(".200"): 91, Decimal(".864"): 4}
    assert {k: len(v) for k, v in npth.items()} == {Decimal("1.600"): 4}
    for drill, refs in ((pth[Decimal(".864")], CONTACTS), (npth[Decimal("1.600")], MOUNTS)):
        assert set(drill) == {(Decimal(row[3]), Decimal(row[4])) for row in positions if row[0] in refs}

    job_path = work / "single-flange-job.gbrjob"
    job = load_json(job_path)
    general = job["GeneralSpecs"]
    assert general["LayerNumber"] == 4 and general["BoardThickness"] == 1.0
    assert general["Finish"] == "ENIG candidate"
    plots = {entry["Path"]: work / entry["Path"] for entry in job["FilesAttributes"]}
    assert len(plots) == len(PLOT_LAYERS)
    for plot in plots.values():
        assert plot.read_bytes().rstrip().endswith(b"M02*"), plot
    board_stack = sexp.child(sexp.child(tree, "setup"), "stackup")
    stack_mm = {
        layer[1].value: float(sexp.value(layer, "thickness"))
        for layer in sexp.children(board_stack, "layer") if sexp.child(layer, "thickness")
    }
    assert abs(sum(stack_mm.values()) - general["BoardThickness"]) < 1e-9
    fab_request = work / "fabrication-request.json"
    write_json(fab_request, {
        "scope": "Bare board bench quote",
        "nominal_finished_thickness_mm": general["BoardThickness"],
        "copper_layer_order": LAYERS,
        "stackup_mm": stack_mm,
        "material": "FR-4",
        "finish_requested": "ENIG",
        "trace_width_clearance_min_mm": [design["rules"]["min_track_width"], design["rules"]["min_clearance"]],
        "via_diameter_drill_mm": [0.5, 0.2],
        "target_hole_native_mm": target["recommended_mounting_hole_mm"],
        "target_hole_excellon_mm": 0.864,
        "target_copper_land_diameter_mm": target["proposed_copper_land_mm"],
        "mechanical_NPTH_mm": 1.6,
        "absolute_mm_plot_and_drill_origin": True,
        "supplier_review": "Confirm stackup and finished thickness, hole and annular tolerances, target fit, antenna keepout, outline, mask registration and USB stack suitability.",
    })
    fab_files = {**plots, **{
        name: work / name for name in (
            job_path.name, "single-flange-PTH.drl", "single-flange-NPTH.drl",
            "single-flange.d356", "drill-report.txt", fab_request.name,
        )
    }}
    fab = work / "single-flange-evt1-fabrication-quote.zip"
    fab_hashes = pack(fab, fab_files)
    fab_manifest = work / "fabrication-manifest.json"
    write_json(fab_manifest, {
        "board_sha256": before, "kicad_version": new_drc["kicad_version"],
        "zip_sha256": digest(fab), "files": fab_hashes,
    })
    files = {
        "README.md": OUT / "README.md", BOARD.name: BOARD, PROJECT.name: PROJECT,
        **{name: work / name for name in (
            fab.name, fab_manifest.name, "drc.json", "erc.json",
            "single-flange-smt-parts.csv", "single-flange-smt-positions.csv",
            "single-flange-manual-targets.csv", "single-flange-native-all-positions.csv",
            "assembly-front.svg", "assembly-back.svg", "preview-front.png", "preview-back.png",
        )},
    }
    library_table = sexp.parse((SOURCE / "fp-lib-table").read_text())
    for library in sexp.children(library_table, "lib"):
        if sexp.value(library, "name") != "Selected":
            library_table.remove(library)
    table = work / "fp-lib-table"
    sexp.write(table, library_table)
    files[table.name] = table
    for directory in ("Selected.pretty", "Selected.3dshapes"):
        for file in (SOURCE / directory).iterdir():
            if file.suffix in (".kicad_mod", ".step"):
                files[str(file.relative_to(SOURCE))] = file
    sources = [BOARD, PROJECT, PARTS, TARGETS, SOURCE / "fp-lib-table", EVT / "body/body-evt1.kicad_pcb",
               SOURCE / "native-checks.json", SOURCE / "schematic-checks.json",
               SOURCE / "single-flange-native.xml", SOURCE / "system-native.xml"]
    manifest = work / "manifest.json"
    write_json(manifest, {
        "scope": "Single-flange PCB bench fabrication and assembly quote",
        "kicad_version": new_drc["kicad_version"],
        "source_sha256": {str(file.relative_to(ROOT)): digest(file) for file in sources},
        "smt_positions": len(smt_rows),
        "smt_purchase_lines": len(order_rows),
        "purchased_manual_targets": len(target_rows),
        "native_placement_checks": len(positions),
        "ipc_d_356_electrical_pad_instances": 163,
        "logical_terminal_checks": 155,
        "plated_vias": 91,
        "plated_target_holes": 4,
        "unplated_mounting_holes": 4,
        "native_erc_drc_violations": 0,
        "files": {name: digest(path) for name, path in files.items()},
        "exporter_sha256": digest(Path(__file__)),
        "supplier_acceptance": False,
        "physical_validation": False,
    })
    files[manifest.name] = manifest
    assembly_zip = work / "single-flange-evt1-assembly-quote.zip"
    pack(assembly_zip, files)
    assert digest(BOARD) == before
    assert digest(EVT / "body/body-evt1.kicad_pcb") == native["source_invariant_sha256"]["body/body-evt1.kicad_pcb"]
    for name, file in files.items():
        if file.parent == work:
            shutil.copyfile(file, OUT / name)
    for file in (assembly_zip, work / "drill-report.txt", fab_request, work / "single-flange.d356"):
        shutil.copyfile(file, OUT / file.name)
    print("Quote exported: 35 SMT placements, 21 SMT order lines, 4 manual targets, 163 native electrical pads.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="single-flange-quote-") as directory:
        work = Path(directory)
        export(args.kicad_cli, work)
        make_quote(work)


if __name__ == "__main__":
    main()
