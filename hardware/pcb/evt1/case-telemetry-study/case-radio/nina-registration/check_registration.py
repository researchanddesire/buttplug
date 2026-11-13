"""Cold-read the OEM STEP, then verify its registration through KiCad 10."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

import OCC
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.GProp import GProp_GProps
from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer


HERE = Path(__file__).resolve().parent
CASE_RADIO = HERE.parent
OEM_DIR = CASE_RADIO.parent / "vendor/nina"
STEP = OEM_DIR / "NINA-B112-OEM.stp"
FOOTPRINT = CASE_RADIO / "Radio.pretty/NINA-B112_OEM.kicad_mod"
SEATING_TOLERANCE_MM = 1e-6


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subshapes(shape, kind):
    explorer = TopExp_Explorer(shape, kind)
    while explorer.More():
        yield explorer.Current()
        explorer.Next()


def bounds(shape):
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape, box, False, False)
    return tuple(round(value, 8) for value in box.Get())


def is_near(a, b):
    return abs(a - b) <= SEATING_TOLERANCE_MM


def read_step(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone or not reader.TransferRoots():
        raise ValueError(f"Could not cold-read {path}")
    shape = reader.OneShape()
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError(f"Invalid imported BRep in {path}")
    return shape


def match_pads(expected, shapes):
    remaining = list(shapes)
    matches = {}
    for number, xy in expected.items():
        distances = [math.dist(xy, ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2)) for b, _ in remaining]
        index = min(range(len(distances)), key=distances.__getitem__)
        assert distances[index] <= SEATING_TOLERANCE_MM, (number, distances[index])
        matches[number] = (*remaining.pop(index), distances[index])
    assert not remaining
    return matches


def face_at(shape, z):
    faces = []
    for face in subshapes(shape, TopAbs_FACE):
        bound = bounds(face)
        if is_near(bound[2], z) and is_near(bound[5], z):
            faces.append(face)
    assert len(faces) == 1
    return faces[0]


def area(shape):
    gprops = GProp_GProps()
    brepgprop.SurfaceProperties(shape, gprops)
    return gprops.Mass()


def ordered_footprint():
    source = FOOTPRINT.read_text()
    rows = re.findall(r'\(pad "(\d+)" smd \w+ \(at ([-.\d]+) ([-.\d]+)(?: ([-.\d]+))?\) \(size ([-.\d]+) ([-.\d]+)\)', source)
    pads = {}
    for number, x, y, angle, _, _ in rows:
        # KiCad top view uses +Y down. STEP and FreeCAD have +Y up.
        pads[int(number)] = (float(x), -float(y))
        assert float(angle or 0) in {0, 90}, (number, angle)
    assert len(rows) == len(pads) == 42 and set(pads) == set(range(1, 43))
    assert pads[1] == (-6.2, -4.125) and pads[15] == (2.725, 2.0) and pads[16] == (2.8, 4.125)
    return source, pads


def kicad_board(directory, source, cli, offset):
    at = source.rfind(")")
    assert at > 0 and "(model " not in source
    step_path = STEP.as_posix()
    if '"' in step_path:
        raise ValueError("KiCad fixture paths must not contain quotation marks")
    footprint = source[:at] + f"""
 (at 100 100)
 (model "{step_path}"
  (offset (xyz {offset[0]} {offset[1]} {offset[2]}))
  (scale (xyz 1 1 1))
  (rotate (xyz 0 0 90)))
 )
