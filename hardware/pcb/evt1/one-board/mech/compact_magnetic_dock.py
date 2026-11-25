"""Build the compact magnetic dock fit candidate with the saved EVT1 plug exterior.

Set COMPASS_MAG_DOCK_MECH to this directory. First run with freecadcmd and
COMPASS_MAG_DOCK_PREPARE=1 to read the linked device model. Then run the same
script with the FreeCAD GUI offscreen and COMPASS_MAG_DOCK_PREPARE unset.
The native file opens with the lid raised.
The supplier head, UI, interlock and UV rail electronics use fit envelopes.
"""

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import traceback

import FreeCAD as App
import Part

MECH = Path(os.environ["COMPASS_MAG_DOCK_MECH"])
sys.path.insert(0, str(MECH))
from compass_datums import CONTACTS, CONTACT_SQ, COVER_OUT_Y, SKIN_T_FACE, box_xyz, cyl_y
from compact_magnetic_dock_uv import add_uv_mounts, uv_hardware

SOURCE = MECH / "compass-device.FCStd"
BUILD = MECH.parent / "build" / "mech"
EXCHANGE = BUILD / "compact-magnetic-dock-exterior"
NAME = "CompactMagneticDock"
V = App.Vector
OVERLAP_LIMIT = 1e-4

# Millimetres, hinge at +Y, user and contact wall at -Y.
OUTSIDE_WIDTH = 84.0
FRONT_Y, REAR_Y = -30.0, 133.0
RIM_Z, LID_Z = 34.0, 58.0
LID_FRONT_Y = -7.0
FLOOR_Z = 8.5
HINGE_Y, HINGE_Z = 137.5, 34.0
LID_OPEN_DEG = 105
FACE_Y = COVER_OUT_Y - SKIN_T_FACE
PLUG_AXIS_Z = 31.0
LOAD_SLIDE = 5.0
TARGET_R = 1.5875
HEAD_X0, HEAD_X1 = -5.5, 27.5
HEAD_Z0, HEAD_Z1 = 18.5, 30.5
HEAD_REAR_Y = -10.0
HEAD_LAND_GAP = 0.5
PIN_R = 0.55
PIN_TRAVEL = 0.4
KEEPERS = [(-3.0, -7.5), (22.0, -3.0)]

PLUM = (0.42, 0.30, 0.55)
DARK = (0.21, 0.23, 0.27)
ORANGE = (0.94, 0.45, 0.15)
BLUE = (0.19, 0.45, 0.74)
GOLD = (0.85, 0.66, 0.33)
METAL = (0.73, 0.75, 0.79)
CREAM = (0.89, 0.83, 0.67)


def move(shape, offset):
    moved = shape.copy()
    moved.translate(offset)
    return moved


def turn(shape, degrees):
    moved = shape.copy()
    moved.rotate(V(0, HINGE_Y, HINGE_Z), V(1, 0, 0), -degrees)
    return moved


def rounded_box(x0, x1, y0, y1, z0, z1, radius):
    raw = box_xyz(x0, x1, y0, y1, z0, z1)
    ascending_edges = [edge for edge in raw.Edges if edge.BoundBox.ZLength > z1 - z0 - 0.01]
    return raw.makeFillet(radius, ascending_edges)


def source_exterior():
    source = App.openDocument(str(SOURCE))
    labels = ["FlangeSkin", "FlangeTray", "RearCover", "MetalBody", "MotorThermistorCap"]
    exterior = {label: source.getObjectsByLabel(label)[0].Shape.copy() for label in labels}
    row = []
    for obj in source.getObjectsByLabel("PCB")[0].Group:
        if obj.Label.startswith("MillMax194"):
            shape = obj.Shape.copy()
            parent = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
            shape.Placement = parent.multiply(shape.Placement)
            bounds = shape.optimalBoundingBox(False, False)
            row.append(((bounds.XMin + bounds.XMax) / 2,
                        bounds.YMin, (bounds.ZMin + bounds.ZMax) / 2))
    row.sort()
    assert len(row) == len(CONTACTS) == 4
    assert all(abs(x - cx) < 0.001 and abs(z - cz) < 0.001
               for (x, _, z), (cx, cz) in zip(row, CONTACTS))
    App.closeDocument(source.Name)
    return exterior, row


