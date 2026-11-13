"""Authorized two-part mate-path repair; guarded critical USB reconstruction."""
from pathlib import Path
import hashlib,json,math,shutil
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3];P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/j7-mate-trial/combined-review.json';pr=json.loads(proof.read_text());native=proof.parent/'CombinedClearanceTrial.FCStd'
assert pr['repair_positions_XZ_mm']=={'U75':[6.3,9],'U71':[-1,-7]}
assert sha(native)==pr['native_sha256']=='dfc2dc4259e04644e73bd546e336e8d87d6070c07d4d4c53d3bcc2cfcee5ed3e'
assert len(pr['sampled_mating_poses'])==59 and all(not x['clashes']and not x['tip_section_access_clashes']for x in pr['sampled_mating_poses'])
meta=json.loads((H/'pcb-state.json').read_text());before=sha(P);assert before==meta['board_sha256']=='c7fa8519054089a71cad11b55d2593b30dd79a87b650c82507b3cde8f903b769'
project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()}
def xy(x,z):return k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6))
def uid(t):return t.m_Uuid.AsString()
def sig(t):return(t.GetNetname(),t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetWidth(),t.IsLocked(),t.GetDrillValue()if isinstance(t,k.PCB_VIA)else None)
def p(ref,n):
 q=next(q for q in fps[ref].Pads()if q.GetNumber()==n);return[round(q.GetPosition().x/1e6-100,6),round(100-q.GetPosition().y/1e6,6)]
original={uid(t):sig(t)for t in b.GetTracks()};critical=json.loads((H/'critical-copper.json').read_text());replace_roles={'USB ESD fanout','USB contact fanout','USB ESD channel landing','USB contact-to-series paired section','ESD short ground return','ESD VBUS bias','PTC to diode anode'}
removed={r['uuid']:'rebuild '+r['role']for r in critical['objects']if r['role']in replace_roles};assert len(removed)==32
# Retire only general routes physically terminating on the former U71 pads.
for t in b.GetTracks():
 if t.IsLocked():continue
 if any(t.IsOnLayer(k.B_Cu)and k.SHAPE.Collide(t.GetEffectiveShape(k.B_Cu),q.GetEffectiveShape(k.B_Cu),0)for q in fps['U71'].Pads()):removed[uid(t)]='old U71 terminal route after1mm translation'
for t in list(b.GetTracks()):
 if uid(t)in removed:b.Delete(t)
positions={'U75':{'old':[-1,4],'new':[6.3,9]},'U71':{'old':[-1,-6],'new':[-1,-7]}}
for ref,d in positions.items():
 assert fps[ref].GetPosition()==xy(*d['old']);fps[ref].SetPosition(xy(*d['new']))
planned=[]
def wire(net,points,layer='B.Cu',width=.15,role='revised USB critical'):
 for a,c in zip(points,points[1:]):
  if a==c:continue
  t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*c));t.SetWidth(k.FromMM(width));t.SetLayer(b.GetLayerID(layer));t.SetNet(b.FindNet(net));t.SetLocked(True)
  planned.append((t,{'kind':'track','uuid':uid(t),'net':net,'layer':layer,'start':a,'end':c,'width_mm':width,'role':role}))
def via(net,pt,role):
 v=k.PCB_VIA(b);v.SetPosition(xy(*pt));v.SetWidth(500000);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True)
 planned.append((v,{'kind':'via','uuid':uid(v),'net':net,'product_XZ_mm':pt,'diameter_mm':.5,'drill_mm':.2,'role':role}))
esd={1:[4.05,8.5],3:[4.4,9.95],6:[8.55,8.05],4:[8.55,9.95]}
for pin,pt in esd.items():
 net='USB_DM_CONTACT'if pin in(1,6)else'USB_DP_CONTACT';via(net,pt,'relocated ESD fanout');wire(net,[p('U75',str(pin)),pt],role='relocated ESD fanout')
