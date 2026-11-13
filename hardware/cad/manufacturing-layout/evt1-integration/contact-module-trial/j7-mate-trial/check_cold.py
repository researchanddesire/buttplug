"""Independent cold native readback: mates, wires and numeric pin order."""
from pathlib import Path
import sys,json,hashlib,math
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
P=Path(__file__).resolve().parent;R=P.parents[5]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bnd(s):
 b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
r=json.loads((P/'wire-review.json').read_text());n=P/'SingleFlangeLoomTrial.FCStd';assert sha(n)==r['native_sha256']
d=A.openDocument(str(n));d.recompute();bodies=[o for o in d.Objects if o.TypeId=='PartDesign::Body']
assert len(bodies)==32
for b in bodies:assert b.Shape.isValid()and len(b.Shape.Solids)==1,b.Name
links=[o.Name for o in d.Objects if o.TypeId=='App::Link'];assert not links
for ref,expected in [('J7',[-7.525,-25.842,-5.5,-2.525,-23.042,5.5]),('J6',[-5.5,31.525,.11,5.5,36.525,2.91])]:
 h=d.getObject(ref+'SHR10Housing');q=h.Shape.copy();q.transformShape(d.getObject(ref+'MatingAssembly').Placement.toMatrix(),True)
 assert max(abs(a-b)for a,b in zip(bnd(q),expected))<1e-6,(ref,bnd(q))
for c in ('U71','U75'):
 q=d.getObject('Context_Actual_'+c+'_Solid0').Shape
 expected=next(p for p in json.loads((P/'combined-review.json').read_text())['parts']if p['ref']==c)['model_checks'][0]['bounds_mm']
 assert max(abs(a-b)for a,b in zip(bnd(q),expected))<1e-6
contracts=json.loads((R/'hardware/pcb/evt1/single-flange-study/native-checks.json').read_text())['native_pad_contracts']
body=json.loads((R/'hardware/pcb/evt1/body/mcad.json').read_text())['pads']
checks=[]
for row in r['wires']:
 name=row['wire'];q=d.getObject(name).Shape;path=d.getObject(name+'Centerline').Shape
 assert abs(q.Volume-row['volume_mm3'])<1e-6
 assert max(abs(a-b)for a,b in zip(bnd(q),row['bounds_mm']))<1e-6
 assert abs(path.Length-row['free_insulated_path_length_mm'])<1e-6
 tube_volume=math.pi*.3**2*path.Length
 relative_volume_error=abs(q.Volume-tube_volume)/tube_volume
 assert relative_volume_error<1e-4 # 0.01 percent numerical volume sanity bound
 p=str(row['pin']);fc=next(v for v in contracts if v['ref']=='J7'and v['pad']==p)
 bc=next(v for v in body if v['ref']=='J6'and v['number']==p)
 start=path.Edges[0].valueAt(path.Edges[0].FirstParameter);end=path.Edges[-1].valueAt(path.Edges[-1].LastParameter)
 a=[bc['xy_mm'][0],31.525,1.51];b=[-2.525,-24.442,fc['product_XZ_mm'][1]]
 assert (start-A.Vector(*a)).Length<1e-6 and (end-A.Vector(*b)).Length<1e-6
 assert fc['net']==bc['net']==row['net']==d.getObject(name).Net
 checks.append({'wire':name,'pin':p,'net':row['net'],'first_point_mm':list(start),'last_point_mm':list(end),'volume_mm3':q.Volume,'length_mm':path.Length,'analytical_tube_volume_relative_error':relative_volume_error})
out={'status':'pass: independently cold-opened native mates/wires and source numeric pin order',
'native_sha256':sha(n),'valid_single_solid_bodies':len(bodies),'external_links':links,'wires':checks,
'source_contract_sha256':sha(R/'hardware/pcb/evt1/single-flange-study/native-checks.json'),
'source_body_MCAD_sha256':sha(R/'hardware/pcb/evt1/body/mcad.json'),'checker_sha256':sha(Path(__file__)),
'physical_validation':False}
(P/'cold-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
