"""Export a populated bench quote from the saved JST lid candidate."""

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
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

OUT = Path(__file__).resolve().parent
LID = OUT.parent
CONTROL = LID.parent
ROOT = CONTROL.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from kicad_sexp import child, children, parse, value

STEM = "dock-lid-jst-candidate"
BOARD = LID / f"{STEM}.kicad_pcb"
PROJECT = BOARD.with_suffix(".kicad_pro")
REVISION = "fbb712251fee3de42941a4081863d6af38ff0cb1c16a4a6933a278c477f43a7a"
VERSION = "10.0.8"
SYSTEM = LID / "system-snapshot"
BARE = LID / "bench-quote"
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts"
QUOTE = "JST-lid-populated-bench-quote.zip"


def digest(data):
    return sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def footprint_text(part, key):
    return next(row[2].value for row in children(part, "fp_text") if row[1].value == key)


def xml_components(xml):
    return {c.get("ref"): c for c in xml.findall("components/comp")}


def xml_terminals(xml):
    return {(node.get("ref"), node.get("pin")):
            (net.get("name"), node.get("pintype"), node.get("pinfunction"))
            for net in xml.findall("nets/net") for node in net.findall("node")}


def export(cli, work):
    def run(*args):
        subprocess.run([cli, *map(str, args)], check=True)

    run("pcb", "drc", "--severity-all", "--exit-code-violations", "--format", "json",
        "-o", work / "drc.json", BOARD)
    run("sch", "erc", "--severity-all", "--exit-code-violations", "--format", "json",
        "-o", work / "erc.json", SYSTEM / "dock-system.kicad_sch")
    run("sch", "export", "netlist", "--format", "kicadxml",
        "-o", work / "dock-system-native.xml", SYSTEM / "dock-system.kicad_sch")
    run("pcb", "export", "gerbers", "--check-zones", "--layers", LAYERS, "-o", f"{work}/", BOARD)
    run("pcb", "export", "drill", "--drill-origin", "absolute", "--excellon-separate-th",
        "--generate-report", "--report-path", work / "drill-report.txt", "-o", f"{work}/", BOARD)
    run("pcb", "export", "ipcd356", "-o", work / f"{STEM}.d356", BOARD)
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
        "-o", work / "jst-lid-positions.csv", BOARD)
    for side, layer, mirror in (("front", "F.Fab", []), ("back", "B.Fab", ["--mirror"])):
        silkscreen = layer.replace("Fab", "SilkS")
        run("pcb", "export", "svg", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet",
            *mirror, "--layers", f"{layer},{silkscreen},Edge.Cuts", "-o", work / f"assembly-{side}.svg", BOARD)


def audit_native(work, footprints, mounting, board_nets):
    drc = read_json(work / "drc.json")
    erc = read_json(work / "erc.json")
    assert drc["kicad_version"] == erc["kicad_version"] == VERSION
    assert not any(drc[k] for k in ("violations", "unconnected_items", "ignored_checks"))
    assert not erc["ignored_checks"] and all(not sheet["violations"] for sheet in erc["sheets"])
    project = read_json(PROJECT)["board"]["design_settings"]
    assert not project["drc_exclusions"] and "ignore" not in project["rule_severities"].values()
    original = ET.parse(CONTROL.parent / "dock-system/native.xml")
    system = ET.parse(work / "dock-system-native.xml")
    components = xml_components(system)
    terminals = xml_terminals(system)
    assert len(terminals) == 812 and terminals == xml_terminals(original)
    assert len(components) == 234 and components.keys() == xml_components(original).keys()
    lid_parts = {ref: c for ref, c in components.items() if c.find("sheetpath").get("names") == "/dock-lid-ui/"}
    assert set(lid_parts) == set(footprints) - mounting | {"LCD301"}
    assert not lid_parts["LCD301"].findtext("footprint")
    assert sum(ref in lid_parts for ref, _ in terminals) == 128

    saved = read_json(LID / "native-checks.json")
    assert digest(BOARD.read_bytes()) == saved["native_board_sha256"] == REVISION
    physical = Counter((ref, pad[1].value, board_nets[value(pad, "net")])
                       for ref, part in footprints.items() if ref not in mounting
                       for pad in children(part, "pad") if pad[1].value)
    assert physical == Counter((row["ref"], row["pin"], row["net"]) for row in saved["native_pin_net_checks"])
    assert sum(physical.values()) == 109
    assert {(ref, pin): net for ref, pin, net in physical} == {
        key: data[0] for key, data in terminals.items() if key[0] in footprints
    }
    ipc = (work / f"{STEM}.d356").read_text().splitlines()
    aliases = {line[8:14].strip(): line[14:].strip() for line in ipc if line.startswith("P  NNAME")}
    records = [(line[20:26].strip(), line[27:31].strip(), line[3:17].strip())
               for line in ipc if line[:3] in {"317", "327", "367"}]
    assert Counter((ref, pin, aliases.get(net, net).upper()) for ref, pin, net in records
                   if ref in footprints and ref not in mounting) == Counter({
        (ref, pin, net.upper()): qty for (ref, pin, net), qty in physical.items()
    })
    assert len({net.upper() for _, _, net in physical}) == len({net for _, _, net in physical})
    return lid_parts


