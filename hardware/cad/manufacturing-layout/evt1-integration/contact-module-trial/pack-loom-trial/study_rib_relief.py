"""Two wire routes + two tiny rib notches; all other geometry immutable."""
from pathlib import Path
import json,hashlib,math
import curve_utils as c
import tray_relief_api as relief
import pack_paths as original
import pack_paths_relief as revised
P=Path(__file__).resolve().parent;A=c.A;Part=c.Part;V=c.V
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=P/'archive/static-negative-6d4dfb5d/CompletePackLoomTrial.FCStd'
assert sha(source)=='6d4dfb5d884b956d56dca9ce4a20691ed05cd49ddce985b85bf5822c038d628a'
baseline=json.loads((P/'archive/static-negative-6d4dfb5d/complete-review.json').read_text())
old=original.interboard()+original.power()+original.ntcs();new=revised.interboard()+revised.power()+revised.ntcs()
changed=['NTC1_RETURN','NTC2_RETURN']
for a,b in zip(old,new):
    if a['name']not in changed:assert a==b
    else:
        assert {k:v for k,v in a.items()if k!='sections'}=={k:v for k,v in b.items()if k!='sections'}
        assert a['sections'][:2]==b['sections'][:2] and a['sections'][-1]==b['sections'][-1]
d=A.openDocument(str(source))
def bnd(s):
    b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def overlap(a,b):return all(a[i+3]>b[i]+1e-8 and b[i+3]>a[i]+1e-8 for i in range(3))
def digest(s):return hashlib.sha256(s.exportBrepToString().encode()).hexdigest()
before={o.Name:digest(o.Shape)for o in d.Objects if hasattr(o,'Shape')and not o.Shape.isNull()and o.TypeId!='App::Part'}
ctx=d.getObject('ImmutableAssemblyContext');src=d.getObject('Context_ProposedFlangeTray');tray_before=src.Shape.copy()
d.removeObject(src.Name)
tray=d.addObject('PartDesign::Body','Context_ProposedFlangeTray');ctx.addObject(tray)
f=tray.newObject('PartDesign::Feature','FrozenTrayBeforeRelief');f.Shape=tray_before
feature=relief.apply_tray_wire_reliefs(tray);tray_after=tray.Shape.copy();removed=tray_before.cut(tray_after)
mask=relief.ribs()[0].fuse(relief.ribs()[1])
outside=removed.cut(mask).Volume;assert outside<1e-7,('Cut outside old pack ribs',outside)
assert removed.Volume>0 and max(abs(a-b)for a,b in zip(bnd(tray_before),bnd(tray_after)))<1e-6
protected={
    'root_clamp_pad':Part.makeCylinder(12,2,V(0,-10,0),V(0,1,0)),
    'actual_metal_body':d.getObject('Context_MetalBody').Shape,
    'actual_nut':d.getObject('Context_RearNutReference').Shape}
for z in (-13,13):protected['cover_post_'+str(z)]=Part.makeCone(2+13.3*math.tan(math.radians(.5)),2,13.3,V(12,-9.6,z),V(0,-1,0))
for x in (-16,-10,-4,2):protected['target_reaction_post_'+str(x)]=Part.makeCylinder(2,3.352,V(x,-25.952,10),V(0,1,0))
for x in (29.5,38.5):protected['old_sensor_boss_'+str(x)]=Part.makeCylinder(2,1.25,V(x,-9.55,3.5),V(0,-1,0))
exclusions=[]
for n,s in protected.items():
    common=removed.common(s).Volume;assert common<1e-7,n
    exclusions.append({'feature':n,'common_mm3':common,'native_distance_mm':removed.distToShape(s)[0]})
rib_support=[]
for i,rib in enumerate(relief.ribs()):
    before_rib=rib.common(tray_before);after_rib=rib.common(tray_after)
    def area_at(q):return sum(Part.Face(w).Area for w in q.slice(V(0,1,0),-14.49))
    a,b=area_at(before_rib),area_at(after_rib)
    rib_support.append({'rib':i,'actual_before_volume_mm3':before_rib.Volume,'actual_remaining_volume_mm3':after_rib.Volume,
        'actual_volume_removed_mm3':before_rib.Volume-after_rib.Volume,'section_Y_mm':-14.49,
        'rear_section_before_mm2':a,'rear_section_after_mm2':b,'rear_section_remaining_fraction':b/a,
        'cut_region_remaining_projection_mm':3.8,'nominal_rib_to_requested_pack_front_gap_mm':.7,
        'current_pack_bearing_or_retention_credited':False})
