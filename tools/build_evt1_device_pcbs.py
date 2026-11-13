"""Integrate EVT1 device circuits with the preserved R35F layout seeds.

Run using KiCad7's bundled Python. Existing power routing is retained outside
the explicitly changed interfaces. Placement, native DRC, netlist parity and
mechanical fit must all pass before these become fabrication candidates.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import wx
APP = wx.App(False)
import pcbnew as k
import kicad_sexp as s

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/pcb/evt1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xy(x, y):
    return k.VECTOR2I(k.FromMM(100+x), k.FromMM(130-y))


def mech(point):
    return [round(k.ToMM(point.x)-100, 6), round(130-k.ToMM(point.y), 6)]


def boardpath(domain):
    return BASE/domain/(domain+"-evt1.kicad_pcb")


def netlist(domain):
    tree = ET.parse(BASE/domain/(domain+"-native.xml")).getroot()
    parts = {c.get("ref"):c for c in tree.findall("./components/comp")}
    pins = {(n.get("ref"), n.get("pin")):net.get("name")
            for net in tree.findall("./nets/net") for n in net}
    return parts, pins


def library(domain, identifier):
    alias, name = identifier.split(":")
    table = s.parse((BASE/domain/"fp-lib-table").read_text())
    lib = next(n for n in s.children(table,"lib") if s.value(n,"name")==alias)
    folder = (BASE/domain/s.value(lib,"uri").replace("${KIPRJMOD}/", "")).resolve()
    return folder, name


def pose(fp, x, y, angle, side):
    if (fp.GetLayer()==k.B_Cu) != (side=="B"):
        fp.Flip(fp.GetPosition(), True)
    fp.SetOrientationDegrees(angle)
    fp.SetPosition(xy(x,y))


def rect(fp, layers):
    boxes = [g.GetBoundingBox() for g in fp.GraphicalItems()
             if isinstance(g,k.PCB_SHAPE) and g.GetLayer() in layers]
    if not boxes:
        boxes = [p.GetBoundingBox() for p in fp.Pads() if p.GetNumber() or p.GetDrillSize().x]
    return [k.ToMM(min(b.GetLeft() for b in boxes))-100,
            130-k.ToMM(max(b.GetBottom() for b in boxes)),
            k.ToMM(max(b.GetRight() for b in boxes))-100,
            130-k.ToMM(min(b.GetTop() for b in boxes))]


def overlaps(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6


def touches(item, boxes):
    bb=item.GetBoundingBox()
    a=[k.ToMM(bb.GetLeft())-100,130-k.ToMM(bb.GetBottom()),
       k.ToMM(bb.GetRight())-100,130-k.ToMM(bb.GetTop())]
    return any((isinstance(item,k.PCB_VIA) or item.GetLayer()==b['layer']) and
               overlaps(a,b['xy']) for b in boxes)


def ripbox(fp, margin):
    b=rect(fp,[k.F_CrtYd,k.B_CrtYd])
    return {'xy':[b[0]-margin,b[1]-margin,b[2]+margin,b[3]+margin],
            'layer':fp.GetLayer()}


def component(board, domain, c, pins, position):
    ref=c.get("ref"); identifier=c.findtext("footprint")
    folder,name=library(domain,identifier)
    f=k.FootprintLoad(str(folder),name); assert f,identifier
    f.SetReference(ref); f.SetValue(c.findtext("value"))
    f.SetFPID(k.LIB_ID(identifier.split(":")[0],name))
    f.SetPath(k.KIID_PATH(c.find("sheetpath").get("tstamps")+c.findtext("tstamps")))
    f.Reference().SetVisible(False);f.Value().SetVisible(False)
    board.Add(f);pose(f,*position)
    for p in f.Pads():
        net=pins.get((ref,p.GetNumber()))
        if net:p.SetNet(board.FindNet(net))
        else:p.SetNetCode(0)
    return f


def outline(board, points):
    for g in list(board.GetDrawings()):
        if g.GetLayer()==k.Edge_Cuts:board.Delete(g)
    for a,b in zip(points,points[1:]+points[:1]):
        g=k.PCB_SHAPE(board);g.SetShape(k.SHAPE_T_SEGMENT)
        g.SetStart(xy(*a));g.SetEnd(xy(*b));g.SetWidth(k.FromMM(.05));g.SetLayer(k.Edge_Cuts);board.Add(g)


def save(board,domain):
    # Native SaveBoard rewrites .kicad_pro, so set these in its settings too.
    d=board.GetDesignSettings(); d.m_MinClearance=k.FromMM(.1)
    d.m_TrackMinWidth=k.FromMM(.15);d.m_CopperEdgeClearance=k.FromMM(.3)
    d.m_HoleClearance=k.FromMM(.25)
    d.m_MinThroughDrill=k.FromMM(.3 if domain=='flange' else .2)
    d.m_ViasMinSize=k.FromMM(.6 if domain=='flange' else .5)
    default=d.m_NetSettings.m_DefaultNetClass
    default.SetClearance(k.FromMM(.1));default.SetTrackWidth(k.FromMM(.2))
    default.SetViaDiameter(k.FromMM(.6 if domain=='flange' else .5))
    default.SetViaDrill(k.FromMM(.3 if domain=='flange' else .2))
    k.SaveBoard(str(boardpath(domain)),board)


def export_dsn(board,domain):
    path=boardpath(domain).with_suffix('.dsn')
    assert k.ExportSpecctraDSN(board,str(path))
    source=path.read_text()
    ground={'In2.Cu','In4.Cu'} if domain=='body' else ({'In1.Cu'} if domain=='flange' else set())
    # Native GND pours are refilled after routing. Reserve complete reference
    # layers; do not pretend all signal layers are unbroken ground planes.
    # Preserve KiCad's DSN lexer-sensitive quote declaration and line layout.
    # These simple native plane polygons have no nested cutouts.
    source=re.sub(r'\s*\(plane GND \(polygon (\S+) [^()]*\)\)',
                  lambda m:m.group(0) if m.group(1) in ground else '',source)
    source=re.sub(r'(\(layer (\S+)\s+\(type )signal(\))',
                  lambda m:m.group(1)+('power' if m.group(2) in ground else 'signal')+m.group(3),source)
    def inset(match):
        nums=[float(v) for v in match.group(1).split()];points=list(zip(nums[::2],nums[1::2]))
        if points[0]==points[-1]:points.pop()
        sign=1 if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))>0 else -1
        shifted=[]
        for a,b,c in zip(points[-1:]+points[:-1],points,points[1:]+points[:1]):
            u=(b[0]-a[0],b[1]-a[1]);v=(c[0]-b[0],c[1]-b[1]);lu=math.hypot(*u);lv=math.hypot(*v)
            n=(-sign*u[1]/lu,sign*u[0]/lu);m=(-sign*v[1]/lv,sign*v[0]/lv)
            # Router's own boundary clearance is about .1mm. Reserve another
            # .22mm, preserving the actual PCB outline in the native file.
            scale=220/(1+n[0]*m[0]+n[1]*m[1])
            shifted.append((b[0]+scale*(n[0]+m[0]),b[1]+scale*(n[1]+m[1])))
        return '(boundary (path pcb 0 '+ ' '.join(f'{v:.3f}' for p in shifted+[shifted[0]] for v in p)+'))'
    source,count=re.subn(r'\(boundary\s+\(path pcb 0\s+([^()]*)\)\s*\)',inset,source)
    assert count==1,(domain,'expected a single polygon boundary')
    path.write_text(source)


def locating_hole(board,ref,point,diameter):
    name=f"NPTH_{diameter}mm_LocatingPin"
    path=BASE/'EVT1.pretty'/(name+'.kicad_mod')
    path.write_text(f'''(footprint "{name}" (version 20221018) (generator build_evt1_device_pcbs)
      (layer "F.Cu") (attr exclude_from_bom exclude_from_pos_files)
      (fp_text reference "REF**" (at 0 0) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (fp_text value "{name}" (at 0 0) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (pad "" np_thru_hole circle (at 0 0) (size {diameter} {diameter}) (drill {diameter}) (layers "*.Cu" "*.Mask")))\n''')
    f=k.FootprintLoad(str(path.parent),name);assert f
    f.SetFPID(k.LIB_ID('EVT1',name))
    f.SetReference(ref);f.SetPosition(xy(*point));f.Reference().SetVisible(False);f.Value().SetVisible(False);board.Add(f)
    return f


def sensor():
    domain='sensor';parts,pins=netlist(domain)
    b=k.BOARD();b.SetFileName(str(boardpath(domain)));b.SetCopperLayerCount(2)
    b.GetDesignSettings().SetBoardThickness(k.FromMM(1))
    for net in sorted(set(pins.values())):b.Add(k.NETINFO_ITEM(b,net))
    positions={'U81':(6.5,4.7,0,'F'),'C81':(6.5,2.6,0,'F'),
               'C82':(8.7,4.85,90,'F'),'C84':(8.7,6.9,0,'F'),
               'C83':(3.2,4.4,90,'F'),'J82':(3.5,8.5,0,'F')}
    for ref,c in parts.items():component(b,domain,c,pins,positions[ref])
    points=[(.5,0),(11.5,0),(12,.5),(12,9.5),(11.5,10),(.5,10),(0,9.5),(0,.5)]
    outline(b,points)
    locating_hole(b,'H1',(1.5,1.5),1.6);locating_hole(b,'H2',(10.5,1.5),1.6)
    for f in b.GetFootprints():f.SetLocked(True)
    # Keep copper/vias below the MEMS body out of the first routing candidate.
    # The solid bottom GND reference is added after routing.
    zone=k.ZONE(b);zone.SetIsRuleArea(True);zone.SetLayer(k.B_Cu)
    zone.SetDoNotAllowTracks(True);zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowCopperPour(False);zone.SetDoNotAllowPads(False);zone.SetDoNotAllowFootprints(False)
    p=zone.Outline();p.NewOutline()
    for q in ((5.45,3.65),(7.55,3.65),(7.55,5.75),(5.45,5.75)):
        a=xy(*q);p.Append(a.x,a.y)
    b.Add(zone);save(b,domain)
    b=k.LoadBoard(str(boardpath(domain)));seed=boardpath(domain).with_name('placement.kicad_pcb');seed.write_bytes(boardpath(domain).read_bytes())
    export_dsn(b,domain)
    rows=[{'ref':f.GetReference(),'xy_mm':mech(f.GetPosition()),'side':'F',
           'courtyard_xy_mm':rect(f,[k.F_CrtYd,k.B_CrtYd]),'fab_xy_mm':rect(f,[k.F_Fab,k.B_Fab]),
           'pads':[{'n':p.GetNumber(),'net':p.GetNetname(),'xy_mm':mech(p.GetPosition())} for p in f.Pads()]} for f in b.GetFootprints()]
    conflicts=[[a['ref'],c['ref']] for i,a in enumerate(rows) for c in rows[i+1:]
               if overlaps(a['courtyard_xy_mm'],c['courtyard_xy_mm'])]
    (BASE/domain/'placement.json').write_text(json.dumps({'placement_sha256':sha(seed),
        'netlist_sha256':sha(BASE/domain/(domain+'-native.xml')),'outline_xy_mm':points,
        'placements':rows,'courtyard_conflicts':conflicts},indent=2)+'\n')
    print('sensor courtyard conflicts:',conflicts,flush=True)


def place(domain):
    parts,pins=netlist(domain)
    source=BASE/"layout-seeds"/(domain+"-r35.kicad_pcb")
    b=k.LoadBoard(str(source));b.SetFileName(str(boardpath(domain)))
    oldroutes=len(list(b.GetTracks()))
    for net in sorted(set(pins.values())):
        if not b.FindNet(net):b.Add(k.NETINFO_ITEM(b,net))
    if b.FindNet("ACCEL_INT_N"):
        for item in list(b.GetTracks()):
            if item.GetNetname()=="ACCEL_INT_N":item.SetNet(b.FindNet("TIP_EXC_EN"))
    # Old rule areas include obsolete MEMS and USB corridors. Replace with the
    # current package/USB reservations after placement, retaining plane zones.
    for z in list(b.Zones()):
        if z.GetIsRuleArea():b.Delete(z)
    footprints={f.GetReference():f for f in b.GetFootprints()}
    removed=[];changed=[];ripboxes=[]
    for ref,f in list(footprints.items()):
        identifier=parts[ref].findtext("footprint") if ref in parts else None
        if ref not in parts or str(f.GetFPID().GetLibItemName()) != identifier.split(":")[-1]:
            ripboxes.append(ripbox(f,.25))
            b.Delete(f);del footprints[ref];removed.append(ref)
    if domain=="body":
        positions={"U7":(-6.05,36.7,0,"F"),"C61":(-3.7,39.1,0,"F"),
                   "R61":(-6.1,39.7,0,"F"),"C62":(-6.1,40.9,0,"F"),
                   "R62":(-6.1,42.1,0,"F"),"R63":(-6.1,43.3,0,"F"),
                   "C63":(-3.9,43.3,0,"F"),"J5":(3.3,50.35,180,"F"),
                   "J81":(-8.7,40.0,90,"F")}
        # EN1 now GND. Remove only its old tiny VBUS branch, leaving charger
        # input/output power loops untouched; new connection is native-routed.
        en=next(p for p in footprints["U1"].Pads() if p.GetNumber()=="6")
        p=mech(en.GetPosition());ripboxes.append({'xy':[p[0]-.35,p[1]-.35,p[0]+.35,p[1]+.35],'layer':k.F_Cu})
    else:
        positions={"J1":(-24.7,-24.15,0,"B"),"U75":(-20.5,-21.4,0,"B"),
                   "R75":(-17.5,-11.3,90,"F"),"R76":(-13.6,-11.3,90,"F"),
                   "R39":(-14.0,-26.7,90,"B"),"R40":(-17.1,-26.1,0,"B"),
                   "C34":(-14.6,-23.6,90,"B"),"U71":(-15.9,-11.5,0,"B"),
                   "C71":(-13.85,-11.2,0,"B"),"R71":(-18,-11.3,90,"B"),
                   "D71":(-21.2,-17.8,0,"B"),"D72":(-15.3,-20.5,90,"B"),
                   "D73":(-16.75,-17.6,0,"B"),"R34":(-14.9,-14.1,90,"B")}
        # These signal paths change at the external interface/diode OR.
        reroute={"USB_DM","USB_DP","POWER_N","BOOT_N","VBAT_ADC","DOCK_5V"}
        for item in list(b.GetTracks()):
            if item.GetNetname() in reroute:b.Delete(item)
        points=[(-37.3,-26),(-18.9,-26),(-18.9,-30.3125),(-12.7,-30.3125),
                (-12.7,-24.5125),(-13.8,-24.5125),(-13.8,-12.5125),
                (-12.7,-12.5125),(-12.7,-6.7125),(-18.9,-6.7125),
                (-18.9,-11),(-37.3,-11)]
        outline(b,points)
        for i,p in enumerate(((-16.7,-29.0125),(-16.7,-8.0125))):
            locating_hole(b,"H"+str(i+1),p,1.8)
    for ref,pos in positions.items():
        if ref not in footprints:continue
        f=footprints[ref];ripboxes.append(ripbox(f,.2))
        pose(f,*pos);changed.append(ref)
        ripboxes.append(ripbox(f,.2))
    for ref,c in parts.items():
        if ref not in footprints:
            assert ref in positions,ref
            footprints[ref]=component(b,domain,c,pins,positions[ref])
            ripboxes.append(ripbox(footprints[ref],.1))
        else:
            f=footprints[ref];f.SetValue(c.findtext("value"))
            f.SetPath(k.KIID_PATH(c.find("sheetpath").get("tstamps")+c.findtext("tstamps")))
            for p in f.Pads():
                net=pins.get((ref,p.GetNumber()))
                if net:p.SetNet(b.FindNet(net))
                else:p.SetNetCode(0)
    if domain=='body':
        # J2 is copper-only, not the retired Pico-Lock housing. Its inherited
        # large header courtyard incorrectly occupied the empty ADC area.
        f=footprints['J2'];old=sorted((p.GetNumber(),mech(p.GetPosition()),p.GetNetname()) for p in f.Pads())
        new=component(b,domain,parts['J2'],pins,(*mech(f.GetPosition()),f.GetOrientationDegrees(),'F'))
        assert sorted((p.GetNumber(),mech(p.GetPosition()),p.GetNetname()) for p in new.Pads())==old
        b.Delete(f);footprints['J2']=new
    for item in list(b.GetTracks()):
        if touches(item,ripboxes):b.Delete(item)
    for f in b.GetFootprints():f.SetLocked(True)
    for item in b.GetTracks():item.SetLocked(True)
    save(b,domain)
    b=k.LoadBoard(str(boardpath(domain)));b.BuildConnectivity()
    k.ZONE_FILLER(b).Fill(b.Zones());save(b,domain)
    # Save a frozen placement/copper seed for reproducible offline routing.
    seed=boardpath(domain).with_name("placement.kicad_pcb");seed.write_bytes(boardpath(domain).read_bytes())
    export_dsn(b,domain)
    rows=[]
    for f in b.GetFootprints():
        rows.append({"ref":f.GetReference(),"xy_mm":mech(f.GetPosition()),"side":"B" if f.GetLayer()==k.B_Cu else "F",
                     "angle_deg":f.GetOrientationDegrees(),"courtyard_xy_mm":rect(f,[k.F_CrtYd,k.B_CrtYd]),
                     "fab_xy_mm":rect(f,[k.F_Fab,k.B_Fab]),
                     "pads":[{"n":p.GetNumber(),"net":p.GetNetname(),"xy_mm":mech(p.GetPosition())} for p in f.Pads()]})
    conflicts=[]
    for i,a in enumerate(rows):
        for c in rows[i+1:]:
            if a["side"]==c["side"] and overlaps(a["courtyard_xy_mm"],c["courtyard_xy_mm"]):conflicts.append([a["ref"],c["ref"]])
    report={"source_sha256":sha(source),"placement_sha256":sha(seed),"netlist_sha256":sha(BASE/domain/(domain+"-native.xml")),
            "old_route_objects":oldroutes,"preserved_route_objects":len(list(b.GetTracks())),
            "removed_or_replaced":removed,"moved":changed,"ripup_boxes_xy_mm":ripboxes,"placements":rows,"courtyard_conflicts":conflicts}
    (BASE/domain/"placement.json").write_text(json.dumps(report,indent=2)+"\n")
    print(domain,"retained",len(list(b.GetTracks())),"route objects; courtyard conflicts:",conflicts,flush=True)


def import_routes(domain):
    path=boardpath(domain);folder=path.parent
    report=json.loads((folder/'placement.json').read_text());seed=folder/'placement.kicad_pcb'
    assert sha(seed)==report['placement_sha256']
    assert sha(folder/(domain+'-native.xml'))==report['netlist_sha256']
    b=k.LoadBoard(str(seed))
    tree=s.parse(path.with_suffix('.ses').read_text());routes=s.child(tree,'routes')
    assert [a.value for a in s.child(routes,'resolution')[1:]]==['um','10']
    layers={b.GetLayerName(i):i for i in b.GetEnabledLayers().CuStack()}
    def point(a,c):return k.VECTOR2I(k.FromMM(float(a.value)/10000),k.FromMM(-float(c.value)/10000))
    for net in s.children(s.child(routes,'network_out'),'net'):
        name=net[1].value;assert b.FindNet(name),name
        for entry in net[2:]:
            if s.tag(entry)=='wire':
                p=s.child(entry,'path');layer=layers[p[1].value]
                points=[point(a,c) for a,c in zip(p[3::2],p[4::2])]
                for a,c in zip(points,points[1:]):
                    if any(isinstance(t,k.PCB_TRACK) and t.GetLayer()==layer and t.GetNetname()==name and
                           ((t.GetStart()==a and t.GetEnd()==c) or (t.GetStart()==c and t.GetEnd()==a)) for t in b.GetTracks()):continue
                    t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(k.FromMM(float(p[2].value)/10000))
                    t.SetLayer(layer);t.SetNet(b.FindNet(name));b.Add(t)
            elif s.tag(entry)=='via':
                match=re.fullmatch(r'Via\[0-\d+\]_(\d+):(\d+)_um',entry[1].value);assert match,entry[1].value
                p=point(entry[2],entry[3])
                existing=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetPosition()==p]
                if existing:
                    assert all(t.GetNetname()==name for t in existing),('Different-net via at the same location',name,mech(p))
                    continue
                v=k.PCB_VIA(b);v.SetPosition(p);v.SetWidth(k.FromMM(float(match[1])/1000));v.SetDrill(k.FromMM(float(match[2])/1000))
                v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(name));b.Add(v)
            else:raise ValueError(s.tag(entry))
    if domain=='sensor':
        for q in ((8.4,2.8),(1.4,6.6),(10.3,7.9)):
            assert not any(isinstance(t,k.PCB_VIA) and t.GetPosition()==xy(*q) for t in b.GetTracks())
            v=k.PCB_VIA(b);v.SetPosition(xy(*q));v.SetWidth(k.FromMM(.5));v.SetDrill(k.FromMM(.2))
            v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet('GND'));b.Add(v)
        for layer in (k.F_Cu,k.B_Cu):
            z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(k.FromMM(.1))
            z.SetMinThickness(k.FromMM(.15));z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(k.FromMM(.15));z.SetThermalReliefSpokeWidth(k.FromMM(.15))
            z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS);p=z.Outline();p.NewOutline()
            for q in ((.4,.4),(11.6,.4),(11.6,9.6),(.4,9.6)):
                a=xy(*q);p.Append(a.x,a.y)
            b.Add(z)
    save(b,domain);b=k.LoadBoard(str(path));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());save(b,domain)
    print(domain,len(list(b.GetTracks())),'routed objects; native DRC pending',flush=True)


def prune(domain):
    """Trim only native-reported loose ends, retaining mid-track junctions.

    A track can have a dangling endpoint while another track joins its middle.
    Deleting that whole track, or recursively using the in-memory endpoint test,
    can remove useful copper. Re-run native DRC between cleanup passes.
    """
    path=boardpath(domain);report_path=path.parent/'drc.json'
    report=json.loads(report_path.read_text());b=k.LoadBoard(str(path))
    ids={item['uuid'] for v in report['violations'] if v['type'] in ('track_dangling','via_dangling') for item in v['items']}
    b.BuildConnectivity();connectivity=b.GetConnectivity();actions=[]
    for t in b.GetTracks():
        uid=t.m_Uuid.AsString()
        if uid not in ids:continue
        row={'uuid':uid,'net':t.GetNetname(),'action':'delete'}
        if not isinstance(t,k.PCB_VIA):
            assert t.GetClass()=='PCB_TRACK','Arc loose ends need a separate trim'
            a,c=mech(t.GetStart()),mech(t.GetEnd());d=[c[i]-a[i] for i in range(2)];ll=sum(v*v for v in d);assert ll>0
            anchors=[]
            def project(q):return max(0,min(1,sum((q[i]-a[i])*d[i] for i in range(2))/ll))
            for q in connectivity.GetConnectedTracks(t):
                if q.m_Uuid.AsString()==uid or q.GetNetname()!=t.GetNetname():continue
                # Connectivity vectors expose vias through PCB_TRACK proxies.
                if q.GetClass()=='PCB_VIA':
                    point=mech(q.GetPosition());anchors.append((project(point),point));continue
                if q.GetLayer()!=t.GetLayer():continue
                assert q.GetClass()=='PCB_TRACK'
                x,y=mech(q.GetStart()),mech(q.GetEnd());e=[y[i]-x[i] for i in range(2)]
                cross=lambda u,v:u[0]*v[1]-u[1]*v[0]
                denominator=cross(d,e)
                if abs(denominator)>1e-12:
                    u=cross([x[i]-a[i] for i in range(2)],e)/denominator
                    v=cross([x[i]-a[i] for i in range(2)],d)/denominator
                    if -1e-6<=u<=1+1e-6 and -1e-6<=v<=1+1e-6:
                        u=max(0,min(1,u));anchors.append((u,[a[i]+u*d[i] for i in range(2)]));continue
                # Overlapping copper can join without intersecting centerlines.
                for point in (x,y):
                    u=project(point);nearest=[a[i]+u*d[i] for i in range(2)]
                    if math.dist(point,nearest)<=k.ToMM(t.GetWidth()+q.GetWidth())/2+1e-6:anchors.append((u,point))
            for pad in connectivity.GetConnectedPads(t):
                point=mech(pad.GetPosition());anchors.append((project(point),point))
            if anchors and math.dist(min(anchors)[1],max(anchors)[1])>1e-6:
                first,last=min(anchors),max(anchors)
                row.update(action='trim',old_start=a,old_end=c,
                           start=first[1],end=last[1])
        actions.append(row)
    byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
    for row in actions:
        t=byid[row['uuid']]
        if row['action']=='delete':b.Delete(t)
        else:t.SetStart(xy(*row['start']));t.SetEnd(xy(*row['end']))
    save(b,domain);b=k.LoadBoard(str(path));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());save(b,domain)
    record=path.parent/'dangling-cleanup.json'
    old=json.loads(record.read_text()) if record.exists() else []
    old.append({'native_DRC_sha256':sha(report_path),'loose_end_actions':actions,'result_board_sha256':sha(path),'native_DRC_rerun_required':True})
    record.write_text(json.dumps(old,indent=2)+'\n')
    print(domain,'trimmed/deleted',len(actions),'native-DRC loose ends; rerun native DRC',flush=True)


def freeze(domain):
    path=boardpath(domain);b=k.LoadBoard(str(path))
    for t in b.GetTracks():t.SetLocked(True)
    save(b,domain);seed=path.parent/'placement.kicad_pcb';seed.write_bytes(path.read_bytes())
    report=json.loads((path.parent/'placement.json').read_text());report['placement_sha256']=sha(seed)
    report['frozen_route_objects']=len(list(b.GetTracks()))
    byref={f.GetReference():f for f in b.GetFootprints()}
    for row in report['placements']:
        f=byref[row['ref']];row.update({'xy_mm':mech(f.GetPosition()),'side':'B' if f.GetLayer()==k.B_Cu else 'F',
            'angle_deg':f.GetOrientationDegrees(),'courtyard_xy_mm':rect(f,[k.F_CrtYd,k.B_CrtYd]),'fab_xy_mm':rect(f,[k.F_Fab,k.B_Fab]),
            'pads':[{'n':p.GetNumber(),'net':p.GetNetname(),'xy_mm':mech(p.GetPosition())} for p in f.Pads()]})
    (path.parent/'placement.json').write_text(json.dumps(report,indent=2)+'\n');export_dsn(b,domain)


def board_outline(b):
    edges=[(mech(g.GetStart()),mech(g.GetEnd())) for g in b.GetDrawings() if g.GetLayer()==k.Edge_Cuts]
    points=list(edges.pop(0))
    while edges:
        match=next((i,c if a==points[-1] else a) for i,(a,c) in enumerate(edges) if a==points[-1] or c==points[-1])
        points.append(match[1]);edges.pop(match[0])
    assert points[-1]==points[0];return points[:-1]


def stitch(domain):
    """Connect surface GND regions to the reserved reference planes.

    Conservative copper/holes/keepout screening only proposes via positions.
    Native DRC is mandatory afterward; it decides electrical connectivity.
    """
    path=boardpath(domain);b=k.LoadBoard(str(path));points=board_outline(b)
    if domain=='flange':
        for z in b.Zones():
            if not z.GetIsRuleArea():
                p=z.Outline();p.RemoveAllContours();p.NewOutline()
                for q in points:
                    a=xy(*q);p.Append(a.x,a.y)
    save(b,domain);b=k.LoadBoard(str(path));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones())
    diameter,drill=(.6,.3) if domain=='flange' else (.5,.2)
    radius=max(diameter/2+.105,drill/2+.255)
    def pt_segment(p,a,c):
        dx,dy=c[0]-a[0],c[1]-a[1];ll=dx*dx+dy*dy
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll)) if ll else 0
        return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
    boxes=[];circles=[];tracks=[];forbidden=[]
    for f in b.GetFootprints():
        for p in f.Pads():
            bb=p.GetBoundingBox();x0,y1=mech(bb.GetOrigin());x1,y0=mech(bb.GetEnd())
            # Also avoid drilling through same-net SMD pads.
            margin=radius if p.GetNetname()!='GND' else drill/2+.15
            boxes.append((x0-margin,y0-margin,x1+margin,y1+margin))
            if p.GetDrillSize().x:
                circles.append((mech(p.GetPosition()),(k.ToMM(p.GetDrillSize().x)+drill)/2+.255))
    for t in b.GetTracks():
        if t.GetNetname()=='GND':continue
        if isinstance(t,k.PCB_VIA):circles.append((mech(t.GetPosition()),k.ToMM(t.GetWidth())/2+radius))
        else:tracks.append((mech(t.GetStart()),mech(t.GetEnd()),radius+k.ToMM(t.GetWidth())/2))
    # Board rule areas and footprint-owned antenna/MEMS keepouts both matter.
    zones=list(b.Zones())
    for f in b.GetFootprints():zones.extend(list(f.Zones()))
    for z in zones:
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            bb=z.GetBoundingBox();a=mech(bb.GetOrigin());c=mech(bb.GetEnd());forbidden.append((a[0]-.3,c[1]-.3,c[0]+.3,a[1]+.3))
    def clear(q):
        if any(pt_segment(q,a,c)<diameter/2+.325 for a,c in zip(points,points[1:]+points[:1])):return False
        if any(a<=q[0]<=c and e<=q[1]<=f for a,e,c,f in boxes+forbidden):return False
        if any(math.dist(q,p)<r for p,r in circles):return False
        if any(pt_segment(q,a,c)<r for a,c,r in tracks):return False
        return True
    added=[]
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname()!='GND':continue
        # KiCad7 ZONE.GetLayer() can return F.Cu for a B.Cu zone. The native
        # layer set is authoritative; guard the filled-polygon map as well.
        layer=next((ly for ly in b.GetEnabledLayers().CuStack() if z.GetLayerSet().Contains(ly)),None)
        if layer is None or not z.HasFilledPolysForLayer(layer):continue
        polys=z.GetFilledPolysList(layer)
        for i in range(polys.OutlineCount()):
            contour=polys.COutline(i);vertices=[mech(contour.CPoint(j)) for j in range(contour.PointCount())]
            if not vertices:continue
            existing=[mech(v.GetPosition()) for v in b.GetTracks() if isinstance(v,k.PCB_VIA) and v.GetNetname()=='GND']
            if any(polys.Contains(xy(p[0]+.26*math.cos(a),p[1]+.26*math.sin(a)),i)
                   for p in existing for a in (0,math.pi/2,math.pi,3*math.pi/2)):continue
            x0=min(p[0] for p in vertices);x1=max(p[0] for p in vertices)
            y0=min(p[1] for p in vertices);y1=max(p[1] for p in vertices)
            candidates=[(x0+.2+.35*x,y0+.2+.35*y) for x in range(max(0,int((x1-x0)/.35))) for y in range(max(0,int((y1-y0)/.35)))]
            candidates.sort(key=lambda q:math.hypot(q[0]-(x0+x1)/2,q[1]-(y0+y1)/2))
            q=next((p for p in candidates if polys.Contains(xy(*p),i) and clear(p)),None)
            if q is None:continue
            v=k.PCB_VIA(b);v.SetPosition(xy(*q));v.SetWidth(k.FromMM(diameter));v.SetDrill(k.FromMM(drill))
            v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet('GND'));b.Add(v)
            added.append({'layer':b.GetLayerName(layer),'xy_mm':q})
    save(b,domain);b=k.LoadBoard(str(path));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());save(b,domain)
    (path.parent/'ground-stitching.json').write_text(json.dumps({'added':added,'board_sha256':sha(path),'scope':'Conservative placement screen; native DRC required'},indent=2)+'\n')
    print(domain,'added',len(added),'GND stitches',flush=True)


def mcad(domain):
    path=boardpath(domain);b=k.LoadBoard(str(path))
    selection_path=BASE/'parts-selection.json'
    selection=json.loads(selection_path.read_text()) if selection_path.exists() else None
    selected={(r['domain'],r['ref']):r for r in selection['components']} if selection else {}
    legacy=json.loads((ROOT/'hardware/pcb/prototype-r2/layout-candidates-r0.json').read_text())['parts']
    heights={ref:float(v['height_mm']) for ref,v in legacy.items()}
    heights.update({'U7':1.1,'J5':2.9,'J6':3.2,'J7':3.2,'J81':1.25,'J82':1.25,'J1':1.25,'U71':.65,'U75':1.45,'U81':1.1,
                    'C83':1.45,'D71':1.25,'D72':1.25,'D73':1.25,'J2':0})
    for ref in ['R61','R62','R63','C61','C62','C63','C71','R71','R75','R76','C81','C82','C84']:heights[ref]=.6
    components=[];pads=[];holes=[]
    for fp in b.GetFootprints():
        ref=fp.GetReference();back=fp.GetLayer()==k.B_Cu
        if not ref.startswith('H'):
            assert ref in heights,ref
            components.append({'ref':ref,'xy_mm':mech(fp.GetPosition()),'back':back,
                               'angle_deg':fp.GetOrientationDegrees(),'fab_bounds_xy_mm':rect(fp,[k.F_Fab,k.B_Fab]),
                               'courtyard_xy_mm':rect(fp,[k.F_CrtYd,k.B_CrtYd]),'height_budget_mm':heights[ref],
                               'scope':'Fab outline / conservative height or hand-wire allowance, not OEM 3D'})
            if selection:
                part=selected[(domain,ref)];row=components[-1]
                row['selected_mpn']=part['mpn']
                if part.get('maximum_height_mm') is not None:
                    assert part['maximum_height_mm']<=heights[ref]+1e-8,(domain,ref,'Selected height exceeds allowance')
                if part.get('maximum_body_xy_mm'):
                    a=math.radians(fp.GetOrientationDegrees());ll,ww=part['maximum_body_xy_mm'];x,y=mech(fp.GetPosition())
                    dx=(abs(math.cos(a))*ll+abs(math.sin(a))*ww)/2;dy=(abs(math.sin(a))*ll+abs(math.cos(a))*ww)/2
                    original=row['fab_bounds_xy_mm'];maximum=[x-dx,y-dy,x+dx,y+dy]
                    row['fab_outline_bounds_xy_mm']=original
                    row['fab_bounds_xy_mm']=[min(original[0],maximum[0]),min(original[1],maximum[1]),max(original[2],maximum[2]),max(original[3],maximum[3])]
                    row['maximum_body_xy_mm']=part['maximum_body_xy_mm']
                    row['scope']='Union of native Fab outline and selected centered part maximum XY; conservative height/hand-wire allowance, not OEM 3D'
        for p in fp.Pads():
            pads.append({'ref':ref,'number':p.GetNumber(),'net':p.GetNetname(),'xy_mm':mech(p.GetPosition()),'back':back})
            if p.GetDrillSize().x:
                holes.append({'ref':ref,'xy_mm':mech(p.GetPosition()),'drill_xy_mm':[k.ToMM(p.GetDrillSize().x),k.ToMM(p.GetDrillSize().y)],
                              'angle_deg':p.GetOrientationDegrees()})
    points=board_outline(b)
    report={'board_file':str(path.relative_to(ROOT)),'board_sha256':sha(path),'thickness_mm':k.ToMM(b.GetDesignSettings().GetBoardThickness()),
            'coordinate_frame':'R35 mechanical XY: native(x,y)=(100+X,130-Y) mm',
            'outline_xy_mm':points,'components':components,'pads':pads,'holes':holes,
            'mating_allowances':[{'ref':'J5','height_from_F_surface_mm':6.3,'scope':'JST eSH top-entry mated assembly reference height6.3mm; wire egress/bends are separate, not included in this housing envelope','source':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf'}] if domain=='body' else [],
            'route_objects':len(list(b.GetTracks()))}
    if selection:
        report['parts_selection_sha256']=sha(selection_path)
    (path.parent/'mcad.json').write_text(json.dumps(report,indent=2)+'\n');print(domain,'native MCAD envelope saved')


def restore_controls(domain):
    """Restore unchanged-terminal copper from primitive source records.

    Avoid loading a second BOARD while the destination is live in KiCad7.
    Native DRC must resolve interactions with the newly added routing.
    """
    assert domain in ('body','flange')
    data=json.loads((BASE/domain/'preserved-control-routes.json').read_text())
    assert sha(BASE/'layout-seeds'/(domain+'-r35.kicad_pcb'))==data['source_sha256']
    b=k.LoadBoard(str(boardpath(domain)))
    for t in list(b.GetTracks()):
        if t.GetNetname() in data['nets']:b.Delete(t)
    def point(q):return k.VECTOR2I(k.FromMM(q[0]),k.FromMM(q[1]))
    layers={b.GetLayerName(i):i for i in b.GetEnabledLayers().CuStack()}
    for row in data['records']:
        if row['kind']=='via':
            t=k.PCB_VIA(b);t.SetPosition(point(row['xy']));t.SetWidth(k.FromMM(row['width']));t.SetDrill(k.FromMM(row['drill']))
            t.SetViaType(k.VIATYPE_THROUGH);t.SetLayerPair(k.F_Cu,k.B_Cu)
        else:
            t=k.PCB_TRACK(b);t.SetStart(point(row['start']));t.SetEnd(point(row['end']));t.SetWidth(k.FromMM(row['width']));t.SetLayer(layers[row['layer']])
        t.SetNet(b.FindNet(row['net']));t.SetLocked(True);b.Add(t)
    save(b,domain);b=k.LoadBoard(str(boardpath(domain)));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());save(b,domain)
    print(domain,'restored',len(data['records']),'source route records; native DRC required')


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=("place","import","prune","freeze","mcad","stitch","restore_controls"));ap.add_argument("domain",choices=("body","flange","sensor"));ap.add_argument("--restart-layout",action="store_true",help="Explicitly discard the current saved board and restart placement from its seed");a=ap.parse_args()
    if a.action=='place' and boardpath(a.domain).exists() and not a.restart_layout:
        ap.error("Saved native board exists. Copy it outside the output directory before using --restart-layout; place discards saved routing.")
    if a.action=='place' and a.domain=='sensor':sensor()
    else:{"place":place,"import":import_routes,"prune":prune,"freeze":freeze,"mcad":mcad,"stitch":stitch,"restore_controls":restore_controls}[a.action](a.domain)
