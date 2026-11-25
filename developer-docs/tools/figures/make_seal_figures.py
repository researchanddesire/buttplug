"""Colour section diagrams of the device seals (docs figures), from the CAD sections.

Run (system python): python3 make_seal_figures.py   (needs .cache/figures/drawings/geom.json)
Writes developer-docs/docs/assets/seals/*.png (and .svg).
"""
import json, os, math, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drawing_lib as DL
from drawing_lib import Sheet, View

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
G = json.load(open(os.path.join(DOCS, '.cache', 'figures', 'drawings', 'geom.json')))
OUT = os.path.join(DOCS, 'docs', 'assets', 'seals')
os.makedirs(OUT, exist_ok=True)
INK = '/Applications/Inkscape.app/Contents/MacOS/inkscape'
SEC = lambda x, y: (y, -x)      # axis horizontal, tip right, +X down

COL = {  # fill, stroke
    'body': ('#cfd4db', '#59616b'), 'cap': ('#cfd4db', '#59616b'), 'nut': ('#9aa1aa', '#4d545c'),
    'oring': ('#16181b', '#16181b'), 'skin': ('#a27bd0', '#5d3a86'), 'tray': ('#55585f', '#2b2d31'),
    'cover': ('#55585f', '#2b2d31'), 'plunger1': ('#ecebe4', '#6f6f68'), 'plunger2': ('#ecebe4', '#6f6f68'),
    'cradle': ('#e98a3a', '#9a4f12'), 'guide': ('#f3c15a', '#a77a12'), 'int_pack': ('#b9c3cf', '#66717e'),
    'int_motor': ('#6b7078', '#3d4147'), 'int_tip': ('#e7d27c', '#8a7425'), 'int_wire': ('#d2552e', '#8c2f14'),
    'pcb_board': ('#2f8a57', '#1c5535'), 'pcb_parts': ('#6c7178', '#33363a'),
}
ORDER = ['skin', 'tray', 'cover', 'plunger1', 'plunger2', 'pcb_board', 'pcb_parts', 'nut', 'body', 'cap', 'cradle', 'guide',
         'int_pack', 'int_motor', 'int_tip', 'int_wire', 'oring']


def draw_parts(view, data, keys=None, w=0.25):
    for k in ORDER:
        if k not in data or (keys and k not in keys):
            continue
        f, s = COL[k]
        view.section(data[k]['loops'], f, stroke=s, w=w)


def num(S, x, y, n, r=3.0):
    S.circle(x, y, r, fill='#e4572e', sw=0)
    S.text(x, y + r * 0.38, str(n), size=r * 1.15, weight='bold', color='white')


def callout(view, p, n, dx, dy, r=3.0, text=None, anchor='start'):
    S = view.s
    a = view.P(*p); bx, by = a[0] + dx, a[1] + dy
    S.line(a[0], a[1], bx, by, 0.25, color='#333')
    S.circle(a[0], a[1], 0.55, fill='#333', sw=0)
    num(S, bx, by, n, r)
    if text:
        S.text(bx + (r + 1.5 if anchor == 'start' else -(r + 1.5)), by + 1.2, text, size=3.2, anchor=anchor)


def label(view, p, dx, dy, text, size=3.0, anchor='start'):
    S = view.s
    a = view.P(*p); bx, by = a[0] + dx, a[1] + dy
    S.line(a[0], a[1], bx, by, 0.22, color='#333')
    S.circle(a[0], a[1], 0.5, fill='#333', sw=0)
    S.line(bx, by, bx + (6 if anchor == 'start' else -6), by, 0.22, color='#333')
    S.text(bx + (7 if anchor == 'start' else -7), by + size * 0.35, text, size=size, anchor=anchor)


def export(S, name, width_px=1800):
    svg = os.path.join(OUT, name + '.svg')
    open(svg, 'w').write(S.svg())
    subprocess.run([INK, svg, '--export-type=png', '--export-filename=' + os.path.join(OUT, name + '.png'),
                    '--export-width=%d' % width_px, '--export-background=white'], check=True, capture_output=True)
    print('wrote', name)


def legend(S, x, y, items, size=2.8):
    for i, (k, t) in enumerate(items):
        f, s = COL[k]
        S.rect(x, y + i * 5.2 - 2.6, 4.2, 3.4, stroke=s, sw=0.25, fill=f)
        S.text(x + 6, y + i * 5.2, t, size=size, anchor='start')


