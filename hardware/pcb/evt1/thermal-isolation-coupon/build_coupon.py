"""Build the standalone comparison coupon with KiCad's pcbnew Python."""
from pathlib import Path
from math import sqrt
import json
import sys

import pcbnew as k

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = HERE.parent / "single-flange-routing"
NAME = "thermal-isolation-coupon"
BOARD = HERE / f"{NAME}.kicad_pcb"
PROJECT = HERE / f"{NAME}.kicad_pro"
LIB = HERE / "ThermalCoupon.pretty"
sys.path.insert(0, str(REPO / "tools"))
import kicad_sexp as sexp

# All positions are in mm. The layout is viewed through the front of the board.
def xy(p):
    return k.VECTOR2I(k.FromMM(p[0]), k.FromMM(p[1]))


def line(board, layer, start, end, width=0.05):
    item = k.PCB_SHAPE(board)
    item.SetShape(k.SHAPE_T_SEGMENT)
    item.SetStart(xy(start))
    item.SetEnd(xy(end))
    item.SetWidth(k.FromMM(width))
    item.SetLayer(layer)
    board.Add(item)


def arc(board, start, mid, end):
    item = k.PCB_SHAPE(board)
    item.SetShape(k.SHAPE_T_ARC)
    item.SetArcGeometry(xy(start), xy(mid), xy(end))
    item.SetWidth(k.FromMM(0.05))
    item.SetLayer(k.Edge_Cuts)
    board.Add(item)


def route_outline(board, vertices, radius):
    """Round each right angle with a tangent arc and connect successive arcs."""
    corners = []
    for index, vertex in enumerate(vertices):
        a, b = vertices[index - 1], vertices[(index + 1) % len(vertices)]
        ux = 0 if a[0] == vertex[0] else (1 if a[0] > vertex[0] else -1)
        uy = 0 if a[1] == vertex[1] else (1 if a[1] > vertex[1] else -1)
        vx = 0 if b[0] == vertex[0] else (1 if b[0] > vertex[0] else -1)
        vy = 0 if b[1] == vertex[1] else (1 if b[1] > vertex[1] else -1)
        assert abs(ux) + abs(uy) == abs(vx) + abs(vy) == 1
        assert ux * vx + uy * vy == 0
        x, y = vertex
        incoming, outgoing = (x + radius * ux, y + radius * uy), (x + radius * vx, y + radius * vy)
        diag = radius * (1 - 1 / sqrt(2))
        middle = (x + diag * (ux + vx), y + diag * (uy + vy))
        corners.append((incoming, middle, outgoing))
    for index, (a, m, b) in enumerate(corners):
        prev = corners[index - 1][2]
        if prev != a:
            line(board, k.Edge_Cuts, prev, a)
        arc(board, a, m, b)


def pad(board, footprint, number, pos, size, net, shape=k.PAD_SHAPE_RECT, paste=False):
    p = k.PAD(footprint)
    p.SetNumber(str(number))
    p.SetShape(shape)
    p.SetAttribute(k.PAD_ATTRIB_SMD)
    p.SetSize(xy(size))
    p.SetPos0(xy(pos) - footprint.GetPosition())
    p.SetPosition(xy(pos))
    layers = k.LSET()
    for layer in (k.B_Cu, k.B_Mask, k.B_Paste) if paste else (k.B_Cu, k.B_Mask):
        layers.AddLayer(layer)
    p.SetLayerSet(layers)
    if net:
        p.SetNet(net)
    footprint.Add(p)


def footprint(board, ref, val, pos, name, courtyard_mm, attr=k.FP_SMD):
    f = k.FOOTPRINT(board)
    f.SetReference(ref)
    f.SetValue(val)
    f.SetFPID(k.LIB_ID("ThermalCoupon", name))
    f.SetLayer(k.B_Cu)
    f.SetPosition(xy(pos))
    f.SetAttributes(attr)
    f.Reference().SetVisible(False)
    f.Value().SetVisible(False)
    x, y = courtyard_mm[0] / 2, courtyard_mm[1] / 2
    box = [(-x, -y), (x, -y), (x, y), (-x, y)]
    for index, end in enumerate(box):
        start = box[index - 1]
        edge = k.FP_SHAPE(f)
        edge.SetShape(k.SHAPE_T_SEGMENT)
        edge.SetStart0(xy(start))
        edge.SetEnd0(xy(end))
        edge.SetStart(xy(start) + f.GetPosition())
        edge.SetEnd(xy(end) + f.GetPosition())
        edge.SetWidth(k.FromMM(0.05))
        edge.SetLayer(k.B_CrtYd)
        f.Add(edge)
    board.Add(f)
    return f


