#!/usr/bin/env python3
"""Build the intact-laminate EVT flange from the frozen routed working PCB."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent / "single-flange-routing"
PROJECT = "single-flange-thermal"
EXPECTED = "bd1d834974698c49e7bfe886a0ead1d0fb34d7bce1f324bef01f03695cfb707a"
BOARD = HERE / f"{PROJECT}.kicad_pcb"
sys.path.insert(0, str(ROOT / "tools"))
import kicad_sexp as sx
import electronics_r0_generate as sch

parse = sx.parse
uid = lambda key: str(uuid5(NAMESPACE_URL, f"compass/thermal-flange-r1/{key}"))
SITES = (
    ("TH1", "J83", 94.25, "PACK_NTC", "PACK_NTC_RET", "J2.3"),
    ("TH2", "J84", 105.75, "PACK_GUARD", "PACK_GUARD_RET", "J2.4"),
)
# Native KiCad absolute mm. Locations are from the active 100/100 mm datum.
SENSOR_X, TAIL_X = 117.75, 125.25
# Match the two original centres and put the long keepout extension toward the
# tails, away from R39. Close both heat windows on F, In1, In2 and B.
WINDOW_X = (114.50, 122.0)
WINDOW_HALF_Y = 3.75
PLANES = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")
REROUTE = (
    (101.49,107.744), (112.1,107.744), (115.0,110.644),
    (122.0,110.644), (123.65,108.994), (123.65,104.7258), (130.2515,98.1243),
)
NTC = "NTCS0402E3103FL1T"
TAIL = "Separate wire pair"
FOOT = {"TH": "NTCS0402_Vishay_Reflow", "J": "SensorWirePair_2x1mm"}
VISHAY = "https://www.vishay.com/docs/29224/handlmount-ntcssmdntctherm.pdf"


def digest(p):
    return sha256(p.read_bytes()).hexdigest()


def pin_symbol_path(root_id, child_id, ref):
    return f"/{root_id}/{child_id}/{sch.uid(ref)}"


def make_schematic():
    sch.OUT = HERE / "sheets"
    sch.PROJECT = PROJECT
    sch.LIB.clear()
    sch.passive("PackThermistor0402", "R")
    sch.LIB["PackThermistor0402"]["source"] = VISHAY
    sch.connector("SensorWirePair", 2)
    leaf = sch.Sheet("09-pack-ntc", "EVT flange thermistor isolation / separate safety channels")
    root = parse((BASE / "single-flange.kicad_sch").read_text())
    root_id = sx.value(root, "uuid")
    child_id = uid("sheet-09-pack-ntc")
    leaf.sheet_path = f"/{root_id}/{child_id}"
    leaf.note("EVT thermal isolation. Pairs are floating on the flange. Route each sensor return separately to body J2.2S.", 20.32, 20.32)
    for i, (ref,jref,_,signal,ret,body) in enumerate(SITES):
        y = 63.5 + i * 55.88
        pins = {"1": signal, "2": ret}
        leaf.part("PackThermistor0402", ref, NTC, 66.04, y, pins, "ThermalTrial:" + FOOT["TH"])
        leaf.part("SensorWirePair", jref, TAIL, 160.02, y, pins, "ThermalTrial:" + FOOT["J"])
        leaf.note(f"{jref}.1 to body {body}, {jref}.2 to body J2.2S. Dedicated twisted pair.", 45.72, y + 20.32)
    leaf.save()
    for sheet in sx.children(root, "sheet"):
        file = sx.prop(sheet, "Sheetfile")
        t = parse((BASE / file).read_text())
        for sym in sx.children(t, "symbol"):
            for inst in sx.children(sx.child(sym, "instances") or [], "project"):
                if inst[1].value == "single-flange":
                    inst[1] = sx.string(PROJECT)
        sx.write(HERE / file, t)
    root.append(parse(f'''(sheet (at 25.4 246.38) (size 152.4 25.4)
      (fields_autoplaced) (stroke (width .1524) (type default))
      (fill (color 0 0 0 0)) (uuid {child_id})
      (property "Sheetname" "Thermistor isolation" (at 25.4 245.872 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
      (property "Sheetfile" "sheets/09-pack-ntc.kicad_sch" (at 25.4 272.288 0) (effects (font (size 1.27 1.27)) (justify left top))))'''))
    title = sx.child(root, "title_block")
    sx.child(title,"title")[1] = sx.string("Compass EVT1 single flange / thermal isolation option")
    sx.child(title,"rev")[1] = sx.string("THERMAL TRIAL R1")
    sx.child(title,"comment")[2] = sx.string("EVT ONLY / INERT COUPON AND BATTERY SIMULATOR")
    sx.write(HERE / f"{PROJECT}.kicad_sch", root)
    lib = parse((BASE / "PrototypeR0.kicad_sym").read_text())
    lib.extend(parse(entry["text"]) for entry in sch.LIB.values())
    sx.write(HERE / "PrototypeR0.kicad_sym", lib)
    return root_id, child_id


def pads(kind, side):
    copper = f'"{side}.Cu"'
    paste = f' "{side}.Paste"' if kind == "TH" else ""
    size, spread = ((.50,.60),.50) if kind == "TH" else ((1.0,1.0),.70)
    return [f'''(pad "{pin}" smd roundrect (at 0 {dy}) (size {size[1]} {size[0]})
      (layers {copper}{paste} "{side}.Mask") (roundrect_rratio 0.2))'''
            for pin,dy in ((1 if side=="B" else 2,-spread),(2 if side=="B" else 1,spread))]


def pattern(kind, side, artwork=False):
    # Vishay 29224 fig/table: 0.50 pad length, 0.60 width, 0.50 gap.
    # Pad line is rotated to make the two matched thermal traces run toward +X.
    package = FOOT[kind] if not artwork else "ThermalTrial:" + FOOT[kind]
    r = .8 if kind == "TH" else 1.35
    x = .38 if kind == "TH" else .68
    attributes = "smd" if kind == "TH" else "smd exclude_from_pos_files exclude_from_bom"
    ref_at, value_at = ("2.05 180", "-2.05 180") if side == "B" else ("-2.05", "2.05")
    cy = r if side == "B" else -r
    return parse(f'''(footprint "{package}" (layer "{side}.Cu") (attr {attributes})
        (descr "{'Vishay 29224 NTCS0402 reflow pattern' if kind == 'TH' else 'Two solder lands for a separate flying wire pair, no paste'}")
        (fp_text reference "REF**" (at 0 {ref_at}) (layer "{side}.SilkS") hide (effects (font (size .75 .75) (thickness .12)) {'(justify mirror)' if side=="B" else ''}))
        (fp_text value "{FOOT[kind]}" (at 0 {value_at}) (layer "{side}.Fab") hide (effects (font (size .65 .65) (thickness .10)) {'(justify mirror)' if side=="B" else ''}))
        (fp_rect (start {-x} {cy}) (end {x} {-cy}) (stroke (width .05) (type default)) (fill none) (layer "{side}.CrtYd"))
        {''.join(pads(kind, side))})''')


def stamp(board_item, key):
    board_item.append(parse(f"(tstamp {uid(key)})"))


def xy(node, key):
    return tuple(round(float(v.value),6) for v in sx.child(node,key)[1:3])


def make_board(root_id, leaf_id):
    source = BASE / "single-flange.kicad_pcb"
    assert digest(source) == EXPECTED, "Active board changed. Redo the clearance and routing review."
    board = parse(source.read_text())
    original = deepcopy(board)
    by_name = {n[2].value: int(n[1].value) for n in sx.children(board, "net")}
    for _,_,_,hi,lo,_ in SITES:
        for net in (hi,lo):
            by_name[net] = max(by_name.values()) + 1
            board.insert(board.index(sx.child(board,"net")),parse(f'(net {by_name[net]} "{net}")'))
    # Replace only two 3V3 segments carrying the diagonal through the -Z sensor field.
    old_path={frozenset((p,q)) for p,q in zip(
        ((101.49,107.744),(120.6318,107.744)), ((120.6318,107.744),(130.2515,98.1243)))}
    old=[t for t in sx.children(board,"segment") if sx.value(t,"layer")=="In2.Cu"
         and int(sx.value(t,"net"))==by_name["3V3"] and frozenset((xy(t,"start"),xy(t,"end"))) in old_path]
    assert len(old)==2 and len({sx.value(t,"width") for t in old})==1
    width=float(sx.value(old[0],"width"))
    removed_uuids=[sx.value(t,"tstamp") for t in old]
    for t in old: board.remove(t)

    def track(p,q,layer,net,width,key):
        t=parse(f'(segment (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (width {width}) (layer "{layer}") (net {by_name[net]}))')
        stamp(t,key)
        board.append(t)

    for i,(p,q) in enumerate(zip(REROUTE,REROUTE[1:])):
        track(p,q,"In2.Cu","3V3",width,f"reroute-{i}")

    for ref,jref,y,hi,lo,body in SITES:
        for kind,name,x in (("TH",ref,SENSOR_X),("J",jref,TAIL_X)):
            fp=pattern(kind,"B",artwork=True)
            stamp(fp,name)
            fp.extend(parse(f'({s})') for s in (f"at {x} {y}",f'path "{pin_symbol_path(root_id,leaf_id,name)}"'))
            for fpt in sx.children(fp,"fp_text"):
                fpt[2] = sx.string(name if fpt[1].value=="reference" else NTC if kind=="TH" else TAIL)
                stamp(fpt,f"{name}/{fpt[1].value}")
            for i,pad in enumerate(sx.children(fp,"pad")):
                net=(hi,lo)[i]
                pad.append(parse(f'(net {by_name[net]} "{net}")'))
                stamp(pad,f"{name}/pad{i+1}")
            for i,item in enumerate(sx.children(fp,"fp_rect")):stamp(item,f"{name}/rect{i}")
            board.append(fp)
        for pin,net in enumerate((hi,lo)):
            sign = 1 if pin else -1
            p=(SENSOR_X,round(y+sign*.5,4))
            q=(TAIL_X-.2,round(y+sign*.5,4))
            r=(TAIL_X,round(y+sign*.7,4))
            track(p,q,"B.Cu",net,.15,f"{ref}/{pin}/0")
            track(q,r,"B.Cu",net,.15,f"{ref}/{pin}/1")
        x0,x1=WINDOW_X
        y0,y1=(round(y-WINDOW_HALF_Y,4),round(y+WINDOW_HALF_Y,4))
        layer_set=" ".join(f'"{n}"' for n in PLANES)
        area = parse(f'''(zone (net 0) (net_name "") (layers {layer_set})
          (name "{ref} thermal no-pour")
          (hatch edge 0.5) (connect_pads (clearance 0.15)) (min_thickness 0.15) (fill (thermal_gap 0.25) (thermal_bridge_width 0.25))
          (keepout (tracks allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
          (polygon (pts (xy {x0} {y0}) (xy {x1} {y0}) (xy {x1} {y1}) (xy {x0} {y1}))))''')
        stamp(area,f"keepout/{ref}")
        board.append(area)
    # Preserve the source net definitions, every existing footprint, board edge,
    # and all tracks/vias except the two named 3V3 segments.
    for tag in ("gr_arc","gr_line","via"):
        assert list(map(sx.dump,sx.children(board,tag)))==list(map(sx.dump,sx.children(original,tag)))
    assert list(map(sx.dump,sx.children(board,"footprint")[:-4]))==list(map(sx.dump,sx.children(original,"footprint")))
    assert set(map(sx.dump,sx.children(original,"segment")))-set(map(sx.dump,sx.children(board,"segment")))==set(map(sx.dump,old))
    sx.write(BOARD,board)
    for kind in FOOT:
        fp=pattern(kind,"F")
        fp.insert(2,parse("(version 20221018)"))
        fp.insert(3,parse("(generator pcbnew)"))
        sx.write(HERE/"ThermalTrial.pretty"/(FOOT[kind]+".kicad_mod"),fp)
    (HERE/"source-binding.json").write_text(json.dumps({
        "active_board": str(source.relative_to(ROOT)), "active_board_sha256": digest(source),
        "active_schematic_root_sha256": digest(BASE/"single-flange.kicad_sch"),
        "removed_in2_3V3_segment_uuids": removed_uuids, "in2_3V3_detour_native_mm":REROUTE,
        "shipped_sensor_sites": [{"ref":a,"pair":b,"native_xy":[SENSOR_X,c],"signals":[d,e],"body_signal":f,"body_return":"J2.2S"} for a,b,c,d,e,f in SITES],
        "thermal_window_native_x_mm":WINDOW_X,"thermal_window_half_y_mm":WINDOW_HALF_Y,
        "stock_pours_preserved":"All existing zones retained and refilled after adding no-pour areas."
    },indent=2)+"\n")


def main():
    make_board(*make_schematic())
    (HERE/f"{PROJECT}.kicad_pro").write_bytes((BASE/"single-flange.kicad_pro").read_bytes())
    (HERE/"sym-lib-table").write_bytes((BASE/"sym-lib-table").read_bytes())
    libs = parse((BASE/"fp-lib-table").read_text())
    libs.append(parse('(lib (name "ThermalTrial") (type "KiCad") (uri "${KIPRJMOD}/ThermalTrial.pretty") (options "") (descr "EVT thermal sensing lands"))'))
    sx.write(HERE/"fp-lib-table",libs)
    # Models for the original positions remain sourced from the active library.
    for directory in ("Selected.pretty","Selected.3dshapes"):
        link = HERE / directory
        target = Path("../single-flange-routing") / directory
        if not link.exists():
            link.symlink_to(target, target_is_directory=True)
        assert link.resolve() == (BASE/directory).resolve()


if __name__ == "__main__":
    main()