# ------------------------------------------------------------------ overview
def col_label(view, p, x_text, y_text, text, size=3.1):
    """Leader from model point p to a text column at sheet (x_text, y_text)."""
    S = view.s
    a = view.P(*p)
    S.circle(a[0], a[1], 0.55, fill='#333', sw=0)
    S.polyline([a, (x_text - 4, y_text), (x_text - 1, y_text)], w=0.22, color='#333')
    for i, t in enumerate(text.split('\n')):
        S.text(x_text, y_text + size * 0.35 + i * size * 1.3, t, size=size, anchor='start')


def overview():
    D = G['device_z0']
    S = Sheet(w=250, h=158)
    k = 1.65
    v = View(S, 16 + 26.2 * k, 62.0, k, SEC)
    draw_parts(v, D)
    v.centerline((0, -27), (0, 99), ext=2)
    callout(v, (-16.75, 63.6), 1, 8, -20, text='Nose O-ring')
    callout(v, (-9.75, -5.0), 2, 22, -24, text='Skin bonded to the metal neck')
    callout(v, (20.0, -14.0), 3, 14, 20, text='One continuous skin over the flange')
    callout(v, (-17.0, -26.3), 4, 10, -26, text='Button domes (no holes)')
    callout(v, (7.8, 89.1), 5, -6, 30, text='Sensor drill is blind from inside', anchor='end')
    legend(S, 16, 128, [('body', 'Stainless steel'), ('oring', 'Rubber O-ring')])
    legend(S, 66, 128, [('skin', 'Cast silicone skin'), ('tray', 'Printed PA12 flange')])
    legend(S, 120, 128, [('pcb_board', 'PCB'), ('int_pack', 'Battery')])
    legend(S, 160, 128, [('cradle', 'Cradle'), ('int_motor', 'Motor')])
    export(S, 'seal-map', 2200)


def nose():
    S = Sheet(w=170, h=86)
    k = 12.0
    v = View(S, 8 - 61.6 * k, 4 + 19.4 * k, k, SEC, clip=(61.6, 13.6, 66.6, 19.4))
    draw_parts(v, G['device_z0'], keys=['body', 'cap', 'oring'], w=0.3)
    col_label(v, (-16.75, 63.62), 76, 24, 'O-ring 32 × 1 mm, squeezed 22 %')
    col_label(v, (-18.7, 64.0), 76, 10, 'Metal faces meet: they set the squeeze')
    col_label(v, (-14.9, 62.0), 76, 52, 'Thread carries the load;\nit is not a seal')
    a = v.P(-15.0, 62.5); S.text(a[0], a[1], 'BODY', size=3.4, anchor='middle', weight='bold', color='#3c434b')
    a = v.P(-15.0, 65.4); S.text(a[0], a[1], 'CAP', size=3.4, anchor='middle', weight='bold', color='#3c434b')
    export(S, 'seal-nose', 1500)


def root():
    S = Sheet(w=220, h=96)
    k = 4.6
    v = View(S, 6 + 16.5 * k, 6 + 21.5 * k, k, SEC, clip=(-16.5, 5.0, 9.5, 21.5))
    draw_parts(v, G['device_z0'], keys=['body', 'nut', 'tray', 'skin', 'pcb_board', 'pcb_parts'], w=0.3)
    col_label(v, (-20.0, -14.0), 136, 14, 'Tray-to-body joint and the flange\nscrews all sit under the skin')
    col_label(v, (-12.0, -12.0), 136, 40, 'Nut clamps the tray root pad to\nthe metal shoulder, inside the skin')
    col_label(v, (-9.75, -5.0), 136, 66, 'Skin bonds to the Ø19.5 land and\nup the Ø15 neck')
    a = v.P(-6.5, 3.0); S.text(a[0], a[1] + 4.0, 'Neck bore (wires)', size=2.9, anchor='middle', color='#333')
    export(S, 'seal-root', 1600)


def buttons():
    S = Sheet(w=200, h=84)
    k = 6.5
    v = View(S, 6 + 27.0 * k, 4 + 23.0 * k, k, SEC, clip=(-27.0, 6.0, -18.6, 23.0))
    draw_parts(v, G['device_z0'], keys=['skin', 'cover', 'plunger1', 'plunger2', 'pcb_board', 'pcb_parts'], w=0.3)
    col_label(v, (-17.0, -26.25), 70, 14, 'Dome: 0.9 mm skin + 0.5 mm dome\nover each plunger head')
    col_label(v, (-14.4, -23.8), 70, 38, 'Plunger slides in the cover bore;\nthe skin covers the 0.2 mm gap')
    col_label(v, (-17.0, -21.7), 70, 62, 'Omron B3U switch on the PCB')
    export(S, 'seal-buttons', 1600)


if __name__ == '__main__':
    for f in (overview, nose, root, buttons):
        f()
