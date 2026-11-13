"""Bounded two-wire repair; preserve every physical source and endpoint."""
from pathlib import Path
import json,hashlib
import curve_utils as c
import pack_paths as original
import pack_paths_repaired as revised
P=Path(__file__).resolve().parent;A=c.A;Part=c.Part;V=c.V
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=P/'archive/static-negative-6d4dfb5d/CompletePackLoomTrial.FCStd'
assert sha(source)=='6d4dfb5d884b956d56dca9ce4a20691ed05cd49ddce985b85bf5822c038d628a'
base=json.loads((P/'archive/static-negative-6d4dfb5d/complete-review.json').read_text())
old=original.interboard()+original.power()+original.ntcs()
new=revised.interboard()+revised.power()+revised.ntcs()
changed=['NTC1_RETURN','NTC2_RETURN']
for a,b in zip(old,new):
    if a['name']not in changed:assert a==b
    else:
        for k in a:
            if k!='sections':assert a[k]==b[k],(a['name'],k)
        assert a['sections'][0]==b['sections'][0] and a['sections'][1]==b['sections'][1]
        assert a['sections'][-1]==b['sections'][-1]
d=A.openDocument(str(source))
def bnd(s):
    b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def overlap(a,b):return all(a[i+3]>b[i]+1e-8 and b[i+3]>a[i]+1e-8 for i in range(3))
def digest(s):return hashlib.sha256(s.exportBrepToString().encode()).hexdigest()
all_shapes={o.Name:(digest(o.Shape),o.Shape.Volume,bnd(o.Shape))for o in d.Objects if hasattr(o,'Shape')and not o.Shape.isNull()}
fixed={o.Name:o.Shape.copy()for o in d.getObject('ImmutableAssemblyContext').Group}
groups={}
for p in new:
    groups[p['name']]=[(c.path(p['sections']),p['OD_mm']/2)]
    if p.get('factory_sections'):groups[p['name']].append((c.path(p['factory_sections']),p['factory_OD_mm']/2))
report=[]
for plan in new:
    name=plan['name']
    if name not in changed:continue
    path=groups[name][0][0];factory=groups[name][1][0]
    checks=c.path_checks(path);assert checks['minimum_sampled_radius_mm']>=plan['minimum_radius_mm']-1e-4
    assert checks['maximum_join_gap_mm']<1e-5 and checks['minimum_join_tangent_dot']>1-1e-6
    oldpath=c.path(next(p for p in old if p['name']==name)['sections'])
    assert (oldpath.Edges[0].valueAt(oldpath.Edges[0].FirstParameter)-path.Edges[0].valueAt(path.Edges[0].FirstParameter)).Length<1e-8
    assert (oldpath.Edges[-1].valueAt(oldpath.Edges[-1].LastParameter)-path.Edges[-1].valueAt(path.Edges[-1].LastParameter)).Length<1e-8
    q=c.trimmed_bare(path,plan['OD_mm'],plan['bare_end_OD_mm'],plan['bare_end_length_mm'])
    q=q.fuse(c.tube(factory,plan['factory_OD_mm']/2)).removeSplitter();assert q.isValid()and len(q.Solids)==1
    qb=bnd(q);hard=[]
    for n,s in fixed.items():
        if not overlap(qb,bnd(s)):continue
        v=q.common(s).Volume
        if v>1e-7:hard.append({'part':n,'common_mm3':v})
    others=[]
    for other,curves in groups.items():
        if other==name:continue
        margins=[a.distToShape(b)[0]-ra-rb for a,ra in groups[name]for b,rb in curves]
        margin=min(margins);assert margin>1e-4,(name,other,margin)
        others.append({'wire':other,'native_centerline_profile_gap_lower_bound_mm':margin})
    assert not hard,(name,hard)
    gaps={n:q.distToShape(d.getObject('Context_'+n).Shape)[0]for n in ('ProposedFlangeTray','PackSizeReference','PackGrowthAllowance','MetalBody')}
    body=d.getObject(name);body.Tip.Shape=q;body.CenterlineJSON=json.dumps(plan)
    body.FreePathLength=path.Length+factory.Length
    d.getObject(name+'Centerline').Shape=Part.makeCompound([factory,path])
    report.append({'wire':name,'checks':checks,'free_extension_path_mm':path.Length,'factory_path_mm':factory.Length,
                   'volume_mm3':q.Volume,'bounds_mm':qb,'hard_intersections':hard,'other_wire_checks':others,'native_surface_gaps_mm':gaps})
    print('REPAIRED_WIRE_CHECKED',name,gaps,flush=True)
d.recompute()
allow=set(changed+[n+'FormedWire'for n in changed]+[n+'Centerline'for n in changed])
unchanged=[]
for name,(h,vol,bounds)in all_shapes.items():
    if name in allow:continue
    assert digest(d.getObject(name).Shape)==h,('Unexpected physical/source change',name)
    unchanged.append(name)
out=P/'CompletePackLoomRepaired.FCStd';d.saveAs(str(out));snap={}
for o in d.Objects:
    if o.TypeId=='PartDesign::Body':
        assert o.Shape.isValid()and len(o.Shape.Solids)==1,o.Name
        snap[o.Name]={'volume_mm3':o.Shape.Volume,'bounds_mm':bnd(o.Shape)}
A.closeDocument(d.Name);cold=A.openDocument(str(out))
assert not[o for o in cold.Objects if o.TypeId=='App::Link']
for n,v in snap.items():
    s=cold.getObject(n).Shape;assert s.isValid()and len(s.Solids)==1
    assert abs(s.Volume-v['volume_mm3'])<1e-6
    assert max(abs(a-b)for a,b in zip(bnd(s),v['bounds_mm']))<1e-6
r={'status':'Two return-wire Tray intersections repaired; digital static candidate, physical gates open',
   'source_negative_native_sha256':sha(source),'source_negative_report_sha256':sha(P/'archive/static-negative-6d4dfb5d/complete-review.json'),
   'native_sha256':sha(out),'repair_script_sha256':sha(Path(__file__)),'path_source_sha256':sha(P/'pack_paths_repaired.py'),
   'original_path_source_sha256':sha(P/'pack_paths.py'),'curve_utilities_sha256':sha(P/'curve_utils.py'),
   'changed_physical_body_names':changed,'unchanged_shape_count':len(unchanged),'unchanged_shape_names':unchanged,
   'endpoint_factory_joint_and_sleeve_changes':False,'checks':report,'cold_valid_single_solid_bodies':len(snap),'cold_body_geometry':snap,
   'cold_external_links':0,'physical_validation':False,'service_motion_validated':False,
   'growth_port_findings_preserved':{'PACK_FACTORY_POWER1_mm3':.07793113276311187,'PACK_FACTORY_POWER2_mm3':.07793113276311187},
   'narrow_passage_gate':'At X11..29, centreY−14.85 in actual pack-front−15.2/Tray−14.5 gap:0.55mm wire leaves0.075mm nominal each side. Received/assembly tolerance, movement and abrasion are not qualified.'}
(P/'return-repair-review.json').write_text(json.dumps(r,indent=2)+'\n')
print('REPAIRED_NATIVE_FROZEN',r['native_sha256'],len(snap),'valid Bodies',flush=True)
