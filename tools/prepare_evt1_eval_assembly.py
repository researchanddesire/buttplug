"""Bind JLC upload BOM and CPL to the checked Compact or Master Bench CAM export."""

import argparse
import csv
from hashlib import sha256
import json
from math import cos, radians, sin
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "hardware/design/evt1-bench-ordering/master-bench-eval"
NATIVE = ROOT / "hardware/pcb/evt1"
BOM_FIELDS = ("Comment", "Designator", "Footprint", "Manufacturer Part Number", "LCSC Part #")
CPL_FIELDS = ("Designator", "Mid X", "Mid Y", "Layer", "Rotation")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def save(path, fields, records):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def indexed(records, field):
    result = {record[field]: record for record in records}
    assert len(result) == len(records), f"Duplicate {field}"
    return result


def prepare(cam):
    manifest = json.loads((cam / "cam-manifest.json").read_text())
    kind = manifest["board"]
    assert kind in {"product", "dev"}
    for key, expected in manifest["source_sha256"].items():
        assert digest(ROOT / key) == expected, f"Stale CAM source: {key}"
    for key, expected in manifest["assembly_review_sha256"].items():
        assert digest(cam / key) == expected, f"Modified CAM file: {key}"
    native = indexed(rows(cam / "native-all-positions.csv"), "Ref")
    smt = indexed(rows(cam / "assembly-parts-for-review.csv"), "Designator")
    lcsc = indexed(rows(EVAL / "jlc-catalog.csv"), "Manufacturer Part Number")
    bench_tht = indexed(rows(EVAL / "bench-through-hole.csv"), "Designator") if kind == "dev" else {}
    assert not smt.keys() & bench_tht.keys()
    quote = smt | bench_tht
    assert quote.keys() <= native.keys()
    assert not quote.keys() & set(manifest["manual_and_unloaded_positions"])
    excluded = set(native) - set(quote)
    # All purchased through-hole bench connectors should reach the file; fixture
    # and copper-only items stay a separately priced operation or have no part.
    assert all(re.fullmatch(r"(?:TP\d+|MH\d+|CT[1-4]|J2|JP1|C12|C22)", r) for r in excluded), excluded
    assert ({"CT1", "CT2", "CT3", "CT4"} <= excluded) == (kind == "product")

    bom, cpl = [], []
    for ref in sorted(quote):
        record, position = quote[ref], native[ref]
        mpn = record["Manufacturer Part Number"]
        code = lcsc[mpn]["LCSC Part #"]
        assert re.fullmatch(r"C\d+", code), (ref, mpn, code)
        assert record.get("Footprint", position["Package"]) == position["Package"], ref
        bom.append({"Comment": record["Comment"], "Designator": ref,
                    "Footprint": position["Package"], "Manufacturer Part Number": mpn, "LCSC Part #": code})
        x, y, rotation = position["PosX"], position["PosY"], position["Rot"]
        if ref in bench_tht:
            # Native through-hole position rows start at pin 1. Use the F.Fab
            # body center for the vendor's placement preview, in millimetres.
            # Native POS y is up; the footprint's unrotated local y is down.
            assert position["Side"] == "top", ref
            dx, dy = (float(record[key]) for key in ("Fab center DX", "Fab center DY"))
            a = radians(float(rotation))
            x = f"{float(x) + dx * cos(a) + dy * sin(a):.6f}"
            y = f"{float(y) + dx * sin(a) - dy * cos(a):.6f}"
            # Five symmetric pin headers use a different zero in JLC's model.
            rotation = f"{(float(rotation) + float(record['JLC rotation delta'])) % 360:.6f}"
        cpl.append({"Designator": ref, "Mid X": x, "Mid Y": y,
                    "Layer": position["Side"], "Rotation": rotation})

    bom_name, cpl_name = "jlc-bom.csv", "jlc-cpl.csv"
    save(cam / bom_name, BOM_FIELDS, bom)
    save(cam / cpl_name, CPL_FIELDS, cpl)
    assert set(indexed(rows(cam / bom_name), "Designator")) == set(indexed(rows(cam / cpl_name), "Designator"))
    (cam / "assembly-upload-manifest.json").write_text(json.dumps({
        "scope": "Upload for quote; vendor confirms stock, parts, rotations and requested secondary operations.",
        "cam_manifest_sha256": digest(cam / "cam-manifest.json"),
        "source_bom_sha256": digest(EVAL / "jlc-catalog.csv"),
        "through_hole_source_sha256": digest(EVAL / "bench-through-hole.csv") if bench_tht else None,
        "surface_and_mixed_mount_positions": len(smt),
        "standard_through_hole_positions": len(bench_tht),
        "excluded_native_positions": sorted(excluded),
        "outputs_sha256": {name: digest(cam / name) for name in (bom_name, cpl_name)},
    }, indent=2) + "\n")
    print(f"{kind}: {len(smt)} surface/mixed-mount + {len(bench_tht)} through-hole placements; BOM/CPL agree.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cam_directory", type=Path)
    prepare(parser.parse_args().cam_directory)
