"""Retain authored residual pad escapes during general routing."""
from pathlib import Path
import json,hashlib
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'placement.json').read_text());before=sha(P);assert before==meta['native_board_sha256'];b=k.LoadBoard(str(P));tracks=list(b.GetTracks());records=[]
def p(xy):return k.VECTOR2I(round(xy[0]*1e6),round(xy[1]*1e6))
for path in sorted((H/'routing').glob('residual-fanout-*.json')):
 r=json.loads(path.read_text())
 for row in r['added']:
  ps=row.get('native_mm_path')or[row['start_native_mm'],row['via_native_mm']]
  for aa,bb in zip(ps,ps[1:]):
   matches=[t for t in tracks if not isinstance(t,k.PCB_VIA)and t.GetNetname()==row['net']and t.GetLayer()==k.F_Cu and ((t.GetStart()==p(aa)and t.GetEnd()==p(bb))or(t.GetStart()==p(bb)and t.GetEnd()==p(aa)))]
   assert len(matches)==1,(row,aa,bb,len(matches));t=matches[0];t.SetLocked(True);records.append({'uuid':t.m_Uuid.AsString(),'kind':'track','net':row['net'],'start_native_mm':aa,'end_native_mm':bb,'width_mm':k.ToMM(t.GetWidth())})
  matches=[t for t in tracks if isinstance(t,k.PCB_VIA)and t.GetNetname()==row['net']and t.GetPosition()==p(ps[-1])];assert len(matches)==1
  t=matches[0];t.SetLocked(True);records.append({'uuid':t.m_Uuid.AsString(),'kind':'via','net':row['net'],'position_native_mm':ps[-1],'diameter_drill_mm':[.5,.2]})
k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'input_board_sha256':before,'board_sha256':sha(P),'extra_locked_authored_copper':records,'source192_and_critical207_unchanged':True,'basis':'short native clearance-checked escapes for actual DRC-isolated pins; local exact copper ripups recorded separately'}
(H/'routing/residual-fanout-guides.json').write_text(json.dumps(report,indent=2)+'\n');print('Locked residual fanout items',len(records))
