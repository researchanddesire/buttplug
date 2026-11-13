"""Bind the verified base layout geometry to the identical lid circuit."""
from pathlib import Path
import json
import re
import shutil
import xml.etree.ElementTree as ET
import build_pcbs as m
k=m.k
source=m.HERE/'base/pcb/dock-uv-base.kicad_pcb'
out=m.HERE/'lid/pcb';out.mkdir(exist_ok=True)
dest=out/'dock-uv-lid.kicad_pcb'
assert not dest.exists(),'Preserve existing lid PCB before cloning'
before=m.sha(source)
assert not json.loads((source.parent/'native-drc.json').read_text())['violations']
check=json.loads((m.HERE/'lid/native-checks.json').read_text())
for rel,h in check['source_sha256'].items():assert m.sha(m.HERE/'lid'/rel)==h,rel
tree=ET.parse(m.HERE/'lid/native.xml').getroot()
comps={c.get('ref'):c for c in tree.findall('./components/comp')}
b=k.LoadBoard(str(source));b.SetFileName(str(dest))
for net in b.GetNetInfo().NetsByNetcode().values():
    name=net.GetNetname()
    net.SetNetname(name.replace('BASE','LID').replace('LOOP_A_RAW','LOOP_B_RAW'))
for fp in b.GetFootprints():
    old=fp.GetReference();match=re.fullmatch(r'([A-Za-z]+)(\d+)',old);assert match,old
    ref=match[1]+str(int(match[2])+100);fp.SetReference(ref)
    if ref in comps:
        c=comps[ref];assert fp.GetValue().replace('BASE','LID').replace('LOOP_A_RAW','LOOP_B_RAW')==c.findtext('value')
        fp.SetValue(c.findtext('value'))
        fp.SetPath(k.KIID_PATH(c.find('sheetpath').get('tstamps')+c.findtext('tstamps')))
    else:assert ref.startswith('H'),ref
shutil.copytree(source.parent/'DockUV.pretty',out/'DockUV.pretty',dirs_exist_ok=True)
shutil.copy2(source.parent/'fp-lib-table',out/'fp-lib-table')
m.save(b,dest)
assert m.sha(source)==before,'Base PCB changed during cloning'
(out/'clone-source.json').write_text(json.dumps({'base_board_sha256':before,
    'lid_native_xml_sha256':m.sha(m.HERE/'lid/native.xml'),
    'lid_parts_sha256':m.sha(m.HERE/'lid/parts-selection.json'),
    'cloner_sha256':m.sha(Path(__file__)),'board_sha256':m.sha(dest),
    'scope':'Identical copper/placement/outline, renamed refs/nets and native schematic paths; properRy180 MCAD transform still required',
    'physical_fit':False},indent=2)+'\n')
print(dest)
