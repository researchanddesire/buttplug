"""Native lid-only route exchange. Run one action per KiCad7 Python process.

Audited source, placement and circuit stay read-only. Local LCD pump/bypass
copper is authored explicitly; only the remaining nets use the offline router.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math,re,shutil,sys
HERE=Path(__file__).resolve().parent
OUT=HERE/'routed-lid'
sys.path.insert(0,str(HERE.parents[3]/'tools'))
import wx
APP=wx.App(False)
import pcbnew as k
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BOARD=OUT/'dock-lid-routed.kicad_pcb'
SEED=OUT/'lcd-local-seed.kicad_pcb'
LAYERS={'F.Cu':k.F_Cu,'In2.Cu':k.In2_Cu,'B.Cu':k.B_Cu}
MOUNTS={'H301':(-30,65),'H302':(30,65),'H303':(-32,115),'H304':(32,105)}
PASSIVES={
 'C301':(-11,117.3,90),'C302':(-9.5,117.3,90),'C303':(-8,117.3,90),
 'C304':(-6.5,117.3,90),'C305':(-5,117.3,90),
 'C306':(-3.5,111.2,90),'C307':(-1,111.2,90),
 'C308':(1.5,111.2,90),'C309':(4,111.2,90),
 'C310':(8,115.6,90),'C311':(1,117.4,0),
 'R301':(12,110,90),'R302':(15,110,90),'R303':(12,106,90),
 'R304':(15,106,90),
 **{'R'+str(305+i):(12+3*(i%2),102-3*(i//2),90)for i in range(8)},
}
def xy(x,y):return k.VECTOR2I(k.FromMM(100+x),k.FromMM(200-y))
def mech(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
def write(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
def record(t,b):
 if isinstance(t,k.PCB_VIA):return{'kind':'via','net':t.GetNetname(),'xy':mech(t.GetPosition()),'diameter':round(k.ToMM(t.GetWidth()),6),'drill':round(k.ToMM(t.GetDrillValue()),6)}
 return{'kind':'track','net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'start':mech(t.GetStart()),'end':mech(t.GetEnd()),'width':round(k.ToMM(t.GetWidth()),6)}
def tracks(b):
 return[record(t,b)for t in b.GetTracks()]
def pad_side(p):
 if p.GetAttribute()==k.PAD_ATTRIB_NPTH:return'NPTH through'
 return'B.Cu'if p.GetLayerSet().Contains(k.B_Cu)else'F.Cu'
def signature(row):
 if row['kind']=='via':return ('via',row['net'],tuple(row['xy']),row['diameter'],row['drill'])
 return ('track',row['net'],row['layer'],tuple(sorted([tuple(row['start']),tuple(row['end'])])),row['width'])
def line(b,net,points,layer=k.F_Cu,width=.15,lock=True):
 for a,c in zip(points,points[1:]):
  if a==c:continue
  t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*c));t.SetWidth(k.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));t.SetLocked(lock);b.Add(t)
def via(b,net,point,diameter=.45,drill=.2,lock=True):
 v=k.PCB_VIA(b);v.SetPosition(xy(*point));v.SetWidth(k.FromMM(diameter));v.SetDrill(k.FromMM(drill));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(lock);b.Add(v)
def pad(fps,ref,n):return next(p for p in fps[ref].Pads()if p.GetNumber()==str(n))
def pos(fps,ref,n):return mech(pad(fps,ref,n).GetPosition())
def save(b,path=BOARD):
 d=b.GetDesignSettings();d.SetBoardThickness(k.FromMM(1));d.m_MinClearance=k.FromMM(.1);d.m_TrackMinWidth=k.FromMM(.15);d.m_HoleClearance=k.FromMM(.2);d.m_CopperEdgeClearance=k.FromMM(.3);d.m_MinThroughDrill=k.FromMM(.2);d.m_ViasMinSize=k.FromMM(.45)
 default=d.m_NetSettings.m_DefaultNetClass;default.SetClearance(k.FromMM(.1));default.SetTrackWidth(k.FromMM(.15));default.SetViaDiameter(k.FromMM(.45));default.SetViaDrill(k.FromMM(.2))
 k.SaveBoard(str(path),b)
 # KiCad7's Models() iterator exposes value copies on this build. Rebase the
 # persisted metadata too; no geometry/placements/copper are changed here.
 text=path.read_text();rebased=text.replace('${KIPRJMOD}/DockControl.3dshapes/','${KIPRJMOD}/../DockControl.3dshapes/')
 if rebased!=text:path.write_text(rebased)
def source_guard():
 report=json.loads((HERE/'native-checks.json').read_text())
 for p,want in report['source_sha256'].items():assert sha(HERE/p)==want,('Stale circuit check',p)
 placement=HERE/'dock-lid-placement.kicad_pcb';pr=json.loads((HERE/'dock-lid-placement.json').read_text());assert sha(placement)==pr['native_board_sha256']
 return placement
def setup_libraries(b):
 local=OUT/'DockControl.pretty';local.mkdir(exist_ok=True)
 needed={str(fp.GetFPID().GetLibItemName())for fp in b.GetFootprints()}
 for f in HERE.glob('DockControl.pretty/*.kicad_mod'):
  if f.stem not in needed:continue
  t=f.read_text().replace('${KIPRJMOD}/DockControl.3dshapes/','${KIPRJMOD}/../DockControl.3dshapes/')
  (local/f.name).write_text(t)
 for fp in b.GetFootprints():
  # Match the derived local footprint snapshot exactly, including model path.
  for model in fp.Models():model.m_Filename=model.m_Filename.replace('${KIPRJMOD}/DockControl.3dshapes/','${KIPRJMOD}/../DockControl.3dshapes/')
 (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "DockControl") (type "KiCad") (uri "${KIPRJMOD}/DockControl.pretty") (options "") (descr "Derived selected lid footprints; local relative model paths")))\n')
 name='MountingHole_2.3mm_M2_R3_Hardware'
 text=f'''(footprint "{name}"(version 20221018)(generator route_lid)(layer "F.Cu")(attr exclude_from_pos_files exclude_from_bom)
 (fp_text reference "REF**"(at 0 -3.6)(layer "F.SilkS")(effects(font(size .8 .8)(thickness .12))))
 (fp_text value "M2 NPTH2.3/R3 hardware"(at 0 3.6)(layer "F.Fab")(effects(font(size .8 .8)(thickness .12))))
 (pad "" np_thru_hole circle(at 0 0)(size 2.3 2.3)(drill 2.3)(layers "*.Cu" "*.Mask"))
 (fp_circle(center 0 0)(end 3 0)(layer "F.CrtYd")(width .05)(fill none))
 (fp_circle(center 0 0)(end 3 0)(layer "B.CrtYd")(width .05)(fill none)))'''
 (local/(name+'.kicad_mod')).write_text(text)
 for ref,p in MOUNTS.items():
  fp=k.FootprintLoad(str(local),name);fp.SetReference(ref);fp.SetValue('M2 NPTH2.3/R3 hardware');fp.SetFPID(k.LIB_ID('DockControl',name));fp.SetPosition(xy(*p));fp.SetLocked(True);fp.Reference().SetVisible(False);fp.Value().SetVisible(False);b.Add(fp)
  z=k.ZONE(b);z.SetIsRuleArea(True);layers=k.LSET()
  for l in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu):layers.AddLayer(l)
  # NPTH pads are allowed inside their own keepout. Both-side R3 courtyards
  # and the separate native pad-to-hardware audit reject component overlap.
  z.SetLayerSet(layers);z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
  poly=z.Outline();poly.NewOutline()
  for i in range(48):
   angle=2*math.pi*i/48;q=xy(p[0]+3*math.cos(angle),p[1]+3*math.sin(angle));poly.Append(q.x,q.y)
  b.Add(z)
def seed():
 placement=source_guard();OUT.mkdir(exist_ok=True)
 assert not BOARD.exists(),'Preserve existing routed output; seed never overwrites a board'
 b=k.LoadBoard(str(placement));b.SetFileName(str(BOARD));b.SetCopperLayerCount(4)
 assert not list(b.GetTracks());setup_libraries(b)
 fps={f.GetReference():f for f in b.GetFootprints()}
 for ref,(x,y,angle)in PASSIVES.items():
  fp=fps[ref]
  if ref.startswith('C'):fp.Flip(fp.GetPosition(),False)
  fp.SetPosition(xy(x,y));fp.SetOrientationDegrees(angle)
  fp.SetLocked(True)
 save(b)
 write('route-floorplan.json',{'source_placement_sha256':sha(placement),'source_XML_sha256':sha(HERE/'dock-lid-ui-native.xml'),'board_seed_sha256':sha(BOARD),'critical_fixed_refs':['J301','J302','S301','S302','S303'],'passive_locations':PASSIVES,'mounts_NPTH2_3mm_R3':MOUNTS,'B_side_components':{r:{'dock_xyz_topUnresolved':p[:2],'case_max_height_mm':1.8 if r in ['C306','C307','C308','C309']else(.55 if r=='C311' else .9),'planned_mounted_clearance_mm':1.95 if r in ['C306','C307','C308','C309']else(.65 if r=='C311' else 1.05)}for r,p in PASSIVES.items()if r.startswith('C')},'height_sources':['https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3216X7R1H225K160AB','https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1E105K080AB','https://www.murata.com/en-global/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno=GRM155R71C104KA88%23'],'pads':{r:[{'n':p.GetNumber(),'net':p.GetNetname(),'xy':mech(p.GetPosition()),'layer':pad_side(p)}for p in f.Pads()]for r,f in fps.items()},'socket_mating_Z_qualified':False,'full_product_order_ready':False})
 print(BOARD)
def plane(b,layer):
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(k.FromMM(.1));z.SetMinThickness(k.FromMM(.15));z.SetPadConnection(k.ZONE_CONNECTION_THERMAL);z.SetThermalReliefGap(k.FromMM(.15));z.SetThermalReliefSpokeWidth(k.FromMM(.2));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
 poly=z.Outline();poly.NewOutline()
 for p in json.loads((HERE/'dock-lid-placement.json').read_text())['outline_dock_xy_mm']:
  q=xy(*p);poly.Append(q.x,q.y)
 b.Add(z)
def local(restart=False):
 source_guard();b=k.LoadBoard(str(BOARD))
 if restart:
  old=json.loads((OUT/'local-copper.json').read_text())
  assert collections.Counter(map(signature,tracks(b)))==collections.Counter(map(signature,old['protected_records'])),'Preserve imported/edited routing before rebuilding the manual seed'
  for t in list(b.GetTracks()):b.Delete(t)
  for z in list(b.Zones()):
   if not z.GetIsRuleArea():b.Delete(z)
 assert not list(b.GetTracks())
 for z in b.Zones():
  if z.GetIsRuleArea()and z.GetLayerSet().Contains(k.In1_Cu):z.SetDoNotAllowPads(False)
 fps={f.GetReference():f for f in b.GetFootprints()}
 # LCD0..4 bypasses: ordered, nested front-side fanout and short B stubs.
 for i,turn,tx in ((1,114.65,-11),(2,114.95,-9.5),(3,115.25,-8),(4,115.55,-6.5)):
  net=pad(fps,'J302',i).GetNetname();p=pos(fps,'J302',i);v=(tx,115.7)
  line(b,net,[p,(p[0],turn),(tx,turn),v]);via(b,net,v)
  line(b,net,[v,pos(fps,'C'+str(300+i),1)],k.B_Cu)
 net='LCD_V4';p=pos(fps,'J302',5);v=(-4,115.85)
 line(b,net,[p,(p[0],115.85),v]);via(b,net,v)
 line(b,net,[v,(-4,116.525),pos(fps,'C305',1)],k.B_Cu)
 for i in range(301,306):
  p=pos(fps,'C'+str(i),2);v=(p[0],119.1)
  line(b,'GND',[p,v],k.B_Cu);via(b,'GND',v)
 # The flying-cap pins escape straight from the actual 0.5mm connector lands.
 pv={}
 for n in range(7,13):
  p=pos(fps,'J302',n);v=(p[0],115 if n%2 else 115.75)
  net=pad(fps,'J302',n).GetNetname();line(b,net,[p,v]);via(b,net,v);pv[n]=v
 line(b,'LCD_C2M',[pv[7],(-4.75,113.75),(-4.75,110.975),pos(fps,'C306',1)],k.B_Cu)
 line(b,'LCD_C2P',[pv[8],(-3,113.175),pos(fps,'C306',2)],k.B_Cu)
 line(b,'LCD_C1P',[pv[9],(-2.5,114.4),(.1,114.4),(.1,110.825),pos(fps,'C307',1)],k.B_Cu)
 # Common C1- is a deliberate, short In2 star to BOTH flying capacitors.
 star=[(-2.25,112.675),(2.75,112.675)]
 line(b,'LCD_C1M',[pv[10],(-2,113),star[0],star[1]],k.In2_Cu)
 for ref,v in zip(('C307','C308'),star):
  via(b,'LCD_C1M',v);line(b,'LCD_C1M',[pos(fps,ref,2),v],k.B_Cu)
 line(b,'LCD_C3P',[pv[11],(.4,115),(.4,110.825),pos(fps,'C308',1)],k.B_Cu)
 # Reservoir positive crosses the common-return star only on a separate layer.
 vout=(5.3,109.725);via(b,'LCD_VOUT',vout)
 line(b,'LCD_VOUT',[pv[12],(6,115.75),(6,109.725),vout],k.In2_Cu)
 line(b,'LCD_VOUT',[vout,pos(fps,'C309',1)],k.B_Cu)
 gv=(5.3,112.675);via(b,'GND',gv);line(b,'GND',[pos(fps,'C309',2),gv],k.B_Cu)
 # Actual 100nF and1uF supply bypasses; read-enable is locally tied high.
 supply=(-.5,116.25);via(b,'3V3_UI',supply)
 line(b,'3V3_UI',[pos(fps,'J302',13),supply])
 line(b,'3V3_UI',[supply,(-.5,117.4),pos(fps,'C311',1)],k.B_Cu)
 bulk=(6.8,114.825);via(b,'3V3_UI',bulk)
 line(b,'3V3_UI',[supply,(6.8,116.25),bulk],k.In2_Cu)
 line(b,'3V3_UI',[bulk,pos(fps,'C310',1)],k.B_Cu)
 line(b,'3V3_UI',[pos(fps,'J302',23),(4.5,114.6),(4.725,114.825),bulk])
 gnd=(.1,116.7);via(b,'GND',gnd);line(b,'GND',[pos(fps,'J302',14),(0,116.6),gnd])
 for ref,v in (('C310',(9.2,116.375)),('C311',(2.15,117.4))):
  via(b,'GND',v);line(b,'GND',[pos(fps,ref,2),v],k.B_Cu)
 # Connect both physical switch terminals of each logical node in copper.
 for ref in ('S301','S302','S303'):
  fp=fps[ref];cx,cy=mech(fp.GetPosition())
  for n in ('1','2'):
   ps=sorted([mech(p.GetPosition())for p in fp.Pads()if p.GetNumber()==n])
   line(b,pad(fps,ref,n).GetNetname(),ps)
  gp=pos(fps,ref,2);v=(cx-5.5,51.75);via(b,'GND',v);line(b,'GND',[gp,v])
 for p in ((-11,112),(11,112),(17,114.4),(33,116),(19,110),(33,110)):
  via(b,'GND',p)
 for l in (k.F_Cu,k.In1_Cu,k.B_Cu):plane(b,l)
 save(b);shutil.copy2(BOARD,SEED)
 write('local-copper.json',{'board_sha256':sha(BOARD),'seed_sha256':sha(SEED),'protected_records':tracks(b),'critical_intent':['V0..4 ordered local bypass fanout and individual ground vias','C2 pair onB; C1+/C3+ onB with commonC1- In2 star','VOUT reservoir path isolated fromcommonreturn bylayer','J302VDD100nF/1uF localbypasses and/RD tie','Allswitchduplicateterminals strapped; independentCENTERnet preserved'],'In1_GND_only':True,'B_side_maximum_mounted_clearance_mm':1.95,'socket_contactheight_qualified':False})
 print('protected local copper',len(list(b.GetTracks())))
def fill():
 b=k.LoadBoard(str(BOARD));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());save(b)
 print('filled',BOARD)
def export():
 source_guard();b=k.LoadBoard(str(BOARD));report=json.loads((OUT/'local-copper.json').read_text())
 protected={signature(r)for r in report['protected_records']};assert protected<={signature(r)for r in tracks(b)}
 for t in b.GetTracks():t.SetLocked(True)
 save(b)
 # Only the reference-plane polygon participates in the routing exchange.
 for z in list(b.Zones()):
  if not z.GetIsRuleArea()and not z.GetLayerSet().Contains(k.In1_Cu):b.Delete(z)
 dsn=BOARD.with_suffix('.dsn');assert k.ExportSpecctraDSN(b,str(dsn));txt=dsn.read_text()
 txt=re.sub(r'(\(layer In1.Cu\s+\(type )signal(\))',r'\1power\2',txt)
 # Planning inset supplements KiCad's 0.1001mm DSN boundary clearance.
 match=re.search(r'\(boundary\s*\(path pcb 0\s+([\d\s.\-]+)\)\s*\)',txt);assert match
 nums=list(map(float,match[1].split()));vs=list(zip(nums[::2],nums[1::2]));assert vs[0]==vs[-1];vs.pop()
 sign=1 if sum(a[0]*c[1]-c[0]*a[1]for a,c in zip(vs,vs[1:]+vs[:1]))>0 else-1;ls=[]
 for p,q in zip(vs,vs[1:]+vs[:1]):
  dx,dy=q[0]-p[0],q[1]-p[1];ll=math.hypot(dx,dy);n=(-sign*dy/ll,sign*dx/ll);ls.append((n,n[0]*p[0]+n[1]*p[1]+220))
 inset=[]
 for i,(n,c)in enumerate(ls):
  m,d=ls[i-1];det=m[0]*n[1]-m[1]*n[0];assert abs(det)>1e-9;inset.append(((d*n[1]-m[1]*c)/det,(m[0]*c-d*n[0])/det))
 inset.append(inset[0]);txt=txt[:match.start()]+'(boundary (path pcb 0 '+' '.join(f'{v:.3f}'for p in inset for v in p)+'))'+txt[match.end():]
 settings='\n    (autoroute_settings (autoroute on) (postroute off) (vias on) (layer_rule F.Cu (active on) (preferred_direction horizontal)) (layer_rule In1.Cu (active off)) (layer_rule In2.Cu (active on) (preferred_direction vertical)) (layer_rule B.Cu (active on) (preferred_direction horizontal)))'
 at=txt.index('\n    (plane GND');txt=txt[:at]+settings+txt[at:];dsn.write_text(txt)
 write('router-exchange.json',{'protected_local_copper_sha256':sha(OUT/'local-copper.json'),'frozen_schematic_XML_sha256':sha(HERE/'dock-lid-ui-native.xml'),'frozen_placement_sha256':sha(HERE/'dock-lid-placement.kicad_pcb'),'board_export_sha256':sha(BOARD),'dsn_sha256':sha(dsn),'In1_router_active':False,'router_only_boundary_inset_mm':.22,'offline_router':'freerouting1.9.0','analytics_disabled':True})
 print(dsn)
def repair_escape():
 """Replace only the auto RESET breakout blocking A0; preserve all local copper."""
 b=k.LoadBoard(str(BOARD));before=tracks(b);protected={signature(r)for r in json.loads((OUT/'local-copper.json').read_text())['protected_records']}
 removed=[]
 oldpoints=[[5.5829,113.2494],[5.55,112.05],[6.7823,112.05]]
 for t in list(b.GetTracks()):
  delete=False
  if t.GetNetname()=='LCD_RESETn':
   if isinstance(t,k.PCB_VIA):delete=mech(t.GetPosition())in oldpoints
   else:
    a,c=mech(t.GetStart()),mech(t.GetEnd())
    delete=(t.GetLayer()==k.F_Cu and max(a[0],c[0])<6.1 and min(a[1],c[1])>110)or(t.GetLayer()==k.B_Cu and any(p in [a,c]for p in oldpoints))
  elif t.GetNetname()=='LCD_A0':
   if isinstance(t,k.PCB_VIA):delete=mech(t.GetPosition())==[5.55,113.25]
   else:delete=t.GetLayer()==k.F_Cu and max(mech(t.GetStart())[0],mech(t.GetEnd())[0])<6
  elif t.m_Uuid.AsString() in {v['items'][0]['uuid']for v in json.loads((OUT/'drc.json').read_text())['violations']if v['type']=='track_dangling'}:
   assert not isinstance(t,k.PCB_VIA)and k.ToMM(t.GetLength())<.1
   delete=True
  if delete:
   r=record(t,b)
   assert signature(r)not in protected,'Never delete authored local copper'
   removed.append(r);b.Delete(t)
 if not any(isinstance(t,k.PCB_VIA)and mech(t.GetPosition())==[-33,55]for t in b.GetTracks()):via(b,'GND',(-33,55))
 if not any(isinstance(t,k.PCB_VIA)and mech(t.GetPosition())==[11.3,108]for t in b.GetTracks()):via(b,'GND',(11.3,108))
 via(b,'LCD_RESETn',(5.55,112.05))
 line(b,'LCD_RESETn',[(6,114),(6,112.5),(5.55,112.05)])
 line(b,'LCD_RESETn',[(5.55,112.05),(6.7823,112.05),(9.3738,109.4585)],k.B_Cu)
 via(b,'LCD_A0',(5.55,113.25))
 line(b,'LCD_A0',[(5.5,114),(5.5,113.55),(5.55,113.5),(5.55,113.25)])
 assert protected<={signature(t)for t in tracks(b)}
 save(b);write('escape-repair.json',{'removed_auto_records':removed,'after_board_sha256':sha(BOARD),'reason':'Separate RESET/A0 fine-pitch front escapes, add front-ground-island stitch and remove only native-reported38umauto stub. Every authored local LCD/pump/bypass/button record remains unchanged.','original_local_records_preserved':len(protected)})
 print('replaced auto records',len(removed))
def import_session():
 source_guard();r=json.loads((OUT/'router-exchange.json').read_text())
 dsn=BOARD.with_suffix('.dsn');ses=BOARD.with_suffix('.ses')
 assert sha(BOARD)==r['board_export_sha256']and sha(dsn)==r['dsn_sha256']
 assert sha(HERE/'dock-lid-ui-native.xml')==r['frozen_schematic_XML_sha256']
 b=k.LoadBoard(str(BOARD));before=tracks(b);fixed={signature(t)for t in before}
 refs=set(re.findall(r'\(place\s+([^\s)]+)',ses.read_text()))
 assert refs=={f.GetReference()for f in b.GetFootprints()},(refs,'router placement set differs')
 sourcepads={f.GetReference():sorted((p.GetNumber(),tuple(mech(p.GetPosition())),p.GetNetname())for p in f.Pads())for f in b.GetFootprints()}
 tree=s.parse(ses.read_text());routes=s.child(tree,'routes');assert [a.value for a in s.child(routes,'resolution')[1:]]==['um','10']
 incoming=[]
 def p(a,c):return [round(float(a.value)/10000-100,6),round(200+float(c.value)/10000,6)]
 for net in s.children(s.child(routes,'network_out'),'net'):
  name=net[1].value;assert b.FindNet(name),name
  for ent in net[2:]:
   if s.tag(ent)=='wire':
    path=s.child(ent,'path');assert path[1].value in LAYERS,('Reserved ground layer was routed',path[1].value)
    points=[p(a,c)for a,c in zip(path[3::2],path[4::2])]
    for start,end in zip(points,points[1:]):incoming.append({'kind':'track','net':name,'layer':path[1].value,'start':start,'end':end,'width':round(float(path[2].value)/10000,6)})
   elif s.tag(ent)=='via':
    dims=re.fullmatch(r'Via\[0-3\]_(\d+):(\d+)_um',ent[1].value);assert dims,ent[1].value
    incoming.append({'kind':'via','net':name,'xy':p(ent[2],ent[3]),'diameter':float(dims[1])/1000,'drill':float(dims[2])/1000})
   else:raise ValueError(s.tag(ent))
 added=[];have=set(fixed)
 for item in incoming:
  sig=signature(item)
  if sig in have:continue
  if item['kind']=='via':via(b,item['net'],item['xy'],item['diameter'],item['drill'],False)
  else:line(b,item['net'],[item['start'],item['end']],LAYERS[item['layer']],item['width'],False)
  added.append(item);have.add(sig)
 assert fixed<={signature(t)for t in tracks(b)}
 for fp in b.GetFootprints():assert sourcepads[fp.GetReference()]==sorted((p.GetNumber(),tuple(mech(p.GetPosition())),p.GetNetname())for p in fp.Pads())
 save(b)
 r.update({'session_sha256':sha(ses),'incoming_records':len(incoming),'added_records':len(added),'preserved_manual_records':len(before),'routed_board_sha256_before_fill':sha(BOARD)})
 write('router-exchange.json',r);print(json.dumps({'incoming':len(incoming),'added':len(added),'manual_preserved':len(before)}))
def ledger():
 """Bind the final board to the authored seed and exact first-pass session."""
 b=k.LoadBoard(str(BOARD));final=tracks(b)
 protected=json.loads((OUT/'local-copper.json').read_text())['protected_records']
 initial=list(protected);ses=OUT/'first-pass.ses';tree=s.parse(ses.read_text())
 routes=s.child(tree,'routes');assert[a.value for a in s.child(routes,'resolution')[1:]]==['um','10']
 # Reproduce the importer’s exact integer-nanometre conversion.
 point=lambda a,c:mech(xy(round(float(a.value)/10000-100,6),round(200+float(c.value)/10000,6)))
 for net in s.children(s.child(routes,'network_out'),'net'):
  name=net[1].value
  for ent in net[2:]:
   if s.tag(ent)=='wire':
    path=s.child(ent,'path');ps=[point(a,c)for a,c in zip(path[3::2],path[4::2])]
    initial +=[{'kind':'track','net':name,'layer':path[1].value,'start':a,'end':c,'width':round(float(path[2].value)/10000,6)}for a,c in zip(ps,ps[1:])]
   elif s.tag(ent)=='via':
    dims=re.fullmatch(r'Via\[0-3\]_(\d+):(\d+)_um',ent[1].value);assert dims
    initial.append({'kind':'via','net':name,'xy':point(ent[2],ent[3]),'diameter':float(dims[1])/1000,'drill':float(dims[2])/1000})
   else:raise ValueError(s.tag(ent))
 old=collections.Counter(map(signature,initial));new=collections.Counter(map(signature,final));fixed=collections.Counter(map(signature,protected))
 assert not fixed-new,'Original authored copper changed'
 missing=old-new;added=new-old
 removed_rows=[];added_rows=[]
 for r in initial:
  key=signature(r)
  if missing[key]:removed_rows.append(r);missing[key]-=1
 for r in final:
  key=signature(r)
  if added[key]:added_rows.append(r);added[key]-=1
 write('escape-repair.json',{'initial_offline_session_sha256':sha(ses),'final_board_sha256':sha(BOARD),'initial_records':len(initial),'final_records':len(final),'removed_initial_auto_records':removed_rows,'added_final_records':added_rows,'original_authored_records_preserved':len(protected),'intent':'Replace the obstructing auto RESET breakout with distinct RESET/A0 escapes; remove only the native-reported38umauto stub; stitch the resistor ground island and front edge; finishA0. All original authored LCDpump/bypass/button copper remains unchanged.','source_circuit_changed':False})
 floor=json.loads((OUT/'route-floorplan.json').read_text());fps={f.GetReference():f for f in b.GetFootprints()}
 floor['pads']={r:[{'n':p.GetNumber(),'net':p.GetNetname(),'xy':mech(p.GetPosition()),'layer':pad_side(p)}for p in f.Pads()]for r,f in fps.items()}
 floor['final_board_sha256']=sha(BOARD);write('route-floorplan.json',floor)
 needed={str(fp.GetFPID().GetLibItemName())for fp in b.GetFootprints()}
 for p in (OUT/'DockControl.pretty').glob('*.kicad_mod'):
  if p.stem not in needed:p.unlink()
 print(json.dumps({'initial':len(initial),'final':len(final),'removed_auto':len(removed_rows),'added':len(added_rows),'authored_preserved':len(protected)}))
def final_rules():
 # KiCad7 defaults omit newer KiCad10 checks. Enable every one explicitly;
 # never use report exclusions to obtain a clean native result.
 path=BOARD.with_suffix('.kicad_pro');project=json.loads(path.read_text())
 settings=project['board']['design_settings'];assert settings['drc_exclusions']==[]
 rules=settings['rule_severities']
 for name in ('missing_courtyard','track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch','pth_inside_courtyard','npth_inside_courtyard','footprint_type_mismatch'):
  rules[name]='warning'
 path.write_text(json.dumps(project,indent=2)+'\n');print('all KiCad10 checks enabled; exclusions empty')
def center_vias():
 b=k.LoadBoard(str(BOARD));items={t.m_Uuid.AsString():t for t in b.GetTracks()};protected={signature(r)for r in json.loads((OUT/'local-copper.json').read_text())['protected_records']};changes=[]
 for v in json.loads((OUT/'drc.json').read_text())['violations']:
  assert v['type']=='track_not_centered_on_via',v['type']
  pair=[items[i['uuid']]for i in v['items']];track=next(t for t in pair if not isinstance(t,k.PCB_VIA));hole=next(t for t in pair if isinstance(t,k.PCB_VIA))
  assert signature(record(track,b))not in protected and track.GetNetname()==hole.GetNetname()
  before=record(track,b);point=hole.GetPosition();ends=[track.GetStart(),track.GetEnd()];dist=[math.hypot(k.ToMM(p.x-point.x),k.ToMM(p.y-point.y))for p in ends];at=dist.index(min(dist));assert dist[at]<.001
  if at==0:track.SetStart(point)
  else:track.SetEnd(point)
  changes.append({'before':before,'after':record(track,b),'delta_mm':dist[at]})
 save(b);write('native-finalization.json',{'reason':'Center only native-reported automatic track endpoints on same-net vias; submicrometre SES conversion correction. Authored local copper unchanged.','changes':changes,'board_sha256_after_alignment':sha(BOARD)})
 print('native via-centering corrections',len(changes))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['seed','local','fill','export','import','repair-escape','ledger','final-rules','center-vias']);ap.add_argument('--restart-local',action='store_true');a=ap.parse_args()
 if a.action=='local':local(a.restart_local)
 elif a.action=='import':import_session()
 elif a.action=='repair-escape':repair_escape()
 elif a.action=='final-rules':final_rules()
 elif a.action=='center-vias':center_vias()
 else:globals()[a.action]()
if __name__=='__main__':main()
