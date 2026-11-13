"""Local device-PCB repairs; native KiCad DRC is the acceptance check.

Run with KiCad7 Python. Routes on one existing signal layer around fixed
copper/pads/holes, preserving component placement and reference-plane layers.
This is a bounded layout aid, not a substitute for native connectivity/DRC.
"""
import argparse
import functools
import heapq
import json
import math
from pathlib import Path
import build_evt1_device_pcbs as m
k=m.k


def distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];ll=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll)) if ll else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


class Router:
    def __init__(self,b,net,layer,width,ignore=()):
        self.poly=m.board_outline(b);self.segments=[];self.circles=[];self.boxes=[]
        half=width/2
        for t in b.GetTracks():
            if t.m_Uuid.AsString() in ignore or t.GetNetname()==net:continue
            if isinstance(t,k.PCB_VIA):
                r=max(half+.105+k.ToMM(t.GetWidth())/2,half+.255+k.ToMM(t.GetDrillValue())/2)
                self.circles.append((m.mech(t.GetPosition()),r))
            elif t.GetLayer()==layer:
                self.segments.append((m.mech(t.GetStart()),m.mech(t.GetEnd()),half+k.ToMM(t.GetWidth())/2+.105))
        zones=list(b.Zones())
        for f in b.GetFootprints():
            zones.extend(list(f.Zones()))
            for p in f.Pads():
                if p.GetNetname()!=net and p.GetLayerSet().Contains(layer):
                    bb=p.GetBoundingBox();a=m.mech(bb.GetOrigin());c=m.mech(bb.GetEnd());r=half+.105
                    self.boxes.append((a[0]-r,c[1]-r,c[0]+r,a[1]+r))
                if p.GetDrillSize().x:
                    self.circles.append((m.mech(p.GetPosition()),half+.255+k.ToMM(p.GetDrillSize().x)/2))
        for z in zones:
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.GetLayerSet().Contains(layer):
                bb=z.GetBoundingBox();a=m.mech(bb.GetOrigin());c=m.mech(bb.GetEnd());r=half+.01
                self.boxes.append((a[0]-r,c[1]-r,c[0]+r,a[1]+r))
        self.edge=half+.325

    def clear(self,p):
        inside=False
        for a,c in zip(self.poly,self.poly[1:]+self.poly[:1]):
            if (a[1]>p[1])!=(c[1]>p[1]) and p[0]<(c[0]-a[0])*(p[1]-a[1])/(c[1]-a[1])+a[0]:inside=not inside
            if distance(p,a,c)<self.edge:return False
        if not inside:return False
        if any(a<=p[0]<=c and e<=p[1]<=f for a,e,c,f in self.boxes):return False
        if any(math.dist(p,c)<r for c,r in self.circles):return False
        if any(distance(p,a,c)<r for a,c,r in self.segments):return False
        return True

    def line(self,a,c):
        n=max(1,math.ceil(math.dist(a,c)/.025))
        return all(self.clear((a[0]+(c[0]-a[0])*i/n,a[1]+(c[1]-a[1])*i/n)) for i in range(n+1))

    def route(self,start,end,step=.05,margin=2):
        assert self.clear(start),('Blocked endpoint',start)
        assert self.clear(end),('Blocked endpoint',end)
        target=(round((end[0]-start[0])/step),round((end[1]-start[1])/step))
        point=lambda n:(start[0]+step*n[0],start[1]+step*n[1])
        @functools.lru_cache(None)
        def clear(n):return self.clear(point(n))
        lo=[min(start[i],end[i])-margin for i in range(2)];hi=[max(start[i],end[i])+margin for i in range(2)]
        heap=[(math.dist(start,end),0,(0,0))];cost={(0,0):0};parent={};finish=None
        while heap:
            _,g,node=heapq.heappop(heap)
            if g>cost[node]+1e-9:continue
            p=point(node)
            if math.dist(p,end)<step*1.1 and self.line(p,end):finish=node;break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
                nxt=(node[0]+dx,node[1]+dy);q=point(nxt)
                if not all(lo[i]<=q[i]<=hi[i] for i in range(2)) or not clear(nxt):continue
                if not self.clear(((p[0]+q[0])/2,(p[1]+q[1])/2)):continue
                ng=g+step*math.hypot(dx,dy)
                if ng>=cost.get(nxt,math.inf)-1e-9:continue
                cost[nxt]=ng;parent[nxt]=node;heapq.heappush(heap,(ng+math.dist(q,end),ng,nxt))
        if finish is None:raise RuntimeError(('No local route',start,end))
        nodes=[finish]
        while nodes[-1]!=(0,0):nodes.append(parent[nodes[-1]])
        pts=[point(n) for n in reversed(nodes)]+[end]
        merged=[]
        for p in pts:
            if merged and math.dist(p,merged[-1])<1e-8:continue
            while len(merged)>=2:
                a,c=merged[-2:];cross=(c[0]-a[0])*(p[1]-c[1])-(c[1]-a[1])*(p[0]-c[0])
                if abs(cross)>1e-8:break
                merged.pop()
            merged.append(p)
        assert all(self.line(a,c) for a,c in zip(merged,merged[1:]))
        return merged


