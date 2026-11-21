"""Compact two-sided relayout of the EVT1 one-board: 52 x 20 mm, four layers.

Reads build/plan.py (placement table), rewrites footprint poses and sides,
replaces the outline, ground pours and keepouts, and strips old copper.
Run from this directory. Routing is a separate Freerouting pass.
"""
import json, math, sys, uuid
from pathlib import Path
sys.path.insert(0, 'build')
from sx import *
import plan

HERE = Path(__file__).resolve().parent
BOARD_FILE = HERE / 'compass-one-board.kicad_pcb'
SOURCE_FILE = HERE / 'backup' / 'compass-one-board-82x26-20261118.kicad_pcb'  # the reviewed 82 x 26 board, KiCad 7 text format
X0, Y0, X1, Y1 = plan.BOARD
R = 2.0

SWAP = {'F.Cu':'B.Cu','B.Cu':'F.Cu','F.Paste':'B.Paste','B.Paste':'F.Paste','F.Mask':'B.Mask','B.Mask':'F.Mask',
        'F.SilkS':'B.SilkS','B.SilkS':'F.SilkS','F.Fab':'B.Fab','B.Fab':'F.Fab','F.CrtYd':'B.CrtYd','B.CrtYd':'F.CrtYd',
        'F.Adhes':'B.Adhes','B.Adhes':'F.Adhes'}

def norm(a):
    a = (a + 180) % 360 - 180
    return 180.0 if a == -180 else a

def swap_layers(node):
    for c in node:
        if isinstance(c, list) and tag(c) in ('layer', 'layers'):
            for i in range(1, len(c)):
                v = c[i].value
                if v in SWAP: c[i] = string(SWAP[v])

def neg_y(node, key):
    c = child(node, key)
    if c: c[2] = atom(-fnum(c[2]))

def flip_footprint(fp):
    lay = child(fp, 'layer'); lay[1] = string(SWAP[lay[1].value])
    to_back = lay[1].value == 'B.Cu'
    for it in fp:
        if not isinstance(it, list): continue
        t = tag(it)
        if t == 'pad':
            at = child(it, 'at'); at[2] = atom(-fnum(at[2]))
            if len(at) > 3: at[3] = atom(norm(-fnum(at[3])))
            swap_layers(it)
        elif t in ('fp_text', 'property'):
            at = child(it, 'at')
            if at:
                at[2] = atom(-fnum(at[2]))
                if len(at) > 3: at[3] = atom(norm(-fnum(at[3])))
            swap_layers(it)
            eff = child(it, 'effects')
            if eff:
                j = child(eff, 'justify')
                if to_back:
                    if j is None: eff.append([atom('justify'), atom('mirror')])
                    elif not any(isinstance(a, Atom) and a.raw == 'mirror' for a in j[1:]): j.append(atom('mirror'))
                elif j is not None:
                    j[:] = [a for a in j if not (isinstance(a, Atom) and a.raw == 'mirror')]
                    if len(j) == 1: eff.remove(j)
        elif t in ('fp_line', 'fp_arc', 'fp_rect', 'fp_circle'):
            for k in ('start', 'end', 'mid', 'center'): neg_y(it, k)
            swap_layers(it)
        elif t == 'fp_poly':
            for p in children(child(it, 'pts'), 'xy'): p[2] = atom(-fnum(p[2]))
            swap_layers(it)

def set_pose(fp, x, y, rot, side):
    at = child(fp, 'at')
    old_rot = fnum(at[3]) if len(at) > 3 else 0.0
    old_side = 'B' if child(fp, 'layer')[1].value == 'B.Cu' else 'F'
    flipped = old_side != side
    # pad angles are stored absolute: keep each pad's local angle through the change
    locals_ = []
    for p in children(fp, 'pad'):
        pat = child(p, 'at'); a = fnum(pat[3]) if len(pat) > 3 else 0.0
        locals_.append(norm(a - old_rot))
    if flipped: flip_footprint(fp)
    for p, la in zip(children(fp, 'pad'), locals_):
        pat = child(p, 'at')
        if flipped: la = norm(-la)
        a = norm(rot + la)
        if len(pat) > 3: pat[3] = atom(a)
        elif a != 0: pat.append(atom(a))
    for it in children(fp, 'fp_text') + children(fp, 'property'):
        tat = child(it, 'at')
        if tat and len(tat) > 3:
            la = norm(fnum(tat[3]) - (norm(-old_rot) if flipped else old_rot))
            tat[3] = atom(norm(rot + la))
    at[1] = atom(x); at[2] = atom(y)
    if rot != 0:
        if len(at) > 3: at[3] = atom(rot)
        else: at.append(atom(rot))
    elif len(at) > 3: del at[3]
    # unlock
    fp[:] = [a for a in fp if not (isinstance(a, Atom) and a.raw == 'locked')]

def ts(): return atom(str(uuid.uuid4()))

def gr_line(a, b):
    return [atom('gr_line'), [atom('start'), atom(a[0]), atom(a[1])], [atom('end'), atom(b[0]), atom(b[1])],
            [atom('stroke'), [atom('width'), atom(0.05)], [atom('type'), atom('default')]], [atom('layer'), string('Edge.Cuts')], [atom('tstamp'), ts()]]

def gr_arc(a, m, b):
    return [atom('gr_arc'), [atom('start'), atom(a[0]), atom(a[1])], [atom('mid'), atom(m[0]), atom(m[1])], [atom('end'), atom(b[0]), atom(b[1])],
            [atom('stroke'), [atom('width'), atom(0.05)], [atom('type'), atom('default')]], [atom('layer'), string('Edge.Cuts')], [atom('tstamp'), ts()]]

