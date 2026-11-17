"""Build the direct-PC fixture from the approved compact plug and wired dock natives."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
from zipfile import ZipFile

import FreeCAD as App
import MeshPart
import Part

V = App.Vector
OUT = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repository", type=Path)
parser.add_argument("--mating-reference", type=Path, default=OUT / "CompactFirstArticleMatingReference.FCStd")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
repo = (args.repository or OUT.parents[3]).resolve()
product = args.mating_reference.resolve()
output = args.output.resolve()
output.mkdir(exist_ok=True, parents=True)
dock = repo / "hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd"
pin_board = dock.parent / "pcb/PinPCB.FCStd"
exterior = repo / ("hardware/cad/manufacturing-layout/evt1-integration/"
                   "contact-module-trial/single-board/exterior/ButtonPressKeepouts.FCStd")
stock_pin_pcb = repo / "hardware/pcb/evt1/pins/pins-evt1.kicad_pcb"
d = App.newDocument("PCContactFixture")
d.Label = "Compass EVT1 • Direct-PC contact fixture"
groups = {name: d.addObject("App::DocumentObjectGroup", name) for name in
          ("Fixture", "Construction", "ContactHardware", "FirstArticleReferences",
           "DockExclusivityWitnesses")}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


reference = json.loads(product.with_name("compact-reference.json").read_text())
assert digest(product) == reference["sha256"], product


def archive_shape(archive_path, role):
    with ZipFile(archive_path) as archive, TemporaryDirectory() as scratch:
        name = role + ".Shape.brp"
        brep = Path(scratch) / name
        brep.write_bytes(archive.read(name))
        shape = Part.read(str(brep))
    assert shape.isValid(), role
    return shape


def placement(archive_path, role):
    with ZipFile(archive_path) as archive:
        root = ElementTree.fromstring(archive.read("Document.xml"))
    obj = root.find(f"./ObjectData/Object[@name='{role}']")
    pose = obj.find("./Properties/Property[@name='LinkPlacement']/PropertyPlacement")
    point = V(*(float(pose.get(f"P{axis}")) for axis in "xyz"))
    rotation = App.Rotation(*(float(pose.get(f"Q{i}")) for i in range(4)))
    return App.Placement(point, rotation)


def hidden(obj):
    if hasattr(obj, "Visibility"):
        obj.Visibility = False
    if obj.ViewObject:
        obj.ViewObject.Visibility = False


def obj(kind, name, group="Construction"):
    model = d.addObject(kind, name)
    groups[group].addObject(model)
    return model


def box(name, x, y, z, width, depth, height):
    model = obj("Part::Box", name)
    model.Length, model.Width, model.Height = width, depth, height
    model.Placement.Base = V(x, y, z)
    return model


def cyl(name, x, y, z, radius, length, axis=V(0, 1, 0)):
    model = obj("Part::Cylinder", name)
    model.Radius, model.Height = radius, length
    model.Placement = App.Placement(V(x, y, z), App.Rotation(V(0, 0, 1), axis))
    return model


def solid(name, shape, group, color=None):
    model = obj("Part::Feature", name, group)
    model.Shape = shape
    if model.ViewObject and color:
        model.ViewObject.ShapeColor = color
    return model


def fuse(name, items):
    result = obj("Part::MultiFuse", name)
    result.Shapes = items
    result.Refine = True
    for item in items:
        hidden(item)
    return result


def cut(name, blank, tool):
    result = obj("Part::Cut", name)
    result.Base, result.Tool, result.Refine = blank, tool, True
    hidden(blank)
    hidden(tool)
    return result


def cuts(name, blank, tools):
    for i, tool in enumerate(tools):
        blank = cut(name if i == len(tools) - 1 else f"{name}Cut{i+1}", blank, tool)
    return blank


def publish(model, label, color):
    model.Label = label
    groups["Construction"].removeObject(model)
    groups["Fixture"].addObject(model)
    if model.ViewObject:
        model.ViewObject.ShapeColor = color
        model.ViewObject.Visibility = True
    return model


def translated(shape, delta):
    result = shape.copy()
    result.translate(delta)
    return result


def shifted(shape, placement):
    result = shape.copy()
    result.Placement = placement.multiply(result.Placement)
    return result


def bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return tuple(round(q, 7) for q in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))


def moved_bounds(box, translation):
    delta = tuple(translation)
    return tuple(v + delta[i % 3] for i, v in enumerate(box))


def overlap(left, right, lb=None, rb=None):
    lb = bounds(left) if lb is None else lb
    rb = bounds(right) if rb is None else rb
    if any(lb[i + 3] <= rb[i] + 1e-6 or rb[i + 3] <= lb[i] + 1e-6 for i in range(3)):
        return 0.0
    return abs(left.common(right, 1e-7).Volume)


def clear(left, right, label, lb=None, rb=None):
    common = overlap(left, right, lb, rb)
    assert common < 1e-4, (label, common)


register = V(0, 53.2, 32)
coordinates = []
targets = []
for i, net in enumerate(("GND", "DM", "DP", "VBUS"), 1):
    name = f"Actual_CT{i}_Solid0"
    st = translated(archive_shape(product, name), register)
    targets.append(solid("CT" + str(i), st, "FirstArticleReferences", (0.83, 0.65, 0.24)))
    b = bounds(st)
    x, y, z = (b[0] + b[3]) / 2, b[1], (b[2] + b[5]) / 2
    pose = placement(dock, "ContactPogo" + str(i - 1))
    assert abs(x - pose.Base.x) < 1e-6 and abs(z - pose.Base.z) < 1e-6
    assert abs(y - 23.2) < 1e-6
    coordinates.append((i, net, x, y, z, pose))

references = {}
for name, color in (
    ("RevisedContinuousSkin", (0.47, 0.36, 0.66)),
    ("MetalBody", (0.67, 0.73, 0.79)),
    ("MotorThermistorCap", (0.74, 0.79, 0.83)),
):
    model = translated(archive_shape(product, name), register)
    references[name] = solid(name, model, "FirstArticleReferences", color)
skin = references["RevisedContinuousSkin"]

# The print carries no permanent magnet. Fixed guides carry transverse load.
# The separate preload bar reacts the pogo springs via two nonmetallic screws.
deck = box("DeckBlank", -50, 8, 5, 100, 112, 5.5)
uprights = [box("PinRailPostLeft", -24, 17.7962, 10.4, 3.8, 4.6038, 26.2),
            box("PinRailPostRight", 8.2, 17.7962, 10.4, 3.8, 4.6038, 26.2)]
side_fences = [box("GuideLeft", -49, 29, 10.4, 3.75, 23, 25),
               box("GuideRight", 45.25, 29, 10.4, 3.75, 23, 25)]
supports = [box("LeftSeat", -39, 30, 10.4, 15, 16, 2.1),
            box("RightSeat", 24, 30, 10.4, 15, 16, 2.1),
            box("BulbSeat", -6, 106, 10.4, 12, 6, 2.35)]
# The raised arrow is on the opposite side in the correct pose.
key_post = box("AntiFlipKeyPost", -35, 17.7, 10.4, 6, 5.5, 24.6)
key = box("AntiFlipKeyNose", -35, 22.9, 29.7, 6, .54, 4.6)
rail = box("PinRailBlank", -24, 17.7962, 35.4, 36, 5.1038, 11.1)
ring_parts = [cyl(f"MetalFaceStop{i}", x, 22.85, z, 1.20, .35)
              for i, _, x, _, z, _ in coordinates]
base_pieces = [deck, *uprights, *side_fences, *supports, key_post, key, rail, *ring_parts]
joined = fuse("BodyBeforePockets", base_pieces)
ring_bores = [cyl(f"TipGuide{i}", x, 21.27, z, .90, 2.1)
              for i, _, x, _, z, _ in coordinates]
barrel_bores = [cyl(f"BarrelClearance{i}", x, 18.77, z, 1.02, 2.61)
                for i, _, x, _, z, _ in coordinates]
retainer_x = (-22.1, 10.1)
pilot_holes = [cyl(f"RetainerPilot{i}", x, 17.45, 40.3, .80, 4.1)
               for i, x in enumerate(retainer_x)]
cap_x = (-47.1, 47.1)
bar_pilots = [cyl(f"BarPilot{i}", x, 49.3, 30, 1.2, 5.5, V(0, 0, 1))
              for i, x in enumerate(cap_x)]
pcb_pocket = box("PCBRecess", -20.20, 17.40, 35.10, 28.4, 1.3962, 10.4)
base = publish(cuts("BenchSaddle", joined,
                    [pcb_pocket, *ring_bores, *barrel_bores, *pilot_holes, *bar_pilots]),
               "Bench saddle • keyed pin carrier", (0.21, 0.55, 0.73))
# Includes a full open exit window for the J94 pigtail and the four pogo tails.
cover = box("RetainerBlank", -24, 15.2, 35.4, 36, 2.5962, 11.1)
wire_window = box("J94WireExit", -18.6, 15.1, 38.5, 25.2, 2.8, 7.0)
cover_bores = [cyl(f"RetainerPass{i}", x, 15.1, 40.3, 1.10, 2.9)
               for i, x in enumerate(retainer_x)]
retainer = publish(cuts("PogoRetainer", cover, [wire_window, *cover_bores]),
                   "J94 board retainer • rear wire window", (0.27, 0.61, 0.80))

crossbeam = box("BarBridge", -49, 48.5, 48, 98, 7, 5)
legs = [box("BarLegLeft", -49, 48.5, 35.4, 24, 7, 13),
        box("BarLegRight", 25, 48.5, 35.4, 24, 7, 13)]
screw_blocks = [box("BarScrewLeft", -39, 48.5, 26.0, 15, 7, 10),
                box("BarScrewRight", 24, 48.5, 26.0, 15, 7, 10)]
push_holes = [cyl(f"M3AxialPilot{i}", x, 48.4, 30.5, 1.25, 7.3)
              for i, x in enumerate((-30, 30))]
cap_holes = [cyl(f"BarPass{i}", x, 49.3, 35.3, 1.6, 18, V(0, 0, 1))
             for i, x in enumerate(cap_x)]
bar = publish(cuts("PreloadBar", fuse("BarBlank", [crossbeam, *legs, *screw_blocks]),
                   [*push_holes, *cap_holes]),
              "Removable preload bar • M3 nylon screws", (0.16, 0.45, 0.58))

# Visual hardware seats. Solder/print thread and compliant compression are not simulated.
for i, x in enumerate((-30, 30)):
    stop = Part.makeCylinder(1.45, 10.3, V(x, 47.2, 30.5), V(0, 1, 0))
    solid(f"PreloadScrew{i}", stop, "ContactHardware", (0.87, 0.89, 0.88))
for i, x in enumerate((-31.5, 31.5)):
    pad = Part.makeBox(15, 16, .50, V(x - 7.5, 30, 12.5))
    solid(f"FlangePad{i}", pad, "ContactHardware", (0.42, 0.48, 0.51))
solid("BulbSupportPad", Part.makeBox(12, 6, .50, V(-6, 106, 12.75)),
      "ContactHardware", (0.42, 0.48, 0.51))

board = solid("J94PinBoard", shifted(archive_shape(pin_board, "Pcb_319a"),
                                     placement(dock, "PinBoardAssembly")),
              "ContactHardware", (0.33, 0.59, 0.36))
pogo_shell = archive_shape(dock, "ContactPogoSourceShellAndTail")
pogo_tip = archive_shape(dock, "ContactPogoSourceVisiblePlunger")
compressed = []
barrels = []
for i, net, _, _, _, pose in coordinates:
    barrels.append(solid(f"P{90+i}Shell", shifted(pogo_shell, pose), "ContactHardware", (0.71, 0.59, 0.33)))
    compressed.append(solid(f"P{90+i}Tip", shifted(pogo_tip, pose), "ContactHardware", (0.90, 0.70, 0.25)))
    barrels[-1].Label = f"P{90+i} brass sleeve / {net}"
    compressed[-1].Label = f"P{90+i} plunger / {net} / seated"

buttons = []
for i in range(2):
    crown = translated(archive_shape(exterior, f"IntegralSiliconeBoss{i}"), register)
    b = bounds(crown)
    buttons.append((i, crown, (b[0] + b[3]) / 2, b[1], (b[2] + b[5]) / 2))

witness_dock = {}
for name in ("LowerChamber", "ContactCarrier"):
    witness_dock[name] = solid("InstalledDock" + name, archive_shape(dock, name),
                               "DockExclusivityWitnesses", (0.68, 0.65, 0.59))
    hidden(witness_dock[name])

d.recompute()
for item in (base, bar, retainer):
    assert item.Shape.isValid() and len(item.Shape.Solids) == 1, item.Name
for a, b in ((base, bar), (base, retainer), (bar, retainer), (base, board), (retainer, board)):
    clear(a.Shape, b.Shape, (a.Name, b.Name))
for sleeve, tip in zip(barrels, compressed):
    for part in (base, retainer, bar):
        clear(sleeve.Shape, part.Shape, (sleeve.Name, part.Name))
        clear(tip.Shape, part.Shape, (tip.Name, part.Name))

travel = []
for (i, net, x, y, z, pose), target, tip in zip(coordinates, targets, compressed):
    head = bounds(target.Shape)
    pin = bounds(tip.Shape)
    assert abs(pin[4] - y) < 1e-6
    assert abs((head[3] - head[0]) / 2 - 1.5875) < 1e-6
    clear(target.Shape, base.Shape, target.Name)
    clear(target.Shape, tip.Shape, tip.Name)
    seat = Part.makeCylinder(1.2, 0.001, V(x, y, z), V(0, 1, 0))
    seat = seat.cut(Part.makeCylinder(.9, .001, V(x, y, z), V(0, 1, 0)))
    seat_overlap = overlap(seat, target.Shape)
    assert seat_overlap > .0019, (i, seat_overlap)
    travel.append({"target": target.Name, "pogo": f"P{90+i}", "net": net, "seat_mm": [x,y,z],
                   "stroke_mm": .6, "radial_head_to_stop_margin_mm": .3875,
                   "annular_face_contact_mm2": round(seat_overlap/.001, 5),
                   "back_clearance_to_catalog_end_stroke_mm": .797})

# Lower at the +Y setback with the bar removed. Set back as needed for received fit.
# Then move in -Y and let the tips retract, before installing the bar/screws.
device = [*references.values(), *targets]
static = [*base_pieces, retainer, board, *barrels]
initial_bounds = {part.Name: bounds(part.Shape) for part in (*device, *static, *compressed)}
print("Seated native shapes and four annular stops passed", flush=True)
loading = []
for stage, axial, rise in (
    *[("lower", 3.0, step) for step in range(36, -1, -2)],
    *[("seat", step / 8, 0) for step in range(24, -1, -1)],
):
    delta = V(0, axial, rise)
    posture = [translated(item.Shape, delta) for item in device]
    pin_delta = V(0, min(.60, axial), 0)
    pin_motion = [translated(tip.Shape, pin_delta) for tip in compressed]
    for original, moved in zip(device, posture):
        moving_bounds = moved_bounds(initial_bounds[original.Name], delta)
        for keepout in static:
            clear(moved, keepout.Shape, (stage, axial, rise, original.Name, keepout.Name),
                  moving_bounds, initial_bounds[keepout.Name])
        for tip, pin in zip(compressed, pin_motion):
            clear(moved, pin, (stage, axial, rise, original.Name, tip.Name),
                  moving_bounds, moved_bounds(initial_bounds[tip.Name], pin_delta))
    loading.append({"stage":stage, "Y_setback_mm":axial, "Z_lift_mm":rise})
print(f"{len(loading)} loading poses passed", flush=True)
for item in device:
    for h in (retainer, bar):
        clear(item.Shape, h.Shape, (item.Name, h.Name))

keying = []
for lateral in (-.25, 0, .25):
    for rise in (0, .25):
        rotated = skin.Shape.copy()
        rotated.rotate(V(0, 0, 32), V(0, 1, 0), 180)
        rotated.translate(V(lateral, 0, rise))
        obstruction = overlap(rotated, key.Shape)
        assert obstruction > .5, (lateral, rise, obstruction)
        rotated_targets = [target.Shape.copy() for target in targets]
        for target in rotated_targets:
            target.rotate(V(0, 0, 32), V(0, 1, 0), 180)
            target.translate(V(lateral, 0, rise))
        pin_to_wrong_target_gap = min(tip.Shape.distToShape(target)[0]
                                      for tip in compressed for target in rotated_targets)
        assert pin_to_wrong_target_gap > 16
        keying.append({"roll_deg": 180, "X_offset_mm": lateral, "Z_lift_mm": rise,
                       "key_interference_mm3": round(obstruction, 5),
                       "minimum_wrong_target_to_pogo_mm": round(pin_to_wrong_target_gap, 5)})

for i, crown, x, y, z in buttons:
    probe = Part.makeCylinder(1.5, y - 7 + .7, V(x, 7, z), V(0, 1, 0))
    for fixed in (base, retainer, bar):
        clear(probe, fixed.Shape, (i, fixed.Name, "button tool"))
    assert overlap(crown, probe) > .1
    hidden(solid(f"ButtonToolProbe{i}", probe, "DockExclusivityWitnesses"))

exclusivity = {name: round(overlap(sh.Shape, base.Shape), 6) for name, sh in witness_dock.items()}
print("Key, button probes and dock co-seating blocks checked", exclusivity, flush=True)
assert all(volume > 10 for volume in exclusivity.values()), exclusivity
info = obj("App::FeaturePython", "SourceBindings", "Fixture")
for name, value in {
    "ProductAssemblySHA256": reference["source_full_assembly_sha256"],
    "MatingReferenceSHA256": digest(product),
    "DockAssemblySHA256": digest(dock),
    "PinBoardNativeSHA256": digest(pin_board),
    "PinBoardKiCadSHA256": digest(stock_pin_pcb),
    "ButtonWitnessSHA256": digest(exterior),
    "Sequence": "Open bar; lower at +3 mm Y; slide -3 mm; close bar; snug nylon tips to the flange",
    "ContactOrdering": "J94 pins 1..4: GND / D- / D+ / protected 5 V",
    "Scope": "Nominal first-article fit and positive single-host geometry; measure received parts and test unpowered fit",
}.items():
    info.addProperty("App::PropertyString", name, "Source and assembly")
    setattr(info, name, value)
    info.setEditorMode(name, 1)

for child in groups["Construction"].Group + groups["DockExclusivityWitnesses"].Group:
    hidden(child)
d.recompute()
native = output / "Compass EVT1 - Direct PC Contact Fixture.FCStd"
d.saveAs(str(native))
for body in (base, bar, retainer):
    body.Shape.exportStep(str(output / (body.Name + ".step")))

meshes = {}
for body in [base, bar, retainer, board, *compressed, *barrels, *references.values(), *targets]:
    mesh = MeshPart.meshFromShape(Shape=body.Shape, LinearDeflection=.15,
                                 AngularDeflection=.3, Relative=False)
    pts, tri = mesh.Topology
    meshes[body.Name] = {"nodes":[[round(x,4) for x in point] for point in pts],
                         "faces":[list(face) for face in tri]}
(output / "review-mesh.json").write_text(json.dumps(meshes, separators=(",", ":")) + "\n")
report = {
    "native_sha256": digest(native),
    "assembly_sources": {
        reference["source_full_assembly"]: reference["source_full_assembly_sha256"],
        **{path.name: digest(path) for path in (product, dock, pin_board, stock_pin_pcb, exterior)}
    },
    "part_bounds_mm": {model.Name: bounds(model.Shape) for model in (base, bar, retainer, board, skin)},
    "contact_checks": travel,
    "device_loading_poses": loading,
    "incorrect_roll_rejection": keying,
    "button_3mm_axial_probes": [{"center_XZ_mm":[x,z], "hands_or_tool_qualification":"open"}
                                for _, _, x, _, z in buttons],
    "simultaneous_dock_seating_common_volume_mm3": exclusivity,
    "unverified": ["print capability, flatness and thread process", "fixture fastener torque and loads",
                   "received-part alignment, contact forces and continuity", "pigtail and strain relief",
                   "tolerance and deformation proof", "USB and powered testing"],
}
(output / "fixture-fit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"native": str(native), "poses": len(loading), "key": keying,
                  "exclusivity": exclusivity, "pin_board_sha256": digest(stock_pin_pcb)}, indent=2))
