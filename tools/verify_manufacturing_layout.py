"""Read-back, finite access/motion and DFM calculations; run with FreeCAD Python."""
from pathlib import Path
import sys,json,hashlib,itertools,math
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A,Part,MeshPart,Mesh
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
def adaptive_volume(shape):
 props=GProp_GProps();error=brepgprop.VolumePropertiesGK(Part.__toPythonOCC__(shape),props,1e-10,True,True,False,False,False);return props.Mass()
folder=Path(sys.argv[1]);r=json.loads((folder/'review.json').read_text());d=A.openDocument(str(folder/'ManufacturingLayout.FCStd'))
assert hashlib.sha256((folder/'ManufacturingLayout.FCStd').read_bytes()).hexdigest()==r['native_sha256']
parts={label:d.getObject(name)for label,name in r['native_object_names'].items()}
body,cap,tray,cover=[parts[n].Shape for n in ['MetalBody','MotorThermistorCap','FlangeTray','RearCover']]
nut=d.getObject('ThinRearNut').Shape
all_parts=dict(parts);all_parts['ThinRearNut']=d.getObject('ThinRearNut')
# Volume/extent/readback guard on the actual saved output.
checks={}
for label,o in all_parts.items():
 back=Part.Shape();back.read(str(folder/(label+'.step')))
 assert o.Shape.isValid() and back.isValid() and len(back.Solids)==1
 assert abs(back.Volume-o.Shape.Volume)<.01,(label,o.Shape.Volume,back.Volume)
 native_mass=adaptive_volume(o.Shape);step_mass=adaptive_volume(back);assert abs(native_mass-step_mass)<.01,(label,native_mass,step_mass)
 checks[label]={'native_adaptive_volume_mm3':native_mass,'STEP_adaptive_volume_delta_mm3':step_mass-native_mass,'optimal_bounds_xyz_mm':[o.Shape.optimalBoundingBox(False,False).XMin,o.Shape.optimalBoundingBox(False,False).YMin,o.Shape.optimalBoundingBox(False,False).ZMin,o.Shape.optimalBoundingBox(False,False).XMax,o.Shape.optimalBoundingBox(False,False).YMax,o.Shape.optimalBoundingBox(False,False).ZMax],'valid_single_solid':len(o.Shape.Solids)==1,'native_default_volume_mm3':o.Shape.Volume,'STEP_volume_delta_mm3':back.Volume-o.Shape.Volume,'STEP_sha256':hashlib.sha256((folder/(label+'.step')).read_bytes()).hexdigest()}
for name in ['FlangeTray','RearCover']:
 m=Mesh.Mesh(str(folder/(name+'.stl')));assert m.isSolid()
 checks[name]['STL_closed']=True;checks[name]['STL_sha256']=hashlib.sha256((folder/(name+'.stl')).read_bytes()).hexdigest()
print('Readbacks checked',flush=True)
module=[cap]+[d.getObject(n).Shape for n in ['BodyElectronicsReference','MotorReferenceFitTBD','TipThermistorHeadReference','TipPottingProcessSpace','OpenEndedInsulatingSleeve','StandardFoamSpacerLeft','StandardFoamSpacerRight']]
motion=[]
for angle in range(0,360,45):
 total=0
 for s in module:
  c=s.copy();c.rotate(A.Vector(),A.Vector(0,1,0),angle);total+=c.common(body).Volume
 assert total<1e-4,(angle,total)
 motion.append({'angle_deg':angle,'intersection_with_body_mm3':total})
print('Rotation checked',flush=True)
# Rigid loading samples only; harness and flexible pad deformation excluded.
loading=[]
for dy in (0,1,2,4,8,16,24,36,48):
 total=0
 for s in module:
  c=s.copy();c.translate(A.Vector(0,dy,0));total+=c.common(body).Volume
 assert total<1e-4,(dy,total)
 loading.append({'Y_translation_mm':dy,'intersection_with_body_mm3':total})
print('Loading checked',flush=True)
# The body front remains turned; rear indexed flats intentionally break symmetry.
front=body.common(Part.makeBox(100,130,100,A.Vector(-50,-7.9,-50)))
c=front.copy();c.rotate(A.Vector(),A.Vector(0,1,0),37)
rot_diff=front.cut(c).Volume+c.cut(front).Volume;assert rot_diff<1e-4,rot_diff
# All-angle nut reservation, loaded from the open rear before boards/pack.
sweep=d.getObject('ThinNutOuterChamfers').Shape.cut(d.getObject('ThinNutFemalePilot').Shape)
nut_loading=[]
for dy in (0,-.5,-1,-2,-4,-8,-12,-20):
 q=sweep.copy();q.translate(A.Vector(0,dy,0))
 hits={name:q.common(shape).Volume for name,shape in [('body_root_envelope',body),('tray',tray)]}
 assert all(v<1e-4 for v in hits.values()),(dy,hits)
 nut_loading.append({'Y_translation_mm':dy,'intersections_mm3':hits})
