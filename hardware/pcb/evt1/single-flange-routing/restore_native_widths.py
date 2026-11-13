"""Bounded repair of pass1 automatic neckdown; preserve every other property."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'single-flange.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((H/'pcb-state.json').read_text());assert sha(P)==m['board_sha256']
assert sha(P)=='5e50f4b2cdcee02bae0c4e0ec64a1274964a1838dd09a2bb3b3ee2c8e397d36b'
drc=json.loads((H/'routing/pass1-drc.json').read_text())
ids={v['items'][0]['uuid']for v in drc['violations']if v['type']=='track_width'}
assert len(ids)==31
project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(P))
def signature(t):
 return(t.GetNetname(),t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetWidth(),t.IsLocked(),t.GetDrillValue()if isinstance(t,k.PCB_VIA)else None)
before={t.m_Uuid.AsString():signature(t)for t in b.GetTracks()};changes=[]
for t in b.GetTracks():
 uid=t.m_Uuid.AsString()
 if uid not in ids:continue
 assert not t.IsLocked()and not isinstance(t,k.PCB_VIA)and 0<t.GetWidth()<150000
 changes.append({'uuid':uid,'net':t.GetNetname(),'layer':k.LayerName(t.GetLayer()),'from_mm':k.ToMM(t.GetWidth()),'to_mm':.15})
 t.SetWidth(150000)
after={t.m_Uuid.AsString():signature(t)for t in b.GetTracks()}
assert set(before)==set(after)and len(changes)==31
for uid,a in before.items():
 c=after[uid]
 assert c==(a[:6]+(150000,)+a[7:]if uid in ids else a)
k.SaveBoard(str(P),b);project.write_bytes(pro)
m['board_sha256']=sha(P);(H/'pcb-state.json').write_text(json.dumps(m,indent=2)+'\n')
(H/'routing/native-width-restoration.json').write_text(json.dumps({'source_board_sha256':'5e50f4b2cdcee02bae0c4e0ec64a1274964a1838dd09a2bb3b3ee2c8e397d36b','board_sha256':sha(P),'purpose':'Restore native0.15mm minimum; disable router automatic neckdown for future passes','changes':changes,'all_other_copper_properties_preserved':True},indent=2)+'\n')
print('Restored31 unlocked router necks to0.15mm; all other copper signatures preserved')
