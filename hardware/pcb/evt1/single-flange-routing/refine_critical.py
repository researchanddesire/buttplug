"""Replace only the native-identified authored crossings; preserve all other copper."""
from pathlib import Path
import json,hashlib
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();xy=lambda x,z:k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6))
m=json.loads((H/'pcb-state.json').read_text());assert sha(P)==m['board_sha256'];c=json.loads((H/'critical-copper.json').read_text());project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()};byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
roles={'protected supply trunk','USB series-to-module paired section'};removed=[r for r in c['objects']if r['role']in roles];assert len(removed)==13
for row in removed:
 t=byid[row['uuid']];assert not isinstance(t,k.PCB_VIA)and t.GetNetname()==row['net']and t.IsLocked()and t.GetLayer()==b.GetLayerID(row['layer']);assert t.GetStart()==xy(*row['start'])and t.GetEnd()==xy(*row['end']);b.Delete(t)
c['objects']=[r for r in c['objects']if r['role']not in roles];out=c['objects']
def p(ref,pin):
 q=next(q for q in fps[ref].Pads()if q.GetNumber()==pin);return[round(q.GetPosition().x/1e6-100,6),round(100-q.GetPosition().y/1e6,6)]
def wire(net,points,layer='F.Cu',width=.15,role='critical refinement'):
 for a,z in zip(points,points[1:]):
  t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*z));t.SetWidth(k.FromMM(width));t.SetLayer(b.GetLayerID(layer));t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t);out.append({'kind':'track','uuid':t.m_Uuid.AsString(),'net':net,'layer':layer,'start':a,'end':z,'width_mm':width,'role':role})
def via(net,point,role):
 v=k.PCB_VIA(b);v.SetPosition(xy(*point));v.SetWidth(500000);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v);out.append({'kind':'via','uuid':v.m_Uuid.AsString(),'net':net,'product_XZ_mm':point,'diameter_mm':.5,'drill_mm':.2,'role':role})
wire('VBUS_CHG',[[7.35,3.3],[6,4.65],[6,7.6],[-5.5,7.6],[-5.5,3.5],[-7.2,3.5]],'In2.Cu',.8,'protected supply trunk');wire('VBUS_CHG',[[7.35,3.3],[8.15,3.3]],'In2.Cu',.6,'protected power stitching')
wire('USB_DM',[[-20.1,3.5],[-22,1.6],[-22,-2],[-23.5,-3.5],[-25.5,-3.5],[-26.8,-4.8],[-26.8,-7.1]],role='USB series-to-module paired section')
wire('USB_DP',[[-20.1,6.5],[-22.5,4.1],[-22.5,-1.8],[-23.8,-3.1],[-26,-3.1],[-27.6,-4.7],[-27.6,-7.1]],role='USB series-to-module paired section')
for net,pin,start,end in[('USB_DM','2',[-14,-4.7],[-26.8,-5]),('USB_DP','3',[-15,-4.7],[-27.6,-4.9])]:
 via(net,start,'retained USB service branch');via(net,end,'retained USB service branch');wire(net,[p('J4',pin),start],'B.Cu',.15,'retained USB service branch')
wire('USB_DM',[[-14,-4.7],[-15,-5.7],[-26.1,-5.7],[-26.8,-5]],'In2.Cu',.15,'retained USB service branch')
wire('USB_DP',[[-15,-4.7],[-16,-3.7],[-26.4,-3.7],[-27.6,-4.9]],'In2.Cu',.15,'retained USB service branch')
for point in([-13,-4.7],[-28.8,-4.5]):via('GND',point,'USB service plane return')
wire('GND',[p('J4','1'),[-13,-4.7]],'B.Cu',.35,'USB service plane return')
prior=m['board_sha256'];k.SaveBoard(str(P),b);project.write_bytes(pro);m['board_sha256']=sha(P);m['critical_preflight_refined']=True;(H/'pcb-state.json').write_text(json.dumps(m,indent=2)+'\n');c['board_sha256']=sha(P);c['refinement']={'input_board_sha256':prior,'native_report_sha256':sha(H/'critical-preflight-drc.json'),'removed_only_authored_UUIDs':[r['uuid']for r in removed],'unchanged_other_copper_UUIDs_preserved':True,'retained_J4_USB_branches':True};(H/'critical-copper.json').write_text(json.dumps(c,indent=2)+'\n');print('Refined only authored crossings;',len(out),'protected objects')
