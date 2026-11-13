"""Derived complete-system ERC context; replace only J302 metadata and symbol ID."""
from pathlib import Path
import hashlib,json,os,shutil,sys
H=Path(__file__).resolve().parent;P=H.parent;R=P.parents[3]
sys.path.insert(0,str(R/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=P.parent/'dock-system';out=H/'system-snapshot';out.mkdir(exist_ok=True)
assert not(out/'dock-system.kicad_sch').exists(),'Preserve existing derived context'
inputs=[source/'dock-system.kicad_sch',source/'dock-system.kicad_pro',source/'native.xml',source/'native-checks.json']+list((source/'sheets').glob('*.kicad_sch'))
guards={str(p.relative_to(R)):sha(p)for p in inputs}
for name in ('dock-system.kicad_sch','dock-system.kicad_pro'):shutil.copyfile(source/name,out/name)
project=out/'dock-system.kicad_pro';settings=json.loads(project.read_text())
settings.setdefault('erc',{})['rule_severities']={n:'warning'for n in ['single_global_label','four_way_junction','simulation_model_issue','footprint_filter']}
project.write_text(json.dumps(settings,indent=2)+'\n')
shutil.copytree(source/'sheets',out/'sheets')
leaf=out/'sheets/dock-lid-ui.kicad_sch';tree=s.parse(leaf.read_text());new=s.parse((H/'dock-lid-ui.kicad_sch').read_text())
a=next(x for x in s.children(tree,'symbol')if s.prop(x,'Reference')=='J302')
b=next(x for x in s.children(new,'symbol')if s.prop(x,'Reference')=='J302')
newprops={p[1].value:p[2]for p in s.children(b,'property')}
for p in s.children(a,'property'):
    if p[1].value in ['Value','Footprint','Datasheet','Manufacturer','MPN','ReviewNote']:p[2]=newprops[p[1].value]
leaf.write_text(s.dump(tree).replace('MOLEX_52437_2771','JST_27FLZ_RSM2_TB')+'\n')
libs={'DockControl':H/'DockControl.kicad_sym','DockSafety':P.parent/'dock-safety/DockSafety.kicad_sym','DockUI':P.parent/'dock-ui/DockUI.kicad_sym','DockUV':P.parent/'dock-uv/base/DockUV.kicad_sym'}
for n,p in libs.items():shutil.copyfile(p,out/(n+'.kicad_sym'));guards[str(p.relative_to(R))]=sha(p)
table=(source/'sym-lib-table').read_text()
for prefix in ['../dock-control/','../dock-safety/','../dock-ui/','../dock-uv/base/']:table=table.replace('${KIPRJMOD}/'+prefix,'${KIPRJMOD}/')
(out/'sym-lib-table').write_text(table)
shutil.copytree(P/'DockControl.pretty',out/'DockControl.pretty')
for path in (P/'DockControl.pretty').glob('*.kicad_mod'):guards[str(path.relative_to(R))]=sha(path)
name='JST_27FLZ-RSM2-TB_1x27_P0.50mm_BottomContact.kicad_mod'
shutil.copyfile(H/'DockControl.pretty'/name,out/'DockControl.pretty'/name)
table=s.parse((source/'fp-lib-table').read_text())
for lib in s.children(table,'lib'):
    target=(out/'DockControl.pretty')if s.value(lib,'name')=='DockControl'else(source/s.value(lib,'uri').replace('${KIPRJMOD}/','')).resolve()
    s.child(lib,'uri')[1]=s.string('${KIPRJMOD}/'+os.path.relpath(target,out))
s.write(out/'fp-lib-table',table)
for p,d in guards.items():assert sha(R/p)==d
(out/'source-bindings.json').write_text(json.dumps({'source_sha256':guards,'builder_sha256':sha(Path(__file__)),'scope':'Complete-system electrical context; only J302 part/library/footprint metadata changes, all terminals unchanged'},indent=2)+'\n')
print(out)