# Major-diameter thread and collar must enter the keyed socket axially.
major=Part.makeCylinder(9,4.75,A.Vector(0,-14.25,0),A.Vector(0,1,0))
body_loading=[]
for dy in (0,.25,.5,1,2,4,8):
 q=body.copy();q.translate(A.Vector(0,dy,0))
 m=major.copy();m.translate(A.Vector(0,dy,0))
 hits={'body':q.common(tray).Volume,'thread_major_diameter':m.common(tray).Volume}
 assert all(v<1e-4 for v in hits.values()),(dy,hits)
 body_loading.append({'Y_translation_mm':dy,'intersections_mm3':hits})
# Axial two-jaw driver reservation: opposed 24 AF jaws, bridge behind tray rim.
# A normal 24 mm socket is not assumed to fit this narrow cavity.
driver=Part.makeBox(1.1,16.6,6.4,A.Vector(12.05,-27,-3.2)).fuse(Part.makeBox(1.1,16.6,6.4,A.Vector(-13.15,-27,-3.2))).fuse(Part.makeBox(26.3,2,6.4,A.Vector(-13.15,-29,-3.2)))
driver_samples=[]
for angle in range(0,360,15):
 q=driver.copy();q.rotate(A.Vector(),A.Vector(0,1,0),angle)
 n=nut.copy();n.rotate(A.Vector(),A.Vector(0,1,0),angle)
 hits={name:q.common(shape).Volume for name,shape in [('body',body),('tray',tray),('nut_with_clearance',n)]}
 assert all(v<1e-4 for v in hits.values()),(angle,hits)
 driver_samples.append({'angle_deg':angle,'intersections_mm3':hits,'tray_clearance_mm':q.distToShape(tray)[0]})
MeshPart.meshFromShape(Shape=driver,LinearDeflection=.04,AngularDeflection=.15,Relative=False).write(str(folder/'RearNutDriverAccess-view.stl'))
key=d.getObject('BodyCollarFlat1').Shape.common(Part.makeBox(30,1.5,30,A.Vector(-15,-9.5,-15)))
key_samples=[]
for float_mm in (0,.3):
 for angle in (-3,3,90):
  q=key.copy();q.rotate(A.Vector(),A.Vector(0,1,0),angle);q.translate(A.Vector(0,float_mm,0))
  v=q.common(tray).Volume;assert v>1e-4,(float_mm,angle,v)
  key_samples.append({'illustrative_axial_float_mm':float_mm,'angle_deg':angle,'blocking_intersection_mm3':v})
q=body.copy();q.rotate(A.Vector(),A.Vector(0,1,0),180);assert q.common(tray).Volume<1e-4
sidewalls=tray.common(Part.makeBox(100,30,10,A.Vector(-50,-30,13)).fuse(Part.makeBox(100,30,10,A.Vector(-50,-30,-23))))
r['rear_joint_geometry_screen']={
 'nut_all_angle_reservation_loading_samples':nut_loading,'body_indexed_axial_loading_samples':body_loading,
 'axial_driver_rotation_samples':driver_samples,'minimum_driver_to_tray_mm':min(x['tray_clearance_mm']for x in driver_samples),
 'nut_sweep_to_sidewalls_mm':sweep.distToShape(sidewalls)[0],
 'key_rotation_blocking_samples':key_samples,'two_indexed_installation_orientations_degrees':[0,180],
 'nut_to_unselected_pack_mm':nut.distToShape(d.getObject('UnselectedPackReference').Shape)[0],
 'body_to_unselected_pack_mm':body.distToShape(d.getObject('UnselectedPackReference').Shape)[0],
 'limits':'Finite rigid screens and smooth thread envelopes. Driver is an unqualified two-jaw reservation, not a selected commercial tool. Boards/pack/loom/cover absent during tightening. No thread helix, strength, installation force, creep or positive nut lock proof. Illustrative axial float is not an accepted creep limit.'}
