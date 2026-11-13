"""Authored, locked USB, supply/decoupling and return paths for fixed placement."""
from pathlib import Path
import hashlib,json,math
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,z):return k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6))
def main():
 meta=json.loads((H/'pcb-state.json').read_text());assert sha(P)==meta['board_sha256']and not meta['routing_started'];project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()};items=[]
 def p(ref,num):
  q=next(q for q in fps[ref].Pads()if q.GetNumber()==num);return[round(q.GetPosition().x/1e6-100,6),round(100-q.GetPosition().y/1e6,6)]
 def wire(net,points,layer='B.Cu',width=.15,role='critical'):
  for a,c in zip(points,points[1:]):
   if xy(*a)==xy(*c):continue
   t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*c));t.SetWidth(k.FromMM(width));t.SetLayer(b.GetLayerID(layer));t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
   items.append({'kind':'track','uuid':t.m_Uuid.AsString(),'net':net,'layer':layer,'start':a,'end':c,'width_mm':width,'role':role})
 def via(net,point,role='critical'):
  v=k.PCB_VIA(b);v.SetPosition(xy(*point));v.SetWidth(k.FromMM(.5));v.SetDrill(k.FromMM(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
  items.append({'kind':'via','uuid':v.m_Uuid.AsString(),'net':net,'product_XZ_mm':point,'diameter_mm':.5,'drill_mm':.2,'role':role});return point
 # Contact fanout to short ESD-entry rows. All data uses F referenced to In1GND.
 esd={1:[-3.25,3.05],3:[-3.25,4.95],6:[1.25,3.05],4:[1.25,4.95]}
 for pin,point in esd.items():
  net='USB_DM_CONTACT'if pin in(1,6)else'USB_DP_CONTACT';via(net,point,'USB ESD fanout');wire(net,[p('U75',str(pin)),point],width=.15,role='USB ESD fanout')
 wire('USB_DM_CONTACT',[p('CT2','1'),[-3.25,3.25],esd[1]],'F.Cu',.15,'USB contact fanout')
 wire('USB_DP_CONTACT',[p('CT3','1'),[-3.25,9.25],esd[3]],'F.Cu',.15,'USB contact fanout')
 wire('USB_DM_CONTACT',[esd[1],esd[6]],'F.Cu',.15,'USB ESD channel landing')
 wire('USB_DP_CONTACT',[esd[3],esd[4]],'F.Cu',.15,'USB ESD channel landing')
 resistors={('R75','1'):[-17.5,3.5],('R76','1'):[-17.5,6.5],('R75','2'):[-20.1,3.5],('R76','2'):[-20.1,6.5]}
 for(ref,pin),point in resistors.items():
  net=('USB_DM'if ref=='R75'else'USB_DP')+('_CONTACT'if pin=='1'else'');via(net,point,'USB22R fanout');wire(net,[p(ref,pin),point],role='USB22R fanout')
 wire('USB_DM_CONTACT',[esd[6],[2.25,2.05],[1.8,1.6],[-15.6,1.6],resistors['R75','1']],'F.Cu',.15,'USB contact-to-series paired section')
 wire('USB_DP_CONTACT',[esd[4],[3.5,2.7],[3.5,1.25],[-16,1.25],[-18.2,3.45],[-18.2,5.8],resistors['R76','1']],'F.Cu',.15,'USB contact-to-series paired section')
 mcu={'USB_DM':[-26.8,-7.1],'USB_DP':[-27.6,-7.1]}
 for net,pin in(('USB_DM','26'),('USB_DP','27')):
  via(net,mcu[net],'USB module fanout');wire(net,[p('U6',pin),mcu[net]],role='USB module fanout')
 wire('USB_DM',[resistors['R75','2'],[-22,1.6],[-22,-2],[-23.5,-3.5],[-25.5,-3.5],[-26.8,-4.8],mcu['USB_DM']],'F.Cu',.15,'USB series-to-module paired section')
 wire('USB_DP',[resistors['R76','2'],[-22.5,4.1],[-22.5,-1.8],[-23.8,-3.1],[-26,-3.1],[-27.6,-4.7],mcu['USB_DP']],'F.Cu',.15,'USB series-to-module paired section')
 # Retained J4 serviceUSB branches stay short and explicit.
 for net,pin,start,end in[('USB_DM','2',[-14,-4.7],[-26.8,-5]),('USB_DP','3',[-15,-4.7],[-27.6,-4.9])]:
  via(net,start,'retained USB service branch');via(net,end,'retained USB service branch');wire(net,[p('J4',pin),start],role='retained USB service branch')
 wire('USB_DM',[[-14,-4.7],[-15,-5.7],[-26.1,-5.7],[-26.8,-5]],'In2.Cu',.15,'retained USB service branch')
 wire('USB_DP',[[-15,-4.7],[-16,-3.7],[-26.4,-3.7],[-27.6,-4.9]],'In2.Cu',.15,'retained USB service branch')
 for point in([-13,-4.7],[-28.8,-4.5]):via('GND',point,'USB service plane return')
 wire('GND',[p('J4','1'),[-13,-4.7]],width=.35,role='USB service plane return')
 # Adjacent plane returns at both USB layer-change regions and ESD GND.
 for pos in([ -3.1,4],[-19.7,5],[-25.5,-7.1]):via('GND',pos,'USB reference return')
 wire('GND',[p('U75','2'),[-3.1,4]],width=.35,role='ESD short ground return')
 # Input PTC and diode retain the actual source polarity/pad numbering.
 via('DOCK_5V',[2.6,6.7],'contact power');wire('DOCK_5V',[p('CT4','1'),[2.6,9.4],[2.6,6.7]],'F.Cu',.8,'contact power trunk');wire('DOCK_5V',[[2.6,6.7],p('F1','1')],width=.6,role='PTC input')
 wire('DOCK_5V',[p('U75','5'),[1.6,4],p('F1','1')],width=.4,role='ESD VBUS bias')
 wire('DOCK_FUSED',[p('F1','2'),[5.4,6.5],[6.6,7.7],[9.95,7.7],[10.65,7],p('D1','1')],width=.6,role='PTC to diode anode')
 for point in([7.35,3.3],[8.15,3.3]):via('VBUS_CHG',point,'protected power stitching')
 wire('VBUS_CHG',[p('D1','2'),[7.35,3.3],[8.15,3.3]],width=.6,role='diode output')
 for pin,net,z in(('1','GND',4.5),('2','VBUS_CHG',3.5),('3','3V3',2.5)):
  via(net,[-7.2,z],'body interface power');wire(net,[p('J7',pin),[-7.2,z]],width=.5,role='body interface power')
 via('VBUS_CHG',[-6.4,3.5],'protected power stitching');wire('VBUS_CHG',[[-7.2,3.5],[-6.4,3.5]],width=.6,role='protected power stitching')
 wire('VBUS_CHG',[[7.35,3.3],[6,4.65],[6,7.6],[-5.5,7.6],[-5.5,3.5],[-7.2,3.5]],'In2.Cu',.8,'protected supply trunk')
 wire('VBUS_CHG',[[7.35,3.3],[8.15,3.3]],'In2.Cu',.6,'protected power stitching')
 # Supply caps face the actual module3V3 pad. Keep this loop short and local.
 for point in([-32.4,7],[-31.6,7]):via('3V3',point,'module supply stitching')
 wire('3V3',[p('U6','3'),[-32.4,7],p('C31','1')],width=.4,role='module supply decoupling')
 wire('3V3',[[-32.4,7],[-31.6,7]],width=.4,role='module supply stitching')
 wire('3V3',[p('C31','1'),[-32,8.45],[-30.025,8.45],p('C32','1')],width=.4,role='parallel local bypass')
 wire('3V3',[[-7.2,2.5],[-22,2.5],[-26.5,7],[-32.4,7]],'In2.Cu',.8,'body-to-radio supply trunk')
 via('GND',[-33.6,7],'module bypass return');wire('GND',[p('C31','2'),[-33.6,8.75],[-33.6,6.7],[-34,6.3],p('U6','1')],width=.35,role='module bypass short return')
 via('GND',[-30.9,9.95],'module bypass return');wire('GND',[p('C32','2'),[-30.175,9.95],p('C31','2')],width=.35,role='shared bypass return')
 # Four ground stitches between the nine EP islands avoid drilling the paste lands.
 epvias=[]
 for x in(-30-.9875,-30+.9875):
  for z in(-.9875,.9875):epvias.append(via('GND',[x,z],'module EP plane stitching'))
 for pad in fps['U6'].Pads():
  if pad.GetNumber()=='49':
   a=[round(pad.GetPosition().x/1e6-100,6),round(100-pad.GetPosition().y/1e6,6)];c=min(epvias,key=lambda c:math.dist(a,c));wire('GND',[a,c],width=.3,role='module EP plane stitching')
 before=meta['board_sha256'];k.SaveBoard(str(P),b);project.write_bytes(pro);meta.update(board_sha256=sha(P),routing_started=True,manual_critical_authored=True);(H/'pcb-state.json').write_text(json.dumps(meta,indent=2)+'\n')
 (H/'critical-copper.json').write_text(json.dumps({'input_board_sha256':before,'board_sha256':sha(P),'objects':items,'locked':True,'source_placement_unchanged':True,'USB_impedance_or_physical_acceptance':False,'nominal_signal_width_mm':.15,'reference_plane':'In1GND; FUSB tracks, adjacentreturn vias at layer changes','manufacturing_note':'Tent/qualify0.2mm through vias and module EP gaps; no unsupported sealing or solder-process credit'},indent=2)+'\n');print('Locked critical copper',len(items),'objects')
if __name__=='__main__':main()
