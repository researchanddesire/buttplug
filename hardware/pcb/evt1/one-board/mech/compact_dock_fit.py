"""Compare the compact Compass against the saved wired dock in FreeCAD."""

from hashlib import sha256
import json
import os
from pathlib import Path
import traceback

import FreeCAD as App
import Part


MECH = Path(os.environ["COMPASS_DOCK_FIT_MECH"])
BUILD = MECH.parent / "build" / "mech"
DOCK = MECH.parents[3] / "cad/evt1-assembly/evt1-wired/DockAssembly.FCStd"
DEVICE = MECH / "compass-device.FCStd"
MODEL = MECH / "CompactDockFit.FCStd"
REPORT = MECH / "compact-dock-fit.json"
EXCHANGE = BUILD / "compact-dock-exchange"

Vector = App.Vector
OVERLAP_MM3 = 1e-5
SKIN_FACE_Y_MM = -25.9
DOCK_TRAVEL_MM = 3.0
PLUG_LIFT_MM = 1.5
STOP_OD_MM = 2.4
STOP_ID_MM = 1.8
POGO_COMPRESSION_MM = 0.60
HINGE_AXIS = Vector(0, 164.4, 40.15)
DISPLAY_OPENING_DEG = 105

DEVICE_PARTS = {
    "FlangeSkin": (0.42, 0.30, 0.55),
    "FlangeTray": (0.24, 0.24, 0.27),
    "RearCover": (0.32, 0.32, 0.35),
    "MetalBody": (0.75, 0.77, 0.81),
    "MotorThermistorCap": (0.67, 0.69, 0.73),
}
BASE_PARTS = (
    "LowerShellInstance", "LowerChamberInstance", "FrontClosureLowerContentsInstance",
    "ContactCarrierInstance", "ContactRetainerInstance", "DeviceSeatingModuleInstance",
    "BaseUVThermalModuleInstance", "UVBaseBoardAssembly", "LeftHallStation", "RightHallStation",
)
LID_PARTS = (
    "UpperShellInstance", "UpperChamberInstance", "FrontClosureUpperContentsInstance",
    "LidUVThermalModuleInstance", "UVLidBoardAssembly", "LeftHallTarget", "RightHallTarget",
)
COLORS = {
    "LowerShellInstance": (0.18, 0.20, 0.24),
    "LowerChamberInstance": (0.90, 0.84, 0.68),
    "ContactCarrierInstance": (0.26, 0.30, 0.34),
    "DeviceSeatingModuleInstance": (0.32, 0.53, 0.60),
    "UpperShellInstance": (0.92, 0.42, 0.14),
    "UpperChamberInstance": (0.90, 0.84, 0.68),
    "ScallopedBezelInstance": (0.94, 0.86, 0.68),
    "DockLCDInstance": (0.15, 0.18, 0.22),
}


def installed_shape(obj):
    shape = obj.Shape.copy()
    if hasattr(obj, "getGlobalPlacement"):
        parent = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
        shape.Placement = parent.multiply(shape.Placement)
    if shape.isNull() or not shape.Solids or not shape.isValid():
        raise ValueError(f"Invalid saved shape for {obj.Name}")
    return shape


def moved(shape, offset):
    result = shape.copy()
    result.translate(offset)
    return result


def bounds(shape):
    return shape.optimalBoundingBox(False, False)


def face_center(shape, y):
    box = bounds(shape)
    return Vector((box.XMin + box.XMax) / 2, y(box), (box.ZMin + box.ZMax) / 2)


def vector_mm(vector):
    return [round(value, 6) for value in (vector.x, vector.y, vector.z)]


def solid_pairs(device, obstacles):
    for part_name, part in device.items():
        part_box = bounds(part)
        for obstacle_name, obstacle in obstacles.items():
            if part_box.intersect(obstacle.BoundBox):
                for solid in obstacle.Solids:
                    if part_box.intersect(solid.BoundBox):
                        yield part_name, part, obstacle_name, solid