# Concrete drill/holder candidate: Guhring6405 2.5mm (4mm shank,
# 20mm flute/62mmOAL/140deg) and Haimer77.160.04 (7mm nose/3deg taper).
# Twenty-five mm tool projection is a proposed setup, not supplier confirmation.
tip=90.5+1.25/math.tan(math.radians(70));nose=tip-25
holder=Part.makeCone(3.5,3.5+25*math.tan(math.radians(3)),25,A.Vector(7.8,nose,0),A.Vector(0,-1,0))
shank=Part.makeCylinder(2,5,A.Vector(7.8,nose,0),A.Vector(0,1,0))
flute=Part.makeCylinder(1.25,90.5-(tip-20),A.Vector(7.8,tip-20,0),A.Vector(0,1,0))
point=Part.makeCone(1.25,0,tip-90.5,A.Vector(7.8,90.5,0),A.Vector(0,1,0))
bit=shank.fuse(flute).fuse(point)
holder_clearance=holder.distToShape(cap)[0]
assert holder_clearance>.25,holder_clearance
assert bit.common(cap).Volume<1e-4
r['sensor_tooling_candidate']={'drill':'Guhring9064050025000:2.5mm diameter,4mm shank,20mm flute,62mmOAL,140deg; catalogtmax16.25mm','holder':'Haimer77.160.04 extra-slim:4mm clamp,7mm nose,3deg taper; simplified taper envelope only',
 'tool_projection_mm':25,'holder_nose_Y_mm':nose,'total_entry_to_drill_tip_mm':tip-54.75,'minimum_holder_to_cap_mm':holder_clearance,'bit_to_cap_intersection_mm3':bit.common(cap).Volume,
 'limits':'Candidate envelope at final depth, not vendor CAD/full toolpath/fixture/live-holder collision approval; grip depth, runout, spot/drill cycle and coolant must be agreed with supplier'}
MeshPart.meshFromShape(Shape=holder,LinearDeflection=.06,AngularDeflection=.2,Relative=False).write(str(folder/'SensorHolderAccess-view.stl'))
MeshPart.meshFromShape(Shape=bit,LinearDeflection=.04,AngularDeflection=.15,Relative=False).write(str(folder/'SensorDrillAccess-view.stl'))
print('Rear nut/driver and sensor tooling reservations checked',flush=True)
# Actual sensor/tool separation and nearest outer dome skin distance, not just
# radial subtraction. Use the construction drill cutter and outer cap blank.
drill=d.getObject('OffsetSensorDrillWithPoint').Shape
blank=d.getObject('ShortTurnedNoseBlank').Shape
outerface=max(blank.Faces,key=lambda f:f.Area)
wall=drill.distToShape(outerface)[0]
assert wall>.8,wall
# Native section caches for the review image only.
clip=Part.makeBox(200,200,50,A.Vector(-100,-50,-50))
for name in ['ThinRearNut','BootCuffBlank','CapFaceSealProcessSpace']:
 o=d.getObject(name)
 MeshPart.meshFromShape(Shape=o.Shape.common(clip),LinearDeflection=.04,AngularDeflection=.15,Relative=False).write(str(folder/(o.Label+'-half-view.stl')))
