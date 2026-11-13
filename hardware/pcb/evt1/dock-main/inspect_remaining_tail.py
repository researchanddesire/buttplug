"""Read-only exact residual-net geometry for independent repair review."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';before=hashlib.sha256(P.read_bytes()).hexdigest();b=k.LoadBoard(str(P));net='LOOP_A_RAW';items=[];lookup={}
for f in b.GetFootprints():
 for p in f.Pads():
  if p.GetNetname()==net:lookup[p.m_Uuid.AsString()]=f.GetReference()+'.'+p.GetNumber();items.append(p)
items+=list(t for t in b.GetTracks()if t.GetNetname()==net)
def xy(p):return [k.ToMM(p.x),k.ToMM(p.y)]
rows=[];layers=(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)
for o in items:
 row={'uuid':o.m_Uuid.AsString(),'type':'pad'if isinstance(o,k.PAD)else('via'if isinstance(o,k.PCB_VIA)else'track'),'locked':o.IsLocked(),'label':lookup.get(o.m_Uuid.AsString()),'layers':[k.LayerName(l)for l in layers if o.IsOnLayer(l)]}
 if isinstance(o,k.PCB_TRACK)and not isinstance(o,k.PCB_VIA):row.update(start_native_mm=xy(o.GetStart()),end_native_mm=xy(o.GetEnd()),width_mm=k.ToMM(o.GetWidth()),length_mm=k.ToMM(o.GetLength()))
 else:row['position_native_mm']=xy(o.GetPosition())
 row['neighbours']=[p.m_Uuid.AsString()for p in items if p.m_Uuid.AsString()!=o.m_Uuid.AsString()and any(o.IsOnLayer(l)and p.IsOnLayer(l)and k.SHAPE.Collide(o.GetEffectiveShape(l),p.GetEffectiveShape(l),0)for l in layers)]
 rows.append(row)
assert before==hashlib.sha256(P.read_bytes()).hexdigest()
report={'status':'read-only inspection, no PCB mutation','board_sha256':before,'net':net,'native_DRC_findings':json.loads((H/'drc.json').read_text())['violations'],'items':rows,'protected_source_or_main_critical_records':[r for file in('source-block/placement.json','critical-routing.json')for r in json.loads((H/file).read_text())['critical_copper']if r['net']==net]}
(H/'routing/remaining-tail-inspection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
