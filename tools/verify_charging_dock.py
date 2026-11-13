"""Saved-native, exchange, interface and finite motion checks; FreeCAD Python.

Usage: verify_charging_dock.py OUTPUT [manufacturing-folder]
No physical fit, magnetic holding, sealing, signal-integrity or powered result.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve()
SOURCE = Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'hardware/cad/manufacturing-layout'
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r = json.loads((OUT/'review.json').read_text())
assert sha(OUT/'ChargingDock.FCStd')==r['native_sha256']
assert sha(SOURCE/'ManufacturingLayout.FCStd')==r['source_native_sha256']
assert sha(SOURCE/'overmold-trial/OvermoldTrial.FCStd')==r['source_trial_native_sha256']
assert sha(ROOT/'tools/build_charging_dock.py')==r['builder_sha256']
assert sha(SOURCE/'charging-dock/contact-seal-spec.json')==r['contact_seal_spec_sha256']
for source in r.get('pcb_sources',{}).values():
    assert sha(ROOT/source['board_file'])==source['board_sha256'],'PCB source changed after MCAD integration'
D = A.openDocument(str(OUT/'ChargingDock.FCStd'))


def volume(shape):
    props=GProp_GProps()
    brepgprop.VolumePropertiesGK(Part.__toPythonOCC__(shape),props,1e-9,True,True,False,False,False)
    return props.Mass()


def sh(role):
    return D.getObject(r['native_roles'].get(role,role)).Shape


def hit(a,b):
    shape=a.common(b)
    return shape.Volume if not shape.isNull() else 0


def moved(shape,delta):
    copy=shape.copy()
    copy.translate(A.Vector(*delta))
    return copy


def plunger(net,compression):
    item=next(c for c in r['contacts'] if c['net']==net)
    x,_,z=item['dock_xyz_mm']
    p=r['pogo']
    return Part.makeCylinder(p['tip_OD_mm']/2,p['free_height_mm']-compression-p['barrel_height_envelope_mm'],
                             A.Vector(x,p['PCB_front_Y_mm']+p['barrel_height_envelope_mm'],z),A.Vector(0,1,0))


def assert_clear(label,shape,obstacles):
    hits={name:hit(shape,other) for name,other in obstacles.items()}
    assert max(hits.values(),default=0)<1e-4,(label,{n:v for n,v in hits.items() if v>=1e-4})
    return hits


checks={}
for name,values in r['exports'].items():
    label=values['label']
    shape=sh(name)
    assert shape.isValid() and len(shape.Solids)==1,label
    step=OUT/(label+'.step')
    assert sha(step)==values['STEP_sha256']
    back=Part.Shape()
    back.read(str(step))
    assert back.isValid() and len(back.Solids)==1,label
    mass=volume(shape)
    delta=volume(back)-mass
    assert abs(delta)<.03,(label,'adaptive volume delta',delta)
    difference=hit(shape.cut(back),shape.cut(back))+hit(back.cut(shape),back.cut(shape))
    assert abs(difference)<.03,(label,'STEP difference',difference)
    view=OUT/(label+'-view.stl')
    assert sha(view)==values['view_STL_sha256']
    assert Mesh.Mesh(str(view)).isSolid(),label
    bounds=shape.optimalBoundingBox(False,False)
    checks[label]={'valid_single_solid':True,'adaptive_volume_mm3':mass,'STEP_adaptive_volume_delta_mm3':delta,
                   'STEP_symmetric_difference_mm3':difference,
                   'optimal_bounds_xyz_mm':[bounds.XMin,bounds.YMin,bounds.ZMin,bounds.XMax,bounds.YMax,bounds.ZMax]}
    if 'print_STL_sha256' in values:
        path=OUT/(label+'.stl')
        assert sha(path)==values['print_STL_sha256']
        mesh=Mesh.Mesh(str(path))
        assert mesh.isSolid()
        assert abs(mesh.BoundBox.ZMin)<1e-4
        assert abs(abs(mesh.Volume)-mass)<max(1,mass*.001),label
        checks[label]['print_mesh_closed']=True
        checks[label]['print_size_xyz_mm']=[mesh.BoundBox.XLength,mesh.BoundBox.YLength,mesh.BoundBox.ZLength]
    if 'section_view_STL_sha256' in values:
        path=OUT/(label+'-section-view.stl')
        assert sha(path)==values['section_view_STL_sha256']
        profile=Mesh.Mesh(str(path))
        assert profile.CountFacets>0,label
        assert abs(profile.BoundBox.ZMin-values['section_plane_Z_mm'])<1e-4,label
        assert abs(profile.BoundBox.ZMax-values['section_plane_Z_mm'])<1e-4,label
        assert abs(profile.Area-values['section_area_mm2'])<max(.03,values['section_area_mm2']*.001),label
        checks[label]['section_view']='Planar open profile mesh; intentionally not a print solid'
for name,expected in r['render_meshes'].items():
    assert sha(OUT/name)==expected

print('Saved native/STEP/meshes checked',flush=True)
nets=[c['net'] for c in r['contacts']]
dock_roles=['DockBase','DockLid','DockNest','PogoCarrier','PogoRetainer','DockDeviceGauge','PinPCBBlank',
            'DockMagnet0','DockMagnet1','MagnetBackSpacer0','MagnetBackSpacer1']
dock_roles += [prefix+net for prefix in ('PogoBarrel_','PogoPlunger_') for net in nets]
dock_roles += [r['usb_board']['native_role']]+r['usb_board']['component_roles']
static=[]
for a,b in itertools.combinations(dock_roles,2):
    amount=hit(sh(a),sh(b))
    assert amount<1e-4,(a,b,amount)
    static.append({'a':a,'b':b,'intersection_mm3':amount})
keepout_checks={}
for name in ('OptionalDisplayKeepout',):
    keepout_checks[name]=assert_clear(name,sh(name),{n:sh(n) for n in dock_roles})
for name in r['pin_wire_exit']['allowance_roles']:
    keepout_checks[name]=assert_clear(name,sh(name),{n:sh(n) for n in ('DockBase','DockNest','PogoCarrier','PogoRetainer')})

# Source-coordinate product integration; old two targets/magnets are explicitly
# not included. Existing board/pack are size references, not a released circuit.
interface=['FourContactRearHalf','FourContactSkin','OriginalTrayReference','LegacyFlangeElectronics',
           'UnselectedBatteryReference','BodyReference','CapReference','BuriedSteelKeeper0','BuriedSteelKeeper1']
interface += [prefix+net for prefix in ('Target_','TargetNut_') for net in nets]
interface += r['contact_seal_roles']
interface_pairs=[]
for a,b in itertools.combinations(interface,2):
    amount=hit(sh(a),sh(b))
    assert amount<1e-4,(a,b,amount)
    interface_pairs.append({'a':a,'b':b,'intersection_mm3':amount})
# Smooth M2 root models must not hide an actual major-diameter clearance issue.
thread_clearance=[]
for item in r['contacts']:
    x,_,z=item['device_xyz_mm']
    major=Part.makeCylinder(1,3.2,A.Vector(x,-24.5,z),A.Vector(0,1,0))
    assert_clear(item['net']+' M2 major',major,{'rear_half':sh('FourContactRearHalf'),'PCB':sh('LegacyFlangeElectronics')})
    thread_clearance.append({'net':item['net'],'major_to_cover_mm':major.distToShape(sh('FourContactRearHalf'))[0],
                             'contact_and_nut_to_PCB_mm':sh('Target_'+item['net']).fuse(sh('TargetNut_'+item['net'])).distToShape(sh('LegacyFlangeElectronics'))[0]})
print('Dock and device interface static fits checked',flush=True)

# Independently inspect the saved miniature face glands and installed seal
# space. This checks dimensions/volume, never elastomer stress or leak tightness.
seal_checks=[]
spec=r['contact_seal'];g=spec['gland'];ring=spec['seal_candidate']
free_volume=2*math.pi**2*(ring['ID_mm']/2+ring['cross_section_mm']/2)*(ring['cross_section_mm']/2)**2
gland_volume=math.pi*((g['OD_mm']/2)**2-(g['ID_mm']/2)**2)*g['depth_mm']
for item in r['contacts']:
    net=item['net'];x,_,z=item['device_xyz_mm'];seal=sh('TargetSeal_'+net)
    assert abs(volume(seal)-free_volume)<1e-6,(net,'Seal-space volume')
    cy=g['bearing_face_product_Y_mm']-g['depth_mm']
    gland=Part.makeCylinder(g['OD_mm']/2,g['depth_mm'],A.Vector(x,cy,z),A.Vector(0,1,0)).cut(
        Part.makeCylinder(g['ID_mm']/2,g['depth_mm']+.02,A.Vector(x,cy-.01,z),A.Vector(0,1,0)))
    assert volume(seal.cut(gland))<1e-6,(net,'Seal outside gland')
    assert volume(sh('Target_'+net).common(gland))<1e-6,(net,'Metal blocks gland')
    assert volume(sh('FourContactSkin').common(gland))<1e-6,(net,'External casting cavity fills seal gland')
    assert abs(seal.BoundBox.YMax-g['bearing_face_product_Y_mm'])<1e-6
    seal_checks.append({'net':net,'nominal_gland_volume_mm3':gland_volume,'free_ring_volume_mm3':free_volume,
        'nominal_fill_fraction':free_volume/gland_volume,'nominal_raw_CS_squeeze_fraction':1-g['depth_mm']/ring['cross_section_mm'],
        'scope':'Saved geometry/volume only. Does not predict deformed ring stress, sealing, compatibility or preload.'})
cases=[]
for ID,CS,gland_ID,depth,flatness in itertools.product(ring['incoming_trial_ID_range_mm'],ring['incoming_trial_CS_range_mm'],
        (g['ID_mm']-g['diameter_tolerance_mm'],g['ID_mm']+g['diameter_tolerance_mm']),
        (g['depth_mm']-g['depth_tolerance_mm'],g['depth_mm']+g['depth_tolerance_mm']),
        (-g['counterface_local_flatness_max_mm'],g['counterface_local_flatness_max_mm'])):
    # Constant-volume circular-section stretch estimate, before axial squeeze.
    lo,hi=0,CS
    for _ in range(60):
        mid=(lo+hi)/2
        if (gland_ID+mid)*mid**2<(ID+CS)*CS**2:lo=mid
        else:hi=mid
    fitted_CS=(lo+hi)/2
    cases.append(1-(depth+flatness)/fitted_CS)
fill_max=(math.pi**2/4*(max(ring['incoming_trial_ID_range_mm'])+max(ring['incoming_trial_CS_range_mm']))*max(ring['incoming_trial_CS_range_mm'])**2)/(
    math.pi*(((g['OD_mm']-g['diameter_tolerance_mm'])/2)**2-((g['ID_mm']+g['diameter_tolerance_mm'])/2)**2)*(g['depth_mm']-g['depth_tolerance_mm']-g['counterface_local_flatness_max_mm']))
assert min(cases)>0 and fill_max<.85,'Trial budgets produce an uncompressed or overfilled gland'
seal_tolerance={'estimated_squeeze_fraction_range':[min(cases),max(cases)],'conservative_fill_fraction_max':fill_max,
    'cases':len(cases),'scope':'Conditional arithmetic using proposed incoming/machining budgets and constant-volume stretch estimate. Not manufacturer agreement, FEA, force or leak qualification.'}

# Removed rear half only: install all four nuts with an axial driver. Its
# 6mm outer diameter and4.2AF opening are a receiving/tool reservation, not a
# qualified purchased socket. Adjacent nuts use their ALL-ANGLE envelopes.
driver_checks=[]
for item in r['contacts']:
    x,_,z=item['device_xyz_mm']
    radius=4.2/math.sqrt(3)
    pts=[A.Vector(x+radius*math.cos(math.radians(i*60)),-22.95,z+radius*math.sin(math.radians(i*60)))for i in range(6)]
    opening=Part.Face(Part.makePolygon(pts+pts[:1])).extrude(A.Vector(0,13,0))
    driver=Part.makeCylinder(3,12,A.Vector(x,-22.9,z),A.Vector(0,1,0)).cut(opening)
    fixed={'removed_rear_half':sh('FourContactRearHalf'),'matching_nut':sh('TargetNut_'+item['net'])}
    for other in r['contacts']:
        if other['net']!=item['net']:
            ox,_,oz=other['device_xyz_mm']
            fixed['adjacent_nut_sweep_'+other['net']]=Part.makeCylinder(4/math.sqrt(3),1.6,A.Vector(ox,-22.9,oz),A.Vector(0,1,0))
    for dy in (0,.5,1,2,4,8):
        posed=moved(driver,(0,dy,0))
        driver_checks.append({'net':item['net'],'Y_translation_mm':dy,
                              'intersections_mm3':assert_clear('target driver '+item['net']+' '+str(dy),posed,fixed)})

lid_motion=[]
obstacles={n:sh(n) for n in ['DockBase','DockNest','PogoCarrier','PogoRetainer','DockDeviceGauge','PinPCBBlank']}
for angle in [0,-1,-2,-3,-4]+list(range(-5,-111,-5)):
    lid=sh('DockLid').copy()
    lid.rotate(A.Vector(*r['hinge_axis_xyz_mm']),A.Vector(1,0,0),angle)
    lid_motion.append({'angle_deg':angle,'intersections_mm3':assert_clear('lid '+str(angle),lid,obstacles)})

# Nominal unloaded descent at +3mm, then axial approach. During final0.6mm,
# retract plungers analytically instead of pretending rigid free tips can overlap.
load_obstacles={n:sh(n) for n in ['DockBase','DockNest','PogoCarrier','PogoRetainer','PinPCBBlank','DockMagnet0','DockMagnet1']}
for net in nets:
    load_obstacles['barrel_'+net]=sh('PogoBarrel_'+net)
    load_obstacles['free_tip_'+net]=plunger(net,0)
loading=[]
for height in (0,.25,.5,1,2,4,8,16,32,64,100):
    part=moved(sh('DockDeviceGauge'),(0,3,height))
    loading.append({'Y_offset_mm':3,'Z_offset_mm':height,'intersections_mm3':assert_clear('lower '+str(height),part,load_obstacles)})
slide=[]
for dy in (3,2.5,2,1.5,1,.6,.4,.2,0):
    part=moved(sh('DockDeviceGauge'),(0,dy,0))
    fixed={n:sh(n) for n in ['DockBase','DockNest','PogoCarrier','PogoRetainer','PinPCBBlank']}
    for net in nets:
        fixed['barrel_'+net]=sh('PogoBarrel_'+net)
        fixed['tip_'+net]=plunger(net,max(0,.6-dy))
    slide.append({'Y_offset_mm':dy,'compression_mm':max(0,.6-dy),'intersections_mm3':assert_clear('slide '+str(dy),part,fixed)})
print('Lid and guided load/slide checked',flush=True)

# Four flat pad faces must touch the annular stop lands and the pin tips at
# the seated position, while the silicone remains behind the rigid datum.
stop_checks=[]
for item in r['contacts']:
    x,y,z=item['dock_xyz_mm']
    post=moved(sh('Target_'+item['net']),(0,40,32))
    land=Part.makeCylinder(1.5,.5,A.Vector(x,12.7,z),A.Vector(0,1,0)).cut(
        Part.makeCylinder(.9,.6,A.Vector(x,12.65,z),A.Vector(0,1,0)))
    assert post.distToShape(land)[0]<1e-5
    assert post.distToShape(sh('PogoPlunger_'+item['net']))[0]<1e-5
    assert hit(land,sh('SeatedSiliconeSkin'))<1e-4
    stop_checks.append({'net':item['net'],'target_to_land_mm':post.distToShape(land)[0],
                        'silicone_to_land_mm':sh('SeatedSiliconeSkin').distToShape(land)[0]})

# Explicit unqualified budgets: pin length +/-0.1524, printed carrier/PCB
# stack +/-0.15, target flat/coplanarity +/-0.05. Use the larger notes tolerance
# where the drawing and generic notes differ; not a guarantee for FDM.
stroke_error=.1524+.15+.05
compression=[.6-stroke_error,.6+stroke_error]
conservative_travel=r['pogo']['max_travel_mm']-.1524
assert compression[0]>0 and compression[1]<conservative_travel
flat_radius=(4-2*.15)/2
tip_radius=(r['pogo']['tip_OD_mm']+r['pogo']['diameter_tolerance_mm'])/2
half_span=(r['contacts'][-1]['device_xyz_mm'][0]-r['contacts'][0]['device_xyz_mm'][0])/2
radial_error=math.hypot(.15,.15)+half_span*math.sin(math.radians(.5))
assert flat_radius-1.5-radial_error>0

# Opposite roll puts the whole contact bank on the other flange edge. Check
# actual face centers rather than claiming arbitrary wrong placement is safe.
reverse=[]
for angle in (180,):
    minimum=1e9
    for item in r['contacts']:
        post=sh('Target_'+item['net']).copy()
        post.rotate(A.Vector(),A.Vector(0,1,0),angle)
        post.translate(A.Vector(0,40,32))
        for net in nets:
            minimum=min(minimum,post.distToShape(sh('PogoPlunger_'+net))[0])
    assert minimum>10
    reverse.append({'roll_degrees':angle,'minimum_target_to_pin_mm':minimum,
                    'scope':'Nominal180degree roll only, not arbitrary reversed/tilted/lateral insertion or a power interlock'})

# Contact face mask FIRST pulls out along-Y. Main split tools open only after
# it has cleared the proud targets. Slot is open to the split, not a blind well.
mask_obstacles={n:sh(n) for n in ['ContactMoldHalfA','ContactMoldHalfB','FourContactSkin','FourContactRearHalf']}
mask_obstacles.update({n:sh(n) for n in ['Target_'+net for net in nets]})
mask_motion=[]
for distance in (0,.1,.3,.5,1,2,4,8,12,16):
    part=moved(sh('ContactFaceMask'),(0,-distance,0))
    mask_motion.append({'Y_translation_mm':-distance,'intersections_mm3':assert_clear('mask '+str(distance),part,mask_obstacles)})
tool_motion=[]
tool_fixed={n:sh(n) for n in ['FourContactSkin','FourContactRearHalf','OriginalTrayReference','BodyReference','CapReference']}
tool_fixed.update({n:sh(n) for n in ['Target_'+net for net in nets]})
for tool,sign,other in [('ContactMoldHalfA',-1,'ContactMoldHalfB'),('ContactMoldHalfB',1,'ContactMoldHalfA')]:
    for distance in (0,.1,.3,.5,1,2,4,8,12,20,30,40):
        part=moved(sh(tool),(0,0,sign*distance))
        tool_motion.append({'tool':tool,'Z_translation_mm':sign*distance,
                            'intersections_mm3':assert_clear(tool+' '+str(distance),part,{**tool_fixed,'other_tool':sh(other)})})
print('Mask withdrawal and split-tool release checked',flush=True)

assembled=sh('DockBase').fuse(sh('DockLid'))
bounds=assembled.optimalBoundingBox(False,False)
r['verified_parts']=checks
r['geometry_checks']={
    'dock_static_pair_checks':len(static),'dock_static_positive_intersections':[],
    'device_interface_pair_checks':len(interface_pairs),'device_interface_positive_intersections':[],
    'thread_major_and_PCB_clearance':thread_clearance,
    'contact_face_seal_nominal_checks':seal_checks,
    'contact_face_seal_conditional_tolerance_arithmetic':seal_tolerance,
    'removed_rear_half_target_nut_driver_samples':driver_checks,
    'closed_case_overall_xyz_mm':[bounds.XLength,bounds.YLength,bounds.ZLength],
    'board_keepout_static_checks':keepout_checks,
    'lid_rotation_samples':lid_motion,'device_lowering_samples':loading,'device_slide_samples':slide,
    'metal_face_hard_stops':stop_checks,'mask_withdrawal_samples':mask_motion,'split_tool_release_samples':tool_motion,
    'reverse_roll_samples':reverse,
    'unqualified_tolerance_arithmetic':{'compression_range_mm':compression,'reduced_travel_mm':conservative_travel,
         'assumed_XZ_location_error_each_mm':.15,'assumed_roll_about_contact_normal_deg':.5,
         'worst_radial_position_mm':radial_error,'remaining_full_stop_land_on_flat_face_mm':flat_radius-1.5-radial_error,
         'remaining_full_pin_tip_on_flat_face_mm':flat_radius-tip_radius-radial_error,
         'limits':'Proposed inspection budgets only, not supplier agreement, printing capability or accepted physical fit.'},
    'limits':'Nominal rigid finite samples. No continuous swept proof, flexible routing, force/strength, actual tolerances, seal, magnetic retention, USB, firmware, UV or physical result.'}
r['verifier_sha256']=sha(Path(__file__))
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'valid_parts':len(checks),'print_parts':len(r['print_parts']),
                  'lid_poses':len(lid_motion),'lowering_poses':len(loading),'slide_poses':len(slide),
                  'mask_poses':len(mask_motion),'tool_poses':len(tool_motion),
                  'overall_case_mm':r['geometry_checks']['closed_case_overall_xyz_mm']}),flush=True)