def overlaps(device, obstacles):
    results = []
    for part_name, part, obstacle_name, solid in solid_pairs(device, obstacles):
        intersection = part.common(solid)
        if intersection.Volume > OVERLAP_MM3:
            results.append((part_name, obstacle_name, intersection))
    return results


def record(hits):
    totals = {}
    for part, obstacle, shape in hits:
        key = (part, obstacle)
        totals[key] = totals.get(key, 0) + shape.Volume
    return [{"plug": part, "dock": obstacle, "volume_mm3": round(volume, 5)}
            for (part, obstacle), volume in sorted(totals.items())]


def add_shape(doc, group, label, shape, color):
    if not shape.isValid() or not shape.Solids:
        raise ValueError(f"Invalid review geometry for {label}")
    obj = doc.addObject("Part::Feature", "Geometry")
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyColor", "ReviewColor")
    obj.ReviewColor = color
    group.addObject(obj)
    return obj


def new_group(doc, name, label):
    group = doc.addObject("App::Part", name)
    group.Label = label
    return group


def add_device(doc, group, device, targets, offset):
    for name, shape in device.items():
        add_shape(doc, group, name, moved(shape, offset), DEVICE_PARTS[name])
    for index, shape in enumerate(targets, 1):
        add_shape(doc, group, f"CT{index} metal target", moved(shape, offset), (0.84, 0.67, 0.32))


def stop_ring(point, depth):
    axis = Vector(0, -1, 0)
    return Part.makeCylinder(STOP_OD_MM / 2, depth, point, axis).cut(
        Part.makeCylinder(STOP_ID_MM / 2, depth, point, axis))


