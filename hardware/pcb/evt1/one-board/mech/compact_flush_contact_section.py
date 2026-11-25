"""Build a compact Compass flush-contact section and check the installed stack.

Run with FreeCAD GUI offscreen. Set COMPASS_FLUSH_MECH to this directory.
Set COMPASS_FLUSH_PREPARE=1 and run in freecadcmd first to capture the source
solids. The concept dimensions are in mm and use the saved device frame.
"""

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import traceback

import FreeCAD as App
import Part


MECH = Path(os.environ["COMPASS_FLUSH_MECH"])
sys.path.insert(0, str(MECH))
from compass_datums import BOARD_F_Y, CONTACTS, CONTACT_HOLE_SQ, CONTACT_SQ, COVER_IN_Y, COVER_OUT_Y, SKIN_T_FACE


NAME = "CompactFlushContactSection"
SOURCE = MECH / "compass-device.FCStd"
DOCK = MECH / "CompactMagneticDock.FCStd"
DOCK_FIT = MECH / "compact-magnetic-dock-fit.json"
BUILD = MECH.parent / "build" / "mech" / "compact-flush-contact"
V = App.Vector
AXIS = V(0, 1, 0)
FACE_Y = COVER_OUT_Y - SKIN_T_FACE
FACE_D = 3.175
STEM_D = 1.50
BORE_D = 1.65
TAIL_D = 0.76
GLAND_OD = 2.80
GLAND_DEPTH = 0.30
SEAL_FREE_ID = 1.80
SEAL_SECTION = 0.40
CLIP_OD = 2.80
CLIP_ID = 1.14
CLIP_THICKNESS = 0.30
CLIP_GROOVE_D = 1.10
CLIP_GROOVE_WIDTH = 0.36
SKIN_WINDOW_MARGIN = 1.50
OVERLAP_MM3 = 1e-5
PIN_FORCE_REFERENCE_N = 0.8
NETS = ("GND", "USB D−", "USB D+", "5 V")
COLORS = {
    "skin": (0.45, 0.30, 0.59),
    "cover": (0.19, 0.22, 0.25),
    "pcb": (0.09, 0.43, 0.29),
    "metal": (0.87, 0.67, 0.31),
    "seal": (0.11, 0.63, 0.76),
    "clip": (0.6, 0.64, 0.7),
    "head": (0.87, 0.82, 0.72),
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cylinder(diameter, y0, y1, x, z):
    return Part.makeCylinder(diameter / 2, y1 - y0, V(x, y0, z), AXIS)


def shape_in_device_frame(obj):
    shape = obj.Shape.copy()
    if hasattr(obj, "getGlobalPlacement"):
        parent = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
        shape.Placement = parent.multiply(shape.Placement)
    return shape


def prepare_sources():
    doc = App.openDocument(str(SOURCE))
    pcb_group = doc.getObjectsByLabel("PCB")[0]
    pcb = doc.getObjectsByLabel("compass-one-board_PCB")[0]
    shapes = {"skin": doc.getObjectsByLabel("FlangeSkin")[0].Shape,
              "cover": doc.getObjectsByLabel("RearCover")[0].Shape,
              "pcb": shape_in_device_frame(pcb)}
    parts_zone = box(-0.1, 22.1, COVER_OUT_Y, -18, -10, -5)
    adjacent = []
    for obj in pcb_group.Group:
        if obj == pcb or obj.Label.startswith("MillMax194") or not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        part = shape_in_device_frame(obj)
        if not part.BoundBox.intersect(parts_zone.BoundBox):
            continue
        row = part.common(parts_zone)
        if row.Volume > OVERLAP_MM3:
            adjacent.append(row)
    if adjacent:
        shapes["adjacent_pcb_parts"] = Part.makeCompound(adjacent)
    saved_targets = []
    for obj in pcb_group.Group:
        if obj.Label.startswith("MillMax194"):
            b = shape_in_device_frame(obj).optimalBoundingBox(False, False)
            saved_targets.append([(b.XMin + b.XMax) / 2, b.YMin, (b.ZMin + b.ZMax) / 2, b.YMax])
    saved_targets.sort()
    assert len(saved_targets) == 4
    assert all(abs(x - sx) < 0.001 and abs(z - sz) < 0.001
               for (x, z), (sx, _, sz, _) in zip(CONTACTS, saved_targets))
    for label, shape in shapes.items():
        assert shape.isValid() and shape.Solids, label
        shape.exportBrep(str(BUILD / f"{label}.brep"))
    App.closeDocument(doc.Name)

    doc = App.openDocument(str(DOCK))
    # These fixture objects are saved in dock coordinates. The two checked
    # centerlines and the face translation relate those coordinates to the plug.
    dock_rows = json.loads(DOCK_FIT.read_text())["contact_centers_mm"]
    dock_z_offset = dock_rows[0][2] - CONTACTS[0][1]
    dock_pins = [doc.getObject(f"Pin{index}").Shape for index in range(1, 5)]
    head = doc.ContactHead.Shape.copy()
    head.translate(V(0, FACE_Y, -dock_z_offset))
    head.exportBrep(str(BUILD / "head.brep"))
    for index, pin in enumerate(dock_pins, 1):
        pin = pin.copy()
        pin.translate(V(0, FACE_Y, -dock_z_offset))
        pin.exportBrep(str(BUILD / f"pin{index}.brep"))
    App.closeDocument(doc.Name)
    (BUILD / "sources.json").write_text(json.dumps({
        "device_sha256": digest(SOURCE), "dock_sha256": digest(DOCK),
        "dock_fit_sha256": digest(DOCK_FIT), "device_parts": list(shapes),
        "original_targets": saved_targets,
    }, indent=2) + "\n")


def groove(x, z):
    return cylinder(GLAND_OD, COVER_OUT_Y, COVER_OUT_Y + GLAND_DEPTH, x, z)


def seal_envelope(x, z):
    # Elliptical section preserves nominal volume at the installed gland height.
    # It represents geometry for section review. Elastomer behavior needs testing.
    c = SEAL_SECTION / 2
    axial_radius = GLAND_DEPTH / 2
    radial_radius = c * c / axial_radius
    center = V(x + SEAL_FREE_ID / 2 + c, COVER_OUT_Y + axial_radius, z)
    ellipse = Part.Ellipse(center + V(radial_radius, 0, 0),
                           center + V(0, axial_radius, 0), center)
    return Part.Face(Part.Wire([ellipse.toShape()])).revolve(V(x, 0, z), AXIS, 360)


def target_stack(x, z, tail_end):
    groove_end = COVER_IN_Y + CLIP_GROOVE_WIDTH
    head = cylinder(FACE_D, FACE_Y, COVER_OUT_Y, x, z)
    stem = cylinder(STEM_D, COVER_OUT_Y, COVER_IN_Y, x, z)
    root = cylinder(CLIP_GROOVE_D, COVER_IN_Y, groove_end, x, z)
    retaining_land = cylinder(STEM_D, groove_end, groove_end + 0.28, x, z)
    tail = cylinder(TAIL_D, groove_end + 0.28, tail_end, x, z)
    target = head.fuse([stem, root, retaining_land, tail]).removeSplitter()
    clip = cylinder(CLIP_OD, COVER_IN_Y, COVER_IN_Y + CLIP_THICKNESS, x, z)
    aperture = cylinder(CLIP_ID, COVER_IN_Y - 0.05, COVER_IN_Y + CLIP_THICKNESS + 0.05, x, z)
    clip_opening = box(x - CLIP_ID / 2, x + CLIP_ID / 2, COVER_IN_Y - 0.05,
                       COVER_IN_Y + CLIP_THICKNESS + 0.05, z, z + CLIP_OD)
    clip = clip.cut([aperture, clip_opening]).removeSplitter()
    return target, seal_envelope(x, z), clip


def add_shape(doc, group, name, label, shape, finish):
    assert shape.isValid() and shape.Solids, label
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    obj.ViewObject.ShapeColor = COLORS[finish]
    group.addObject(obj)
    return obj


def contact_geometry(cache):
    source_parts = {label: Part.read(str(BUILD / f"{label}.brep")) for label in cache["device_parts"]}
    pcb = source_parts["pcb"]
    cover = source_parts["cover"]
    skin = source_parts["skin"]
    half_window = CONTACT_SQ / 2 + SKIN_WINDOW_MARGIN
    xmin, xmax = CONTACTS[0][0] - half_window, CONTACTS[-1][0] + half_window
    zmin, zmax = CONTACTS[0][1] - half_window, CONTACTS[0][1] + half_window
    skin = skin.fuse(box(xmin, xmax, FACE_Y, COVER_OUT_Y, zmin, zmax))
    fills, cuts, skin_holes, stacks = [], [], [], []
    for (x, z), (_, _, _, tail_end) in zip(CONTACTS, cache["original_targets"]):
        half = CONTACT_HOLE_SQ / 2 + 0.08
        fills.append(box(x - half, x + half, COVER_OUT_Y, COVER_IN_Y, z - half, z + half))
        cuts.extend([cylinder(BORE_D, COVER_OUT_Y - 0.1, COVER_IN_Y + 0.1, x, z), groove(x, z)])
        skin_holes.append(cylinder(FACE_D, FACE_Y - 0.05, COVER_OUT_Y + 0.05, x, z))
        stacks.append(target_stack(x, z, tail_end))
    cover = cover.fuse(fills).cut(cuts).removeSplitter()
    skin = skin.cut(skin_holes).removeSplitter()
    solids = [cover, skin, *(shape for stack in stacks for shape in stack)]
    assert all(shape.isValid() and len(shape.Solids) == 1 for shape in solids)
    return source_parts, pcb, cover, skin, stacks


def check_stack(cache, source_parts, pcb, cover, skin, stacks, pins):
    checks = []
    adjacent = source_parts.get("adjacent_pcb_parts")
    for (x, z), original, net, (target, seal, clip), pin in zip(
            CONTACTS, cache["original_targets"], NETS, stacks, pins):
        pairs = {
            "target_cover": (target, cover), "target_skin": (target, skin),
            "target_laminate": (target, pcb), "target_pogo": (target, pin),
            "seal_cover": (seal, cover), "seal_target": (seal, target),
            "clip_cover": (clip, cover), "clip_target": (clip, target),
        }
        if adjacent is not None:
            pairs["target_adjacent_pcb_packages"] = (target, adjacent)
            pairs["clip_adjacent_pcb_packages"] = (clip, adjacent)
        clashes = {name: round(a.common(b).Volume, 8) for name, (a, b) in pairs.items()}
        face_y = target.optimalBoundingBox(False, False).YMin
        contact_gap = target.distToShape(pin)[0]
        support_gap = target.distToShape(cover)[0]
        assert max(clashes.values(), default=0) <= OVERLAP_MM3, (net, clashes)
        assert abs(face_y - FACE_Y) < 1e-5 and contact_gap < 1e-5 and support_gap < 1e-5
        gland_volume = math.pi * ((GLAND_OD / 2)**2 - (BORE_D / 2)**2) * GLAND_DEPTH
        checks.append({
            "net": net, "axis_xz_mm": [x, z], "outer_face_y_mm": round(face_y, 6),
            "extension_from_saved_target_mm": round(original[1] - face_y, 6),
            "loaded_dock_gap_mm": round(contact_gap, 6), "head_to_cover_gap_mm": round(support_gap, 6),
            "seal_envelope_volume_fill_pct": round(seal.Volume / gland_volume * 100, 3),
            "pair_overlap_mm3": clashes,
        })
    return checks


def save_review(cache, pcb, cover, skin, stacks, pins, checks):
    import ImportGui

    doc = App.newDocument(NAME)
    full = doc.addObject("App::Part", "CompleteParts")
    full.Label = "Full revised cover, skin and central PCB reference"
    section = doc.addObject("App::Part", "ContactSection")
    section.Label = "Section through CT1–CT4"
    section_z = CONTACTS[0][1]
    section_cut = box(-4.5, 24.5, FACE_Y - 5, -18.0, section_z - 3.0, section_z)
    head = Part.read(str(BUILD / "head.brep"))
    features = [("Skin", "Silicone skin with four individual openings", skin, "skin"),
                ("Cover", "Rigid cover with four face-seal glands", cover, "cover"),
                ("PCB", "Saved PCB laminate and PTH holes", pcb, "pcb"),
                ("Head", "Shared dock or cable head reference", head, "head")]
    for index, (stack, pin, net) in enumerate(zip(stacks, pins, NETS), 1):
        target, seal, clip = stack
        features.extend([(f"Target{index}", f"CT{index} {net} flush target", target, "metal"),
                         (f"Seal{index}", f"CT{index} compressed seal envelope", seal, "seal"),
                         (f"Clip{index}", f"CT{index} dry-side retaining clip envelope", clip, "clip"),
                         (f"Pin{index}", f"Dock pogo {index} at seated position", pin, "metal")])
    for name, label, shape, finish in features:
        add_shape(doc, full, name, label, shape, finish)
        add_shape(doc, section, f"{name}Section", label, shape.common(section_cut), finish)
    full.ViewObject.Visibility = False
    doc.recompute()
    destination = MECH / f"{NAME}.FCStd"
    if destination.exists():
        (BUILD / destination.name).write_bytes(destination.read_bytes())
    doc.saveAs(str(destination))
    stage = BUILD / f"{NAME}.step"
    ImportGui.export(section.Group, str(stage))
    source_solids = [solid for obj in section.Group for solid in obj.Shape.Solids]
    checked = Part.read(str(stage))
    assert checked.isValid() and len(checked.Solids) == len(source_solids)
    volume = sum(s.Volume for s in source_solids)
    assert abs(sum(s.Volume for s in checked.Solids) - volume) < volume * 1e-5
    os.replace(stage, MECH / stage.name)
    for backup in MECH.glob(f"{NAME}.*.FCBak"):
        backup.replace(BUILD / backup.name)

    bearing_area = math.pi * ((FACE_D / 2)**2 - (GLAND_OD / 2)**2)
    report = {
        "native_sha256": digest(destination), "step_sha256": digest(MECH / stage.name),
        "source_device_sha256": cache["device_sha256"], "source_dock_sha256": cache["dock_sha256"],
        "source_dock_fit_sha256": cache["dock_fit_sha256"], "native_section_solid_count": len(source_solids),
        "contact_pitch_mm": CONTACTS[1][0] - CONTACTS[0][0], "target_face_diameter_mm": FACE_D,
        "contact_to_contact_metal_edge_gap_mm": CONTACTS[1][0] - CONTACTS[0][0] - FACE_D,
        "nominal_face_to_pcb_F_Cu_mm": round(BOARD_F_Y - FACE_Y, 4),
        "stamped_clip_envelope_thickness_mm": CLIP_THICKNESS,
        "face_seal": {
            "free_id_mm": SEAL_FREE_ID, "free_section_mm": SEAL_SECTION, "gland_depth_mm": GLAND_DEPTH,
            "gland_od_mm": GLAND_OD, "nominal_squeeze_pct": (1 - GLAND_DEPTH / SEAL_SECTION) * 100,
            "nominal_cover_bearing_land_mm2_per_contact": round(bearing_area, 5),
            "illustrative_bearing_pressure_MPa_at_0p8N": round(PIN_FORCE_REFERENCE_N / bearing_area, 4),
        },
        "contacts": checks,
        "scope": "Nominal section and interference screen. Target, seal and clip are proposed geometry. "
                 "The silicone overlap, overmold flash, clip installation and retention, plate strength, "
                 "unmated wash seal, wet bridging, contact wear and USB require prototype checks. "
                 "The dock head and keeper pockets are unchanged concepts awaiting hardware selection.",
    }
    (MECH / "compact-flush-contact-fit.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    cache = json.loads((BUILD / "sources.json").read_text())
    assert all(cache[key] == digest(path) for key, path in (
        ("device_sha256", SOURCE), ("dock_sha256", DOCK), ("dock_fit_sha256", DOCK_FIT)))
    source_parts, pcb, cover, skin, stacks = contact_geometry(cache)
    pins = [Part.read(str(BUILD / f"pin{index}.brep")) for index in range(1, 5)]
    checks = check_stack(cache, source_parts, pcb, cover, skin, stacks, pins)
    if App.GuiUp:
        save_review(cache, pcb, cover, skin, stacks, pins, checks)
    else:
        print(json.dumps(checks), flush=True)


BUILD.mkdir(parents=True, exist_ok=True)
try:
    if os.environ.get("COMPASS_FLUSH_PREPARE") == "1":
        prepare_sources()
    else:
        main()
    (BUILD / "run.log").write_text("Completed flush contact section.\n")
except Exception:
    (BUILD / "run.log").write_text(traceback.format_exc())
    os._exit(1)
os._exit(0)