def sensor(board, number, x, nets):
    pos = (x, 11.5)
    f = footprint(board, f"TH{number}", "NTCS0402E3103FL1T", pos, "Vishay_NTCS0402_Reflow", (1.9, 1.0))
    t = footprint(board, f"J{number}", "Two isolated solder tabs", (x, 27), "Dual_Wire_0p9x1p6", (2.9, 2.1),
                  k.FP_SMD | k.FP_EXCLUDE_FROM_POS_FILES | k.FP_EXCLUDE_FROM_BOM)
    for pin, factor, net in zip((1, 2), (-1, 1), nets):
        # Vishay NTCS0402 reflow dimensions are 0.50 mm gap,
        # 0.50 x 0.60 mm lands, and 1.50 mm overall length.
        contact = (x + 0.50 * factor, 11.5)
        a = (x + 0.50 * factor, 12.4)
        b = (x + 0.22 * factor, 12.68)
        c = (x + 0.22 * factor, 24.0)
        d = (x + 0.75 * factor, 24.53)
        terminal = (x + 0.75 * factor, 27)
        pad(board, f, pin, contact, (0.50, 0.60), net, paste=True)
        pad(board, t, pin, terminal, (0.9, 1.6), net)
        for start, end in zip((contact, a, b, c, d), (a, b, c, d, terminal)):
            track = k.PCB_TRACK(board)
            track.SetLayer(k.B_Cu)
            track.SetStart(xy(start))
            track.SetEnd(xy(end))
            track.SetWidth(k.FromMM(0.15))
            track.SetNet(net)
            board.Add(track)


