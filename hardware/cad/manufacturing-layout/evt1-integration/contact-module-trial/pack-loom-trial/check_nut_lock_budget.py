"""Unselected, all-angle sharp-hex nut rear-stack clearance budget."""
from pathlib import Path
import json,math,hashlib
import curve_utils as c
import Sketcher
P=Path(__file__).resolve().parent;A=c.A;Part=c.Part;V=c.V
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=P/'LocalTrayReliefLoomTrial.FCStd'
r=json.loads((P/'rib-relief-review.json').read_text());assert sha(source)==r['native_sha256']
d=A.openDocument(str(source));n=A.newDocument('NutLockClearanceBudget')
def bnd(s):
    b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def overlap(a,b):return all(a[i+3]>b[i]+1e-8 and b[i+3]>a[i]+1e-8 for i in range(3))
def budget(name,shift,inner):
    b=n.addObject('PartDesign::Body',name);s=b.newObject('Sketcher::SketchObject',name+'AnnularSection')
    s.Placement=A.Placement(V(0,-14+shift,0),A.Rotation(V(1,0,0),-90))
    for radius in (24/math.sqrt(3),inner):
        i=s.addGeometry(Part.Circle(V(),V(0,0,1),radius),False);s.addConstraint(Sketcher.Constraint('Block',i))
    n.recompute();p=b.newObject('PartDesign::Pad',name+'FourMMNutSweep');p.Profile=s;p.Length=4;n.recompute();s.Visibility=False
    assert p.Shape.isValid()and len(p.Shape.Solids)==1
    b.addProperty('App::PropertyString','Scope');b.Scope='UNSELECTED all-angle angular-sweep clearance budget, not an actual nut/washer. Inner-hole radius is an explicit scenario parameter; saved source pilot is17 mm.'
    b.addProperty('App::PropertyLength','UnselectedRearwardStackAllowance');b.UnselectedRearwardStackAllowance=-shift
    return b
scenarios=[('SavedPilot17_CurrentRear',0,8.5),('SavedPilot17_RearMinusHalfMM',-.5,8.5),('ExtraLumen12_CurrentRear',0,6.),('ExtraLumen12_RearMinusHalfMM',-.5,6.)]
parts={p['wire']:d.getObject(p['wire']).Shape.copy()for p in json.loads((P/'complete-review.json').read_text())['wires']}
for name in ('PackNTC1','PackNTC2','NTC1_SIGNALJointSleeve','NTC1_RETURNJointSleeve','NTC2_SIGNALJointSleeve','NTC2_RETURNJointSleeve'):
    parts[name]=d.getObject(name).Shape.copy()
checks=[]
for name,shift,inner in scenarios:
    b=budget(name,shift,inner);q=b.Shape.copy();hits=[]
    for part,s in parts.items():
        if not overlap(bnd(q),bnd(s)):continue
        common=s.common(q)
        if common.Volume>1e-7:
            segments=[];o=d.getObject(part)
            if hasattr(o,'CenterlineJSON'):
                plan=json.loads(o.CenterlineJSON)
                for i,section in enumerate(plan['sections']):
                    e=c.edge(section);clearance=e.distToShape(q)[0]
                    if clearance<=plan['OD_mm']/2+1e-5:segments.append({'section_index':i,'kind':section['kind'],'native_centerline_distance_mm':clearance})
            hits.append({'part':part,'common_mm3':common.Volume,'common_bounds_mm':bnd(common),'near_or_inside_curve_sections':segments})
            f=n.addObject('PartDesign::Feature',name+'Conflict_'+part);f.Shape=common
            if f.ViewObject:f.ViewObject.ShapeColor=(.9,.15,.08)
    checks.append({'scenario':name,'rearward_shift_mm':shift,'inner_hole_diameter_mm':inner*2,'reservation_bounds_mm':bnd(q),'intersections':hits})
    print('NUT_BUDGET',name,hits,flush=True)
n.recompute();out=P/'NutLockClearanceBudget.FCStd';n.saveAs(str(out))
original=d.getObject('Context_RearNutReference').Shape
source_circle_radii=sorted(set(round(e.Curve.Radius,6)for e in original.Edges if isinstance(e.Curve,Part.Circle)))
assert 8.5 in source_circle_radii,source_circle_radii
result={'status':'Conservative locking-space study; any listed conflict blocks wire promotion for that reservation',
 'source_native_sha256':sha(source),'source_rib_report_sha256':sha(P/'rib-relief-review.json'),'script_sha256':sha(Path(__file__)),
 'budget_native_sha256':sha(out),'fixed_saved_nut_bounds_mm':bnd(original),'fixed_saved_nut_volume_mm3':original.Volume,'saved_nut_circular_edge_radii_mm':source_circle_radii,
 'budget':{'AF_mm':24,'regular_sharp_hex_corner_diameter_mm':48/math.sqrt(3),'all_angle_outer_radius_mm':24/math.sqrt(3),
   'axial_thickness_mm':4,'source_saved_nut_Y_mm':[-14,-10],'rearward_stack_mm':.5,'rearward_stack_breakdown_mm':{'candidate_unselected_washer':.3,'setup_margin':.2},
   'reserved_Y_mm':[-14.5,-10.5],'primary_saved_pilot_diameter_mm':17,'extra_conservative_excluded_lumen_diameter_mm':12,
   'inner_exclusion_reason':'Primary scenarios retain the saved17mm source pilot; final received M18x1 thread limits remain unqualified. Separate Ø12-lumen scenarios deliberately overestimate material between the fixed body bore and the actual female thread; their extra hits must not be conflated with actual thread material.','washer_selected':False,'nut_or_Tray_changed':False,
   'actual_ifm_E10028_drawing_outer27_not_used_as_sharp_hex_corner_bound':True,'primary_reference_URL':'https://www.ifm.com/us/en/product/E10028'},
 'checks':checks,'source_geometry_mutated':False,'physical_validation':False,
 'promotion_gate':'Select the actual nut, lock form, angular registration and received stack, or reroute all reported conductors/heads against the conservative budget. The current0.223..0.226mm saved-nut gaps do not establish lock compatibility.'}
(P/'nut-lock-budget-review.json').write_text(json.dumps(result,indent=2)+'\n')
print('NUT_BUDGET_FROZEN',result['budget_native_sha256'],flush=True)
