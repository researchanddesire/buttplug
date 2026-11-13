"""Refresh selected PCBA poses from final routed-candidate MCAD, exterior fixed."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parents[6];sp=importlib.util.spec_from_file_location('m',R/'tools/build_evt1_flange_contact_module.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
P=m.OUT;A=m.App;Part=m.Part;N=P/'SingleFlangeBoardTrial.FCStd'
assert m.sha(N)=='5c348efe59825bde7b0c91fa99e66e62f69fff4aa421e58338a5896c09de2b4f'
ex=P/'exterior/SingleFlangeExterior.FCStd';assert m.sha(ex)=='4b9471fea1af7ace656350d1bc001c665d675ac7fe8014103637b7c204a3b7c5'
src=m.source();src.recompute();d=A.openDocument(str(N));d.recompute();jp,data=m.active_mcaddata()
old=json.loads((P/'archive/frozen-39-pre-mate-clearance/review.json').read_text())['actual_PCBA']
changes=[]
for c in data['components']:
 raw=Part.read(str(R/c['model']));assert raw.isValid()and raw.Solids and m.sha(R/c['model'])==c['model_sha256']
 raw.transformShape(A.Matrix(*[v for row in c['model_to_product_matrix4']for v in row]),False,False)
 group=d.getObject('Actual_'+c['ref']);bs=[o for o in group.Group if o.TypeId=='PartDesign::Body'];bs.sort(key=lambda o:int(o.Name.rsplit('Solid',1)[1]))
 assert len(bs)==len(raw.Solids),c['ref']
 for b,s in zip(bs,raw.Solids):b.Placement=A.Placement();b.Tip.Shape=s
 prior=next(x for x in old['parts']if x['ref']==c['ref'])
 if prior['model_to_product']!=c['model_to_product_matrix4']:changes.append(c['ref'])
assert sorted(changes)==['U71','U75'],changes
# The finished PCB/native outline is explicitly unchanged; outer copper is
# not mistaken for the raw KiCad0.91mm FR4 export envelope.
assert data['finished_board_local_STEP_sha256']==old['finished_board_STEP_sha256']
d.recompute();d.save();newsha=m.sha(N)
b=json.loads((P/'exterior/source-binding.json').read_text());b['mechanical_native_sha256']=newsha;b['MCAD_path']=str(jp.relative_to(R));b['MCAD_sha256']=m.sha(jp);b['PCB_sha256']=data['board_sha256'];b['internal_only_repair']={'U75_XZ_mm':[6.3,9],'U71_XZ_mm':[-1,-7],'portable_exterior_geometry_changed':False};(P/'exterior/source-binding.json').write_text(json.dumps(b,indent=2)+'\n')
assert m.sha(ex)=='4b9471fea1af7ace656350d1bc001c665d675ac7fe8014103637b7c204a3b7c5'
print(json.dumps({'new_native_sha256':newsha,'MCAD_sha256':m.sha(jp),'board_sha256':data['board_sha256'],'changed_refs':changes,'exterior_sha256':m.sha(ex)},indent=2))
