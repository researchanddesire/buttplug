"""Independent saved-native wire, closed mesh, bend and assembly checks.

Native curve derivatives and BRep solids are inspected; source route points
and a successful sweep are not accepted as proof of clearance or bend radius.
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
PRODUCT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration';OUT=PRODUCT/'loom'
PCB=ROOT/'hardware/pcb/evt1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'review.json').read_text());p=json.loads((PRODUCT/'review.json').read_text())
assert sha(OUT/'EVT1Loom.FCStd')==r['native_sha256']
assert sha(PRODUCT/'EVT1Product.FCStd')==r['source_product_native_sha256']==p['native_sha256']
assert sha(ROOT/'tools/build_evt1_loom_cad.py')==r['builder_sha256']
assert sha(ROOT/'tools/evt1_loom_paths.py')==r['path_builder_sha256']
for domain,digest in r['source_mcad_sha256'].items():assert sha(PCB/domain/'mcad.json')==digest
D=A.openDocument(str(OUT/'EVT1Loom.FCStd'))
def sh(n):return D.getObject(n).Shape
def vol(shape):
    if shape.isNull() or not shape.Solids:return 0
    q=GProp_GProps();brepgprop.VolumePropertiesGK(Part.__toPythonOCC__(shape),q,1e-9,True,True,False,False,False);return q.Mass()
def overlap(a,b):
    x,y=a.BoundBox,b.BoundBox
    if any(min(getattr(x,c+'Max'),getattr(y,c+'Max'))<=max(getattr(x,c+'Min'),getattr(y,c+'Min'))+1e-7 for c in 'XYZ'):return 0
    return vol(a.common(b))
withdrawn=r['wire_STEP_exports'];assert withdrawn['status']=='withdrawn'
assert sha(OUT/withdrawn['study'])==withdrawn['study_sha256']
assert not list(OUT.glob('IB*.step')),'Withdrawn wire STEP exports must stay in the archive'
findings=[];checks={}
body=json.loads((PCB/'body/mcad.json').read_text());flange=json.loads((PCB/'flange/mcad.json').read_text())
header=next(v for v in flange['components'] if v['ref']=='J7')
assert abs(header['angle_deg']+90)<1e-6,'Current route requires the neck-facing J7 placement'
for item in r['wires']:
    name=item['name'];solid=sh(item['solid_role']);path=sh(item['centerline_role'])
    assert solid.isValid() and len(solid.Solids)==1,name
    solid.check(True)
    source=next(v for v in body['pads'] if v['ref']==item['start']['ref'] and v['number']==item['start']['pin'])
    target=next(v for v in flange['pads'] if v['ref']==item['end']['ref'] and v['number']==item['end']['pin'])
    assert source['net']==target['net']==item['net']
    expected_start=A.Vector(source['xy_mm'][0],p['bounds']['Body_J6_Mate'][1],p['bounds']['BodyPCB'][5]+1.4)
    expected_end=A.Vector(p['bounds']['Flange_J7_Mate'][3],p['bounds']['FlangePCB'][4]+1.4,target['xy_mm'][1]+17.5125)
    remaining=list(path.Edges);ordered=[];here=expected_start
    while remaining:
        candidate=next(((i,False) for i,e in enumerate(remaining) if (e.valueAt(e.FirstParameter)-here).Length<1e-5),None)
        if candidate is None:candidate=next(((i,True) for i,e in enumerate(remaining) if (e.valueAt(e.LastParameter)-here).Length<1e-5),None)
        assert candidate is not None,(name,'Open/disordered native centreline',here)
        i,reverse=candidate;e=remaining.pop(i);ordered.append((e,reverse));here=e.valueAt(e.FirstParameter if reverse else e.LastParameter)
    assert (here-expected_end).Length<1e-5,(name,'Wrong wire endpoint')
    maximum_k=0;sample_count=0;last=None;max_join_angle=0
    for e,reverse in ordered:
        start=e.LastParameter if reverse else e.FirstParameter;end=e.FirstParameter if reverse else e.LastParameter
        a=e.tangentAt(start)*(-1 if reverse else 1);b=e.tangentAt(end)*(-1 if reverse else 1)
        if last is not None:max_join_angle=max(max_join_angle,math.degrees(last.getAngle(a)))
        last=b
        knots=e.Curve.getKnots() if hasattr(e.Curve,'getKnots') else [e.FirstParameter,e.LastParameter]
        cuts=sorted(set([e.FirstParameter,e.LastParameter]+[v for v in knots if e.FirstParameter<=v<=e.LastParameter]))
        for lo,hi in zip(cuts,cuts[1:]):
            for i in range(13):
                t=lo+(hi-lo)*i/12;k=abs(e.curvatureAt(t));maximum_k=max(maximum_k,k);sample_count+=1
    radius=1/maximum_k if maximum_k else None
    assert math.degrees(last.getAngle(A.Vector(-1,0,0)))<.1,(name,'Wire must enter the neck-facing housing along-X')
    if radius is not None and radius<item['minimum_centerline_radius_mm']-.001:findings.append({'wire':name,'issue':'Minimum bend radius','sampled_minimum_mm':radius,'required_mm':item['minimum_centerline_radius_mm']})
    if max_join_angle>.1:findings.append({'wire':name,'issue':'Tangent discontinuity','degrees':max_join_angle})
    expected_volume=math.pi*(item['OD_mm']/2)**2*path.Length;actual_volume=vol(solid)
    assert abs(actual_volume-expected_volume)<max(.02,expected_volume*.001),(name,'Sweep volume',actual_volume,expected_volume)
    for kind,digest in r['exports'][name].items():
        if kind=='centerline_role':continue
        assert kind=='view_STL_sha256','Only closed view meshes are exported'
        file=OUT/(name+'-view.stl');assert sha(file)==digest
        mesh=Mesh.Mesh(str(file));assert mesh.isSolid()
        assert abs(abs(mesh.Volume)-actual_volume)<max(.03,actual_volume*.005),(name,'Mesh volume mismatch')
    checks[name]={'free_insulated_path_mm':path.Length,'sampled_minimum_bend_radius_mm':radius,'curvature_samples':sample_count,
        'maximum_native_join_angle_degrees':max_join_angle,'sweep_volume_mm3':actual_volume,'theoretical_tube_volume_mm3':expected_volume,
        'view_mesh_closed_and_volume_checked':True}
    print(name,'radius',radius,'length',path.Length,flush=True)
# Exclude only explicit hand-solder volumes, which are not physical packages.
# Every real board/part/mated housing and soft good remains an obstacle.
hand_lands={'Body_J81','Sensor_J82','Flange_J1'}
obstacles=[n for n in r['source_context_roles'] if n not in hand_lands]
static_pairs=0
for item in r['wires']:
    wire=sh(item['solid_role'])
    for n in obstacles:
        amount=overlap(wire,sh('Source_'+n));static_pairs+=1
        if amount>1e-5:findings.append({'wire':item['name'],'issue':'Part collision','part':n,'intersection_mm3':amount})
wire_pairs=0;minimum_separation=None
for a,b in itertools.combinations(r['wires'],2):
    distance=sh(a['solid_role']).distToShape(sh(b['solid_role']))[0];wire_pairs+=1
    minimum_separation=distance if minimum_separation is None else min(minimum_separation,distance)
    if distance<.005:findings.append({'wires':[a['name'],b['name']],'issue':'Wire contact/intersection','surface_distance_mm':distance,'intersection_mm3':overlap(sh(a['solid_role']),sh(b['solid_role']))})
result={'pass':not findings,'wire_count':len(r['wires']),'checks':checks,'part_pair_checks':static_pairs,'wire_pair_checks':wire_pairs,
    'minimum_wire_surface_distance_mm':minimum_separation,'findings':findings,'verified_product_review_sha256':sha(PRODUCT/'review.json'),
    'scope':'Saved nominal centreline/native BOP, closed mesh/volume, sampled bend radius and static clearance only. Wire STEP conversion is withdrawn with its failed comparison archived. No continuous bend bound, produced crimp/free length, flexible assembly, strain relief, current/thermal or physical fit proof.',
    'verifier_sha256':sha(Path(__file__))}
r['geometry_checks']=result;(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'pass':result['pass'],'wires':result['wire_count'],'findings':findings,'minimum_wire_surface_distance_mm':minimum_separation}),flush=True)
assert result['pass'],'Wire-form findings remain; no release/packaging permitted'