def order_tables(work, footprints, mounting, components):
    prior = {item["reference"]: item for item in read_json(CONTROL / "parts-selection.json")["parts"]
             if item["board"] == "lid"}
    assert prior.keys() == components.keys() and prior["J302"]["mpn"] == "52437-2771"
    with (work / "jst-lid-positions.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 28 and {row["Ref"] for row in rows} == set(footprints) - mounting
    assert Counter(row["Side"] for row in rows) == {"top": 17, "bottom": 11}
    groups = defaultdict(list)
    for row in rows:
        ref = row["Ref"]
        part = footprints[ref]
        comp = components[ref]
        assert comp.findtext("value") == row["Val"] == footprint_text(part, "value")
        assert comp.findtext("footprint") == part[1].value == f"DockControl:{row['Package']}"
        x, y, *rotation = map(lambda atom: float(atom.value), child(part, "at")[1:])
        assert (float(row["PosX"]), float(row["PosY"])) == (x, -y)
        assert abs((float(row["Rot"]) - (rotation or [0])[0] + 180) % 360 - 180) < 1e-6
        assert {"F.Cu": "top", "B.Cu": "bottom"}[value(part, "layer")] == row["Side"]
        fields = {field.get("name"): field.text for field in comp.findall("fields/field")}
        manufacturer, mpn = fields["Manufacturer"], fields["MPN"]
        assert manufacturer and mpn and mpn != "–"
        if ref == "J302":
            assert (manufacturer, mpn) == ("JST", "27FLZ-RSM2-TB")
        else:
            assert (manufacturer, mpn) == (prior[ref]["manufacturer"], prior[ref]["mpn"])
        groups[manufacturer, mpn].append(row)
    assert len(groups) == 8
    with (work / "jst-lid-ordered-parts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Manufacturer", "MPN", "QtyPerBoard", "References", "Value", "Footprint", "Side"])
        for (manufacturer, mpn), parts in sorted(groups.items()):
            assert len({(p["Val"], p["Package"], p["Side"]) for p in parts}) == 1
            first = parts[0]
            writer.writerow([manufacturer, mpn, len(parts), " ".join(p["Ref"] for p in parts),
                             first["Val"], first["Package"], first["Side"]])
    assert prior["LCD301"]["mpn"] == "NHD-C12864B2Z-RN-FBW"


def check_fab(work, footprints, mounting):
    saved = read_json(BARE / "manifest.json")
    bare_zip = BARE / "JST-lid-bench-gerbers.zip"
    assert digest(bare_zip.read_bytes()) == saved["fabrication_zip_sha256"]
    assert saved["source_board_sha256"] == REVISION and saved["source_project_sha256"] == digest(PROJECT.read_bytes())
    bare_files = saved["fabrication_file_sha256"]

    def without_creation_stamp(data):
        return [line for line in data.splitlines() if not any(
            marker in line for marker in (b"Created by KiCad", b"CreationDate", b"; DRILL file KiCad")
        )]

    with ZipFile(bare_zip) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == bare_files.keys()
        for name, sha in bare_files.items():
            old = archive.read(name)
            assert digest(old) == sha
            if not name.endswith(".gbrjob"):
                assert without_creation_stamp(old) == without_creation_stamp((work / name).read_bytes()), name

    job_file = work / f"{STEM}-job.gbrjob"
    job = read_json(job_file)
    with ZipFile(bare_zip) as archive:
        assert job["GeneralSpecs"] == json.loads(archive.read(job_file.name))["GeneralSpecs"]
    assert job["GeneralSpecs"]["LayerNumber"] == 4 and job["GeneralSpecs"]["BoardThickness"] == 1
    plots = {row["Path"] for row in job["FilesAttributes"]}
    assert len(plots) == 11
    for suffix, apertures in (("F_Paste.gtp", 87), ("B_Paste.gbp", 22)):
        assert (work / f"{STEM}-{suffix}").read_text().count("D03*") == apertures
    holes = {}
    for plating, tool, count in (("PTH", "0.200", 81), ("NPTH", "2.300", 4)):
        drill = (work / f"{STEM}-{plating}.drl").read_text()
        assert re.findall(r"^T\d+C([\d.]+)$", drill, flags=re.M) == [tool]
        holes[plating] = {(float(x), float(y)) for x, y in
                          re.findall(r"^X([\d.-]+)Y([\d.-]+)$", drill, flags=re.M)}
        assert len(holes[plating]) == count
    native_mounting = set()
    for ref in mounting:
        part = footprints[ref]
        pad, = children(part, "pad")
        assert pad[2].value == "np_thru_hole" and float(value(pad, "drill")) == 2.3
        x, y = [float(axis.value) for axis in child(part, "at")[1:3]]
        native_mounting.add((x, -y))
    assert holes["NPTH"] == native_mounting
    return plots | {f"{STEM}{suffix}" for suffix in ("-job.gbrjob", "-PTH.drl", "-NPTH.drl", ".d356")} | {"drill-report.txt"}


