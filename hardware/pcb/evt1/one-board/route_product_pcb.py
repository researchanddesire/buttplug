"""Prepare an offline Specctra route pass and import copper without moving parts."""
import argparse
import json
from pathlib import Path
import re
import sys

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "tools"))
import kicad_sexp as sexp

HIGH_CURRENT = ("PACK_P", "SYS", "VBUS_CHG", "MOTOR_3V7", "MOTOR_P", "MOTOR_N",
                "DOCK_5V", "DOCK_FUSED", "REG1_L1", "REG1_L2", "REG2_L1", "REG2_L2")
POWER_CLASSES = {"Power": (500, HIGH_CURRENT), "V3P3": (300, ("3V3",))}
SIGNAL_LAYERS = ("F.Cu", "In2.Cu", "B.Cu")
USB_NETS = {"USB_DP", "USB_DM", "USB_DP_CONTACT", "USB_DM_CONTACT"}


def restore_ground_planes(board_file):
    """Recreate the original flange's reference and ground return pours."""
    board = pcb.LoadBoard(str(board_file))
    if any(not zone.GetIsRuleArea() for zone in board.Zones()):
        raise ValueError("Review existing copper pours before replacing them")
    outline_source = HERE.parent / "single-flange-routing/mcad.json"
    outline = json.loads(outline_source.read_text())["outline_product_XZ_mm"]
    ground = board.FindNet("GND")
    assert ground is not None
    for layer in (pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu):
        zone = pcb.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(ground)
        zone.SetLocalClearance(pcb.FromMM(.15))
        zone.SetMinThickness(pcb.FromMM(.15))
        zone.SetPadConnection(pcb.ZONE_CONNECTION_FULL if layer == pcb.In1_Cu
                              else pcb.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(pcb.FromMM(.2))
        zone.SetThermalReliefSpokeWidth(pcb.FromMM(.25))
        zone.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
        polygon = zone.Outline()
        polygon.NewOutline()
        for x, z in outline:
            polygon.Append(pcb.FromMM(100+x), pcb.FromMM(100-z))
        board.Add(zone)
    project = board_file.with_suffix(".kicad_pro")
    settings = project.read_bytes()
    pcb.SaveBoard(str(board_file), board)
    project.write_bytes(settings)
    print("Restored the In1 reference plane and In2/B ground return pours.")


def clean_seed(board_file, drc, result):
    """Remove only inherited copper that conflicts with the new placement."""
    if result.exists():
        raise ValueError(f"Output exists: {result}")
    board = pcb.LoadBoard(str(board_file))
    tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    conflicts = {item["uuid"] for violation in json.loads(drc.read_text())["violations"]
                 if violation["type"] in {"shorting_items", "clearance", "hole_clearance",
                                          "solder_mask_bridge"}
                 for item in violation["items"] if item["uuid"] in tracks}
    usb = sorted(uid for uid in conflicts if tracks[uid].GetNetname() in USB_NETS)
    if usb:
        raise ValueError(f"Placement crosses preserved USB copper. Repair placement first: {usb}")
    for uid in sorted(conflicts):
        board.Delete(tracks[uid])
    board.SetFileName(str(result))
    pcb.SaveBoard(str(result), board)
    result.with_suffix(".kicad_pro").write_bytes(board_file.with_suffix(".kicad_pro").read_bytes())
    if not pcb.ExportSpecctraDSN(board, str(result.with_suffix(".dsn"))):
        raise RuntimeError("Unable to export cleaned placement")
    print(f"Removed {len(conflicts)} inherited copper objects reported in native DRC.")


def restore_widths(board_file):
    """Restore the native minimum after routing, then review fresh DRC."""
    board = pcb.LoadBoard(str(board_file))
    project = board_file.with_suffix(".kicad_pro")
    settings = project.read_bytes()
    changed = 0
    for trace in board.GetTracks():
        if isinstance(trace, pcb.PCB_VIA) or trace.GetWidth() >= pcb.FromMM(.15):
            continue
        if trace.IsLocked():
            raise ValueError(f"Fixed trace is below 0.15 mm: {trace.m_Uuid.AsString()}")
        trace.SetWidth(pcb.FromMM(.15))
        changed += 1
    pcb.SaveBoard(str(board_file), board)
    project.write_bytes(settings)
    print(f"Restored {changed} imported track widths to 0.15 mm.")


def make_exchange(infile, outfile):
    source = infile.read_text()
    source = re.sub(r"(\(layer In1.Cu\s+\(type )signal(\))", r"\1power\2", source)
    settings = """(autoroute_settings (fanout off) (autoroute on) (postroute off) (vias on)
      (via_costs 25) (plane_via_costs 4) (start_ripup_costs 100)
      (layer_rule F.Cu (active on) (preferred_direction horizontal))
      (layer_rule In1.Cu (active off) (preferred_direction horizontal))
      (layer_rule In2.Cu (active on) (preferred_direction vertical))
      (layer_rule B.Cu (active on) (preferred_direction horizontal)))
    """
    at = source.index("(boundary")
    source = source[:at] + settings + source[at:]
    start = source.index("(class kicad_default")
    end = source.index("(circuit", start)
    classes = source[start:end]
    for _, nets in POWER_CLASSES.values():
        for net in nets:
            if not re.search(r"(?<!\S)" + net + r"(?!\S)", classes):
                raise ValueError(f"Expected net missing from default class: {net}")
            classes = re.sub(r"(?<!\S)" + net + r"(?!\S)", "", classes)
    source = source[:start] + classes + source[end:]
    at = source.index("(wiring")
    before = source[:at]
    end_network = before.rfind(")")
    all_classes = []
    for name, (width, nets) in POWER_CLASSES.items():
        all_classes.append(f"(class {name} {' '.join(nets)} "
                           f"(circuit (use_via Via[0-3]_500:200_um))"
                           f"(rule (width {width}) (clearance 150.1)))")
    source = before[:end_network] + "\n    ".join(all_classes) + "\n  " + source[end_network:]
    outfile.write_text(source)


def coord(x, y, scale):
    return pcb.VECTOR2I(round(float(x.value)*scale), round(-float(y.value)*scale))


def position_key(pos):
    return round(pos.x/1000), round(pos.y/1000)


def trace_key(a, b, layer, net):
    return layer, net, tuple(sorted((position_key(a), position_key(b))))


def load_routes(board_file, session, result):
    if result.exists():
        raise ValueError(f"Output exists: {result}")
    board = pcb.LoadBoard(str(board_file))
    board.SetFileName(str(result))
    settings_source = board_file.with_suffix(".kicad_pro")
    settings_target = result.with_suffix(".kicad_pro")
    settings = settings_source.read_bytes()
    existing_traces, existing_vias = set(), {}
    for track in list(board.GetTracks()):
        if not track.IsLocked():
            board.Delete(track)
        elif isinstance(track, pcb.PCB_VIA):
            existing_vias[position_key(track.GetPosition())] = track.GetNetname()
        else:
            existing_traces.add(trace_key(track.GetStart(), track.GetEnd(), track.GetLayer(), track.GetNetname()))
    locked = {item.m_Uuid.AsString() for item in board.GetTracks()}
    routes = sexp.child(sexp.parse(session.read_text()), "routes")
    unit, scale = [atom.value for atom in sexp.child(routes, "resolution")[1:]]
    scale = {"um":1000, "mm":1000000, "nm":1}[unit] / float(scale)
    added = 0
    for route in sexp.children(sexp.child(routes, "network_out"), "net"):
        name = route[1].value
        net = board.FindNet(name)
        if net is None:
            raise ValueError(f"Unexpected router net {name}")
        for item in route[2:]:
            if sexp.tag(item) == "wire":
                path = sexp.child(item, "path")
                layer_name = path[1].value
                if layer_name not in SIGNAL_LAYERS:
                    raise ValueError(f"Signal on unrouteable layer {layer_name}")
                layer = board.GetLayerID(layer_name)
                width = round(float(path[2].value)*scale)
                points = [coord(x,y,scale) for x,y in zip(path[3::2],path[4::2])]
                for a,b in zip(points,points[1:]):
                    key = trace_key(a,b,layer,name)
                    if a == b or key in existing_traces:
                        continue
                    track = pcb.PCB_TRACK(board)
                    track.SetStart(a)
                    track.SetEnd(b)
                    track.SetWidth(width)
                    track.SetLayer(layer)
                    track.SetNet(net)
                    board.Add(track)
                    existing_traces.add(key)
                    added += 1
            elif sexp.tag(item) == "via":
                position = coord(item[2],item[3],scale)
                key = position_key(position)
                previous = existing_vias.get(key)
                if previous is not None:
                    if previous != name:
                        raise ValueError(f"Via overlaps different net at {position}")
                    continue
                spec = re.fullmatch(r"Via\[0-3\]_(\d+):(\d+)_um", item[1].value)
                if spec is None:
                    raise ValueError(f"Unsupported via {item[1].value}")
                via = pcb.PCB_VIA(board)
                via.SetPosition(position)
                via.SetViaType(pcb.VIATYPE_THROUGH)
                via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
                via.SetWidth(int(spec[1])*1000)
                via.SetDrill(int(spec[2])*1000)
                via.SetNet(net)
                board.Add(via)
                existing_vias[key] = name
                added += 1
            else:
                raise ValueError(f"Unexpected SES copper {sexp.tag(item)}")
    assert locked == {item.m_Uuid.AsString() for item in board.GetTracks() if item.IsLocked()}
    pcb.SaveBoard(str(result), board)
    settings_target.write_bytes(settings)
    print(f"Imported {added} copper objects, preserved {len(locked)} fixed objects.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    dsn = sub.add_parser("dsn")
    dsn.add_argument("native_dsn", type=Path)
    dsn.add_argument("output", type=Path)
    clean = sub.add_parser("clean")
    clean.add_argument("board", type=Path)
    clean.add_argument("drc", type=Path)
    clean.add_argument("output", type=Path)
    widths = sub.add_parser("widths")
    widths.add_argument("board", type=Path)
    ground = sub.add_parser("ground")
    ground.add_argument("board", type=Path)
    ses = sub.add_parser("ses")
    ses.add_argument("board", type=Path)
    ses.add_argument("session", type=Path)
    ses.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.action == "dsn":
        make_exchange(args.native_dsn, args.output)
    elif args.action == "clean":
        clean_seed(args.board, args.drc, args.output)
    elif args.action == "widths":
        restore_widths(args.board)
    elif args.action == "ground":
        restore_ground_planes(args.board)
    else:
        load_routes(args.board, args.session, args.output)


if __name__ == "__main__":
    main()