for a,c,net in[(1,6,'USB_DM_CONTACT'),(3,4,'USB_DP_CONTACT')]:wire(net,[p('U75',str(a)),p('U75',str(c))],role='ESD pass-through row')
wire('USB_DM_CONTACT',[p('CT2','1'),[-8.2,8.2],[-6,8.2],[-5,7.2],[0,7.2],[1,5.9],[3.5,5.9],esd[1]],'F.Cu',.15,'contact to ESD entry')
wire('USB_DP_CONTACT',[p('CT3','1'),[-2,12],[4.4,12],esd[3]],'F.Cu',.15,'contact to ESD entry')
wire('USB_DM_CONTACT',[esd[6],[9.5,7.1],[9.5,4.4],[7,4.4],[5,2.4],[5,1.6],[-15.6,1.6],[-17.5,3.5]],'F.Cu',.15,'ESD to22R paired section')
wire('USB_DP_CONTACT',[esd[4],[10,8.5],[10,4],[7.2,4],[5.4,2.2],[5.4,1.25],[-16,1.25],[-18.2,3.45],[-18.2,5.8],[-17.5,6.5]],'F.Cu',.15,'ESD to22R paired section')
via('GND',[4.4,9.15],'relocated ESD plane return');wire('GND',[p('U75','2'),[4.4,9.15]],width=.3,role='relocated ESD plane return')
via('DOCK_5V',[8.2,9],'relocated ESD bias');wire('DOCK_5V',[p('U75','5'),[8.2,9]],width=.3,role='relocated ESD bias')
wire('DOCK_5V',[[8.2,9],[9.3,9],[9.3,2.5],[8.4,1.6],[4.2,1.6],[2.6,3.2],[2.6,6.7]],'In2.Cu',.3,'relocated ESD bias')
wire('DOCK_FUSED',[p('F1','2'),[5.4,5.9],[6.6,7.1],[9.95,7.1],[10.65,6.4],p('D1','1')],width=.6,role='PTC to diode anode relocated beneath ESD')
# Identify actual foreign-copper blockers; only newly autorouted unlocked objects
# may be retired. Every unaffected UUID/property is checked before saving.
layers=(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu);conflicts=[];pads=[q for f in b.GetFootprints()for q in f.Pads()]
for o,record in planned:
 for layer in layers:
  if not o.IsOnLayer(layer):continue
  shape=o.GetEffectiveShape(layer)
  for q in pads:
   if q.IsOnLayer(layer)and q.GetNetCode()!=o.GetNetCode()and k.SHAPE.Collide(shape,q.GetEffectiveShape(layer),200000 if q.GetAttribute()==k.PAD_ATTRIB_NPTH else 150000):conflicts.append({'planned':record,'pad':q.GetParent().GetReference()+'.'+q.GetNumber()})
  for t in b.GetTracks():
   if not t.IsOnLayer(layer)or t.GetNetCode()==o.GetNetCode():continue
   if k.SHAPE.Collide(shape,t.GetEffectiveShape(layer),150000):
    if t.IsLocked():conflicts.append({'planned':record,'protected_copper':uid(t)})
    else:removed[uid(t)]='general routing intersected reconstructed ESD critical copper'
# New pads may intersect old general routes after the two translations.
for ref in positions:
 for q in fps[ref].Pads():
  for t in b.GetTracks():
   if not t.IsOnLayer(k.B_Cu)or t.GetNetCode()==q.GetNetCode():continue
   if k.SHAPE.Collide(q.GetEffectiveShape(k.B_Cu),t.GetEffectiveShape(k.B_Cu),150000):
    if t.IsLocked():conflicts.append({'moved_pad':ref+'.'+q.GetNumber(),'protected_copper':uid(t)})
    else:removed[uid(t)]='general routing intersected translated pad'
# Validate planned foreign-net intersections independently of old/general routing.
for i,(o,rec)in enumerate(planned):
 for t,other in planned[:i]:
  if t.GetNetCode()==o.GetNetCode():continue
  if any(o.IsOnLayer(l)and t.IsOnLayer(l)and k.SHAPE.Collide(o.GetEffectiveShape(l),t.GetEffectiveShape(l),150000)for l in layers):conflicts.append({'planned':rec,'other_new':other})
(H/'routing/connector-repair-preflight.json').write_text(json.dumps({'input_board_sha256':before,'conflicts':conflicts,'proposed_removed_UUIDs':removed},indent=2)+'\n')
assert not conflicts,'Critical repair preflight failed; native PCB NOT saved'
for t in list(b.GetTracks()):
 if uid(t)in removed:b.Delete(t)
for o,_ in planned:b.Add(o)
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
current={uid(t):sig(t)for t in b.GetTracks()};assert all(current.get(u)==v for u,v in original.items()if u not in removed)
archive=H/'routing/before-connector-repair.kicad_pcb';assert not archive.exists();shutil.copyfile(P,archive);shutil.copyfile(H/'critical-copper.json',H/'routing/before-connector-repair-critical.json')
k.SaveBoard(str(P),b);project.write_bytes(pro);meta.update(board_sha256=sha(P),authorized_placement_exceptions=positions);(H/'pcb-state.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'input_board_sha256':before,'board_sha256':sha(P),'frozen_study_board_sha256':meta['frozen_study_board_sha256'],'authorization':'Root-approved two-part repair after independent native placement DRC and UV59-pose mating proof','positions_product_XZ_mm':positions,'all_other_footprints_and_models_unchanged':True,'mechanical_proof_path':str(proof.relative_to(ROOT)),'mechanical_proof_sha256':sha(proof),'mechanical_native_sha256':sha(native),'disposable_native_placement_DRC_sha256':sha(Path('/private/tmp/compass-flange-courtyard-trial/drc.json')),'removed_copper':[{'uuid':u,'reason':v,'original_signature':original[u]}for u,v in removed.items()],'preserved_original_copper':len(original)-len(removed),'replacement_critical':len(planned),'all_other_copper_properties_preserved':True,'native_full_DRC_required':True}
(H/'connector-clearance-repair.json').write_text(json.dumps(report,indent=2)+'\n')
critical['objects']=[r for r in critical['objects']if r['uuid']not in removed]+[r for _,r in planned];critical.update(board_sha256=sha(P),source_placement_unchanged=False,authorized_two_part_repair_sha256=sha(H/'connector-clearance-repair.json'));(H/'critical-copper.json').write_text(json.dumps(critical,indent=2)+'\n');print('Applied exact2-part translation; guarded copper repair',len(planned),'new objects')