def zone(board, layer, vertices, net=None):
    z = k.ZONE(board)
    z.SetLayer(layer)
    if net:
        z.SetNet(net)
        z.SetLocalClearance(k.FromMM(0.2))
        z.SetMinThickness(k.FromMM(0.15))
        z.SetPadConnection(k.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
    else:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetDoNotAllowVias(True)
    p = z.Outline()
    p.NewOutline()
    for coord in vertices:
        v = xy(coord)
        p.Append(v.x, v.y)
    board.Add(z)


def silk(board, text, pos, layer=k.F_SilkS, size=1.1):
    label = k.PCB_TEXT(board)
    label.SetLayer(layer)
    label.SetText(text)
    label.SetTextSize(xy((size, size)))
    label.SetTextThickness(k.FromMM(0.16))
    label.SetPosition(xy(pos))
    label.SetMirrored(layer == k.B_SilkS)
    board.Add(label)


def fixture_hole(board, ref, pos):
    f = footprint(board, ref, "2.2 mm fixture hole", pos, "MountingHole_2p2mm", (2.7, 2.7),
                  k.FP_THROUGH_HOLE | k.FP_EXCLUDE_FROM_POS_FILES | k.FP_EXCLUDE_FROM_BOM)
    p = k.PAD(f)
    p.SetShape(k.PAD_SHAPE_CIRCLE)
    p.SetAttribute(k.PAD_ATTRIB_NPTH)
    p.SetSize(xy((2.2, 2.2)))
    p.SetDrillSize(xy((2.2, 2.2)))
    p.SetLayerSet(k.PAD.PTHMask())
    p.SetPos0(xy((0, 0)))
    p.SetPosition(xy(pos))
    f.Add(p)


def main():
    config = json.loads((BASE / "single-flange.kicad_pro").read_text())
    config["meta"]["filename"] = PROJECT.name
    constraints = config["board"]["design_settings"]["rules"]
    constraints.update(min_copper_edge_clearance=0.25, min_clearance=0.15, min_track_width=0.15)
    config["board"]["design_settings"]["drc_exclusions"] = []
    config["board"]["design_settings"]["rule_severities"].update(lib_footprint_issues="warning",
                                                                lib_footprint_mismatch="warning")
    config["net_settings"]["classes"][0].update(clearance=0.15, track_width=0.15)
    project_text = json.dumps(config, indent=2) + "\n"
    b = k.BOARD()
    b.SetCopperLayerCount(4)
    b.GetDesignSettings().SetBoardThickness(k.FromMM(1))
    frame = [(0, 0), (48, 0), (48, 30), (0, 30)]
    route_outline(b, frame, 1.0)
    route_outline(b, [
        (35.4, 23.5), (35.4, 15.5), (32.4, 15.5), (32.4, 7.5),
        (39.6, 7.5), (39.6, 15.5), (36.6, 15.5), (36.6, 23.5),
        (37.8, 23.5), (37.8, 16.7), (40.8, 16.7), (40.8, 6.3),
        (31.2, 6.3), (31.2, 16.7), (34.2, 16.7), (34.2, 23.5),
    ], 0.5)
    nets = {}
    for net_name in ("GND", "A_SENSE", "A_RETURN", "B_SENSE", "B_RETURN"):
        nets[net_name] = k.NETINFO_ITEM(b, net_name)
        b.Add(nets[net_name])
    for number, label, x in ((901, "A", 12), (902, "B", 36)):
        sensor(b, number, x, (nets[f"{label}_SENSE"], nets[f"{label}_RETURN"]))
        silk(b, f"{label}  " + ("KEEPOUT" if label == "A" else "ROUTED"), (x, 4.25))
        silk(b, f"{label}  " + ("KEEPOUT" if label == "A" else "ROUTED"), (x, 4.25), k.B_SilkS)
        silk(b, "1", (x - 0.75, 28.8), k.B_SilkS, 0.90)
        silk(b, "2", (x + 0.75, 28.8), k.B_SilkS, 0.90)
        for layer in (k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu):
            zone(b, layer, [(x - 5.2, 5.8), (x + 5.2, 5.8), (x + 5.2, 24.3),
                            (x - 5.2, 24.3)], None)
    silk(b, "COMPASS EVT THERMAL COUPON", (24, 1.9))
    fixture_hole(b, "H901", (3., 27.))
    fixture_hole(b, "H902", (45., 27.))
    p = footprint(b, "TP901", "Plane anchor", (24, 27), "Plane_Anchor", (1.5, 1.5),
                  k.FP_SMD | k.FP_EXCLUDE_FROM_POS_FILES | k.FP_EXCLUDE_FROM_BOM)
    pad(b, p, 1, (24, 27), (1.0, 1.0), nets["GND"])
    via = k.PCB_VIA(b)
    via.SetPosition(xy((24, 27)))
    via.SetWidth(k.FromMM(0.55))
    via.SetDrill(k.FromMM(0.30))
    via.SetViaType(k.VIATYPE_THROUGH)
    via.SetLayerPair(k.F_Cu, k.B_Cu)
    via.SetNet(nets["GND"])
    b.Add(via)
    for layer in (k.In1_Cu, k.In2_Cu, k.B_Cu):
        zone(b, layer, frame, nets["GND"])
    LIB.mkdir(exist_ok=True)
    used_names = set()
    for f in b.GetFootprints():
        name = str(f.GetFPID().GetLibItemName())
        if name not in used_names:
            k.FootprintSave(str(LIB), f)
            used_names.add(name)
    k.SaveBoard(str(BOARD), b)
    PROJECT.write_text(project_text)

    # Copy the real flange stack description, then refill using the coupon's
    # project settings. This keeps the board-to-copper comparison controlled.
    board_tree = sexp.parse(BOARD.read_text())
    stackup = sexp.child(sexp.child(sexp.parse((BASE / "single-flange.kicad_pcb").read_text()), "setup"), "stackup")
    setup = sexp.child(board_tree, "setup")
    old = sexp.child(setup, "stackup")
    if old:
        setup.remove(old)
    setup.insert(1, stackup)
    sexp.write(BOARD, board_tree)
    del b
    board = k.LoadBoard(str(BOARD))
    board.BuildConnectivity()
    assert k.ZONE_FILLER(board).Fill(board.Zones()), "zone fill failed"
    k.SaveBoard(str(BOARD), board)
    PROJECT.write_text(project_text)



if __name__ == "__main__":
    main()
