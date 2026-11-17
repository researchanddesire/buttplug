"""Export the electrically checked Compass product or bench PCB for CAM review."""

import argparse
import csv
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
EVT = ROOT / "hardware/pcb/evt1"
NON_COPPER = ("F.Mask", "B.Mask", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "Edge.Cuts")
BOARDS = {"product": ("one-board", 4, 1.0), "dev": ("one-board-dev", 6, 1.6)}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def checked(status, message):
    if not status:
        raise ValueError(message)


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def stage_project(source, stem, work):
    for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_sch", ".kicad_dru"):
        path = source / (stem + suffix)
        if path.exists():
            shutil.copyfile(path, work / path.name)
    (work / "sheets").symlink_to(source / "sheets", target_is_directory=True)
    for name in ("fp-lib-table", "sym-lib-table"):
        text = (source / name).read_text()
        (work / name).write_text(text.replace("${KIPRJMOD}/", f"{source}/"))


def check_native(drc, erc):
    for field in ("ignored_checks", "unconnected_items", "violations", "schematic_parity"):
        checked(field in drc and not drc[field], f"Native DRC has findings in {field}")
    checked("ignored_checks" in erc and not erc["ignored_checks"] and erc.get("sheets"),
            "Missing ERC sheets or disabled native checks")
    checked(all(not sheet["violations"] for sheet in erc["sheets"]), "Native ERC has findings")


def check_contact_drill(drill):
    diameter = None
    tools = {}
    at = set()
    for row in drill.read_text().splitlines():
        if match := re.fullmatch(r"T(\d+)C([\d.]+)", row):
            tools[match[1]] = Decimal(match[2])
        elif match := re.fullmatch(r"T(\d+)", row):
            diameter = tools.get(match[1])
        elif diameter == Decimal("1.02"):
            if match := re.fullmatch(r"X([\d.-]+)Y([\d.-]+)", row):
                at.add(tuple(Decimal(v) for v in match.groups()))
    checked(at == {(Decimal(x), Decimal(-90)) for x in (84, 90, 96, 102)},
            f"Unexpected 1.02 mm plated target holes in CAM output: {at}")


def check_plots(work, stem, copper, thickness):
    job = work / f"{stem}-job.gbrjob"
    payload = json.loads(job.read_text())
    specs = payload["GeneralSpecs"]
    checked(specs["LayerNumber"] == len(copper) and specs["BoardThickness"] == thickness,
            "Layer count or nominal thickness differs from the source project contract")
    plots = [work / item["Path"] for item in payload["FilesAttributes"]]
    checked(len({p.name for p in plots}) == len(copper) + len(NON_COPPER), "Unexpected plot count")
    for plot in plots:
        checked(plot.read_bytes().rstrip().endswith(b"M02*"), f"Incomplete Gerber {plot.name}")
    return [job, *plots]


def cam_request(kind):
    if kind == "product":
        return (
            "Four-layer 1.00 mm FR-4, ENIG. Quote JLC3313 for 90 ohm differential USB.\n"
            "The F.Cu USB reference is In1.Cu. Nominal F.Cu width is 0.15 mm and parallel edge gap "
            "is 0.20 mm. Return the actual stack, finished copper and an impedance solve before CAM edits.\n"
            "CT1 through CT4 are 1.020 mm nominal plated holes on 3.20 mm lands. "
            "Return drill compensation and guaranteed finished range. The contact fit screen needs "
            "a finished minimum of 0.9144 mm. Quote those holes separately from ordinary vias.\n"
            "U75 B.Cu pads 2 and 3 contain 0.20 mm through drills at native coordinates "
            "(104.4, 90.85) and (104.4, 90.05) mm. Quote resin fill, planarization and plated "
            "capping for both plated vias in pads. Excellon uses the negated native Y.\n"
            "Review the 0.20 mm plated via drills, outline, mounting holes and antenna keepout. "
            "Review Standard two-side assembly handling rails and return any panel, solder mask "
            "or geometry adjustments for review.\n"
            "R21 and R43 use the RESI PTFR0805 recommended 4.00 mm land span, "
            "1.65 mm land width and 1.20 mm gap (C16003 V8 p2). Quote fixtured "
            "post-SMT installation of CT1 through CT4, and the J2 pigtail operation separately.\n"
            "Leave C12 and C22 unpopulated. Omit paste at those two references in the assembly stencil.\n"
        )
    return (
        "Six-layer 1.60 mm FR-4. Return actual stack and finished copper. "
        "Review the 0.20 mm minimum plated drill and the unchanged J110 USB-C "
        "locating holes with their local 0.15 mm hole-to-copper spacing.\n"
        "Confirm fabrication of the shell slots and assembly processing for the J110 "
        "shell tabs if automated soldering is included in the quote.\n"
        "R21 and R43 use the RESI PTFR0805 recommended 4.00 mm land span, "
        "1.65 mm land width and 1.20 mm gap (C16003 V8 p2). "
        "Quote through-hole connectors and the J2 pigtail as vendor operations.\n"
        "Leave C12 and C22 unpopulated. Omit paste at those two references in the assembly stencil.\n"
    )


