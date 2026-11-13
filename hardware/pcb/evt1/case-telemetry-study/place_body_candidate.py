"""Native footprint packing seed; no original body source/artwork mutation.

This is explicitly a placement-only derivative. The source routed board remains
the protected route authority; do not use this seed as replacement artwork.
"""
from pathlib import Path
import hashlib,json,math,sys,xml.etree.ElementTree as E
import wx
APP=wx.App(False)
import pcbnew as k

H=Path(__file__).resolve().parent
ROOT=H.parents[3]
O=H/'body-instrumentation'
SOURCE=ROOT/'hardware/pcb/evt1/body/body-evt1.kicad_pcb'
DEST=O/'body-instrumentation-placement.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mm=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
point=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))


def boxes(fp):
    points=[]
    for g in fp.GraphicalItems():
        if g.GetLayer()in(k.F_CrtYd,k.B_CrtYd):
            bb=g.GetBoundingBox()
            points.extend([mm(bb.GetOrigin()),mm(bb.GetEnd())])
    if not points:
        # J81 is the original four hand-solder lands, not a purchased package.
        # Preserve its existing explicit source wire-access reservation.
        assert fp.GetReference()=='J81',fp.GetReference()
        source=json.loads((ROOT/'hardware/pcb/evt1/body/mcad.json').read_text())
        c=next(v for v in source['components']if v['ref']=='J81')['courtyard_xy_mm']
        return [100+c[0],130-c[3],100+c[2],130-c[1]]
    return [min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]


def inside(x,y):
    # Original finished-outline polygon; conservative0.3edge allowance.
    X,Y=x-100,130-y
    return -9.7<=X<=9.7 and 26.3<=Y<=53.7 and (Y>=31 or abs(X)<=7+(Y-26)*.6-.3)


