"""Rubber nose face seal in the compact device's existing metal gland.

32 x 1 mm stock O-ring shown as a volume-preserving squeezed ellipse. This is
an installed geometry reference, not an elastomer/contact simulation or a
material selection. The native part is an editable sketch and revolution.
"""
import os, sys, json, math, hashlib, traceback
from pathlib import Path

# All dimensions in mm; device frame Z up, nose +Y, dock/front -Y.
RING_ID = 32.0
RING_SECTION = 1.0
JOINT_FACE_Y = 64.0
GLAND_ID = 31.6
GLAND_OD = 34.8
GLAND_DEPTH = 0.78
RUBBER_COLOUR = (0.065, 0.070, 0.080)

MECH = Path(__file__).resolve().parent
BUILD = MECH.parent / 'build' / 'mech'
sys.path.insert(0, str(MECH))
import FreeCAD as App, Part, Sketcher, ImportGui

BUILD.mkdir(parents=True, exist_ok=True)
log = open(BUILD / 'CapFaceSeal.log', 'w')
try:
    doc = App.newDocument('CapFaceSealPart')
    body = doc.addObject('PartDesign::Body', 'CapFaceSeal')
    body.Label = 'Cap face seal - rubber 32 x 1 (installed)'
    dims = {'StockID': RING_ID, 'StockSection': RING_SECTION,
            'JointFaceY': JOINT_FACE_Y, 'GlandID': GLAND_ID,
            'GlandOD': GLAND_OD, 'GlandDepth': GLAND_DEPTH}
    for key, val in dims.items():
        body.addProperty('App::PropertyLength', key, 'Seal dimensions')
        setattr(body, key, val)
    body.addProperty('App::PropertyString', 'Qualification', 'Seal dimensions')
    body.Qualification = 'Candidate rubber O-ring; material, tolerances, finish, closure and leak testing open.'

    # Constant mean radius and section area preserve the nominal free-ring volume.
    mean_r = (RING_ID + RING_SECTION) / 2
    axial_r = GLAND_DEPTH / 2
    radial_r = (RING_SECTION / 2) ** 2 / axial_r
    center_y = JOINT_FACE_Y - GLAND_DEPTH / 2
    sketch = doc.addObject('Sketcher::SketchObject', 'InstalledSealProfile')
    body.addObject(sketch)
    sketch.Label = 'Installed elliptical section (nominal volume preserved)'
    # Local sketch vertical axis is global Y, the device/turning axis.
    center = App.Vector(mean_r, center_y, 0)
    ellipse = Part.Ellipse(center + App.Vector(radial_r, 0, 0),
                           center + App.Vector(0, axial_r, 0), center)
    sketch.addGeometry(ellipse, False)
    sketch.addConstraint(Sketcher.Constraint('Block', 0))
    doc.recompute()
    rev = body.newObject('PartDesign::Revolution', 'InstalledSeal')
    rev.Profile = sketch
    rev.ReferenceAxis = (sketch, ['V_Axis'])
    rev.Angle = 360
    doc.recompute()
    assert rev.Shape.isValid() and len(rev.Shape.Solids) == 1
    sketch.Visibility = False
    body.ViewObject.ShapeColor = RUBBER_COLOUR
    rev.ViewObject.ShapeColor = RUBBER_COLOUR
    nominal_volume = 2 * math.pi * mean_r * math.pi * (RING_SECTION / 2) ** 2
    assert abs(rev.Shape.Volume - nominal_volume) < 1e-4
    b = rev.Shape.optimalBoundingBox(False, False)
    log.write('ellipse radii %s %s; bounding box %s\n' % (ellipse.MajorRadius, ellipse.MinorRadius, b))
    assert abs(b.YMin - (JOINT_FACE_Y - GLAND_DEPTH)) < 1e-5
    assert abs(b.YMax - JOINT_FACE_Y) < 1e-5
    assert mean_r - radial_r > GLAND_ID / 2
    assert mean_r + radial_r < GLAND_OD / 2

    App.ParamGet('User parameter:BaseApp/Preferences/Mod/Import').SetInt('ImportMode', 0)
    doc.recompute()
    doc.saveAs(str(MECH / 'CapFaceSeal.FCStd'))
    ImportGui.export([body], str(MECH / 'CapFaceSeal.step'))
    # Read back the written STEP, not just the in-memory solid.
    saved = Part.Shape(); saved.read(str(MECH / 'CapFaceSeal.step'))
    assert saved.isValid() and len(saved.Solids) == 1
    assert abs(saved.Volume - nominal_volume) < 1e-4
    report = {
        'candidate_ring_mm': {'ID': RING_ID, 'section': RING_SECTION},
        'gland_mm': {'ID': GLAND_ID, 'OD': GLAND_OD, 'depth': GLAND_DEPTH, 'face_Y': JOINT_FACE_Y},
        'installed_section_mm': {'radial_width': 2 * radial_r, 'axial_height': GLAND_DEPTH},
        'installed_bbox_mm': [round(v, 6) for v in (b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax)],
        'nominal_squeeze_percent': round(100 * (1 - GLAND_DEPTH / RING_SECTION), 2),
        'nominal_volume_mm3': round(nominal_volume, 6),
        'saved_step_volume_mm3': round(saved.Volume, 6),
        'valid_saved_step': True,
        'metal_inputs_sha256': {f: hashlib.sha256((MECH / f).read_bytes()).hexdigest() for f in ('MetalBody.step', 'MotorThermistorCap.step')},
        'scope': 'Volume-preserving installed envelope. Rubber grade, actual deformation/contact, swell, tolerances, assembly torque and sealing are not validated.'
    }
    (MECH / 'cap-seal-fit.json').write_text(json.dumps(report, indent=2) + '\n')
    log.write(json.dumps(report, indent=2) + '\nOK\n')
except Exception:
    log.write(traceback.format_exc())
    log.flush()
    os._exit(1)
finally:
    log.close()
os._exit(0)
