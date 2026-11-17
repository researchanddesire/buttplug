"""Place the bench variant and preserve compatible local EVT copper."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import wx
APP = wx.App(False)
import pcbnew as pcb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import kicad_sexp as sexp

NAME = "compass-one-board-dev"
BOARD = HERE / (NAME + ".kicad_pcb")
DSN = HERE / (NAME + ".dsn")
XML = HERE / (NAME + "-native.xml")
SOURCES = [
    (HERE.parent / "single-flange-routing" / "single-flange.kicad_pcb", (0, 0), {pcb.In1_Cu: pcb.In2_Cu, pcb.In2_Cu: pcb.In3_Cu}),
    (HERE.parent / "body" / "body-evt1.kicad_pcb", (0, 35), {}),
]
OUTLINE = [(54, 71), (100, 71), (100, 70.5), (121, 70.5), (121, 71),
           (163, 71), (163, 151), (54, 151), (54, 109), (62, 109),
           (62, 91), (54, 91)]
# Remove laminate in the module's antenna region and keep its other approach
# bounds clear on every layer. Preserve the approved module clocking.
RF_KEEP_OUT = [(54, 89), (62.0, 89), (62.0, 111), (54, 111)]
BENCH_POSES = {
    "J110": (110.5, 74.25, 180), "R101": (108.5, 80.5, 0), "R102": (112.7, 80.5, 0),
    "J111": (132, 78, 0), "J112": (118.3, 83.54, 0),
    "J120": (115, 127, 90), "J121": (115, 115, 90), "J122": (82, 116, 0),
    "J124": (78, 135, 90), "J125": (131, 122, 0),
    "J8": (86, 126, -90), "R88": (86, 132, 0), "C88": (86, 130, 0),
}
TP_POSES = {
    i: (138 + 9 * ((i - 101) % 3), 91 + 8 * ((i - 101) // 3), 0)
    for i in range(101, 122)
}
MOUNTS = [(60, 77), (157, 77), (157, 145), (60, 145)]
# These were already routed locally in the active dedicated boards. Transfer
# only when the native endpoint sets agree after the integration.
LOCAL_NETS = {
    "CHG_ILIM", "CHG_ISET", "SYS", "TIP_NTC", "TIP_EXC_HALF", "PACK_NTC",
    "PACK_GUARD", "DOCK_FUSED", "MOTOR_P", "MOTOR_N", "MOTOR_IN1",
    "MCU_EN", "BOOT_N", "USB_DM", "USB_DP",
    "REG1_AUX", "REG1_FB", "REG1_L1", "REG1_L2", "REG1_PS",
    "REG2_AUX", "REG2_FB", "REG2_L1", "REG2_L2", "REG2_PS",
}
CRITICAL_LAYERS = {"F.Cu": pcb.F_Cu, "B.Cu": pcb.B_Cu, "In1.Cu": pcb.In1_Cu,
                   "In2.Cu": pcb.In2_Cu, "In3.Cu": pcb.In3_Cu, "In4.Cu": pcb.In4_Cu}


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def load_netlist():
    source = ET.parse(XML)
    parts = {part.get("ref"): part for part in source.findall("./components/comp")
             if part.findtext("footprint") and not part.get("ref").startswith("#")}
    pins = {(pin.get("ref"), pin.get("pin")): net.get("name")
            for net in source.findall("./nets/net") for pin in net.findall("node")
            if pin.get("ref") in parts}
    return parts, pins


def libraries():
    table = sexp.parse((HERE / "fp-lib-table").read_text())
    return {sexp.value(lib, "name"): (HERE / sexp.value(lib, "uri").removeprefix("${KIPRJMOD}/")).resolve()
            for lib in sexp.children(table, "lib")}


def source_data():
    output = []
    for path, offset, layers in SOURCES:
        board = pcb.LoadBoard(str(path))
        fo = {}
        contacts = defaultdict(set)
        offset_p = point(*offset)
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            fo[ref] = (fp.GetPosition() + offset_p, fp.GetOrientationDegrees(), fp.GetLayer(), str(fp.GetFPID().GetLibItemName()))
            for pad in fp.Pads():
                if pad.GetNetname():
                    contacts[pad.GetNetname()].add((ref, pad.GetNumber()))
        wires = []
        for track in board.GetTracks():
            net = track.GetNetname()
            if net not in LOCAL_NETS:
                continue
            layer = layers.get(track.GetLayer(), track.GetLayer())
            if isinstance(track, pcb.PCB_VIA):
                wires.append((net, "via", track.GetPosition() + offset_p, track.GetWidth(), track.GetDrillValue()))
            elif isinstance(track, pcb.PCB_TRACK) and not isinstance(track, pcb.PCB_ARC):
                wires.append((net, "segment", track.GetStart() + offset_p, track.GetEnd() + offset_p,
                              track.GetWidth(), layer))
        output.append((fo, dict(contacts), wires))
    return output


def add_outline(board):
    for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        edge = pcb.PCB_SHAPE(board)
        edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(point(*a))
        edge.SetEnd(point(*b))
        edge.SetWidth(pcb.FromMM(.05))
        edge.SetLayer(pcb.Edge_Cuts)
        board.Add(edge)


def add_zone(board, area, layer, net=None):
    zone = pcb.ZONE(board)
    zone.SetLayer(layer)
    if net is None:
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowCopperPour(True)
        zone.SetDoNotAllowFootprints(False)
    else:
        zone.SetNet(board.FindNet(net))
        zone.SetLocalClearance(pcb.FromMM(.20))
        zone.SetPadConnection(pcb.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(pcb.FromMM(.20))
        zone.SetThermalReliefSpokeWidth(pcb.FromMM(.22))
        zone.SetMinThickness(pcb.FromMM(.15))
    polygon = zone.Outline()
    polygon.NewOutline()
    for q in area:
        p = point(*q)
        polygon.Append(p.x, p.y)
    board.Add(zone)
    return zone


def add_mount_plane_keepouts(board):
    existing = {zone.GetZoneName() for zone in board.Zones()}
    for i, (x, y) in enumerate(MOUNTS, start=1):
        area = [(x - 1.95, y - 1.95), (x + 1.95, y - 1.95),
                (x + 1.95, y + 1.95), (x - 1.95, y + 1.95)]
        for layer in (pcb.F_Cu, pcb.In2_Cu, pcb.In4_Cu, pcb.B_Cu):
            name = f"Mount H{i} plane relief {board.GetLayerName(layer)}"
            if name in existing:
                continue
            zone = add_zone(board, area, layer)
            zone.SetZoneName(name)


def add_outer_ground_zones(board):
    existing = {zone.GetZoneName() for zone in board.Zones()}
    for layer in (pcb.F_Cu, pcb.B_Cu):
        name = f"Ground stitching {board.GetLayerName(layer)}"
        if name in existing:
            continue
        zone = add_zone(board, OUTLINE, layer, "GND")
        zone.SetZoneName(name)
        zone.SetPadConnection(pcb.ZONE_CONNECTION_THT_THERMAL)


def set_settings(board):
    settings = board.GetDesignSettings()
    settings.SetBoardThickness(pcb.FromMM(1.6))
    settings.m_MinClearance = pcb.FromMM(.10)
    settings.m_TrackMinWidth = pcb.FromMM(.15)
    settings.m_CopperEdgeClearance = pcb.FromMM(.25)
    settings.m_HoleClearance = pcb.FromMM(.15)
    settings.m_MinThroughDrill = pcb.FromMM(.20)
    settings.m_ViasMinSize = pcb.FromMM(.5)
    default = settings.m_NetSettings.m_DefaultNetClass
    default.SetClearance(pcb.FromMM(.10))
    default.SetTrackWidth(pcb.FromMM(.20))
    default.SetViaDiameter(pcb.FromMM(.55))
    default.SetViaDrill(pcb.FromMM(.25))


def add_footprint(board, library, comp, pins, positions):
    ref = comp.get("ref")
    identifier = comp.findtext("footprint")
    alias, name = identifier.split(":")
    fp = pcb.FootprintLoad(str(library[alias]), name)
    assert fp, (ref, identifier)
    fp.SetReference(ref)
    set_symbol_metadata(fp, comp)
    fp.SetFPID(pcb.LIB_ID(alias, name))
    fp.SetPath(pcb.KIID_PATH(comp.find("sheetpath").get("tstamps") + comp.findtext("tstamps")))
    board.Add(fp)
    loc, angle, side, _ = positions[ref]
    if side == pcb.B_Cu:
        fp.Flip(fp.GetPosition(), True)
    fp.SetOrientationDegrees(angle)
    fp.SetPosition(loc)
    fp.SetLocked(True)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    actual = set()
    for pad in fp.Pads():
        number = pad.GetNumber()
        net = pins.get((ref, number))
        if net:
            pad.SetNet(board.FindNet(net))
        else:
            pad.SetNetCode(0)
        if number:
            actual.add(number)
    assert {k[1] for k in pins if k[0] == ref} <= actual, (ref, actual)
    return fp


def set_symbol_metadata(footprint, component):
    footprint.SetValue(component.findtext("value"))
    if component.find("property[@name='exclude_from_bom']") is not None:
        footprint.SetAttributes(
            footprint.GetAttributes() | pcb.FP_EXCLUDE_FROM_BOM | pcb.FP_EXCLUDE_FROM_POS_FILES
        )
    for entry in component.findall("./property"):
        name = entry.get("name")
        if name not in {"Sheetname", "Sheetfile", "ki_description", "exclude_from_bom", "dnp"}:
            footprint.SetProperty(name, entry.get("value", ""))
    for entry in component.findall("./fields/field"):
        if entry.text:
            footprint.SetProperty(entry.get("name"), entry.text)
    datasheet = component.findtext("datasheet")
    if datasheet:
        footprint.SetProperty("Datasheet", datasheet)


def sync_symbol_metadata():
    parts, _ = load_netlist()
    board = pcb.LoadBoard(str(BOARD))
    for footprint in board.GetFootprints():
        component = parts.get(footprint.GetReference())
        if component is not None:
            set_symbol_metadata(footprint, component)
    add_mount_plane_keepouts(board)
    add_outer_ground_zones(board)
    for track in board.GetTracks():
        if not isinstance(track, pcb.PCB_VIA) and not track.IsLocked() and track.GetWidth() < pcb.FromMM(.15):
            track.SetWidth(pcb.FromMM(.15))
    pcb.SaveBoard(str(BOARD), board)
    board = pcb.LoadBoard(str(BOARD))
    board.BuildConnectivity()
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    pcb.SaveBoard(str(BOARD), board)
    report = json.loads((HERE / "placement.json").read_text())
    report["source_netlist_sha256"] = hashlib.sha256(XML.read_bytes()).hexdigest()
    (HERE / "placement.json").write_text(json.dumps(report, indent=2) + "\n")


def add_mount(board, library, i, x, y):
    name = "MountingHole_3.2mm_M3"
    fp = pcb.FootprintLoad(str(library["DevBench"]), name)
    assert fp is not None
    fp.SetFPID(pcb.LIB_ID("DevBench", name))
    fp.SetPosition(point(x, y))
    fp.SetReference(f"H{i}")
    fp.SetValue(name)
    fp.SetAttributes(pcb.FP_BOARD_ONLY | pcb.FP_EXCLUDE_FROM_BOM | pcb.FP_EXCLUDE_FROM_POS_FILES)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    board.Add(fp)


def add_silk(board, value, x, y, size=1.0):
    text = pcb.PCB_TEXT(board)
    text.SetLayer(pcb.F_SilkS)
    text.SetText(value)
    text.SetPosition(point(x, y))
    text.SetTextSize(point(size, size))
    text.SetTextThickness(pcb.FromMM(.16))
    board.Add(text)


def preserve_routes(board, pins, datasets):
    counts = defaultdict(int)
    for _, endpoints, wires in datasets:
        for net, kind, *geometry in wires:
            new_names = {pins.get(pin) for pin in endpoints[net]}
            if len(new_names) != 1 or None in new_names:
                continue
            new_net = new_names.pop()
            if new_net == "unconnected-":
                continue
            if kind == "via":
                position, diameter, drill = geometry
                item = pcb.PCB_VIA(board)
                item.SetPosition(position)
                item.SetWidth(diameter)
                item.SetDrill(drill)
                item.SetViaType(pcb.VIATYPE_THROUGH)
                item.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
            else:
                start, end, width, layer = geometry
                item = pcb.PCB_TRACK(board)
                item.SetStart(start)
                item.SetEnd(end)
                item.SetWidth(width)
                item.SetLayer(layer)
            item.SetNet(board.FindNet(new_net))
            item.SetLocked(True)
            board.Add(item)
            counts[new_net] += 1
    return counts


def place():
    parts, pins = load_netlist()
    library = libraries()
    datasets = source_data()
    positions = {}
    for source, _, _ in datasets:
        positions.update(source)
    for ref, (x, y, angle) in {**BENCH_POSES, **{f"TP{i}": pose for i, pose in TP_POSES.items()}}.items():
        positions[ref] = (point(x, y), angle, pcb.F_Cu, None)
    assert set(parts) <= set(positions), set(parts) - set(positions)
    board = pcb.BOARD()
    board.SetFileName(str(BOARD))
    board.SetCopperLayerCount(6)
    set_settings(board)
    for net in sorted(set(pins.values())):
        board.Add(pcb.NETINFO_ITEM(board, net))
    add_outline(board)
    for ref, comp in parts.items():
        add_footprint(board, library, comp, pins, positions)
    for i, (x, y) in enumerate(MOUNTS, start=1):
        add_mount(board, library, i, x, y)
    for title, x, y in (("COMPASS EVT1 / OPEN BENCH", 85, 76), ("USB-C", 110.5, 72.2),
                        ("DOCK HOST", 135, 75.3), ("HOST KEY  PC / DOCK", 122.3, 88.54),
                        ("3V3 LINK", 116.2, 124.3), ("MOTOR VM", 116.2, 112.5),
                        ("PACK+", 82, 113.3), ("NTC SIM", 82, 138), ("RECOVERY", 131, 119),
                        ("FIT ONE HOST KEY WITH POWER OFF", 119, 147)):
        add_silk(board, title, x, y, .8 if title != "COMPASS EVT1 / OPEN BENCH" else 1.2)
    for i, (x, y, _) in TP_POSES.items():
        testpoint = parts[f"TP{i}"]
        add_silk(board, testpoint.findtext("value").replace("DEV_", ""), x, y - 2.4, .80)
    preserved = preserve_routes(board, pins, datasets)
    for layer in CRITICAL_LAYERS.values():
        add_zone(board, RF_KEEP_OUT, layer)
    for layer in (pcb.In2_Cu, pcb.In4_Cu):
        add_zone(board, OUTLINE, layer, "GND")
    add_mount_plane_keepouts(board)
    add_outer_ground_zones(board)
    if not pcb.SaveBoard(str(BOARD), board):
        raise RuntimeError("Could not save native KiCad board")
    report = {"source_netlist_sha256": hashlib.sha256(XML.read_bytes()).hexdigest(),
              "boards": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p, _, _ in SOURCES},
              "footprints": len(parts), "preserved_local_copper": dict(preserved)}
    (HERE / "placement.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Placed", len(parts), "schematic footprints and retained", sum(preserved.values()), "local copper objects")


def export_dsn():
    board = pcb.LoadBoard(str(BOARD))
    if not pcb.ExportSpecctraDSN(board, str(DSN)):
        raise RuntimeError("Could not export router interchange")
    exchange = DSN.read_text()
    for layer in ("In2.Cu", "In4.Cu"):
        exchange = re.sub(r'(\(layer ' + re.escape(layer) + r'\s+\(type )signal', r'\1power', exchange)
    active = "\n    (autoroute_settings (autoroute on) (postroute off) (vias on) "
    for layer in CRITICAL_LAYERS:
        status = "off" if layer in ("In2.Cu", "In4.Cu") else "on"
        axis = "horizontal" if layer in ("F.Cu", "In3.Cu") else "vertical"
        active += f"(layer_rule {layer} (active {status}) (preferred_direction {axis})) "
    active += ")"
    insert = exchange.index("\n    (boundary")
    exchange = exchange[:insert] + active + exchange[insert:]
    supply = ("DEV_DOCK_5V", "DEV_PACK_POS", "DEV_USB_5V", "DOCK_5V", "PACK_P")
    header = exchange.index("(class kicad_default")
    circuit = exchange.index("(circuit", header)
    names = exchange[header:circuit]
    for net in supply:
        names = re.sub(r"(?<!\S)" + re.escape(net) + r"(?=\s)", "", names)
    exchange = exchange[:header] + names + exchange[circuit:]
    insert = exchange.rfind("\n  )", 0, exchange.index("\n  (wiring"))
    power_class = ("\n    (class BenchSupply " + " ".join(supply) + "\n"
                   "      (circuit (use_via Via[0-5]_550:250_um))\n"
                   "      (rule (width 450) (clearance 100.1))\n"
                   "    )")
    exchange = exchange[:insert] + power_class + exchange[insert:]
    DSN.write_text(exchange)


def import_ses(path):
    board = pcb.LoadBoard(str(BOARD))

    def coords(position):
        return round(position.x / 1000), round(position.y / 1000)

    def signature(item):
        if isinstance(item, pcb.PCB_VIA):
            return item.GetNetname(), "via", coords(item.GetPosition()), item.GetWidth(), item.GetDrillValue()
        return (item.GetNetname(), item.GetLayerName(),
                tuple(sorted((coords(item.GetStart()), coords(item.GetEnd())))), item.GetWidth())

    session = sexp.parse(path.read_text())
    routes = sexp.child(session, "routes")
    resolution = sexp.child(routes, "resolution")
    assert resolution[1].value == "um", resolution[1].value
    units = float(resolution[2].value) * 1000

    def session_point(x, y):
        return point(float(x.value) / units, -float(y.value) / units)

    existing = {signature(track) for track in board.GetTracks()}
    added = 0
    for net in sexp.children(sexp.child(routes, "network_out"), "net"):
        use_net = board.FindNet(net[1].value)
        assert use_net is not None, net[1].value
        items = []
        for wire in sexp.children(net, "wire"):
            trace = sexp.child(wire, "path")
            width = max(pcb.FromMM(.15), pcb.FromMM(float(trace[2].value) / units))
            vertices = [session_point(x, y) for x, y in zip(trace[3::2], trace[4::2])]
            for a, b in zip(vertices, vertices[1:]):
                if a == b:
                    continue
                item = pcb.PCB_TRACK(board)
                item.SetStart(a)
                item.SetEnd(b)
                item.SetWidth(width)
                item.SetLayer(CRITICAL_LAYERS[trace[1].value])
                items.append(item)
        for hole in sexp.children(net, "via"):
            via_type = re.fullmatch(r"Via\[\d+-\d+\]_(\d+):(\d+)_um", hole[1].value)
            assert via_type, hole[1].value
            item = pcb.PCB_VIA(board)
            item.SetPosition(session_point(hole[2], hole[3]))
            item.SetWidth(pcb.FromMM(float(via_type[1]) / 1000))
            item.SetDrill(pcb.FromMM(float(via_type[2]) / 1000))
            item.SetViaType(pcb.VIATYPE_THROUGH)
            item.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
            items.append(item)
        for item in items:
            item.SetNet(use_net)
            key = signature(item)
            if key not in existing:
                board.Add(item)
                existing.add(key)
                added += 1
    pcb.SaveBoard(str(BOARD), board)
    board = pcb.LoadBoard(str(BOARD))
    board.BuildConnectivity()
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    pcb.SaveBoard(str(BOARD), board)
    print("Imported", added, "new copper objects")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("place", "export", "import", "sync"))
    parser.add_argument("--session", type=Path)
    args = parser.parse_args()
    project_path = BOARD.with_suffix(".kicad_pro")
    old_project = json.loads(project_path.read_text()) if project_path.exists() else {}
    if args.action == "place":
        place()
    elif args.action == "export":
        export_dsn()
        return
    elif args.action == "sync":
        sync_symbol_metadata()
    else:
        if not args.session:
            parser.error("--session is required for import")
        import_ses(args.session)
    # KiCad 7 saves the native artwork but does not know the KiCad 10-only
    # check keys. Preserve the project's selected severities on each save.
    if old_project:
        project = json.loads(project_path.read_text())
        old_rules = old_project.get("board", {}).get("design_settings", {}).get("rule_severities", {})
        project["board"]["design_settings"]["rule_severities"].update(old_rules)
        if "erc" in old_project:
            project["erc"] = old_project["erc"]
        project_path.write_text(json.dumps(project, indent=2) + "\n")


if __name__ == "__main__":
    main()
