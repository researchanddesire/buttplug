"""Pack the checked product enclosure STEP files for a supplier quote."""

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ASSEMBLY = ROOT / "hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd"
PACKET = HERE / "Compass-EVT1-Dock-Enclosure-Quote.zip"


def digest(data):
    return sha256(data).hexdigest()


def validate_native(report):
    with ZipFile(ASSEMBLY) as archive:
        tree = ET.fromstring(archive.read("Document.xml"))
        objects = {node.attrib["name"]: node for node in tree.findall("./ObjectData/Object")}

        def check(row):
            node = objects[row["native_object"]]
            stream = node.find("./Properties/Property[@name='Shape']/Part").attrib["file"]
            if digest(archive.read(stream)) != row["native_brep_sha256"]:
                raise ValueError(f"Re-export changed native body {row['native_object']}")

        for row in report["parts"].values():
            check(row)
            if "installed_counterpart" in row:
                check(row["installed_counterpart"])


def packet(entries):
    report = json.loads(entries["geometry-check.json"])
    validate_native(report)
    parts = io.StringIO()
    writer = csv.writer(parts, lineterminator="\n")
    writer.writerow(("STEP file", "Quantity", "Quote finish"))
    for name, row in report["parts"].items():
        if digest(entries[f"parts/{name}"]) != row["step_sha256"]:
            raise ValueError(f"STEP hash mismatch for {name}")
        writer.writerow((name, row["quantity"], row["quote_finish"]))
    entries.update({"README.md": (HERE / "README.md").read_bytes(),
                    "parts.csv": parts.getvalue().encode(),
                    "dock-reference.png": (ROOT / "developer-docs/docs/assets/native-dock-open.png").read_bytes()})
    manifest = {"source_assembly": str(ASSEMBLY.relative_to(ROOT)),
                "exported_assembly_sha256": report["source_assembly_sha256"],
                "checked_current_assembly_sha256": digest(ASSEMBLY.read_bytes()),
                "files_sha256": {k: digest(v) for k, v in sorted(entries.items())}}
    entries["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--exports", type=Path)
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.exports:
        report = (args.exports / "geometry-check.json").read_bytes()
        entries = {"geometry-check.json": report}
        for name in json.loads(report)["parts"]:
            entries[f"parts/{name}"] = (args.exports / name).read_bytes()
        entries = packet(entries)
        with ZipFile(PACKET, "w") as archive:
            for name, data in sorted(entries.items()):
                archive.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)

    with ZipFile(PACKET) as archive:
        if archive.testzip() is not None:
            raise ValueError("Invalid supplier ZIP")
        actual = {name: archive.read(name) for name in archive.namelist()}
        entries = {name: data for name, data in actual.items()
                   if name == "geometry-check.json" or name.startswith("parts/")}
        expected = packet(entries)
        # A placement-only assembly revision can still use the same verified bodies.
        if json.loads(actual["manifest.json"])["files_sha256"] != json.loads(expected["manifest.json"])["files_sha256"]:
            raise ValueError("Supplier packet files changed or need regeneration")
        if set(actual) != set(expected) or any(actual[name] != expected[name] for name in actual if name != "manifest.json"):
            raise ValueError("Supplier ZIP contents differ from the checked package")
    print(f"Verified {len(json.loads(actual['geometry-check.json'])['parts'])} product enclosure STEP files")


if __name__ == "__main__":
    main()
