"""Sample actual saved-native liner and device assembly paths in FreeCAD GUI.

This is a nominal rigid-body check. It does not prove continuous clearance,
received tolerances, flexible loom installation, UV backing or physical fit.
"""
from pathlib import Path
import hashlib
import json
import sys
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from evt1_brep_checks import solid_parts, exact_common
OUT=ROOT/'hardware/cad/evt1-assembly'
native=OUT/'DockAssembly.FCStd'
doc=next((d for d in App.listDocuments().values() if d.FileName==str(native)),None)
if doc is None:
    doc=App.openDocument(str(native))
doc.Motion.OpeningAngle=110
doc.recompute()


def clashes(shape, obstacles):
    bounds=shape.optimalBoundingBox(False,False)
    hits=[]
    moving_parts=None
    for name,other in obstacles:
        if not bounds.intersect(other.optimalBoundingBox(False,False)):
            continue
        if max(len(shape.Solids),len(other.Solids))>64:
            if moving_parts is None:moving_parts=solid_parts(shape)
            common=exact_common(moving_parts,solid_parts(other))
        else:
            common=shape.common(other)
        if common.Volume>1e-4:
            hits.append({'component':name,'volume_mm3':common.Volume})
    return hits


def objects(module, excluded=(), placement=None):
    rows=[]
    for o in module.Group:
        if o.Name in excluded or not hasattr(o,'Shape') or o.Shape.isNull():
            continue
        shape=o.Shape.copy()
        if placement is not None:
            shape.Placement=placement.multiply(shape.Placement)
        rows.append((o.Name,shape))
    return rows


# Main PCB precedes the liner; the complete contact module is installed through
# its two floor ports afterward. UV modules and plug/baffles follow the liner.
contact_parts=('ContactCarrierInstance','ContactRetainerInstance','PinBoardAssembly',
               'PogoContact1','PogoContact2','PogoContact3','PogoContact4',
               'DockTargetMagnet0','DockTargetMagnet1','DockTargetMagnetSpring0','DockTargetMagnetSpring1',
               'ContactRetainerScrew0','ContactRetainerScrew1','CarrierScrew0','CarrierScrew1')
after_liner=('BaseUVThermalModuleInstance','FrontClosureLowerContentsInstance','DeviceSeatingModuleInstance',
             'LidSwitchAInstance','LidSwitchBInstance',
             'LeftLidCutoffMountScrew0','LeftLidCutoffMountScrew1',
             'RightLidCutoffMountScrew0','RightLidCutoffMountScrew1')
excluded=('LowerChamberInstance','DeviceAssembly','UVBaseBoardAssembly',
          'LowerUVScrew0','LowerUVScrew1','LowerUVScrew2','LowerUVScrew3',
          'ChamberScrew0','ChamberScrew1','ChamberScrew2','ChamberScrew3')+contact_parts+after_liner
fixed=objects(doc.BaseModule,excluded)
fixed+=objects(doc.LidModule,placement=doc.LidAssembly.LinkPlacement)
liner=[]
for lift in [i*.5 for i in range(0,61)]+[35,40,45,50,60]:
    shape=doc.LowerChamberInstance.Shape.copy()
    shape.translate(App.Vector(0,0,lift))
    liner.append({'lift_mm':lift,'intersections':clashes(shape,fixed)})

fixed=objects(doc.BaseModule,('DeviceAssembly',))
fixed+=objects(doc.LidModule,placement=doc.LidAssembly.LinkPlacement)
device=[]
# Load away from the pins at +3mmY, lower, then slide toward -Y to mate.
for lift in [i*2 for i in range(0,36)]:
    shape=doc.DeviceAssembly.Shape.copy()
    shape.translate(App.Vector(0,3,lift))
    device.append({'phase':'lower','lift_mm':lift,'offset_y_mm':3,
                   'intersections':clashes(shape,fixed)})
for offset in [i*.25 for i in range(0,13)]:
    shape=doc.DeviceAssembly.Shape.copy()
    shape.translate(App.Vector(0,offset,0))
    device.append({'phase':'mate','lift_mm':0,'offset_y_mm':offset,
                   'intersections':clashes(shape,fixed)})

