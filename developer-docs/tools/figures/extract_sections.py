"""Extract 2D section and projection geometry from the device CAD for the docs drawings.

Run with FreeCAD's console:
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(compile(open('extract_sections.py').read(), 'extract_sections.py', 'exec'), {'__file__': 'extract_sections.py'})"
Writes developer-docs/.cache/figures/drawings/geom.json. Coordinates are device-frame mm.
"""
import os, sys, json, math, traceback
import FreeCAD as App, Part
import TechDraw


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MECH = os.path.join(os.environ.get('COMPASS_DESIGN_ROOT', REPO), 'hardware/pcb/evt1/one-board/mech')
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), '.cache', 'figures', 'drawings')
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, MECH)
from compass_datums import pcb_matrix, SWITCHES
V = App.Vector
log = open(os.path.join(OUT, 'extract.log'), 'w', buffering=1)

def read(name):
    s = Part.Shape(); s.read(os.path.join(MECH, name)); return s

def pts_of(edge, defl=0.004):
    try:
        if isinstance(edge.Curve, Part.Line):
            return [edge.Vertexes[0].Point, edge.Vertexes[-1].Point]
    except Exception:
        pass
    return edge.discretize(Deflection=defl)

def loops_of_slice(shape, normal, d, axes):
    """Closed section loops of `shape` cut by the plane normal.p = d, mapped to 2D by `axes`."""
    out = []
    for so in (shape.Solids or [shape]):
        try:
            wires = so.slice(normal, d)
        except Exception as e:
            log.write('slice failed %s\n' % e); continue
        for w in wires:
            try:
                pts = w.discretize(Deflection=0.004)
            except Exception:
                pts = [v.Point for v in w.OrderedVertexes]
            out.append([axes(p) for p in pts])
    return out

def proj_edges(shape, direction, axes, which=(0, 1, 3)):
    """Visible edges (hard, smooth, outline) of `shape` viewed from `direction`, as 2D polylines."""
    r = TechDraw.projectEx(shape, direction)
    out = []
    for i in which:
        c = r[i]
        if c is None or c.isNull():
            continue
        for e in c.Edges:
            out.append([axes(p) for p in pts_of(e)])
    return out

def half(shape, keep_below_z=0.0):
    box = Part.makeBox(400, 400, 200, V(-200, -200, keep_below_z - 200))
    return shape.common(box)

