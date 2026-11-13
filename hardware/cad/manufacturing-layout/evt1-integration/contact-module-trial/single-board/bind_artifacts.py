from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;R=P.parents[5];N=P/'SingleFlangeBoardTrial.FCStd';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((P/'review.json').read_text());c=json.loads((P/'cold-readback.json').read_text());v=json.loads((P/'render-binding.json').read_text())
assert sha(N)==c['native_sha256']==v['native_sha256']
assert not r['source_hard_clashes'];assert r['closed_rigid_halves_common_mm3']<1e-6
assert all(x['common_mm3']<1e-6 for x in r['permanent_barrier_hard_checks']+r['continuous_skin_hard_checks'])
a=r['actual_PCBA'];assert sha(R/a['json_path'])==a['json_sha256'];j=json.loads((R/a['json_path']).read_text());assert sha(R/j['native_board'])==a['board_sha256'];assert sha(R/a['finished_board_STEP'])==a['finished_board_STEP_sha256']
for p in a['parts']:assert sha(R/p['source'])==p['sha256']
assert not a['hard_clashes'] and not a['actual_package_pair_clashes']
for name in('whole_PCB_loading','RearHalf_closing'):assert all(not p['collisions']for p in r[name])
for name in('whole_PCBA_loading','whole_PCBA_closing'):assert all(not p['collisions']for p in a[name])
files={}
for p in sorted(P.rglob('*')):
 if not p.is_file()or p.suffix in('.FCBak','.pyc')or'__pycache__'in p.parts or'archive'in p.parts or p.name=='artifact-bindings.json':continue
 files[str(p.relative_to(P))]=sha(p)
helper=R/'tools/build_evt1_flange_contact_module.py';files[str(helper.relative_to(R))]=sha(helper)
b={'status':'Hash-bound nominal mechanical candidate; routed source candidate, physical gates open','native_sha256':sha(N),'source_product_sha256':r['sources']['product_sha256'],'PCBsha256':a['board_sha256'],'MCADsha256':a['json_sha256'],'actual_selected_positions':len(a['parts']),'native_component_bodies':len(c['bodies']),'source_hard_pairs':len(r['source_hard_pairs']),'actual_package_to_fixed_checks':len(a['package_to_fixed_checks']),'PCB_loading_poses':len(r['whole_PCB_loading']),'PCBA_loading_poses':len(a['whole_PCBA_loading']),'PCBA_closing_poses':len(a['whole_PCBA_closing']),'files':files,'physical_validation':False};(P/'artifact-bindings.json').write_text(json.dumps(b,indent=2)+'\n');print(json.dumps({k:v for k,v in b.items()if k!='files'},indent=2))
