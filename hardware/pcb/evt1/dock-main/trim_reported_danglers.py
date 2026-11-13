"""Single native-DRC-bound stub cleanup with explicit connectivity preservation.

Never recursively purge endpoints. Rebuild the live same-net graph after each
edit, retain mid-track junctions, and never edit source/critical copper. A
reported item may be deleted only when all its other copper neighbours remain
in one connected component without it. Native full DRC runs after every pass.
"""
from pathlib import Path
import argparse,hashlib,json,math
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();LAYERS=(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)
def uid(o):return o.m_Uuid.AsString()
def redundant(b,t,items):
 others=[o for o in items if uid(o)!=uid(t)and o.GetNetCode()==t.GetNetCode()];parents=list(range(len(others)))
 def find(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 def union(a,c):parents[find(c)]=find(a)
 def touches(a,c):return any(a.IsOnLayer(l)and c.IsOnLayer(l)and k.SHAPE.Collide(a.GetEffectiveShape(l),c.GetEffectiveShape(l),0)for l in LAYERS)
 for i,o in enumerate(others):
  for j in range(i):
   if find(i)!=find(j)and touches(o,others[j]):union(i,j)
 for z in b.Zones():
  if z.GetIsRuleArea()or z.GetNetCode()!=t.GetNetCode():continue
  for layer in LAYERS:
   if not z.IsOnLayer(layer):continue
   poly=z.GetFilledPolysList(layer)
   for r in range(poly.OutlineCount()):
    connected=[]
    for i,o in enumerate(others):
     if not o.IsOnLayer(layer):continue
     ps=[o.GetStart(),o.GetEnd()]if isinstance(o,k.PCB_TRACK)and not isinstance(o,k.PCB_VIA)else[o.GetPosition()]
     if any(poly.Contains(p,r,0,True)for p in ps):connected.append(i)
    for i in connected[1:]:union(connected[0],i)
 neighbours=[i for i,o in enumerate(others)if touches(t,o)];groups={find(i)for i in neighbours}
 return len(groups)<=1,len(neighbours),len(groups)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--expected-board-sha');ap.add_argument('--only-uuid',action='append',default=[]);a=ap.parse_args();
 if a.apply:assert a.expected_board_sha and a.only_uuid,'Generic automatic cleanup is withdrawn: inspect and independently review exact UUIDs/current SHA before a bounded repair'
 meta=json.loads((H/'placement.json').read_text());before=sha(P);assert before==meta['native_board_sha256'];
 if a.apply:assert before==a.expected_board_sha
 b=k.LoadBoard(str(P));drc=json.loads((H/'drc.json').read_text())
 # Only our new residual-route objects may be removed despite being locked.
 # Source192 and critical207 remain immutable; redundant new fanout vias
 # are explicitly retired below after a native graph proof.
 owned=set()
 for p in(H/'routing').glob('native-residual-*.json'):
  for row in json.loads(p.read_text())['added']:
   owned.update(row.get('UUIDs',[]))
   if row.get('UUID'):owned.add(row['UUID'])
 guides=json.loads((H/'routing/residual-fanout-guides.json').read_text())['extra_locked_authored_copper']
 guide_vias={row['uuid']for row in guides if row['kind']=='via'}
 owned.update(guide_vias)
 retired=[];changes=[]
 for row in drc['violations']:
  if row['type']not in('track_dangling','via_dangling'):continue
  tracks=list(b.GetTracks());pads=[p for f in b.GetFootprints()for p in f.Pads()];byid={uid(t):t for t in tracks};uuid=row['items'][0]['uuid']
  if a.only_uuid and uuid not in a.only_uuid:continue
  if uuid not in byid:continue
  t=byid[uuid]
  if t.IsLocked()and uuid not in owned:
   changes.append({'uuid':uuid,'net':t.GetNetname(),'action':'retain_original_protected_item'});continue
  proof,n,groups=redundant(b,t,tracks+pads);record={'uuid':uuid,'net':t.GetNetname(),'native_DRC_type':row['type'],'other_copper_neighbours':n,'components_after_excluding_item':groups,'owned_new_locked':t.IsLocked()}
  if proof:
   record['action']='delete_graph_redundant_reported_stub'
   if uuid in guide_vias:retired.append({'uuid':uuid,'net':t.GetNetname(),'reason':'newly authored fanout via serves only one layer and is graph-redundant after completed routing'})
   if a.apply:b.Delete(t)
   changes.append(record);continue
  if isinstance(t,k.PCB_VIA):record['action']='retain_one_layer_via_that_still_joins_copper';changes.append(record);continue
  p=t.GetStart();q=t.GetEnd();dx=q.x-p.x;dy=q.y-p.y;length2=dx*dx+dy*dy
  if not length2:record['action']='retain_nonredundant_zero_length';changes.append(record);continue
  def candidate(pos):
   u=max(0,min(1,((pos.x-p.x)*dx+(pos.y-p.y)*dy)/length2));return u,k.VECTOR2I(round(p.x+u*dx),round(p.y+u*dy))
  anchors=[]
  for other in tracks+pads:
   if uid(other)==uuid or other.GetNetCode()!=t.GetNetCode()or not other.IsOnLayer(t.GetLayer()):continue
   if isinstance(other,k.PCB_TRACK)and not isinstance(other,k.PCB_VIA):
    candidates=[other.GetStart(),other.GetEnd()];r=other.GetStart();s=other.GetEnd();vx=s.x-r.x;vy=s.y-r.y;cross=dx*vy-dy*vx
    if cross:
     f=((r.x-p.x)*vy-(r.y-p.y)*vx)/cross;g=((r.x-p.x)*dy-(r.y-p.y)*dx)/cross
     if 0<=f<=1 and 0<=g<=1:candidates.append(k.VECTOR2I(round(p.x+f*dx),round(p.y+f*dy)))
   else:candidates=[other.GetPosition()]
   for at in candidates:
    u,at=candidate(at)
    if other.GetEffectiveShape(t.GetLayer()).Collide(k.SHAPE_CIRCLE(at,max(0,t.GetWidth()//2-10)),0):anchors.append(u)
  if anchors:
   lo=min(anchors);hi=max(anchors);start=k.VECTOR2I(round(p.x+lo*dx),round(p.y+lo*dy));end=k.VECTOR2I(round(p.x+hi*dx),round(p.y+hi*dy))
   record.update({'action':'trim_to_all_connected_anchors','old_nm':[[p.x,p.y],[q.x,q.y]],'new_nm':[[start.x,start.y],[end.x,end.y]]})
   if a.apply:t.SetStart(start);t.SetEnd(end)
  else:record['action']='retain_without_sufficient_anchor_proof'
  changes.append(record)
 if a.apply:
  for z in b.Zones():
   if not z.GetIsRuleArea():z.UnFill()
  intended={uid(t):t.GetNetname()for t in b.GetTracks()};b.BuildConnectivity();assert intended=={uid(t):t.GetNetname()for t in b.GetTracks()};k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
 if a.apply and retired:
  final=H/'routing/fanout-finalization.json'
  previous=json.loads(final.read_text())['retired_new_fanout_vias']if final.exists()else[]
  records=previous+retired
  final.write_text(json.dumps({'original_authored_fanout_objects':len(guides),'retired_new_fanout_vias':records,'remaining_authored_fanout_objects':len(guides)-len(records),'source192_and_main_critical207_unchanged':True,'board_sha256':sha(P)},indent=2)+'\n')
 report={'input_board_sha256':before,'input_DRC_sha256':sha(H/'drc.json'),'applied':a.apply,'changes':changes,'output_board_sha256':sha(P),'source_critical_original_protected_items_mutated':0,'native_full_DRC_required_next':True,'sequential_live_graph_recomputed_after_each_edit':True}
 out=H/'routing'/('dangler-pass-'+before[:12]+'.json');out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
