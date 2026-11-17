"""Place the contact adapter, preserve the USB launch, and import routed copper."""

import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pcbnew as pcb

from build_schematic import HERE, LIBRARY, NAME, sexp

BOARD = HERE / f"{NAME}.kicad_pcb"
LIBRARIES = HERE / f"{LIBRARY}.pretty"
FRONT = pcb.F_Cu
BACK = pcb.B_Cu
GROUND = pcb.In1_Cu
INNER = pcb.In2_Cu
LAYERS = {pcb.BOARD().GetLayerName(layer): layer for layer in (FRONT, BACK, GROUND, INNER)}
OUTLINE = ((100, 100), (135, 100), (135, 126), (100, 126))
POSES = {
    "J1": (117.5, 102.675, 180), "J2": (120.5, 121, 180),
    "U1": (109.8, 109.55, 90), "U2": (109.8, 116, 90),
    "U3": (124.2, 110.1, -90), "U4": (128.4, 114.8, 180),
    "U5": (117.5, 112.3, 180), "Q1": (124.5, 115.1, 90),
    "D1": (117.5, 109, 0), "D2": (118.8, 116.1, 0),
    "R1": (125.9, 104.8, 0), "R2": (110.0, 104.7, 180),
    "R3": (106.7, 112.2, 90), "R4": (128.3, 120.05, 90),
    "R5": (131.15, 117.6, 0), "R6": (128.45, 110.1, 0),
    "R7": (121.6, 113.85, 90), "R8": (125.6, 120.6, 90),
    "C1": (108.0, 106.2, 0), "C2": (112.55, 112.9, 90),
    "C3": (110.6, 120.4, 90), "C4": (129.3, 107.5, 0),
    "C5": (132.1, 113.2, 0), "C6": (116.2, 114.9, 180), "C7": (125.0, 106.9, 0),
}
MOUNTS = ((103, 103), (132, 103), (103, 123), (132, 123))
USB_DP = "PC_DP"
USB_DM = "PC_DM"


def mm(value):
    return pcb.FromMM(value)


def point(x, y):
    return pcb.VECTOR2I(mm(x), mm(y))


def xy(q):
    return q.x / 1_000_000, q.y / 1_000_000


def path(board, net, layer, width, *vertices, locked=False):
    for a, b in zip(vertices, vertices[1:]):
        start, end = point(*a), point(*b)
        if start == end:
            continue
        track = pcb.PCB_TRACK(board)
        track.SetStart(start)
        track.SetEnd(end)
        track.SetLayer(layer)
        track.SetWidth(mm(width))
        track.SetNet(board.FindNet(net))
        track.SetLocked(locked)
        board.Add(track)


def via(board, net, at, width=0.55, drill=0.25, locked=False):
    item = pcb.PCB_VIA(board)
    item.SetPosition(point(*at))
    item.SetWidth(mm(width))
    item.SetDrill(mm(drill))
    item.SetViaType(pcb.VIATYPE_THROUGH)
    item.SetLayerPair(FRONT, BACK)
    item.SetNet(board.FindNet(net))
    item.SetLocked(locked)
    board.Add(item)


def pad_xy(board, ref, number):
    footprint = board.FindFootprintByReference(ref)
    return xy(next(pad.GetPosition() for pad in footprint.Pads() if pad.GetNumber() == number))


