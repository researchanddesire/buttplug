"""Replace the long input-cap feed detour with a direct low-R connection."""
import json
import math
import sys
from pathlib import Path
import build_pcbs as m
from route_pcbs import ctx
k=m.k
folder,path,b=ctx(sys.argv[1]);before=m.sha(path)
oldsegments=[((-38,109.1),(-35.8,109.1)),((-35.8,109.1),(-35.8,104.525)),((-35.8,104.525),(-38,104.525))]
removed=[]
for t in list(b.GetTracks()):
    if t.GetNetname()!='UV_5V_SW':continue
    if isinstance(t,k.PCB_VIA):
        if math.dist(m.dock(t.GetPosition()),(-38,109.1))<1e-5:removed.append(t.m_Uuid.AsString());b.Delete(t)
    else:
        ends=(m.dock(t.GetStart()),m.dock(t.GetEnd()))
        if any(set(ends)==set(seg)for seg in oldsegments):removed.append(t.m_Uuid.AsString());b.Delete(t)
        elif t.GetLayer()==k.F_Cu and set(ends)=={(-38,131.6),(-38,109.1)}:
            t.SetStart(m.xy(-38,131.6));t.SetEnd(m.xy(-38,102.3));removed.append('extended:'+t.m_Uuid.AsString())
assert len(removed)==5,removed
m.via(b,'UV_5V_SW',(-38,102.3));m.track(b,'UV_5V_SW',[(-38,102.3),(-38,104.525)],k.B_Cu,.6)
m.save(b,path)
(folder/'rail-improvement.json').write_text(json.dumps({'before_sha256':before,'after_sha256':m.sha(path),
    'script_sha256':m.sha(Path(__file__)),'removed_or_extended_UUIDs':removed,
    'old_B_feed_length_width_mm':[8.975,.4],'new_B_feed_length_width_mm':[2.225,.6],
    'new_cap_via_planar_mm':[-38,102.3],
    'scope':'Routing only; no change to SW/COMP/FB or components/source'},indent=2)+'\n')
print('Improved input-cap feed',sys.argv[1])
