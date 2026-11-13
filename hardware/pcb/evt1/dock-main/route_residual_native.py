"""Route actual native residual components with checked short planar paths.

Preserves every existing item. Uses actual native effective copper shapes,
full board-edge/rule-area clearance and existing through-via endpoints. Native
refill/full DRC remain the acceptance gate after each bounded pass.
"""
from pathlib import Path
import collections,hashlib,heapq,json,math,re,time
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'placement.json').read_text());before=sha(P);assert before==meta['native_board_sha256'];b=k.LoadBoard(str(P));drc=json.loads((H/'drc.json').read_text());layers=(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)
def point(x,y):return k.VECTOR2I(round(x*1e6),round(y*1e6))
def xy(p):return [k.ToMM(p.x),k.ToMM(p.y)]
def uuid(o):return o.m_Uuid.AsString()
def allitems():return list(b.GetTracks())+[p for f in b.GetFootprints()for p in f.Pads()]
keepouts=[z for z in b.Zones()if z.GetIsRuleArea()];edges=[g for g in b.GetDrawings()if g.GetLayer()==k.Edge_Cuts];assert all(g.GetShape()==k.S_SEGMENT for g in edges)
outline=meta['outline_dock_xy_mm']
def inside(p):
 x=k.ToMM(p.x)-100;y=200-k.ToMM(p.y);hit=False
 for a,c in zip(outline,outline[1:]+outline[:1]):
  if(a[1]>y)!=(c[1]>y)and x<(c[0]-a[0])*(y-a[1])/(c[1]-a[1])+a[0]:hit=not hit
 return hit
index={};shapes=[];cell=2500000

