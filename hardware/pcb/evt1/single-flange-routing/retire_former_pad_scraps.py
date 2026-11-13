"""Retire exactly three SES rounding scraps on the former U75 pads.

Their new native-search connections are removed with them. No retained pad,
source copper, via or junction is removed; every other copper signature is held.
"""
from pathlib import Path
import hashlib,json,sys
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();state=json.loads((H/'pcb-state.json').read_text());before=sha(P);assert before==state['board_sha256']=='2c9b69ff9e7879e507023eff27e374fbcef0899acf7da658af54e20bf99c5579'
repair=json.loads((H/'connector-clearance-repair.json').read_text());old=s.parse((H/'routing/before-connector-repair.kicad_pcb').read_text());oldids={s.value(t,'tstamp')for t in old if isinstance(t,list)and s.tag(t)in('segment','via')};critical=json.loads((H/'critical-copper.json').read_text());criticalids={r['uuid']for r in critical['objects']};preexisting=(oldids-{r['uuid']for r in repair['removed_copper']})|criticalids
scraps={'c2841b25-82f5-41be-aa02-f74b01fa5d2c':'DOCK_5V','d8f5de07-6675-4d7e-becb-519ce45e88e7':'USB_DM_CONTACT','9ebec31b-7a72-4cc4-85ad-eea471f30268':'USB_DP_CONTACT'}
# Exact former pad6,4,5 native locations, independent of the current footprint.
centres={'DOCK_5V':(100137500,96000000),'USB_DM_CONTACT':(100137500,96950000),'USB_DP_CONTACT':(100137500,95050000)}
project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(P));uid=lambda t:t.m_Uuid.AsString()
def signature(t):return(t.GetNetname(),t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetWidth(),t.IsLocked(),t.GetDrillValue()if isinstance(t,k.PCB_VIA)else None)
original={uid(t):signature(t)for t in b.GetTracks()};remove=[]
for t in b.GetTracks():
 u=uid(t)
 if u in scraps:
  assert t.GetNetname()==scraps[u]and not t.IsLocked()and t.GetLayer()==k.B_Cu and not isinstance(t,k.PCB_VIA)
  assert abs(t.GetLength()-500)<=1 and t.GetWidth()==150000
  x,y=centres[t.GetNetname()];assert(t.GetStart()-k.VECTOR2I(x,y)).EuclideanNorm()<=501 and(t.GetEnd()-k.VECTOR2I(x,y)).EuclideanNorm()<=501
  remove.append(u)
 elif u not in preexisting and t.GetNetname()in set(scraps.values()):
  assert t.IsLocked()and not isinstance(t,k.PCB_VIA)and t.GetLayer()==k.B_Cu
  remove.append(u)
assert set(scraps)<=set(remove)and not criticalids&set(remove)
for t in list(b.GetTracks()):
 if uid(t)in remove:b.Delete(t)
current={uid(t):signature(t)for t in b.GetTracks()};assert set(current)==set(original)-set(remove);assert all(v==original[u]for u,v in current.items())
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(P),b);project.write_bytes(pro);state['board_sha256']=sha(P);(H/'pcb-state.json').write_text(json.dumps(state,indent=2)+'\n')
r={'input_board_sha256':before,'board_sha256':sha(P),'reason':'Three0.0005mm SES quantization fragments belonged to former U75 pads; connecting them after component translation would create dead USB/power branches. Only these scraps and the immediately preceding native-search routes to them are retired.','former_pad_scraps':scraps,'removed_copper':[{'uuid':u,'signature':original[u]}for u in remove],'all_other_copper_properties_preserved':True,'retained_pads_removed':0,'critical_copper_removed':0,'native_full_DRC_required':True};(H/'routing/former-pad-scrap-retirement.json').write_text(json.dumps(r,indent=2)+'\n');print('Retired',len(remove),'objects:3rounding scraps +their new dead branches')