def analyze():
    dock = App.openDocument(str(DOCK))
    device = App.openDocument(str(DEVICE))
    exterior = {obj.Label: installed_shape(obj) for obj in device.RootObjects
                if obj.Label in DEVICE_PARTS}
    if set(exterior) != set(DEVICE_PARTS):
        raise ValueError("Compact plug assembly is missing exterior parts")
    target_objects = sorted((obj for obj in device.getObjectsByLabel("PCB")[0].Group
                             if obj.Label.startswith("MillMax194")), key=lambda obj: obj.Placement.Base.x)
    if len(target_objects) != 4:
        raise ValueError("Could not identify all four compact CT targets")
    targets = [installed_shape(obj) for obj in target_objects]
    pins = [installed_shape(dock.getObject(f"ContactPogo{index}")) for index in range(4)]
    target_centers = [face_center(shape, lambda box: box.YMin) for shape in targets]
    pin_centers = [face_center(shape, lambda box: box.YMax) for shape in pins]
    existing = dock.DeviceMetalBody.Placement.Base
    aligned = pin_centers[0] - target_centers[0]
    if any((pin - target - aligned).Length > 0.001 for pin, target in zip(pin_centers, target_centers)):
        raise ValueError("Compact and existing pin axes cannot be registered with a translation")
    base = {name: installed_shape(dock.getObject(name)) for name in BASE_PARTS}
    lid = {name: installed_shape(dock.getObject(name)) for name in LID_PARTS}
    obstacles = base | lid
    aligned_hits = overlaps({name: moved(shape, aligned) for name, shape in exterior.items()}, obstacles)
    print("Existing carrier aligned:", aligned, record(aligned_hits), flush=True)

    existing_body = {name: moved(shape, existing) for name, shape in exterior.items()}
    existing_hits = overlaps(existing_body, obstacles)
    print("Existing body position:", existing, record(existing_hits), flush=True)

    # Preserve the plug's lateral and axial positions relative to the UV boards.
    # Lift it above the existing liner. Stop rings represent a fit envelope.
    revised_pose = existing + Vector(0, 0, PLUG_LIFT_MM)
    revised_centers = [center + revised_pose for center in target_centers]
    recess = target_centers[0].y - SKIN_FACE_Y_MM
    noses = [stop_ring(center, recess + 0.30) for center in revised_centers]
    shifted_pins = [moved(pin, center - old_center) for pin, center, old_center
                    in zip(pins, revised_centers, pin_centers)]
    revised_device = {name: moved(shape, revised_pose) for name, shape in exterior.items()}
    ring_shapes = {f"Stop ring {index}": shape for index, shape in enumerate(noses, 1)}
    pin_shapes = {f"Pogo {index}": shape for index, shape in enumerate(shifted_pins, 1)}
    ring_hits = overlaps(revised_device, ring_shapes | pin_shapes)
    ring_pin_hits = overlaps(ring_shapes, pin_shapes)
    replaced_modules = ("ContactCarrierInstance", "ContactRetainerInstance", "DeviceSeatingModuleInstance")
    retained_case = {name: shape for name, shape in obstacles.items() if name not in replaced_modules}
    revised_case_hits = overlaps(revised_device, retained_case)
    clearance_pairs = (("FlangeSkin", "LowerChamberInstance"), ("FlangeSkin", "UpperChamberInstance"),
                       ("MetalBody", "UVLidBoardAssembly"), ("MotorThermistorCap", "UVLidBoardAssembly"))
    clearances = [{"plug": name, "dock": obstacle,
                   "gap_mm": round(revised_device[name].distToShape(retained_case[obstacle])[0], 6)}
                  for name, obstacle in clearance_pairs]
    print("Raised plug:", record(revised_case_hits), clearances, flush=True)
    dock_interface_hits = overlaps(ring_shapes | pin_shapes, retained_case)
    approach = []
    for delta in (DOCK_TRAVEL_MM, 2.0, 1.0, POGO_COMPRESSION_MM, 0.30, 0.0):
        pose = {name: moved(shape, Vector(0, delta, 0)) for name, shape in revised_device.items()}
        approach.append({"slide_offset_mm": delta, "overlaps": record(overlaps(pose, ring_shapes))})
    print("Revised rings:", record(ring_hits), "Pins:", record(ring_pin_hits),
          "Case:", record(dock_interface_hits), flush=True)

    review = App.newDocument("CompactDockFit")
    context = new_group(review, "DockContext", "Wired dock | lid opened for inspection")
    display_names = ("LowerShellInstance", "LowerChamberInstance", "UpperShellInstance",
                     "UpperChamberInstance", "ScallopedBezelInstance",
                     "DockLCDInstance", "DockButtonLeftCapInstance", "DockButtonCenterCapInstance",
                     "DockButtonRightCapInstance")
    for name in display_names:
        shape = installed_shape(dock.getObject(name))
        if name not in BASE_PARTS:
            shape.rotate(HINGE_AXIS, Vector(1, 0, 0), -DISPLAY_OPENING_DEG)
        add_shape(review, context, name.replace("Instance", ""), shape, COLORS.get(name, (0.16, 0.43, 0.68)))
    retained = new_group(review, "ExistingCarrier", "Existing pin row | forced alignment")
    add_shape(review, retained, "Existing carrier", base["ContactCarrierInstance"], COLORS["ContactCarrierInstance"])
    seat = "DeviceSeatingModuleInstance"
    add_shape(review, retained, "Existing seat", base[seat], COLORS[seat])
    add_device(review, retained, exterior, targets, aligned)
    for index, (_, obstacle, shape) in enumerate(aligned_hits, 1):
        add_shape(review, retained, f"Interference {index} with {obstacle}", shape, (0.94, 0.14, 0.09))
    centered = new_group(review, "RevisedRow", "Centered plug | revised contact-row envelope")
    add_device(review, centered, exterior, targets, revised_pose)
    for name, shape in (ring_shapes | pin_shapes).items():
        add_shape(review, centered, name, shape, (0.12, 0.52, 0.76) if name.startswith("Stop") else (0.79, 0.63, 0.30))
    review.recompute()
    review.saveAs(str(MODEL))

    report = {
        "sources": {str(path.relative_to(MECH.parents[4])): sha256(path.read_bytes()).hexdigest()
                    for path in (DOCK, DEVICE)},
        "existing_body_translation_xyz_mm": vector_mm(existing),
        "compact_target_faces_xyz_mm": [vector_mm(point) for point in target_centers],
        "existing_loaded_pin_faces_xyz_mm": [vector_mm(point) for point in pin_centers],
        "compact_targets_below_flat_skin_face_mm": round(recess, 6),
        "forced_alignment": {"translation_xyz_mm": vector_mm(aligned), "overlaps": record(aligned_hits)},
        "existing_body_overlaps": record(existing_hits),
        "revised_row": {
            "plug_translation_xyz_mm": vector_mm(revised_pose),
            "removed_from_fit_context": list(replaced_modules),
            "retained_case_overlaps": record(revised_case_hits),
            "selected_closed_clearances": clearances,
            "target_faces_xyz_mm": [vector_mm(point) for point in revised_centers],
            "loaded_pin_shift_xyz_mm": vector_mm(revised_centers[0] - pin_centers[0]),
            "stop_od_mm": STOP_OD_MM, "stop_id_mm": STOP_ID_MM,
            "stop_radial_margin_on_target_mm": round((bounds(targets[0]).XLength - STOP_OD_MM) / 2, 6),
            "nominal_pin_compression_mm": POGO_COMPRESSION_MM,
            "noncontact_body_to_stop_or_pin_overlaps": record(ring_hits),
            "stop_to_pin_overlaps": record(ring_pin_hits),
            "stop_or_pin_to_retained_dock_overlaps": record(dock_interface_hits),
            "stop_ring_slide_samples": approach,
        },
        "scope": "Saved nominal solids, selected closed dock obstacles and sampled axial approach to revised stop rings. "
                 "The revised row is a geometric fit envelope. The carrier, mount and nest changes, wire/PCB placement, "
                 "retention, user loading, physical contact sequencing, UV coverage and powered behavior need validation.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")


