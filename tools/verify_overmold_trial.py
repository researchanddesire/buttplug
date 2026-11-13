"""Independent saved-native/STEP/mesh and finite-release checks, FreeCAD Python.

Usage: python tools/verify_overmold_trial.py OUTPUT [manufacturing-folder]
These are geometry checks, not a flow simulation, slicer or physical trial.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import Mesh

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve()
SOURCE = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / 'hardware/cad/manufacturing-layout'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = json.loads((OUT / 'review.json').read_text())
native = OUT / 'OvermoldTrial.FCStd'
assert sha(native) == report['native_sha256']
assert sha(SOURCE / 'ManufacturingLayout.FCStd') == report['source_native_sha256']
assert sha(ROOT / 'tools/build_overmold_trial.py') == report['builder_sha256']
D = A.openDocument(str(native))
sh = lambda name: D.getObject(name).Shape
intersection = lambda a, b: a.common(b).Volume
EPS = 1e-4

checks = {}
for name, expected in report['exports'].items():
    shape = sh(name)
    assert shape.isValid() and len(shape.Solids) == 1, name
    step = OUT / (name + '.step')
    assert sha(step) == expected['STEP_sha256']
    back = Part.Shape()
    back.read(str(step))
    assert back.isValid() and len(back.Solids) == 1, name
    volume_delta = back.Volume - shape.Volume
    assert abs(volume_delta) < .02, (name, volume_delta)
    difference = shape.cut(back).Volume + back.cut(shape).Volume
    assert abs(difference) < .02, (name, difference)
    view = OUT / (name + '-view.stl')
    assert sha(view) == expected['view_STL_sha256']
    assert Mesh.Mesh(str(view)).isSolid(), name
    checks[name] = {'valid_single_solid': True, 'STEP_symmetric_difference_mm3': difference,
                    'STEP_volume_delta_mm3': volume_delta, 'native_volume_mm3': shape.Volume}
    if 'section_view_STL_sha256' in expected:
        section = OUT / (name + '-section-view.stl')
        assert sha(section) == expected['section_view_STL_sha256']
        mesh = Mesh.Mesh(str(section))
        assert mesh.isSolid()
        assert abs(abs(mesh.Volume) - shape.Volume / 2) < max(1, shape.Volume * .0005)
    if 'print_STL_sha256' in expected:
        printed = OUT / (name + '.stl')
        assert sha(printed) == expected['print_STL_sha256']
        mesh = Mesh.Mesh(str(printed))
        assert mesh.isSolid()
        bounds = mesh.BoundBox
        assert abs(bounds.ZMin) < 1e-4
        checks[name]['print_mesh_closed'] = True
        checks[name]['print_bounds_xyz_mm'] = [bounds.XLength, bounds.YLength, bounds.ZLength]
        # Purposeful flat-face print poses are rigid transforms of native geometry.
        assert abs(abs(mesh.Volume) - shape.Volume) < max(1, shape.Volume * .0005)

flange = sh('ClosedFlangeEnvelope')
envelope = sh('RoundedSkinEnvelope90x38')
assert flange.cut(envelope).Volume < EPS, 'Closed rigid insert leaves silicone envelope'
minimum = Part.makeShell(flange.Faces).distToShape(Part.makeShell(envelope.Faces))[0]
assert .99 <= minimum <= 1.01, minimum
skin, dummy = sh('TrialContinuousSkin'), sh('ClosedAssemblyDummy')
for obstacle in (dummy, sh('InstalledMetalBodyReference'), sh('InstalledCapReference')):
    assert intersection(skin, obstacle) < EPS
assert len(skin.Solids) == 1, 'The skin must be continuous'
assert intersection(sh('BackArrowPlusX'), skin) > 1, 'Back marker missing'
for name in ('FillRunnerDiameter4', 'Vent0', 'Vent1', 'Vent2', 'Vent3'):
    assert intersection(sh(name), skin) > .001, (name, 'does not reach skin')

# Shared fill/vent network must connect to the skin, apart from the insert.
flow = skin.multiFuse([sh(name) for name in ('FillRunnerDiameter4', 'FillEntryFunnel', 'Vent0', 'Vent1', 'Vent2', 'Vent3')])
flow = flow.cut(dummy).removeSplitter()
assert flow.isValid() and len(flow.Solids) == 1, 'Disconnected gate/vent/skin network'
stock = sh('ToolStockA').fuse(sh('ToolStockB'))
fill_volume = flow.common(stock).Volume

fixed = {
    'trial_dummy': dummy,
    'continuous_skin': skin,
    'source_installed_body': sh('InstalledMetalBodyReference'),
    'source_installed_cap': sh('InstalledCapReference'),
}
for index, (x, y) in enumerate(report['dowel_centers_XY_mm']):
    fixed['alignment_dowel' + str(index)] = Part.makeCylinder(2, 10, A.Vector(x, y, -5))
release = []
for name, sign, other in (('MoldHalfA', -1, 'MoldHalfB'), ('MoldHalfB', 1, 'MoldHalfA')):
    tool = sh(name)
    for distance in (0, .1, .25, .5, 1, 2, 4, 8, 16, 28, 40):
        moved = tool.copy()
        moved.translate(A.Vector(0, 0, sign * distance))
        hits = {part: intersection(moved, solid) for part, solid in {**fixed, 'other_tool_half': sh(other)}.items()}
        assert max(hits.values()) < EPS, (name, distance, hits)
        release.append({'tool': name, 'Z_translation_mm': sign * distance, 'intersections_mm3': hits})

pin_geometry = []
for index, (x, y) in enumerate(report['dowel_centers_XY_mm']):
    pin = Part.makeCylinder(2, 10, A.Vector(x, y, -5))
    assert intersection(pin, sh('MoldHalfA')) < EPS
    assert intersection(pin, sh('MoldHalfB')) < EPS
    pin_geometry.append({'index': index, 'diametrical_clearance_mm': .2, 'total_axial_end_clearance_mm': 1})
bolt_geometry = []
for index, (x, y) in enumerate(report['M4_bolt_centers_XY_mm']):
    bolt = Part.makeCylinder(2, 56, A.Vector(x, y, -28))
    assert intersection(bolt, sh('MoldHalfA')) < EPS
    assert intersection(bolt, sh('MoldHalfB')) < EPS
    bolt_geometry.append({'index': index, 'diametrical_shank_clearance_mm': .5})

report['verified_parts'] = checks
report['geometry_checks'] = {
    'minimum_flange_envelope_to_rigid_insert_mm': minimum,
    'continuous_skin_valid_single_solid': True,
    'connected_skin_gate_vent_network': True,
    'nominal_connected_fill_volume_ml': fill_volume / 1000,
    'release_translation_samples': release,
    'dowel_geometry': pin_geometry, 'bolt_geometry': bolt_geometry,
    'limits': 'Rigid nominal geometry and finite translations only; bolts removed, tools slide along straight dowels during opening. No continuous swept proof, fit, clamping, flow, flash, cure, shrink, adhesion or physical validation.',
}
report['verifier_sha256'] = sha(Path(__file__))
(OUT / 'review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'valid_parts': len(checks), 'tool_release_poses': len(release),
                  'minimum_end_skin_mm': minimum, 'nominal_fill_ml': fill_volume / 1000,
                  'source_unchanged': True}), flush=True)
