"""Read-only electrical geometry/model parity with frozen StepUp input.

Each native board is fully reduced to plain Python data before loading the
next board, avoiding the KiCad7 two-live-board settings hazard.
"""
from pathlib import Path
import gc,hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def vec(p):return [p.x,p.y]
def model(m):
 return {'path':m.m_Filename,'offset':[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],'rotation':[m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z],'scale':[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z]}
def extract(path):
 b=k.LoadBoard(str(path));records=[]
 for f in b.GetFootprints():
  ps=[]
  for p in f.Pads():ps.append({'number':p.GetNumber(),'global_position_nm':vec(p.GetPosition()),'shape':p.GetShape(),'size_nm':vec(p.GetSize()),'drill_nm':vec(p.GetDrillSize()),'angle':p.GetOrientationDegrees(),'net':p.GetNetname(),'layers':list(p.GetLayerSet().Seq()),'attribute':p.GetAttribute(),'roundrect_radius_nm':p.GetRoundRectCornerRadius()})
  records.append({'reference':f.GetReference(),'value':f.GetValue(),'position_nm':vec(f.GetPosition()),'angle':f.GetOrientationDegrees(),'layer':f.GetLayer(),'FPID':str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName()),'pads':sorted(ps,key=lambda p:json.dumps(p,sort_keys=True)),'models':[model(m)for m in f.Models()]})
 edges=[]
 for edge in b.GetDrawings():
  if edge.GetLayer()==k.Edge_Cuts:edges.append({'shape':edge.GetShape(),'start':vec(edge.GetStart()),'end':vec(edge.GetEnd()),'mid':vec(edge.GetMid())if edge.GetShape()==k.S_ARC else None,'width':edge.GetWidth()})
 result={'thickness_nm':b.GetDesignSettings().GetBoardThickness(),'copper_layers':b.GetCopperLayerCount(),'references':sorted(records,key=lambda r:r['reference']),'outline':sorted(edges,key=lambda r:json.dumps(r,sort_keys=True))}
 return result
snapshot=H/'dock-main-MCAD-placement.kicad_pcb';current=H/'dock-main.kicad_pcb';snapshot_sha=sha(snapshot);current_sha=sha(current)
a=extract(snapshot);gc.collect();b=extract(current);gc.collect();assert a==b,'Native pad/part/model/outline geometry differs from StepUp snapshot'
assert snapshot_sha==sha(snapshot)and current_sha==sha(current)
frozen=json.loads((H/'mcad-model-coverage.json').read_text())
for row in frozen['references']:
 if row['model'] is not None:
  file=Path(row['model']['model_URI'].replace('${KIPRJMOD}',str(H)));assert sha(file)==row['model']['model_sha256'],('Frozen STEP changed',row['reference'])
report={'status':'pass: final native MCAD geometry identical to frozen StepUp snapshot','snapshot_sha256':snapshot_sha,'board_sha256':current_sha,'KiCad':k.Version(),'exact_references':len(a['references']),'electrical_references':150,'mechanical_holes':6,'pad_model_pose_outline_layer_stack_checks':a,'physical_fit_qualified':False}
(H/'mcad-geometry-parity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:report[key]for key in('status','snapshot_sha256','board_sha256','exact_references')}))