print('RIB_ONLY_REMOVAL',removed.Volume,rib_support,flush=True)
fixed={o.Name:o.Shape.copy()for o in ctx.Group}
groups={p['name']:[(c.path(p['sections']),p['OD_mm']/2)]+([(c.path(p['factory_sections']),p['factory_OD_mm']/2)]if p.get('factory_sections')else[])for p in new}
reports=[]
for plan in new:
    name=plan['name']
    if name not in changed:continue
    path,factory=groups[name][0][0],groups[name][1][0]
    check=c.path_checks(path);assert check['minimum_sampled_radius_mm']>=plan['minimum_radius_mm']-1e-4
    assert check['maximum_join_gap_mm']<1e-5 and check['minimum_join_tangent_dot']>1-1e-6
    oldpath=c.path(next(p for p in old if p['name']==name)['sections'])
    for which in ('first','last'):
        a,b=(oldpath.Edges[0],path.Edges[0])if which=='first'else(oldpath.Edges[-1],path.Edges[-1])
        t1,t2=(a.FirstParameter,b.FirstParameter)if which=='first'else(a.LastParameter,b.LastParameter)
        assert (a.valueAt(t1)-b.valueAt(t2)).Length<1e-8
    q=c.trimmed_bare(path,plan['OD_mm'],plan['bare_end_OD_mm'],plan['bare_end_length_mm'])
    q=q.fuse(c.tube(factory,plan['factory_OD_mm']/2)).removeSplitter();assert q.isValid()and len(q.Solids)==1
    bad=[];qb=bnd(q)
    for n,s in fixed.items():
        if not overlap(qb,bnd(s)):continue
        v=q.common(s).Volume
        if v>1e-7:bad.append({'part':n,'common_mm3':v})
    pairs=[]
    for other,curves in groups.items():
        if other==name:continue
        gap=min(a.distToShape(b)[0]-ra-rb for a,ra in groups[name]for b,rb in curves)
        assert gap>1e-4,(name,other,gap)
        pairs.append({'other':other,'native_profile_gap_lower_bound_mm':gap})
    assert not bad,(name,bad)
    gaps={n:q.distToShape(d.getObject('Context_'+n).Shape)[0]for n in ('ProposedFlangeTray','PackSizeReference','PackGrowthAllowance','MetalBody','RearNutReference')}
    body=d.getObject(name);body.Tip.Shape=q;body.CenterlineJSON=json.dumps(plan);body.FreePathLength=path.Length+factory.Length
    d.getObject(name+'Centerline').Shape=Part.makeCompound([factory,path])
    reports.append({'wire':name,'checks':check,'extension_free_path_mm':path.Length,'factory_path_mm':factory.Length,
       'volume_mm3':q.Volume,'bounds_mm':qb,'fixed_intersections':bad,'wire_pairs':pairs,'native_surface_gaps_mm':gaps})
    print('RETURN_CHECKED',name,gaps,flush=True)
d.recompute()
allow={'Context_ProposedFlangeTray'}|set(changed+[n+'FormedWire'for n in changed]+[n+'Centerline'for n in changed])
unchanged=[]
for n,h in before.items():
    if n in allow:continue
    assert digest(d.getObject(n).Shape)==h,('Unexpected change',n);unchanged.append(n)
out=P/'LocalTrayReliefLoomTrial.FCStd';d.saveAs(str(out));snap={}
for o in d.Objects:
    if o.TypeId=='PartDesign::Body':
        assert o.Shape.isValid()and len(o.Shape.Solids)==1,o.Name
        snap[o.Name]={'volume_mm3':o.Shape.Volume,'bounds_mm':bnd(o.Shape)}
tray.Tip.Shape.exportStep(str(P/'TrayLocalRibReliefs.step'))
s=Part.Shape();s.read(str(P/'TrayLocalRibReliefs.step'));assert s.isValid()and len(s.Solids)==1
A.closeDocument(d.Name);cold=A.openDocument(str(out))
assert not[o for o in cold.Objects if o.TypeId=='App::Link']
for n,v in snap.items():
    q=cold.getObject(n).Shape;assert q.isValid()and len(q.Solids)==1
    assert abs(q.Volume-v['volume_mm3'])<1e-6
    assert max(abs(a-b)for a,b in zip(bnd(q),v['bounds_mm']))<1e-6
r={'status':'Separate two-rib/two-wire local successor; no source or master promotion',
   'native_sha256':sha(out),'source_negative_native_sha256':sha(source),
   'source_negative_report_sha256':sha(P/'archive/static-negative-6d4dfb5d/complete-review.json'),
   'script_sha256':sha(Path(__file__)),'path_source_sha256':sha(P/'pack_paths_relief.py'),
   'native_relief_API_sha256':sha(P/'tray_relief_api.py'),'curve_utilities_sha256':sha(P/'curve_utils.py'),
   'changed_physical_components':['Tray','NTC1_RETURN','NTC2_RETURN'],'original_product_and_PCB_changed':False,
   'changed_endpoint_factory_head_joint_sleeve_or_pack_geometry':False,
   'unchanged_shape_count':len(unchanged),'unchanged_shape_names':unchanged,
   'Tray_delta':{'bounds_unchanged':True,'removed_volume_mm3':removed.Volume,'removed_outside_original_rib_lofts_mm3':outside,
                 'geometry':relief.GEOMETRY,'protected_features':exclusions,'remaining_rib_geometry':rib_support,
                 'four_main_parts_preserved':True,'pack_support_force_and_retention_qualified':False},
   'returned_wire_checks':reports,'cold_valid_single_solid_bodies':len(snap),'cold_body_geometry':snap,'cold_external_links':0,
   'tray_STEP_sha256':sha(P/'TrayLocalRibReliefs.step'),'tray_STEP_cold_read_solids':len(s.Solids),
   'physical_validation':False,'service_motion_validated':False,
   'unchanged_growth_port_findings':[{'wire':'PACK_FACTORY_POWER1','common_mm3':.07793113276311187},{'wire':'PACK_FACTORY_POWER2','common_mm3':.07793113276311187}],
   'open_gates':['Received pack/PCB/print and wire tolerances, abrasion and assembled load checks',
                 'Actual pack support/retention and no-preload NTC attachment',
                 'Crimp/solder/heat-shrink process and positive strain relief',
                 'Attached-wire mating and cap-threading/service sequence',
                 'Power, thermal, RF, magnetic, molding and complete product qualification']}
(P/'rib-relief-review.json').write_text(json.dumps(r,indent=2)+'\n')
print('LOCAL_SUCCESSOR_FROZEN',r['native_sha256'],len(snap),'cold valid Bodies',flush=True)
