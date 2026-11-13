"""Independent native terminal conservation for merged flange and retained body."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
H=Path(__file__).resolve().parent;E=H.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
 r=ET.parse(p).getroot();return {c.get('ref'):c for c in r.findall('./components/comp')},{(q.get('ref'),q.get('pin')):n.get('name')for n in r.findall('./nets/net')for q in n.findall('node')}
old,oldpins=load(E/'system-native.xml');full,pins=load(H/'system-native.xml');flange,fpins=load(H/'single-flange-native.xml');study=json.loads((E/'single-flange-study/native-checks.json').read_text());expected={r['ref']for r in study['model_coverage']};assert set(flange)==expected and len(expected)==39
for p,v in study['source_invariant_sha256'].items():assert sha(E/p)==v,('frozen original source/artwork changed',p)
assert set(full)==(set(old)-{'J1','J82'})|{'CT1','CT2','CT3','CT4'} and len(full)==111
unchanged={r for r in old if r not in('J1','J82')};compared=[]
for (ref,pin),net in oldpins.items():
 if ref not in unchanged:continue
 assert pins[ref,pin]==net,(ref,pin,net,pins.get((ref,pin)));compared.append({'ref':ref,'pin':pin,'net':net})
for ref in unchanged:
 assert full[ref].findtext('value')==old[ref].findtext('value')
 prior=old[ref].findtext('footprint')or'';current=full[ref].findtext('footprint')or''
 assert current==(('Selected:'+prior.split(':')[1])if ref in expected else prior),(ref,prior,current)
for i,net in enumerate(('GND','USB_DM_CONTACT','USB_DP_CONTACT','DOCK_5V'),1):
 assert oldpins['J1',str(i)]==pins['CT'+str(i),'1']==net
assert {(r,p):n for(r,p),n in pins.items()if r in expected}==fpins and len(fpins)==155
for p in range(1,11):assert fpins['J7',str(p)]==oldpins['J6',str(p)]==oldpins['J7',str(p)]
for row in study['native_pad_contracts']:assert fpins[row['ref'],row['pad']]==row['net']
erc=json.loads((H/'system-erc.json').read_text());viol=[q for sh in erc['sheets']for q in sh['violations']];assert not viol and not erc.get('ignored_checks')
bind=json.loads((H/'schematic-source-bindings.json').read_text())
for p,v in bind['source_inputs_sha256'].items():assert sha(H.parents[3]/p)==v,('original source changed',p)
for p,v in bind['schematic_outputs_sha256'].items():assert sha(H/p)==v
r={'status':'pass: native full-device ERC0 and terminal conservation','source_body_board_sha256':sha(E/'body/body-evt1.kicad_pcb'),'frozen_study_board_sha256':study['board_sha256'],'merged_positions':39,'standalone_logical_terminals':len(fpins),'full_context_components':len(full),'full_context_logical_terminals':len(pins),'unchanged_original_terminal_checks':compared,'preserved_J7_numeric_interface':[{'pin':str(i),'net':fpins['J7',str(i)]}for i in range(1,11)],'new_target_nets':{r:fpins[r,'1']for r in('CT1','CT2','CT3','CT4')},'native_ERC_violations':0,'native_ERC_ignored_checks':[],'native_KiCad_version':erc['kicad_version'],'no_new_power_flags':True,'new_full_context_XML_sha256':sha(H/'system-native.xml'),'merged_XML_sha256':sha(H/'single-flange-native.xml'),'ERC_sha256':sha(H/'system-erc.json'),'schematic_source_binding_sha256':sha(H/'schematic-source-bindings.json'),'source_authoring_or_body_artwork_changed':False,'routing_or_build_release':False}
(H/'schematic-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in('status','merged_positions','standalone_logical_terminals','full_context_components','full_context_logical_terminals','native_ERC_violations')}))