def connector_launch(board):
    # Preserve the same-layer flip-pin merge from the checked J110 bench
    # connector artwork. Only the via continuation changes on this board.
    def at(x, y):
        return 117.5 + x, 102.675 + y

    dp, dm = at(-0.833, 4.638), at(0.667, 4.986)
    path(board, USB_DP, FRONT, 0.20, at(0.25, 3.68), at(0.25, 2.903),
         at(-0.75, 2.903), at(-0.75, 4.556), dp, locked=True)
    path(board, USB_DM, FRONT, 0.20, at(-0.25, 3.68), at(-0.25, 4.457),
         at(0.75, 4.457), at(0.75, 3.68), locked=True)
    path(board, USB_DM, FRONT, 0.20, at(0.75, 4.457), at(0.75, 4.903), dm, locked=True)
    via(board, USB_DP, dp, locked=True)
    via(board, USB_DM, dm, locked=True)

    near_dp, near_dm = (116.57, 109.425), (118.43, 109.425)
    via(board, USB_DP, near_dp, locked=True)
    via(board, USB_DM, near_dm, locked=True)
    path(board, USB_DP, INNER, 0.20, dp, (dp[0], 109.328), near_dp, locked=True)
    path(board, USB_DM, INNER, 0.20, dm, (dm[0], 108.60), (near_dm[0], 108.863), near_dm, locked=True)

    dp1, dm1 = pad_xy(board, "D1", "1"), pad_xy(board, "D1", "2")
    dp2, dm2 = pad_xy(board, "U5", "5"), pad_xy(board, "U5", "4")
    path(board, USB_DP, FRONT, 0.17, near_dp, dp1, (dp1[0], 110.1),
         (dp2[0], 110.15), dp2, locked=True)
    path(board, USB_DM, FRONT, 0.17, near_dm, dm1, (dm1[0], 109.94),
         (dm2[0], 110.29), dm2, locked=True)

    # Keep the two branches adjacent from the switch, then fan out to the
    # fixed 2 mm single-row PH. No second host branch or second mux input.
    contact_dp = pad_xy(board, "U5", "1")
    contact_dm = pad_xy(board, "U5", "2")
    dp_clamp = pad_xy(board, "D2", "1")
    dm_clamp = pad_xy(board, "D2", "2")
    path(board, "CONTACT_DP", FRONT, 0.17, contact_dp, (118.25, 112.5),
         (118.25, 115.67), (118.45, 115.87), dp_clamp, locked=True)
    path(board, "CONTACT_DM", FRONT, 0.17, contact_dm, (118.9, 112.1),
         (119.35, 112.55), (119.35, 115.8), (119.15, 116.0), dm_clamp, locked=True)
    path(board, "CONTACT_DP", FRONT, 0.20, dp_clamp, (118.45, 117.95),
         (116.5, 119.90), pad_xy(board, "J2", "3"), locked=True)
    path(board, "CONTACT_DM", FRONT, 0.20, dm_clamp, (119.15, 120.35),
         pad_xy(board, "J2", "2"), locked=True)


def local_ground(board):
    # Short return paths into the unbroken reference plane under the pair.
    returns = {
        ("D1", "3"): ((117.5, 107.84),),
        ("D2", "3"): ((118.8, 115.1),),
        ("U5", "3"): ((117.9, 111.30), (118.35, 110.85)),
    }
    for (ref, pin), vertices in returns.items():
        path(board, "GND", FRONT, 0.15, pad_xy(board, ref, pin), *vertices, locked=True)
        via(board, "GND", vertices[-1], locked=True)


def add_ground_plane(board):
    zone = pcb.ZONE(board)
    zone.SetLayer(GROUND)
    zone.SetNet(board.FindNet("GND"))
    zone.SetLocalClearance(mm(0.20))
    zone.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(mm(0.15))
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in OUTLINE:
        outline.Append(mm(x), mm(y))
    board.Add(zone)


def silk(board, string, loc, height=0.9, layer=pcb.F_SilkS):
    item = pcb.PCB_TEXT(board)
    item.SetText(string)
    item.SetPosition(point(*loc))
    item.SetTextSize(point(height, height))
    item.SetTextThickness(mm(0.12))
    item.SetLayer(layer)
    if layer == pcb.B_SilkS:
        item.SetMirrored(True)
    board.Add(item)


def add_footprint(board, comp, pins):
    ref = comp.get("ref")
    _, name = comp.findtext("footprint").split(":")
    footprint = pcb.FootprintLoad(str(LIBRARIES), name)
    footprint.SetFPID(pcb.LIB_ID(LIBRARY, name))
    footprint.SetReference(ref)
    footprint.SetValue(comp.findtext("value"))
    footprint.SetPath(pcb.KIID_PATH(comp.find("sheetpath").get("tstamps") + comp.findtext("tstamps")))
    for field in comp.findall("./fields/field"):
        if field.text:
            footprint.SetProperty(field.get("name"), field.text)
    for field in ("datasheet", "description"):
        value = comp.findtext(field)
        if value:
            footprint.SetProperty(field.capitalize(), value)
    x, y, angle = POSES[ref]
    footprint.SetOrientationDegrees(angle)
    footprint.SetPosition(point(x, y))
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    board.Add(footprint)
    for pad in footprint.Pads():
        name = pins.get((ref, pad.GetNumber()))
        if name:
            pad.SetNet(board.FindNet(name))
    expected = {pin for comp_ref, pin in pins if comp_ref == ref}
    assert expected <= {pad.GetNumber() for pad in footprint.Pads()}, ref