frontclip=Part.makeBox(50,20,25,A.Vector(-25,60,-25))
MeshPart.meshFromShape(Shape=body.common(frontclip),LinearDeflection=.04,AngularDeflection=.15,Relative=False).write(str(folder/'MetalBody-front-half-view.stl'))
r['design_budget_calculations']={
 'status':'Proposed budgets only, not released limits or supplier agreement',
 'seal':{'cross_section_mm':[.92,1.08],'gland_width_mm':[1.55,1.65],'gland_depth_mm':[.76,.80],'residual_closure_gap_mm':[0,.02],
 'squeeze_fraction_min':(.92-.82)/.92,'squeeze_fraction_max':(1.08-.76)/1.08,
 'maximum_simple_area_fill_fraction':math.pi*(1.08/2)**2/(1.55*.76),'nominal_simple_area_fill_fraction':math.pi*.5**2/(1.6*.78),
 'limits':'Cross-section approximation; does not include gland corner volumes, diameter/volume tolerances, stretch, pressure direction or swell'},
 'rear_key_diametrical_clearance_mm':[20.15-20.02,20.25-19.98],
 'rear_key_clearance_across_flats_mm':[18.55-18.43,18.65-18.37],
 'collar_setback_from_nut_bearing_face_mm':[1.9-1.55,2.1-1.45],
 'rear_thread_nominal_root_wall_mm':(18-1.22687-12)/2,
 'rear_thread_relief_nominal_wall_mm':(16.4-12)/2,
 'tool_bar_candidates':{'large_bore':{'diameter_mm':12,'assumed_overhang_mm':42,'overhang_to_diameter':3.5,'type':'steel, supplier confirmation'},'cone_small_end':{'diameter_mm':8,'assumed_overhang_mm':42,'overhang_to_diameter':5.25,'type':'carbide, minimum cutting diameter/holder/chip clearance not validated'}},
 'mass':{'net_metal_cm3':(checks['MetalBody']['native_adaptive_volume_mm3']+checks['MotorThermistorCap']['native_adaptive_volume_mm3'])/1000,'illustrative_density_g_cm3':8,'illustrative_metal_only_mass_g':(checks['MetalBody']['native_adaptive_volume_mm3']+checks['MotorThermistorCap']['native_adaptive_volume_mm3'])*.008,'limits':'Illustrative density only, no alloy selected; excludes electronics/pack/soft goods'}
}
# A small corner fillet exposed default volume-integration drift on revolved
# spline surfaces. Check its local Boolean partition with adaptive integration.
pre=d.getObject('BodySpigotRootRadius').Shape
gland=d.getObject('FaceGlandBottomRadii').Shape
added=gland.cut(pre);removed=pre.cut(gland)
partition=adaptive_volume(gland)-adaptive_volume(pre)-adaptive_volume(added)+adaptive_volume(removed)
assert abs(partition)<1e-4,partition
r['gland_fillet_partition_check']={'method':'OCCT BRepGProp VolumePropertiesGK, eps1e-10','added_adaptive_mm3':adaptive_volume(added),'removed_mm3':removed.Volume,'partition_residual_mm3':partition,'limits':'Default Volume on spline surfaces drifts; use adaptive masses for weight estimates. Geometry/STEP acceptance still separate from physical production.'}
r['verifier_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();r['verified_parts']=checks;r['rigid_module_rotation_samples']=motion;r['rigid_module_loading_samples']=loading
r['front_body_rotational_invariance_symmetric_difference_mm3']=rot_diff
if len(sys.argv)>2:
 baseline_path=Path(sys.argv[2]);baseline=A.openDocument(str(baseline_path))
 old_body=next(o.Shape for o in baseline.Objects if o.Label=='MetalBody')
 old_cap=next(o.Shape for o in baseline.Objects if o.Label=='MotorThermistorCap')
 clip=Part.makeBox(100,130,100,A.Vector(-50,-7,-50))
 a=body.common(clip);b=old_body.common(clip)
 delta=a.cut(b).Volume+b.cut(a).Volume
 cap_delta=cap.cut(old_cap).Volume+old_cap.cut(cap).Volume
 assert delta<1e-4 and cap_delta<1e-4,(delta,cap_delta)
 r['baseline_geometry_comparison']={'baseline_native_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),'body_above_Y_minus7_symmetric_difference_mm3':delta,'cap_symmetric_difference_mm3':cap_delta,'scope':'Checks preserved neck/body front and cap geometry, not physical acceptance'}
 A.closeDocument(baseline.Name)
r['cap_sensor']['minimum_distance_drill_to_outer_dome_mm']=wall
r['scope']=r['scope'].split(' Eight angular/')[0]+' Eight angular/nine axial cap-module poses plus rear nut/loading/driver/key samples are finite screens, not thread/harness/tool-force or physical assembly approval.'
(folder/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print('VERIFIED',json.dumps({'parts':checks,'drill_minimum_outer_wall_mm':wall,'module_rotation_poses':len(motion),'module_loading_poses':len(loading),'rear_driver_poses':len(driver_samples),'front_axisymmetry_delta':rot_diff}),flush=True)

# Vector section coordinates for a review drawing, derived from these native
# shapes. These are geometry sections, not a fully toleranced machining print.
section_rows={}
print('Drawing sections',flush=True)
for name,shape,axis in [('body',body,'Z'),('cap',cap,'Z'),('rear_body',body,'X'),('rear_tray',tray,'X'),('rear_nut',nut,'X'),('rear_cuff',d.getObject('BootCuffBlank').Shape,'X'),('tool_holder',holder,'Z'),('tool_bit',bit,'Z')]:
    print('Section',name,flush=True)
    normal=A.Vector(0,0,1) if axis=='Z' else A.Vector(1,0,0)
    loops=[]
    for wire in shape.slice(normal,0):
        pts=wire.discretize(Deflection=.02)
        loops.append([[p.x if axis=='Z' else p.z,p.y]for p in pts])
    section_rows[name]=loops
(folder/'section-data.json').write_text(json.dumps({'native_sha256':r['native_sha256'],'sections':section_rows})+'\n')