def outline():
    k = R * (1 - math.sqrt(0.5))
    items = [gr_line((X0 + R, Y0), (X1 - R, Y0)), gr_line((X1, Y0 + R), (X1, Y1 - R)),
             gr_line((X1 - R, Y1), (X0 + R, Y1)), gr_line((X0, Y1 - R), (X0, Y0 + R)),
             gr_arc((X1 - R, Y0), (X1 - k, Y0 + k), (X1, Y0 + R)),
             gr_arc((X1, Y1 - R), (X1 - k, Y1 - k), (X1 - R, Y1)),
             gr_arc((X0 + R, Y1), (X0 + k, Y1 - k), (X0, Y1 - R)),
             gr_arc((X0, Y0 + R), (X0 + k, Y0 + k), (X0 + R, Y0))]
    return items

def poly(pts):
    return [atom('polygon'), [atom('pts')] + [[atom('xy'), atom(x), atom(y)] for x, y in pts]]

def rect(x0, y0, x1, y1): return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def gnd_zone(layer, gnd):
    return [atom('zone'), [atom('net'), atom(gnd)], [atom('net_name'), string('GND')], [atom('layer'), string(layer)],
            [atom('tstamp'), ts()], [atom('hatch'), atom('edge'), atom(0.5)],
            [atom('connect_pads'), atom('yes') if layer == 'In1.Cu' else atom('thermal_reliefs'), [atom('clearance'), atom(0.15)]] if False else
            ([atom('connect_pads'), atom('yes'), [atom('clearance'), atom(0.15)]] if layer == 'In1.Cu' else [atom('connect_pads'), [atom('clearance'), atom(0.15)]]),
            [atom('min_thickness'), atom(0.15)], [atom('filled_areas_thickness'), atom('no')],
            [atom('fill'), atom('yes'), [atom('thermal_gap'), atom(0.2)], [atom('thermal_bridge_width'), atom(0.25)], [atom('island_removal_mode'), atom(0)], [atom('island_area_min'), atom(0)]],
            poly(rect(X0, Y0, X1, Y1))]

def keepout(layers, pts, tracks, vias, pads, pour, footprints, name=''):
    z = [atom('zone'), [atom('net'), atom(0)], [atom('net_name'), string('')]]
    if len(layers) == 1: z.append([atom('layer'), string(layers[0])])
    else: z.append([atom('layers')] + [string(l) for l in layers])
    z += [[atom('tstamp'), ts()]]
    if name: z.append([atom('name'), string(name)])
    z += [[atom('hatch'), atom('edge'), atom(0.5)], [atom('connect_pads'), [atom('clearance'), atom(0)]],
          [atom('min_thickness'), atom(0.25)], [atom('filled_areas_thickness'), atom('no')],
          [atom('keepout'), [atom('tracks'), atom(tracks)], [atom('vias'), atom(vias)], [atom('pads'), atom(pads)], [atom('copperpour'), atom(pour)], [atom('footprints'), atom(footprints)]],
          [atom('fill'), [atom('thermal_gap'), atom(0.5)], [atom('thermal_bridge_width'), atom(0.5)]], poly(pts)]
    return z

def main():
    root = parse(SOURCE_FILE.read_text())
    gnd = next(n[1].raw for n in children(root, 'net') if n[2].value == 'GND')
    keep = []
    removed = {'copper': 0, 'zone': 0, 'edge': 0, 'fp': 0}
    for it in root:
        if isinstance(it, list):
            t = tag(it)
            if t in ('segment', 'via', 'arc'): removed['copper'] += 1; continue
            if t == 'zone': removed['zone'] += 1; continue
            if t.startswith('gr_') and child(it, 'layer') and child(it, 'layer')[1].value == 'Edge.Cuts': removed['edge'] += 1; continue
            if t == 'footprint' and ref_of(it) in plan.DELETE: removed['fp'] += 1; continue
        keep.append(it)
    root[:] = keep
    placed = set()
    for fp in children(root, 'footprint'):
        ref = ref_of(fp)
        if ref not in plan.P: raise SystemExit(f'no plan for {ref}')
        x, y, rot, side = plan.P[ref]
        set_pose(fp, x, y, float(rot), side)
        placed.add(ref)
    missing = set(plan.P) - placed
    if missing: raise SystemExit(f'plan refs not on board: {missing}')
    cu = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
    new = outline()
    new += [gnd_zone(l, gnd) for l in cu]
    ax0, ay0, ax1, ay1 = plan.ANT
    new.append(keepout(cu, rect(ax0, ay0, ax1, ay1), 'not_allowed', 'not_allowed', 'not_allowed', 'not_allowed', 'allowed', 'ESP32 antenna keepout'))
    for ref in ('CT1', 'CT2', 'CT3', 'CT4'):
        x, y, _, _ = plan.P[ref]
        for l in cu: new.append(keepout([l], rect(x - 2, y - 2, x + 2, y + 2), 'allowed', 'not_allowed', 'allowed', 'allowed', 'allowed'))
    for ref in ('MH1', 'MH3'):
        x, y, _, _ = plan.P[ref]
        for l in ('F.Cu', 'B.Cu'): new.append(keepout([l], rect(x - 1.75, y - 1.75, x + 1.75, y + 1.75), 'not_allowed', 'not_allowed', 'allowed', 'not_allowed', 'allowed'))
    root += new
    BOARD_FILE.write_text(dump(root) + '\n')
    print('removed', removed, 'placed', len(placed), 'added', len(new))

if __name__ == '__main__':
    main()
