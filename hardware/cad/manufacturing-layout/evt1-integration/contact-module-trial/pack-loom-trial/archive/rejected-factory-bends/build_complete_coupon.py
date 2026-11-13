"""Complete disposable pack/NTC/18-wire assembly, without source promotion."""
from pathlib import Path
import sys, json, hashlib, importlib.util, math
P = Path(__file__).resolve().parent; R = P.parents[5]
sys.path.insert(0,str(P))
import curve_utils as c
import pack_paths as pp
A=c.A; Part=c.Part; V=c.V
def module(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
m=module('j7',R/'tools/build_evt1_single_flange_j7_loom.py')
am=module('ach',R/'tools/build_evt1_single_flange_pack_loom.py')
fm=module('flange',R/'tools/build_evt1_flange_contact_module.py')
sha=m.sha
SOURCE=P.parent/'single-board/SingleFlangeBoardTrial.FCStd'
SOURCE_SHA='e2430ff72e0b36d9a079791ec246fe2c94ea94c3a07bae22ed7cae8e10cc2884'
assert sha(SOURCE)==SOURCE_SHA
active_path,active=fm.active_mcaddata()
old=json.loads(m.MCAD.read_text())
assert next(x['model_to_product_matrix4']for x in active['components']if x['ref']=='J7')==next(x['model_to_product_matrix4']for x in old['components']if x['ref']=='J7')
product=fm.source();product.recompute();src=A.openDocument(str(SOURCE));src.recompute()
d=A.newDocument('CompletePackLoomTrial');d.Label='Single flange: complete disposable pack and wiring trial'
context=d.addObject('App::Part','ImmutableAssemblyContext')
installed=fm.installed_objects(src)
for name in ('PackGrowthAllowance','PackSizeReference','BodyPCB','MetalBody','MotorThermistorCap','RearNutReference','BodyInsulatingSleeve','BodyFoamLeft','BodyFoamRight'):
    o=product.getObject(name)
    if o:installed.append(o)
for o in product.getObject('Electronics').Group:
    if o.Name.startswith('Body_') and o.Name!='Body_J6':installed.append(o)
shapes={o.Name:o.Shape.copy()for o in installed}
# Replace only the former J6 height-budget package with the selected header
# model used by the unchanged J7. The original body source is never mutated.
j7=next(x for x in active['components']if x['ref']=='J7')
q=Part.Shape();q.read(str(R/j7['model']));q.translate(V(0,36,0))
for i,s in enumerate(q.Solids):shapes['SelectedBodyJ6Solid'+str(i)]=s
for n,s in shapes.items():
    f=d.addObject('PartDesign::Feature','Context_'+n);f.Shape=s;context.addObject(f)
    f.addProperty('App::PropertyString','ImmutableSource');f.ImmutableSource='Bound source geometry; not an edited product component'
mates=m.add_mates(d)
ach=am.build_mated(d,'ProposedLooseACHAssembly')
ACH_FRAME=[[-1,0,0,-7.1],[0,0,1,-18.4],[0,1,0,-1.1],[0,0,0,1]]
ach['group'].Placement=A.Placement(m.matrix(ACH_FRAME))
parts=d.addObject('App::Part','PackNTCSensorsAndJoints')
def body(name,shape,mpn,scope,color):
    b=d.addObject('PartDesign::Body',name);f=b.newObject('PartDesign::Feature',name+'Geometry');f.Shape=shape
    b.addProperty('App::PropertyString','MPN');b.MPN=mpn;m.note(b,scope);parts.addObject(b)
    if b.ViewObject:b.ViewObject.ShapeColor=color
    return b
for sensor,sign in ((1,1),(2,-1)):
    h=Part.makeCylinder(1.5,7,V(18.5,-13.7,sign*4),V(1,0,0))
    for x in (18.5,25.5):h=h.fuse(Part.makeSphere(1.5,V(x,-13.7,sign*4)))
    body('PackNTC'+str(sensor),h.removeSplitter(),'NTCLE413E2103F524A',
         'Vishay primary 29078: maximum head diameter 3 mm and length 10 mm. Dry tape-supported installation; no hard potting, immersion or overmold credit.',(.08,.08,.08))

wg=d.addObject('App::Part','CompleteWireBundle');cg=d.addObject('App::DocumentObjectGroup','WireCenterlines')
rows=[];wire_shapes={};paths={}
plans=pp.interboard()+pp.power()+pp.ntcs()
for plan in plans:
    name=plan['name'];path=c.path(plan['sections']);chk=c.path_checks(path)
    assert path.isValid() and chk['maximum_join_gap_mm']<1e-5 and chk['minimum_join_tangent_dot']>1-1e-6,(name,chk)
    assert chk['minimum_sampled_radius_mm']>plan['minimum_radius_mm']-.01,(name,chk)
    if 'bare_end_length_mm'in plan:q=c.trimmed_bare(path,plan['OD_mm'],plan['bare_end_OD_mm'],plan['bare_end_length_mm'])
    else:q=c.tube(path,plan['OD_mm']/2)
    factory=None
    if plan.get('factory_sections'):
        factory=c.path(plan['factory_sections']);fc=c.path_checks(factory)
        assert fc['minimum_sampled_radius_mm']>plan['factory_minimum_radius_requirement_mm']-.01
        q=q.fuse(c.tube(factory,plan['factory_OD_mm']/2)).removeSplitter()
        assert q.isValid() and len(q.Solids)==1
        # Installed sleeve is a project maximum-OD acceptance geometry, not
        # an inferred fully recovered tube diameter or a solder-strength model.
        joint=V(*plan['joint_center_mm']);a=joint+V(-4.5,0,0)
        sleeve=Part.makeCylinder(1.2,9,a,V(1,0,0)).cut(Part.makeCylinder(.56,9,a,V(1,0,0)))
        body(name+'JointSleeve',sleeve,'RNF-100-1/16-BK-SP',
             'TE 5052894108 exact spool stock. 9 mm cut; installed OD must be <=2.4 mm. Intended 3 mm solder lap and coverage need a received joint coupon; this model gives no joint strength/seal credit.',(.05,.05,.05))
    b=d.addObject('PartDesign::Body',name);f=b.newObject('PartDesign::Feature',name+'FormedWire');f.Shape=q;wg.addObject(b)
    for prop,value in [('MPN',plan['wire']),('Net',plan['net']),('CenterlineJSON',json.dumps(plan))]:b.addProperty('App::PropertyString',prop);setattr(b,prop,value)
    b.addProperty('App::PropertyLength','FreePathLength');b.FreePathLength=path.Length+(factory.Length if factory else 0)
    m.note(b,'Nominal static circular-profile native wire. Received OD, formed routes, handling and strain relief are physical qualification gates. This is not a qualified flexible cable assembly.')
    if b.ViewObject:b.ViewObject.ShapeColor=(.7,.4,.12)if name.startswith('IB')else(.8,.08,.06)if 'POWER1'in name else(.18,.18,.18)
    ce=d.addObject('PartDesign::Feature',name+'Centerline');ce.Shape=path if not factory else Part.makeCompound([factory,path]);cg.addObject(ce);ce.Visibility=False
    rows.append(dict(wire=name,net=plan['net'],bounds_mm=m.bound(q),volume_mm3=q.Volume,
                     free_path_mm=path.Length,factory_path_mm=factory.Length if factory else None,
                     OD_mm=plan['OD_mm'],**chk))
    wire_shapes[name]=q;paths[name]=path
    print('WIRE_READY',name,b.FreePathLength.Value,chk['minimum_sampled_radius_mm'],flush=True)

d.recompute();out=P/'CompletePackLoomTrial.FCStd';d.saveAs(str(out));print('COMPLETE_NATIVE_CHECKPOINT_SAVED',flush=True)
geometry=[]
for name,q in wire_shapes.items():
    qb=m.bound(q);bad=[]
    for n,s in shapes.items():
        if not m.bb_common(qb,m.bound(s)):continue
        v=q.common(s).Volume
        if v>1e-7:bad.append({'part':n,'common_mm3':v})
    geometry.append({'wire':name,'intersections':bad});print('FIXED_CHECK',name,bad,flush=True)
pairs=[]
for i,(name,q)in enumerate(wire_shapes.items()):
    for other,s in list(wire_shapes.items())[i+1:]:
        if not m.bb_common(m.bound(q),m.bound(s)):continue
        v=q.common(s).Volume
        if v>1e-7:pairs.append({'a':name,'b':other,'common_mm3':v})
    print('PAIR_CHECKED',name,flush=True)
ach_shape=Part.makeCompound([m.globalshape(o)for o in [ach['plug'],ach['socket']]+ach['contacts']])
ach_checks=[]
for n,s in shapes.items():
    if not m.bb_common(m.bound(ach_shape),m.bound(s)):continue
    v=ach_shape.common(s).Volume
    if v>1e-7:ach_checks.append({'part':n,'common_mm3':v})
report={'status':'Disposable complete-bundle candidate; intersections below are findings, not waivers',
        'native_sha256':sha(out),'source_native_sha256':SOURCE_SHA,
        'source_MCAD_sha256':sha(fm.OUT/'active-PCBA-source.json'),
        'builder_sha256':sha(Path(__file__)),'paths_sha256':sha(P/'pack_paths.py'),'curve_utilities_sha256':sha(P/'curve_utils.py'),
        'wire_count':len(rows),'neck_conductors':16,'wires':rows,'fixed_checks':geometry,'wire_pair_intersections':pairs,
        'ACH_candidate_matrix4':ACH_FRAME,'ACH_fixed_intersections':ach_checks,
        'physical_validation':False,'service_motion_validated':False,
        'open_gates':['Received factory pack exits and longer power lead request','Complete live connector/tool handling and opening motion',
                      'Actual crimp and solder joints, insulation coverage, strain relief and received wire diameters',
                      'Dry NTC mounting/adhesive/wrapper compatibility and independent thermal response',
                      'RF, electrical power/charging, material/temperature/aging and molding qualification']}
(P/'complete-review.json').write_text(json.dumps(report,indent=2)+'\n')
print('REVIEW_SAVED',len(rows),'wire bodies',len(pairs),'wire-pair findings',flush=True)
