"""Merged native flange/compass candidate with immutable full-device ERC context.

Only J1/J82 interconnect lands are removed; four selected fixed targets replace
J1 electrically. Original body artwork and authoring schematics are untouched.
"""
from pathlib import Path
import copy,hashlib,json,shutil,sys,uuid
H=Path(__file__).resolve().parent;E=H.parent;ROOT=H.parents[3];STUDY=E/'single-flange-study';sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
import electronics_r0_generate as g
from build_evt1_electrical import remove_component
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();NS=uuid.UUID('f07a977f-6120-4904-a254-0c82d19cfefe');uid=lambda x:str(uuid.uuid5(NS,x));q=json.dumps
PROJECT='single-flange';SYSTEM='single-flange-system'
def top(name,title,entries):
 root=s.parse(f'(kicad_sch (version 20230121) (generator single_flange_merge) (uuid {uid(name)}) (paper "A3") (title_block (title {q(title)}) (date "2026-11-12") (rev "EVT1 single flange candidate") (company "Research and Desire") (comment 1 "FIXED39-POSITION STUDY / NO FABRICATION RELEASE")) (lib_symbols) (sheet_instances (path "/" (page "1"))))')
 for i,(label,filename,identity)in enumerate(entries):
  x=25.4+(i%2)*177.8;y=63.5+(i//2)*60.96
  root.append(s.parse(f'(sheet (at {x} {y}) (size 152.4 25.4) (fields_autoplaced) (stroke (width .1524) (type default)) (fill (color 0 0 0 0)) (uuid {identity}) (property "Sheetname" {q(label)} (at {x} {y-.508} 0) {g.effects(1.27,"(justify left bottom)")}) (property "Sheetfile" {q(filename)} (at {x} {y+25.908} 0) {g.effects(1.016,"(justify left top)")}))'))
 return root

def main():
 guard=json.loads((STUDY/'native-checks.json').read_text());assert guard['board_sha256']==sha(STUDY/'single-flange-placement.kicad_pcb');assert guard['models']==39
 for p,v in guard['all_local_source_sha256'].items():assert sha(STUDY/p)==v,('frozen study changed',p)
 for name in('Selected.pretty','Selected.3dshapes'):
  shutil.copytree(STUDY/name,H/name,dirs_exist_ok=True)
 shutil.copyfile(STUDY/'fp-lib-table',H/'fp-lib-table')
 (H/'sheets').mkdir(exist_ok=True);(H/'validation-context/body').mkdir(parents=True,exist_ok=True)
 inputs={};trees={};retained={};entries=[]
 for name in('01-power','03-control','06-interboard','07-recovery'):
  source=E/'flange'/(name+'.kicad_sch');inputs[str(source.relative_to(ROOT))]=sha(source);tree=s.parse(source.read_text())
  if name=='01-power':remove_component(tree,'J1')
  for symbol in s.children(tree,'symbol'):
   ref=s.prop(symbol,'Reference');fp=s.prop(symbol,'Footprint')
   if fp:
    prop=next(p for p in s.children(symbol,'property')if p[1].value=='Footprint');prop[2]=s.string('Selected:'+fp.split(':')[1]);retained[ref]=str(source.relative_to(ROOT))
  target=H/'sheets'/(name+'.kicad_sch');trees[target]=tree;entries.append((name,'sheets/'+target.name,uid('sheet-'+name)))
 source=E/'sensor/sensor-evt1.kicad_sch';inputs[str(source.relative_to(ROOT))]=sha(source);tree=s.parse(source.read_text());remove_component(tree,'J82')
 for symbol in s.children(tree,'symbol'):
  ref=s.prop(symbol,'Reference');fp=s.prop(symbol,'Footprint')
  if fp:
   next(p for p in s.children(symbol,'property')if p[1].value=='Footprint')[2]=s.string('Selected:'+fp.split(':')[1]);retained[ref]=str(source.relative_to(ROOT))
 trees[H/'sheets/08-compass.kicad_sch']=tree;entries.append(('Fixed flange compass','sheets/08-compass.kicad_sch',uid('sheet-compass')))
 # Exact one-pin passive target symbol; no invented supply drivers.
 g.LIB.clear();g.OUT=H/'sheets';g.PROJECT=PROJECT
 g.ic('FixedTarget1946',[(1,'TARGET','passive')],[],'https://www.mill-max.com/products/pin/1946','1946-0-00-15-00-00-03-0 solder-tail fixed target; same four interface nets')
 contacts=g.Sheet('04-targets','Four PCB-mounted charge/data targets')
 for i,net in enumerate(('GND','USB_DM_CONTACT','USB_DP_CONTACT','DOCK_5V'),1):contacts.part('FixedTarget1946','CT'+str(i),'1946-0-00-15-00-00-03-0',76.2,50.8+35.56*(i-1),{'1':net},'Selected:MillMax_1946_0_PTH_Study',domain='MAIN_T')
 contacts.note('Same GND/D−/D+/5V order on6mm pitch. Fixed39-part placement is mechanically source-bound.\nBody electronics/J7 interface unchanged. No new output/driver flags are added.',25.4,15.24)
 contacts.save();target=H/'sheets/04-targets.kicad_sch';trees[target]=s.parse(target.read_text());entries.append(('Fixed target interface','sheets/04-targets.kicad_sch',uid('sheet-targets')))
 trees[H/(PROJECT+'.kicad_sch')]=top(PROJECT,'Single flange / radio, controls, USB recovery and fixed compass',entries)
 # Full ERC uses the real retained body drivers and existing external NTCs.
 for source in sorted((E/'body').glob('*.kicad_sch')):
  inputs[str(source.relative_to(ROOT))]=sha(source);trees[H/'validation-context/body'/source.name]=s.parse(source.read_text())
 for name in('external-04-sensors.kicad_sch','external-05-charge-guard.kicad_sch'):
  source=E/name;inputs[str(source.relative_to(ROOT))]=sha(source);trees[H/'validation-context'/name]=s.parse(source.read_text())
 context=[('Unmodified body electronics','validation-context/body/body-evt1.kicad_sch',uid('body-instance')),('Single merged flange',PROJECT+'.kicad_sch',uid('flange-instance')),('Remote tip NTC','validation-context/external-04-sensors.kicad_sch',uid('tip-instance')),('Requested pack dual NTCs','validation-context/external-05-charge-guard.kicad_sch',uid('pack-instance'))]
 trees[H/(SYSTEM+'.kicad_sch')]=top(SYSTEM,'Single-flange complete device ERC context / body circuit conserved',context)
 def annotate(path,project,instance):
  tree=trees[path]
  for symbol in s.children(tree,'symbol'):
   ref=s.prop(symbol,'Reference');old=s.child(symbol,'instances')
   if old is None:old=s.parse('(instances)');symbol.append(old)
   old[:]=[a for a in old if not(isinstance(a,list)and s.tag(a)=='project'and a[1].value==project)]
   old.append(s.parse(f'(project {q(project)} (path {q(instance)} (reference {q(ref)}) (unit {s.value(symbol,"unit")or"1"})))'))
  for sheet in s.children(tree,'sheet'):annotate((path.parent/s.prop(sheet,'Sheetfile')).resolve(),project,instance+'/'+s.value(sheet,'uuid'))
 trees={p.resolve():t for p,t in trees.items()}
 for project in(PROJECT,SYSTEM):annotate((H/(project+'.kicad_sch')).resolve(),project,'/'+uid(project))
 # Library is the exact union of embedded source definitions, plus the target.
 library={}
 for tree in trees.values():
  for symbol in s.children(s.child(tree,'lib_symbols'),'symbol'):
   name=symbol[1].value;key=name.split(':',1)[1];node=copy.deepcopy(symbol);node[1]=s.string(key)
   if key in library:assert s.dump(library[key])==s.dump(node),('conflicting source symbol',key)
   else:library[key]=node
 symbols=s.parse('(kicad_symbol_lib (version 20220914) (generator single_flange_merge))');symbols.extend(library[k]for k in sorted(library));s.write(H/'PrototypeR0.kicad_sym',symbols)
 s.write(H/'sym-lib-table',s.parse('(sym_lib_table (version 7) (lib (name "PrototypeR0") (type "KiCad") (uri "${KIPRJMOD}/PrototypeR0.kicad_sym") (options "") (descr "Exact cached source symbols plus passive1946 target")))'))
 # Body library URIs are read-only source context, not copied PCB artwork.
 fptable=s.parse((H/'fp-lib-table').read_text())
 for lib in s.children(s.parse((E/'body/fp-lib-table').read_text()),'lib'):
  node=copy.deepcopy(lib);uri=s.value(node,'uri');resolved=Path(uri.replace('${KIPRJMOD}',str(E/'body'))).resolve();next(a for a in s.children(node,'uri'))[1]=s.string('${KIPRJMOD}/'+__import__('os').path.relpath(resolved,H));fptable.append(node)
 s.write(H/'fp-lib-table',fptable)
 for path,tree in trees.items():s.write(path,tree)
 for project in(PROJECT,SYSTEM):
  settings=json.loads((STUDY/'single-flange-placement.kicad_pro').read_text());settings['erc']={'erc_exclusions':[],'rule_severities':{k:'warning'for k in('single_global_label','four_way_junction','simulation_model_issue','footprint_filter')}};(H/(project+'.kicad_pro')).write_text(json.dumps(settings,indent=2)+'\n')
 report={'scope':'35 retained source refs plus4fixed targets; body69 artwork unchanged','frozen_study_board_sha256':guard['board_sha256'],'frozen_study_checks_sha256':sha(STUDY/'native-checks.json'),'frozen_study_MCAD_sha256':sha(STUDY/'mcad.json'),'source_inputs_sha256':inputs,'retained_flange_sensor_reference_map':retained,'removed_refs':{'J1':'four copper contact lands becomeCT1..CT4, same nets/order','J82':'redundant sensor-only interboard lands; direct circuit joins on same flange'},'new_targets':{'CT1':'GND','CT2':'USB_DM_CONTACT','CT3':'USB_DP_CONTACT','CT4':'DOCK_5V'},'no_new_supply_flags':True,'full_ERC_context':'single-flange-system.kicad_sch includes read-only circuit snapshots of real body drivers and existing remote NTCs','schematic_outputs_sha256':{str(p.relative_to(H)):sha(p)for p in trees},'source_replacement_or_fabrication_release':False}
 assert len(retained)==35;(H/'schematic-source-bindings.json').write_text(json.dumps(report,indent=2)+'\n');print('Merged35+4source positions; body context preserved')
if __name__=='__main__':main()