def tracks(b,net,layer,width,points):
    for a,c in zip(points,points[1:]):
        if math.dist(a,c)<1e-7:continue
        t=k.PCB_TRACK(b);t.SetStart(m.xy(*a));t.SetEnd(m.xy(*c));t.SetWidth(k.FromMM(width))
        t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)


def move_part(b,ref,position):
    """Move an SMD part and replace its directly attached terminal segments."""
    f=next(f for f in b.GetFootprints() if f.GetReference()==ref);old=m.mech(f.GetPosition());connections=[];deleted={}
    for p in f.Pads():
        center=m.mech(p.GetPosition());radius=max(k.ToMM(p.GetSize().x),k.ToMM(p.GetSize().y))/2+.02
        for t in b.GetTracks():
            if isinstance(t,k.PCB_VIA) or t.GetNetname()!=p.GetNetname() or not p.GetLayerSet().Contains(t.GetLayer()):continue
            a,c=m.mech(t.GetStart()),m.mech(t.GetEnd())
            if math.dist(a,center)<=radius:connections.append((p.GetNumber(),t.GetLayer(),k.ToMM(t.GetWidth()),c));deleted[t.m_Uuid.AsString()]=t
            elif math.dist(c,center)<=radius:connections.append((p.GetNumber(),t.GetLayer(),k.ToMM(t.GetWidth()),a));deleted[t.m_Uuid.AsString()]=t
    assert connections,('No part terminal segments found',ref)
    for t in deleted.values():b.Delete(t)
    f.SetPosition(m.xy(*position));paths=[]
    for number,ly,w,end in connections:
        p=next(p for p in f.Pads() if p.GetNumber()==number);start=m.mech(p.GetPosition());net=p.GetNetname()
        route=Router(b,net,ly,w).route(start,end,margin=4);tracks(b,net,ly,w,route)
        paths.append({'pad':number,'net':net,'layer':b.GetLayerName(ly),'points':route})
    return {'action':'move_part','ref':ref,'from_xy_mm':old,'to_xy_mm':position,'terminal_routes':paths}


def reroute(b,uid):
    t=next(t for t in b.GetTracks() if t.m_Uuid.AsString()==uid)
    assert not isinstance(t,k.PCB_VIA)
    a,c=m.mech(t.GetStart()),m.mech(t.GetEnd());net=t.GetNetname();ly=t.GetLayer();w=k.ToMM(t.GetWidth())
    selected={uid:t}
    router=Router(b,net,ly,w,selected)
    # A crossing at a shared vertex requires replacing the neighboring segment
    # as well. Extend only along an unbranched same-layer chain.
    for _ in range(24):
        vertices={}
        for q in selected.values():
            for p in (m.mech(q.GetStart()),m.mech(q.GetEnd())):vertices[tuple(p)]=vertices.get(tuple(p),0)+1
        ends=[p for p,n in vertices.items() if n==1]
        assert len(ends)==2,('Local chain branches',uid,ends)
        blocked=[p for p in ends if not router.clear(p)]
        if not blocked:break
        added=False
        for p in blocked:
            for q in b.GetTracks():
                if isinstance(q,k.PCB_VIA) or q.GetNetname()!=net or q.GetLayer()!=ly or q.m_Uuid.AsString() in selected:continue
                if min(math.dist(m.mech(q.GetStart()),p),math.dist(m.mech(q.GetEnd()),p))<1e-6:
                    selected[q.m_Uuid.AsString()]=q;added=True
        assert added,('Blocked endpoint is not an extendable track junction',blocked)
    points=router.route(ends[0],ends[1])
    for q in selected.values():b.Delete(q)
    tracks(b,net,ly,w,points)
    return {'action':'segment','old_uuids':list(selected),'net':net,'layer':b.GetLayerName(ly),'width_mm':w,'points_xy_mm':points}


