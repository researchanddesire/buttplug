"""Dock figures for the docs. Run: blender -b --python render_dock.py -- <shot> [preview]
Writes developer-docs/.cache/figures/raw/dock-<shot>.png (+ .json anchors)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_lib as R, dock_common as DC
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SHOT = argv[0] if argv else 'hero'
PREVIEW = 'preview' in argv
RAW = os.path.join(R.CACHE, 'raw'); os.makedirs(RAW, exist_ok=True)
MM = R.MM

def setup(w=1600, h=1000, samples=64):
    if PREVIEW:
        w, h, samples = w // 2, h // 2, 16
    R.reset(width=w, height=h, samples=samples)

def out(name):
    return os.path.join(RAW, 'dock-' + name + ('-preview' if PREVIEW else '') + '.png')

def P(x, y, z):
    return Vector((x, y, z)) * MM

def light_and_frame(direction, lens=70, margin=0.07, margin_x=None, objs=None):
    vis = objs or R.visible_meshes()
    lo, hi = R.world_bbox(vis)
    R.studio_lights((lo + hi) / 2, (hi - lo).length, power=0.22)
    cam = R.camera(direction, lens=lens); R.frame_camera(cam, objs=vis, margin=margin, margin_x=margin_x)
    return lo, hi

BASE_SHELL = ['LowerShellInstance']
MAIN = ['USBBoardAssembly', 'MainBoardScrew']
CONTACT = ['ContactCarrierInstance', 'ContactRetainerInstance', 'ContactPogo', 'ContactMagnet', 'PinBoardAssembly',
           'ContactRetainerScrew', 'ContactFootScrew']
UVBASE = ['UVBaseBoardAssembly', 'BaseUVThermalModuleInstance', 'LowerUVScrew', 'J401 to J621']
LINER = ['LowerChamberInstance', 'ChamberScrew']
HALL = ['Left Hall sensor station', 'Right Hall sensor station']
HARNESS = ['J102 to J94']
SEAT = ['DeviceSeatingModuleInstance', 'FrontClosureLowerContentsInstance']
HINGE = ['CustomHingePinInstance', 'HingeRetainingWasherInstance', 'HingeRetainingScrew', 'J201 to J301']
LID_OUT = ['UpperShellInstance', 'DockButton', 'ScallopedBezelInstance', 'BezelScrew']
LID_IN = ['DockLCDInstance', 'LCDRetentionModuleInstance', 'LCDSocketTrialShimsInstance', 'UIBoardAssembly', 'UIBoardScrew',
          'Left captive Hall magnet', 'Right captive Hall magnet', 'UVLidBoardAssembly', 'LidUVThermalModuleInstance', 'UpperUVScrew',
          'UpperChamberInstance', 'UpperChamberScrew', 'FrontClosureUpperContentsInstance']

def g(parts, *groups):
    return DC.select(parts, groups=[x for grp in groups for x in grp])

# ---------------------------------------------------------------- views
def shot_hero():
    setup(); parts, hinge = DC.load()
    lo, hi = light_and_frame((0.75, -1.3, 0.72), lens=70)
    a = {'screen': P(0, 87, 68.8), 'left': P(-22, 53, 73), 'center': P(0, 53, 73), 'right': P(22, 53, 73),
         'usb': P(0, -6.0, 6.0), 'lid': P(55, 40, 60), 'base': P(60, 20, 20), 'latch': P(0, -8.0, 40)}
    R.render(out('hero'), floor_z=lo.z, anchors=a)

def shot_open():
    setup(); parts, hinge = DC.load(); DC.open_lid(hinge, 105)
    lo, hi = light_and_frame((0.45, -1.2, 1.25), lens=70)
    R.render(out('open'), floor_z=0.0, anchors={'contacts': P(-7, 23.2, 42), 'seat': P(0, 60, 13.5), 'hinge': P(-30, 164.4, 40.15)})

def shot_base_inside():
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE, HALL, HARNESS, HINGE[:3]))
    lo, hi = light_and_frame((0.5, -1.05, 1.35), lens=70)
    a = {'main': P(20, 40, 6.4), 'usb': P(0, -4, 7), 'carrier': P(-18, 18, 46), 'pogo': P(-10, 23.2, 42), 'uvbase': P(30, 110, 13.2),
         'spreader': P(-40, 120, 11.8), 'hall': P(-50.5, 32, 34.8), 'harness': P(-30, 40, 12), 'j401': P(27, 112, 9)}
    R.render(out('base-inside'), floor_z=0.0, anchors=a)

def shot_lid_inside():
    setup(); parts, hinge = DC.load(); DC.open_lid(hinge, 180)
    DC.show_only(parts, [p['obj'] for p in parts if p['side'] == 'LidAssembly' and not p['group'].startswith('UpperChamber')])
    lo, hi = light_and_frame((0.45, -1.0, 1.5), lens=70)
    R.render(out('lid-inside'), floor_z=lo.z, anchors={'ui': P(-20, 268.8, 21.3), 'uv': P(40, 198.8, 25.0), 'magnet': P(-50.5, 291.3, 43.9), 'lcd': P(0, 220.3, 15.9)})

def shot_contact_head():
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, CONTACT, HARNESS, MAIN, ['DeviceSeatingModuleInstance']))
    vis = g(parts, CONTACT)
    lo, hi = light_and_frame((0.55, 1.0, 0.55), lens=85, objs=vis, margin=0.12)
    a = {'pogo': P(-16, 23.2, 42), 'carrier': P(-40, 18, 40), 'retainer': P(-30, 9, 30), 'pinboard': P(-6, 18.3, 44),
         'magnet': P(-14.5, 22.0, 24), 'foot': P(-30, 16, 6), 'wires': P(-10, 12, 40)}
    R.render(out('contact-head'), floor_z=lo.z, anchors=a)

# ---------------------------------------------------------------- assembly steps (base)
def shot_d1():   # Main board into the lower shell
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN))
    DC.move(g(parts, ['USBBoardAssembly']), (0, 0, 52)); DC.move(g(parts, ['MainBoardScrew']), (0, 0, 70))
    lo, hi = light_and_frame((0.45, -1.1, 1.0), lens=70)
    R.render(out('d1'), floor_z=0.0, anchors={'main': P(20, 40, 58.4), 'screws': P(44, 55.7, 76), 'usb': P(0, -4, 59), 'shell': P(60, 120, 30), 'bosses': P(8, 23.5, 5.4)})

def shot_d2():   # contact module from below the shell floor
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN, CONTACT))
    R.ghost(g(parts, BASE_SHELL, MAIN), 0.55)
    DC.move(g(parts, CONTACT), (0, 0, 46))
    lo, hi = light_and_frame((0.45, 1.05, 0.9), lens=70, objs=g(parts, CONTACT, ['USBBoardAssembly']), margin=0.1)
    a = {'pogo': P(-16, 23.2, 88), 'carrier': P(-44, 18, 86), 'magnet': P(-14.5, 22.2, 70), 'pinboard': P(-6, 18.3, 90), 'foot': P(-30, 16, 52)}
    R.render(out('d2'), floor_z=lo.z, anchors=a)

def shot_d3():   # base UV module and its harness
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE))
    R.ghost(g(parts, BASE_SHELL, MAIN, CONTACT), 0.55)
    DC.move(g(parts, ['UVBaseBoardAssembly', 'BaseUVThermalModuleInstance']), (0, 0, 22)); DC.move(g(parts, ['LowerUVScrew']), (0, 0, 34))
    lo, hi = light_and_frame((0.45, -1.1, 1.1), lens=70)
    a = {'board': P(30, 110, 35.2), 'leds': P(0, 128, 35.2), 'spreader': P(-40, 120, 22), 'harness': P(27, 112, 9), 'screws': P(45, 132, 46)}
    R.render(out('d3'), floor_z=0.0, anchors=a)

def shot_d4():   # lower liner
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE, LINER))
    R.ghost(g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE), 0.55)
    DC.move(g(parts, ['LowerChamberInstance']), (0, 0, 40)); DC.move(g(parts, ['ChamberScrew']), (0, 0, 58))
    lo, hi = light_and_frame((0.45, -1.1, 1.0), lens=70)
    R.render(out('d4'), floor_z=0.0, anchors={'liner': P(55, 100, 70), 'screws': P(52, 115, 72), 'pocket': P(0, 89, 52)})

def shot_d5():   # contact harness under the seated liner (liner hidden to show the wires)
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE, HARNESS))
    R.ghost(g(parts, BASE_SHELL, UVBASE), 0.6)
    vis = g(parts, CONTACT, HARNESS, ['USBBoardAssembly'])
    lo, hi = light_and_frame((0.35, -1.0, 1.25), lens=70, objs=vis, margin=0.08)
    a = {'j102': P(-20, 52, 8), 'j94': P(-12, 14, 44), 'wires': P(-26, 34, 20)}
    R.render(out('d5'), floor_z=0.0, anchors=a)

def shot_d6():   # Hall stations
    setup(); parts, hinge = DC.load()
    DC.show_only(parts, g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE, LINER, HALL))
    R.ghost(g(parts, BASE_SHELL, MAIN, CONTACT, UVBASE, LINER), 0.55)
    DC.move(g(parts, HALL), (0, 0, 16))
    lo, hi = light_and_frame((0.6, -1.0, 1.0), lens=70)
    R.render(out('d6'), floor_z=0.0, anchors={'hallL': P(-50.5, 32, 50.8), 'hallR': P(50.5, 32, 50.8)})

# ---------------------------------------------------------------- assembly steps (lid)
def shot_d7():   # lid outside: bezel and button caps go on from above
    setup(); parts, hinge = DC.load()
    objs = DC.select(parts, groups=['UpperShellInstance', 'DockButton', 'ScallopedBezelInstance'])
    DC.show_only(parts, objs)
    R.ghost(DC.select(parts, groups=['UpperShellInstance']), 0.45)
    DC.move(DC.select(parts, groups=['ScallopedBezelInstance']), (0, 0, 14))
    DC.move(DC.select(parts, groups=['DockButton']), (0, 0, 30))
    lo, hi = light_and_frame((0.5, -1.1, 1.0), lens=70)
    a = {'bezel': P(-38, 70, 84.5), 'caps': P(22, 78, 102), 'springs': P(-22, 78, 92), 'lid': P(55, 120, 60)}
    R.render(out('d7'), floor_z=lo.z, anchors=a)

def shot_d8():   # lid inside: LCD, UI board on shims, magnets, UV lid module (upper liner off)
    setup(); parts, hinge = DC.load(); DC.open_lid(hinge, 180)
    lid = [p['obj'] for p in parts if p['side'] == 'LidAssembly' and not p['group'].startswith(('UpperChamber', 'FrontClosureUpper'))]
    DC.show_only(parts, lid)
    R.ghost(DC.select(parts, groups=['UpperShellInstance', 'ScallopedBezelInstance', 'DockButton', 'BezelScrew']), 0.45)
    lo, hi = light_and_frame((0.45, -1.0, 1.4), lens=70)
    R.render(out('d8'), floor_z=lo.z, anchors={'ui': P(-20, 268.8, 21.3), 'uv': P(40, 198.8, 25.0), 'magnet': P(-50.5, 291.3, 43.9), 'lcd': P(0, 220.3, 15.9)})

def shot_d9():   # hinge pin, washer and screw; flex through the hinge
    setup(); parts, hinge = DC.load(); DC.open_lid(hinge, 70)
    pin = DC.select(parts, groups=['CustomHingePinInstance'])
    DC.move(pin, (-45, 0, 0))
    lo, hi = light_and_frame((-0.9, 1.0, 0.75), lens=70)
    R.render(out('d9'), floor_z=0.0, anchors={'pin': P(-75, 164.4, 40.15), 'flex': P(0, 158, 30), 'washer': P(36.5, 164.4, 40.15)})

SHOTS = {k[5:]: v for k, v in globals().items() if k.startswith('shot_')}
SHOTS[SHOT]()
