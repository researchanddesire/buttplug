"""One owner/peer-reviewed exact segment removal, not a cleanup loop.

The prior automatic sequence was stopped by approval review. Three independent
native inspections established this specific unbranched B.Cu tail; root agreed
to this exact SHA/UUID/endpoints only. Keep all other copper and zone identities.
"""
from pathlib import Path
import hashlib,json,shutil
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
EXPECTED='8a00e40491fff508f95fb872acfc6eaad7cb6cc74bbd274359a80264cfb93dc7';TARGET='b54f1b76-160c-44ef-8fa8-6c3e2fca143a';VIA='a8d25886-7ff0-4346-9403-af7035bf772d'
assert sha(P)==EXPECTED,'Exact reviewed input changed; stop for review'
meta=json.loads((H/'placement.json').read_text());assert meta['native_board_sha256']==EXPECTED
proof=json.loads((H/'routing/remaining-tail-inspection.json').read_text());assert proof['board_sha256']==EXPECTED
review=Path('/private/tmp/compass-jobs/final-loop-stub-review.json');assert review.exists()
b=k.LoadBoard(str(P));items=list(b.GetTracks());matches=[t for t in items if t.m_Uuid.AsString()==TARGET];assert len(matches)==1;t=matches[0]
assert not isinstance(t,k.PCB_VIA)and not t.IsLocked()and t.GetNetname()=='LOOP_A_RAW'and t.GetLayer()==k.B_Cu and t.GetWidth()==200000
assert(t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y)==(115625000,140851000,100176000,156300000)
assert len([x for x in items if x.GetNetname()=='LOOP_A_RAW'and not isinstance(x,k.PCB_VIA)and x.GetLayer()==k.B_Cu])==1
row=next(r for r in proof['items']if r['uuid']==TARGET);assert row['neighbours']==[VIA]and not proof['protected_source_or_main_critical_records']
def copper(o):
 common=[o.m_Uuid.AsString(),o.GetNetname(),o.IsLocked(),o.GetWidth()]
 if isinstance(o,k.PCB_VIA):return common+['via',o.GetPosition().x,o.GetPosition().y,o.GetDrillValue(),list(o.GetLayerSet().Seq())]
 return common+['track',o.GetLayer(),o.GetStart().x,o.GetStart().y,o.GetEnd().x,o.GetEnd().y]
def polygon(poly):
 return [[[poly.COutline(i).CPoint(j).x,poly.COutline(i).CPoint(j).y]for j in range(poly.COutline(i).PointCount())]for i in range(poly.OutlineCount())]
def zones():return {z.m_Uuid.AsString():[z.GetNetname(),list(z.GetLayerSet().Seq()),z.GetIsRuleArea(),polygon(z.Outline()),z.GetLocalClearance(),z.GetMinThickness(),z.GetPadConnection()]for z in b.Zones()}
other={x.m_Uuid.AsString():copper(x)for x in items if x.m_Uuid.AsString()!=TARGET};zone_before=zones();assert VIA in other
backup=H/'routing/before-reviewed-single-tail.kicad_pcb';assert not backup.exists();shutil.copyfile(P,backup)
b.Delete(t)
assert {x.m_Uuid.AsString():copper(x)for x in b.GetTracks()}==other
assert zones()==zone_before
k.SaveBoard(str(P),b);removed_sha=sha(P)
# Refill the existing zone objects, preserving every zone UUID and outline.
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones())
assert {x.m_Uuid.AsString():copper(x)for x in b.GetTracks()}==other,'Other copper/net changed during refill'
assert zones()==zone_before,'Zone identity, outline, net or settings changed'
k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P);(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
report={'status':'exact independently reviewed one-segment repair; full native DRC required next','input_board_sha256':EXPECTED,'removed_only_UUID':TARGET,'net':'LOOP_A_RAW','layer':'B.Cu','start_native_mm':[115.625,140.851],'end_native_mm':[100.176,156.3],'width_mm':.2,'preserved_start_via_UUID':VIA,'all_other_copper_signatures_unchanged':True,'all_zone_UUIDs_outlines_nets_settings_unchanged':True,'deletion_stage_sha256':removed_sha,'board_sha256':sha(P),'own_read_only_proof_sha256':sha(H/'routing/remaining-tail-inspection.json'),'root_independent_proof_sha256':sha(review),'root_agreed_exact_scope':True,'previous_generic_cleanup_not_rerun':True,'physical_validation':False}
(H/'routing/reviewed-single-tail-repair.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
