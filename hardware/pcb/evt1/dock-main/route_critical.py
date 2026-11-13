"""Intentional clock, bypass/ADC, power-cut and reference routing on ONE base.

Preserves every source-block copper item. Run one native BOARD per process.
The router may later complete only unlocked/general copper on F/B surfaces.
"""
from pathlib import Path
import argparse,hashlib,json,math,shutil
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent
P=H/'dock-main.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,y):return k.VECTOR2I(round((100+x)*1e6),round((200-y)*1e6))
def dock(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--restart-critical',action='store_true');a=ap.parse_args()
 meta=json.loads((H/'placement.json').read_text());assert sha(P)==meta['native_board_sha256']
 folder=H/'routing';folder.mkdir(exist_ok=True);seed=folder/'before-critical.kicad_pcb'
 if meta.get('routing_started'):
  last=json.loads((H/'critical-routing.json').read_text())
  assert a.restart_critical and not meta.get('general_routing_imported') and sha(P)==last['board_sha256']
  assert sha(seed)==last['seed_sha256'];shutil.copyfile(seed,P)
 else:
  assert not seed.exists(),'Preserve existing routing seed rather than silently replacing it'
  shutil.copyfile(P,seed)
 b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()}
 source=json.loads((H/'source-block/placement.json').read_text())
 frozen=set(source['frozen_references'])
 moves={'C208':(-30.5,36.1,180),'C209':(-27.5,36.1,0),
        'C210':(-4,42,0),'C614':(35.8,44.3,0),'C616':(16.6,46,0),
        'R606':(20,46,0),'C606':(18,39,270),'C608':(15.6,37.8,0),
        'C602':(37,28.95,180),'R616':(41,24.5,0),'C620':(25,29.5,0)}
 for r,pos in moves.items():
  assert r not in frozen;f=fps[r];f.SetPosition(xy(*pos[:2]));f.SetOrientationDegrees(pos[2])
  meta['footprint_placements_dock_xy_native_angle'][r]=list(pos)
 # Root-authorized relocation of the new, unmanufactured rear support.
 # Both original GH headers remain at their previously audited placements.
 f=fps['H706'];old=dock(f.GetPosition());target=[44,55.7]
 if old!=target:
  assert old==[44,57];delta=xy(*target)-f.GetPosition();f.SetPosition(xy(*target))
  moved=0
  for zone in b.Zones():
   if zone.GetIsRuleArea() and dock(zone.GetBoundingBox().GetCenter())==[44,57]:
    zone.Move(delta);moved+=1
  assert moved==2,('rear support keepout count',moved)
 for row in meta['mounting_holes_dock_xy_d_mm']:
  if row[:2]in([44,57],[44,56.2]):row[1]=55.7
 def pad(r,n):return next(p for p in fps[r].Pads()if p.GetNumber()==n)
 def at(r,n):return dock(pad(r,n).GetPosition())
 records=[]
 def track(net,points,width=.2,layer=k.F_Cu,role='local'):
  for x,y in zip(points,points[1:]):
   if x==y:continue
   t=k.PCB_TRACK(b);t.SetStart(xy(*x));t.SetEnd(xy(*y));t.SetWidth(k.FromMM(width))
   t.SetLayer(layer);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
   records.append({'kind':'track','net':net,'start':x,'end':y,'width':width,'layer':k.LayerName(layer),'role':role})
 def join(r,n,s,m,points=(),width=.2,role='local'):
  net=pad(r,n).GetNetname();assert net==pad(s,m).GetNetname()
  track(net,[at(r,n),*points,at(s,m)],width,role=role)
 def via(net,p,role='local'):
  v=k.PCB_VIA(b);v.SetPosition(xy(*p));v.SetWidth(k.FromMM(.5));v.SetDrill(k.FromMM(.2))
  v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
  records.append({'kind':'via','net':net,'position':p,'diameter':.5,'drill':.2,'role':role})
 def access(r,n,p,width=.2,role='reference'):
  net=pad(r,n).GetNetname();track(net,[at(r,n),p],width,role=role);via(net,p,role)
 # Local edge-conditioned physical clocks: no long shared route or MCU edge.
 join('U614','6','U609','3',((34.7,45.7),(34.7,46.6),(29,46.6),(28.7,46.9),(28.7,50.65)),role='physical release clock')
 join('U614','4','U609','11',((34.7,42.9),(37.3,42.9),(38,43.6),(38,50)),role='physical press clock')
 # Four distinct LQFP VDD bypass loops; keep each path next to its own pin.
 join('U201','48','C201','1',((-31.75,49.32),),.2,'MCU VDD48 bypass')
 join('U201','1','C202','1',((-34.4,45.75),(-34.88,45.27)),.2,'MCU VDD1 bypass')
 join('U201','24','C203','1',((-26.25,37.75),(-25.8,37.3)),.2,'MCU VDD24 bypass')
 join('U201','36','C204','1',((-23.7,45.75),(-23.22,45.27)),.2,'MCU VDD36 bypass')
 join('U201','9','C205','1',((-34.4,41.75),(-34.875,42.225)),.2,'MCU VDDA bypass')
 join('C205','1','C206','1',width=.3,role='analog supply bulk')
 join('U202','8','C210','1',width=.2,role='ADS local bypass')
 # Filter capacitor signal faces the MCU, with the ground pad outside the
 # direct path. ADC input traces remain short after the1k series resistors.
 join('U201','18','C208','1',((-29.25,36.87),),.15,'NTC base filtered ADC')
 join('U201','19','C209','1',((-28.75,36.87),),.15,'NTC lid filtered ADC')
 join('R220','2','C208','1',width=.2,role='NTC base filter source')
 join('R221','2','C209','1',width=.2,role='NTC lid filter source')
 # Intentional safety bypass paths, not a bank of distant supply capacitors.
 join('U614','5','C614','1',width=.3,role='clock buffer bypass')
 join('U609','14','C609','1',((35.8625,52.8),),.3,'physical latch bypass')
 join('U612','14','C612','1',((25.8625,52.8),),.3,'safety AND bypass')
 join('U615','14','C615','1',((45.7,51.95),),.3,'permission AND bypass')
 join('U616','5','C616','1',width=.3,role='delay supervisor bypass')
 join('U606','1','C606','1',((18.8,39.975),),.2,'watchdog bypass')
 join('U607','3','C607','1',width=.2,role='3V3 supervisor bypass')
 join('U608','4','C608','1',width=.2,role='physical debounce bypass')
 join('U613','5','C613','1',((43,38),),.2,'loop buffer bypass')
 join('U602','1','C602','1',width=.3,role='contact loop switch bypass')
 # Switch power pins use0.4mm necks (0.175mm nominal adjacent-pad spacing)
 # before broad copper. No0.8mm track is forced through the fine pad pitch.
 track('UV_5V_LIMITED',[at('J103','2'),(23.5,28),(25.8,28)],1.2,role='UV cut input trunk')
 track('UV_5V_LIMITED',[(25.8,28),at('U610','2')],.4,role='cut A input neck')
 track('UV_5V_LIMITED',[(24.52,28),at('C620','1')],.4,role='cut A input capacitor')
 track('UV_5V_MID',[at('U610','6'),(29.4,28)],.4,role='cut A output neck')
 track('UV_5V_MID',[(29.4,28),(29.6,28)],1.0,role='two cut local link')
 track('UV_5V_MID',[(29.6,28),at('U611','2')],.4,role='cut B input neck')
 track('UV_5V_MID',[(29.2,28),(29.2,30.5),at('C621','1')],.3,role='cut intermediate capacitor')
 track('UV_5V_SW',[at('U611','6'),(32.7,28)],.4,role='cut B output neck')
 for point in ((32.7,27.8),(32.7,28.6)):
  track('UV_5V_SW',[(32.7,28),point],.5,role='postcut parallel stitching');via('UV_5V_SW',point,'postcut parallel stitching')
 track('UV_5V_SW',[(32.7,27.8),at('C622','1')],.5,role='postcut capacitor')
 for r,p in [('U610',(26.8,29)),('U611',(30.4,29.6))]:
  track('HOST_5V',[at(r,'1'),(p[0],28.5),p],.15,role='cut bias power');via('HOST_5V',p,'cut bias power')
 access('C610','1',(27.7,25),.3,'cut A bias bypass')
 access('C611','1',(30.1,24),.3,'cut B bias bypass')
 track('GND',[at('U610','4'),(28,26.8),(27,26.8)],.2,role='cut A solid ground')
 via('GND',(27,26.8),'cut A solid ground')
 access('U611','4',(31,26),.2,'cut B solid ground')
 # Board sourceESD VBUS tied to its nearby inner power reference directly;
 # the source pair/convergence prevents a wide surface trace through here.
 access('U121','5',(0,12.85),.3,'ESD VBUS inner access')
 # Explicit low-current3V3 link from the LDO to the controller/safety plane.
 access('C105','1',(-21,3.5),.4,'LDO3V3 access')
 track('3V3',[(-21,3.5),(-22.2,5),(-22.2,15.5),(-20.5,17.2),(-20.5,24.5),(-22,26),(-24,28),(-24,32)],.5,k.B_Cu,'3V3 trunk')
 via('3V3',(-24,32),'3V3 plane entry')
 # Parallel branch power/return stitches beneath the header body. The rear
 # support moved instead of altering either established header/harness datum.
 for r,ys in [('J621',(58.0,58.6)),('J622',(61.3,61.9))]:
  for n in ('1','2'):
   net=pad(r,n).GetNetname();x=at(r,n)[0]
   track(net,[at(r,n),(x,ys[0]),(x,ys[1])],.6,role='UV branch parallel stitching')
   for y in ys:via(net,(x,y),'UV branch parallel stitching')
 # Local reference vias are selected by native copper collision checks.
 # They avoid foreign pads/tracks on every layer, NPTHs and all six head
 # reservations. The connected surface stub is checked too.
 boardpads=[p for f in b.GetFootprints()for p in f.Pads()]
 def legal_ground(seed,p):
  for x,y,d in meta['mounting_holes_dock_xy_d_mm']:
   if math.hypot(x-p[0],y-p[1])<3.3:return False
  if not(-46.5<p[0]<46.5 and 2<p[1]<66.5):return False
  for x,y in [(-43,19),(-15,19)]:
   if x-4.6<p[0]<x+4.6 and y-4.6<p[1]<y+4.6:return False
  c=k.SHAPE_CIRCLE(xy(*p),k.FromMM(.25));stub=k.SHAPE_SEGMENT(seed.GetPosition(),xy(*p),k.FromMM(.2))
  for q in boardpads:
   if q.GetNetname()=='GND':continue
   for layer in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu):
    if not q.IsOnLayer(layer):continue
    sh=q.GetEffectiveShape(layer)
    if sh.Collide(c,k.FromMM(.205))or(layer==k.F_Cu and sh.Collide(stub,k.FromMM(.155))):return False
  for q in b.GetTracks():
   if isinstance(q,k.PCB_VIA):
    qp=dock(q.GetPosition())
    if math.hypot(qp[0]-p[0],qp[1]-p[1])<.46:return False
   if q.GetNetname()=='GND':continue
   layer=q.GetLayer();sh=q.GetEffectiveShape()
   if sh.Collide(c,k.FromMM(.205))or(layer==k.F_Cu and sh.Collide(stub,k.FromMM(.155))):return False
  return True
 ground_results=[]
 # Known body-side MCU vias keep analog and VDD escapes separate.
 for n,p in [('8',(-31.9,42.25)),('23',(-26.75,40.2)),('35',(-26.1,45.25)),('47',(-31.25,45.8))]:
  assert legal_ground(pad('U201',n),p),('MCU ground clearance',n,p)
  access('U201',n,p,.2,'MCU local reference');ground_results.append(['U201',n,p])
 requests=[]
 for r,f in sorted(fps.items()):
  if r in frozen or not r.startswith(('C','U'))or r=='U201'or r in ('U610','U611'):continue
  for q in f.Pads():
   if q.GetNetname()=='GND' and q.GetNumber():requests.append((r,q))
 for r,q in requests:
  p0=dock(q.GetPosition());centre=dock(fps[r].GetPosition())
  theta=math.atan2(p0[1]-centre[1],p0[0]-centre[0]);chosen=None
  for length in (.8,1.0,1.2,1.5,1.8,2.2):
   for a0 in (0,math.pi,math.pi/2,-math.pi/2,math.pi/4,-math.pi/4,3*math.pi/4,-3*math.pi/4):
    p=[round(p0[0]+length*math.cos(theta+a0),6),round(p0[1]+length*math.sin(theta+a0),6)]
    if legal_ground(q,p):chosen=p;break
   if chosen:break
  assert chosen,('No clear local ground via',r,q.GetNumber(),p0)
  access(r,q.GetNumber(),chosen,.2,'local bypass/reference');ground_results.append([r,q.GetNumber(),chosen])
 # Separated inner power regions, in addition to continuous In1 ground.
 def power_plane(net,points):
  z=k.ZONE(b);z.SetLayer(k.In2_Cu);z.SetNet(b.FindNet(net));z.SetLocalClearance(k.FromMM(.2))
  z.SetMinThickness(k.FromMM(.2));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
  z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS);p=z.Outline();p.NewOutline()
  for x,y in points:q=xy(x,y);p.Append(q.x,q.y)
  b.Add(z)
 power_plane('HOST_5V',[(-40,2.7),(-5,2.7),(-5,-3.3),(5,-3.3),(5,2.7),(25,2.7),(36,10),(45,18),(45,25.5),(31.6,25.5),(31.6,30.5),(22,30.5),(22,25.5),(-40,25.5)])
 power_plane('UV_5V_SW',[(32.1,26.5),(47.2,26.5),(47.2,64.5),(28.8,64.5),(28.8,57),(32.1,57)])
 power_plane('3V3',[(-47,31),(13,31),(13,31.2),(31.4,31.2),(31.4,56.5),(28.2,56.5),(28.2,67),(-44.5,67),(-47,64)])
 k.SaveBoard(str(P),b)
 meta['native_board_sha256']=sha(P);meta['routing_started']=True;meta['general_routing_imported']=False
 meta['critical_routing_records']=len(records);meta['ground_reference_filled']=False
 (H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
 report={'status':'intentional native critical copper candidate; native DRC pending',
 'seed_sha256':sha(seed),'board_sha256':sha(P),'source192_preserved':True,'source_block_sha256':meta['source_block_sha256'],
 'component_adjustments_dock_xy_native_angle':moves,'critical_copper':records,'local_ground_vias':ground_results,
 'new_rear_support_dock_xy_mm':[44,55.7],'original_header_positions_preserved':True,
 'reserved_reference':'In1 GND; In2 separated HOST/UV_SW/3V3; general signals F/B only',
 'power_resistance_qualified':False,'physical_or_powered_result':False}
 (H/'critical-routing.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'added_locked_items':len(records),'local_reference_vias':len(ground_results),'adjusted_parts':len(moves)}))
if __name__=='__main__':main()