def prepare_exterior():
    """Snapshot the linked source solids for an offscreen GUI export."""
    exterior, row = source_exterior()
    EXCHANGE.mkdir(parents=True, exist_ok=True)
    for name, shape in exterior.items():
        shape.exportBrep(str(EXCHANGE / (name + ".brep")))
    data = {"source_sha256": sha256(SOURCE.read_bytes()).hexdigest(),
            "parts": list(exterior), "target_row": row}
    (EXCHANGE / "source.json").write_text(json.dumps(data, indent=2) + "\n")


def cached_exterior():
    data = json.loads((EXCHANGE / "source.json").read_text())
    assert data["source_sha256"] == sha256(SOURCE.read_bytes()).hexdigest(), "Refresh the linked source solids"
    exterior = {name: Part.read(str(EXCHANGE / (name + ".brep"))) for name in data["parts"]}
    return exterior, data["target_row"]


def flush_interface(skin, row):
    # Restore the flat contact window in the concept skin and mask four round faces.
    half_window = CONTACT_SQ / 2 + 1.5
    x0, x1 = row[0][0] - half_window, row[-1][0] + half_window
    z0, z1 = row[0][2] - half_window, row[0][2] + half_window
    window_fill = box_xyz(x0, x1, FACE_Y, COVER_OUT_Y, z0, z1)
    faces = [cyl_y(TARGET_R, FACE_Y, old_y, x, z) for x, old_y, z in row]
    filled = skin.fuse(window_fill).removeSplitter()
    filled = filled.cut(faces).removeSplitter()
    assert filled.isValid() and len(filled.Solids) == 1
    return filled, faces