def main():
    assert not DEST.exists(),'Existing placement candidate must be preserved; explicitly remove only after review'
    start=sha(SOURCE)
    r=E.parse(O/'native.xml').getroot()
    terminals={(n.get('ref'),n.get('pin')):net.get('name')for net in r.findall('./nets/net')for n in net.findall('node')}
    parts=json.loads((O/'source-bindings.json').read_text())['new_parts']
    # Strip routing from a text-derived temporary seed before native loading.
    # KiCad7 mutating SWIG ownership while iterating mixed track/zone wrappers
    # can invalidate later wrappers. No C++ removal or original-file edit.
    sys.path.insert(0,str(ROOT/'tools'))
    import kicad_sexp as sexp
    tree=sexp.parse(SOURCE.read_text())
    removed=sum(sexp.tag(x)in('segment','via','arc')for x in tree)
    tree=[x for x in tree if sexp.tag(x)not in('segment','via','arc','zone')]
    seed=Path('/private/tmp/compass-case-telemetry/body-empty-placement-seed.kicad_pcb')
    sexp.write(seed,tree)
    del tree
    b=k.LoadBoard(str(seed))
    old={f.GetReference():f for f in b.GetFootprints()};assert len(old)==69
    pose=lambda f:(*mm(f.GetPosition()),f.GetOrientationDegrees(),f.IsFlipped())
    oldposes={ref:pose(fp)for ref,fp in old.items()}
    # Remove copper only in this explicitly unrouted packing derivative.
    # The authoritative original2369route objects are never rewritten.
    assert not list(b.GetTracks()) and b.GetAreaCount()==0
    for name in sorted(set(terminals.values())):
        if name not in b.GetNetsByName():b.Add(k.NETINFO_ITEM(b,name))
    for ref,fp in old.items():
        for p in fp.Pads():
            num=p.GetNumber()
            if num and (ref,num)in terminals:p.SetNet(b.GetNetsByName()[terminals[(ref,num)]])
    occupied=[(f.IsFlipped(),boxes(f))for f in old.values()]
    # Real selected land-pattern courtyards, not component bounding proxies.
    preferred={
      'U802':(7.8,50.8,False,90),'U803':(-8,40.1,True,90),
      'U804':(-5.6,45.4,False,0),'U801':(-1.9,36.8,False,0),
      'C802':(5.5,53.5,False,0),'C803':(-8,42,True,0),
      'C804':(-2.6,45.4,False,0),'C801':(-1.8,38.5,False,0),
      'R801':(7.9,43.5,False,0),'R802':(8,49.7,False,0),
      'R803':(-3.4,40.5,False,0),'R804':(-8,41.9,True,0),
      'C807':(7.8,49,False,0),'C808':(-8,42,True,0),
      'R805':(-7.7,38.8,False,0),'C805':(-5.2,38.5,False,0),
      'R806':(-3.5,37.5,False,0),'C806':(-2,38.5,False,0),
      'R807':(-5.3,46,False,0),'R808':(-2.2,35,False,0),
      'R809':(-1.8,39.5,False,0)}
    byref={p['ref']:p for p in parts};assert set(byref)==set(preferred)
    order=['U802','U803','U804','U801','C802','C803','C804','C801']+[x for x in preferred if not x.startswith('U')and x not in('C802','C803','C804','C801')]
    placements=[]
    for ref in order:
        data=byref[ref];px,py,back,preferred_angle=preferred[ref]
        fp=k.FootprintLoad(str(O/'Telemetry.pretty'),data['footprint'].split(':')[1]);assert fp
        fp.SetReference(ref);fp.SetValue(data['value']);fp.SetFPID(k.LIB_ID('Telemetry',data['footprint'].split(':')[1]))
        b.Add(fp)
        # Selected side is explicit. Stay on that side; no hidden layer escape.
        if back:fp.Flip(fp.GetPosition(),False)
        candidates=[]
        for a in (preferred_angle,(preferred_angle+90)%180):
            fp.SetPosition(point(100,130));fp.SetOrientationDegrees(a)
            rel=boxes(fp);rel=[rel[0]-100,rel[1]-130,rel[2]-100,rel[3]-130]
            for ix in range(-93,94):
                for iy in range(263,538):
                    x,y=100+ix/10,130-iy/10
                    box=[x+rel[0],y+rel[1],x+rel[2],y+rel[3]]
                    if not all(inside(xx,yy)for xx,yy in((box[0],box[1]),(box[0],box[3]),(box[2],box[1]),(box[2],box[3]))):continue
                    if any(side==back and not(box[2]+.025<c[0]or box[0]-.025>c[2]or box[3]+.025<c[1]or box[1]-.025>c[3])for side,c in occupied):continue
                    score=math.hypot(ix/10-px,iy/10-py)+(.05 if a!=preferred_angle else 0)
                    candidates.append((score,x,y,a,box))
        assert candidates,('no placement',ref)
        _,x,y,a,box=min(candidates)
        fp.SetPosition(point(x,y));fp.SetOrientationDegrees(a)
        for p in fp.Pads():
            key=(ref,p.GetNumber())
            if key in terminals:p.SetNet(b.GetNetsByName()[terminals[key]])
        fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
        occupied.append((back,box))
        placements.append({'ref':ref,'body_XY_mm':[x-100,130-y],'angle_native_deg':a,'back':back,'native_courtyard_bounds_mm':box,'preferred_XY_mm':[px,py],'footprint':data['footprint']})
    assert all(pose(old[ref])==v for ref,v in oldposes.items())
    assert sha(SOURCE)==start
    k.SaveBoard(str(DEST),b)
    settings=json.loads(SOURCE.with_suffix('.kicad_pro').read_text())
    # New default KiCad10 checks must be enabled even when authoring inKiCad7.
    for name in ('track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch',
                 'missing_courtyard','pth_inside_courtyard','npth_inside_courtyard','footprint_type_mismatch'):
        settings['board']['design_settings']['rule_severities'][name]='error'
    settings['board']['design_settings']['drc_exclusions']=[]
    DEST.with_suffix('.kicad_pro').write_text(json.dumps(settings,indent=2)+'\n')
    report={'status':'Native packing seed only; not a replacement routedbody or physical-fit acceptance',
            'builder_sha256':sha(Path(__file__)),'source_original_board_sha256':start,'candidate_board_sha256':sha(DEST),
            'source_full_native_XML_sha256':sha(O/'native.xml'),'all69_original_poses_preserved':True,
            'retained_existing_copper_in_candidate':False,'copper_objects_removed_from_placement_derivative':removed,
            'source_routed_copper_remains_authority':True,'new_positions':placements,'total_positions':90,
            'outline_stackup_unchanged':True,'finished_thickness_mm':1,'layers':6,
            'physical_3D_packing_and_tolerance_acceptance':False,
            'route_requirement':'Carry original source copper into a separate routing derivative with bounded newpart/ADS ripup and nativeDRC; do not route this seed by blindly replacing original artwork.'}
    (O/'placement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'board_sha256':report['candidate_board_sha256'],'positions':90,'old_poses_preserved':69,'added':21}))


if __name__=='__main__':main()
