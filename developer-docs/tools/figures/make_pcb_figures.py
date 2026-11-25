"""PCB figures: kicad-cli renders of both faces with labelled parts.

Run (system python): python3 make_pcb_figures.py
Renders hardware/pcb/evt1/one-board/compass-one-board.kicad_pcb (read only) into
.cache/figures/pcb/ and writes assembly-docs/assets/pcb/pcb-front.jpg, pcb-back.jpg, pcb-angle.jpg.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import annotate, pngutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
BOARD = os.path.join(os.environ.get('COMPASS_DESIGN_ROOT', REPO), 'hardware/pcb/evt1/one-board/compass-one-board.kicad_pcb')
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
CACHE = os.path.join(DOCS, '.cache', 'figures', 'pcb')
OUT = os.path.join(os.path.dirname(DOCS), 'assembly-docs', 'assets', 'pcb')

os.makedirs(CACHE, exist_ok=True); os.makedirs(OUT, exist_ok=True)
KX0, KX1, KY0, KY1 = 74.0, 126.0, 90.0, 110.0
QUALITY = 'basic'          # board outline (KiCad mm)


def render(side, name, extra=(), zoom=2.0):
    path = os.path.join(CACHE, name)
    subprocess.run(['kicad-cli', 'pcb', 'render', '--side', side, '--quality', QUALITY, '--width', '2400', '--height', '1100',
                    '--background', 'transparent', '--zoom', str(zoom), '--light-camera', '0.25'] + list(extra) + ['-o', path, BOARD],
                   check=True, capture_output=True)
    return path


def anchors(path, pts, mirror=False):
    x0, y0, x1, y1 = pngutil.alpha_bbox(path)
    sx = (x1 - x0) / (KX1 - KX0); sy = (y1 - y0) / (KY1 - KY0)
    out = {}
    for k, (kx, ky) in pts.items():
        px = (x1 - (kx - KX0) * sx) if mirror else (x0 + (kx - KX0) * sx)
        out[k] = [round(px, 1), round(y0 + (ky - KY0) * sy, 1)]
    import struct
    w, h = struct.unpack('>II', open(path, 'rb').read(24)[16:24])
    json.dump({'width': w, 'height': h, 'anchors': out}, open(path + '.json', 'w'), indent=1)
    return (x0, y0, x1, y1)


front = render('top', 'front.png')
bb = anchors(front, {
    'sw1': (83.0, 100.0), 'sw2': (91.0, 100.0), 'ct1': (102.0, 107.5), 'ct2': (108.0, 107.5), 'ct3': (114.0, 107.5), 'ct4': (120.0, 107.5),
    'u1': (116.5, 100.5), 'u7': (90.5, 104.4), 'u5': (103.5, 91.9), 'u81': (81.5, 92.2), 'u75': (111.0, 103.3), 'jp1': (111.8, 92.5),
    'f1': (121.0, 101.9), 'ant': (76.4, 100.0), 'u71': (98.9, 92.2)})
pad = 330
crop = (bb[0] - pad, bb[1] - 170, bb[2] + pad, bb[3] + 170)
annotate.compose(front, os.path.join(OUT, 'pcb-front.jpg'), crop=crop, labels=[
    {'anchor': 'u81', 'text': 'U81 compass + accelerometer', 'side': 'top'},
    {'anchor': 'u5', 'text': 'U5 motor driver', 'side': 'top'},
    {'anchor': 'jp1', 'text': 'JP1 charge enable', 'side': 'top'},
    {'anchor': 'ant', 'text': 'Antenna keepout', 'side': 'left'},
    {'anchor': 'sw1', 'text': 'SW1 power', 'side': 'left'},
    {'anchor': 'sw2', 'text': 'SW2 mode', 'side': 'left'},
    {'anchor': 'u7', 'text': 'U7 16-bit ADC', 'side': 'left'},
    {'anchor': 'u1', 'text': 'U1 charger', 'side': 'right'},
    {'anchor': 'f1', 'text': 'F1 fuse', 'side': 'right'},
    {'anchor': 'u75', 'text': 'U75 USB ESD', 'side': 'right'},
    {'anchor': 'ct1', 'text': 'GND', 'side': 'bottom'},
    {'anchor': 'ct2', 'text': 'D−', 'side': 'bottom'},
    {'anchor': 'ct3', 'text': 'D+', 'side': 'bottom'},
    {'anchor': 'ct4', 'text': '5 V', 'side': 'bottom'},
], font_px=34)

back = render('bottom', 'back.png')
bb = anchors(back, {
    'u6': (88.5, 100.0), 'ant': (77.5, 100.0), 'j4': (98.9, 92.6), 'j3': (106.7, 92.6), 'j2': (113.0, 92.6), 'j5': (119.35, 92.6),
    'u2': (116.0, 98.75), 'u3': (104.0, 98.75), 'l1': (116.0, 103.1), 'l2': (104.0, 103.1), 'u9': (123.8, 100.5), 'ct': (108.0, 107.5)}, mirror=True)
crop = (bb[0] - pad, bb[1] - 170, bb[2] + pad, bb[3] + 170)
annotate.compose(back, os.path.join(OUT, 'pcb-back.jpg'), crop=crop, labels=[
    {'anchor': 'j5', 'text': 'J5 tip sensor', 'side': 'top'},
    {'anchor': 'j2', 'text': 'J2 battery', 'side': 'top'},
    {'anchor': 'j3', 'text': 'J3 motor', 'side': 'top'},
    {'anchor': 'j4', 'text': 'J4 service', 'side': 'top'},
    {'anchor': 'u9', 'text': 'U9 supervisor', 'side': 'left'},
    {'anchor': 'u2', 'text': 'U2 + L1: 3.3 V buck-boost', 'side': 'left'},
    {'anchor': 'u3', 'text': 'U3 + L2: 3.7 V motor supply', 'side': 'bottom'},
    {'anchor': 'u6', 'text': 'U6 ESP32-C3 module', 'side': 'right'},
    {'anchor': 'ant', 'text': 'Antenna', 'side': 'right'},
], font_px=34)

angle = render('top', 'angle.png', ['--perspective', '--rotate', '-38,0,18'], zoom=1.25)
x0, y0, x1, y1 = pngutil.alpha_bbox(angle, thresh=30)
annotate.compose(angle, os.path.join(OUT, 'pcb-angle.jpg'), crop=(max(0, x0 - 60), max(0, y0 - 60), x1 + 60, y1 + 60))
print('done')