# Complete carrier/PCB/pins/retainer/magnet/spring subassembly is preassembled
# outside the shell, then lowered after the liner and fastened from underneath.
moving=[o.Shape for o in doc.BaseModule.Group if o.Name in contact_parts
        and not o.Name.startswith('CarrierScrew')]
module=Part.makeCompound(moving)
contact_late=tuple(n for n in after_liner if n!='FrontClosureLowerContentsInstance')
obstacles=objects(doc.BaseModule,contact_parts+contact_late+('DeviceAssembly','UVBaseBoardAssembly',
                  'LowerUVScrew0','LowerUVScrew1','LowerUVScrew2','LowerUVScrew3'))
obstacles+=objects(doc.LidModule,placement=doc.LidAssembly.LinkPlacement)
contact_loading=[]
for lift in [0,.25,.5,1,2,3,4,5,6,8,10,15,20,30,40,60]:
    shape=module.copy();shape.translate(App.Vector(0,0,lift))
    contact_loading.append({'lift_mm':lift,'intersections':clashes(shape,obstacles)})

# Install the upper liner from its cavity side after the electronics/thermal
# modules. Adjusters and jamnuts travel with it; the catch plug follows it.
upper_moving_names=('UpperChamberInstance','LeftLidCutoffAdjuster','RightLidCutoffAdjuster',
                    'LeftLidCutoffJamnut','RightLidCutoffJamnut')
upper_moving=Part.makeCompound([o.Shape for o in doc.LidModule.Group if o.Name in upper_moving_names])
upper_excluded=upper_moving_names+tuple('UpperChamberScrew'+str(i)for i in range(4))+('FrontClosureUpperContentsInstance',)
upper_fixed=objects(doc.LidModule,upper_excluded)
upper_fixed+=objects(doc.BaseModule,('DeviceAssembly',),doc.LidAssembly.LinkPlacement.inverse())
upper_loading=[]
for lift in [i*.5 for i in range(0,61)]+[35,40,45,50,60]:
    shape=upper_moving.copy();shape.translate(App.Vector(0,0,-lift))
    upper_loading.append({'withdrawal_mm':lift,'intersections':clashes(shape,upper_fixed)})

drivers=[]
for i,(x,y) in enumerate(((-52,60),(52,60),(-52,115),(52,115))):
    # Axial straight-driver reservation only. Exact selected bit/access and
    # torque are physical trial requirements; screws are not obstacles.
    obstacles=objects(doc.BaseModule,('DeviceAssembly','UVBaseBoardAssembly',
              'LowerUVScrew0','LowerUVScrew1','LowerUVScrew2','LowerUVScrew3',
              'ChamberScrew0','ChamberScrew1','ChamberScrew2','ChamberScrew3')+contact_parts+after_liner)
    obstacles+=objects(doc.LidModule,placement=doc.LidAssembly.LinkPlacement)
    tool=Part.makeCylinder(2.5,100,App.Vector(x,y,13.1))
    drivers.append({'screw':i,'driver_radius_mm':2.5,
                    'intersections':clashes(tool,obstacles)})

doc.Motion.OpeningAngle=0
doc.recompute()
report={'scope':__doc__.strip(),'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),
        'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'intersection_helper_sha256':hashlib.sha256((ROOT/'tools/evt1_brep_checks.py').read_bytes()).hexdigest(),
        'liner_sequence':'main PCB, liner and its screws, plug/baffles, preassembled contact module, lid cutoffs, UV modules, device',
        'liner_poses':liner,'device_poses':device,'liner_driver_access':drivers,
        'contact_module_loading':contact_loading,
        'upper_liner_loading':upper_loading,
        'pass':not any(p['intersections'] for p in liner+device+drivers+contact_loading+upper_loading),
        'limits':['Sampled nominal poses, not a continuous swept-volume/tolerance result',
                  'Actual linked boards, selected screw profiles, thermal modules and device seats are included',
                  'Flexible looms, actual bits, received hardware and process fit remain unqualified'],
        'physical_validation':False}
(OUT/'loading-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Native loading check:',report['pass'],len(liner),'liner poses,',len(device),'device poses')