def make_board(netlist):
    board = pcb.BOARD()
    board.SetCopperLayerCount(4)
    settings = board.GetDesignSettings()
    settings.SetBoardThickness(mm(1.6))
    settings.m_MinClearance = mm(0.10)
    settings.m_TrackMinWidth = mm(0.15)
    settings.m_CopperEdgeClearance = mm(0.25)
    settings.m_HoleClearance = mm(0.15)
    settings.m_MinThroughDrill = mm(0.20)
    settings.m_ViasMinSize = mm(0.50)
    default = settings.m_NetSettings.m_DefaultNetClass
    default.SetClearance(mm(0.10))
    default.SetTrackWidth(mm(0.20))
    default.SetViaDiameter(mm(0.55))
    default.SetViaDrill(mm(0.25))
    settings.SetAuxOrigin(point(*OUTLINE[0]))
    for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        edge = pcb.PCB_SHAPE(board)
        edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(point(*a))
        edge.SetEnd(point(*b))
        edge.SetWidth(mm(0.05))
        edge.SetLayer(pcb.Edge_Cuts)
        board.Add(edge)

    source = ET.parse(netlist)
    pins = {}
    for net in source.findall("./nets/net"):
        name = net.get("name")
        board.Add(pcb.NETINFO_ITEM(board, name))
        for node in net.findall("node"):
            pins[(node.get("ref"), node.get("pin"))] = name
    for comp in source.findall("./components/comp"):
        if comp.findtext("footprint"):
            add_footprint(board, comp, pins)
    for index, (x, y) in enumerate(MOUNTS, 1):
        name = "MountingHole_2.2mm_M2"
        mount = pcb.FootprintLoad(str(LIBRARIES), name)
        mount.SetFPID(pcb.LIB_ID(LIBRARY, name))
        mount.SetReference(f"H{index}")
        mount.SetValue("M2")
        mount.SetPosition(point(x, y))
        mount.SetAttributes(mount.GetAttributes() | pcb.FP_BOARD_ONLY | pcb.FP_EXCLUDE_FROM_BOM |
                            pcb.FP_EXCLUDE_FROM_POS_FILES)
        mount.Reference().SetVisible(False)
        mount.Value().SetVisible(False)
        board.Add(mount)
    silk(board, "PC USB-C", (108.2, 101.6), 1.0)
    silk(board, "COMPASS", (105.4, 115.1), 0.85)
    silk(board, "DIRECT PC", (105.4, 116.5), 0.8)
    silk(board, "EVT1-EA1", (105.4, 117.9), 0.8)
    silk(board, "5V   D+   D-   G", (117.65, 124.1), 0.85)
    silk(board, "J94", (126.0, 123.4), 0.85)
    silk(board, "BENCH EVALUATION", (117.5, 124.25), 1.0, pcb.B_SilkS)
    silk(board, "J2: 1 GND  2 D-  3 D+  4 5V", (117.5, 118.95), 0.9, pcb.B_SilkS)
    connector_launch(board)
    add_ground_plane(board)
    local_ground(board)
    return board


def export_dsn(board, destination):
    if not pcb.ExportSpecctraDSN(board, str(destination)):
        raise RuntimeError("Could not export board for routing")
    exchange = destination.read_text()
    exchange = re.sub(r"(\(layer In1\.Cu\s+\(type )signal", r"\1power", exchange)
    layer_rules = "\n    (autoroute_settings (autoroute on) (postroute off) (vias on) " \
                  "(layer_rule F.Cu (active on) (preferred_direction vertical)) " \
                  "(layer_rule In1.Cu (active off) (preferred_direction horizontal)) " \
                  "(layer_rule In2.Cu (active on) (preferred_direction horizontal)) " \
                  "(layer_rule B.Cu (active on) (preferred_direction vertical)))"
    insert = exchange.index("\n    (boundary")
    destination.write_text(exchange[:insert] + layer_rules + exchange[insert:])