def positions_and_bom(work, board_kind):
    path = work / "native-all-positions.csv"
    with path.open(newline="") as stream:
        positions = {row["Ref"]: row for row in csv.DictReader(stream)}
    candidate = EVT / "one-board/assembly-parts-candidate.csv"
    with candidate.open(newline="") as stream:
        catalog = {row["Designator"]: row for row in csv.DictReader(stream)}
    manual = EVT / "one-board/manual-positions.csv"
    with manual.open(newline="") as stream:
        no_smt = {row["Reference"]: row["Treatment"] for row in csv.DictReader(stream)}
    checked(not (no_smt.keys() & catalog.keys()), "Manual or unloaded parts appear in the SMT list")
    if board_kind == "dev":
        catalog.update({
            "J110": {"Comment": "USB-C receptacle", "Manufacturer Part Number": "USB4105-GF-A-120"},
            **{ref: {"Comment": "5.1k 1%", "Manufacturer Part Number": "RC0603FR-075K1L"}
               for ref in ("R101", "R102")},
        })
    checked(catalog.keys() <= positions.keys(), f"Missing centroid rows: {catalog.keys() - positions.keys()}")
    with (work / "assembly-centroids-for-review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("Designator", "Mid X", "Mid Y", "Layer", "Rotation"))
        for ref in sorted(catalog):
            row = positions[ref]
            writer.writerow((ref, row["PosX"], row["PosY"], row["Side"], row["Rot"]))
    with (work / "assembly-parts-for-review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("Designator", "Comment", "Footprint", "Manufacturer Part Number"))
        for ref, row in sorted(catalog.items()):
            footprint = positions[ref]["Package"]
            checked(row.get("Footprint", footprint) == footprint, f"Parts list footprint mismatch: {ref}")
            writer.writerow((ref, row["Comment"], footprint, row["Manufacturer Part Number"]))
    if board_kind == "dev":
        no_smt = {ref: note for ref, note in no_smt.items() if not ref.startswith("CT")}
    return sorted(positions.keys() - catalog.keys()), no_smt


def pack_cam(destination, files):
    hashes = {file.name: digest(file) for file in files}
    checked(len(hashes) == len(files), "Multiple CAM inputs have the same filename")
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)
    with ZipFile(destination) as archive:
        checked(archive.testzip() is None and set(archive.namelist()) == hashes.keys(), "Corrupt CAM archive")
        checked(all(sha256(archive.read(name)).hexdigest() == checksum for name, checksum in hashes.items()),
                "CAM files differ from the verified archive members")
    return hashes


def export(cli, kind, output):
    folder, layer_count, thickness = BOARDS[kind]
    source = EVT / folder
    stem = "compass-" + folder
    board_name = stem + ".kicad_pcb"
    source_paths = [source / board_name, source / (stem + ".kicad_pro"), source / (stem + ".kicad_sch")]
    source_paths.extend(sorted((source / "sheets").glob("*.kicad_sch")))
    source_paths.extend(source / name for name in ("fp-lib-table", "sym-lib-table"))
    source_paths.extend(EVT / "one-board" / name for name in (
        "assembly-parts-candidate.csv", "manual-positions.csv",
    ))
    source_paths.append(EVT / "single-flange-routing/Selected.pretty/RESI_PTFR0805_C16003.kicad_mod")
    custom_rules = source / (stem + ".kicad_dru")
    if custom_rules.exists():
        source_paths.append(custom_rules)
    bindings = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    design = json.loads(source_paths[1].read_text())["board"]["design_settings"]
    checked(not design["drc_exclusions"] and "ignore" not in design["rule_severities"].values(),
            "The source project contains hidden or ignored DRC findings")
    copper = ("F.Cu", *(f"In{i}.Cu" for i in range(1, layer_count - 1)), "B.Cu")
    checked(not output.exists(), f"Output already exists: {output}")
    with TemporaryDirectory(prefix="compass-one-board-cam-") as tmp:
        work = Path(tmp)
        stage_project(source, stem, work)
        board = work / board_name
        schematic = work / (stem + ".kicad_sch")
        with (work / "export.log").open("w") as log:
            def run(*args):
                result = subprocess.run([cli, *map(str, args)], stdout=log, stderr=log)
                checked(not result.returncode,
                        f"KiCad failed on {' '.join(map(str, args[:3]))} (exit {result.returncode})")

            run("pcb", "drc", "--refill-zones", "--save-board", "--schematic-parity",
                "--severity-all", "--format", "json", "-o", work / "drc.json", board)
            run("sch", "erc", "--severity-all", "--format", "json", "-o", work / "erc.json", schematic)
            drc, erc = (json.loads((work / name).read_text()) for name in ("drc.json", "erc.json"))
            check_native(drc, erc)
            run("pcb", "export", "gerbers", "--check-zones", "-l", ",".join(copper + NON_COPPER),
                "-o", str(work) + "/", board)
            run("pcb", "export", "drill", "--excellon-separate-th", "--excellon-units", "mm",
                "--generate-report", "--report-path", work / "drill-report.txt", "-o", str(work) + "/", board)
            run("pcb", "export", "ipcd356", "-o", work / (stem + ".d356"), board)
            run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
                "-o", work / "native-all-positions.csv", board)

        plots = check_plots(work, stem, copper, thickness)
        drills = [work / f"{stem}-{kind}.drl" for kind in ("PTH", "NPTH")]
        for drill in drills:
            contents = drill.read_text()
            checked("METRIC" in contents and contents.rstrip().endswith("M30"), f"Incomplete drill file {drill.name}")
        if kind == "product":
            check_contact_drill(drills[0])
        unlisted, no_smt = positions_and_bom(work, kind)
        archive = work / f"{stem}-cam-review.zip"
        member_hashes = pack_cam(archive, [*plots, *drills])
        (work / "cam-request.txt").write_text(cam_request(kind))
        checked(all(digest(ROOT / name) == checksum for name, checksum in bindings.items()),
                "An input changed during export")
        save_json(work / "cam-manifest.json", {
            "board": kind, "kicad_version": drc["kicad_version"], "source_sha256": bindings,
            "filled_board_sha256": digest(board), "copper_order": copper, "nominal_thickness_mm": thickness,
            "archive_sha256": digest(archive), "members_sha256": member_hashes,
            "unlisted_native_positions": unlisted,
            "manual_and_unloaded_positions": no_smt,
            "assembly_review_sha256": {name: digest(work / name) for name in (
                "native-all-positions.csv", "assembly-centroids-for-review.csv",
                "assembly-parts-for-review.csv",
            )},
            "review": "Confirm stackup, finished holes, library stock and loaded assembly orientations in CAM review.",
        })
        output.mkdir(parents=True)
        deliverables = [archive, board, work / (stem + ".d356")]
        deliverables.extend(work / name for name in (
            "cam-manifest.json", "cam-request.txt", "erc.json", "drc.json", "drill-report.txt", "export.log",
            "native-all-positions.csv", "assembly-centroids-for-review.csv", "assembly-parts-for-review.csv",
        ))
        for path in deliverables:
            shutil.copyfile(path, output / path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", choices=BOARDS)
    parser.add_argument("output", type=Path)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    args = parser.parse_args()
    try:
        export(args.kicad_cli, args.board, args.output)
    except ValueError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
