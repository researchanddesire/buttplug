"""Place/export or import offline routes for the two EVT1 cradle boards.

Run with KiCad7's bundled Python. Native DRC and schematic parity are separate
checks. This never changes the R35F seeds or product-body PCB layouts.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import kicad_sexp as s
import wx
APP = wx.App(False)
import pcbnew as k

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/pcb/evt1"


def xy(x, y):
    return k.VECTOR2I(k.FromMM(100 + x), k.FromMM(100 + y))


def coords(p):
    return [round(k.ToMM(p.x)-100, 6), round(k.ToMM(p.y)-100, 6)]


def board_path(domain):
    return BASE / domain / (domain + "-evt1.kicad_pcb")


def save(board, path):
    # SaveBoard also writes the project. Set the intended fabrication rules in
    # its native settings, not only in a JSON file it would then overwrite.
    d=board.GetDesignSettings()
    d.m_MinClearance=k.FromMM(.2);d.m_TrackMinWidth=k.FromMM(.15)
    d.m_HoleClearance=k.FromMM(.15);d.m_CopperEdgeClearance=k.FromMM(.3)
    k.SaveBoard(str(path),board)


def component(board, ref, library, value, position, angle, nets, path):
    alias, name = library.split(":")
    fp = k.FootprintLoad(str(BASE / (alias + ".pretty")), name)
    assert fp, library
    fp.SetReference(ref); fp.SetValue(value)
    fp.SetPosition(xy(*position)); fp.SetOrientationDegrees(angle)
    fp.SetPath(k.KIID_PATH(path)); fp.SetLocked(True)
    fp.Reference().SetTextSize(k.VECTOR2I(k.FromMM(.8), k.FromMM(.8)))
    fp.Reference().SetTextThickness(k.FromMM(.12))
    fp.Value().SetVisible(False)
    for pad in fp.Pads():
        name = nets.get((ref, pad.GetNumber()))
        if name:
            pad.SetNet(board.FindNet(name))
        elif pad.GetNumber():
            # Explicit NC pads have no second terminal to route. Their native
            # netlist names are still assigned above when present.
            assert pad.GetNumber() in ("A8", "B8"), (ref, pad.GetNumber())
    board.Add(fp)
    return fp


def usb_escapes(board):
    """Explicitly bridge both USB-C orientations before the general router.

    A6/B6 and A7/B7 are separate receptacle terminals. A router must not leave
    an orientation floating inside the other pair's escape. Short fanout is
    not a controlled-impedance or measured USB result.
    """
    def track(net, points, layer):
        for a,b in zip(points,points[1:]):
            t=k.PCB_TRACK(board);t.SetStart(xy(*a));t.SetEnd(xy(*b));t.SetWidth(k.FromMM(.2))
            t.SetLayer(layer);t.SetNet(board.FindNet(net));t.SetLocked(True);board.Add(t)
    def via(net, point):
        v=k.PCB_VIA(board);v.SetPosition(xy(*point));v.SetWidth(k.FromMM(.6));v.SetDrill(k.FromMM(.3))
        v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(board.FindNet(net));v.SetLocked(True);board.Add(v)
    for points in (((3.855,10.25),(4.7,10.25),(5.4,9.55)),
                   ((3.855,11.25),(6.2,11.25))):
        track("DOCK_DM",points,k.F_Cu)
    for point in ((5.4,9.55),(6.2,11.25),(9.6,10.05)):via("DOCK_DM",point)
    track("DOCK_DM",((6.2,11.25),(6.2,9.55),(8.1,9.55),(9.6,10.05)),k.B_Cu)
    track("DOCK_DM",((5.4,9.55),(6.2,9.55)),k.B_Cu)
    track("DOCK_DM",((9.6,10.05),(11.3625,10.05),(13.6375,10.05)),k.F_Cu)
    track("DOCK_DP",((3.855,10.75),(4.7,10.75),(5.5,10.3),(8.5,10.3),(10.15,11.95),(11.3625,11.95)),k.F_Cu)
    track("DOCK_DP",((3.855,11.75),(4.8,11.75),(5.45,12.4),(6.4,12.4),(8.5,10.3)),k.F_Cu)


def place(domain):
    path = board_path(domain)
    netlist = ET.parse(path.parent / (domain + "-native.xml")).getroot()
    b = k.BOARD(); b.SetFileName(str(path)); b.SetCopperLayerCount(2)
    b.GetDesignSettings().SetBoardThickness(k.FromMM(1))
    settings = b.GetDesignSettings()
    settings.m_MinClearance = k.FromMM(.2)
    settings.m_TrackMinWidth = k.FromMM(.15)
    settings.m_MinThroughDrill = k.FromMM(.3)
    settings.m_ViasMinSize = k.FromMM(.6)
    default = settings.m_NetSettings.m_DefaultNetClass
    default.SetClearance(k.FromMM(.21)); default.SetTrackWidth(k.FromMM(.2))
    default.SetViaDiameter(k.FromMM(.6)); default.SetViaDrill(k.FromMM(.3))
    nets = {}
    for net in netlist.findall("./nets/net"):
        name = net.get("name")
        b.Add(k.NETINFO_ITEM(b, name))
        for node in net: nets[(node.get("ref"), node.get("pin"))] = name
    if domain == "dock":
        width, height = 28, 22
        # The narrow PCB nose passes through the case wall under the connector.
        # At MCAD origin X=-54, the receptacle face is X=-57.5, flush with case.
        positions = {"J91": ((.175,11),-90), "U91": ((12.5,11),0), "U92": ((19,9),0),
                     "R91": ((8.8,7.5),0), "R92": ((8.8,14.5),0), "R93": ((21.5,12.5),90),
                     "R94": ((24,9),90), "C91": ((15,5.5),0), "C92": ((22,5.5),0),
                     "J93": ((12,18),0), "TP91": ((25,13),0)}
    else:
        width, height = 28, 10
        positions = {"P"+str(91+i): ((4+6*i,6.7),0) for i in range(4)}
        positions["J94"] = ((7.5,8.5),0)
    for c in netlist.findall("./components/comp"):
        ref = c.get("ref")
        assert ref in positions, ref
        position, angle = positions[ref]
        sheet = c.find("sheetpath").get("tstamps")
        fp=component(b, ref, c.findtext("footprint"), c.findtext("value"), position, angle,
                     nets, sheet + c.findtext("tstamps"))
        if ref == "J94":
            fp.Flip(fp.GetPosition(),False)
            fp.Reference().SetPosition(xy(18,8.5))
    if domain == "dock":
        for i, point in enumerate(((7,3),(7,19),(25,3),(25,19))):
            fp = k.FootprintLoad("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/MountingHole.pretty", "MountingHole_2.2mm_M2")
            fp.SetReference("H"+str(i+1));fp.SetPosition(xy(*point));fp.SetLocked(True)
            fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
            b.Add(fp)
    outline = [(0,0),(width,0),(width,height),(0,height)]
    if domain == "dock":
        outline += [(0,16.25),(-2.925,16.25),(-2.925,5.75),(0,5.75)]
    for a,c in zip(outline,outline[1:]+outline[:1]):
        line = k.PCB_SHAPE(b); line.SetShape(k.SHAPE_T_SEGMENT)
        line.SetStart(xy(*a));line.SetEnd(xy(*c));line.SetWidth(k.FromMM(.05));line.SetLayer(k.Edge_Cuts);b.Add(line)
    if domain == "dock": usb_escapes(b)
    text = k.PCB_TEXT(b);text.SetText("EVT1 " + domain + " 1mm")
    text.SetPosition(xy(14, .9 if domain == "dock" else 9.1))
    text.SetTextSize(k.VECTOR2I(k.FromMM(.8), k.FromMM(.8)));text.SetTextThickness(k.FromMM(.12));text.SetLayer(k.F_SilkS);b.Add(text)
    save(b,path)
    seed = path.with_name("placement.kicad_pcb")
    seed.write_bytes(path.read_bytes())
    b = k.LoadBoard(str(path)); b.BuildConnectivity()
    assert k.ExportSpecctraDSN(b, str(path.with_suffix(".dsn")))
    report = {"schematic_netlist_sha256": hashlib.sha256((path.parent/(domain+"-native.xml")).read_bytes()).hexdigest(),
              "placement_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "board_mm": [width,height,1], "outline_xy_mm": outline,
              "native_pads": {f.GetReference(): [{"number": p.GetNumber(), "net": p.GetNetname(), "xy_mm": coords(p.GetPosition())}
                   for p in f.Pads()] for f in b.GetFootprints()}}
    (path.parent / "placement.json").write_text(json.dumps(report,indent=2)+"\n")
    print(path.with_suffix(".dsn"), flush=True)


def import_routes(domain):
    path = board_path(domain)
    source = path.with_name("placement.kicad_pcb")
    report = json.loads((path.parent / "placement.json").read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == report["placement_sha256"]
    assert hashlib.sha256((path.parent/(domain+"-native.xml")).read_bytes()).hexdigest() == report["schematic_netlist_sha256"]
    b = k.LoadBoard(str(source))
    # The KiCad7 ImportSpecctraSES wrapper requires a GUI-owned active board.
    # Apply only native route records to the frozen headless placement instead.
    session = s.parse(path.with_suffix(".ses").read_text())
    routes = s.child(session, "routes")
    assert [a.value for a in s.child(routes, "resolution")[1:]] == ["um", "10"]
    def point(a, c):
        return k.VECTOR2I(k.FromMM(float(a.value)/10000),k.FromMM(-float(c.value)/10000))
    for net in s.children(s.child(routes, "network_out"), "net"):
        name = net[1].value
        assert b.FindNet(name), name
        for entry in net[2:]:
            if s.tag(entry) == "wire":
                p = s.child(entry, "path")
                assert p[1].value in ("F.Cu", "B.Cu")
                points = [point(a,c) for a,c in zip(p[3::2],p[4::2])]
                for a,c in zip(points,points[1:]):
                    if any(isinstance(t,k.PCB_TRACK) and t.GetNetname()==name and t.GetLayer()==(k.F_Cu if p[1].value=="F.Cu" else k.B_Cu) and
                           ((t.GetStart()==a and t.GetEnd()==c) or (t.GetStart()==c and t.GetEnd()==a)) for t in b.GetTracks()): continue
                    item = k.PCB_TRACK(b);item.SetStart(a);item.SetEnd(c)
                    item.SetWidth(k.FromMM(float(p[2].value)/10000))
                    item.SetLayer(k.F_Cu if p[1].value == "F.Cu" else k.B_Cu)
                    item.SetNet(b.FindNet(name));b.Add(item)
            elif s.tag(entry) == "via":
                dims = re.fullmatch(r"Via\[0-1\]_(\d+):(\d+)_um",entry[1].value)
                assert dims, entry[1].value
                if any(isinstance(t,k.PCB_VIA) and t.GetPosition()==point(entry[2],entry[3]) for t in b.GetTracks()):continue
                item = k.PCB_VIA(b);item.SetPosition(point(entry[2],entry[3]))
                item.SetWidth(k.FromMM(float(dims[1])/1000));item.SetDrill(k.FromMM(float(dims[2])/1000))
                item.SetViaType(k.VIATYPE_THROUGH);item.SetLayerPair(k.F_Cu,k.B_Cu)
                item.SetNet(b.FindNet(name));b.Add(item)
            else:
                raise ValueError("Unsupported route-session entry: " + s.tag(entry))
    for f in b.GetFootprints():
        # USB duplicate shell pads share a number, so compare complete multiset.
        actual = sorted((p.GetNumber(),coords(p.GetPosition())) for p in f.Pads())
        saved = sorted((p["number"],p["xy_mm"]) for p in report["native_pads"][f.GetReference()])
        assert actual == saved, (domain, f.GetReference(), "router moved placement")
    save(b,path)
    fill(domain)


def fill(domain):
    path = board_path(domain)
    b = k.LoadBoard(str(path))
    for z in list(b.Zones()): b.Delete(z)
    width,height=(28,22) if domain == "dock" else (28,10)
    stitches = [(3,3),(10,3),(23,15)] if domain == "dock" else [(6,8.5),(25.5,8.5)]
    for x,y in stitches:
        point=xy(x,y)
        if not any(isinstance(t,k.PCB_VIA) and t.GetPosition()==point for t in b.GetTracks()):
            v=k.PCB_VIA(b);v.SetPosition(point);v.SetWidth(k.FromMM(.6));v.SetDrill(k.FromMM(.3))
            v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet("GND"));b.Add(v)
    if domain == "pins" and not any(isinstance(t,k.PCB_TRACK) and t.GetStart()==xy(6,8.5) and t.GetEnd()==xy(7.5,8.5) for t in b.GetTracks()):
        t=k.PCB_TRACK(b);t.SetStart(xy(6,8.5));t.SetEnd(xy(7.5,8.5));t.SetWidth(k.FromMM(.2));t.SetLayer(k.B_Cu);t.SetNet(b.FindNet("GND"));b.Add(t)
    for layer in (k.F_Cu,k.B_Cu):
        z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet("GND"))
        z.SetLocalClearance(k.FromMM(.21));z.SetMinThickness(k.FromMM(.15))
        z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(k.FromMM(.2));z.SetThermalReliefSpokeWidth(k.FromMM(.25))
        z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        outline=z.Outline();outline.NewOutline()
        for point in ((.3,.3),(width-.3,.3),(width-.3,height-.3),(.3,height-.3)):
            p=xy(*point);outline.Append(p.x,p.y)
        b.Add(z)
    save(b,path)
    b=k.LoadBoard(str(path));b.BuildConnectivity()
    filler=k.ZONE_FILLER(b);filler.Fill(b.Zones());save(b,path)
    print(domain, len(list(b.GetFootprints())), "footprints", len(list(b.GetTracks())), "route objects",flush=True)


def mcad(domain):
    path=board_path(domain);b=k.LoadBoard(str(path))
    components=[];holes=[];tracks=[];pads=[]
    for fp in b.GetFootprints():
        points=[]
        for item in fp.GraphicalItems():
            if item.GetLayer()==k.F_Fab and isinstance(item,k.FP_SHAPE):
                box=item.GetBoundingBox()
                points += [coords(box.GetOrigin()),coords(box.GetEnd())]
        if points:
            bounds=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
            components.append({"ref":fp.GetReference(),"fab_bounds_xy_mm":bounds,
                               "height_budget_mm":3.41 if fp.GetReference()=="J91" else 1.6})
        for pad in fp.Pads():
            pads.append({"ref":fp.GetReference(),"number":pad.GetNumber(),"net":pad.GetNetname(),"xy_mm":coords(pad.GetPosition()),
                         "front":pad.GetLayerSet().Contains(k.F_Cu),"back":pad.GetLayerSet().Contains(k.B_Cu)})
            if pad.GetDrillSize().x:
                holes.append({"ref":fp.GetReference(),"number":pad.GetNumber(),"xy_mm":coords(pad.GetPosition()),
                              "drill_xy_mm":[k.ToMM(pad.GetDrillSize().x),k.ToMM(pad.GetDrillSize().y)],"angle_deg":pad.GetOrientationDegrees()})
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):
            tracks.append({"kind":"via","net":t.GetNetname(),"xy_mm":coords(t.GetPosition()),"diameter_mm":k.ToMM(t.GetWidth())})
        else:
            tracks.append({"kind":"track","net":t.GetNetname(),"start":coords(t.GetStart()),"end":coords(t.GetEnd()),
                           "width_mm":k.ToMM(t.GetWidth()),"layer":b.GetLayerName(t.GetLayer())})
    data={"board_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"board_file":str(path.relative_to(ROOT)),
          "outline_xy_mm":json.loads((path.parent/"placement.json").read_text())["outline_xy_mm"],
          "thickness_mm":k.ToMM(b.GetDesignSettings().GetBoardThickness()),"components":components,"holes":holes,"routes":tracks,"pads":pads}
    (path.parent/"mcad.json").write_text(json.dumps(data,indent=2)+"\n")
    print(path.parent/"mcad.json")


if __name__ == "__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=("place","import","fill","mcad"));ap.add_argument("domain",choices=("dock","pins"));args=ap.parse_args()
    {"place":place,"import":import_routes,"fill":fill,"mcad":mcad}[args.action](args.domain)
