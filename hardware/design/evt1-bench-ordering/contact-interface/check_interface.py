"""Export the saved contact carrier and check the two actual PCB contact rows."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import kicad_sexp as kicad

DOCK = ROOT / "hardware/cad/evt1-assembly"
CARRIER = DOCK / "recentered-carrier-trial"
PRODUCT = DOCK / "evt1-wired"
TARGET_PRODUCT = ROOT / ("hardware/cad/manufacturing-layout/evt1-integration/"
                         "contact-module-trial/single-board")
BUTTONS = ROOT / ("hardware/cad/manufacturing-layout/evt1-integration/"
                  "contact-module-trial/single-board/exterior/ButtonPressKeepouts.FCStd")
PCB = ROOT / "hardware/pcb/evt1"
ROWS = (
    ("P91", "CT1", "GND", "GND", "Contact_GND"),
    ("P92", "CT2", "DOCK_DM", "USB_DM_CONTACT", "Contact_USB_DM"),
    ("P93", "CT3", "DOCK_DP", "USB_DP_CONTACT", "Contact_USB_DP"),
    ("P94", "CT4", "DOCK_5V", "DOCK_5V", "Contact_DOCK_5V"),
)


def digest(data):
    return sha256(data).hexdigest()


def bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax


def read_native(archive, label, scratch):
    path = scratch / "part.brep"
    path.write_bytes(archive.read(label + ".Shape.brp"))
    shape = Part.read(str(path))
    assert not shape.isNull() and shape.isValid(), label
    return shape


def compare(saved, exchange):
    assert all(shape.isValid() and len(shape.Solids) == 1
               for shape in (saved, exchange))
    delta = max(abs(a - b) for a, b in zip(bounds(saved), bounds(exchange)))
    shared = saved.common(exchange, 1e-6).Volume
    volume_error = abs(saved.Volume - shared) + abs(exchange.Volume - shared)
    assert delta <= .001 and volume_error <= .05, (delta, volume_error)
    return {"volume_mm3": saved.Volume, "bounds_mm": bounds(saved),
            "max_bound_error_mm": delta, "volume_difference_mm3": volume_error}


def link_data(objects, name):
    props = objects[name].find("Properties")
    link = props.find("Property[@name='LinkedObject']")[0]
    pose = props.find("Property[@name='LinkPlacement']/PropertyPlacement")
    origin = App.Vector(*(float(pose.get(f"P{axis}")) for axis in ("x", "y", "z")))
    rotation = App.Rotation(*(float(pose.get(f"Q{axis}")) for axis in range(4)))
    return link.get("name"), link.get("file"), App.Placement(origin, rotation)


def check_close(value, expected):
    assert math.isclose(value, expected, abs_tol=1e-6), (value, expected)


def ref(footprint):
    return kicad.prop(footprint, "Reference") or next(
        item[2].value for item in kicad.children(footprint, "fp_text") if item[1].value == "reference"
    )


def pads(board, references):
    selected = {}
    for footprint in kicad.children(kicad.parse(board.decode()), "footprint"):
        name = ref(footprint)
        if name not in references:
            continue
        pad, = kicad.children(footprint, "pad")
        assert pad[1].value == "1" and pad[2].value == "thru_hole"
        net = kicad.child(pad, "net")[2].value
        x, y = [float(value.value) for value in kicad.child(footprint, "at")[1:3]]
        selected[name] = (net, x, y, float(kicad.value(pad, "drill")))
    assert set(selected) == set(references)
    return selected


def quote_board(path, board_member, expected_hash):
    with ZipFile(path) as assembly:
        assert assembly.testzip() is None
        fabrication_member, = [name for name in assembly.namelist() if name.endswith("fabrication-quote.zip")]
        with ZipFile(BytesIO(assembly.read(fabrication_member))) as fab:
            assert fab.testzip() is None
            pth, = [name for name in fab.namelist() if name.endswith("-PTH.drl")]
            drill_data = fab.read(pth).decode()
        assert digest(assembly.read(board_member)) == expected_hash
    tools, holes, active = {}, [], None
    for line in drill_data.splitlines():
        if match := re.fullmatch(r"(T\d+)C([\d.]+)", line):
            tools[match[1]] = float(match[2])
        elif re.fullmatch(r"T\d+", line):
            active = tools[line]
        elif match := re.fullmatch(r"X(-?[\d.]+)Y(-?[\d.]+)", line):
            holes.append((float(match[1]), -float(match[2]), active))
    return holes


def button_access(dock, scratch, prior):
    assert digest(BUTTONS.read_bytes()) == prior["device_mating"]["pressed_keepout_SHA256"]
    dx, dy, dz = prior["device_mating"]["device_translation_mm"]
    names = ("LowerShell", "LowerChamber", "ContactCarrier", "ContactRetainer")
    obstacles = {name: read_native(dock, name, scratch) for name in names}
    start = -12.0
    rows = []
    with ZipFile(BUTTONS) as crowns:
        for index in range(2):
            x0, y0, z0, x1, _, z1 = bounds(read_native(crowns, f"IntegralSiliconeBoss{index}", scratch))
            x, y, z = (x0 + x1) / 2 + dx, y0 + dy, (z0 + z1) / 2 + dz
            probe = Part.makeCylinder(1.5, y - start, App.Vector(x, start, z), App.Vector(0, 1, 0))
            intersections = {}
            for name, shape in obstacles.items():
                intersection = shape.common(probe).Volume
                assert intersection > 1, (index, name, intersection)
                intersections[name] = round(intersection, 6)
            rows.append({"crown_xyz_mm": [round(v, 6) for v in (x, y, z)],
                         "intersections_mm3": intersections})
    return {"straight_axial_tool_diameter_mm": 3.0, "start_y_mm": start, "rows": rows,
            "scope": "One straight rear approach per button. No geometry change or search of other access paths."}


def check(output):
    prior = json.loads((CARRIER / "native-checks.json").read_text())
    pin_board = (PCB / "pins/pins-evt1.kicad_pcb").read_bytes()
    target_board = (PCB / "single-flange-routing/single-flange.kicad_pcb").read_bytes()
    pin_quote = PCB / "pins/assembly-quote/pins-evt1-assembly-quote.zip"
    target_quote = PCB / "single-flange-routing/assembly-quote/single-flange-evt1-assembly-quote.zip"
    pin_drill = quote_board(pin_quote, "pins-evt1.kicad_pcb", digest(pin_board))
    target_drill = quote_board(target_quote, "single-flange.kicad_pcb", digest(target_board))
    pin_pads = pads(pin_board, [row[0] for row in ROWS])
    target_pads = pads(target_board, [row[1] for row in ROWS])

    files, pairs = {}, []
    dock_bytes = (PRODUCT / "DockAssembly.FCStd").read_bytes()
    exterior_bytes = (PRODUCT / "sources/SingleFlangeExterior.FCStd").read_bytes()
    assert exterior_bytes == (TARGET_PRODUCT / "exterior/SingleFlangeExterior.FCStd").read_bytes()
    assert digest(exterior_bytes) == prior["device_mating"]["source_SHA256"]
    carrier_path = CARRIER / "RecenteredCarrierTrial.FCStd"
    assert digest(carrier_path.read_bytes()) == prior["native_SHA256"]
    with (ZipFile(BytesIO(dock_bytes)) as dock, ZipFile(BytesIO(exterior_bytes)) as exterior,
          ZipFile(carrier_path) as carrier, TemporaryDirectory() as temporary):
        scratch = Path(temporary)
        tree = ET.fromstring(dock.read("Document.xml"))
        objects = {node.get("name"): node for node in tree.findall("./ObjectData/Object")}
        for name in ("ContactCarrier", "ContactRetainer"):
            saved = read_native(dock, name, scratch)
            trial_name = name.replace("Contact", "Recentered")
            trial = read_native(carrier, trial_name, scratch)
            assert next(item for item in prior["body_checks"] if item["name"] == trial_name)["BOP_pass"]
            name_step = name + ".step"
            exchange = HERE / name_step
            files[name_step] = {"sha256": digest(exchange.read_bytes()),
                                "solids": {name: compare(saved, Part.read(str(exchange)))}}
            files[name_step]["trial_equivalence"] = compare(saved, trial)

        dock_carrier = read_native(dock, "ContactCarrier", scratch)
        skin_name, _, skin_pose = link_data(objects, "DeviceContinuousSkin")
        skin = read_native(exterior, skin_name, scratch)
        skin.Placement = skin_pose * skin.Placement
        plunger = read_native(dock, "ContactPogoSourceVisiblePlunger", scratch)
        stop_y = bounds(dock_carrier)[4]
        skin_clearance = dock_carrier.distToShape(skin)[0]
        for index, (p, ct, pin_net, target_net, native) in enumerate(ROWS):
            pn, px, py, ph = pin_pads[p]
            tn, tx, ty, th = target_pads[ct]
            target_name, external, target_pose = link_data(objects, f"Device{native}")
            assert target_name == native and external == "sources/SingleFlangeExterior.FCStd"
            target_shape = read_native(exterior, target_name, scratch)
            target_shape.Placement = target_pose * target_shape.Placement
            target = bounds(target_shape)
            target_x, target_z = (target[0] + target[3]) / 2, (target[2] + target[5]) / 2
            assert (pn, tn) == (pin_net, target_net)
            assert (ph, th) == (.6, 1.02)
            assert (px, py, round(ph, 3)) in pin_drill
            assert (tx, ty, round(th, 3)) in target_drill
            check_close(px - 120, target_x)
            check_close(tx - 100, target_x)
            assert (py, ty) == (106.7, 90.0)
            check_close(target_z, 42)
            check_close(target[1], stop_y)
            _, _, pin_pose = link_data(objects, f"ContactPogo{index}")
            check_close(pin_pose.Base.x, target_x)
            check_close(pin_pose.Base.z, target_z)
            pin_tip = plunger.copy()
            pin_tip.Placement = pin_pose * pin_tip.Placement
            check_close(bounds(pin_tip)[4], stop_y)
            check_close(pin_tip.distToShape(target_shape)[0], 0)
            # Intersect with the coincident contact plane because the solid
            # intersection can discard a face with zero shared volume.
            square = Part.makePolygon([
                App.Vector(target_x + dx, stop_y, target_z + dz)
                for dx, dz in ((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5),
                               (-1.5, 1.5), (-1.5, -1.5))
            ])
            stop_face = dock_carrier.common(Part.Face(square))
            contact_area = stop_face.common(target_shape).Area
            check_close(contact_area, math.pi * (1.2**2 - .9**2))
            pairs.append({"pin": p, "target": ct, "pin_net": pn, "target_net": tn,
                          "pin_nominal_plated_drill_mm": ph, "target_nominal_plated_drill_mm": th,
                          "dock_axis_XZ_mm": [round(target_x, 6), 42],
                          "seating_plane_y_mm": pin_pose.Base.y,
                          "stop_and_target_face_y_mm": round(stop_y, 6),
                          "stop_face_contact_area_mm2": round(contact_area, 6)})
        access = button_access(dock, scratch, prior)

    pogo = json.loads((DOCK / "vendor/pogo/source.json").read_text())
    dims = pogo["nominal_dimensions_mm"]
    tolerance = pogo["general_drawing_tolerance_in"]
    target_dims = json.loads((TARGET_PRODUCT / "selected-parts.json").read_text())["selected_targets"]
    target_height_tolerance = target_dims["published_generic_length_tolerance_mm"]
    position_difference = 2 * target_height_tolerance
    pin_height_tolerance = tolerance["length"] * 25.4
    compression = pairs[0]["seating_plane_y_mm"] + dims["free_height_from_PCB_seating_face"] - stop_y
    check_close(compression, .6)
    check_close(skin_clearance, .3)
    return {
        "scope": "Product dock contact STEP parity, seated geometry and component-only dimensional screen",
        "dock_native_sha256": digest(dock_bytes),
        "editable_carrier_trial_sha256": prior["native_SHA256"],
        "device_exterior_sha256": digest(exterior_bytes),
        "pin_quote_sha256": digest(pin_quote.read_bytes()),
        "target_quote_sha256": digest(target_quote.read_bytes()),
        "pin_board_sha256": digest(pin_board), "target_board_sha256": digest(target_board),
        "geometry": files, "rows": pairs,
        "seated_button_access": access,
        "pogo_compression_mm": round(compression, 4),
        "pogo_compression_with_free_height_tolerance_only_mm": [
            round(compression + sign * pin_height_tolerance, 4) for sign in (-1, 1)
        ],
        "geometry_screen": {
            "nominal_carrier_to_skin_gap_mm": round(skin_clearance, 4),
            "component_only_target_face_height_difference_max_mm": round(position_difference, 4),
            "pogo_compression_with_pin_height_and_planar_target_height_variation_mm": [
                round(compression - pin_height_tolerance - position_difference, 4),
                round(compression + pin_height_tolerance, 4),
            ],
            "max_round_stop_to_round_target_center_offset_before_losing_full_overlap_mm": round(
                (target_dims["diameters_mm"]["face"]
                 - target_dims["published_generic_diameter_tolerance_mm"]) / 2 - 1.2, 4
            ),
            "spring_maker_nominal_mid_stroke_mm": dims["nominal_mid_stroke"],
            "vendor_nominal_full_stroke_mm": dims["nominal_max_stroke"],
            "assumed_min_full_stroke_for_dimensional_screen_mm": round(dims["nominal_max_stroke"] - .005 * 25.4, 4),
        },
        "pogo_finished_hole_min_based_on_max_tail_mm": round(
            dims["tail_diameter"] + tolerance["diameter"] * 25.4 + .004 * 25.4, 4
        ),
        "physical_validation": False,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = check(args.output)
    (args.output / "exchange-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified two STEP solids, four mating stations, and both PCB quote archives")