def prepare_export():
    doc = App.openDocument(str(MODEL))
    EXCHANGE.mkdir(parents=True, exist_ok=True)
    scenarios = {}
    for filename, group in (("CompactDockExistingCarrier", doc.ExistingCarrier), ("CompactDockFit", doc.RevisedRow)):
        entries = []
        for obj in doc.DockContext.Group + group.Group:
            path = EXCHANGE / f"{obj.Name}.brep"
            obj.Shape.exportBrep(str(path))
            entries.append({"file": path.name, "label": obj.Label, "color": list(obj.ReviewColor[:3])})
        scenarios[filename] = entries
    (EXCHANGE / "manifest.json").write_text(json.dumps(scenarios, indent=2) + "\n")


def export():
    import ImportGui

    # A minimal document keeps the offscreen exporter independent of the
    # native assembly view and its grouped view providers.
    scenarios = json.loads((EXCHANGE / "manifest.json").read_text())
    for filename, entries in scenarios.items():
        doc = App.newDocument(filename)
        objects = []
        for entry in entries:
            obj = doc.addObject("Part::Feature", "Geometry")
            obj.Label = entry["label"]
            obj.Shape = Part.read(str(EXCHANGE / entry["file"]))
            obj.ViewObject.ShapeColor = tuple(entry["color"])
            objects.append(obj)
        doc.recompute()
        preview = EXCHANGE / f"{filename}.step"
        ImportGui.export(objects, str(preview))
        shape = Part.read(str(preview))
        original_solids = [solid for obj in objects for solid in obj.Shape.Solids]
        original_volume = sum(solid.Volume for solid in original_solids)
        imported_volume = sum(solid.Volume for solid in shape.Solids)
        if (not shape.isValid() or len(shape.Solids) != len(original_solids)
                or abs(imported_volume - original_volume) > original_volume * 1e-5):
            raise ValueError(f"STEP readback differs from the native solids in {filename}")
        os.replace(preview, MECH / preview.name)
        App.closeDocument(doc.Name)


BUILD.mkdir(parents=True, exist_ok=True)
log = BUILD / "compact-dock-fit.log"
try:
    mode = os.environ.get("COMPASS_DOCK_EXPORT")
    if mode == "prepare":
        prepare_export()
    elif mode == "1":
        export()
    else:
        analyze()
    log.write_text("Completed compact dock fit.\n")
except Exception:
    log.write_text(traceback.format_exc())
    os._exit(1)
os._exit(0)
