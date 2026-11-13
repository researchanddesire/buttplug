"""Native source-power placement/critical copper subset of ONE shared base PCB.

Run with KiCad7 Python. Frozen source schematics are read, never edited.
This board is an integration block, not a separate stacked/fabrication board.
"""
from pathlib import Path
import argparse, hashlib, json, math, shutil, xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
HERE=Path(__file__).resolve().parent
EVT=HERE.parents[1]
SRC=EVT/'dock-ui'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OUT=HERE/'source-block.kicad_pcb'
def xy(x,y):return k.VECTOR2I(round((100+x)*1e6),round((200-y)*1e6))
def dock(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
POS={
 'J101':(0,-1.325,0),'U121':(0,11,90),'J102':(-3.75,24,0),
 'U103':(-15,7,0),'U102':(-24,8,0),'U104':(10,17,0),
 'U105':(25,21,0),'U114':(-5,18,0),'U120':(-32,14,0),
 'U123':(-32,22,0),'U124':(-24,14,0),'U122':(20,8,0),
 'J103':(21,25,0),'J104':(16,12,0),
 'C101':(-27,10.5,0),'C102':(7.3,17.4,180),'C103':(21.4,21.8,180),
 'C104':(-30,10,90),'C105':(-21,5.5,90),'C106':(13.3,17,0),
 'C107':(29,21.8,0),'C108':(-18,9,180),'C109':(-5,14,0),
 'C110':(-28,15,90),'C111':(-28,22,90),
 'C112':(20,4,0),'C113':(-24,18,0),'C114':(15,21,90),
 'Q103':(13.5,7,0),
 'R101':(-18,3.5,0),'R105':(-6,12,0),'R106':(13.5,14.5,0),
 'R107':(29,17,0),'R108':(3,21,0),
 'R120':(-11,11,90),'R121':(-3,9,90),'R122':(15,24,90),
 'R123':(12,21,90),'R124':(32,21,90),'R125':(-9,12,90),
 'R126':(17,24,90),'R127':(-21,22,90),'R128':(-19,12,90),
 'R129':(-35,18,90),'R130':(-35,11,90),
 'R131':(-38,23,90),'R132':(-31,7,0),'R133':(22,17,90),
}
OUTLINE=[(-5.5,-4),(5.5,-4),(5.5,2),(25,2),(47.5,15),
 (48,25),(48,65),(45,68),(-45,68),(-48,65),(-48,15),(-25,2),(-5.5,2)]
HOLES=[]
for x,y in ((-43,19),(-15,19)):
 HOLES.append([(x-3.5,y-4),(x+3.5,y-4),(x+4,y-3.5),(x+4,y+3.5),
 (x+3.5,y+4),(x-3.5,y+4),(x-4,y+3.5),(x-4,y-3.5)])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--restart',action='store_true');a=ap.parse_args()
 if OUT.exists():
  last=json.loads((HERE/'placement.json').read_text())
  assert a.restart and sha(OUT)==last['board_sha256'],'Preserve modified block before rebuilding'
 check=json.loads((SRC/'native-checks.json').read_text())
 for p,d in check['source_sha256'].items():assert sha(SRC/p)==d,('Stale native source',p)
 for p,d in check['reports_sha256'].items():assert sha(SRC/p)==d,('Stale native report',p)
 # Local, hash-bound derived library: copper/pad geometry is unchanged.
 # Only nonphysical silk/courtyard graphics adapt to the existing shell.
 libdir=HERE/'SourceBlock.pretty';libdir.mkdir(exist_ok=True)
 for f in (SRC/'DockUI.pretty').glob('*.kicad_mod'):shutil.copyfile(f,libdir/f.name)
 f=libdir/'USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod'
 txt=f.read_text().replace('(end -4.67 3.25)','(end -4.67 2.475)').replace('(end 4.67 3.25)','(end 4.67 2.475)');f.write_text(txt)
 f=libdir/'Contact_Loom_4Land.kicad_mod'
 txt=f.read_text().replace('(start -1.5 -1.5) (end 9.0 -1.5)','(start -1.0 -1.0) (end 8.5 -1.0)')
 txt=txt.replace('(start 9.0 -1.5) (end 9.0 1.5)','(start 8.5 -1.0) (end 8.5 1.0)')
 txt=txt.replace('(start 9.0 1.5) (end -1.5 1.5)','(start 8.5 1.0) (end -1.0 1.0)')
 txt=txt.replace('(start -1.5 1.5) (end -1.5 -1.5)','(start -1.0 1.0) (end -1.0 -1.0)');f.write_text(txt)
 xml=ET.parse(SRC/'source-native.xml').getroot();b=k.BOARD();b.SetFileName(str(OUT));b.SetCopperLayerCount(4)
 ds=b.GetDesignSettings();ds.SetBoardThickness(k.FromMM(1));ds.m_MinClearance=k.FromMM(.15)
 ds.m_TrackMinWidth=k.FromMM(.15);ds.m_CopperEdgeClearance=k.FromMM(.3)
 ds.m_HoleClearance=k.FromMM(.15);ds.m_MinThroughDrill=k.FromMM(.2);ds.m_ViasMinSize=k.FromMM(.5)
 nc=ds.m_NetSettings.m_DefaultNetClass;nc.SetClearance(k.FromMM(.15));nc.SetTrackWidth(k.FromMM(.2))
 nc.SetViaDiameter(k.FromMM(.5));nc.SetViaDrill(k.FromMM(.2))
 ds.SetAuxOrigin(xy(0,0));netmap={}
 for n in xml.findall('./nets/net'):
  name=n.get('name');b.Add(k.NETINFO_ITEM(b,name))
  for p in n.findall('node'):netmap[(p.get('ref'),p.get('pin'))]=name
 fps={}
 for c in xml.findall('./components/comp'):
  r=c.get('ref');lib=c.findtext('footprint');name=lib.split(':')[1]
  fp=k.FootprintLoad(str(libdir),name);assert fp,lib
  fp.SetFPID(k.LIB_ID('DockUI',name));fp.SetReference(r);fp.SetValue(c.findtext('value'))
  fp.SetPosition(xy(*POS[r][:2]));fp.SetOrientationDegrees(POS[r][2]);fp.SetLocked(True)
  fp.SetPath(k.KIID_PATH(c.find('sheetpath').get('tstamps')+c.findtext('tstamps')))
  fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
  for p in fp.Pads():
   net=netmap.get((r,p.GetNumber()))
   if net:p.SetNet(b.FindNet(net))
  b.Add(fp);fps[r]=fp
 assert set(fps)==set(POS) and len(fps)==48
 def pad(r,n):return dock(next(p for p in fps[r].Pads()if p.GetNumber()==n).GetPosition())
 records=[]
 def track(net,pts,width=.2,layer=k.F_Cu,role='local'):
  for p,q in zip(pts,pts[1:]):
   if p==q:continue
   t=k.PCB_TRACK(b);t.SetStart(xy(*p));t.SetEnd(xy(*q));t.SetWidth(k.FromMM(width))
   t.SetLayer(layer);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
   records.append({'kind':'track','net':net,'start':p,'end':q,'width':width,'layer':k.LayerName(layer),'role':role})
 def via(net,p,role='local'):
  v=k.PCB_VIA(b);v.SetPosition(xy(*p));v.SetWidth(k.FromMM(.5));v.SetDrill(k.FromMM(.2))
  v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
  records.append({'kind':'via','net':net,'position':p,'diameter':.5,'drill':.2,'role':role})
 def join(r,n,s,m,via_points=(),width=.2,layer=k.F_Cu,role='local'):
  net=netmap[(r,n)];assert net==netmap[(s,m)],(r,n,s,m)
  track(net,[pad(r,n),*via_points,pad(s,m)],width,layer,role)
 def to_via(r,n,p,width=.2,role='ground-return'):
  net=netmap[(r,n)];track(net,[pad(r,n),p],width,role=role);via(net,p,role)
 def graphic(poly):
  for p,q in zip(poly,poly[1:]+poly[:1]):
   x=k.PCB_SHAPE(b);x.SetShape(k.SHAPE_T_SEGMENT);x.SetLayer(k.Edge_Cuts)
   x.SetStart(xy(*p));x.SetEnd(xy(*q));x.SetWidth(k.FromMM(.05));b.Add(x)
 graphic(OUTLINE)
 for h in HOLES:graphic(h)
 # Rotated, source-preserved USB orientation escape from the already native-
 # checked old dock. New physical J101 is angle0, with mouth toward dock-Y.
 T=lambda p:[p[1]-11,p[0]-1.5]
 for pts in (((3.855,10.25),(4.7,10.25),(5.4,9.55)),((3.855,11.25),(6.2,11.25))):
  track('USB_DM',[T(p)for p in pts],role='USB orientation escape')
 for p in ((5.4,9.55),(6.2,11.25),(9.6,10.05)):via('USB_DM',T(p),'USB orientation escape')
 track('USB_DM',[T(p)for p in ((6.2,11.25),(6.2,9.55),(8.1,9.55),(9.6,10.05))],layer=k.B_Cu,role='USB orientation escape')
 track('USB_DM',[T(p)for p in ((5.4,9.55),(6.2,9.55))],layer=k.B_Cu,role='USB orientation escape')
 track('USB_DM',[T(p)for p in ((9.6,10.05),(11.3625,10.05),(13.6375,10.05))],role='USB ESD flow through')
 for pts in (((3.855,10.75),(4.7,10.75),(5.5,10.3),(8.5,10.3),(10.15,11.95),(11.3625,11.95)),
             ((3.855,11.75),(4.8,11.75),(5.45,12.4),(6.4,12.4),(8.5,10.3))):
  track('USB_DP',[T(p)for p in pts],role='USB orientation escape')
 join('U121','3','U121','4',role='USB ESD flow through')
 join('U121','6','J102','2',((-0.95,13),(-.25,13.7),(-.25,22),(-1.25,23)),role='USB pair to device loom')
 join('U121','4','J102','3',((.95,13),(.25,13.7),(.25,22),(1.25,23)),role='USB pair to device loom')
 # Manual CC escapes run under the insulated connector body with tented
 # vias, then avoid the connector shell stakes and locating holes.
 to_via('J101','A5',(-1.25,1),.2,'CC1 escape')
 to_via('J101','B5',(1.75,1),.2,'CC2 escape')
 track('CC1',[(-1.25,1),(-1.25,0),(-3.59,0),(-3.59,3.1),(-4.8,3.1),(-5.6,3.9),(-18.5,3.9),(-18.5,7.8),(-17.5,7.8)],.15,k.In2_Cu,'CC1 manual')
 track('CC2',[(1.75,1),(.8,1),(.8,6.5),(3,8.7),(3,10.2),(-20.2,10.2),(-20.2,6.2),(-17.5,6.2)],.2,k.B_Cu,'CC2 manual')
 for net,p in [('CC1',(-17.5,7.8)),('CC2',(-17.5,6.2))]:via(net,p,'CC terminal escape')
 track('CC1',[(-17.5,7.8),(-16.7,7.8),(-16.1,7.2),pad('U103','1')],.2,role='CC1 manual')
 track('CC2',[(-17.5,6.2),(-16.7,6.2),(-16.1,6.8),pad('U103','2')],.2,role='CC2 manual')
 # Every local capacitor has an outward ground return. The non-ground side
 # is left for the merged power route unless an explicit local loop below.
 for r in ('C101','C102','C103','C104','C105','C106','C107','C108','C109','C110','C111','C112','C113'):
  p=pad(r,'2');q=pad(r,'1');d=math.hypot(p[0]-q[0],p[1]-q[1])
  end=(round(p[0]+.8*(p[0]-q[0])/d,6),round(p[1]+.8*(p[1]-q[1])/d,6))
  to_via(r,'2',end,.25)
 # Short ESD and USB ground/reference return. In1 remains unbroken beneath
 # the pair; orientation-bridge vias also get an adjacent return connection.
 to_via('U121','2',(0,8.9),.25)
 for n,x in [('A1',-3.2),('A12',3.2)]:to_via('J101',n,(x,3.5),.4)
 for x in (-4.32,4.32):
  track('GND',[(x,1.78),(x,3.8)],.4,role='USB shell return');via('GND',(x,3.8),'USB shell return')
 # Input contacts fan out to the broad HOST_5V distribution access.
 for n,x in [('A4',-2.4),('A9',2.4)]:to_via('J101',n,(x,3.5),.5,'VBUS entry')
 track('HOST_5V',[(-2.4,3.5),(-2.4,2),(2.4,2),(2.4,3.5)],.6,k.In2_Cu,'VBUS bridge')
 # Explicit LDO local input/enable/output loops and CC decoupling. Broad
 # merged-board power routing joins the capacitor power pads; these short
 # surface loops must remain fixed and do not rely on a wide router escaping
 # the tiny CC package supply pin.
 join('U102','1','C101','1',((-27.825,8.95),),.5,role='LDO local input')
 join('U102','3','U102','1',((-27.2,7.05),(-27.2,8.95)),.4,role='LDO enable VIN')
 join('U102','5','C105','1',((-21.84,8.95),(-21.84,4.725)),.4,role='LDO local output')
 join('U103','12','C108','1',((-15.6,8.8),(-17.52,8.8)),.15,role='CC supply local loop')
 # WLCSP two-column fanout uses outward0.15mm necks, no via-in-pad or
 # between-ball escape. VIN A1/B1 are intentionally common.
 join('U104','A1','U104','B1',width=.15,role='device limiter VIN')
 track('HOST_5V',[pad('U104','A1'),(9.1,17.4),pad('C102','1')],.15,role='device limiter input loop')
 via('HOST_5V',(8.6,17.4),'device limiter input access')
 track('HOST_5V',[(8.6,17.4),pad('C102','1')],.4,role='device limiter input loop')
 to_via('U104','A2',(11.3,18.5),.15,'device fault outward escape')
 to_via('U104','C2',(11.3,15.5),.15,'device ILIM outward escape')
 to_via('U104','C1',(8.6,15.5),.15,'device GND outward escape')
 track('CONTACT_5V',[pad('U104','B2'),(11.3,17)],.15,role='device limiter output neck')
 via('CONTACT_5V',(11.3,17),'device limiter output access')
 track('CONTACT_5V',[(11.3,17),pad('C106','1')],.5,role='device limiter output loop')
 to_via('J102','4',(3.75,25.2),.6,'device power output')
 track('CONTACT_5V',[(11.3,17),(10,17),(10,18.5),(4,18.5),(4,25.2),(3.75,25.2)],.8,k.B_Cu,'device power output')
 # UV limiter local input/output loops and low resistance export. Decouplers
 # face the power terminals. U105 is adjacent to the two safety cuts.
 join('U105','1','C103','1',width=.6,role='UV limiter input loop')
 join('U105','6','C107','1',width=.6,role='UV limiter output loop')
 to_via('C103','1',(21.9,23),.6,'UV limiter input access')
 to_via('U105','2',(22.7,20.5),.3,'UV limiter ground return')
 track('UV_5V_LIMITED',[pad('U105','6'),(26.8,22.6),(25,23.4),(23.5,23.4),(23.5,25)],.8,role='UV limited export')
 # Current-program resistor close to ILIM, with a separate ground return.
 join('U105','5','R107','1',((27.2,21),(27.2,17),),.2,role='UV current programming')
 p=pad('R107','2');to_via('R107','2',(p[0]+.9,p[1]),.25)
 # Additional local ground access is routed outward from the package edge.
 for r,n,p in [('U103','10',(-14.8,9.2)),('U103','3',(-16.6,5.5)),
  ('U102','2',(-26.3,8)),('U114','2',(-7.3,18)),('U120','2',(-34.3,14)),
  ('U123','2',(-34.3,22)),('U124','2',(-26.3,14)),('U122','2',(17.7,8)),
  ('Q103','2',(11.2,7))]:to_via(r,n,p,.15 if r=='U103' else .2)
 # Complete the selected local current-programming branch across the via.
 track('DEVICE_ILIM',[(11.3,15.5),pad('R106','1')],.2,role='device ILIM local')
 to_via('R105','1',(-6,12),.2,'device ILIM branch')
 track('DEVICE_ILIM',[(11.3,15.5),(10.5,14.7),(-4,14.7),(-6,12)],.2,k.B_Cu,'device ILIM branch')
 # Explicit input-power connection uses a narrow clearance-controlled neck at
 # the connector, then broad inner copper. It does not split In1 ground.
 track('HOST_5V',[(2.4,3.5),(3.4,4.5)],.3,k.In2_Cu,'VBUS entry neck')
 track('HOST_5V',[(3.4,4.5),(4,6.5),(4,9),(6,11),(7,12),(7,14.5),(7.5,15),(7.5,17.4),(8.6,17.4)],1.0,k.In2_Cu,'HOST power trunk')
 track('HOST_5V',[(8.6,17.4),(8.6,19),(12,21),(12,24),(15,26),(21.9,23)],1.0,k.In2_Cu,'HOST power trunk')
 # Fault escape completes on the resistor side; physical UV power stays
 # on its separate route and the hardware-latch path is not changed.
 to_via('R123','2',(13.4,21.825),.2,'device fault pullup')
 track('DEVICE_FAULTn',[(11.3,18.5),(12.4,19.6),(13.4,20.6),(13.4,21.825)],.2,k.B_Cu,'device fault pullup')
 # Existing shell bosses, not newly inferred mount locations. Mechanical
 # positions are separate from all48 source-circuit references.
 for i,(x,y) in enumerate(((-8,5.5),(8,5.5),(-8,23.5),(8,23.5)),101):
  f=k.FOOTPRINT(b);f.SetReference('H'+str(i));f.SetValue('M2 existing boss / NPTH2.3 / R3 hardware')
  f.SetPosition(xy(x,y));f.Reference().SetVisible(False);f.Value().SetVisible(False);f.SetLocked(True)
  p=k.PAD(f);p.SetAttribute(k.PAD_ATTRIB_NPTH);p.SetShape(k.PAD_SHAPE_CIRCLE)
  p.SetSize(k.VECTOR2I(k.FromMM(2.3),k.FromMM(2.3)));p.SetDrillSize(k.VECTOR2I(k.FromMM(2.3),k.FromMM(2.3)))
  layers=k.LSET.AllCuMask();layers.AddLayer(k.F_Mask);layers.AddLayer(k.B_Mask)
  p.SetLayerSet(layers);p.SetPosition(xy(x,y));f.Add(p)
  c=k.FP_SHAPE(f);c.SetShape(k.SHAPE_T_CIRCLE);c.SetLayer(k.F_CrtYd)
  c.SetStart0(k.VECTOR2I(0,0));c.SetEnd0(k.VECTOR2I(k.FromMM(3),0));c.SetDrawCoord();c.SetWidth(k.FromMM(.05));f.Add(c);b.Add(f)
  z0=k.ZONE(b);ls=k.LSET();ls.AddLayer(k.F_Cu);ls.AddLayer(k.B_Cu);z0.SetLayerSet(ls)
  z0.SetIsRuleArea(True);z0.SetDoNotAllowTracks(True);z0.SetDoNotAllowVias(True)
  z0.SetDoNotAllowCopperPour(True);z0.SetDoNotAllowPads(False);z0.SetDoNotAllowFootprints(False)
  po=z0.Outline();po.NewOutline()
  for j in range(72):
   ang=2*math.pi*j/72;q=xy(x+3*math.cos(ang),y+3*math.sin(ang));po.Append(q.x,q.y)
  b.Add(z0)
 # The port projects past the PCB nose. Clip only the two printed silk ends
 # to the actual board; selected copper pads, NPTHs, fab and body are intact.
 for g in fps['J101'].GraphicalItems():
  if g.GetLayer()==k.F_SilkS:
   end=g.GetEnd0()
   if k.ToMM(end.y)>2.475:g.SetEnd0(k.VECTOR2I(end.x,k.FromMM(2.475)));g.SetDrawCoord()
 # Continuous In1 GND reference, with cutouts clipped by native edge geometry.
 z=k.ZONE(b);z.SetLayer(k.In1_Cu);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(k.FromMM(.2))
 z.SetMinThickness(k.FromMM(.2));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
 z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
 poly=z.Outline();poly.NewOutline()
 for p in OUTLINE:q=xy(*p);poly.Append(q.x,q.y)
 b.Add(z)
 k.SaveBoard(str(OUT),b)
 # Project rule file shares agreed 0.15/0.15 and 0.5/0.2 capabilities; no DRC exclusions.
 pro=json.loads((EVT/'dock-control/dock-controller-placement.kicad_pro').read_text())
 rules=pro['board']['design_settings']['rules']
 rules.update(min_clearance=.15,min_track_width=.15,min_hole_clearance=.15,min_via_diameter=.5,min_through_hole_diameter=.2)
 pro['net_settings']['classes'][0].update(clearance=.15,via_diameter=.5,via_drill=.2)
 base=pro['net_settings']['classes'][0]
 for name,width in [('HOST_POWER',.6),('UV_POWER',.8),('DEVICE_POWER',.6),('UI_POWER',.3)]:
  c=dict(base);c.update(name=name,track_width=width);pro['net_settings']['classes'].append(c)
 pro['net_settings']['netclass_assignments']={'HOST_5V':'HOST_POWER','UV_5V_LIMITED':'UV_POWER','CONTACT_5V':'DEVICE_POWER','3V3':'UI_POWER'}
 (HERE/'source-block.kicad_pro').write_text(json.dumps(pro,indent=2)+'\n')
 (HERE/'fp-lib-table').write_text('(fp_lib_table (lib (name "DockUI")(type "KiCad")(uri "${KIPRJMOD}/SourceBlock.pretty")(options "")(descr "Frozen source selected footprints")))\n')
 sources={str(p.relative_to(EVT)):sha(p)for p in [SRC/'source-native.xml',SRC/'native-checks.json',SRC/'source-circuit-parts.json',SRC/'dock-ui-source.kicad_sch',*sorted((SRC/'DockUI.pretty').glob('*.kicad_mod'))]}
 result={'status':'native source-power critical copper integration block; NOT fabrication','board_sha256':sha(OUT),
 'source_sha256_relative_evt1':sources,'frame':'pcbX=100+dockX; pcbY=200-dockY; F.Cu normal+dockZ',
 'board_top_bottom_z_mm':[6.4,5.4],'layers':4,'thickness_mm':1,
 'footprint_placements_dock_xy_native_angle':POS,'frozen_references':sorted(fps),'mechanical_hole_refs':['H101','H102','H103','H104'],'existing_shell_mounts':{'dock_xy_mm':[[-8,5.5],[8,5.5],[-8,23.5],[8,23.5]],'NPTH_mm':2.3,'hardware_clearance_radius_mm':3},
 'critical_copper':records,'all_critical_copper_locked':True,
 'USB_datum':{'reference':'J101','native_origin_mm':[100,201.325],'native_angle_deg':0,
 'mating_face_dock_mm':[0,-5],'manufacturer_front_relative_footprint_mm':[0,3.675],
 'face_direction_dock':[0,-1,0],'OEM_body_top_z_mm':9.71,'selected_120_stake_bottom_z_mm':5.2,
 'existing_window_bottom_z_mm':5.1,'stock_KiCad_STEP_stake_mm':.95,'selected_stake_mm':1.2,
 'source':'https://gct.co/files/drawings/usb4105.pdf Rev B4 2023-12-18',
 'note':'5.1mm is old enclosure-window bottom, not socket-body bottom. Stock STEP has0.95mm stakes; selected120 has1.20mm. Native footprint face maps through Y inversion; STEP model uses+Y opposite nativePCB+Y.'},
 'UV_export':{'UV_5V_LIMITED_dock_xy_mm':[23.5,25],'target_safety_cut_centres_mm':[[28,28],[31,28]],'width_mm':.8},
 'open':['noncritical signal completion on merged shared board','merged-board refill/DRC/connectivity','impedance stackup and USB physical test','source voltage-drop/current/thermal qualification','full MCAD selected component heights','manufacturer routing/process acceptance'],
 'full_product_order_ready':False}
 (HERE/'placement.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'references':len(fps),'critical_items':len(records),'board_sha256':sha(OUT)}))
if __name__=='__main__':main()
