"""Bounded two-layer repairs; final acceptance is native KiCad10 DRC."""
import collections
import functools
import heapq
import json
import math
import sys
import build_pcbs as m
from route_pcbs import ctx
k=m.k

def distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];ll=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll))if ll else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

class Router:
    def __init__(self,board,net,width=.25):
        self.width=width;self.net=net;self.rows={};self.bins=collections.defaultdict(list);self.padboxes=[]
        for layer in(k.F_Cu,k.B_Cu):
            rows=[]
            def add(kind,shape,box):
                idx=len(rows);rows.append((kind,shape))
                for x in range(math.floor(box[0]),math.ceil(box[2])+1):
                    for y in range(math.floor(box[1]),math.ceil(box[3])+1):self.bins[layer,x,y].append(idx)
            for t in board.GetTracks():
                if t.GetNetname()==net:continue
                if isinstance(t,k.PCB_VIA):
                    p=m.dock(t.GetPosition());r=max(k.ToMM(t.GetWidth())/2+.205,k.ToMM(t.GetDrillValue())/2+.255)
                    add('circle',(p,r),(p[0]-r-.4,p[1]-r-.4,p[0]+r+.4,p[1]+r+.4))
                elif t.GetLayer()==layer:
                    a,c=m.dock(t.GetStart()),m.dock(t.GetEnd());r=k.ToMM(t.GetWidth())/2+.205
                    add('line',(a,c,r),(min(a[0],c[0])-r-.4,min(a[1],c[1])-r-.4,max(a[0],c[0])+r+.4,max(a[1],c[1])+r+.4))
            for f in board.GetFootprints():
                for p in f.Pads():
                    bb=p.GetBoundingBox();a=m.dock(bb.GetOrigin());c=m.dock(bb.GetEnd())
                    box=(a[0],c[1],c[0],a[1])
                    if layer==k.F_Cu:self.padboxes.append(box)
                    if p.GetNetname()!=net and p.GetLayerSet().Contains(layer):
                        add('box',box,(box[0]-.65,box[1]-.65,box[2]+.65,box[3]+.65))
                    if p.GetDrillSize().x:
                        pp=m.dock(p.GetPosition());r=k.ToMM(p.GetDrillSize().x)/2+.255
                        add('circle',(pp,r),(pp[0]-r-.4,pp[1]-r-.4,pp[0]+r+.4,pp[1]+r+.4))
            self.rows[layer]=rows

    def clear(self,p,layer,via=False):
        half=.3 if via else self.width/2
        inside=False
        for a,c in zip(m.OUTLINE,m.OUTLINE[1:]+m.OUTLINE[:1]):
            if(a[1]>p[1])!=(c[1]>p[1])and p[0]<(c[0]-a[0])*(p[1]-a[1])/(c[1]-a[1])+a[0]:inside=not inside
            if distance(p,a,c)<half+.315:return False
        if not inside:return False
        if any(math.dist(p,q)<3+half+.015 for q in m.MOUNTS):return False
        if layer==k.F_Cu and -48-half<p[0]<-42.8+half and 102-half<p[1]<108+half:return False
        for idx in self.bins[layer,math.floor(p[0]),math.floor(p[1])]:
            kind,shape=self.rows[layer][idx]
            if kind=='circle':
                c,r=shape
                if math.dist(p,c)<r+half:return False
            elif kind=='line':
                a,c,r=shape
                if distance(p,a,c)<r+half:return False
            else:
                x1,y1,x2,y2=shape
                if x1-half-.205<=p[0]<=x2+half+.205 and y1-half-.205<=p[1]<=y2+half+.205:return False
        if via and any(a-.4<=p[0]<=c+.4 and e-.4<=p[1]<=f+.4 for a,e,c,f in self.padboxes):return False
        return True

    def path(self,start,end,start_layer,end_layer,margin=6):
        step=.10;point=lambda n:(start[0]+n[0]*step,start[1]+n[1]*step)
        @functools.lru_cache(None)
        def clear(x,y,layer):return self.clear(point((x,y)),layer)
        @functools.lru_cache(None)
        def via(x,y):return all(self.clear(point((x,y)),ly,True)for ly in(k.F_Cu,k.B_Cu))
        assert self.clear(start,start_layer),('startblocked',self.net,start,start_layer)
        assert self.clear(end,end_layer),('endblocked',self.net,end,end_layer)
        lo=[min(start[i],end[i])-margin for i in range(2)];hi=[max(start[i],end[i])+margin for i in range(2)]
        initial=(0,0,start_layer);cost={initial:0};parent={};heap=[(math.dist(start,end),0,initial)];finish=None
        while heap:
            _,g,n=heapq.heappop(heap)
            if g>cost[n]+1e-9:continue
            p=point(n)
            if n[2]==end_layer and math.dist(p,end)<.15:
                if all(self.clear((p[0]+(end[0]-p[0])*i/5,p[1]+(end[1]-p[1])*i/5),n[2])for i in range(6)):finish=n;break
            if len(cost)>500000:break
            for dx,dy in((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
                nxt=(n[0]+dx,n[1]+dy,n[2]);q=point(nxt)
                if not all(lo[i]<=q[i]<=hi[i]for i in range(2))or not clear(*nxt):continue
                if not self.clear(((p[0]+q[0])/2,(p[1]+q[1])/2),n[2]):continue
                ng=g+step*math.hypot(dx,dy)
                if ng<cost.get(nxt,math.inf)-1e-9:
                    cost[nxt]=ng;parent[nxt]=n;heapq.heappush(heap,(ng+math.dist(q,end),ng,nxt))
            other=k.B_Cu if n[2]==k.F_Cu else k.F_Cu
            nxt=(n[0],n[1],other)
            if via(n[0],n[1]) and g+3<cost.get(nxt,math.inf):
                cost[nxt]=g+3;parent[nxt]=n;heapq.heappush(heap,(g+3+math.dist(p,end),g+3,nxt))
        if finish is None:raise RuntimeError(('No repairroute',self.net,start,end,len(cost)))
        nodes=[finish]
        while nodes[-1]!=initial:nodes.append(parent[nodes[-1]])
        points=[(point(n),n[2])for n in reversed(nodes)]+[(end,end_layer)]
        return points,len(cost)

def connect(b,net,a,c,la=k.B_Cu,lc=k.B_Cu):
    router=Router(b,net);points,nodes=router.path(a,c,la,lc)
    merged=[]
    for p,ly in points:
        if merged and math.dist(p,merged[-1][0])<1e-8 and ly==merged[-1][1]:continue
        while len(merged)>=2 and merged[-1][1]==merged[-2][1]==ly:
            x,y=merged[-2][0],merged[-1][0]
            if abs((y[0]-x[0])*(p[1]-y[1])-(y[1]-x[1])*(p[0]-y[0]))>1e-8:break
            merged.pop()
        merged.append((p,ly))
    for (p,lp),(q,lq)in zip(merged,merged[1:]):
        if lp!=lq:
            assert math.dist(p,q)<1e-6;m.via(b,net,p)
        else:m.track(b,net,[p,q],lp,.25)
    print(net,'nodes',nodes,'vertices',len(merged),flush=True)
    return {'net':net,'points':merged,'search_nodes':nodes}

def main(side):
    folder,path,b=ctx(side);before=m.sha(path);prefix=side.upper();base=400 if side=='base'else 500
    report=json.loads((folder/'native-drc.json').read_text())
    removed=[]
    for v in report['violations']:
        if v['type']=='via_dangling':
            uid=v['items'][0]['uuid'];item=next(t for t in b.GetTracks()if t.m_Uuid.AsString()==uid)
            assert isinstance(item,k.PCB_VIA) and item.GetNetname() in(prefix+'_THERM_SEND',prefix+'_VOUT_DIV','LOOP_A_RAW'if side=='base'else'LOOP_B_RAW','NTC_'+prefix,'UV_CTRL')
            removed.append(uid);b.Delete(item)
    reroutes=(prefix+'_THERM_SEND',prefix+'_VOUT_DIV',prefix+'_CATHODE_GATE')
    for t in list(b.GetTracks()):
        if t.GetNetname()in reroutes:removed.append(t.m_Uuid.AsString());b.Delete(t)
    operations=[]
    for net in reroutes:
        pads=[p for f in b.GetFootprints()for p in f.Pads()if p.GetNetname()==net]
        tree=[pads.pop(0)]
        while pads:
            a,c=min(((a,c)for a in tree for c in pads),key=lambda pair:math.dist(m.dock(pair[0].GetPosition()),m.dock(pair[1].GetPosition())))
            operations.append(connect(b,net,m.dock(a.GetPosition()),m.dock(c.GetPosition()),k.B_Cu,k.B_Cu))
            tree.append(c);pads.remove(c)
    fps={f.GetReference():f for f in b.GetFootprints()}
    def p(ref,num):return next(q for q in fps[ref].Pads()if q.GetNumber()==str(num))
    for net,a,c in[(prefix+'_FB_RAW',p('R'+str(base+8),1),p('Q'+str(base+1),2)),
                    ('UV_CTRL',p('J'+str(base+1),3),p('R'+str(base+2),1))]:
        operations.append(connect(b,net,m.dock(a.GetPosition()),m.dock(c.GetPosition()),k.B_Cu,k.B_Cu))
    m.save(b,path)
    (folder/'route-repairs.json').write_text(json.dumps({'before_sha256':before,'after_sha256':m.sha(path),'tool_sha256':m.sha(__import__('pathlib').Path(__file__)),'removed_route_UUIDs':removed,'operations':operations},indent=2)+'\n')

if __name__=='__main__':main(sys.argv[1])