"""
    board = directory / "registration-fixture.kicad_pcb"
    board.write_text('''(kicad_pcb (version 20240108) (generator pcbnew)
 (general (thickness 1))
 (paper "A4")
 (layers (0 "F.Cu" signal)(31 "B.Cu" signal)(44 "Edge.Cuts" user))
 (gr_rect (start 90 92) (end 110 108) (stroke(width .05)(type default))(fill none)(layer "Edge.Cuts"))
''' + footprint + ")\n")
    output = directory / "registration-fixture.step"
    subprocess.run([cli, "pcb", "export", "step", "--user-origin", "100x100mm",
                    "--include-pads", "--output", str(output), str(board)], check=True, capture_output=True)
    return read_step(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    cli = str(Path(options.kicad_cli).resolve())
    version = subprocess.check_output([cli, "--version"], text=True).strip()
    assert version == "10.0.8", version
    provenance = json.loads((OEM_DIR / "extraction.json").read_text())
    assert sha256(STEP) == provenance["STEP_sha256"]
    assert sha256(FOOTPRINT) == provenance["native_footprint_sha256"]
    assert "|ROTZ=270.000|" in provenance["model_record"]

    native = read_step(STEP)
    native_bounds = bounds(native)
    native_solids = [(bounds(s), s) for s in subshapes(native, TopAbs_SOLID)]
    assert len(native_solids) == 101
    xmin, ymin, native_seat, xmax, ymax, native_top = native_bounds
    assert is_near(xmax - xmin, 10.0) and is_near(ymax - ymin, 14.0)
    assert is_near(native_top - native_seat, 3.779)
    # Manufacturer orientation is 270° about +Z. KiCad's model tuple uses the
    # opposite Euler sign, verified below through a real native STEP export.
    translation = (round(-(ymin + ymax) / 2, 8), round((xmin + xmax) / 2, 8), -native_seat)
    tx = gp_Trsf()
    tx.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(0, 0, 1)), -math.pi / 2)
    tx.SetTranslationPart(gp_Vec(*translation))
    local = BRepBuilderAPI_Transform(native, tx, True).Shape()
    local_solids = [(bounds(s), s) for s in subshapes(local, TopAbs_SOLID)]
    assert bounds(local) == (-7, -5, 0, 7, 5, 3.779)
    antenna, = [b for b, _ in local_solids if is_near(b[5], 3.779)]
    assert antenna == (3.1, -5, .779, 7, 5, 3.779)
    substrate, = [b for b, _ in local_solids if b[:2] == (-7, -5) and b[3:5] == (7, 5)]
    shield, = [b for b, _ in local_solids if b[0] < -6.8 and 2 < b[5] < 2.5]
    assert substrate == (-7, -5, .02, 7, 5, .78)
    source, pads = ordered_footprint()
    local_pads = match_pads(pads, [(b, s) for b, s in local_solids if is_near(b[2], 0)])

    # The 1.00 mm temporary fixture has a 0.93 mm core and 0.04 mm top copper
    # export. KiCad places models at 1.015 mm before offset. Applying -0.045
    # to the local seat therefore puts the lowest terminal at top copper.
    # This tool-specific offset belongs only to the checked fixture stack.
    fixture_offset = (*translation[:2], round(translation[2] - .045, 8))
    with tempfile.TemporaryDirectory(prefix="nina-registration-") as directory:
        exported = kicad_board(Path(directory), source, cli, fixture_offset)
    exported_solids = [(bounds(s), s) for s in subshapes(exported, TopAbs_SOLID)]
    assert len(exported_solids) == 144
    seating_z = .97
    host_pads = match_pads(pads, [(b, s) for b, s in exported_solids
                                 if is_near(b[2], .93) and is_near(b[5], seating_z)])
    exported_pads = match_pads(pads, [(b, s) for b, s in exported_solids
                                     if is_near(b[2], seating_z) and is_near(b[5], .99)])
    rows = []
    for number, xy in pads.items():
        module = face_at(exported_pads[number][1], seating_z)
        host = face_at(host_pads[number][1], seating_z)
        common = area(BRepAlgoAPI_Common(module, host).Shape())
        assert common > 0 and abs(common / area(host) - 1) <= 1e-6, (number, common)
        rows.append({
            "pad": number,
            "center_XY_mm": xy,
            "module_local_bounds_mm": local_pads[number][0],
            "position_error_mm": round(max(x[number][2] for x in (local_pads, exported_pads, host_pads)), 8),
            "module_contact_area_mm2": round(area(module), 8),
            "host_contact_area_mm2": round(area(host), 8),
            "common_area_mm2": round(common, 8),
        })

    report = {
        "pass": True,
        "scope": "OEM package and native land registration with a temporary one-footprint PCB",
        "model": "NINA-B112 OEM library solid, checked against NINA-B112-05B-00 family drawing",
        "tools": {"KiCad": version, "PythonOCC": OCC.VERSION},
        "source_sha256": {str(p.relative_to(CASE_RADIO.parent)): sha256(p)
                          for p in (STEP, FOOTPRINT, OEM_DIR / "extraction.json", Path(__file__))},
        "OEM_bounds_mm": native_bounds,
        "OEM_solid_count": len(native_solids),
        "local_registration": {
            "frame": "center of the module outline; +X to antenna, +Y up in top view; Z0 at contact bottoms",
            "right_handed_formula": "(x,y,z)=(y_oem+tx,-x_oem+ty,z_oem+tz)",
            "translation_after_minus_90_degree_z_rotation_mm": translation,
            "module_bounds_mm": bounds(local),
            "antenna_bounds_mm": antenna,
            "substrate_bounds_mm": substrate,
            "shield_bounds_mm": shield,
        },
        "verified_fixture_only_KiCad_model_fields": {
            "offset_mm": fixture_offset, "scale": [1, 1, 1], "rotate_degrees": [0, 0, 90],
            "board_copper_top_Z_mm": seating_z,
            "board_outline_XY_mm": [-10, -8, 10, 8],
            "board_thickness_setting_mm": 1.0,
            "exported_solids": len(exported_solids),
        },
        "pads": rows,
        "dock_pose_selected": False,
        "physical_validation": False,
    }
    options.output.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: valid OEM BRep, 42 local and 42 exported pad registrations, seating and face overlap")


if __name__ == "__main__":
    main()
