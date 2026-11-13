from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
r=Path(__file__).resolve().parents[5];p=Path(__file__).resolve().parent;h=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
j=json.loads((p/'review.json').read_text());n=p/'RearJointServiceTrial.FCStd';assert j['pass']and h(n)==j['native_sha256'];assert h(r/'tools/build_evt1_rear_joint_trial.py')==j['builder_sha256']
assert not any(x.FileName==str(n)for x in A.listDocuments().values()),'Close this trial before its cold check'
d=A.openDocument(str(n));rows=[]
for o in d.Objects:
 if o.TypeId=='PartDesign::Body':
  s=o.Shape;errors=s.check(True);assert not errors and s.isValid()and len(s.Solids)==1,(o.Name,errors)
  rows.append({'body':o.Name,'volume_mm3':s.Volume,'BOP_errors':errors})
 if o.TypeId=='Sketcher::SketchObject':assert o.FullyConstrained,o.Name
for name in('IFME10028','TwoJawDriver'):
 q=Part.read(str(p/(name+'.step')));a=d.getObject(name).Shape
 assert q.isValid()and len(q.Solids)==1 and abs(q.Volume-a.Volume)<1e-6
 assert (q.Solids[0].CenterOfMass-a.Solids[0].CenterOfMass).Length<1e-6
assert len(rows)==5
A.closeDocument(d.Name)
report={'pass':True,'native_sha256':h(n),'review_sha256':h(p/'review.json'),'checker_sha256':h(Path(__file__)),'bodies':rows,'all_native_sketches_fully_constrained':True,'STEP_parity':True,'physical_validation':False}
(p/'cold-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print('Cold5-body/BOP/sketch/2STEP parity passed',flush=True)
