"""New ten-wire forms in the accepted combined candidate; static digital trial."""
from pathlib import Path
import sys,json,hashlib,importlib.util,math
R=Path(__file__).resolve().parents[6]
spec=importlib.util.spec_from_file_location('j7',R/'tools/build_evt1_single_flange_j7_loom.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
A=m.A;Part=m.Part;V=m.V;P=m.OUT
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCC.Core.TopoDS import topods
sp=importlib.util.spec_from_file_location('wire_plan',P/'path-plan.py');pp=importlib.util.module_from_spec(sp);sp.loader.exec_module(pp)
source=P/'CombinedClearanceTrial.FCStd';binding=json.loads((P/'combined-review.json').read_text());assert m.sha(source)==binding['native_sha256']
assert binding['repair_positions_XZ_mm']=={'U75':[6.3,9],'U71':[-1,-7]}
d=A.openDocument(str(source));d.recompute()
context={o.Name.removeprefix('Context_'):o.Shape.copy()for o in d.getObject('ImmutableAssemblyContext').Group}
pack=json.loads((R/'hardware/pcb/evt1/pack-spec.json').read_text())['lead_exit']['product_mated_connector_bounds_mm']
context['RequestedBatteryPowerConnectorReservation']=m.box_bound(pack)
fixed={n:m.bound(q)for n,q in context.items()}
wg=d.addObject('App::Part','TenInterboardWires');cg=d.addObject('App::DocumentObjectGroup','WireCenterlines')

def edge(s):
 p=[V(*x)for x in s['points']]
 if s['kind']=='line':return Part.makeLine(*p)
 if s['kind']=='arc':return Part.Arc(*p).toShape()
 if s['kind']=='bezier':
  c=Part.BezierCurve();c.setPoles(p);return c.toShape()
 c=Part.BSplineCurve();c.interpolate(p)
 # Tangent-preserving end handles, avoiding interpolation hooks.
 first=V(*s['first_tangent']);last=V(*s['last_tangent']);first.normalize();last.normalize()
 c.setPole(2,p[0]+first*(c.getPole(2)-p[0]).Length)
 c.setPole(c.NbPoles-1,p[-1]-last*(c.getPole(c.NbPoles-1)-p[-1]).Length)
 return c.toShape()

rows=[];wires={}
for plan in pp.make_plan():
 n=plan['pin'];name='IB%02d'%n;path=Part.Wire([edge(s)for s in plan['sections']]);assert path.isValid()
 start=path.Edges[0].valueAt(path.Edges[0].FirstParameter);tan=path.Edges[0].tangentAt(path.Edges[0].FirstParameter)
 profile=Part.Wire([Part.makeCircle(.3,start,tan)])
 pipe=BRepOffsetAPI_MakePipeShell(topods.Wire(Part.__toPythonOCC__(path)))
 pipe.SetMode(False);pipe.SetTolerance(1e-6,1e-6,1e-6);pipe.SetMaxDegree(12);pipe.SetMaxSegments(500);pipe.SetForceApproxC1(True)
 pipe.Add(topods.Wire(Part.__toPythonOCC__(profile)),False,False);pipe.Build();assert pipe.IsDone() and pipe.MakeSolid()
 q=Part.__fromPythonOCC__(pipe.Shape());assert q.isValid() and len(q.Solids)==1,name
 b=d.addObject('PartDesign::Body',name);f=b.newObject('PartDesign::Feature','FormedWire'+str(n));f.Shape=q;wg.addObject(b)
 b.addProperty('App::PropertyString','MPN');b.MPN='Accu-Glass100690'
 b.addProperty('App::PropertyString','Net');b.Net=m.NETS[n-1]
 b.addProperty('App::PropertyString','CenterlineJSON');b.CenterlineJSON=json.dumps(plan)
 b.addProperty('App::PropertyLength','InsulationOD');b.InsulationOD=.6
 b.addProperty('App::PropertyLength','FreePathLength');b.FreePathLength=path.Length
 m.note(b,'Native circular sweep at design incoming OD0.60mm; nominal OEM wire0.508mm. Static formed candidate only; no flex, restraint or physical assembly proof. Finished cut length must include qualified terminal take-up.')
 if b.ViewObject:b.ViewObject.ShapeColor=(.52,.34,.12)
 ce=d.addObject('PartDesign::Feature',name+'Centerline');ce.Shape=path;cg.addObject(ce);ce.Visibility=False
 radii=[];junction=[]
 for i,e in enumerate(path.Edges):
  for j in range(1001):
   try:k=e.curvatureAt(e.FirstParameter+(e.LastParameter-e.FirstParameter)*j/1000)
   except (Part.OCCError,RuntimeError):k=0.
   if abs(k)>1e-10:radii.append(1/abs(k))
  if i:
   prev=path.Edges[i-1];gap=(prev.valueAt(prev.LastParameter)-e.valueAt(e.FirstParameter)).Length
   dot=prev.tangentAt(prev.LastParameter).dot(e.tangentAt(e.FirstParameter));junction.append({'gap_mm':gap,'tangent_dot':dot})
 assert min(radii)>4-1e-4,(name,min(radii))
 assert max(j['gap_mm']for j in junction)<1e-5 and min(j['tangent_dot']for j in junction)>1-1e-6
 rows.append({'wire':name,'pin':n,'net':m.NETS[n-1],'free_insulated_path_length_mm':path.Length,'OD_mm':.6,
  'minimum_sampled_radius_mm':min(radii),'curvature_samples_per_edge':1001,'junctions':junction,
  'bounds_mm':m.bound(q),'volume_mm3':q.Volume})
 wires[name]=q;print('WIRE_READY',name,path.Length,min(radii),flush=True)

d.recompute();out=P/'SingleFlangeLoomTrial.FCStd';d.saveAs(str(out));print('WIRE_NATIVE_SAVED',flush=True)
allbounds=[min(v['bounds_mm'][i]for v in rows)for i in range(3)]+[max(v['bounds_mm'][i]for v in rows)for i in range(3,6)]
empty=[];proofs=[]
for n,s in context.items():
 if not m.bb_common(allbounds,fixed[n]):empty.append(n);continue
 if n in ('RevisedContinuousSkin','ProposedRearHalf','ProposedFlangeTray','BodyInsulatingSleeve'):
  vol=m.box_bound(allbounds).common(s).Volume;proofs.append({'part':n,'common_mm3':vol})
  if vol<1e-7:empty.append(n)
checks=[]
for row in rows:
 name=row['wire'];q=wires[name];bad=[]
 for n,s in context.items():
  if n in empty or not m.bb_common(row['bounds_mm'],fixed[n]):continue
  v=q.common(s).Volume
  if v>1e-7:bad.append({'part':n,'common_mm3':v})
 checks.append({'wire':name,'clashes':bad});print('WIRE_CHECK',name,bad,flush=True)
pairs=[]
for i,name in enumerate(wires):
 for other in list(wires)[i+1:]:
  q=wires[name];s=wires[other];v=q.common(s).Volume
  pairs.append({'a':name,'b':other,'common_mm3':v,'surface_gap_mm':q.distToShape(s)[0]})
# A loose requested power-disconnect placement is an explicitly separate
# proposal, not an edit to the pack specification or to selected PCB sources.
altpack=context['RequestedBatteryPowerConnectorReservation'].copy();altpack.translate(V(-6,0,0))
alt={'translation_mm':[-6,0,0],'bounds_mm':m.bound(altpack),'wire_intersections':[],'fixed_intersections':[]}
for name,q in wires.items():
 v=q.common(altpack).Volume
 if v>1e-7:alt['wire_intersections'].append({'part':name,'common_mm3':v})
for n,s in context.items():
 if n=='RequestedBatteryPowerConnectorReservation' or not m.bb_common(alt['bounds_mm'],fixed[n]):continue
 v=altpack.common(s).Volume
 if v>1e-7:alt['fixed_intersections'].append({'part':n,'common_mm3':v})
r={'status':'Static formed-wire coupon; do not infer complete installed loom or physical assembly',
 'source_combined_native_sha256':m.sha(source),'source_PCB_sha256':binding['source_PCB_sha256'],
 'native_sha256':m.sha(out),'builder_sha256':m.sha(Path(__file__)),'path_builder_sha256':m.sha(P/'path-plan.py'),
 'wires':rows,'hard_checks':checks,'wire_pairs':pairs,'empty_region_proofs':{'bounds_mm':allbounds,'proofs':proofs},
 'loose_pack_disconnect_alternative':alt,'physical_validation':False,
 'open_gates':['Final routed candidate MCAD/source refresh','Actual mating housing exit datum and wire OD received checks','Pack loose-disconnect actual OEM geometry/installed route','Other six pack conductors and complete bundle clearance','Strain relief and service slack during preclosure mating','Received tool/shank/grip and controlled crimp process']}
(P/'wire-review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'native':str(out),'wire_hard_collisions':checks,'wire_pair_collisions':[p for p in pairs if p['common_mm3']>1e-7],'pack_alternative':alt},indent=2),flush=True)
