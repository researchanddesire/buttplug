"""FreeCAD helpers for the separate inert, full-scale FDM appearance mockup.

The production STEP sources are read-only. All lengths are millimetres.
The product frame is retained: Z up, dock face toward -Y, tip toward +Y.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import shutil
import FreeCAD as App
import Part
import Sketcher
import MeshPart

MECH = Path(__file__).resolve().parent
PROJECT = MECH.parent
BUILD = PROJECT / 'build' / 'mockup'
PACKET = MECH / 'print-mockup'
for folder in (BUILD, PACKET):
    folder.mkdir(parents=True, exist_ok=True)
SOURCES = ['MetalBody.step', 'MotorThermistorCap.step', 'FlangeSkin.step']
SEAM_BLEND_HALF_WIDTH_MM = 0.1
EXTERIOR_VERSION = 2

def source_hashes():
    return {n: hashlib.sha256((MECH / n).read_bytes()).hexdigest()
            for n in SOURCES + ['compass_datums.py']}

def read_shape(path):
    shape = Part.Shape()
    shape.read(str(path))
    assert shape.isValid() and len(shape.Solids) >= 1, str(path)
    return shape

def exterior():
    """Fill enclosed voids while retaining the saved product's outside surface.

    The closed rigid flange envelope fills the skin's internal cavity; the
    contact window retains its shallow recessed floor. Contact pins and
    electronics are deliberately absent from this inert appearance model.
    """
    from compass_datums import (capped_slab2, FLANGE_X, FLANGE_Z, FLANGE_R,
        SHOULDER_Y, COVER_OUT_Y, FLANGE_END_R, FLANGE_SIDE_R, DOCK_END_R,
        DOCK_SIDE_R)
    cache = BUILD / 'MockupExterior.brep'
    provenance = BUILD / 'MockupExterior.json'
    hashes = source_hashes()
    if cache.exists() and provenance.exists():
        cached = json.loads(provenance.read_text())
        if cached['sources_sha256'] == hashes and cached.get('version') == EXTERIOR_VERSION:
            return read_shape(cache)
    envelope = capped_slab2(FLANGE_X / 2, FLANGE_Z / 2, FLANGE_R,
        SHOULDER_Y, COVER_OUT_Y, FLANGE_END_R, FLANGE_SIDE_R,
        DOCK_END_R, DOCK_SIDE_R)
    joined = read_shape(MECH / 'FlangeSkin.step').fuse(envelope, 0.01)
    for name in ['MetalBody.step', 'MotorThermistorCap.step']:
        joined = joined.fuse(read_shape(MECH / name), 0.01)
    joined = joined.removeSplitter()
    assert joined.isValid() and len(joined.Solids) == 1
    outer = max(joined.Shells, key=lambda s: abs(Part.makeSolid(s).Volume))
    assert outer.isClosed()
    filled = Part.makeSolid(outer)
    assert filled.isValid() and len(filled.Solids) == 1
    # This removes internal cavities, with no added exterior geometry.
    assert joined.cut(filled).Volume < 0.05
    # The source cap/prism seam contains coincident curves with different
    # tessellations. Replace only its 0.2 mm axial band by a ruled section
    # loft. This changes about 0.2 mm3 and produces a closed printable mesh.
    from compass_datums import SKIN_DOCK_END_R, SKIN_T_FACE
    seam_y = COVER_OUT_Y - SKIN_T_FACE + SKIN_DOCK_END_R
    delta = SEAM_BLEND_HALF_WIDTH_MM
    sections = [filled.slice(App.Vector(0, 1, 0), seam_y + d)
                for d in (-delta, delta)]
    assert all(len(wires) == 1 and wires[0].isClosed() for wires in sections)
    bridge = Part.makeLoft([wires[0] for wires in sections], True, True)
    rear = filled.common(Part.makeBox(200, 200 + seam_y - delta, 200,
        App.Vector(-100, -200, -100)))
    front = filled.common(Part.makeBox(200, 200, 200,
        App.Vector(-100, seam_y + delta, -100)))
    printable = rear.fuse(bridge, 1e-5).fuse(front, 1e-5).removeSplitter()
    assert printable.isValid() and len(printable.Solids) == 1
    volume_delta = printable.Volume - filled.Volume
    assert abs(volume_delta) < 1.0
    filled = printable
    filled.exportBrep(str(cache))
    provenance.write_text(json.dumps({'sources_sha256': hashes, 'version': EXTERIOR_VERSION,
        'filled_internal_volume_mm3': filled.Volume - joined.Volume,
        'seam_blend_axial_width_mm': 2 * delta, 'seam_blend_volume_delta_mm3': volume_delta,
        'scope': 'Inert appearance mockup; exterior with 0.2 mm seam band simplified; filled interior; contacts omitted.'}, indent=2) + '\n')
    return filled

def bounds(shape):
    # Trimmed B-spline face boxes include unused control geometry. Measure
    # the exported surface mesh instead, at the documented 0.025 mm chord.
    b = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.025,
        AngularDeflection=math.radians(8), Relative=False).BoundBox
    return [round(getattr(b, k), 6) for k in
            ['XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax']]

def features(shape):
    b = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.025,
        AngularDeflection=math.radians(8), Relative=False).BoundBox
    sizes = sorted([b.XLength, b.YLength, b.ZLength], reverse=True)
    return dict(volume_cm3=round(shape.Volume / 1000, 6),
        area_cm2=round(shape.Area / 100, 6),
        **dict(zip(['size_x_mm', 'size_y_mm', 'size_z_mm'],
                   [round(v, 6) for v in sizes])))

def write_part(doc, body, name, print_shape, color, qty=1):
    doc.recompute()
    assert body.Shape.isValid() and len(body.Shape.Solids) == 1
    assert print_shape.isValid() and len(print_shape.Solids) == 1
    if App.GuiUp:
        body.ViewObject.ShapeColor = color
        body.Tip.ViewObject.ShapeColor = color
    doc.saveAs(str(MECH / (name + '.FCStd')))
    if App.GuiUp:
        import ImportGui
        ImportGui.export([body], str(MECH / (name + '.step')))
    else:
        body.Shape.exportStep(str(MECH / (name + '.step')))
    mesh = MeshPart.meshFromShape(Shape=print_shape, LinearDeflection=0.025,
        AngularDeflection=math.radians(8), Relative=False)
    assert mesh.BoundBox.ZMin >= -1e-4, 'Print mesh is below the split plane'
    assert mesh.isSolid() and mesh.hasNonManifolds() is False
    assert mesh.countComponents() == 1
    stl = PACKET / (name + '.stl')
    mesh.write(str(stl))
    reread = read_shape(MECH / (name + '.step'))
    assert abs(reread.Volume - body.Shape.Volume) < body.Shape.Volume * 1e-5
    report = {'valid': True, 'native_solids': 1, 'mesh_watertight': mesh.isSolid(),
        'mesh_components': mesh.countComponents(), 'triangles': mesh.CountFacets,
        'assembled_bounds_mm': bounds(body.Shape),
        'print_bounds_mm': bounds(print_shape), 'sources_sha256': source_hashes(),
        'features': features(body.Shape), 'quantity': qty,
        'print_mesh': str(stl.relative_to(MECH)), 'physical_print_verified': False}
    (PACKET / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    fab = {'kind': '3dp', 'name': name + ' (inert local print)', 'source': name + '.step',
        'qty': qty, 'order': False, 'options': {'process': 'fdm', 'material': 'pla',
        'color': 'gray'}, 'features': features(body.Shape)}
    (MECH / (name + '.fab.json')).write_text(json.dumps(fab, indent=2) + '\n')
    for backup in MECH.glob('*.FCBak'):
        shutil.move(str(backup), str(BUILD / backup.name))
    return report

def build_half(name, sign, hole_d, hole_depth, centers):
    solid = exterior()
    clip = Part.makeBox(200, 300, 100,
        App.Vector(-100, -100, 0 if sign > 0 else -100))
    blank_shape = solid.common(clip)
    assert blank_shape.isValid() and len(blank_shape.Solids) == 1
    doc = App.newDocument(name)
    body = doc.addObject('PartDesign::Body', 'MockupHalf')
    body.addProperty('App::PropertyString', 'SourceHashes', 'Provenance')
    body.SourceHashes = json.dumps(source_hashes(), sort_keys=True)
    body.addProperty('App::PropertyString', 'Purpose', 'Provenance')
    body.Purpose = 'Inert full-scale appearance mockup; source product unchanged.'
    base = body.newObject('PartDesign::Feature', 'SourceExteriorHalf')
    base.Label = 'Saved exterior, filled and split at Z=0'
    base.Shape = blank_shape
    sketch = body.newObject('Sketcher::SketchObject', 'AlignmentHoleSketch')
    sketch.Label = 'Three alignment holes on the flat join'
    for x, y in centers:
        i = sketch.addGeometry(Part.Circle(App.Vector(x, y, 0), App.Vector(0, 0, 1), hole_d / 2), False)
        sketch.addConstraint(Sketcher.Constraint('Diameter', i, hole_d))
        sketch.addConstraint(Sketcher.Constraint('DistanceX', i, 3, x))
        sketch.addConstraint(Sketcher.Constraint('DistanceY', i, 3, y))
        hole = Part.makeCylinder(hole_d / 2, hole_depth, App.Vector(x, y, 0), App.Vector(0, 0, sign))
        assert abs(blank_shape.common(hole).Volume - hole.Volume) < 1e-3, 'Hole breaks through the exterior'
    doc.recompute()
    pocket = body.newObject('PartDesign::Pocket', 'AlignmentHoles')
    pocket.Profile = sketch
    pocket.Length = hole_depth
    pocket.Reversed = sign > 0
    doc.recompute()
    assert pocket.Shape.isValid() and len(pocket.Shape.Solids) == 1
    assert blank_shape.Volume - pocket.Shape.Volume > 90
    if App.GuiUp:
        base.ViewObject.Visibility = False
        sketch.ViewObject.Visibility = False
    print_shape = body.Shape.copy()
    if sign < 0:
        print_shape.rotate(App.Vector(), App.Vector(0, 1, 0), 180)
    report = write_part(doc, body, name, print_shape, (0.72, 0.73, 0.76))
    report.update(hole_diameter_mm=hole_d, blind_hole_depth_mm=hole_depth,
        hole_centers_XY_mm=centers, split_plane='Z=0', print_orientation='Flat split face down')
    (PACKET / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n')

def run_logged(name, function):
    import traceback
    code = 0
    try:
        (BUILD / (name + '.log')).write_text('Building\n')
        function()
        (BUILD / (name + '.log')).write_text('OK\n')
    except Exception:
        (BUILD / (name + '.log')).write_text(traceback.format_exc())
        code = 1
    finally:
        os._exit(code)
