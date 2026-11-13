from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part,importlib.util
small=Part.makeBox(1,1,1,A.Vector(.5,.5,.5));large=Part.makeBox(2,2,2);outside=Part.makeBox(1,1,1,A.Vector(4,0,0));assert Part.makeCompound([small,outside]).distToShape(large)[0]<1e-9
P=Path(__file__).resolve().parent;N=P/'SingleFlangeBoardTrial.FCStd';d=A.openDocument(str(N));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for o in d.Objects:
 if o.TypeId=='PartDesign::Body':
  s=o.Shape;assert not s.isNull()and s.isValid()and len(s.Solids)==1,o.Name
  rows.append({'name':o.Name,'volume_mm3':s.Volume,'solids':len(s.Solids)})
exports=[]
for p in sorted(P.glob('*.step'))+sorted((P/'models').glob('*.step')):
 s=Part.read(str(p));assert not s.isNull()and s.isValid()and len(s.Solids)>0,p
 exports.append({'path':str(p.relative_to(P)),'sha256':sha(p),'solids':len(s.Solids),'volume_mm3':s.Volume})
 if p.name=='MillMax1946.step':
  assert len(s.Solids)==1 and abs(s.Volume-12.031202541537699)<1e-6
  b=s.optimalBoundingBox(False,False);expected=[-1.5875,-1.5875,-2.794,1.5875,1.5875,3.048]
  assert max(abs(a-b)for a,b in zip([b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],expected))<1e-6
m=P/'models/MillMax1946.FCStd';md=A.openDocument(str(m));assert md.getObject('MillMax1946').Shape.isValid()and len(md.getObject('MillMax1946').Shape.Solids)==1
review=json.loads((P/'review.json').read_text());modelposes=[];root=P.parents[5]
for c in review['actual_PCBA']['parts']:
 g=d.getObject('Actual_'+c['ref']);assert g
 shape=Part.makeCompound([o.Shape for o in g.Group if o.TypeId=='PartDesign::Body'])
 expected=Part.read(str(root/c['source']));expected.transformShape(A.Matrix(*[v for row in c['model_to_product']for v in row]),False,False);eb=expected.optimalBoundingBox(False,False);expected_bb=[eb.XMin,eb.YMin,eb.ZMin,eb.XMax,eb.YMax,eb.ZMax]
 b=shape.optimalBoundingBox(False,False);bb=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
 assert max(abs(a-b)for a,b in zip(bb,expected_bb))<1e-5,c['ref']
 assert abs(shape.Volume-expected.Volume)<1e-4,c['ref']
 assert abs(shape.Volume-c['volume_mm3'])<1e-4,c['ref']
 modelposes.append({'ref':c['ref'],'solids':len(shape.Solids),'bounds_mm':bb,'native_vs_source_pose':'pass'})
board=d.getObject('ActualNativeFlangePCB').Shape;b=board.optimalBoundingBox(False,False)
assert max(abs(a-b)for a,b in zip([b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],[-41,-26.952,-13,41,-25.952,13]))<1e-5
R=P.parents[5];f=R/'tools/build_evt1_flange_contact_module.py';sp=importlib.util.spec_from_file_location('helper',f);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
source=m.source();parity=[]
for n in('MetalBody','MotorThermistorCap','BodyPCB'):
 q=d.getObject('Source'+n).Shape;t=source.getObject(n).Shape
 assert abs(q.Volume-t.Volume)<1e-6
 assert q.cut(t).Volume<1e-6 and t.cut(q).Volume<1e-6,n
 parity.append({'name':n,'unchanged_source_geometry':True})
ex=[]
for o in m.exterior_objects(d):
 q=o.Shape.copy();before=m.bnd(q);q.translate(m.V(0,53.2,32));ex.append({'native_object':o.Name,'product_bounds_mm':before,'dock_bounds_mm':m.bnd(q),'volume_mm3':q.Volume})
exnative=P/'exterior/SingleFlangeExterior.FCStd';exdoc=A.openDocument(str(exnative));assert len([o for o in exdoc.Objects if o.TypeId=='PartDesign::Body'])==9 and not any(o.TypeId=='App::Link'for o in exdoc.Objects)
for o in [o for o in exdoc.Objects if o.TypeId=='PartDesign::Body']:assert o.Shape.isValid()and len(o.Shape.Solids)==1
(P/'exterior-poses.json').write_text(json.dumps({'native_sha256':sha(N),'source_product_sha256':m.SOURCE_SHA,'dock_translation_mm':[0,53.2,32],'objects':ex,'body_and_cap_geometry_changed':False,'whole_dock_fit_acceptance':False},indent=2)+'\n')
r={'status':'cold savednative, exactmodelpose and all STEP BRep readback','native_sha256':sha(N),'checker_sha256':sha(Path(__file__)),'bodies':rows,'STEPs':exports,'selected_target_native_sha256':sha(m.OUT/'models/MillMax1946.FCStd'),'39_native_model_poses':modelposes,'unchanged_source_parity':parity,'installed_object_count':len(m.installed_objects(d)),'exterior_object_count':len(ex),'exterior_native_sha256':sha(exnative),'exterior_native_cold_body_count':9,'exterior_transitive_links':0,'physical_validation':False};(P/'cold-readback.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'bodies':len(rows),'STEP_exports':len(exports),'actual_model_poses':len(modelposes),'installed_objects':len(m.installed_objects(d)),'exterior_objects':len(ex)}))
