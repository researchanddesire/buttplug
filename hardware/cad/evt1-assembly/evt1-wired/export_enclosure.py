"""Export individual product enclosure solids from the saved FreeCAD dock."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import FreeCAD as App
import Part


PARTS = (
    ("LowerShell", "lower-shell", 1, "dark shell"),
    ("UpperShell", "upper-shell", 1, "orange shell"),
    ("LowerChamber", "lower-liner", 1, "cream chamber"),
    ("UpperChamber", "upper-liner", 1, "cream chamber"),
    ("ScallopedBezel", "display-bezel", 1, "cream bezel"),
    ("DockButtonLeftCap", "left-button-cap", 1, "blue"),
    ("DockButtonCenterCap", "center-button-cap", 1, "blue"),
    ("DockButtonRightCap", "right-button-cap", 1, "blue"),
    ("ContactCarrier", "contact-carrier", 1, "dark interior"),
    ("ContactRetainer", "contact-retainer", 1, "dark interior"),
    ("LCDRetentionLeftCarrier", "lcd-retainer-left", 1, "internal"),
    ("LCDRetentionRightCarrier", "lcd-retainer-right", 1, "internal"),
    ("FrontClosureLowerPlug", "lower-latch-baffle", 1, "opaque"),
    ("FrontClosureUpperPlug", "upper-latch-baffle", 1, "opaque"),
    ("DockBaseUVDryNTCClip", "base-ntc-clip", 1, "internal"),
    ("DockLidUVDryNTCClip", "lid-ntc-clip", 1, "internal"),
    ("DockBaseUVTerminalGuard", "base-uv-terminal-guard", 1, "internal"),
    ("DockLidUVTerminalGuard", "lid-uv-terminal-guard", 1, "internal"),
    ("LeftBracket", "hall-left-support", 1, "internal nonmagnetic polymer"),
    ("RightBracket", "hall-right-support", 1, "internal nonmagnetic polymer"),
    ("LeftCloseCarrier", "hall-left-magnet-carrier", 1, "machined nonmagnetic polymer"),
    ("RightCloseCarrier", "hall-right-magnet-carrier", 1, "machined nonmagnetic polymer"),
    ("LeftSpacer", "hall-left-magnet-backer", 1, "machined PEEK"),
    ("RightSpacer", "hall-right-magnet-backer", 1, "machined PEEK"),
    ("LeftHallBracketScrewSpacer1", "hall-bracket-screw-spacer", 4, "machined PEEK"),
    ("CustomHingePin", "hinge-pin", 1, "machined stainless"),
    ("DockBaseUVSpreader6061", "uv-spreader-6061", 2, "machined 6061-T6"),
    ("DockBaseUVThermostatPressureBar6061", "uv-thermostat-pressure-bar-6061", 2, "machined 6061-T6"),
)

LID_COPIES = {
    "DockBaseUVSpreader6061": "DockLidUVSpreader6061",
    "DockBaseUVThermostatPressureBar6061": "DockLidUVThermostatPressureBar6061",
}


def bounds(shape):
    box = shape.optimalBoundingBox(False, False)
    return [getattr(box, name) for name in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")]


def require_equivalent(original, imported, name):
    if imported.isNull() or not imported.isValid() or len(imported.Solids) != 1:
        raise ValueError(f"{name}: STEP does not contain one valid solid")
    bound_error = max(abs(x - y) for x, y in zip(bounds(original), bounds(imported)))
    shared = original.common(imported, 1e-6).Volume
    volume_error = abs(original.Volume - shared) + abs(imported.Volume - shared)
    volume_tolerance = max(.05, original.Volume * 1e-5)
    if bound_error > .001 or volume_error > volume_tolerance:
        raise ValueError(f"{name}: STEP differs by {bound_error:.6f} mm, {volume_error:.6f} mm³")
    return {"bound_error_mm": bound_error, "symmetric_volume_difference_mm3": volume_error}


def export(assembly, output):
    source_hash = sha256(assembly.read_bytes()).hexdigest()
    report = {"source_assembly_sha256": source_hash, "freecad": App.Version()[:3], "parts": {}}
    with ZipFile(assembly) as archive, tempfile.TemporaryDirectory() as directory:
        tree = ET.fromstring(archive.read("Document.xml"))
        objects = {node.attrib["name"]: node for node in tree.findall("./ObjectData/Object")}
        extracted = Path(directory, "part.brep")

        def body(name):
            stream = objects[name].find("./Properties/Property[@name='Shape']/Part").attrib["file"]
            data = archive.read(stream)
            extracted.write_bytes(data)
            shape = Part.read(str(extracted))
            if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
                raise ValueError(f"{name}: source does not contain one valid solid")
            return shape, sha256(data).hexdigest()

        for name, slug, quantity, finish in PARTS:
            original, brep_hash = body(name)
            target = output / (slug + ".step")
            original.exportStep(str(target))
            row = require_equivalent(original, Part.read(str(target)), name)
            report["parts"][target.name] = {
                "native_object": name, "native_brep_sha256": brep_hash,
                "quantity": quantity, "quote_finish": finish,
                "step_sha256": sha256(target.read_bytes()).hexdigest(),
                "bounds_mm": bounds(original), "volume_mm3": original.Volume, **row,
            }
            if name in LID_COPIES:
                lid_name = LID_COPIES[name]
                lid, lid_hash = body(lid_name)
                installed = original.copy()
                installed.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 180)
                installed.translate(App.Vector(0, 0, 68.5))
                report["parts"][target.name]["installed_counterpart"] = {
                    "native_object": lid_name, "native_brep_sha256": lid_hash,
                    **require_equivalent(lid, installed, lid_name),
                }
            print(f"Verified {target.name}", flush=True)

    if sha256(assembly.read_bytes()).hexdigest() != source_hash:
        raise ValueError("Dock assembly changed during export")
    (output / "geometry-check.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assembly", type=Path)
    parser.add_argument("output", type=Path, help="Existing empty output directory")
    args = parser.parse_args()
    if not args.output.is_dir() or any(args.output.iterdir()):
        parser.error("Choose an empty output directory")
    export(args.assembly, args.output)
