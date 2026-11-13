"""Independent saved-native EVT1 assembly checks, using FreeCAD Python.

Finite nominal positions and simplified component/mate envelopes do not prove
physical fit, tolerance capability, wiring, materials or a molding process.
"""
from pathlib import Path
import hashlib
import itertools
import json
import math
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import Mesh
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'review.json').read_text())
assert sha(OUT/'EVT1Product.FCStd')==r['native_sha256']
assert sha(ROOT/'tools/build_evt1_product.py')==r['builder_sha256']
if r.get('parts_selection_sha256'):
    assert sha(ROOT/'hardware/pcb/evt1/parts-selection.json')==r['parts_selection_sha256']
if r.get('pack_spec_sha256'):
    assert sha(ROOT/'hardware/pcb/evt1/pack-spec.json')==r['pack_spec_sha256']
assert sha(ROOT/'hardware/cad/manufacturing-layout/ManufacturingLayout.FCStd')==r['source_manufacturing_sha256']
assert sha(ROOT/'hardware/cad/manufacturing-layout/charging-dock/ChargingDock.FCStd')==r['source_dock_sha256']
for source in r['boards'].values():assert sha(ROOT/source['source'])==source['sha256']
D=A.openDocument(str(OUT/'EVT1Product.FCStd'))
def sh(name):return D.getObject(name).Shape
def volume(shape):
    prop=GProp_GProps();brepgprop.VolumePropertiesGK(Part.__toPythonOCC__(shape),prop,1e-9,True,True,False,False,False);return prop.Mass()
def hit(a,b):
    aa=a.BoundBox;bb=b.BoundBox
    if any(min(getattr(aa,c+'Max'),getattr(bb,c+'Max'))<=max(getattr(aa,c+'Min'),getattr(bb,c+'Min'))+1e-7 for c in 'XYZ'):return 0
    return a.common(b).Volume
def compound(names):return Part.makeCompound([sh(n) for n in names])
def shifted(shape,offset):
    s=shape.copy();s.translate(A.Vector(*offset));return s
def clear(label,shape,names):
    collisions={n:hit(shape,sh(n)) for n in names}
    bad={n:v for n,v in collisions.items() if v>1e-4}
    assert not bad,(label,bad)

checks={}
for name,files in r['exports'].items():
    shape=sh(name);assert shape.isValid() and len(shape.Solids)==1,name
    for kind,digest in files.items():
        path=OUT/(name+{'view_STL_sha256':'-view.stl','print_STL_sha256':'.stl','STEP_sha256':'.step'}[kind])
        assert sha(path)==digest,(name,kind,'stale export')
        if kind=='STEP_sha256':
            back=Part.Shape();back.read(str(path));assert back.isValid() and len(back.Solids)==1,name
            delta=volume(back)-volume(shape);assert abs(delta)<.03,(name,delta)
            diff=volume(shape.cut(back))+volume(back.cut(shape));assert diff<.03,(name,diff)
            checks[name]={'STEP_volume_delta_mm3':delta,'STEP_symmetric_difference_mm3':diff}
        else:
            mesh=Mesh.Mesh(str(path));assert mesh.isSolid(),(name,kind)
            if kind=='print_STL_sha256':
                assert abs(mesh.BoundBox.ZMin)<1e-4,(name,'not on bed')
                assert abs(abs(mesh.Volume)-volume(shape))<max(.5,volume(shape)*.001)
print('Native, STEP and mesh readback pass',flush=True)

hard=[o.Name for group in ('ProductParts','Electronics','Contacts') for o in D.getObject(group).Group]+['RearNutReference','PackSizeReference','MotorReference','TipThermistor']
if r.get('motor_interface'):hard.append(r['motor_interface']['lead_exit_allowance_role'])
if r.get('battery_interface'):hard+=r['battery_interface']['thermistor_roles']
if r.get('battery_interface',{}).get('power_connector_role'):hard.append(r['battery_interface']['power_connector_role'])
for a,b in itertools.combinations(hard,2):clear((a,b),sh(a),[b])
for name,item in r['mating_allowances'].items():clear(name,sh(name),[n for n in hard if n!=item['domain'].title()+'_'+item['ref']])
# Screw major envelopes intentionally intersect their pilot walls. No other
# screw/board/component interference is allowed. Head is outside the PCB face.
for names in r['sensor_screw_refs'].values():
    shaft,head=names
    clear(head,sh(head),hard)
    clear(shaft,sh(shaft),[n for n in hard if n!='FlangeTray'])
for n in ('BodyInsulatingSleeve','BodyFoamL','BodyFoamR'):
    clear(n,sh(n),hard)
