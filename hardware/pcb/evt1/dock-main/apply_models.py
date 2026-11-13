"""Resolve only model metadata to local STEP; conserve all electrical geometry."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[3]/'tools'))
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=H/'dock-main.kicad_pcb';meta=json.loads((H/'placement.json').read_text());assert sha(P)==meta['native_board_sha256']
plan=json.loads((H/'model-plan.json').read_text());fpplan=plan['footprint_models'];copper=set(plan['copper_only_footprints'])
def without_models(node):
 if isinstance(node,s.Atom):return node.raw
 return [without_models(n)for n in node if not(isinstance(n,list)and s.tag(n)=='model')]
def apply(fp,lib):
 models=s.children(fp,'model')
 if lib in copper:
  assert not models;return None
 assert lib in fpplan,lib;record=fpplan[lib];local=H/'DockMain.3dshapes'/record['local_STEP'];assert sha(local)==record['sha256']
 before=without_models(fp)
 if models:
  assert len(models)==1;model=models[0]
 else:
  model=s.parse('(model "" (offset(xyz 0 0 0))(scale(xyz 1 1 1))(rotate(xyz 0 0 0)))');fp.append(model)
 model[1]=s.string('${KIPRJMOD}/DockMain.3dshapes/'+local.name)
 assert without_models(fp)==before,'Model edit changed another footprint token'
 return {'model_URI':model[1].value,'model_sha256':sha(local),'classification':record['classification'],'transforms':{key:[x.value for x in s.child(s.child(model,key),'xyz')[1:]]for key in ('offset','scale','rotate')}}
for folder in H.glob('*.pretty'):
 for path in folder.glob('*.kicad_mod'):
  fp=s.parse(path.read_text());lib=folder.stem+':'+path.stem
  before=without_models(fp);apply(fp,lib);assert before==without_models(fp);s.write(path,fp)
root=s.parse(P.read_text());original=without_models(root);old=sha(P);records=[]
for fp in s.children(root,'footprint'):
 ref=next(t[2].value for t in s.children(fp,'fp_text')if t[1].value=='reference')
 if ref.startswith('H70'):continue
 lib=fp[1].value;model=apply(fp,lib);records.append({'reference':ref,'source_footprint':lib,'model':model,'copper_only':model is None})
assert len(records)==150 and sum(r['copper_only']for r in records)==12
assert original==without_models(root),'Non-model board metadata/copper/pad/placement changed'
s.write(P,root);assert without_models(s.parse(P.read_text()))==original
meta['native_board_sha256']=sha(P);meta['local_model_metadata_only']={'before_sha256':old,'after_sha256':sha(P),'all_other_tokens_exact':True};(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'status':'all138 physical package positions have local STEP;12 copper-only positions correctly omit purchased-body models','board_before_sha256':old,'board_after_sha256':sha(P),'electrical_references':150,'physical_model_positions':138,'copper_only_positions':12,'all_other_board_tokens_exact':True,'references':records,'model_plan_sha256':sha(H/'model-plan.json'),'physical_validation':False}
provenance=json.loads((H/'footprint-provenance.json').read_text())
for lib,row in provenance.items():
 local=H/row['local'];row['local_sha256']=sha(local)
 row['models']=[n[1].value for n in s.children(s.parse(local.read_text()),'model')]
 row['local_model_binding']='model-plan.json; all non-model footprint tokens conserved by apply_models.py'
(H/'footprint-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(H/'model-coverage.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