geom = {}
try:
    body = read('MetalBody.step'); cap = read('MotorThermistorCap.step'); nut = read('ThinRearNut.step')
    oring = read('CapFaceSeal.step'); tray = read('FlangeTray.step'); cover = read('RearCover.step')
    skin = read('FlangeSkin.step'); plunger = read('ButtonPlunger.step')
    cradle = read('InternalCradle.step'); guide = read('CradleWireGuide.step')
    internals = read('Internals.step')
    pcb = read('compass-one-board.step'); pcb = pcb.transformGeometry(pcb_matrix()) if False else pcb.transformShape(pcb_matrix(), True) or pcb
    # transformShape returns None and acts in place in FreeCAD; keep the placed copy
    log.write('loaded\n')
    XY = lambda p: (round(p.x, 4), round(p.y, 4))           # section plane Z = 0: (X radial, Y axial)
    # ---- metal parts: section through the axis (Z = 0) + visible edges of the far half
    for name, sh in (('body', body), ('cap', cap), ('nut', nut), ('oring', oring)):
        geom[name + '_section'] = {'loops': loops_of_slice(sh, V(0, 0, 1), 0.0, XY),
                                   'edges': proj_edges(half(sh), V(0, 0, 1), XY)}
        log.write('%s section %d loops\n' % (name, len(geom[name + '_section']['loops'])))
    # body: the same through the collar flats (plane X = 0 shows the 18.4 AF)
    YZ = lambda p: (round(p.z, 4), round(p.y, 4))
    geom['body_section_x0'] = {'loops': loops_of_slice(body, V(1, 0, 0), 0.0, YZ)}
    # end views along the axis. Viewer at -Y (rear end): TechDraw gives (x, y) = (-Z, X); store (X, Z).
    RE = lambda p: (round(p.y, 4), round(-p.x, 4))
    geom['body_rear_view'] = {'edges': proj_edges(body, V(0, -1, 0), RE)}
    geom['cap_rear_view'] = {'edges': proj_edges(cap, V(0, -1, 0), RE)}
    geom['nut_view'] = {'edges': proj_edges(nut, V(0, -1, 0), RE)}
    # Viewer at +Y (front, nose end): TechDraw gives (x, y) = (Z, X); store (X, Z) as seen from the front.
    FR = lambda p: (round(p.y, 4), round(p.x, 4))
    geom['body_front_view'] = {'edges': proj_edges(body, V(0, 1, 0), FR)}
    # ---- whole-device section at Z = 0 for the seals page (each part separately)
    parts = {'body': body, 'cap': cap, 'nut': nut, 'oring': oring, 'tray': tray, 'cover': cover, 'skin': skin,
             'cradle': cradle, 'guide': guide}
    for i, (x, z) in enumerate(SWITCHES):
        p = plunger.copy(); p.translate(V(x - SWITCHES[0][0], 0, z - SWITCHES[0][1])); parts['plunger%d' % (i + 1)] = p
    dev = {}
    for k, sh in parts.items():
        dev[k] = {'loops': loops_of_slice(sh, V(0, 0, 1), 0.0, XY)}
    # internals: classify solids by their position (pack, motor, potting, NTC, wires, plugs)
    internal_loops = {}
    for so in internals.Solids:
        bb = so.BoundBox
        if bb.ZMin > 0 or bb.ZMax < 0:
            continue
        if bb.XLength > 20 and bb.YLength > 30: k = 'pack'
        elif bb.YMin > 66 and bb.XLength > 10: k = 'motor'
        elif bb.YMin > 85 and bb.XLength < 3: k = 'tip'
        elif bb.YMin > 80 and bb.XLength < 3: k = 'tip'
        else: k = 'wire'
        internal_loops.setdefault(k, []).extend(loops_of_slice(so, V(0, 0, 1), 0.0, XY))
    for k, v in internal_loops.items():
        dev['int_' + k] = {'loops': v}
    # PCB: the board and the parts crossing the section planes
    board_loops, comp_loops = [], []
    for so in pcb.Solids:
        bb = so.BoundBox
        if bb.ZMin > 0.001 or bb.ZMax < -0.001:
            continue
        l = loops_of_slice(so, V(0, 0, 1), 0.0, XY)
        (board_loops if bb.XLength > 40 else comp_loops).extend(l)
    dev['pcb_board'] = {'loops': board_loops}; dev['pcb_parts'] = {'loops': comp_loops}
    geom['device_z0'] = dev
    # contact row section at Z = -7.5 (through CT1..CT4)
    cz = -7.5
    row = {}
    for k in ('cover', 'skin', 'tray'):
        row[k] = {'loops': loops_of_slice(parts[k], V(0, 0, 1), cz, XY)}
    bl, cl = [], []
    for so in pcb.Solids:
        bb = so.BoundBox
        if bb.ZMin > cz + 0.001 or bb.ZMax < cz - 0.001:
            continue
        l = loops_of_slice(so, V(0, 0, 1), cz, XY)
        (bl if bb.XLength > 40 else cl).extend(l)
    row['pcb_board'] = {'loops': bl}; row['pcb_parts'] = {'loops': cl}
    geom['device_contacts'] = row
    # tip sensor: section through the drill (Z = 0 passes through X 7.8)
    json.dump(geom, open(os.path.join(OUT, 'geom.json'), 'w'))
    log.write('OK\n')
except Exception:
    log.write(traceback.format_exc())
log.close()
