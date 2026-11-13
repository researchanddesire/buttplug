"""Intentional local C71 bypass after the authorized reset-IC translation."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((H/'pcb-state.json').read_text());before=sha(P);assert before==m['board_sha256'];drc=json.loads((H/'drc.json').read_text());assert not drc['violations']and not drc['unconnected_items']
project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(P));planned=[]
def xy(x,z):return k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6))
def wire(net,ps,w,role):
 for a,c in zip(ps,ps[1:]):
  t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*c));t.SetWidth(k.FromMM(w));t.SetLayer(k.B_Cu);t.SetNet(b.FindNet(net));t.SetLocked(True);planned.append((t,{'kind':'track','uuid':t.m_Uuid.AsString(),'net':net,'layer':'B.Cu','start':a,'end':c,'width_mm':w,'role':role}))
def via(pt,role):
 v=k.PCB_VIA(b);v.SetPosition(xy(*pt));v.SetWidth(500000);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet('GND'));v.SetLocked(True);planned.append((v,{'kind':'via','uuid':v.m_Uuid.AsString(),'net':'GND','product_XZ_mm':pt,'diameter_mm':.5,'drill_mm':.2,'role':role}))
wire('3V3',[[-.7,-6.5],[-.2,-6.5],[-.2,-8.2],[-1.48,-8.2],[-1.48,-9]],.2,'reset local bypass supply')
wire('GND',[[-.52,-9],[.3,-9]],.25,'reset capacitor direct plane return');via([.3,-9],'reset capacitor direct plane return')
wire('GND',[[-1.3,-7],[-.7,-7],[-.7,-7.5]],.2,'reset package ground tie');wire('GND',[[-1.3,-7],[-2.2,-7]],.2,'reset package direct plane return');via([-2.2,-7],'reset package direct plane return')
layers=(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu);existing=list(b.GetTracks())+[p for f in b.GetFootprints()for p in f.Pads()];conflicts=[]
for t,r in planned:
 for o in existing:
  if t.GetNetCode()==o.GetNetCode():continue
  if any(t.IsOnLayer(l)and o.IsOnLayer(l)and k.SHAPE.Collide(t.GetEffectiveShape(l),o.GetEffectiveShape(l),150000)for l in layers):conflicts.append({'planned':r,'other':o.m_Uuid.AsString()})
for i,(t,r)in enumerate(planned):
 for o,q in planned[:i]:
  if t.GetNetCode()!=o.GetNetCode()and any(t.IsOnLayer(l)and o.IsOnLayer(l)and k.SHAPE.Collide(t.GetEffectiveShape(l),o.GetEffectiveShape(l),150000)for l in layers):conflicts.append({'planned':r,'other_planned':q})
(H/'routing/reset-bypass-preflight.json').write_text(json.dumps({'input_board_sha256':before,'conflicts':conflicts},indent=2)+'\n');assert not conflicts,'PCB NOT saved; refine local paths before mutation'
for t,r in planned:b.Add(t)
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(P),b);project.write_bytes(pro);m['board_sha256']=sha(P);(H/'pcb-state.json').write_text(json.dumps(m,indent=2)+'\n')
c=H/'critical-copper.json';r=json.loads(c.read_text());r['objects']+=[q for _,q in planned];r['board_sha256']=sha(P);c.write_text(json.dumps(r,indent=2)+'\n');(H/'routing/reset-bypass.json').write_text(json.dumps({'input_board_sha256':before,'board_sha256':sha(P),'added':[r for _,r in planned],'all_preexisting_copper_preserved':True,'C71_VDD_route_mm':4.28,'C71_direct_GND_return_mm':.82,'purpose':'Avoid two via transitions/remote path in the local100nF reset bypass after the authorized U71 move; actual high-frequency supply behaviour remains to measure'},indent=2)+'\n');print('Authored',len(planned),'local reset bypass objects; no preexisting copper changed')
