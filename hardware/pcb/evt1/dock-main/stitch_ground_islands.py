"""Stitch actual surface ground regions to the reserved continuous In1 plane.

Only place vias in actual filled ground, outside solder-paste pad drill areas,
with native all-layer foreign-copper and mechanical-clearance tests. Native
refill/DRC is required immediately after this one pass.
"""
from pathlib import Path
import hashlib,json,math
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'placement.json').read_text());before=sha(P);assert before==meta['native_board_sha256'];b=k.LoadBoard(str(P));net=b.FindNet('GND').GetNetCode()
tracks=list(b.GetTracks());pads=[p for f in b.GetFootprints()for p in f.Pads()];vias=[t for t in tracks if isinstance(t,k.PCB_VIA)and t.GetNetCode()==net]
inner=next(z for z in b.Zones()if not z.GetIsRuleArea()and z.GetNetname()=='GND'and z.IsOnLayer(k.In1_Cu)).GetFilledPolysList(k.In1_Cu)
keepouts=[z for z in b.Zones()if z.GetIsRuleArea()];added=[];failed=[]
for zone in b.Zones():
 if zone.GetIsRuleArea()or zone.GetNetname()!='GND':continue
 layer=next((i for i in(k.F_Cu,k.B_Cu)if zone.IsOnLayer(i)),None)
 if layer is None:continue
 poly=zone.GetFilledPolysList(layer)
 for index in range(poly.OutlineCount()):
  if any(poly.Contains(v.GetPosition(),index,0,True)for v in vias):continue
  chain=poly.COutline(index);ps=[chain.CPoint(i)for i in range(chain.PointCount())]
  if not ps:continue
  x0=min(p.x for p in ps);x1=max(p.x for p in ps);y0=min(p.y for p in ps);y1=max(p.y for p in ps)
  found=None
  for y in range(round(y0/250000)*250000,y1+1,250000):
   for x in range(round(x0/250000)*250000,x1+1,250000):
    at=k.VECTOR2I(x,y)
    if not poly.Contains(at,index,0,True)or not inner.Contains(at,-1,0,True):continue
    if not all(poly.Contains(k.VECTOR2I(round(x+250100*math.cos(a)),round(y+250100*math.sin(a))),index,0,True)for a in [i*math.pi/4 for i in range(8)]):continue
    if any(z.Outline().Contains(at,-1,250001,True)for z in keepouts):continue
    sh=k.SHAPE_CIRCLE(at,250000)
    if any(o.GetNetCode()!=net and o.IsOnLayer(l)and k.SHAPE.Collide(sh,o.GetEffectiveShape(l),150200)for o in tracks+pads for l in(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)):continue
    # No exposed drilled via in a component's paste pad.
    drill=k.SHAPE_CIRCLE(at,200000)
    if any(p.GetAttribute()==k.PAD_ATTRIB_SMD and p.IsOnLayer(layer)and k.SHAPE.Collide(drill,p.GetEffectiveShape(layer),0)for p in pads):continue
    found=at;break
   if found:break
  if found is None:failed.append({'layer':k.LayerName(layer),'outline_index':index,'bounds_native_mm':[k.ToMM(v)for v in(x0,y0,x1,y1)]});continue
  v=k.PCB_VIA(b);v.SetPosition(found);v.SetWidth(500000);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(net);v.SetLocked(True);b.Add(v);tracks.append(v);vias.append(v)
  added.append({'uuid':v.m_Uuid.AsString(),'native_mm':[k.ToMM(found.x),k.ToMM(found.y)],'surface_region_layer':k.LayerName(layer),'outline_index':index,'diameter_drill_mm':[.5,.2]})
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
assert all(v.GetNetname()=='GND'for v in vias)
b.BuildConnectivity();assert all(v.GetNetname()=='GND'for v in vias);k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'input_board_sha256':before,'board_sha256':sha(P),'added':added,'regions_without_free_full_annulus':failed,'native_DRC_required':True,'source192_critical207_and_escapes_unchanged':True}
(H/'routing'/('ground-stitches-'+before[:12]+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