def horizontal_enclosure(flange_support_z, body_support_z):
    half_w = OUTSIDE_WIDTH / 2
    base = rounded_box(-half_w, half_w, FRONT_Y, REAR_Y, 2.5, RIM_Z, 12)
    dish = rounded_box(-36, 36, -0.5, 130.0, FLOOR_Z, RIM_Z + 1, 8)
    skirt_relief = rounded_box(-36, 36, -4.1, 130.0, 31.4, RIM_Z + 1, 8)
    base = base.cut([dish, skirt_relief])
    # Front deck opens from below for the display, buttons, controller and head.
    service_bay = rounded_box(-36, 36, -26, -12, 1.5, 31.5, 3)
    service_bay = service_bay.fuse(box_xyz(-28, 30, -15, -4, 1.5, 17))
    display = box_xyz(-15, 15, -26.1, -12, 31.4, RIM_Z + 1)
    buttons = [Part.makeCylinder(3.3, 5, V(x, -19, 31)) for x in (-25, 22, 31)]
    head_slot = box_xyz(HEAD_X0 - 0.2, HEAD_X1 + 0.2, HEAD_REAR_Y - 0.3, 0.1,
                        HEAD_Z0 - 0.2, HEAD_Z1 + 0.2)
    head_wire = box_xyz(4, 17, -12.5, -9.8, 19, 23)
    service_bay = service_bay.fuse(box_xyz(4, 17, -13, -10.5, 16, 23))
    base = base.cut([service_bay, display, *buttons, head_slot, head_wire])

    # Broad, integral supports carry weight and align the flange.
    y0, y1 = 8.0, 14.0
    # The second set contacts the plug near its widest body section.
    supports = [rounded_box(-17, 17, y0, y1, FLOOR_Z - 0.15, flange_support_z, 1.3),
                rounded_box(-12, 12, 71, 82, FLOOR_Z - 0.15, body_support_z, 1.3)]
    guides = [box_xyz(x0, x1, 8, 25, FLOOR_Z - 0.15, 29)
              for x0, x1 in [(-35, -30.3), (30.3, 35)]]
    # Face stops land away from the recessed UI and exposed contacts.
    stops = [box_xyz(-14, -10, -1, 0, 22, 26),
             box_xyz(15, 22, -1, 0, 30.95, 31.35)]
    # A soft tip restraint can occupy the rear clearance after the UV geometry is settled.
    base = base.fuse(supports + guides + stops).removeSplitter()

    # Continuous inside skirt forms a two-turn seam with the base rim. The hinge is external.
    lid_outline = rounded_box(-half_w, half_w, LID_FRONT_Y, REAR_Y, RIM_Z, LID_Z, 11)
    lid_cavity = rounded_box(-37.5, 37.5, -4.7, 130.4, RIM_Z - 1, LID_Z - 3, 9)
    lid = lid_outline.cut(lid_cavity)
    skirt = rounded_box(-35.4, 35.4, -3.7, 128.6, RIM_Z - 2.2, RIM_Z + 0.5, 8.0)
    skirt_inner = rounded_box(-33.4, 33.4, -1.7, 126.6, RIM_Z - 3, RIM_Z + 1, 6.0)
    skirt = skirt.cut(skirt_inner)
    seam_roof = rounded_box(-38, 38, -5.4, 131.3, RIM_Z, RIM_Z + 0.5, 9.8).cut(skirt_inner)
    lid = lid.fuse([skirt, seam_roof])
    base_knuckles = [(-30, -10.5), (10.5, 30)]
    lid_knuckle = (-10.1, 10.1)
    for x0, x1 in base_knuckles:
        ear = Part.makeCylinder(3.8, x1-x0, V(x0, HINGE_Y, HINGE_Z), V(1, 0, 0))
        bridge = box_xyz(x0, x1, 131.5, HINGE_Y, 30.2, 33.6)
        base = base.fuse([ear, bridge])
    x0, x1 = lid_knuckle
    ear = Part.makeCylinder(3.8, x1-x0, V(x0, HINGE_Y, HINGE_Z), V(1, 0, 0))
    bridge = box_xyz(x0, x1, 131.5, HINGE_Y, 34.4, 37.8)
    lid = lid.fuse([ear, bridge])
    bore = Part.makeCylinder(1.65, 64, V(-32, HINGE_Y, HINGE_Z), V(1, 0, 0))
    base = base.cut(bore).removeSplitter()
    lid = lid.cut(bore).removeSplitter()
    cover = rounded_box(-half_w + 0.6, half_w - 0.6, FRONT_Y + 0.6, REAR_Y - 0.6,
                        0.0, 2.5, 11.6)
    base, lid = add_uv_mounts(base, lid, FLOOR_Z, RIM_Z)
    return base, lid, cover


def check_collisions(moving, fixed):
    overlaps = []
    for moving_name, moving_shape in moving.items():
        for fixed_name, fixed_shape in fixed.items():
            if moving_shape.BoundBox.intersect(fixed_shape.BoundBox):
                common = moving_shape.common(fixed_shape)
                if common.Volume > OVERLAP_LIMIT:
                    overlaps.append([moving_name, fixed_name, round(common.Volume, 6),
                                     str(common.BoundBox)])
    return overlaps


def support_height(shape, x0, x1, y0, y1):
    # Sample the bottom in the footprint swept over each support on insertion.
    sweep = shape.common(box_xyz(x0, x1, y0 - LOAD_SLIDE, y1, 7, 18))
    assert sweep.Solids
    return sweep.optimalBoundingBox(False, False).ZMin


def feature(doc, group, name, label, shape, color):
    assert shape.isValid() and len(shape.Solids) >= 1, label
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    obj.ViewObject.ShapeColor = color
    group.addObject(obj)
    return obj


def body(doc, name, label, shape, color):
    assert shape.isValid() and len(shape.Solids) == 1, (label, len(shape.Solids))
    obj = doc.addObject("PartDesign::Body", name)
    obj.Label = label
    geometry = obj.newObject("PartDesign::Feature", name + "Shape")
    geometry.Shape = shape
    geometry.ViewObject.ShapeColor = color
    obj.ViewObject.ShapeColor = color
    return obj


