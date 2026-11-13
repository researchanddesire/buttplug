"""Reopen and inspect the saved native dock, independently of its builder.

Run in FreeCAD GUI. This checks nominal geometry and editing, not received
parts, a printing process, optical performance or functional electronics.
"""
from pathlib import Path
from itertools import combinations, product
import hashlib
import json
import math
import sys
import time

import FreeCAD as App
import FreeCADGui as Gui
import Part

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from evt1_brep_checks import solid_parts, exact_common
OUT = ROOT / 'hardware/cad/evt1-assembly'
native = OUT / 'DockAssembly.FCStd'
started=time.monotonic()
def progress(stage):
    (OUT/'verification-progress.json').write_text(json.dumps({
        'stage':stage,'elapsed_seconds':time.monotonic()-started,
        'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest()},indent=2)+'\n')
progress('reopening saved native')
for document in list(App.listDocuments().values()):
    if document.FileName == str(native):
        App.closeDocument(document.Name)
doc = App.openDocument(str(native))
doc.recompute()
assert doc.DockAssembly.TypeId == 'Assembly::AssemblyObject'
assert doc.RearHinge.JointType == 'Revolute'
import UtilsAssembly
for reference, expected in ((doc.RearHinge.Reference1, doc.BaseAssembly),
                            (doc.RearHinge.Reference2, doc.LidAssembly)):
    assert UtilsAssembly.isRefValid(reference, 2)
    assert UtilsAssembly.getMovingPart(reference) == expected
    assert UtilsAssembly.getObject(reference) is not None
assert doc.USBBoardAssembly.LinkedObject.Document != doc
assert doc.PinBoardAssembly.LinkedObject.Document != doc
assert doc.DeviceMetalBody.LinkedObject.Document != doc
for name,solid_count in (('UVBase',41),('UVLid',41),('LidUI',32),('MainPCB',None)):
    object_name='USBBoardAssembly'if name=='MainPCB'else'UIBoardAssembly' if name=='LidUI' else name+'BoardAssembly'
    link=doc.getObject(object_name)
    assert link is not None and link.LinkedObject.Document!=doc,name
    imported=json.loads((OUT/'pcb'/(name+'-stepup-import.json')).read_text())
    assert hashlib.sha256((ROOT/imported['board']).read_bytes()).hexdigest()==imported['board_sha256']
    assert hashlib.sha256((ROOT/imported['native']).read_bytes()).hexdigest()==imported['native_sha256']
    assert len(link.Shape.Solids)==imported['solid_count']
    if solid_count is not None:assert imported['solid_count']==solid_count
    for model in imported['selected_models'].values():
        assert hashlib.sha256((ROOT/model['path']).read_bytes()).hexdigest()==model['sha256']
    assert not imported['missing_component_models']
    if name=='MainPCB':
        assert len(imported['selected_models'])==138 and len(imported['unmodeled_copper_only_references'])==12
        binding=imported['model_coverage_binding']
        assert hashlib.sha256((ROOT/binding['file']).read_bytes()).hexdigest()==binding['sha256']

def exact_bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return [getattr(b, k) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]

body_checks = []
for body in doc.Objects:
    if body.TypeId != 'PartDesign::Body':
        continue
    assert body.Shape.isValid() and len(body.Shape.Solids) == 1, body.Name
    body_checks.append({'name': body.Name, 'tip_type': body.Tip.TypeId,
                        'exact_bounds_mm': exact_bounds(body.Shape)})

def component_shapes(module, placement):
    rows = []
    for obj in module.Group:
        if not hasattr(obj, 'Shape') or obj.Shape.isNull():
            continue
        shape = obj.Shape.copy()
        shape.Placement = placement.multiply(shape.Placement)
        assert shape.isValid(), obj.Name
        rows.append((obj.Name, shape))
    return rows

thread_mates={}
thread_checks=[]
for i,(x,y) in enumerate(((-52,60),(52,60),(-52,115),(52,115))):
    thread_mates[frozenset(('ChamberScrew'+str(i),'LowerShellInstance'))]=Part.makeCylinder(1.0001,4.2502,App.Vector(x,y,6.7499))
for i,x in enumerate((-43,-15)):
    thread_mates[frozenset(('ContactFootScrew'+str(i),'ContactCarrierInstance'))]=Part.makeCylinder(1.5001,6.7502,App.Vector(x,19,5.4999))
for i,(x,y) in enumerate(((-50,80),(50,80),(-25,144),(25,144))):
    thread_mates[frozenset(('UpperChamberScrew'+str(i),'UpperShellInstance'))]=Part.makeCylinder(1.0001,4.2502,App.Vector(x,y,57.4999))
for i,(x,y) in enumerate(((-45,89),(45,89),(-45,132),(45,132))):
    thread_mates[frozenset(('LowerUVScrew'+str(i),'LowerShellInstance'))]=Part.makeCylinder(1.0001,5.0002,App.Vector(x,y,7.1999))
    thread_mates[frozenset(('UpperUVScrew'+str(i),'UpperShellInstance'))]=Part.makeCylinder(1.0001,5.0002,App.Vector(x,y,56.2999))
thread_mates[frozenset(('HingeRetainingScrew','CustomHingePinInstance'))]=Part.makeCylinder(1.0001,3.7002,App.Vector(32.6999,164.4,40.15),App.Vector(1,0,0))
for i,(x,y) in enumerate(((-30,65),(30,65),(-32,115),(32,105))):
    thread_mates[frozenset(('UIBoardScrew'+str(i),'UpperShellInstance'))]=Part.makeCylinder(1.0001,4.0002,App.Vector(x,y,61.4999))
for i,(x,y) in enumerate(((-8,5.5),(8,5.5),(-8,23.5),(8,23.5),(-44,64),(44,55.7))):
    thread_mates[frozenset(('MainBoardScrew'+str(i),'LowerShellInstance'))]=Part.makeCylinder(1.0001,3.0002,App.Vector(x,y,2.3999))
for i,x in enumerate((-41.5,-13.5)):
    thread_mates[frozenset(('ContactRetainerScrew'+str(i),'ContactCarrierInstance'))]=Part.makeCylinder(1.0001,4.1002,App.Vector(x,15.8999,33),App.Vector(0,1,0))
for i,(x,y) in enumerate(((-34.5,69),(34.5,69),(-13,105),(13,105))):
    thread_mates[frozenset(('BezelScrew'+str(i),'ScallopedBezelInstance'))]=Part.makeCylinder(1.0001,2.3002,App.Vector(x,y,67.6999))
for side,sign in (('Left',-1),('Right',1)):
    for i,y in enumerate((26.75,33.25)):
        thread_mates[frozenset((side+'LidCutoffMountScrew'+str(i),'LowerChamberInstance'))]=Part.makeCylinder(1.0001,4.2002,App.Vector(sign*53.3999,y,31),App.Vector(sign,0,0))
    thread_mates[frozenset((side+'LidCutoffAdjuster','UpperChamberInstance'))]=Part.makeCylinder(1.0001,6.4002,App.Vector(sign*50.5,37.55,43.0999))
    thread_mates[frozenset((side+'LidCutoffAdjuster',side+'LidCutoffJamnut'))]=Part.makeCylinder(1.0001,1.6002,App.Vector(sign*50.5,37.55,41.4999))
for side,z,depth,target in (('Lower',34.8,2.1,'LowerShellInstance'),('Upper',42,2.4,'UpperShellInstance')):
    thread_mates[frozenset(('FrontClosure'+side+'ContentsInstance',target))]=Part.makeCylinder(1.0001,depth+.0002,App.Vector(0,.4001,z),App.Vector(0,-1,0))

def overlaps(rows, other=None):
    findings = []
    count = 0
    bounds={name:shape.optimalBoundingBox(False,False) for name,shape in rows+(other or [])}
    # Large imported PCB compounds include hundreds of independent package
    # solids. Reject separated solid boxes before asking the same Boolean
    # kernel for their exact intersections; retain whole-shape operations for
    # small assemblies where decomposition is slower.
    decomposed={}
    pairs=combinations(rows,2) if other is None else product(rows,other)
    for (name1, shape1), (name2, shape2) in pairs:
        count += 1
        b1 = bounds[name1]
        b2 = bounds[name2]
        if not b1.intersect(b2):
            continue
        if max(len(shape1.Solids),len(shape2.Solids))>64:
            if name1 not in decomposed:decomposed[name1]=solid_parts(shape1)
            if name2 not in decomposed:decomposed[name2]=solid_parts(shape2)
            common=exact_common(decomposed[name1],decomposed[name2])
        else:
            common=shape1.common(shape2)
        if common.Volume > 1e-4:
            allowance=thread_mates.get(frozenset((name1,name2)))
            if allowance is not None:
                outside=common.cut(allowance).Volume
                thread_checks.append({'first':name1,'second':name2,'common_volume_mm3':common.Volume,'outside_thread_cylinder_mm3':outside})
                if outside < 1e-4:
                    continue
            findings.append({'first': name1, 'second': name2,
                             'common_volume_mm3': common.Volume})
    return count, findings

parameters = doc.Parameters
poses = []
pivot = App.Vector(0, 164.4, 40.15)
base_shapes = component_shapes(doc.BaseModule, doc.BaseAssembly.LinkPlacement)
progress('static component intersections')
base_pairs, base_findings = overlaps(base_shapes)
lid_pairs, lid_findings = overlaps(component_shapes(doc.LidModule, App.Placement()))
closed_components = None
for angle in (0,.25,.5,1,2,3,5,10,30,60,90,110):
    progress('opening pose '+str(angle)+' degrees')
    doc.Motion.OpeningAngle=angle
    doc.recompute()
    placement = doc.LidAssembly.LinkPlacement
    pivot_error = (placement.multVec(pivot)-pivot).Length
    rotation = placement.Rotation.multVec(App.Vector(0,1,0))
    expected = App.Vector(0,math.cos(math.radians(angle)),-math.sin(math.radians(angle)))
    direction_error = (rotation-expected).Length
    tip_error_bound = 165*direction_error
    assert pivot_error < 1e-6 and direction_error < 1e-9, (angle, pivot_error, rotation)
    upper = component_shapes(doc.LidModule, placement)
    pairs, findings = overlaps(base_shapes,upper)
    poses.append({'angle_deg':angle, 'pairs':pairs,
                  'pivot_error_mm':pivot_error, 'direction_error':direction_error,
                  'case_tip_numeric_error_bound_mm':tip_error_bound,
                  'intersections':findings})
    if angle == 0:
        closed_components = {name: exact_bounds(shape) for name,shape in base_shapes+upper}
    (OUT/'fit-progress.json').write_text(json.dumps({'poses':poses,'base_findings':base_findings,'lid_findings':lid_findings},indent=2)+'\n')

# Exercise an actual sketch dimension driver and restore it; this catches
# accidental conversion to inert meshes or broken native expressions.
progress('editing and restoring native dimensions')
parameters.set('B1','131 mm')
doc.recompute()
assert abs(doc.BaseBulge.getDatum('Width').Value-131) < 1e-6
assert doc.LowerShell.Shape.isValid() and doc.UpperShell.Shape.isValid()
parameters.set('B1','130 mm')
doc.Motion.OpeningAngle=0
doc.recompute()
assert abs(doc.BaseBulge.getDatum('Width').Value-130) < 1e-6
assert doc.LowerShell.Shape.isValid() and doc.UpperShell.Shape.isValid()

# The socket trial changes the actual linked board, screw, shim and button
# tip geometry. Recheck both ends in the complete closed enclosure.
import build_evt1_dock_lcd_socket as socket
ui_trial=[]
for stack in (.5,1.5,1.0):
    progress('UI equal-shim stack '+str(stack)+' mm')
    doc.LCDSocketTrialShimsParameters.Stack=stack
    doc.recompute()
    top=float(doc.LCDSocketTrialShimsParameters.PCBTopZ)
    assert abs(doc.UIBoardAssembly.LinkPlacement.Base.z-top)<1e-8
    assert abs(float(doc.DockButtonParameters.BoardZ)-top)<1e-8
    shim_check=socket.validate_shims(doc.LCDSocketTrialShims)
    for i,(x,y)in enumerate(((-30,65),(30,65),(-32,115),(32,105))):
        assert abs(doc.getObject('UIBoardScrew'+str(i)).LinkPlacement.Base.z-(top-1))<1e-8
        thread_mates[frozenset(('UIBoardScrew'+str(i),'UpperShellInstance'))]=Part.makeCylinder(
            1.0001,top+5-61.5+.0002,App.Vector(x,y,61.4999))
    rows=component_shapes(doc.LidModule,App.Placement())
    pairs,findings=overlaps(rows)
    changed=[row for row in rows if row[0]in ('UIBoardAssembly','LCDSocketTrialShimsInstance')
             or row[0].startswith('UIBoardScrew')
             or(row[0].startswith('DockButton')and'CapInstance'in row[0])]
    cross_pairs,cross_findings=overlaps(base_shapes,changed)
    ui_trial.append({'equal_stack_mm':stack,'PCB_F_Z_mm':top,
                     'lid_pairs':pairs,'closed_base_pairs':cross_pairs,
                     'shim_checks':shim_check,'intersections':findings+cross_findings})

import build_evt1_dock_display as display
import build_evt1_dock_pogo as pogo
component_checks = {'display': display.validate_installed(doc.DockLCD),
                    'pogo': pogo.validate(doc.ContactPogoSource)}
bad_states = [{'name':o.Name,'state':o.State} for o in doc.Objects
              if any(s in ('Invalid','Error') for s in o.State)]
assert not bad_states, bad_states
intersections = [dict(group='base',**f) for f in base_findings]+[dict(group='lid',**f) for f in lid_findings]
intersections += [dict(angle_deg=p['angle_deg'], **f) for p in poses for f in p['intersections']]
intersections += [dict(UI_equal_stack_mm=p['equal_stack_mm'],**f)for p in ui_trial for f in p['intersections']]
report = {'scope':'Saved native readback, editable dimensions and nominal assembled BRep intersections only',
          'FreeCAD_version': App.Version(),
          'native_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
          'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'intersection_helper_sha256':hashlib.sha256((ROOT/'tools/evt1_brep_checks.py').read_bytes()).hexdigest(),
          'saved_reopen':True, 'dimension_edit_restore':True,
          'component_checks': component_checks, 'bodies':body_checks,
          'base_static_pairs':base_pairs, 'lid_static_pairs':lid_pairs,
          'closed_component_bounds_mm':closed_components,
          'poses':poses, 'intersections':intersections,
          'UI_equal_shim_trials':ui_trial,
          'intentional_thread_mates':thread_checks,
          'nominal_geometry_pass':not intersections, 'physical_validation':False,
          'full_product_order_ready':False}
(OUT/'native-check.json').write_text(json.dumps(report,indent=2)+'\n')
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
print('Native dock readback:', len(body_checks), 'bodies;', len(intersections), 'intersection findings')
progress('saved readback complete')
