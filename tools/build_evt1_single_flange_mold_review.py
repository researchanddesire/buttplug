"""Author and verify the small-mask insert mold candidate in FreeCAD.

Call build(legacy_native, flange_native, output_directory) from a macro.
Input copies may omit legacy GuiDocument.xml to avoid GUI restore faults.
Keep the product geometry and source documents read-only.
"""

import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Part


V = App.Vector
EPS = 0.0001


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def y_cylinder(radius, y0, y1, x, z):
    return Part.makeCylinder(radius, y1 - y0, V(x, y0, z), V(0, 1, 0))


def intersection(first, second):
    if not first.BoundBox.intersect(second.BoundBox):
        return 0.0
    return first.common(second).Volume


def translated(shape, vector):
    copy = shape.copy()
    copy.translate(vector)
    return copy


def fuse(shapes):
    shapes = list(shapes)
    return shapes[0].multiFuse(shapes[1:]).removeSplitter()


def single(shape, name):
    assert shape.isValid() and len(shape.Solids) == 1, name
    return shape


def build(legacy_native, flange_native, output_directory):
    legacy = App.openDocument(str(legacy_native))
    flange = App.openDocument(str(flange_native))
    if App.GuiUp:
        import FreeCADGui as Gui
    out = Path(output_directory)
    out.mkdir(parents=True, exist_ok=False)
    doc = App.newDocument("SingleFlangeMoldReview")
    doc.Label = "Single-board flange mold / removable rear contact insert"
    group = doc.addObject("App::DocumentObjectGroup", "Construction")
    context = doc.addObject("App::DocumentObjectGroup", "SavedFlangeReferences")

    def feature(name, shape, owner=group):
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Shape = shape
        owner.addObject(obj)
        return obj

    def cut(name, base, tool, owner=None):
        obj = doc.addObject("Part::Cut", name)
        obj.Base = base
        obj.Tool = tool
        obj.Refine = True
        if owner:
            owner.addObject(obj)
        doc.recompute()
        return obj

    roles = {
        "RigidTray": "ProposedFlangeTray", "RearCover": "ProposedRearHalf",
        "Silicone": "RevisedContinuousSkin", "Diaphragm": "PermanentSixOpeningDiaphragm",
        "TargetGND": "Contact_GND", "TargetDM": "Contact_USB_DM_CONTACT",
        "TargetDP": "Contact_USB_DP_CONTACT", "Target5V": "Contact_DOCK_5V",
    }
    reference = {name: feature(name, flange.getObject(source).Shape.copy(), context)
                 for name, source in roles.items()}
    skin = reference["Silicone"].Shape
    saved_mask = feature("SavedFaceMask", flange.ContactMoldingFaceMask.Shape.copy(), context)

    # A full solid outer cavity avoids a disconnected island inside the shell.
    # Translate the rear half of the previous filleted profile and bridge the
    # translation at a constant section. Add the saved button crowns and arrow.
    exterior = legacy.RoundedSkinEnvelope90x38.Shape
    split_y = -20.0
    fore = exterior.common(box(-60, 60, split_y, 1, -25, 25))
    aft = exterior.common(box(-60, 60, -37, split_y, -25, 25))
    aft.translate(V(0, -3.2, 0))
    section = max(exterior.slice(V(0, 1, 0), split_y), key=lambda w: Part.Face(w).Area)
    bridge = Part.Face(section).extrude(V(0, -3.2, 0))
    root = legacy.RoundedRootTransition.Shape.common(box(-25, 25, -8, 1, -25, 25))
    arrow = skin.common(box(24.5, 36.5, -30.1, -29.6999, -2.5, 2.5))
    crowns = [flange.getObject(f"IntegralSiliconeBoss{i}").Shape for i in range(2)]
    cavity = feature("CurrentOuterCavity", single(fuse([fore, aft, bridge, root, arrow, *crowns]), "cavity"))
    metal_port = feature("MetalShutoffPort", legacy.TurnedBodyExteriorSource.Shape.copy())
    assert skin.cut(cavity.Shape).Volume < EPS, "Cavity clips the saved silicone"

    # Open the insert window to the Z=0 split. A closed window's lower lip
    # would strike the proud contacts as the upper half moves in +Z.
    rear_face = -38.0
    window = box(-19.5, 5.5, rear_face - 0.1, -29.55, 0, 13.35)
    entry_clearance = box(-19.65, 5.65, rear_face - 0.1, -30.8, 0, 13.50)
    slot = feature("RearInsertSlot", fuse([window, entry_clearance]))
    hole_centres = (-24.0, 10.0)
    pilot_cuts = [y_cylinder(1.25, rear_face - 0.05, rear_face + 5.5, x, 10)
                  for x in hole_centres]
    # Move the parting-line gate clear of the mask window and rear screws.
    gate = y_cylinder(2, rear_face - .1, -29.0, 20, 0)
    funnel = Part.makeCone(4, 2, 3.2, V(20, rear_face - 0.05, 0), V(0, 1, 0))
    vents = [legacy.getObject(f"Vent{i}").Shape.copy() for i in range(4)]
    old_fasteners = [legacy.getObject(f"M4ClampBore{i}").Shape.copy() for i in range(4)]
    dowels = [legacy.getObject(f"AlignmentDowelPocket{i}").Shape.copy() for i in range(2)]
    # A common compound tool retains every real feature as a separate
    # construction object. The overlapping cavity/port/gates are fused.
    flow = single(fuse([skin, gate, funnel, *vents]), "connected skin fill and vents")
    fluid_cut = fuse([cavity.Shape, metal_port.Shape, gate, funnel, *vents])
    shared = feature("CavityGateVentAndClampCuts", Part.makeCompound([fluid_cut, *old_fasteners, *dowels]))
    upper_clearance = feature("InsertAndRetainerClearance", Part.makeCompound([slot.Shape, *pilot_cuts]))
    lower_stock = feature("LowerStock", box(-58, 58, rear_face, 13, -28, 0))
    upper_stock = feature("UpperStock", box(-58, 58, rear_face, 13, 0, 28))
    lower = cut("MoldHalfA", lower_stock, shared)
    upper_base = cut("UpperCavity", upper_stock, shared, group)
    upper = cut("MoldHalfB", upper_base, upper_clearance)

    # Bearing on the outer tool face sets insertion depth. The plate's holes
    # mount to the tool; the contact face lands do not support the fasteners.
    target_solids = [reference[name].Shape for name in ("TargetGND", "TargetDM", "TargetDP", "Target5V")]
    nose = box(-19.5, 5.5, rear_face - 0.02, -29.55, 0, 13.35)
    for void in [cavity.Shape, *target_solids]:
        nose = nose.cut(void)
    carrier = feature("InsertCarrier", single(nose.removeSplitter(), "insert carrier"))
    stop_plate = feature("InsertStopPlate", box(-27, 13, rear_face - 2.6, rear_face, 0, 15))
    pull_tab = feature("InsertPullTab", box(-12, -2, rear_face - 9.0, rear_face - 2.59, 7, 13))
    mounting_clearance = [y_cylinder(1.65, rear_face - 2.7, rear_face + 0.05, x, 10)
                          for x in hole_centres]
    grip = Part.makeCylinder(1.6, 7, V(-7, rear_face - 6, 6.5))
    insert_positive = feature("JoinedInsertAndMask", fuse(
        [carrier.Shape, stop_plate.Shape, pull_tab.Shape, saved_mask.Shape]))
    insert_cuts = feature("InsertMountAndPullHoles", Part.makeCompound([*mounting_clearance, grip]))
    insert = cut("RearContactInsert", insert_positive, insert_cuts)

    tools = [lower, upper, insert]
    for tool in tools:
        single(tool.Shape, tool.Name)
        assert not tool.Shape.check(True), tool.Name
    shapes = {name: obj.Shape for name, obj in reference.items()}
    shapes["MetalBody"] = flange.SourceMetalBody.Shape
    shapes["MetalCap"] = flange.SourceMotorThermistorCap.Shape
    static = {tool.Name: {name: intersection(tool.Shape, shape) for name, shape in shapes.items()}
              for tool in tools}
    assert max(value for row in static.values() for value in row.values()) < EPS, static
    assert intersection(lower.Shape, upper.Shape) < EPS
    # Stop plate remains outside the stock. Check the insert with fasteners
    # withdrawn and the molded assembly fixed while the tool is closed.
    pull = []
    for distance in [i / 4 for i in range(37)]:
        moved = translated(insert.Shape, V(0, -distance, 0))
        max_overlap = max(intersection(moved, shape)
                          for shape in [lower.Shape, upper.Shape, *shapes.values()])
        pull.append([distance, max_overlap])
    assert max(v for _, v in pull) < EPS, pull
    # The shaped nose occupies the cut window next to the saved skin. Check
    # the independent gate path against the installed insert.
    assert intersection(insert.Shape, fuse([gate, funnel])) < EPS
    release = []
    for tool, sign in [(lower, -1), (upper, 1)]:
        for distance in [i / 2 for i in range(15)] + [9, 12, 16, 20, 28, 40]:
            moved = translated(tool.Shape, V(0, 0, sign * distance))
            maximum = max(intersection(moved, shape) for shape in shapes.values())
            release.append([tool.Name, distance, maximum])
    assert max(row[-1] for row in release) < EPS, release
    doc.recompute()
    if App.GuiUp:
        for obj in group.Group + context.Group:
            obj.Visibility = False
        for obj, color in [(lower, (.79, .81, .84)), (upper, (.70, .74, .80)),
                           (insert, (.84, .42, .19)), (reference["Silicone"], (.29, .58, .71))]:
            obj.ViewObject.ShapeColor = color
        lower.Visibility = True
        reference["Silicone"].Visibility = True
        insert.Visibility = True
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.activeDocument().activeView().saveImage(str(out / "OpenMold.png"), 1400, 1000, "White")
    path = out / "SingleFlangeMoldReview.FCStd"
    doc.saveAs(str(path))
    exports = {}
    for obj in tools:
        step = out / (obj.Name + ".step")
        obj.Shape.exportStep(str(step))
        returned = Part.read(str(step))
        single(returned, step.name)
        assert abs(returned.Volume - obj.Shape.Volume) < 0.002
        exports[step.name] = sha(step)
    report = {
        "scope": "Inert casting-tool review, with native product references and sampled removal",
        "legacy_geometry_copy_sha256": sha(legacy_native),
        "flange_geometry_copy_sha256": sha(flange_native),
        "builder_sha256": sha(Path(__file__)),
        "native_sha256": sha(path),
        "STEP_sha256": exports,
        "static_overlaps_mm3": static,
        "rear_insert_poses_mm_and_overlap_mm3": pull,
        "lateral_mold_poses_mm_and_overlap_mm3": release,
        "connected_skin_runner_vents_mL": flow.Volume / 1000,
        "physical_validation": False,
        "geometry_pass": True,
    }
    (out / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
