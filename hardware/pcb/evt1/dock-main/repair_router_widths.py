"""Raise only DRC-named new router necks to native minimum; recheck spacing."""
from pathlib import Path
import json,hashlib
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((H/'placement.json').read_text());before=sha(P);assert before==m['native_board_sha256'];b=k.LoadBoard(str(P));ts={t.m_Uuid.AsString():t for t in b.GetTracks()};d=json.loads((H/'drc.json').read_text());changed=[]
for v in d['violations']:
 if v['type']!='track_width':continue
 uid=v['items'][0]['uuid'];t=ts[uid];assert not t.IsLocked()and t.GetWidth()<150000
 changed.append({'uuid':uid,'net':t.GetNetname(),'prior_width_nm':t.GetWidth(),'new_width_nm':150000});t.SetWidth(150000)
k.SaveBoard(str(P),b);m['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(m,indent=2)+'\n');(H/'routing/router-width-repair.json').write_text(json.dumps({'input_board_sha256':before,'board_sha256':sha(P),'new_router_necks_only':changed,'native_spacing_DRC_required_next':True},indent=2)+'\n');print(json.dumps(changed))
for gap in d['unconnected_items']:
 print('GAP')
 for row in gap['items']:
  o=ts.get(row['uuid']);print(row['description'],row['pos'])
  if o and not isinstance(o,k.PCB_VIA):print('  ends',[(k.ToMM(p.x),k.ToMM(p.y))for p in(o.GetStart(),o.GetEnd())],'locked',o.IsLocked())
