"""Native checked straight escapes for actual DRC-isolated fine/edge pads.

Only adds copper. Native DRC/refill and source conservation remain required.
This guides the remaining cross-board search without moving selected parts.
"""
from pathlib import Path
import argparse,json,math,hashlib
ap=argparse.ArgumentParser();ap.add_argument("--ripup-unlocked",action="store_true");args=ap.parse_args()
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'placement.json').read_text());before=sha(P);assert before==meta['native_board_sha256']
b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()};tracks=list(b.GetTracks());pads=[p for f in fps.values()for p in f.Pads()]
drc=json.loads((H/'drc.json').read_text());wanted=set()
for gap in drc['unconnected_items']:
 for item in gap['items']:
  if item['description'].startswith('Pad '):
   import re
   m=re.match(r'Pad (\S+) \[.*\] of (\S+) on',item['description']);wanted.add((m[2],m[1]))
clear=150200;width=150000;vd=500000
rips=set();removed=[]
holes=[k.VECTOR2I(round((100+x)*1e6),round((200-y)*1e6))for x,y,d in meta['mounting_holes_dock_xy_d_mm']]
outline=meta['outline_dock_xy_mm']
def inside(p):
 x=k.ToMM(p.x)-100;y=200-k.ToMM(p.y);hit=False
 for(a,c)in zip(outline,outline[1:]+outline[:1]):
  if(a[1]>y)!=(c[1]>y) and x<(c[0]-a[0])*(y-a[1])/(c[1]-a[1])+a[0]:hit=not hit
 return hit
zones=[z for z in b.Zones()if z.GetIsRuleArea()]
def free_shape(shape,net,layer):
 for other in tracks+pads:
  if other.GetNetCode()==net or not other.IsOnLayer(layer):continue
  if k.SHAPE.Collide(shape,other.GetEffectiveShape(layer),clear):
   if args.ripup_unlocked and isinstance(other,k.PCB_TRACK)and not other.IsLocked():rips.add(other.m_Uuid.AsString());continue
   return False
 for h in holes:
  if k.SHAPE.Collide(shape,k.SHAPE_CIRCLE(h,3000000),0):return False
 return True
def free_via(at,net):
 shape=k.SHAPE_CIRCLE(at,vd//2)
 if not inside(at):return False
 for layer in(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu):
  if not free_shape(shape,net,layer):return False
 for z in zones:
  if z.Outline().Contains(at,-1,300000,True):return False
 return True
added=[];failed=[]
for ref,num in sorted(wanted):
 f=fps[ref];p=next(p for p in f.Pads()if p.GetNumber()==num);net=p.GetNetCode();at=p.GetPosition()
 # Already has an escape into a through-via: do not add needless duplicate escapes.
 own=[t for t in tracks if t.GetNetCode()==net and isinstance(t,k.PCB_VIA)and (t.GetPosition()-at).EuclideanNorm()<=1500000]
 if own:continue
 dx=at.x-f.GetPosition().x;dy=at.y-f.GetPosition().y
 if abs(dx)>abs(dy):sx=1 if dx>0 else-1;sy=0
 else:sx=0;sy=1 if dy>0 else-1
 success=False
 paths=[]
 if (ref,num)==('U103','11'):
  paths.append([at,k.VECTOR2I(84800000,191150000),k.VECTOR2I(84200000,190550000)])
 for ex,ey in((sx,sy),(-sy,sx),(sy,-sx),(-sx,-sy)):
  for distance in(.5,.7,.9,1.1,1.35,1.6,2.0,2.5,3.0):paths.append([at,k.VECTOR2I(at.x+round(ex*distance*1e6),at.y+round(ey*distance*1e6))])
  for exit in(.3,.45,.65,.85,1.1):
   for lateral in(.4,-.4,.7,-.7,1.,-1.,1.4,-1.4,2.,-2.):
    mid=k.VECTOR2I(at.x+round(ex*exit*1e6),at.y+round(ey*exit*1e6))
    paths.append([at,mid,k.VECTOR2I(mid.x+round(-ey*lateral*1e6),mid.y+round(ex*lateral*1e6))])
 for path in paths:
  rips=set()
  end=path[-1]
  if not inside(end)or not free_via(end,net):continue
  if any(not free_shape(k.SHAPE_SEGMENT(aa,bb,width),net,k.F_Cu)for aa,bb in zip(path,path[1:])):continue
  blocked=False
  for aa,bb in zip(path,path[1:]):
   for i in range(11):
    q=k.VECTOR2I(round(aa.x+(bb.x-aa.x)*i/10),round(aa.y+(bb.y-aa.y)*i/10))
    if any(z.Outline().Contains(q,-1,150000,True)for z in zones):blocked=True;break
  if blocked:continue
  to_remove=[t for t in tracks if t.m_Uuid.AsString()in rips]
  tracks=[t for t in tracks if t.m_Uuid.AsString()not in rips]
  for old in to_remove:
   assert not old.IsLocked();removed.append({'uuid':old.m_Uuid.AsString(),'net':old.GetNetname(),'kind':'via'if isinstance(old,k.PCB_VIA)else'track'});b.Delete(old)
  for aa,bb in zip(path,path[1:]):
   t=k.PCB_TRACK(b);t.SetStart(aa);t.SetEnd(bb);t.SetLayer(k.F_Cu);t.SetWidth(width);t.SetNetCode(net);b.Add(t);tracks.append(t)
  v=k.PCB_VIA(b);v.SetPosition(end);v.SetWidth(vd);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(net);b.Add(v);tracks.append(v)
  added.append({'ref':ref,'pad':num,'net':p.GetNetname(),'native_mm_path':[[k.ToMM(v.x),k.ToMM(v.y)]for v in path],'track_width_mm':k.ToMM(width),'via_diameter_drill_mm':[.5,.2]});success=True;break
 if not success:failed.append([ref,num,p.GetNetname()])
b.BuildConnectivity();k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'input_board_sha256':before,'input_DRC_sha256':sha(H/'drc.json'),'output_board_sha256':sha(P),'added':added,'no_direct_free_escape':failed,'physical_DRC_clearance_test_mm':.1502,'native_DRC_required':True,'protected_copper_mutated':0,'bounded_unlocked_ripup':removed,'ripup_option_explicit':args.ripup_unlocked}
(H/'routing'/('residual-fanout-'+before[:12]+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