for net in ('GND','USB_DM','USB_DP','DOCK_5V'):
    clear('contact face seal '+net,sh('ContactSeal_'+net),hard)
if r.get('battery_interface'):
    clear('pack growth allowance',sh(r['battery_interface']['growth_role']),[n for n in hard if n!='PackSizeReference'])

motions={}
def module(domain):
    return [r['boards'][domain]['role']]+[n for n,v in r['components'].items() if v['domain']==domain]+[n for n,v in r['mating_allowances'].items() if v['domain']==domain]
# The rear half and pack are absent during board loading. Screws are absent
# during sensor seating. Electrical tails are not represented by these boxes.
for domain,travel,obstacles in (
        ('flange',12,['FlangeTray','RearNutReference','MetalBody']),
        ('sensor',12,['FlangeTray','RearNutReference','MetalBody']+module('flange'))):
    shape=compound(module(domain));count=0
    for i in range(int(travel*2)+1):clear((domain,'load',i/2),shifted(shape,(0,-i/2,0)),obstacles);count+=1
    motions[domain+'_board_loading']={'poses':count,'axis':'Y','start_offset_mm':-travel,'end_offset_mm':0,'scope':'Open flange; pack and rear half absent'}
sensor_screws=[n for names in r['sensor_screw_refs'].values() for n in names]
pack_module=compound(['PackSizeReference']+(r['battery_interface']['thermistor_roles'] if r.get('battery_interface') else []))
for i in range(29):clear(('pack load',i/2),shifted(pack_module,(0,-i/2,0)),['FlangeTray','RearNutReference','MetalBody']+module('flange')+module('sensor')+sensor_screws)
motions['pack_loading']={'poses':29,'axis':'Y','start_offset_mm':-14,'end_offset_mm':0,'scope':'Requested pack maximum and two NTC envelopes; rear half absent, flexible leads/support process need integration'}
tools=[]
for i,x in enumerate((29.5,38.5)):
    reservation=Part.makeCylinder(1.6,15,A.Vector(x,-27.65,3.5),A.Vector(0,1,0))
    clear(('sensor screw axial access',i),reservation,['FlangeTray','RearNutReference','MetalBody']+module('flange')+module('sensor'))
    tools.append({'center_XZ_mm':[x,3.5],'OD_mm':3.2,'axial_length_mm':15,'scope':'Access reservation; selected bit/shank and torque process require a physical trial before pack loading'})
cap_module=compound(['MotorThermistorCap','MotorReference','TipThermistor','TipPottingSpace','BodyInsulatingSleeve','BodyFoamL','BodyFoamR']+([r['motor_interface']['lead_exit_allowance_role']] if r.get('motor_interface') else [])+module('body'))
count=0
for y in (0,.25,.5,1,2,4,8,16,32):
    for angle in range(0,360,30):
        shape=cap_module.copy();shape.rotate(A.Vector(),A.Vector(0,1,0),angle);shape.translate(A.Vector(0,y,0))
        clear(('cap module load',y,angle),shape,['MetalBody']);count+=1
motions['cap_module_loading']={'poses':count,'translation_Y_mm':[0,.25,.5,1,2,4,8,16,32],'rotation_step_deg':30,'scope':'Nominal module envelopes in straight bore; thread teeth, flexible tails, connector bends and foam compression not qualified'}

clearances={}
for a,b in [('Flange_R39','FlangeTray'),('Sensor_C83','PackSizeReference'),('SensorPCB','PackSizeReference')]:
    distance=sh(a).distToShape(sh(b))[0];assert distance>.05,(a,b,distance);clearances[a+'/'+b]=distance
axis={'frame':'Product right-handed XYZ; +X is molded back/tailbone arrow; +Y is toward tip',
      'sensor_PCB_X_axis_in_product':[1,0,0],'sensor_PCB_Y_axis_in_product':[0,0,-1],
      'sensor_PCB_F_normal_in_product':[0,-1,0],
      'scope':'Mechanical registration only; package accel/mag axes and factory calibration must be derived from LSM303AGR drawing and measured on built assembly'}
r['geometry_checks']={'verifier_sha256':sha(Path(__file__)),'exports':checks,'hard_pair_checks':len(hard)*(len(hard)-1)//2,
                      'hard_intersections':0,'mating_intersections':0,'sensor_screws_clear_except_intended_pilot_thread':True,
                      'softgoods_clear':True,'motions':motions,'sensor_tool_reservations':tools,
                      'nominal_clearances_mm':clearances,'mechanical_sensor_axes':axis,'physical_validation':False}
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'nominal_pair_checks':r['geometry_checks']['hard_pair_checks'],'motions':{n:v['poses'] for n,v in motions.items()},'clearances_mm':clearances,'physical_validation':False}),flush=True)
