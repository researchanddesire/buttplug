"""Place the bulb-battery product PCB from the active flange and merged netlist.

Use KiCad's bundled Python. The CAD position input is the one-board mechanical
study's flange-placement-review.json. This command creates an unrouted seed
and deliberately refuses to overwrite a board that already exists.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
EVT = HERE.parent
FLANGE = EVT / "single-flange-routing"
sys.path.insert(0, str(HERE.parents[3] / "tools"))
import kicad_sexp as sexp


def xy(x, z):
    return pcb.VECTOR2I(pcb.FromMM(100 + x), pcb.FromMM(100 - z))


def xz(point):
    return pcb.ToMM(point.x) - 100, 100 - pcb.ToMM(point.y)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(footprint, layers):
    graphics = [item.GetBoundingBox() for item in footprint.GraphicalItems()
                if isinstance(item, pcb.PCB_SHAPE) and item.GetLayer() in layers]
    boxes = graphics or [pad.GetBoundingBox() for pad in footprint.Pads()]
    return (
        min(pcb.ToMM(box.GetLeft()) for box in boxes) - 100,
        100 - max(pcb.ToMM(box.GetBottom()) for box in boxes),
        max(pcb.ToMM(box.GetRight()) for box in boxes) - 100,
        100 - min(pcb.ToMM(box.GetTop()) for box in boxes),
    )


def library_paths(table_path):
    root = sexp.parse(table_path.read_text())
    return {sexp.value(row, "name"): (table_path.parent / sexp.value(row, "uri")
                                     .replace("${KIPRJMOD}/", "")).resolve()
            for row in sexp.children(root, "lib")}


def netlist(path):
    root = ET.parse(path).getroot()
    components = {part.get("ref"): part for part in root.findall("./components/comp")
                  if part.findtext("footprint") and part.find("properties/property[@name='exclude_from_board']") is None}
    pins = {(node.get("ref"), node.get("pin")): net.get("name")
            for net in root.findall("./nets/net") for node in net.findall("node")
            if node.get("ref") in components}
    return components, pins


def set_symbol_metadata(footprint, component):
    footprint.SetValue(component.findtext("value"))
    if component.find("property[@name='exclude_from_bom']") is not None:
        footprint.SetAttributes(
            footprint.GetAttributes() | pcb.FP_EXCLUDE_FROM_BOM | pcb.FP_EXCLUDE_FROM_POS_FILES
        )
    for entry in component.findall("property"):
        name = entry.get("name")
        if name not in {"Sheetname", "Sheetfile", "ki_description", "exclude_from_bom", "dnp"}:
            footprint.SetProperty(name, entry.get("value", ""))
    for entry in component.findall("fields/field"):
        if entry.text:
            footprint.SetProperty(entry.get("name"), entry.text)
    datasheet = component.findtext("datasheet")
    if datasheet:
        footprint.SetProperty("Datasheet", datasheet)


def set_identity(footprint, ref, component, pins, board):
    set_symbol_metadata(footprint, component)
    sheet = component.find("sheetpath").get("tstamps")
    footprint.SetPath(pcb.KIID_PATH(sheet + component.findtext("tstamps").split()[0]))
    for pad in footprint.Pads():
        name = pins.get((ref, pad.GetNumber()))
        if name is None:
            pad.SetNetCode(0)
        else:
            pad.SetNet(board.FindNet(name))


def center_fab(footprint, x, z):
    left, bottom, right, top = bbox(footprint, (pcb.F_Fab, pcb.B_Fab))
    cx, cz = xz(footprint.GetPosition())
    footprint.SetPosition(xy(cx + x - (left + right) / 2, cz + z - (bottom + top) / 2))


def overlap(first, second):
    return (first[0] < second[2] and first[2] > second[0] and
            first[1] < second[3] and first[3] > second[1])


def within(point, poly):
    x, z = point
    return sum((az > z) != (bz > z) and x < ax + (bx-ax)*(z-az)/(bz-az)
               for (ax, az), (bx, bz) in zip(poly, poly[1:] + poly[:1])) % 2 == 1


def orient_side_entry(fp, direction):
    for angle in (0, 90, 180, 270):
        fp.SetOrientationDegrees(angle)
        hold = [xz(pad.GetPosition()) for pad in fp.Pads() if pad.GetNumber() == "MP"]
        signal = [xz(pad.GetPosition()) for pad in fp.Pads() if pad.GetNumber() in ("1", "2")]
        assert len(hold) == len(signal) == 2, fp.GetReference()
        vector = tuple(sum(h[index] - s[index] for h, s in zip(hold, signal))
                       for index in range(2))
        if sum(a*b for a, b in zip(vector, direction)) > .1:
            return
    raise ValueError(f"Unable to orient {fp.GetReference()} to {direction}")


def fit_additions(footprint, ref, board, outline, antenna, probe):
    anchors = {"J8": (17, -6), "R88": (18, -7), "C88": (18, -7)}
    occupied = [bbox(other, (pcb.B_CrtYd, pcb.F_CrtYd))
                for other in board.GetFootprints()
                if other.GetLayer() == pcb.B_Cu or other.GetReference().startswith(("CT", "MH"))]
    occupied.append(antenna)
    # The conservative central nut/mated-connector keepout is applied to J8.
    if ref == "J8":
        occupied.extend(((-14, -13, 12, 13), (29, -5, 38, 5)))
    preferred = anchors[ref]
    grid = [(x/2, z/2) for x in range(-54, 76) for z in range(-22, 23)]
    grid.sort(key=lambda point: (point[0]-preferred[0])**2 + (point[1]-preferred[1])**2)
    for x, z in grid:
        for angle in (0, 90, 180, 270):
            footprint.SetOrientationDegrees(angle)
            center_fab(footprint, x, z)
            x0, z0, x1, z1 = bbox(footprint, (pcb.B_CrtYd,))
            candidate = (x0-.15, z0-.15, x1+.15, z1+.15)
            corners = [(xx, zz) for xx in candidate[::2] for zz in candidate[1::2]]
            if all(within(point, outline) for point in corners) and not any(
                overlap(candidate, rectangle) for rectangle in occupied
            ):
                return {"x_mm": x, "z_mm": z, "angle": angle, "basis": probe}
    raise ValueError(f"No placement for {ref}")


def route_seed(board, source_pins, merged_pins, removed, old_change_nets):
    mapping = {}
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        for pad in footprint.Pads():
            key = ref, pad.GetNumber()
            old_name = source_pins.get(key)
            new_name = merged_pins.get(key)
            if ref not in removed and old_name and new_name:
                mapping.setdefault(old_name, set()).add(new_name)

    kept = 0
    for track in list(board.GetTracks()):
        original = track.GetNetname()
        targets = mapping.get(original, ())
        if not track.IsLocked() or len(targets) != 1 or original in old_change_nets:
            board.Delete(track)
            continue
        track.SetNet(board.FindNet(next(iter(targets))))
        kept += 1
    for zone in list(board.Zones()):
        if zone.GetIsRuleArea():
            continue
        targets = mapping.get(zone.GetNetname(), ())
        if len(targets) != 1 or zone.GetLayer() != pcb.In1_Cu:
            board.Delete(zone)
        else:
            zone.SetNet(board.FindNet(next(iter(targets))))
            zone.UnFill()
    return kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", type=Path, required=True)
    parser.add_argument("--mechanical-placement", type=Path, required=True)
    parser.add_argument("--board", type=Path, default=HERE / "compass-one-board.kicad_pcb")
    args = parser.parse_args()
    target = args.board.resolve()
    if target.exists():
        parser.error(f"Board already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    source = FLANGE / "single-flange.kicad_pcb"
    components, pins = netlist(args.netlist)
    fl_components, fl_pins = netlist(FLANGE / "single-flange-native.xml")
    old_change_nets = {net for (ref, _), net in fl_pins.items() if ref == "J7"} - {"GND"}
    body_data = json.loads((EVT / "body/mcad.json").read_text())
    fl_data = json.loads((FLANGE / "mcad.json").read_text())
    assert digest(source) == fl_data["board_sha256"]
    body = {part["ref"]: part for part in body_data["components"]}
    places = json.loads(args.mechanical_placement.read_text())["component_positions"]
    expected = (set(fl_components) - {"J7"}) | set(places) | {"J8", "R88", "C88"}
    if set(components) != expected:
        raise ValueError(f"Schematic footprint delta. Missing {expected-set(components)}, extra {set(components)-expected}")

    board = pcb.LoadBoard(str(source))
    board.SetFileName(str(target))
    for name in sorted(set(pins.values())):
        if board.FindNet(name) is None:
            board.Add(pcb.NETINFO_ITEM(board, name))
    kept = route_seed(board, fl_pins, pins, {"J7"}, old_change_nets)
    present = {fp.GetReference(): fp for fp in board.GetFootprints()}
    board.Delete(present.pop("J7"))
    for ref, footprint in present.items():
        if ref in components:
            set_identity(footprint, ref, components[ref], pins, board)
        elif ref in ("MH1", "MH2", "MH3", "MH4"):
            footprint.SetAttributes(footprint.GetAttributes() | pcb.FP_BOARD_ONLY)

    libraries = library_paths(FLANGE / "fp-lib-table")
    outline = fl_data["outline_product_XZ_mm"]
    antenna = fl_data["RF_antenna_region_product_XZ_mm"]
    actual = {}
    for ref in dict.fromkeys([*places, "J8", "R88", "C88"]):
        entry = components[ref]
        ident = entry.findtext("footprint")
        alias, name = ident.split(":", maxsplit=1)
        fp = pcb.FootprintLoad(str(libraries[alias]), name)
        assert fp, ident
        fp.SetReference(ref)
        fp.SetFPID(pcb.LIB_ID(alias, name))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
        fp.Flip(fp.GetPosition(), True)
        if ref in places:
            planned = places[ref]
            x, z = planned["center_xz_mm"]
            native_angle = body[planned.get("geometry_from_source_ref", ref)]["angle_deg"]
            fp.SetOrientationDegrees(native_angle + planned["quarter_turn"] * 90)
            if "geometry_from_source_ref" in planned and ref in ("J3", "J8"):
                orient_side_entry(fp, {"J3": (-1, 0), "J8": (0, -1)}[ref])
            center_fab(fp, x, z)
            pose = {"x_mm":x, "z_mm":z, "angle":fp.GetOrientationDegrees(),
                    "basis":"mechanical study; verify mating and package poses on final copper"}
        else:
            pose = fit_additions(fp, ref, board, outline, antenna, "initial electrical placement")
        set_identity(fp, ref, entry, pins, board)
        actual[ref] = pose

    project = target.with_suffix(".kicad_pro")
    design = project.read_bytes() if project.exists() else (FLANGE / "single-flange.kicad_pro").read_bytes()
    pcb.SaveBoard(str(target), board)
    project.write_bytes(design)
    # Relative model paths in the baseline board were relative to its project.
    target.write_text(target.read_text().replace(
        "${KIPRJMOD}/Selected.3dshapes/", "${KIPRJMOD}/../single-flange-routing/Selected.3dshapes/"
    ))
    if not pcb.ExportSpecctraDSN(board, str(target.with_suffix(".dsn"))):
        raise RuntimeError("KiCad did not export the Specctra seed")
    (target.parent / f"{target.stem}-placement.json").write_text(json.dumps({
        "source_flange_sha256":digest(source),
        "mechanical_placement_sha256":digest(args.mechanical_placement),
        "netlist_sha256":digest(args.netlist),
        "seed_sha256":digest(target),
        "electrical_footprints":len(components),
        "preserved_locked_copper":kept,
        "inside_face_placements":actual,
        "scope":"PCB placement seed. Complete and audit copper, pad parity, CAD and fabrication before ordering.",
    }, indent=2) + "\n")
    print(f"Placed {len(components)} electrical footprints; retained {kept} locked copper objects.")


if __name__ == "__main__":
    main()