def move_via(b,uid):
    via=next(t for t in b.GetTracks() if t.m_Uuid.AsString()==uid);assert isinstance(via,k.PCB_VIA)
    old=m.mech(via.GetPosition());net=via.GetNetname();diam=k.ToMM(via.GetWidth())
    routers=[Router(b,net,ly,diam,(uid,)) for ly in b.GetEnabledLayers().CuStack()]
    candidates=[(old[0]+i*.1,old[1]+j*.1) for i in range(-12,13) for j in range(-12,13) if i or j]
    candidates.sort(key=lambda p:math.dist(p,old))
    new=next((p for p in candidates if all(r.clear(p) for r in routers)),None)
    if new is None:raise RuntimeError(('No via position',old,net))
    connections=[]
    for t in list(b.GetTracks()):
        if isinstance(t,k.PCB_VIA) or t.GetNetname()!=net:continue
        a,c=m.mech(t.GetStart()),m.mech(t.GetEnd())
        if math.dist(a,old)<1e-6:connections.append((t,c))
        elif math.dist(c,old)<1e-6:connections.append((t,a))
    assert connections,('Via has no terminal segments',uid)
    paths=[]
    for t,end in connections:
        ly=t.GetLayer();w=k.ToMM(t.GetWidth());r=Router(b,net,ly,w,(uid,t.m_Uuid.AsString()))
        points=r.route(new,end);paths.append((t,ly,w,points))
    via.SetPosition(m.xy(*new))
    for t,ly,w,points in paths:b.Delete(t);tracks(b,net,ly,w,points)
    return {'action':'via','uuid':uid,'net':net,'from_xy_mm':old,'to_xy_mm':new}


def ground(b,identifier,domain):
    ref,number=identifier.split('.')
    f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
    pad=next(p for p in f.Pads() if p.GetNumber()==number);assert pad.GetNetname()=='GND'
    start=m.mech(pad.GetPosition());layer=f.GetLayer();diam,drill=(.6,.3) if domain=='flange' else (.5,.2)
    probes=[Router(b,'GND',ly,diam) for ly in b.GetEnabledLayers().CuStack()]
    surface=Router(b,'GND',layer,.15)
    candidates=[(start[0]+i*.1,start[1]+j*.1) for i in range(-20,21) for j in range(-20,21)]
    candidates.sort(key=lambda p:math.dist(p,start))
    def avoids_smd_hole(p):
        # Hand-solder loom lands can use a plated via in the land. Reflow pads
        # retain a small mask/drill separation to avoid solder wicking.
        for fp in b.GetFootprints():
            if fp.GetReference() in ('J81','J82'):continue
            for q in fp.Pads():
                if q.GetNetname()!='GND':continue
                bb=q.GetBoundingBox();a=m.mech(bb.GetOrigin());c=m.mech(bb.GetEnd())
                dx=max(a[0]-p[0],0,p[0]-c[0]);dy=max(c[1]-p[1],0,p[1]-a[1])
                if math.hypot(dx,dy)<drill/2+.075:return False
        return True
    valid=[p for p in candidates if all(r.clear(p) for r in probes) and avoids_smd_hole(p)]
    chosen=next((p for p in valid if surface.line(start,p)),None);points=None
    if chosen is not None:points=[start,chosen]
    else:
        for p in valid[:12]:
            try:points=surface.route(start,p);chosen=p;break
            except (AssertionError,RuntimeError):continue
    if chosen is None:raise RuntimeError(('No GND escape',identifier,len(valid)))
    tracks(b,'GND',layer,.15,points)
    v=k.PCB_VIA(b);v.SetPosition(m.xy(*chosen));v.SetWidth(k.FromMM(diam));v.SetDrill(k.FromMM(drill))
    v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet('GND'));b.Add(v)
    return {'action':'ground','pad':identifier,'via_xy_mm':chosen,'via_diameter_drill_mm':[diam,drill],
            'layer':b.GetLayerName(layer),'track_xy_mm':points,'hand_land_via_in_pad':ref in ('J81','J82') and math.dist(chosen,start)<.1}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('domain',choices=('body','flange'))
    ap.add_argument('kind',choices=('segment','via','ground'));ap.add_argument('uuids',nargs='+');a=ap.parse_args()
    path=m.boardpath(a.domain);before=m.sha(path);b=k.LoadBoard(str(path));rows=[]
    for uid in a.uuids:
        row=ground(b,uid,a.domain) if a.kind=='ground' else (reroute if a.kind=='segment' else move_via)(b,uid)
        rows.append(row);print(row,flush=True)
    m.save(b,a.domain);b=k.LoadBoard(str(path));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());m.save(b,a.domain)
    log=path.parent/'routing-adjustments.json';old=json.loads(log.read_text()) if log.exists() else []
    old.append({'before_sha256':before,'after_sha256':m.sha(path),'repairs':rows,'native_DRC_required':True})
    log.write_text(json.dumps(old,indent=2)+'\n')


if __name__=='__main__':main()
