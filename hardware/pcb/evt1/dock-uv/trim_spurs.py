"""Trim native-DRC-listed free track tails to their connected anchors only."""
import json
import math
import sys
from pathlib import Path
import build_pcbs as m
from route_pcbs import ctx
from repair_routes import distance
k=m.k
folder,path,b=ctx(sys.argv[1]);before=m.sha(path);report=json.loads((folder/'native-drc.json').read_text());rows=[]
for finding in report['violations']:
    assert finding['type']=='track_dangling','Resolve non-tail findings separately'
    uid=finding['items'][0]['uuid'];t=next(t for t in b.GetTracks()if t.m_Uuid.AsString()==uid)
    assert not isinstance(t,k.PCB_VIA)
    a,c=m.dock(t.GetStart()),m.dock(t.GetEnd());d=(c[0]-a[0],c[1]-a[1]);ll=d[0]**2+d[1]**2;anchors=[]
    def anchor(p):
        if distance(p,a,c)>.005:return
        u=((p[0]-a[0])*d[0]+(p[1]-a[1])*d[1])/ll
        if -.0001<=u<=1.0001:anchors.append((max(0,min(1,u)),p))
    for f in b.GetFootprints():
        for pad in f.Pads():
            if pad.GetNetname()==t.GetNetname()and pad.GetLayerSet().Contains(t.GetLayer()):anchor(m.dock(pad.GetPosition()))
    for q in b.GetTracks():
        if q.m_Uuid.AsString()==uid or q.GetNetname()!=t.GetNetname():continue
        if isinstance(q,k.PCB_VIA):anchor(m.dock(q.GetPosition()))
        elif q.GetLayer()==t.GetLayer():
            anchor(m.dock(q.GetStart()));anchor(m.dock(q.GetEnd()))
    assert anchors,(uid,'no connectedanchor')
    low,high=min(anchors),max(anchors)
    assert high[0]-low[0]<.999,'Both original endpoints connected; do not remove this track'
    if math.dist(low[1],high[1])<.005:b.Delete(t);action='delete free spur'
    else:t.SetStart(m.xy(*low[1]));t.SetEnd(m.xy(*high[1]));action='trim to surviving anchors'
    rows.append({'uuid':uid,'net':t.GetNetname()if action!='delete free spur'else finding['items'][0]['description'],'action':action,'anchors':anchors})
m.save(b,path)
(folder/'spur-trim.json').write_text(json.dumps({'before_sha256':before,'after_sha256':m.sha(path),'script_sha256':m.sha(Path(__file__)),'native_findings_only':rows},indent=2)+'\n')
print('Trimmed',len(rows),'native-listed free tails')
