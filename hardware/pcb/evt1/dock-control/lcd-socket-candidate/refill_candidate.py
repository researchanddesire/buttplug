"""One bounded clearance repair and actual native zone refill, candidate only."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent
P=H/'dock-lid-jst-candidate.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(P);b=k.LoadBoard(str(P))
matches=[t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and t.GetNetname()=='3V3_UI'and t.GetPosition().x==k.FromMM(106.8)and t.GetPosition().y in (k.FromMM(85.125),k.FromMM(85.175))]
assert len(matches)==1,'Repair applies once to the source via, never silently reroutes other copper'
old=matches[0].GetPosition()
new=k.VECTOR2I(k.FromMM(106.9),k.FromMM(85.175))
changes=[]
for t in b.GetTracks():
    if t.GetNetname()!='3V3_UI':continue
    if isinstance(t,k.PCB_VIA):
        if t.GetPosition()==old:t.SetPosition(new);changes.append('supply via +0.100 mm dockX, restore original dockY')
    else:
        if t.GetStart()==old:t.SetStart(new);changes.append('connected supply track start')
        if t.GetEnd()==old:t.SetEnd(new);changes.append('connected supply track end')
assert changes.count('supply via +0.100 mm dockX, restore original dockY')==1,changes
k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(P),b)
(H/'local-repair.json').write_text(json.dumps({'before_board_sha256':before,'after_board_sha256':sha(P),'reason':'JST signal land length grows .8 to 1.1 mm; move one local supply via 0.10 mm in dockX away from pin27 and refill existing zones','changes':changes,'all_other_tracks_pads_placements_preserved':True,'tool_sha256':sha(Path(__file__))},indent=2)+'\n')
print(json.dumps({'changes':changes,'board_sha256':sha(P)}))
