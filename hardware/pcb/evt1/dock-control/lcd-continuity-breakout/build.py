"""Generate the passive continuity breakout from the frozen lid J302."""

import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / "lcd-socket-candidate"
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import kicad_sexp as sexp

NAME = "JST27-continuity"
SOCKET_ORIGIN = (100, 49)
PROBE_ORIGIN = (100, 13)
LID_SHA256 = "fbb712251fee3de42941a4081863d6af38ff0cb1c16a4a6933a278c477f43a7a"
SOCKET_LIB = "JST_27FLZ-RSM2-TB_1x27_P0.50mm_BottomContact"
PROBE_LIB = "ProbeRow_1x27_P2.54mm"


def fields(name, *items):
    return [sexp.atom(name), *items]


def number(value):
    return sexp.atom(f"{value:.5f}".rstrip("0").rstrip("."))


def pin_net(pin):
    return fields("net", number(pin), sexp.string(f"PIN_{pin:02d}"))


def pad_signature(pad):
    return (
        pad[1].value,
        pad[2].value,
        pad[3].value,
        *[tuple(v.value for v in sexp.child(pad, name)[1:]) for name in ("at", "size", "layers")],
    )


def pad_decimal_signature(pad):
    pin, kind, shape, at, size, layers = pad_signature(pad)
    return pin, kind, shape, tuple(map(float, at)), tuple(map(float, size)), layers


def j302_footprint(board):
    return next(
        fp
        for fp in sexp.children(board, "footprint")
        if fp[1].value == f"DockControl:{SOCKET_LIB}"
    )


def normalized_footprint(module, name, reference, origin):
    footprint = copy.deepcopy(module)
    footprint[1] = sexp.string(name)
    footprint[:] = [value for value in footprint if sexp.tag(value) not in ("version", "generator", "path")]
    at = sexp.child(footprint, "at")
    placement = fields("at", *map(number, origin))
    if at is None:
        footprint.insert(2, placement)
    else:
        at[:] = placement
    for text in sexp.children(footprint, "fp_text"):
        if text[1].value == "reference":
            text[2] = sexp.string(reference)
    return footprint


def probe_library():
    header = f"""(footprint "{PROBE_LIB}"
      (version 20221018) (generator pcbnew) (layer "F.Cu")
      (attr through_hole exclude_from_bom exclude_from_pos_files)
      (descr "Individually numbered 2.54 mm pitch plated probe holes")
      (fp_text reference "REF**" (at 0 -3.8) (layer "F.SilkS") hide
        (effects (font (size 1 1) (thickness 0.15))))
      (fp_text value "Passive test points" (at 0 3.8) (layer "F.Fab") hide
        (effects (font (size 1 1) (thickness 0.15))))
      (fp_rect (start -34.3 -1.27) (end 34.3 1.27)
        (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start -34.3 -1.27) (end 34.3 1.27)
        (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd"))
    """
    pads = []
    for pin in range(1, 28):
        x = (pin - 14) * 2.54
        shape = "rect" if pin == 1 else "circle"
        pads.append(
            f'(pad "{pin}" thru_hole {shape} (at {x:.2f} 0) (size 1.8 1.8)'
            ' (drill 1) (layers "*.Cu" "*.Mask"))'
        )
    return sexp.parse(header + "\n".join(pads) + ")")


def segment(start, end, pin):
    return sexp.parse(
        f'(segment (start {start[0]:.5f} {start[1]:.5f})'
        f' (end {end[0]:.5f} {end[1]:.5f}) (width 0.20) (layer "F.Cu") (net {pin}))'
    )


def silk(text, x, y, size=1.0):
    return sexp.parse(
        f'(gr_text "{text}" (at {x:.5f} {y:.5f}) (layer "F.SilkS")'
        f' (effects (font (size {size} {size}) (thickness 0.15))))'
    )


def main():
    source = CANDIDATE / "dock-lid-jst-candidate.kicad_pcb"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == LID_SHA256
    lid = sexp.parse(source.read_text())
    source_socket = j302_footprint(lid)
    source_pads = list(map(pad_decimal_signature, sexp.children(source_socket, "pad")))
    source_lib = CANDIDATE / "DockControl.pretty" / f"{SOCKET_LIB}.kicad_mod"
    socket_lib = sexp.parse(source_lib.read_text())
    assert source_pads == list(map(pad_decimal_signature, sexp.children(socket_lib, "pad")))

    socket = normalized_footprint(source_socket, f"Bench:{SOCKET_LIB}", "J302", SOCKET_ORIGIN)
    probe_lib = probe_library()
    probe = normalized_footprint(probe_lib, f"Bench:{PROBE_LIB}", "TP1", PROBE_ORIGIN)
    for footprint in (socket, probe):
        for pad in sexp.children(footprint, "pad"):
            pad[:] = [item for item in pad if sexp.tag(item) != "net"]
            if pad[1].value.isnumeric():
                pad.append(pin_net(int(pad[1].value)))

    board = sexp.parse("""(kicad_pcb (version 20221018) (generator pcbnew)
      (general (thickness 1))
      (paper "A4")
      (layers
        (0 "F.Cu" signal) (31 "B.Cu" signal)
        (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen")
        (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user)
        (40 "Dwgs.User" user "User.Drawings") (44 "Edge.Cuts" user)
        (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
        (48 "B.Fab" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0))
      (net 0 "")
    )""")
    board.extend(pin_net(pin) for pin in range(1, 28))
    board.extend([socket, probe])
    board.append(sexp.parse(
        '(gr_rect (start 63 9) (end 137 61)'
        ' (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))'
    ))
    board.extend([silk("JST 27FLZ-RSM2-TB", 100, 57.2), silk("UNPOWERED TEST ONLY", 100, 59.4)])
    for pin in range(1, 28):
        signal_x = 100 + (pin - 14) * 0.5
        probe_x = 100 + (pin - 14) * 2.54
        board.extend([
            segment((signal_x, 49), (signal_x, 47), pin),
            segment((signal_x, 47), (probe_x, 13), pin),
            silk(f"{pin:02d}", probe_x, 10.7, size=0.8),
        ])

    bench_lib = HERE / "Bench.pretty"
    bench_lib.mkdir(exist_ok=True)
    (bench_lib / source_lib.name).write_bytes(source_lib.read_bytes())
    sexp.write(bench_lib / f"{PROBE_LIB}.kicad_mod", probe_lib)
    (HERE / "fp-lib-table").write_text(
        '(fp_lib_table (version 7)\n'
        '  (lib (name "Bench") (type "KiCad") (uri "${KIPRJMOD}/Bench.pretty")'
        ' (options "") (descr "J302 continuity coupon")))\n'
    )
    project = json.loads(source.with_suffix(".kicad_pro").read_text())
    project["meta"]["filename"] = f"{NAME}.kicad_pro"
    settings = project["board"]["design_settings"]
    settings["rules"]["min_clearance"] = 0.15
    project["net_settings"]["classes"][0]["clearance"] = 0.15
    (HERE / f"{NAME}.kicad_pro").write_text(json.dumps(project, indent=2) + "\n")
    sexp.write(HERE / f"{NAME}.kicad_pcb", board)


if __name__ == "__main__":
    main()