def package(work):
    tree = parse(BOARD.read_text())
    footprints = {footprint_text(part, "reference"): part for part in children(tree, "footprint")}
    board_nets = {row[1].value: row[2].value for row in children(tree, "net")}
    mounting = {f"H30{i}" for i in range(1, 5)}
    assert len(footprints) == 32 and mounting <= set(footprints)
    components = audit_native(work, footprints, mounting, board_nets)
    order_tables(work, footprints, mounting, components)
    fab_files = check_fab(work, footprints, mounting)
    evidence = ("dock-system-native.xml", "drc.json", "erc.json")
    tables = ("jst-lid-ordered-parts.csv", "jst-lid-positions.csv", "assembly-front.svg", "assembly-back.svg")
    files = {f"fab/{name}": work / name for name in fab_files}
    files.update({f"checks/{name}": work / name for name in evidence})
    files.update({name: work / name for name in tables})
    files.update({"README.md": OUT / "README.md", "checks/selected-donor-parts.json": CONTROL / "parts-selection.json",
                  "checks/saved-native-checks.json": LID / "native-checks.json"})
    native = Path("native/dock-control/lcd-socket-candidate")
    for source in (BOARD, PROJECT, LID / "fp-lib-table", *(LID / "DockControl.pretty").glob("*.kicad_mod")):
        files[str(native / source.relative_to(LID))] = source
    models = {entry[1].value.removeprefix("${KIPRJMOD}/../") for part in footprints.values()
              for entry in children(part, "model")}
    models.update({"DockControl.3dshapes/KiCad-LICENSE.md", "model-provenance.json"})
    files.update({str(native.parent / path): CONTROL / path for path in models})
    source_files = [BOARD, PROJECT, CONTROL / "parts-selection.json", BARE / "manifest.json",
                    BARE / "JST-lid-bench-gerbers.zip", CONTROL.parent / "dock-system/native.xml",
                    LID / "native-checks.json", *(SYSTEM / "sheets").glob("*.kicad_sch"),
                    SYSTEM / "dock-system.kicad_sch", SYSTEM / "dock-system.kicad_pro", Path(__file__)]
    manifest = {
        "scope": "Populated JST lid for pre-radio dock bench quote",
        "kicad_version": VERSION, "onboard_smt_positions": 28, "top": 17, "bottom": 11,
        "manufacturer_part_numbers": 8, "offboard": {"LCD301": "NHD-C12864B2Z-RN-FBW", "hinge_link": "0151660220"},
        "drc_violations": 0, "drc_unconnected": 0, "whole_system_erc_violations": 0,
        "whole_system_terminal_checks": 812, "lid_physical_pad_checks": 109,
        "fab_geometry_matches_bare_fit_quote": True,
        "J302_received_mate_verified": False, "powered_validation": False, "supplier_accepted": False,
        "source_sha256": {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in sorted(source_files)},
        "file_sha256": {name: digest(path.read_bytes()) for name, path in sorted(files.items())},
    }
    result = work / QUOTE
    with ZipFile(result, "w", compression=ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
    with ZipFile(result) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(files) | {"manifest.json"}
        assert all(digest(archive.read(name)) == sha for name, sha in manifest["file_sha256"].items())
    assert digest(BOARD.read_bytes()) == REVISION
    (OUT / QUOTE).write_bytes(result.read_bytes())
    print(f"{QUOTE}: 28 placements, 8 exact MPNs, 109 pad checks, CRC and file hashes passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="jst-lid-assembly-") as temporary:
        work = Path(temporary)
        export(args.kicad_cli, work)
        package(work)