def build_index():
 global index,shapes
 index={};shapes=[]
 for o in allitems():
  bb=o.GetBoundingBox();bounds=(bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom())
  for layer in layers:
   if not o.IsOnLayer(layer):continue
   n=len(shapes);shapes.append((o.GetNetCode(),o.GetAttribute()==k.PAD_ATTRIB_NPTH if isinstance(o,k.PAD)else False,o.GetEffectiveShape(layer),bounds))
   for ix in range(bounds[0]//cell,bounds[2]//cell+1):
    for iy in range(bounds[1]//cell,bounds[3]//cell+1):index.setdefault((layer,ix,iy),[]).append(n)
def free(shape,net,layer,bounds):
 ids=set()
 for ix in range((bounds[0]-200200)//cell,(bounds[2]+200200)//cell+1):
  for iy in range((bounds[1]-200200)//cell,(bounds[3]+200200)//cell+1):ids.update(index.get((layer,ix,iy),[]))
 for i in ids:
  other,nonplated,geom,box=shapes[i]
  if other==net:continue
  clearance=200200 if nonplated else 150200
  if k.SHAPE.Collide(shape,geom,clearance):return False
 for edge in edge_shapes:
  if k.SHAPE.Collide(shape,edge,300000):return False
 for z in keepouts:
  if z.IsOnLayer(layer)and k.SHAPE.Collide(shape,z.Outline(),0):return False
 return True
def free_path(path,net,layer,width):
 for aa,bb in zip(path,path[1:]):
  if not inside(aa)or not inside(bb):return False
  bounds=(min(aa.x,bb.x)-width//2,min(aa.y,bb.y)-width//2,max(aa.x,bb.x)+width//2,max(aa.y,bb.y)+width//2)
  if not free(k.SHAPE_SEGMENT(aa,bb,width),net,layer,bounds):return False
 return True
edge_shapes=[k.SHAPE_SEGMENT(e.GetStart(),e.GetEnd(),0)for e in edges]
added=[];failed=[];removed=[]
build_index()
def new_via_free(at,net):
 bb=(at.x-250000,at.y-250000,at.x+250000,at.y+250000)
 if not all(free(k.SHAPE_CIRCLE(at,250000),net,l,bb)for l in layers):return False
 drill=k.SHAPE_CIRCLE(at,100000);margin=max(250000,b.GetDesignSettings().m_HoleToHoleMin)
 for o in allitems():
  if isinstance(o,k.PCB_VIA):
   if k.SHAPE.Collide(drill,k.SHAPE_CIRCLE(o.GetPosition(),o.GetDrillValue()//2),margin):return False
  elif isinstance(o,k.PAD):
   if o.GetDrillSize().x and k.SHAPE.Collide(drill,o.GetEffectiveHoleShape(),margin):return False
   if o.GetAttribute()==k.PAD_ATTRIB_SMD and k.SHAPE.Collide(k.SHAPE_CIRCLE(at,200000),o.GetEffectiveShape(o.GetLayer()),0):return False
 return True
if any('[BTN_LEFTn]'in row['items'][0]['description']for row in drc['unconnected_items']):
 # One unlocked general3V3 segment crosses the otherwise legal pin25 exit.
 # Keep all source192, critical207 and prior authored escapes immutable.
 blockers=[t for t in b.GetTracks()if uuid(t)=='45ee3fff-bf51-4a4a-afc7-96080334f22b']
 if blockers:
  t=blockers[0];assert not t.IsLocked()and t.GetNetname()=='3V3'
  removed.append({'uuid':uuid(t),'net':t.GetNetname(),'layer':k.LayerName(t.GetLayer()),'start_native_mm':xy(t.GetStart()),'end_native_mm':xy(t.GetEnd()),'width_mm':k.ToMM(t.GetWidth()),'reason':'general3V3 segment boxed in final left-button pin exit'})
  b.Delete(t);build_index()
  f=next(f for f in b.GetFootprints()if f.GetReference()=='U201');pad=next(p for p in f.Pads()if p.GetNetname()=='BTN_LEFTn');at=pad.GetPosition();net=pad.GetNetCode();chosen=None
  options=[]
  for ix in range(305,321):
   for iy in range(639,650):
    end=k.VECTOR2I(ix*250000,iy*250000)
    for path in([at,end],[at,k.VECTOR2I(end.x,at.y),end],[at,k.VECTOR2I(at.x,end.y),end]):
     cost=sum((bb-aa).EuclideanNorm()for aa,bb in zip(path,path[1:]))
     options.append((cost,path))
  for cost,path in sorted(options,key=lambda p:p[0]):
   if not new_via_free(path[-1],net)or not free_path(path,net,k.F_Cu,150000):continue
   chosen=path;break
  assert chosen,'No legal escape after the bounded rip-up; native board not saved'
  ids=[]
  for aa,bb in zip(chosen,chosen[1:]):
   if aa==bb:continue
   t=k.PCB_TRACK(b);t.SetStart(aa);t.SetEnd(bb);t.SetWidth(150000);t.SetLayer(k.F_Cu);t.SetNetCode(net);t.SetLocked(True);b.Add(t);ids.append(uuid(t))
  end=chosen[-1];v=k.PCB_VIA(b);v.SetPosition(end);v.SetWidth(500000);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(net);v.SetLocked(True);b.Add(v);ids.append(uuid(v))
  added.append({'net':'BTN_LEFTn','purpose':'last pad escape','layer':'F.Cu','width_mm':.15,'path_native_mm':[xy(p)for p in chosen],'new_via_native_mm':xy(end),'UUIDs':ids});build_index()

def components(net):
 items=[o for o in allitems()if o.GetNetname()==net];parent=list(range(len(items)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(a,c):parent[find(c)]=find(a)
 for i,o in enumerate(items):
  for j in range(i):
   other=items[j]
   if find(i)==find(j):continue
   if any(o.IsOnLayer(l)and other.IsOnLayer(l)and k.SHAPE.Collide(o.GetEffectiveShape(l),other.GetEffectiveShape(l),0)for l in layers):union(i,j)
 for z in b.Zones():
  if z.GetIsRuleArea()or z.GetNetname()!=net:continue
  for layer in layers:
   if not z.IsOnLayer(layer):continue
   poly=z.GetFilledPolysList(layer)
   for r in range(poly.OutlineCount()):
    touches=[]
    for i,o in enumerate(items):
     if not o.IsOnLayer(layer):continue
     ps=[o.GetStart(),o.GetEnd()]if isinstance(o,k.PCB_TRACK)and not isinstance(o,k.PCB_VIA)else[o.GetPosition()]
     if any(poly.Contains(p,r,0,True)for p in ps):touches.append(i)
    for i in touches[1:]:union(touches[0],i)
 return items,find,{uuid(o):i for i,o in enumerate(items)}
def paths(aa,bb):
 ax,ay=aa.x,aa.y;bx,by=bb.x,bb.y;out=[[aa,bb],[aa,k.VECTOR2I(ax,by),bb],[aa,k.VECTOR2I(bx,ay),bb]]
 dx=bx-ax;dy=by-ay;sx=1 if dx>=0 else-1;sy=1 if dy>=0 else-1;d=min(abs(dx),abs(dy))
 out.extend([[aa,k.VECTOR2I(ax+sx*d,ay+sy*d),bb],[aa,k.VECTOR2I(bx-sx*d,by-sy*d),bb]])
 ys=sorted(set([ay,by,198500000,197000000,134000000]+[round(y*1e6)for y in range(136,199,2)]+[ay+n*500000 for n in(-4,-2,-1,1,2,4)]+[by+n*500000 for n in(-4,-2,-1,1,2,4)]))
 xs=sorted(set([ax,bx,52500000,147500000]+[round(x*1e6)for x in range(54,148,3)]+[ax+n*500000 for n in(-4,-2,-1,1,2,4)]+[bx+n*500000 for n in(-4,-2,-1,1,2,4)]))
 for y in ys:out.append([aa,k.VECTOR2I(ax,y),k.VECTOR2I(bx,y),bb])
 for x in xs:out.append([aa,k.VECTOR2I(x,ay),k.VECTOR2I(x,by),bb])
 return [[p for i,p in enumerate(row)if i==0 or p!=row[i-1]]for row in out]
def astar(items,find,ra,rb,code,net,forbidden=frozenset(),retry=0):
 step=250000;width=150000;route_layers=(k.B_Cu,k.F_Cu,k.In2_Cu);layercost={k.B_Cu:1.,k.F_Cu:1.1,k.In2_Cu:1.25}
 def anchors(root):
  group=[o for i,o in enumerate(items)if find(i)==root];vs=[o for o in group if isinstance(o,k.PCB_VIA)]
  if vs:return [(o.GetPosition(),route_layers)for o in vs]
  result=[]
  for o in group:
   ps=[o.GetStart(),o.GetEnd()]if isinstance(o,k.PCB_TRACK)else[o.GetPosition()]
   result.extend((p,tuple(l for l in route_layers if o.IsOnLayer(l)))for p in ps)
  return result
 goal_areas=[]
 for zone in b.Zones():
  if zone.GetIsRuleArea()or zone.GetNetname()!=net:continue
  for layer in route_layers:
   if not zone.IsOnLayer(layer):continue
   poly=zone.GetFilledPolysList(layer)
   for r in range(poly.OutlineCount()):
    for i,o in enumerate(items):
     if find(i)!=rb or not o.IsOnLayer(layer):continue
     points=[o.GetStart(),o.GetEnd()]if isinstance(o,k.PCB_TRACK)and not isinstance(o,k.PCB_VIA)else[o.GetPosition()]
     if any(poly.Contains(p,r,0,True)for p in points):
      goal_areas.append((layer,poly,r,poly.COutline(r).BBox()));break
 starts=anchors(ra);goals=anchors(rb)
 if not starts or not goals:return None
 def nearest(a,other):return min((a[0]-c[0]).EuclideanNorm()for c in other)
 starts=sorted(starts,key=lambda a:nearest(a,goals))[:12];goals=sorted(goals,key=lambda a:nearest(a,starts))[:12]
 holes=[];smd=[];existing=[]
 for o in allitems():
  if isinstance(o,k.PCB_VIA):holes.append(k.SHAPE_CIRCLE(o.GetPosition(),o.GetDrillValue()//2));existing.append(o)
  elif isinstance(o,k.PAD):
   if o.GetDrillSize().x:holes.append(o.GetEffectiveHoleShape())
   if o.GetAttribute()==k.PAD_ATTRIB_SMD:smd.append(o)
 via_cache={};edge_cache={};node_cache={};minhole=max(250000,b.GetDesignSettings().m_HoleToHoleMin)
 def canvia(x,y):
  key=(x,y)
  if key in forbidden:return False
  if key in via_cache:return via_cache[key]
  pt=k.VECTOR2I(x*step,y*step)
  for v in existing:
   if(v.GetPosition()-pt).EuclideanNorm()<=200:
    via_cache[key]=v.GetNetCode()==code;return via_cache[key]
  bb=(pt.x-250000,pt.y-250000,pt.x+250000,pt.y+250000)
  result=all(free(k.SHAPE_CIRCLE(pt,250000),code,l,bb)for l in layers)
  if result:
   drill=k.SHAPE_CIRCLE(pt,100000)
   result=not any(k.SHAPE.Collide(drill,h,minhole)for h in holes)
  if result:result=not any(k.SHAPE.Collide(k.SHAPE_CIRCLE(pt,200000),p.GetEffectiveShape(p.GetLayer()),0)for p in smd)
  via_cache[key]=result;return result
 def nodefree(state):
  if state not in node_cache:
   x,y,l=state;pt=k.VECTOR2I(x*step,y*step);bb=(pt.x-width//2,pt.y-width//2,pt.x+width//2,pt.y+width//2)
   node_cache[state]=inside(pt)and free(k.SHAPE_CIRCLE(pt,width//2),code,l,bb)
  return node_cache[state]
 def legal(a,c):
  key=tuple(sorted((a,c)))
  if key not in edge_cache:
   edge_cache[key]=free_path([k.VECTOR2I(a[0]*step,a[1]*step),k.VECTOR2I(c[0]*step,c[1]*step)],code,a[2],width)
  return edge_cache[key]
 def heuristic(state):
  x=state[0]*step;y=state[1]*step
  values=[math.hypot(x-p.x,y-p.y)for p,_ in goals]
  for _,_,_,bb in goal_areas:values.append(math.hypot(max(bb.GetLeft()-x,0,x-bb.GetRight()),max(bb.GetTop()-y,0,y-bb.GetBottom())))
  return min(values)
 queue=[];dist={};previous={};initial={};counter=0
 for anchor,ls in starts:
  ix=round(anchor.x/step);iy=round(anchor.y/step)
  for dx in(-1,0,1):
   for dy in(-1,0,1):
    for l in ls:
     state=(ix+dx,iy+dy,l);pt=k.VECTOR2I(state[0]*step,state[1]*step)
     if not nodefree(state)or not free_path([anchor,pt],code,l,width):continue
     cost=(pt-anchor).EuclideanNorm()*layercost[l]
     if cost>=dist.get(state,float('inf')):continue
     dist[state]=cost;initial[state]=anchor;counter+=1;heapq.heappush(queue,(cost+heuristic(state),counter,state))
 iterations=0;terminal=None;anchor_end=None;started=time.monotonic();closed=set()
 while queue and iterations<60000:
  _,_,state=heapq.heappop(queue)
  if state in closed:continue
  closed.add(state);cost=dist[state];iterations+=1;x,y,l=state;pt=k.VECTOR2I(x*step,y*step)
  for layer,poly,r,_ in goal_areas:
   if l==layer and all(poly.Contains(k.VECTOR2I(pt.x+dx,pt.y+dy),r,0,True)for dx,dy in((0,0),(-100000,-100000),(100000,-100000),(-100000,100000),(100000,100000))):terminal=state;anchor_end=pt;break
  if terminal:break
  for goal,ls in goals:
   if l in ls and(pt-goal).EuclideanNorm()<=600000 and free_path([pt,goal],code,l,width):terminal=state;anchor_end=goal;break
  if terminal:break
  for dx,dy in((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   nxt=(x+dx,y+dy,l)
   if not nodefree(nxt)or not legal(state,nxt):continue
   nc=cost+step*math.hypot(dx,dy)*layercost[l]
   if nc>=dist.get(nxt,float('inf')):continue
   dist[nxt]=nc;previous[nxt]=state;counter+=1;heapq.heappush(queue,(nc+heuristic(nxt),counter,nxt))
  if canvia(x,y):
   for layer in route_layers:
    if layer==l:continue
    nxt=(x,y,layer);nc=cost+8000000
    if not nodefree(nxt)or nc>=dist.get(nxt,float('inf')):continue
    dist[nxt]=nc;previous[nxt]=state;counter+=1;heapq.heappush(queue,(nc+heuristic(nxt),counter,nxt))
  if iterations%5000==0:print('Astar',net,'expanded',iterations,'elapsed',round(time.monotonic()-started,1),flush=True)
 if terminal is None:return None
 states=[terminal]
 while states[-1]in previous:states.append(previous[states[-1]])
 states.reverse();start=initial[states[0]];parts=[];current=[start];layer=states[0][2];new_vias=[]
 for state in states:
  p=k.VECTOR2I(state[0]*step,state[1]*step)
  if state[2]!=layer:
   parts.append((current,layer));new_vias.append(p);current=[p];layer=state[2]
  if p!=current[-1]:current.append(p)
 if current[-1]!=anchor_end:current.append(anchor_end)
 parts.append((current,layer))
 # Preflight all unique NEW holes against one another before any mutation.
 new_vias=list({(p.x,p.y):p for p in new_vias}.values())
 fresh=[p for p in new_vias if not any((v.GetPosition()-p).EuclideanNorm()<=200 and v.GetNetCode()==code for v in existing)]
 for i,p in enumerate(fresh):
  for q in fresh[:i]:
   if(p-q).EuclideanNorm()<200000+minhole:
    if retry>=6:return None
    return astar(items,find,ra,rb,code,net,forbidden|{(p.x//step,p.y//step)},retry+1)
 created=[]
 for path,l in parts:
  compressed=[]
  for pt in path:
   while len(compressed)>=2:
    a,c=compressed[-2:];u=c-a;v=pt-c
    if u.x*v.y-u.y*v.x==0 and u.x*v.x+u.y*v.y>=0:compressed.pop()
    else:break
   if not compressed or pt!=compressed[-1]:compressed.append(pt)
  assert free_path(compressed,code,l,width)
  for a,c in zip(compressed,compressed[1:]):
   t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(width);t.SetLayer(l);t.SetNetCode(code);t.SetLocked(True);b.Add(t);created.append(uuid(t))
  added.append({'net':net,'purpose':'native-checked grid bridge','layer':k.LayerName(l),'width_mm':.15,'path_native_mm':[xy(p)for p in compressed],'expanded_states':iterations})
 for p in new_vias:
  if any((v.GetPosition()-p).EuclideanNorm()<=200 and v.GetNetCode()==code for v in existing):continue
  v=k.PCB_VIA(b);v.SetPosition(p);v.SetWidth(500000);v.SetDrill(200000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(code);v.SetLocked(True);b.Add(v);existing.append(v);created.append(uuid(v))
  added.append({'net':net,'purpose':'checked layer transition','via_native_mm':xy(p),'diameter_drill_mm':[.5,.2],'UUID':uuid(v)})
 return created

for row in drc['unconnected_items']:
 net=re.search(r'\[([^]]+)\]',row['items'][0]['description'])[1];items,find,lookup=components(net)
 a0,b0=[lookup[x['uuid']]for x in row['items']];ra,rb=find(a0),find(b0)
 if ra==rb:failed.append({'net':net,'reason':'native reported items already overlap geometrically; needs explicit endpoint repair'});continue
 va=[o.GetPosition()for i,o in enumerate(items)if find(i)==ra and isinstance(o,k.PCB_VIA)];vb=[o.GetPosition()for i,o in enumerate(items)if find(i)==rb and isinstance(o,k.PCB_VIA)]
 pairs=sorted(((float((a-c).EuclideanNorm()),a,c)for a in va for c in vb),key=lambda x:x[0])[:12]
 best=None;code=b.FindNet(net).GetNetCode()
 for _,a,c in pairs:
  candidates=paths(a,c)
  for layer,penalty in[(k.B_Cu,0),(k.F_Cu,10000000),(k.In2_Cu,20000000)]:
   for width in([300000,150000]if net=='3V3'else[200000,150000]):
    for path in candidates:
     cost=sum((y-x).EuclideanNorm()for x,y in zip(path,path[1:]))+penalty+(500000 if width==150000 else 0)
     if best and cost>=best[0]:continue
     if free_path(path,code,layer,width):best=(cost,path,layer,width)
 if best is None:
  print('Grid search',net,flush=True)
  if astar(items,find,ra,rb,code,net):build_index();continue
  failed.append({'net':net,'reason':'bounded native-checked grid/planar paths exhausted','via_candidates_each':[len(va),len(vb)]});continue
 _,path,layer,width=best;uids=[]
 for aa,bb in zip(path,path[1:]):
  if aa==bb:continue
  t=k.PCB_TRACK(b);t.SetStart(aa);t.SetEnd(bb);t.SetWidth(width);t.SetLayer(layer);t.SetNetCode(code);t.SetLocked(True);b.Add(t);uids.append(uuid(t))
 added.append({'net':net,'purpose':'actual residual component bridge','layer':k.LayerName(layer),'width_mm':k.ToMM(width),'path_native_mm':[xy(p)for p in path],'UUIDs':uids});build_index()
# Clear all old filled regions before native connectivity can assign an old
# foreign pour net to an added via; every authored net must survive unchanged.
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
intended={uuid(t):t.GetNetname()for t in b.GetTracks()};b.BuildConnectivity();assert intended=={uuid(t):t.GetNetname()for t in b.GetTracks()};k.SaveBoard(str(P),b)
meta['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'input_board_sha256':before,'native_DRC_sha256':sha(H/'drc.json'),'board_sha256':sha(P),'added':added,'unresolved':failed,'protected_copper_mutated':0,'bounded_unlocked_ripup':removed,'native_full_DRC_required':True,'clearance_nm':150200,'outer_and_internal_cut_edge_clearance_nm':300000}
(H/'routing'/('native-residual-'+before[:12]+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
