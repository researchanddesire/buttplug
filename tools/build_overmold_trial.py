"""Build an inert, closed-flange silicone casting trial with FreeCAD Python.

Usage: python tools/build_overmold_trial.py [manufacturing-folder] [output-folder]
No product source is modified. The solid dummy represents the CLOSED assembly;
it deliberately has no battery, electronics, buttons, feedthroughs or threads.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import MeshPart

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'hardware/cad/manufacturing-layout'
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else SOURCE / 'overmold-trial'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_native = SOURCE / 'ManufacturingLayout.FCStd'
source_review = json.loads((SOURCE / 'review.json').read_text())
assert sha(source_native) == source_review['native_sha256'], 'Source checkpoint differs'
S = A.openDocument(str(source_native))
D = A.newDocument('OvermoldTrial')
D.Label = 'Closed-flange overmold / inert casting trial only'
construction = D.addObject('App::DocumentObjectGroup', 'Construction')
trial = D.addObject('App::DocumentObjectGroup', 'TrialParts')
references = D.addObject('App::DocumentObjectGroup', 'ProductReferences')


def feature(name, shape, group=construction):
    obj = D.addObject('PartDesign::Feature', name)
    obj.Shape = shape
    group.addObject(obj)
    return obj


def boolean(kind, name, left, right):
    obj = D.addObject('Part::' + kind, name)
    obj.Base, obj.Tool, obj.Refine = left, right, True
    construction.addObject(obj)
    D.recompute()
    return obj


def union(name, objects):
    obj = D.addObject('Part::MultiFuse', name)
    obj.Shapes, obj.Refine = objects, True
    construction.addObject(obj)
    D.recompute()
    return obj


def box(name, x, y, z, length, width, height):
    obj = D.addObject('Part::Box', name)
    obj.Length, obj.Width, obj.Height = length, width, height
    obj.Placement.Base = A.Vector(x, y, z)
    construction.addObject(obj)
    return obj


def cylinder(name, radius, start, length, axis=(0, 0, 1)):
    obj = D.addObject('Part::Cylinder', name)
    obj.Radius, obj.Height = radius, length
    obj.Placement = A.Placement(A.Vector(*start), A.Rotation(A.Vector(0, 0, 1), A.Vector(*axis)))
    construction.addObject(obj)
    return obj


def rounded_rectangle(hx, hz, radius, y):
    vec = lambda x, z: A.Vector(x, y, z)
    q = math.sqrt(.5)
    steps = [
        ((-hx+radius, -hz), (hx-radius, -hz), None),
        ((hx-radius, -hz), (hx, -hz+radius), (hx-radius+radius*q, -hz+radius-radius*q)),
        ((hx, -hz+radius), (hx, hz-radius), None),
        ((hx, hz-radius), (hx-radius, hz), (hx-radius+radius*q, hz-radius+radius*q)),
        ((hx-radius, hz), (-hx+radius, hz), None),
        ((-hx+radius, hz), (-hx, hz-radius), (-hx+radius-radius*q, hz-radius+radius*q)),
        ((-hx, hz-radius), (-hx, -hz+radius), None),
        ((-hx, -hz+radius), (-hx+radius, -hz), (-hx+radius-radius*q, -hz+radius-radius*q)),
    ]
    return Part.Wire([Part.makeLine(vec(*a), vec(*b)) if middle is None else
                      Part.Arc(vec(*a), vec(*middle), vec(*b)).toShape()
                      for a, b, middle in steps])


def final(obj):
    construction.removeObject(obj)
    trial.addObject(obj)
    assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1, (obj.Name, obj.Shape.isValid(), len(obj.Shape.Solids), [s.Volume for s in obj.Shape.Solids])
    return obj


# A solid OUTER gauge of the two CLOSED halves. Do not fill the real electronics
# cavity with silicone or infer sealing at its existing openings from this gauge.
tray_outer = feature('ClosedTrayEnvelope', S.getObject('DraftedTrayOutside').Shape.copy())
cover_outer = feature('ClosedCoverEnvelope', S.getObject('CoverPlateBlank').Shape.copy())
closed_flange = union('ClosedFlangeEnvelope', [tray_outer, cover_outer])
body = feature('InstalledMetalBodyReference', S.getObject(source_review['native_object_names']['MetalBody']).Shape.copy(), references)
cap = feature('InstalledCapReference', S.getObject(source_review['native_object_names']['MotorThermistorCap']).Shape.copy(), references)
body_exterior = feature('TurnedBodyExteriorSource', S.getObject('TurnedBodyBlank').Shape.copy())

# Full continuous skin target. 90 x 38 follows the current packaging target;
# only 1 mm nominal silicone remains beyond the 88 mm rigid flange ends.
outside = Part.Face(rounded_rectangle(45, 19, 7, -26.5)).extrude(A.Vector(0, 20.5, 0))
perimeter_edges = [edge for edge in outside.Edges if edge.BoundBox.YLength < 1e-6]
outside = outside.makeFillet(1.0, perimeter_edges)
flange_skin_envelope = feature('RoundedSkinEnvelope90x38', outside)
root_points = [(0, -8), (15, -8), (15, -6), (10.5, -3), (0, -3)]
wire = Part.makePolygon([A.Vector(r, y, 0) for r, y in root_points + root_points[:1]])
root = feature('ContinuousRootEnvelope', Part.Face(wire).revolve(A.Vector(), A.Vector(0, 1, 0), 360))
skin_envelope = union('SkinEnvelopeWithRoot', [flange_skin_envelope, root])
root_edges = [edge for edge in skin_envelope.Shape.Edges
              if edge.BoundBox.YLength < 1e-5 and abs(edge.BoundBox.YMin + 6) < 1e-4
              and abs(edge.BoundBox.XLength - 30) < 1e-4]
assert len(root_edges) == 1, 'Identify only the external root/flange transition'
smooth = feature('RoundedRootTransition', skin_envelope.Shape.makeFillet(.8, root_edges))
# Tactile +X back marker. This is a proposed manufacturing-axis assignment,
# not registration of a sensor that has not yet been selected or installed.
arrow_points = [(25, -.7), (32, -.7), (32, -2), (36, 0), (32, 2), (32, .7), (25, .7)]
arrow_wire = Part.makePolygon([A.Vector(x, -26.49, z) for x, z in arrow_points + arrow_points[:1]])
arrow = feature('BackArrowPlusX', Part.Face(arrow_wire).extrude(A.Vector(0, -.36, 0)))
marked_envelope = union('MarkedSkinEnvelope', [smooth, arrow])
insert_and_body = union('ClosedInsertAndInstalledBody', [closed_flange, body_exterior])
skin = final(boolean('Cut', 'TrialContinuousSkin', marked_envelope, insert_and_body))

# Inert one-piece print gauge ONLY. It is not a proposed replacement for the
# two product halves, a structural root test, or a threaded assembly trial.
root_clip = box('RootGaugeClip', -20, -25, -20, 40, 38, 40)
dummy_root = boolean('Common', 'InertRootExterior', body_exterior, root_clip)
stem = cylinder('DummyNeckExtension', 7.5, (0, 12.9, 0), 9.1, (0, 1, 0))
locator_bar = box('DummyAxialLocator', -13, 13, -4, 26, 4, 8)
dummy = final(union('ClosedAssemblyDummy', [closed_flange, dummy_root, stem, locator_bar]))
dummy.addProperty('App::PropertyString', 'Scope')
dummy.Scope = 'Solid inert CLOSED-assembly gauge; no threads, internals or product service/assembly proof'

# Split at Z=0; tools open along +/-Z around the already-installed root.
# The body contour above the cuff is the nominal shutoff. No printable-fit,
# flash seal, pressure rating or finished-metal clamping allowance is inferred.
casting_envelope = union('MoldCavityAndBodyPort', [marked_envelope, body_exterior])
gate = cylinder('FillRunnerDiameter4', 2, (0, -37.1, 0), 11.5, (0, 1, 0))
funnel = feature('FillEntryFunnel', Part.makeCone(4, 2, 3.2, A.Vector(0, -37.1, 0), A.Vector(0, 1, 0)))
vents = [box('Vent' + str(i), x-.3, bottom, -.15, .6, 13.1-bottom, .3)
         for i, (x, bottom) in enumerate([(-32, -6.5), (32, -6.5), (-10.2, -4), (10.2, -4)])]
bolt_centers = [(-52, -31), (52, -31), (-52, 6), (52, 6)]
bolts = [cylinder('M4ClampBore' + str(i), 2.25, (x, y, -28.1), 56.2)
         for i, (x, y) in enumerate(bolt_centers)]
pin_centers = [(-52, -15), (51, -7)]
pins = [cylinder('AlignmentDowelPocket' + str(i), 2.1, (x, y, -5.5), 11)
        for i, (x, y) in enumerate(pin_centers)]
pry_slots = [box('PartingPryRelief' + str(i), x, -20, -.8, 2.1, 6, 1.6)
             for i, x in enumerate((-58.1, 56))]
common_cuts = union('SharedToolCuts', [casting_envelope, gate, funnel] + vents + bolts + pins + pry_slots)
mold_a = final(boolean('Cut', 'MoldHalfA', box('ToolStockA', -58, -37, -28, 116, 50, 28), common_cuts))
mold_b = final(boolean('Cut', 'MoldHalfB', box('ToolStockB', -58, -37, 0, 116, 50, 28), common_cuts))

intent = D.addObject('App::FeaturePython', 'TrialIntent')
for key, value in {
    'Scope': 'PRINTABLE INERT CASTING TRIAL; no product/tooling/material/process release',
    'Sequence': 'Installed lower body + BOTH CLOSED rigid flange halves, then one continuous skin',
    'Dummy': 'Solid one-piece representation of CLOSED assembly for fill/demold only; no internals',
    'SkinTarget': '90 x 38; Y -26.5..-6; root to Y-3; raised back arrow adds 0.35 at rear',
    'Split': 'Z=0 through metal-body axis; remove bolts, A pulls -Z and B pulls +Z along dowels',
    'Fill': '4mm gate from Y-37 into rear skin; four 0.6 x 0.3 vents exit Y13; no flow or pressure qualification',
    'Hardware': '4 x M4x65 through bolts, 8 M4 flat washers, 4 M4 nuts; 2 x diameter4 x10 removable dowels',
    'Locator': 'Dummy-only bar rests on tool top Y13; do not add it to the metal product',
    'Marker': 'Raised back arrow proposes +X; electronics axis registration remains open',
    'Fit': 'Zero nominal neck shutoff, dowel bores4.2; actual printing/finish fit requires a dry trial',
    'Omissions': 'Contacts/button barriers, actual closed-cavity seals, final bond keys and battery service remain open',
    'Cap': 'Current cap prewired/threaded and tails joined before closing flange; cap-last remains unproven',
}.items():
    intent.addProperty('App::PropertyString', key, 'TrialIntent')
    setattr(intent, key, value)
D.recompute()

parts = [skin, dummy, mold_a, mold_b]
exports = {}
for obj in parts:
    assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1, obj.Name
    step = OUT / (obj.Name + '.step')
    obj.Shape.exportStep(str(step))
    step.write_text('\n'.join(line.rstrip() for line in step.read_text().splitlines()) + '\n')
    display = MeshPart.meshFromShape(Shape=obj.Shape, LinearDeflection=.05, AngularDeflection=.2, Relative=False)
    assert display.isSolid(), obj.Name
    display.write(str(OUT / (obj.Name + '-view.stl')))
    if obj != skin:
        shape = obj.Shape.copy()
        # Tool cavity faces UP. Dummy prints on its closed rear flange face.
        if obj == mold_a:
            pass
        elif obj == mold_b:
            shape.rotate(A.Vector(), A.Vector(1, 0, 0), 180)
        else:
            shape.rotate(A.Vector(), A.Vector(1, 0, 0), 90)
        bounds = shape.BoundBox
        shape.translate(A.Vector(-bounds.XMin, -bounds.YMin, -bounds.ZMin))
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.04, AngularDeflection=.2, Relative=False)
        assert mesh.isSolid()
        mesh.write(str(OUT / (obj.Name + '.stl')))
    exports[obj.Name] = {'STEP_sha256': sha(step), 'view_STL_sha256': sha(OUT / (obj.Name + '-view.stl'))}
    if obj != skin:
        exports[obj.Name]['print_STL_sha256'] = sha(OUT / (obj.Name + '.stl'))

# Native, real section faces for the review renderer; no triangle clipping.
negative_z = Part.makeBox(200, 200, 80, A.Vector(-100, -80, -80))
for obj in (skin, dummy):
    shape = obj.Shape.common(negative_z)
    section_path = OUT / (obj.Name + '-section-view.stl')
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=.04, AngularDeflection=.2, Relative=False).write(str(section_path))
    exports[obj.Name]['section_view_STL_sha256'] = sha(section_path)
native = OUT / 'OvermoldTrial.FCStd'
D.saveAs(str(native))

# Headless FreeCAD has no view providers. Add a default cavity-facing native
# view without modifying any geometry entries, matching existing repo practice.
with zipfile.ZipFile(native) as archive:
    payload = [(info, archive.read(info)) for info in archive.infolist()]
    document = ET.fromstring(archive.read('Document.xml'))
names = [obj.get('name') for obj in document.findall('Objects/Object')]
visible = {'TrialParts', 'MoldHalfA', 'TrialIntent'}
gui = ET.Element('Document', SchemaVersion='1', HasExpansion='1')
ET.SubElement(gui, 'Expand', count='0')
providers = ET.SubElement(gui, 'ViewProviderData', Count=str(len(names)))
for rank, name in enumerate(names):
    provider = ET.SubElement(providers, 'ViewProvider', name=name, expanded='0', treeRank=str(rank))
    properties = ET.SubElement(provider, 'Properties', Count='1', TransientCount='0')
    prop = ET.SubElement(properties, 'Property', name='Visibility', type='App::PropertyBool', status='1')
    ET.SubElement(prop, 'Bool', value='true' if name in visible else 'false')
pending = native.with_suffix('.view-tmp')
with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for info, blob in payload:
        if info.filename != 'GuiDocument.xml':
            archive.writestr(info, blob)
    archive.writestr('GuiDocument.xml', ET.tostring(gui, encoding='utf-8', xml_declaration=True))
with zipfile.ZipFile(pending) as archive:
    assert all(archive.read(info.filename) == blob for info, blob in payload if info.filename != 'GuiDocument.xml')
pending.replace(native)

review = {
    'scope': 'Inert closed-assembly overmold casting trial only; no electronics/human-use/tooling release',
    'native_sha256': sha(native), 'source_native_sha256': sha(source_native),
    'builder_sha256': sha(Path(__file__)), 'exports': exports,
    'skin_target_mm': [90, 38], 'minimum_nominal_end_skin_mm': 1,
    'rear_face_Y_mm': -26.5, 'top_face_Y_mm': -6, 'root_end_Y_mm': -3,
    'arrow': {'direction': '+X back proposal', 'height_mm': .35},
    'tool_half_block_mm': [116, 50, 28], 'tool_split': 'Z=0; opens +/-Z',
    'M4_bolt_centers_XY_mm': bolt_centers, 'dowel_centers_XY_mm': pin_centers,
    'dowel_pocket_diameter_mm': 4.2, 'dowel_pocket_total_depth_mm': 11,
    'gate_diameter_mm': 4, 'vent_width_depth_mm': [.6, .3],
    'vent_center_X_bottomY_mm': [[-32, -6.5], [32, -6.5], [-10.2, -4], [10.2, -4]],
    'hardware_trial': {'M4x65_bolt': 4, 'M4_flat_washer': 8, 'M4_nut': 4, 'diameter4x10_dowel': 2},
    'silicone_skin_volume_ml': skin.Shape.Volume / 1000,
    'limits': [
        'Solid dummy replaces the closed assembly ONLY for external filling/demolding; no real cavity-leak/button/contact test.',
        'No exact silicone/tool/release material, shrink allowance, pressure, cure time or production temperature selected.',
        'Nominal zero neck shutoff; printing, finishing and real metal tolerance need physical fit and flash trials.',
        'Dummy locator bar is not a product feature. Dummy print needs support under this external bar.',
        'Source metal threads remain pilot/root envelopes; dummy has no threads or structural acceptance.',
        'Clamp holes and removable dowels are dimensional allowances; no clamp-force or tool-strength rating.',
        'Nut locking, actual pack/battery service, contact/button sealing, NTC/USB/compass PCB and dock remain unresolved.',
    ],
}
(OUT / 'review.json').write_text(json.dumps(review, indent=2) + '\n')
assert sha(source_native) == source_review['native_sha256'], 'Product source changed during trial build'
print(json.dumps({'native': str(native), 'silicone_skin_ml': review['silicone_skin_volume_ml'], 'source_unchanged': True}), flush=True)
