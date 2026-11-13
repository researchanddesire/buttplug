"""Prepare/import an isolated neck-facing J7 routing candidate; KiCad7 Python.

Existing copper outside the old/new component areas stays locked. The shared
Specctra exporter reserves the reference layer. Native DRC/official CAD are
required before promotion; this tool never overwrites the source board.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,re,shutil
import build_evt1_device_pcbs as m
from route_evt1_repairs import Router
k=m.k;s=m.s
ROOT=Path(__file__).resolve().parents[1]
TRIAL=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/loom/neck-facing-j7-trial'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def parity(board,source):
    mcad=json.loads((source.parent/'mcad.json').read_text());assert mcad['board_sha256']==sha(source)
    expected=Counter((p['ref'],p['number'],p['net']) for p in mcad['pads'])
    actual=Counter((f.GetReference(),p.GetNumber(),p.GetNetname()) for f in board.GetFootprints() for p in f.Pads())
    assert actual==expected,'Pad/ref/net multiset changed'

def prepare(folder):
    source=m.boardpath('flange');snapshot=json.loads((TRIAL/'source-snapshot.json').read_text())
    assert sha(source)==snapshot['files'][str(source.relative_to(ROOT))]
    proposal=json.loads((TRIAL/'placement-proposal.json').read_text());assert not proposal['courtyard_intersections']
    assert sha(TRIAL/'placement-proposal.json')==snapshot['placement_proposal_sha256']
    assert folder!=source.parent.resolve();folder.mkdir(parents=True,exist_ok=True);path=folder/source.name
    for suffix in ('.kicad_pcb','.kicad_pro'):shutil.copy2(source.with_suffix(suffix),path.with_suffix(suffix))
    for name in ('fp-lib-table','sym-lib-table'):
        p=source.parent/name
        if p.exists():(folder/name).write_text(p.read_text().replace('${KIPRJMOD}',str(source.parent)))
    b=k.LoadBoard(str(path));fps={f.GetReference():f for f in b.GetFootprints()};boxes=[]
    old_outline=m.board_outline(b);outline=proposal['outline_xy_mm']
    for drawing in list(b.GetDrawings()):
        if drawing.GetLayer()==k.Edge_Cuts:b.Delete(drawing)
    for start,end in zip(outline,outline[1:]+outline[:1]):
        line=k.PCB_SHAPE(b);line.SetShape(k.SHAPE_T_SEGMENT);line.SetStart(m.xy(*start));line.SetEnd(m.xy(*end));line.SetWidth(k.FromMM(.05));line.SetLayer(k.Edge_Cuts);b.Add(line)
    for zone in b.Zones():
        if zone.GetIsRuleArea():continue
        poly=zone.Outline();assert poly.TotalVertices()==len(old_outline),'Unexpected zone contour'
        poly.RemoveAllContours();poly.NewOutline()
        for x,y in outline:
            point=m.xy(x,y);poly.Append(point.x,point.y)
    for ref in proposal['poses']:boxes.append(m.ripbox(fps[ref],.25))
    for ref,v in proposal['poses'].items():
        m.pose(fps[ref],*v['origin'],v['angle'],'B');boxes.append(m.ripbox(fps[ref],.25))
    fps['U75'].Reference().SetPosition(m.xy(-26.3,-27.2))
    def inside(q):
        value=False
        for p,c in zip(outline,outline[1:]+outline[:1]):
            if (p[1]>q[1])!=(c[1]>q[1]) and q[0]<(c[0]-p[0])*(q[1]-p[1])/(c[1]-p[1])+p[0]:value=not value
        return value
    from route_evt1_repairs import distance
    minimum_pad_edge=999
    for ref in proposal['poses']:
        for pad in fps[ref].Pads():
            bb=pad.GetBoundingBox();p,c=m.mech(bb.GetOrigin()),m.mech(bb.GetEnd())
            for q in ((p[0],p[1]),(p[0],c[1]),(c[0],p[1]),(c[0],c[1])):
                assert inside(q),(ref,pad.GetNumber(),'Pad outside proposed PCB',q)
                clearance=min(distance(q,a,c) for a,c in zip(outline,outline[1:]+outline[:1]));minimum_pad_edge=min(minimum_pad_edge,clearance)
                assert clearance>=.3-1e-6,(ref,pad.GetNumber(),'Pad edge clearance',clearance)
    removed=[]
    for t in list(b.GetTracks()):
        if not isinstance(t,k.PCB_VIA) and m.touches(t,boxes):removed.append(t.m_Uuid.AsString());b.Delete(t)
    # Vias beneath newly moved pads must clear both copper and drill budgets.
    pads=[p for ref in proposal['poses'] for p in fps[ref].Pads()];all_pads=[p for f in b.GetFootprints() for p in f.Pads()]
    def gap(point,p):
        bb=p.GetBoundingBox();a,c=m.mech(bb.GetOrigin()),m.mech(bb.GetEnd())
        return math.hypot(max(min(a[0],c[0])-point[0],0,point[0]-max(a[0],c[0])),max(min(a[1],c[1])-point[1],0,point[1]-max(a[1],c[1])))
    moved=[]
    for via in list(b.GetTracks()):
        if not isinstance(via,k.PCB_VIA):continue
        old=m.mech(via.GetPosition());diam=k.ToMM(via.GetWidth());drill=k.ToMM(via.GetDrillValue())
        radius=max(diam/2+.105,drill/2+.255)
        if not any(p.GetNetname()!=via.GetNetname() and gap(old,p)<radius for p in pads):continue
        uid=via.m_Uuid.AsString()
        for t in list(b.GetTracks()):
            if isinstance(t,k.PCB_VIA) or t.GetNetname()!=via.GetNetname():continue
            if min(math.dist(m.mech(t.GetStart()),old),math.dist(m.mech(t.GetEnd()),old))<1e-6:
                removed.append(t.m_Uuid.AsString());b.Delete(t)
        probes=[Router(b,via.GetNetname(),ly,diam,(uid,)) for ly in b.GetEnabledLayers().CuStack()]
        candidates=[(old[0]+i*.1,old[1]+j*.1) for i in range(-25,26) for j in range(-25,26) if i or j]
        candidates.sort(key=lambda q:math.dist(q,old))
        def mask_clear(q):
            return all(p.GetParent().GetReference() in ('J1','J81','J82') or p.GetDrillSize().x or gap(q,p)>=drill/2+.075 for p in all_pads)
        new=next((q for q in candidates if all(r.clear(q) for r in probes) and mask_clear(q)),None)
        assert new is not None,('No via relocation',uid,old)
        via.SetPosition(m.xy(*new));moved.append({'uuid':uid,'net':via.GetNetname(),'from':old,'to':new});print('Moved via',moved[-1],flush=True)
    for t in b.GetTracks():t.SetLocked(True)
    parity(b,source);m.boardpath=lambda domain:path;m.save(b,'flange')
    seed=folder/'placement.kicad_pcb';shutil.copy2(path,seed);m.export_dsn(b,'flange')
    report={'scope':'Isolated candidate; autorouting/native DRC/official CAD pending','stage':'prepared_unrouted',
        'source_board_sha256':sha(source),'seed_sha256':sha(seed),'candidate_board_sha256':sha(path),
        'poses':proposal['poses'],'source_outline_xy_mm':old_outline,'outline_xy_mm':outline,'minimum_proposed_pad_bbox_edge_clearance_mm':minimum_pad_edge,
        'removed_track_UUIDs':removed,'moved_vias':moved,'preserved_locked_route_objects':len(list(b.GetTracks())),
        'exporter_sha256':sha(ROOT/'tools/build_evt1_device_pcbs.py'),'script_sha256':sha(Path(__file__)),
        'physical_validation':False,'ready_to_promote':False}
    (folder/'placement-routing.json').write_text(json.dumps(report,indent=2)+'\n')
    assert sha(source)==report['source_board_sha256'];print('Prepared DSN',path.with_suffix('.dsn'),flush=True)

def import_session(folder,session):
    source=m.boardpath('flange');path=folder/source.name;r=json.loads((folder/'placement-routing.json').read_text());seed=folder/'placement.kicad_pcb'
    assert sha(source)==r['source_board_sha256'] and sha(seed)==r['seed_sha256']
    b=k.LoadBoard(str(seed));tree=s.parse(session.read_text());routes=s.child(tree,'routes')
    assert [a.value for a in s.child(routes,'resolution')[1:]]==['um','10']
    layers={b.GetLayerName(i):i for i in b.GetEnabledLayers().CuStack()}
    point=lambda a,c:k.VECTOR2I(k.FromMM(float(a.value)/10000),k.FromMM(-float(c.value)/10000))
    added=0
    for net in s.children(s.child(routes,'network_out'),'net'):
        name=net[1].value;assert b.FindNet(name),name
        for entry in net[2:]:
            if s.tag(entry)=='wire':
                p=s.child(entry,'path');layer=layers[p[1].value];points=[point(a,c) for a,c in zip(p[3::2],p[4::2])]
                for a,c in zip(points,points[1:]):
                    if any(not isinstance(t,k.PCB_VIA) and t.GetLayer()==layer and t.GetNetname()==name and ((t.GetStart()==a and t.GetEnd()==c) or (t.GetStart()==c and t.GetEnd()==a)) for t in b.GetTracks()):continue
                    t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(k.FromMM(float(p[2].value)/10000));t.SetLayer(layer);t.SetNet(b.FindNet(name));b.Add(t);added+=1
            elif s.tag(entry)=='via':
                match=re.fullmatch(r'Via\[0-\d+\]_(\d+):(\d+)_um',entry[1].value);assert match,entry[1].value;q=point(entry[2],entry[3])
                same=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetPosition()==q]
                if same:assert all(t.GetNetname()==name for t in same);continue
                v=k.PCB_VIA(b);v.SetPosition(q);v.SetWidth(k.FromMM(float(match[1])/1000));v.SetDrill(k.FromMM(float(match[2])/1000));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(name));b.Add(v);added+=1
            else:raise ValueError(s.tag(entry))
    parity(b,source);m.boardpath=lambda domain:path;m.save(b,'flange');b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());m.save(b,'flange')
    r.update({'stage':'session_imported_native_DRC_pending','candidate_board_sha256':sha(path),'session_sha256':sha(session),'added_route_objects':added,'script_sha256':sha(Path(__file__))})
    (folder/'placement-routing.json').write_text(json.dumps(r,indent=2)+'\n');assert sha(source)==r['source_board_sha256'];print('Imported session',path,added,flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=('prepare','import'));ap.add_argument('--output',required=True,type=Path);ap.add_argument('--session',type=Path);a=ap.parse_args()
    if a.action=='prepare':prepare(a.output.resolve())
    else:assert a.session;import_session(a.output.resolve(),a.session.resolve())
if __name__=='__main__':main()
