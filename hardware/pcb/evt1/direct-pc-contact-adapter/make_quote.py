"""Export native-verified fabrication and assembly quote inputs."""

import argparse
from collections import defaultdict
from decimal import Decimal
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from build_schematic import HERE, NAME, PARTS

SCHEMATIC = HERE / f"{NAME}.kicad_sch"
BOARD = HERE / f"{NAME}.kicad_pcb"
GERBER_LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,F.Paste,Edge.Cuts"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_native(netlist):
    tree = ET.parse(netlist)
    actual_pins = {(pin.get("ref"), pin.get("pin")): net.get("name")
                   for net in tree.findall("./nets/net") for pin in net.findall("node")
                   if not net.get("name").startswith("unconnected-") and not pin.get("ref").startswith("#")}
    expected_pins = {(record[0], pin): net for record in PARTS for pin, net in record[5].items()}
    assert actual_pins == expected_pins, (actual_pins.keys() - expected_pins.keys(),
                                         expected_pins.keys() - actual_pins.keys())
    components = {part.get("ref"): part for part in tree.findall("./components/comp")}
    assert components.keys() == {record[0] for record in PARTS}, components.keys()
    return components, len(actual_pins)


def write_bom(components, path):
    groups = defaultdict(list)
    for ref, part in components.items():
        fields = {field.get("name"): field.text for field in part.findall("./fields/field")}
        groups[(part.findtext("value"), part.findtext("footprint").split(":", 1)[1],
                fields["LCSC"], fields["Manufacturer"], fields["MPN"])].append(ref)

    with path.open("w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(("Comment", "Designator", "Footprint", "LCSC Part #", "Manufacturer", "MPN"))
        for (value, footprint, lcsc, manufacturer, mpn), refs in sorted(
                groups.items(), key=lambda group: sorted(group[1])[0]):
            writer.writerow((value, ",".join(sorted(refs)), footprint, lcsc, manufacturer, mpn))


def write_cpl(source, components, destination):
    with source.open(newline="") as native, destination.open("w", newline="") as out:
        rows = list(csv.DictReader(native))
        assert len(rows) == len(components) and {row["Ref"] for row in rows} == components.keys()
        assert all(row["Side"] == "top" for row in rows), rows
        writer = csv.writer(out)
        writer.writerow(("Designator", "Mid X", "Mid Y", "Layer", "Rotation"))
        for row in rows:
            ref = row["Ref"]
            x, y = Decimal(row["PosX"]), Decimal(row["PosY"])
            if ref == "J2":
                # The stock PH footprint origin is pin 1. Its F.Fab housing
                # rectangle has center (3, 0.55) in the footprint frame.
                assert Decimal(row["Rot"]) == 180
                x -= Decimal("3")
                y += Decimal("0.55")
            writer.writerow((ref, f"{x:.6f}", f"{y:.6f}", "Top", row["Rot"]))


def export(kicad, destination):
    destination.mkdir(parents=True, exist_ok=True)

    def cli(*args):
        subprocess.run((kicad, *args), check=True)

    with TemporaryDirectory(prefix="compass-contact-quote-") as directory:
        temp = Path(directory)
        erc, drc, netlist = (temp / item for item in ("erc.json", "drc.json", "native.xml"))
        cli("sch", "erc", "--format", "json", "--severity-all", "--exit-code-violations", "-o", erc, SCHEMATIC)
        cli("pcb", "drc", "--format", "json", "--schematic-parity", "--severity-all",
            "--exit-code-violations", "-o", drc, BOARD)
        cli("sch", "export", "netlist", "--format", "kicadxml", "-o", netlist, SCHEMATIC)
        components, pins = read_native(netlist)

        gerber_path = temp / "gerber"
        gerber_path.mkdir()
        cli("pcb", "export", "gerbers", "-o", str(gerber_path) + "/", "--layers", GERBER_LAYERS,
            "--use-drill-file-origin", "--subtract-soldermask", BOARD)
        cli("pcb", "export", "drill", "-o", str(gerber_path) + "/", "--format", "excellon",
            "--drill-origin", "plot", "--excellon-separate-th", "--excellon-oval-format", "route", BOARD)
        gerbers = destination / f"{NAME}-gerbers.zip"
        with ZipFile(gerbers, "w", ZIP_DEFLATED) as zip_file:
            for path in sorted(gerber_path.iterdir()):
                zip_file.write(path, path.name)

        pos = temp / "positions.csv"
        cli("pcb", "export", "pos", "--format", "csv", "--units", "mm",
            "--side", "both", "--use-drill-file-origin", "-o", pos, BOARD)
        bom = destination / f"{NAME}-bom.csv"
        cpl = destination / f"{NAME}-cpl.csv"
        write_bom(components, bom)
        write_cpl(pos, components, cpl)

    sources = [SCHEMATIC, BOARD, BOARD.with_suffix(".kicad_pro"), BOARD.with_suffix(".kicad_dru"),
               HERE / "fp-lib-table", HERE / "sym-lib-table", HERE / "ContactAdapter.kicad_sym",
               *sorted((HERE / "ContactAdapter.pretty").glob("*.kicad_mod"))]
    status = {
        "revision": "EVT1-EA1",
        "status": "bench evaluation quote inputs",
        "kicad": subprocess.check_output((kicad, "version"), text=True).strip(),
        "outline_mm": [35, 26, 1.6],
        "copper_layers": 4,
        "erc_findings": 0,
        "drc_findings": 0,
        "drc_opens": 0,
        "schematic_parity_findings": 0,
        "audited_electrical_terminals": pins,
        "populated_references": len(components),
        "j2_to_j94": {"1": "GND", "2": "D-", "3": "D+", "4": "5 V"},
        "source_sha256": {str(path.relative_to(HERE)): digest(path) for path in sources},
        "quote_sha256": {path.name: digest(path) for path in (gerbers, bom, cpl)},
    }
    (destination / "review.json").write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    parser.add_argument("--output", type=Path, default=HERE / "quote")
    args = parser.parse_args()
    export(args.kicad_cli, args.output.resolve())
