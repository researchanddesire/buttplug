"""Independent cold native/terminal/part validation; never writes a native."""
from pathlib import Path
import sys,json,hashlib,math
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
P=Path(__file__).resolve().parent;R=P.parents[5]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bnd(s):
    b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
r=json.loads((P/'rib-relief-review.json').read_text());n=P/'LocalTrayReliefLoomTrial.FCStd';assert sha(n)==r['native_sha256']
d=A.openDocument(str(n))
bodies=[o for o in d.Objects if o.TypeId=='PartDesign::Body'];assert len(bodies)==53
assert not[o for o in d.Objects if o.TypeId=='App::Link']
for b in bodies:
    assert b.Shape.isValid()and len(b.Shape.Solids)==1,b.Name
    expected=r['cold_body_geometry'][b.Name]
    assert abs(b.Shape.Volume-expected['volume_mm3'])<1e-6
    assert max(abs(a-b)for a,b in zip(bnd(b.Shape),expected['bounds_mm']))<1e-6
sk=d.getObject('NTCReturnCrossingProfile');assert sk.FullyConstrained
assert d.getObject('NTCReturnCrossingReliefs').TypeId=='PartDesign::Pocket'
fcontract=R/'hardware/pcb/evt1/single-flange-routing/native-checks.json'
bcontract=R/'hardware/pcb/evt1/body/mcad.json'
fc=json.loads(fcontract.read_text())['native_pad_contracts'];bc=json.loads(bcontract.read_text())
assert next(x for x in bc['components']if x['ref']=='J6')['xy_mm']==[0.,31.]
checks=[]
for i in range(1,11):
    o=d.getObject('IB%02d'%i);p=json.loads(o.CenterlineJSON)
    f=next(x for x in fc if x['ref']=='J7'and x['pad']==str(i))
    b=next(x for x in bc['pads']if x['ref']=='J6'and x['number']==str(i))
    assert o.Net==p['net']==f['net']==b['net']
    first=p['sections'][0]['points'][0];last=p['sections'][-1]['points'][-1]
    assert max(abs(a-b)for a,b in zip(first,[b['xy_mm'][0],31.525,1.51]))<1e-8
    assert max(abs(a-b)for a,b in zip(last,[-2.525,-24.442,f['product_XZ_mm'][1]]))<1e-8
    ce=d.getObject(o.Name+'Centerline').Shape
    assert (ce.Edges[0].valueAt(ce.Edges[0].FirstParameter)-A.Vector(*first)).Length<1e-6
    assert (ce.Edges[-1].valueAt(ce.Edges[-1].LastParameter)-A.Vector(*last)).Length<1e-6
    checks.append({'wire':o.Name,'pin':i,'net':o.Net,'first_mm':first,'last_mm':last,'native_length_mm':ce.Length})
j2=json.loads((P/'body-J2-pad-geometry.json').read_text());pad_checks=[]
mapping={'BODY_POWER1':0,'BODY_POWER2':1,'NTC1_RETURN':2,'NTC2_RETURN':2,'NTC1_SIGNAL':3,'NTC2_SIGNAL':4}
for name,index in mapping.items():
    o=d.getObject(name);plan=json.loads(o.CenterlineJSON);pad=j2[index]
    assert o.Net==pad['net'];end=plan['sections'][-1]['points'][-1]
    x0,y0,x1,y1=pad['native_bounds_mm'];bb=[x0-100,135-y1,x1-100,135-y0]
    rad=plan['bare_end_OD_mm']/2
    assert abs(end[2])<1e-8 and bb[0]-1e-8<=end[0]-rad and end[0]+rad<=bb[2]+1e-8 and bb[1]-1e-8<=end[1]-rad and end[1]+rad<=bb[3]+1e-8,(name,end,bb,rad)
    pad_checks.append({'wire':name,'net':o.Net,'pad_source_index':index,'bare_end_diameter_mm':rad*2,'endpoint_mm':end,'pad_product_XY_bounds_mm':bb})
assert d.getObject('NTC1_RETURN').Net==d.getObject('NTC2_RETURN').Net=='GND'
tray=d.getObject('Context_ProposedFlangeTray').Shape
step=Part.Shape();step.read(str(P/'TrayLocalRibReliefs.step'));assert step.isValid()and len(step.Solids)==1
step_volume_difference=abs(step.Volume-tray.Volume)
step_vertex_residual=max(max(min((v.Point-w.Point).Length for w in step.Vertexes)for v in tray.Vertexes),max(min((v.Point-w.Point).Length for w in tray.Vertexes)for v in step.Vertexes))
assert step_volume_difference<1e-5 and step_volume_difference/tray.Volume<1e-9
assert step_vertex_residual<1e-6 and max(abs(a-b)for a,b in zip(bnd(step),bnd(tray)))<1e-6
native_summary={'path':str(n.relative_to(R)),'sha256':sha(n),'valid_single_solid_bodies':53,'external_links':0,'fully_constrained_relief_profile':True}
A.closeDocument(d.Name)
br=json.loads((P/'nut-lock-budget-review.json').read_text());bn=P/'NutLockClearanceBudget.FCStd';assert sha(bn)==br['budget_native_sha256']
bd=A.openDocument(str(bn));budget_bodies=[o for o in bd.Objects if o.TypeId=='PartDesign::Body'];assert len(budget_bodies)==4
for b in budget_bodies:assert b.Shape.isValid()and len(b.Shape.Solids)==1
assert not[o for o in bd.Objects if o.TypeId=='App::Link']
# Trim loose spline intersection boxes by their known containing budget.
# These are conservative regions, not asserted tight trimmed-face extrema.
regions=[]
for scenario in br['checks']:
    if scenario['scenario']!='SavedPilot17_RearMinusHalfMM':continue
    bb=scenario['reservation_bounds_mm']
    for hit in scenario['intersections']:
        raw=hit['common_bounds_mm'];clipped=[max(raw[k],bb[k])if k<3 else min(raw[k],bb[k])for k in range(6)]
        regions.append({'part':hit['part'],'common_mm3':hit['common_mm3'],'conservative_intersection_region_mm':clipped,'curve_sections':hit['near_or_inside_curve_sections']})
out={'status':'Independent cold native/STEP/terminal checks pass; nut-lock budget conflicts remain',
     'native':native_summary,'checker_sha256':sha(Path(__file__)),'rib_report_sha256':sha(P/'rib-relief-review.json'),
     'terminal_source_sha256':{'flange':sha(fcontract),'body':sha(bcontract),'J2_pads':sha(P/'body-J2-pad-geometry.json')},
     'SH_numeric_contract_checks':checks,'J2_bare_land_checks':pad_checks,'tray_STEP_matches_cold_native':True,'STEP_parity':{'absolute_volume_difference_mm3':step_volume_difference,'relative_volume_difference':step_volume_difference/tray.Volume,'bidirectional_nearest_vertex_residual_mm':step_vertex_residual,'volume_numeric_limit_mm3':1e-5,'vertex_numeric_limit_mm':1e-6},
     'nut_budget_native_sha256':sha(bn),'nut_budget_report_sha256':sha(P/'nut-lock-budget-review.json'),
     'nut_budget_cold_valid_bodies':4,'shifted_saved_pilot_intersection_regions':regions,
     'physical_validation':False,'service_motion_validated':False,'nut_lock_compatible':False}
(P/'independent-cold-readback.json').write_text(json.dumps(out,indent=2)+'\n')
print('COLD_CHECKS_PASS',native_summary['sha256'],53,'Bodies; nut budget remains a promotion gate',flush=True)