def main():
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import").SetInt("ImportMode", 0)
    progress("Reading saved exterior solids")
    exterior, row = cached_exterior()
    progress("Building flush contact row")
    exterior["FlangeSkin"], caps = flush_interface(exterior["FlangeSkin"], row)
    plug_transform = V(0, -FACE_Y, PLUG_AXIS_Z)
    plug = {name: move(shape, plug_transform) for name, shape in exterior.items()}
    caps = [move(shape, plug_transform) for shape in caps]
    flange_support_z = support_height(plug["FlangeSkin"], -17, 17, 8, 14)
    body_support_z = support_height(plug["MetalBody"], -12, 12, 71, 82)
    progress("Building base and lid")
    base, lid, cover = horizontal_enclosure(flange_support_z, body_support_z)
    fixed_uv, moving_uv, uv_source = uv_hardware(MECH.parents[1] / "dock-uv", FLOOR_Z)
    uv_base_shapes = {name: shape for name, _, shape, _ in fixed_uv}
    uv_lid_shapes = {name: shape for name, _, shape, _ in moving_uv}
    uv_mount_hits = check_collisions(uv_base_shapes, {"base": base, "cover": cover})
    uv_mount_hits += check_collisions(uv_lid_shapes, {"lid": lid})
    head = box_xyz(HEAD_X0, HEAD_X1, HEAD_REAR_Y, -HEAD_LAND_GAP, HEAD_Z0, HEAD_Z1)
    pin_centers = [(x, PLUG_AXIS_Z + z) for x, _, z in row]
    loaded_pins = [cyl_y(PIN_R, -HEAD_LAND_GAP, 0, x, z) for x, z in pin_centers]
    free_pins = [cyl_y(PIN_R, -HEAD_LAND_GAP, PIN_TRAVEL, x, z) for x, z in pin_centers]
    keeper_gauges = [cyl_y(1.7, FACE_Y + 1.4, FACE_Y + 2.4, x, z)
                     for x, z in KEEPERS]

    positions = [(LOAD_SLIDE, lift) for lift in (42, 32, 24, 16, 12, 8, 4, 2, 0)]
    positions += [(slide, 0) for slide in (4, 3, 2, 1, 0.5, PIN_TRAVEL, 0.2, 0)]
    progress("Checking loading motion")
    load_hits = []
    open_lid = turn(lid, LID_OPEN_DEG)
    fixed = {"base": base, "open lid": open_lid, "head": head, **uv_base_shapes}
    fixed.update({name: turn(shape, LID_OPEN_DEG) for name, shape in uv_lid_shapes.items()})
    fixed.update({f"pin {i}": pin for i, pin in enumerate(free_pins, 1)})
    for advance, lift in positions:
        moving = {name: move(shape, V(0, advance, lift)) for name, shape in plug.items()}
        for hit in check_collisions(moving, fixed):
            load_hits.append([advance, lift, *hit])

    # Sweep the lid against the actual plug and stationary base.
    hinge_samples = (0, 1, 2, 4, 8, 15, 25, 40, 60, 80, LID_OPEN_DEG)
    progress("Checking hinge motion")
    hinge_hits = []
    for angle in hinge_samples:
        moving = {name: turn(shape, angle) for name, shape in {"lid": lid, **uv_lid_shapes}.items()}
        for hit in check_collisions(moving, {"base": base, **plug, **uv_base_shapes}):
            hinge_hits.append([angle, *hit])
    head_hits = check_collisions({"head": head}, {"base": base, **plug})
    target_contacts = [round(cap.distToShape(pin)[0], 5) for cap, pin in zip(caps, loaded_pins)]
    seated_lid_gap = min(shape.distToShape(lid)[0] for shape in plug.values())
    closed = Part.makeCompound([base, lid, cover]).optimalBoundingBox(False, False)
    uv_construction = Part.makeCompound(list(uv_base_shapes.values()))
    uv_plug_gap = min(shape.distToShape(uv_construction)[0] for shape in plug.values())
    report = {
        "source": {"file": SOURCE.name, "sha256": sha256(SOURCE.read_bytes()).hexdigest()},
        "case_closed_width_depth_height_mm": [round(v, 2) for v in
                                              (closed.XLength, closed.YLength, closed.ZLength)],
        "modeled_custom_rigid_dock_parts": ["base with integral nest", "lid with seam skirt", "bottom cover"],
        "face_extension_mm": [round(old_y - FACE_Y, 3) for _, old_y, _ in row],
        "contact_centers_mm": [[round(x, 3), 0, round(z, 3)] for x, z in pin_centers],
        "loaded_pin_to_target_gap_mm": target_contacts,
        "maximum_sampled_lid_open_deg": LID_OPEN_DEG,
        "minimum_closed_plug_to_lid_mm": round(seated_lid_gap, 3),
        "load_poses": len(positions), "lid_poses": len(hinge_samples),
        "load_overlaps": load_hits, "lid_overlaps": hinge_hits, "head_overlaps": head_hits,
        "uv_c": {
            **uv_source, "fixed_rails": 2, "separate_hall_stations": 2,
            "underfloor_free_height_mm": 4.1, "chamber_floor_over_bay_mm": 1.9,
            "minimum_closed_plug_to_uv_hardware_mm": round(uv_plug_gap, 3),
            "mount_overlaps": uv_mount_hits,
            "scope": "Source Vishay geometry. Rail PCBs, thermal attachment, cable feedthroughs and Hall integration are packaging candidates."
        },
        "scope": "Nominal fit of the source plug exterior, contact interface and UV hardware. Physical fit, cutoff, thermal behavior, leakage and cleaning efficacy require measurement."
    }
    (BUILD / (NAME + "-attempt.json")).write_text(json.dumps(report, indent=2) + "\n")
    assert not (load_hits or hinge_hits or head_hits or uv_mount_hits), "Nominal interference; see attempt report"
    assert target_contacts == [0.0] * 4 and seated_lid_gap > 1
    if not App.GuiUp:
        return
    import ImportGui
    progress("Saving native assembly")

    doc = App.newDocument(NAME)
    base_obj = body(doc, "Base", "Dark base with integral nest and contact pocket", base, DARK)
    lid_obj = body(doc, "Lid", "Orange lid with integral seam skirt", lid, ORANGE)
    lid_obj.Placement = App.Placement(V(), App.Rotation(V(1, 0, 0), -LID_OPEN_DEG),
                                     V(0, HINGE_Y, HINGE_Z))
    cover_obj = body(doc, "ServiceCover", "Bottom service cover", cover, DARK)
    context = doc.addObject("App::Part", "Plug")
    context.Label = "Compact Compass with proposed flush face"
    context.addProperty("App::PropertyString", "ExteriorSource")
    context.ExteriorSource = SOURCE.name
    plug_objects = [feature(doc, context, name, name, shape, PLUM if name == "FlangeSkin" else METAL)
                    for name, shape in plug.items()]
    for i, (cap, net) in enumerate(zip(caps, ("GND", "D-", "D+", "5V")), 1):
        plug_objects.append(feature(doc, context, f"Target{i}", f"Flush target {i} / {net}", cap, GOLD))
    keepers = doc.addObject("App::Part", "Keepers")
    keepers.Label = "Buried keeper pocket envelopes"
    for i, gauge in enumerate(keeper_gauges, 1):
        feature(doc, keepers, f"Keeper{i}", f"Passive keeper {i}",
                move(gauge, plug_transform), METAL)
    keepers.Visibility = False
    hardware = doc.addObject("App::Part", "DockHardware")
    hardware.Label = "Dock hardware and UI envelopes"
    hardware_objects = [feature(doc, hardware, "ContactHead", "Shared magnetic head envelope", head, CREAM)]
    for i, pin in enumerate(loaded_pins, 1):
        hardware_objects.append(feature(doc, hardware, f"Pin{i}", f"Dock spring pin {i}", pin, GOLD))
    hinge = Part.makeCylinder(1.5, 60, V(-30, HINGE_Y, HINGE_Z), V(1, 0, 0))
    hardware_objects.append(feature(doc, hardware, "HingeRod", "Stock 3 mm hinge rod envelope", hinge, METAL))
    screen = rounded_box(-14.8, 14.8, -25.8, -12.2, 32, RIM_Z, 0.8)
    hardware_objects.append(feature(doc, hardware, "Display", "Display lens envelope", screen, (0.15, 0.19, 0.23)))
    for i, x in enumerate((-25, 22, 31), 1):
        switch = Part.makeCylinder(3.1, 2.5, V(x, -19, 32))
        hardware_objects.append(feature(doc, hardware, f"Button{i}", f"Button {i} envelope", switch, BLUE))

    fixed_uv_group = doc.addObject("App::Part", "FixedUV")
    fixed_uv_group.Label = "Four UV-C emitters and two fixed thermal cutoff rails"
    fixed_uv_objects = [feature(doc, fixed_uv_group, *item) for item in fixed_uv]
    lid_uv_group = doc.addObject("App::Part", "LidInterlockTargets")
    lid_uv_group.Label = "Two passive lid interlock targets"
    lid_uv_objects = [feature(doc, lid_uv_group, *item) for item in moving_uv]
    for obj in lid_uv_objects:
        obj.Placement = lid_obj.Placement
    doc.recompute()
    destination = MECH / (NAME + ".FCStd")
    if destination.exists():
        (BUILD / destination.name).write_bytes(destination.read_bytes())
    doc.saveAs(str(destination))
    export = [base_obj, lid_obj, cover_obj, *plug_objects, *hardware_objects,
              *fixed_uv_objects, *lid_uv_objects]
    ImportGui.export(export, str(MECH / (NAME + ".step")))
    lid_obj.Placement = App.Placement()
    for obj in lid_uv_objects:
        obj.Placement = App.Placement()
    doc.recompute()
    ImportGui.export(export, str(MECH / (NAME + "Closed.step")))
    if os.environ.get("COMPASS_MAG_DOCK_EXPORT_CABLE"):
        # Sample dismounted cable head at the same face. Readback of the CAD is separate from USB tests.
        cable = doc.addObject("App::Part", "Cable")
        cable.Label = "Standalone cable, shared magnetic head aligned"
        cable_offset = V(0, -3, 0)
        cable_objects = [feature(doc, cable, "CableHead", "Standalone magnetic head envelope",
                                 move(head, cable_offset), CREAM)]
        for i, pin in enumerate(free_pins, 1):
            cable_objects.append(feature(doc, cable, f"CablePin{i}", f"Cable pin {i}",
                                         move(pin, cable_offset), GOLD))
        tail = Part.makeCylinder(1.6, 22, V(HEAD_X1, -7, 24.5), V(1, 0, 0))
        cable_objects.append(feature(doc, cable, "CableTail", "Cable exit envelope", tail, DARK))
        doc.recompute()
        ImportGui.export([*plug_objects, *cable_objects], str(MECH / "CompactMagneticCable.step"))
    (MECH / "compact-magnetic-dock-fit.json").write_text(json.dumps(report, indent=2) + "\n")
    for backup in MECH.glob(NAME + "*.FCBak"):
        backup.replace(BUILD / backup.name)


def progress(message):
    with (BUILD / (NAME + "-progress.log")).open("a") as log:
        log.write(message + "\n")


BUILD.mkdir(parents=True, exist_ok=True)
try:
    if os.environ.get("COMPASS_MAG_DOCK_PREPARE"):
        prepare_exterior()
    else:
        main()
    (BUILD / (NAME + ".log")).write_text("Completed geometry run.\n")
except Exception:
    (BUILD / (NAME + ".log")).write_text(traceback.format_exc())
    os._exit(1)
os._exit(0)
