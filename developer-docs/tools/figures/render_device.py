"""Device figures for the docs. Run: blender -b --python render_device.py -- <shot> [preview]
Writes developer-docs/.cache/figures/raw/<shot>.png and <shot>.png.json (anchor pixels)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_lib as R, device_common as D
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SHOT = argv[0] if argv else 'hero'
PREVIEW = 'preview' in argv
RAW = os.path.join(R.CACHE, 'raw'); os.makedirs(RAW, exist_ok=True)

# Device datums (mm, device frame: Y axis to the tip, Z up, X across the flange; dock face toward -Y)
CONTACTS = [(2.0, -7.5), (8.0, -7.5), (14.0, -7.5), (20.0, -7.5)]      # GND, D-, D+, 5 V
SWITCHES = [(-17.0, 0.0), (-9.0, 0.0)]                                  # SW1 power, SW2 mode
SKIN_FACE_Y, COVER_OUT_Y, BOARD_F_Y, BOARD_B_Y = -25.9, -24.6, -21.0, -20.0
HORIZONTAL = (0, 0, -90)   # device axis along world +X (tip right), device Z up
STANDING = (90, 0, 0)      # tip up, dock face down

def setup(w=1600, h=1000, samples=128, **kw):
    if PREVIEW:
        w, h, samples = w // 2, h // 2, 16
    R.reset(width=w, height=h, samples=samples, **kw)

def lights_for(objs=None, power=0.25):
    lo, hi = R.world_bbox(objs or R.visible_meshes())
    R.studio_lights((lo + hi) / 2, max((hi - lo).length, 0.05), power=power)
    return lo, hi

def P(frame, p):   # device mm -> world
    return frame @ (Vector(p) * R.MM)

def only(parts, keys):
    """Hide everything except the given part keys."""
    keep = set()
    for k in keys:
        for o in parts.get(k, []):
            keep.add(o)
    for k, v in parts.items():
        for o in v:
            o.hide_render = o.hide_viewport = o not in keep

def show(parts, keys, hidden=False):
    for k in keys:
        for o in parts.get(k, []):
            o.hide_render = o.hide_viewport = hidden

def ghost(parts, keys, amount=0.72):
    for k in keys:
        R.ghost(parts.get(k, []), amount)

def move(parts, keys, vec, frame):
    for k in keys:
        R.offset(parts.get(k, []), vec, frame)

def out(name):
    return os.path.join(RAW, name + ('-preview' if PREVIEW else '') + '.png')

INT_ALL = ['int_pack', 'int_motor', 'int_tip', 'int_plugs', 'int_wires', 'int_pads']

# ---------------------------------------------------------------- product views
def shot_hero():
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=STANDING)
    only(parts, ['body', 'cap', 'skin'])
    lo, hi = lights_for()
    cam = R.camera((1.0, -1.7, 0.55), lens=85); R.frame_camera(cam, margin=0.1)
    R.render(out('hero'), floor_z=lo.z)

def shot_dockface():
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=(0, 0, 0))
    only(parts, ['body', 'cap', 'skin', 'pcb'])
    lo, hi = lights_for()
    cam = R.camera((0.55, -1.0, 0.42), lens=100)
    R.frame_camera(cam, margin=0.06, margin_x=0.2)
    a = {}
    for i, (x, z) in enumerate(CONTACTS):
        a['ct%d' % (i + 1)] = P(f, (x, -24.13, z))
    a['sw1'] = P(f, (SWITCHES[0][0], SKIN_FACE_Y - 0.5, 0)); a['sw2'] = P(f, (SWITCHES[1][0], SKIN_FACE_Y - 0.5, 0))
    a['arrow'] = P(f, (-2.0, SKIN_FACE_Y - 0.4, 9.5)); a['icon'] = P(f, (19.0, SKIN_FACE_Y, 8.5))
    a['skin'] = P(f, (-24.0, SKIN_FACE_Y + 2, -15.0)); a['body'] = P(f, (14.0, 45.0, 6.0))
    a['window'] = P(f, (11.0, COVER_OUT_Y - 0.2, -11.9))
    R.render(out('dockface'), anchors=a)

def shot_exploded():
    setup(1800, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL)
    show(parts, ['int_wires', 'int_plugs', 'int_pads', 'int_tip'], hidden=True)
    ex = {  # part keys -> offset (mm, device frame)
        'skin': (0, -128, 0), 'screws_cover': (0, -96, 0), 'cover': (0, -84, 0), 'button1': (0, -70, 0), 'button2': (0, -70, 0),
        'pcb': (0, -56, 0), 'screws_pcb': (0, -44, 0),
        'nut': (0, -32, 0), 'tray': (0, -12, 0),
        'cradle': (0, 6, 52), 'int_pack': (0, 6, 52), 'guide': (0, 6, 68), 'screws_guide': (0, 6, 76),
        'int_motor': (0, 30, 52), 'oring': (0, 16, 0), 'cap': (0, 34, 0),
    }
    for k, v in ex.items():
        move(parts, [k], v, f)
    lo, hi = lights_for()
    cam = R.camera((-0.22, -1.0, 0.45), lens=100)
    R.frame_camera(cam, margin=0.06)
    def A(p, k):
        o = ex.get(k, (0, 0, 0)); return P(f, (p[0] + o[0], p[1] + o[1], p[2] + o[2]))
    a = {
        'skin': A((-29.6, -18, 0), 'skin'), 'cover': A((0, -24.6, -14), 'cover'), 'buttons': A((-17, -24.8, 0), 'button1'),
        'screws_cover': A((20, -24.6, -13), 'screws_cover'), 'pcb': A((-20, -21, -8), 'pcb'), 'screws_pcb': A((24, -19.5, 8.3), 'screws_pcb'),
        'nut': A((0, -12, -12), 'nut'), 'tray': A((-27, -15, -10), 'tray'), 'body': A((0, 30, -15), 'body'),
        'cradle': A((10, 40, -4), 'cradle'), 'pack': A((-9, 50, 0), 'int_pack'), 'guide': A((0, 18, 4.5), 'guide'),
        'screws_guide': A((-8, 66.7, 5.6), 'screws_guide'), 'motor': A((0, 80, 5.5), 'int_motor'),
        'oring': A((0, 63.6, -16.5), 'oring'), 'cap': A((0, 80, -10), 'cap'),
    }
    R.render(out('exploded'), floor_z=lo.z, anchors=a)

def shot_cutaway():
    setup(1800, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL, cut=True, whole=True, screws=True)
    # cut enclosure + whole internals/board
    only(parts, ['body_cut', 'cap_cut', 'nut_cut', 'tray_cut', 'cover_cut', 'skin_cut', 'button1_cut', 'button2_cut', 'oring_cut',
                 'pcb', 'cradle', 'guide', 'screws_guide', 'screws_pcb'] + INT_ALL)
    lo, hi = lights_for()
    cam = R.camera((0.18, -0.62, 1.0), lens=70)
    R.frame_camera(cam, margin=0.06, margin_x=0.16)
    a = {
        'cap': P(f, (0, 96, -0.5)), 'motor': P(f, (0, 80, 5.55)), 'tip': P(f, (7.8, 89.1, 0.6)), 'oring': P(f, (16.5, 63.6, 0)),
        'thread': P(f, (14.6, 60.5, 0)), 'pack': P(f, (-4, 48, 2.2)), 'cradle': P(f, (10.0, 64.0, -2.0)), 'guide': P(f, (0, 45, 4.7)),
        'body': P(f, (-15.5, 45, 0)), 'neck': P(f, (-7.2, 2, 0)), 'wires': P(f, (0.5, 0, 3.4)), 'nut': P(f, (-12, -12, 0)),
        'tray': P(f, (-27.5, -14, 0)), 'pcb': P(f, (-15, -20.5, 3)), 'cover': P(f, (-27, -23.8, 0)), 'skin': P(f, (-29.5, -20, 0)),
        'button': P(f, (-17, -24.8, 0)), 'contacts': P(f, (14, -23.5, -7.5)),
    }
    R.render(out('cutaway'), floor_z=lo.z, anchors=a)

# ---------------------------------------------------------------- assembly steps
def shot_step01():   # tray onto the body stub, then the thin nut
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL)
    only(parts, ['body', 'tray', 'nut'])
    move(parts, ['tray'], (0, -14, 0), f); move(parts, ['nut'], (0, -34, 0), f)
    R.dashed((0, -52, 0), (0, -9, 0), f)
    arrows = R.arrow((0, -46, 19), (0, -37, 19), f) + R.arrow((0, -27, 19), (0, -15, 19), f)
    lo, hi = lights_for()
    cam = R.camera((-0.75, -1.0, 0.55), lens=85); R.frame_camera(cam, margin=0.08, margin_x=0.15)
    a = {'tray': P(f, (-26, -22, -8)), 'nut': P(f, (-10, -48, -6)), 'stub': P(f, (0, -13, 9)), 'collar': P(f, (0, -9, -10)), 'body': P(f, (0, 30, -16)),
         'socket': P(f, (9.3, -26, 3))}
    R.render(out('step01'), floor_z=lo.z, anchors=a)

def shot_step02():   # motor and tip sensor into the nose cap (cap shown cut)
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL, cut=True, whole=True, screws=False)
    only(parts, ['cap_cut', 'int_motor', 'int_tip'])
    move(parts, ['int_motor'], (0, -34, 0), f)
    arrows = R.arrow((0, 36, 9), (0, 56, 9), f)
    lo, hi = lights_for()
    cam = R.camera((0.25, -0.6, 1.0), lens=85); R.frame_camera(cam, margin=0.08, margin_x=0.16)
    a = {'cap': P(f, (14, 85, 0)), 'pocket': P(f, (0, 70, 5.55)), 'motor': P(f, (0, 45, 5.5)), 'tip': P(f, (7.8, 89.1, 0.6)), 'stop': P(f, (-5.5, 93.3, 0))}
    R.render(out('step02'), floor_z=lo.z, anchors=a)

def shot_step03():   # battery into the cradle, then the wire guide and its screws
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL)
    only(parts, ['cradle', 'int_pack', 'int_pads', 'guide', 'screws_guide'])
    move(parts, ['guide'], (0, 0, 16), f); move(parts, ['screws_guide'], (0, 0, 26), f)
    arrows = []
    for (x, y) in [(-5.0, 29.8), (5.0, 29.8), (-8.0, 66.7), (8.0, 66.7)]:
        arrows += R.arrow((x, y, 27.5), (x, y, 23.0), f, shaft_mm=0.35, head_mm=1.0)
    arrows += R.arrow((14, 48, 16), (14, 48, 7), f)
    lo, hi = lights_for()
    cam = R.camera((0.35, -1.0, 0.85), lens=85); R.frame_camera(cam, margin=0.08, margin_x=0.16)
    a = {'cradle': P(f, (10, 25, -2)), 'pack': P(f, (-10.5, 50, 0)), 'guide': P(f, (0, 10, 19.5)), 'screws': P(f, (8, 66.7, 31.5)),
         'stop': P(f, (0, 66.8, 1)), 'leads': P(f, (-1.1, 31.0, -1.0))}
    R.render(out('step03'), floor_z=lo.z, anchors=a)

def shot_step04():   # module into the body through the nose; O-ring into the gland
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL, cut=True, whole=True)
    only(parts, ['body_cut', 'tray_cut', 'nut_cut', 'cradle', 'guide', 'screws_guide', 'int_pack', 'int_pads', 'oring'])
    ghost(parts, ['body_cut', 'tray_cut', 'nut_cut'], 0.6)
    move(parts, ['cradle', 'guide', 'screws_guide', 'int_pack', 'int_pads'], (0, 42, 0), f)
    move(parts, ['oring'], (0, 14, 0), f)
    arrows = R.arrow((0, 122, 12), (0, 100, 12), f) + R.arrow((24, 88, 0), (24, 70, 0), f)
    lo, hi = lights_for()
    cam = R.camera((0.2, -0.7, 1.0), lens=70); R.frame_camera(cam, margin=0.07, margin_x=0.12)
    a = {'module': P(f, (-10, 92, 0)), 'oring': P(f, (0, 77.6, -16.5)), 'gland': P(f, (16.5, 63.8, 0)), 'body': P(f, (-15, 40, 0)),
         'neck': P(f, (-7, 2, 0)), 'tray': P(f, (-27, -14, 0))}
    R.render(out('step04'), floor_z=lo.z, anchors=a)

def shot_step05():   # thread the cap on (wires through the neck)
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL)
    only(parts, ['body', 'tray', 'nut', 'cap', 'oring'])
    ghost(parts, ['body', 'tray', 'nut'], 0.55)
    move(parts, ['cap'], (0, 22, 0), f)
    arrows = R.arrow((0, 112, 19), (0, 96, 19), f)
    lo, hi = lights_for()
    cam = R.camera((0.6, -1.0, 0.55), lens=85); R.frame_camera(cam, margin=0.08, margin_x=0.12)
    a = {'cap': P(f, (0, 100, -12)), 'oring': P(f, (12, 63.6, -11.7)), 'thread': P(f, (0, 82, 14.2))}
    R.render(out('step05'), floor_z=lo.z, anchors=a)

def shot_step06():   # plungers into the cover, then the PCB onto the cover bosses
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=STANDING)   # cover outer face down on the bench, look in from above
    only(parts, ['cover', 'button1', 'button2', 'pcb', 'screws_pcb'])
    move(parts, ['pcb'], (0, 14, 0), f); move(parts, ['screws_pcb'], (0, 24, 0), f)
    move(parts, ['button1', 'button2'], (0, 5, 0), f)
    arrows = R.arrow((31, 2, 0), (31, -12, 0), f)
    for (x, z) in [(-4.0, -8.4), (24.0, 8.3)]:
        arrows += R.arrow((x, 12.0, z), (x, 6.5, z), f, shaft_mm=0.35, head_mm=1.0)
    for (x, z) in [(-17.0, 0.0), (-9.0, 0.0)]:
        arrows += R.arrow((x, -11.0, z + 7.0), (x, -16.5, z + 7.0), f, shaft_mm=0.3, head_mm=0.9)
    lo, hi = lights_for()
    cam = R.camera((0.45, -0.8, 1.0), lens=85); R.frame_camera(cam, margin=0.08, margin_x=0.15)
    a = {'cover': P(f, (20, -24, 15.5)), 'plungers': P(f, (-17, -13.5, 2.5)), 'pcb': P(f, (-24, -6, 9.0)), 'screws': P(f, (24, 12.9, 8.3)),
         'esp': P(f, (-12, -3.6, -2)), 'connectors': P(f, (6.7, -3.0, 8.5))}
    R.render(out('step06'), floor_z=lo.z, anchors=a)

def shot_step07():   # connect J2, J3, J5 (flange shown cut so the plugs are visible)
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL, cut=True, whole=True)
    only(parts, ['body_cut', 'tray_cut', 'nut_cut', 'cover_cut', 'button1_cut', 'button2_cut', 'pcb', 'screws_pcb', 'int_plugs', 'int_wires', 'guide', 'cradle'])
    ghost(parts, ['body_cut', 'tray_cut', 'nut_cut', 'cover_cut', 'button1_cut', 'button2_cut', 'guide', 'cradle'], 0.6)
    lo, hi = lights_for()
    cam = R.camera((-0.35, -0.25, 1.0), lens=85)
    R.frame_camera(cam, objs=[o for k in ('pcb', 'int_plugs', 'tray_cut', 'nut_cut') for o in parts[k]], margin=0.08, margin_x=0.18)
    a = {'j2': P(f, (13, -18.5, 12.4)), 'j3': P(f, (6.7, -18.5, 12.4)), 'j5': P(f, (19.35, -18.5, 12.4)), 'j4': P(f, (-1.1, -18.8, 6.4)),
         'pack_wires': P(f, (2, -14.6, -0.8)), 'neck': P(f, (-4, -10, 0))}
    R.render(out('step07'), floor_z=lo.z, anchors=a)

def shot_step08():   # close the flange: cover + PCB into the tray, two M2 x 6 screws
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL)
    only(parts, ['body', 'cap', 'tray', 'nut', 'cover', 'button1', 'button2', 'pcb', 'screws_cover'])
    ghost(parts, ['body', 'cap', 'tray', 'nut'], 0.55)
    move(parts, ['cover', 'button1', 'button2', 'pcb'], (0, -16, 0), f)
    move(parts, ['screws_cover'], (0, -30, 0), f)
    arrows = R.arrow((-30, -44, 0), (-30, -30, 0), f)
    for (x, z) in [(-20.0, 13.0), (20.0, -13.0)]:
        arrows += R.arrow((x, -52, z), (x, -45, z), f, shaft_mm=0.4, head_mm=1.2)
    lo, hi = lights_for()
    cam = R.camera((-1.0, -0.8, 0.65), lens=85)
    R.frame_camera(cam, objs=[o for k in ('tray', 'cover', 'screws_cover', 'pcb', 'body') for o in parts[k]], margin=0.08, margin_x=0.14)
    a = {'cover': P(f, (-28, -41, -8)), 'screws': P(f, (20, -50, -13)), 'tray': P(f, (-28, -16, 8)), 'contacts': P(f, (14, -40.2, -7.5))}
    R.render(out('step08'), floor_z=lo.z, anchors=a)

def shot_step09():   # cast the skin
    setup(1600, 1000)
    roots, parts, f = D.load(frame_rot=HORIZONTAL)
    only(parts, ['body', 'cap', 'skin', 'pcb', 'cover', 'button1', 'button2'])
    lo, hi = lights_for()
    cam = R.camera((-0.75, -1.0, 0.5), lens=85); R.frame_camera(cam, margin=0.08, margin_x=0.15)
    a = {'skin': P(f, (29.6, -16, -8)), 'window': P(f, (11, -24.8, -11.9)), 'domes': P(f, (-17, -26.4, 0)), 'ramp': P(f, (12.5, 1.0, -0.5)),
         'arrow': P(f, (-2, -26.3, 9.5)), 'icon': P(f, (19.0, -25.9, 8.5))}
    R.render(out('step09'), floor_z=lo.z, anchors=a)


# ---------------------------------------------------------------- single parts (mechanical page)
def part_shot(name, keys, direction, rot=HORIZONTAL, lens=85, cut=False, margin=0.1):
    setup(1200, 800, samples=32)
    roots, parts, f = D.load(frame_rot=rot, cut=cut, whole=True)
    only(parts, keys)
    lo, hi = lights_for()
    cam = R.camera(direction, lens=lens); R.frame_camera(cam, margin=margin)
    R.render(out('part-' + name), floor_z=lo.z)

def shot_part_body():    part_shot('body', ['body'], (-0.55, -1.0, 0.5))
def shot_part_cap():     part_shot('cap', ['cap'], (-0.9, -0.8, 0.55))
def shot_part_nut():     part_shot('nut', ['nut'], (-1.0, -0.6, 0.8))
def shot_part_tray():    part_shot('tray', ['tray'], (-1.0, -0.75, 0.75))
def shot_part_cover():   part_shot('cover', ['cover', 'button1', 'button2'], (0.5, -0.8, 1.0), rot=STANDING)
def shot_part_cover_in(): part_shot('cover-inside', ['cover'], (0.5, -0.8, 1.0), rot=(-90, 0, 0))
def shot_part_plunger(): part_shot('plunger', ['button1'], (0.6, -0.9, 0.9), rot=STANDING)
def shot_part_cradle():  part_shot('cradle', ['cradle', 'guide', 'screws_guide'], (0.35, -1.0, 0.85))
def shot_part_skin():    part_shot('skin', ['skin'], (-0.75, -1.0, 0.5))
def shot_part_oring():   part_shot('oring', ['oring'], (0.0, -1.0, 0.9), rot=STANDING)

SHOTS = {k[5:]: v for k, v in globals().items() if k.startswith('shot_')}
if SHOT == 'list':
    print('SHOTS', ' '.join(SHOTS))
else:
    SHOTS[SHOT]()