def import_ses(board, session):
    def track_key(net, layer, width, a, b):
        return net, layer, width, tuple(sorted((a, b)))

    tracks = set()
    vias = set()
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA):
            vias.add((item.GetNetname(), tuple(round(v, 4) for v in xy(item.GetPosition()))))
        else:
            a = tuple(round(v, 4) for v in xy(item.GetStart()))
            b = tuple(round(v, 4) for v in xy(item.GetEnd()))
            tracks.add(track_key(item.GetNetname(), item.GetLayer(), item.GetWidth(), a, b))
    routes = sexp.child(sexp.parse(session.read_text()), "routes")
    resolution = sexp.child(routes, "resolution")
    assert resolution[1].value == "um"
    units = 1000 * float(resolution[2].value)

    def session_xy(x, y):
        return round(float(x.value) / units, 4), round(-float(y.value) / units, 4)

    for item in sexp.children(sexp.child(routes, "network_out"), "net"):
        net = item[1].value
        for wire in sexp.children(item, "wire"):
            record = sexp.child(wire, "path")
            layer = LAYERS[record[1].value]
            width = max(0.15, float(record[2].value) / units)
            vertices = [session_xy(x, y) for x, y in zip(record[3::2], record[4::2])]
            for a, b in zip(vertices, vertices[1:]):
                key = track_key(net, layer, mm(width), a, b)
                if key not in tracks:
                    path(board, net, layer, width, a, b)
                    tracks.add(key)
        for record in sexp.children(item, "via"):
            dims = re.fullmatch(r"Via\[\d+-\d+\]_(\d+):(\d+)_um", record[1].value)
            assert dims, record[1].value
            at = session_xy(*record[2:4])
            if (net, at) not in vias:
                via(board, net, at, *(float(v) / 1000 for v in dims.groups()))
                vias.add((net, at))


def finish_routing(board):
    """Close the remaining supply, monitor, and ground connections."""
    # The router ran the contact rail across the U2 ground escape. Preserve
    # that branch junction and move the rail south for a plane via at pin 2.
    old = {
        ((108.748, 117.3658), (108.8591, 117.4769)),
        ((108.8591, 117.4769), (109.8895, 117.4769)),
        ((109.8895, 117.4769), (109.8895, 120.4645)),
        ((109.8895, 117.4769), (110.45, 117.4769)),
    }
    for track in list(board.GetTracks()):
        if isinstance(track, pcb.PCB_VIA) or track.GetLayer() != FRONT or track.GetNetname() != "CONTACT_5V":
            continue
        key = tuple(sorted(tuple(round(v, 4) for v in xy(at)) for at in (track.GetStart(), track.GetEnd())))
        if key in old:
            board.Remove(track)
            old.remove(key)
    assert not old, old
    path(board, "CONTACT_5V", FRONT, 0.20, (108.748, 117.3658), (108.748, 117.9345),
         (109.114, 118.3005), (109.8895, 118.3005), (109.8895, 120.4645))
    path(board, "CONTACT_5V", FRONT, 0.20, (110.45, 117.4769), (110.45, 117.74), (109.8895, 118.3005))

    returns = {
        ("R3", "2"): (106.7, 110.6),
        ("U2", "2"): (109.8, 117.62),
    }
    for (ref, pin), at in returns.items():
        path(board, "GND", FRONT, 0.20, pad_xy(board, ref, pin), at)
        via(board, "GND", at)
    path(board, "GND", FRONT, 0.20, (108.349, 109.3), (108.149, 109.1), (108.08, 109.1))
    for at in ((108.08, 109.1), (113.23, 111.445), (125.775, 105.8), (125.45, 118.4)):
        via(board, "GND", at)

    vbus_valid = ((128.4, 115.301), (123.55, 117.18))
    for at in vbus_valid:
        via(board, "VBUS_VALID", at)
    path(board, "VBUS_VALID", BACK, 0.20, vbus_valid[0], (128.4, 117.0), (128.22, 117.18), vbus_valid[1])
    path(board, "VBUS_VALID", FRONT, 0.20, vbus_valid[1], pad_xy(board, "Q1", "1"))

    logic = ((127.625, 110.78), (127.2625, 116.55))
    for at in logic:
        via(board, "ADAPTER_3V3", at)
    path(board, "ADAPTER_3V3", FRONT, 0.20, pad_xy(board, "R6", "1"), logic[0])
    path(board, "ADAPTER_3V3", FRONT, 0.20, pad_xy(board, "U4", "6"), logic[1])
    path(board, "ADAPTER_3V3", INNER, 0.20, logic[0], (127.625, 112.14), (127.2625, 112.5025), logic[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", type=Path, required=True)
    tasks = parser.add_mutually_exclusive_group(required=True)
    tasks.add_argument("--export-dsn", type=Path)
    tasks.add_argument("--import-ses", type=Path)
    parser.add_argument("--finish", action="store_true", help="apply native geometry repairs for the checked routing session")
    opts = parser.parse_args()
    if opts.finish and not opts.import_ses:
        parser.error("--finish requires --import-ses")
    board = make_board(opts.netlist)
    if opts.export_dsn:
        export_dsn(board, opts.export_dsn)
    else:
        import_ses(board, opts.import_ses)
        if opts.finish:
            finish_routing(board)
        pcb.SaveBoard(str(BOARD), board)


if __name__ == "__main__":
    main()
