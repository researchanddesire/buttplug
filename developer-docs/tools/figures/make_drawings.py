"""Engineering drawings of the Compass metal parts, generated from the CAD sections.

Run (system python): python3 make_drawings.py
Needs developer-docs/.cache/figures/drawings/geom.json from extract_sections.py (FreeCAD).
Writes developer-docs/docs/assets/drawings/*.svg, *.pdf and *.png.
Every dimension is the CAD value (measured from MetalBody.step, MotorThermistorCap.step,
ThinRearNut.step and CapFaceSeal.step in hardware/pcb/evt1/one-board/mech/).
"""
import json, os, math, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drawing_lib as DL
from drawing_lib import Sheet, View, THICK, THIN, XTHIN

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
G = json.load(open(os.path.join(DOCS, '.cache', 'figures', 'drawings', 'geom.json')))
OUT = os.path.join(DOCS, 'docs', 'assets', 'drawings')
os.makedirs(OUT, exist_ok=True)
INK = '/Applications/Inkscape.app/Contents/MacOS/inkscape'
DATE = '2026-11-23'

SEC = lambda x, y: (y, -x)       # section A-A (plane Z = 0) seen from +Z: axis horizontal, nose right, +X down
END = lambda a, b: (b, -a)       # end view from the rear (stored as (X, Z)): +Z right, +X down (third angle, left of A-A)


def datum(view, p, letter, dx, dy):
    S = view.s
    a = view.P(*p)
    bx, by = a[0] + dx, a[1] + dy
    S.line(a[0], a[1], bx, by, XTHIN)
    # filled triangle on the feature
    ang = math.atan2(by - a[1], bx - a[0])
    ux, uy = math.cos(ang), math.sin(ang)
    t = [(a[0] - uy * 1.2, a[1] + ux * 1.2), (a[0] + uy * 1.2, a[1] - ux * 1.2), (a[0] + ux * 1.8, a[1] + uy * 1.8)]
    S.polyline(t, w=0.1, close=True, fill='#000')
    S.rect(bx - 2.5, by - 2.5, 5, 5, sw=0.25)
    S.text(bx, by + 1.2, letter, size=3.4, weight='bold')


def dia_half(view, y_model, x_model, text, over=3.0, size=DL.TXT, tshift=0.0):
    """Diameter on a half section: line from just past the axis to the feature at (x_model, y_model),
    one arrowhead at the feature, text along the line."""
    S = view.s
    a = view.P(x_model, y_model); o = view.P(0, y_model)
    sgn = 1 if a[1] < o[1] else -1          # feature above the axis on the sheet -> start below it
    y0 = o[1] + sgn * over
    S.line(a[0], y0, a[0], a[1], XTHIN)
    S.arrowhead(a[0], a[1], -math.pi / 2 if sgn > 0 else math.pi / 2)
    tx = view.P(x_model * 0 + (3.0 if x_model > 0 else -3.0), y_model)
    S.text(a[0] - 0.9, tx[1] + tshift, text, size=size, rot=-90)


def finish_sheet(sheet, name):
    svg = os.path.join(OUT, name + '.svg')
    open(svg, 'w').write(sheet.svg())
    subprocess.run([INK, svg, '--export-type=pdf', '--export-filename=' + os.path.join(OUT, name + '.pdf')], check=True, capture_output=True)
    subprocess.run([INK, svg, '--export-type=png', '--export-filename=' + os.path.join(OUT, name + '.png'), '--export-width=2480',
                    '--export-background=white'], check=True, capture_output=True)
    print('wrote', svg)


def profile_rows(loop_key, ys, outer=True):
    loop = max(G[loop_key]['loops'], key=lambda l: max(p[0] for p in l))
    rows = []
    for y in ys:
        xs = []
        for a, b in zip(loop, loop[1:] + loop[:1]):
            if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
                t = (y - a[1]) / (b[1] - a[1]); xs.append(a[0] + t * (b[0] - a[0]))
        rows.append((y, max(xs) if outer else min(xs)))
    return rows


# =============================================================== sheet 1: metal body
def sheet_body():
    S = Sheet(); S.frame()
    hatch = S.hatch('h45', 45, 1.3)
    # ---- main view: section A-A at 2:1 (axis horizontal, nose right)
    v = View(S, 107.0 + 14.25 * 2, 100.0, 2.0, SEC)
    v.section(G['body_section']['loops'], hatch)
    v.edges(G['body_section']['edges'], THICK)
    v.centerline((0, -14.25), (0, 64.0), ext=5)
    S.text(v.P(0, 24.9)[0], 40.0, 'SECTION A–A  (2:1)', size=4.0, weight='bold')
    base = v.P(18.669, 0)[1]
    v.dim((7.9, -14.25), (18.2574, 64.0), 0, '78.25', 'h', at=base + 24)
    v.dim((12.0, -8.0), (18.2574, 64.0), 0, '72', 'h', at=base + 15)
    v.dim((12.0, -8.0), (7.5, 0.0), 0, '8', 'h', at=base + 6)
    v.dim((7.5, 0.0), (7.5, 8.0), 0, '8', 'h', at=base + 6)
    v.dim((-7.5, 4.0), (7.5, 4.0), 0, 'Ø15', 'v', at=v.P(0, 4.0)[0])
    v.leader((6.0, 13.0), 12, 26, '', lines=['Ø12 bore', '24.6 from B'])
    datum(v, (6.0, 9.0), 'A', -3, 16)
    v.leader((14.0, 44.0), 8, 22, '', lines=['Ø28 bore'])
    v.dim((-18.669, 55.0), (18.669, 55.0), 0, 'Ø37.34 (max, ref.)', 'v', at=v.P(0, 64.0)[0] + 12)
    datum(v, (12.0, -8.0), 'B', -9, 14)
    v.leader((-15.0, 30.0), -14, -25, '', shelf=-1, lines=['Outer profile: see table', 'Bore keeps a 2.2 wall to it', 'from 24.6 to 43.0 from B'])
    v.detail_circle((-9.0, -8.0), 8.0, 'C')
    v.detail_circle((-16.0, 59.0), 6.5, 'D')
    # ---- end view from the rear (third angle: left of A-A)
    cx, cy = 55.0, 100.0
    e = View(S, cx, cy, 2.0, END)
    e.edges(G['body_rear_view']['edges'], THICK)
    e.centerline((0, -19.5), (0, 19.5), ext=0); e.centerline((-19.5, 0), (19.5, 0), ext=0)
    S.text(cx, 40.0, 'VIEW FROM REAR  (2:1)', size=4.0, weight='bold')
    for X in (-21.0, 21.0):
        px, py = e.P(X, 0.0)
        S.line(px, py - 2.5 if py < cy else py, px, py if py < cy else py + 2.5, 0.7)
        S.line(px, py, px - 6, py, 0.3); S.arrowhead(px - 6.8, py, math.pi, l=2.4, w=0.8)
        S.text(px - 10.5, py + 1.5, 'A', size=4.2, weight='bold')
    e.dim((5.0, -9.2), (5.0, 9.2), 0, '18.4 AF', 'h', at=cy + 52)
    def at_ang(r, deg):
        return (r * math.sin(math.radians(deg)), r * math.cos(math.radians(deg)))   # model (X, Z) at a sheet angle from +h
    # sheet angle t: h = Z = r cos t, v = -X = r sin t -> X = -r sin t
    P = lambda r, t: (-r * math.sin(math.radians(t)), r * math.cos(math.radians(t)))
    e.leader(P(12.0, 140), -12, -22, '', shelf=-1, lines=['Ø24 shoulder'])
    e.leader(P(10.0, 200), -14, 14, '', shelf=-1, lines=['Ø20 collar', 'with 2 flats'])
    e.leader(P(8.39, 315), 16, 26, '', lines=['M18×1-6g'])
    e.leader(P(6.0, 30), 24, -30, '', lines=['Ø12'])
    e.leader(P(18.669, 60), 8, -12, '', lines=['Ø37.34 (bulb)'])
    # ---- detail C: rear joint, 5:1 (the -X half, above the axis)
    k = 5.0
    c = View(S, 295.0 + 15.2 * k, 116.0, k, SEC, clip=(-15.2, -0.1, -0.6, 13.2))
    c.section(G['body_section']['loops'], hatch)
    c.edges(G['body_section']['edges'], THICK)
    c.centerline((0, -15.2), (0, -0.6), ext=1)
    S.text(c.P(0, -7.9)[0], 128.0, 'DETAIL C  (5:1)', size=4.0, weight='bold')
    top = c.P(-12.0, 0)[1]
    c.dim((-7.9, -14.25), (-12.0, -8.0), 0, '6.25', 'h', at=top - 22)
    c.dim((-8.3866, -13.75), (-8.3866, -10.25), 0, '3.5', 'h', at=top - 14)
    c.dim((-8.2, -10.25), (-8.2, -9.5), 0, '0.75', 'h', at=top - 7, inside_arrows=False, text_shift=-3.0)
    c.dim((-10.0, -9.5), (-10.0, -8.3), 0, '1.2', 'h', at=top - 14, inside_arrows=False, text_shift=2.5)
    c.dim((-12.0, -8.0), (-12.0, -7.0), 0, '1', 'h', at=top - 7, inside_arrows=False, text_shift=0.0)
    c.dim((-9.75, -7.0), (-9.75, -3.0), 0, '4', 'h', at=top - 7)
    dia_half(c, -12.0, -8.3866, 'M18×1-6g', size=2.6)
    dia_half(c, -9.87, -8.2, 'Ø16.4', size=2.4)
    dia_half(c, -8.9, -10.0, 'Ø20', size=2.6)
    dia_half(c, -7.5, -12.0, 'Ø24', size=2.6)
    dia_half(c, -5.0, -9.75, 'Ø19.5', size=2.6)
    dia_half(c, -2.4, -10.5, 'Ø21', size=2.6)
    c.leader((-8.15, -14.0), -6, 10, '', shelf=-1, lines=['C0.5'])
    c.leader((-10.3, -8.25), 4, -26, '', lines=['R0.3 relief'])
    c.leader((-9.75, -4.5), 14, 34, '', lines=['Skin bond land:', 'keep clean'])
    # ---- detail D: nose thread and face-seal gland, 5:1 (the -X half, above the axis)
    d = View(S, 296.0 - 52.4 * k, 146.0 + 19.4 * k, k, SEC, clip=(52.4, 12.6, 64.8, 19.4))
    d.section(G['body_section']['loops'], hatch)
    d.edges(G['body_section']['edges'], THICK)
    S.text(d.P(0, 58.6)[0], d.P(-12.6, 0)[1] + 20, 'DETAIL D  (5:1)', size=4.0, weight='bold')
    bot = d.P(-12.6, 60)[1]
    d.dim((-14.25, 55.75), (-14.25, 62.95), 0, '7.2', 'h', at=bot + 9)
    d.dim((-15.2, 53.5), (-15.2, 55.75), 0, '2.25', 'h', at=bot + 9, inside_arrows=False, text_shift=-3)
    d.dim((-17.4, 63.22), (-17.4, 64.0), 0, '0.78', 'h', at=d.P(-19.4, 60)[1] - 4, inside_arrows=False, text_shift=-4)
    d.leader((-14.25, 59.0), -10, -12, '', shelf=-1, lines=['M30×1.5-6H', '(pilot Ø28.5)'])
    d.leader((-15.2, 54.4), -12, -4, '', shelf=-1, lines=['Ø30.4 relief']) if False else None
    d.leader((-14.62, 63.33), 12, 12, '', lines=['C0.75×45°'])
    d.leader((-15.8, 63.6), 16, 4, '', lines=['Gland ID Ø31.6'])
    d.leader((-17.4, 63.6), 16, -5, '', lines=['Gland OD Ø34.8'])
    d.leader((-17.32, 63.29), 26, -13, '', lines=['R0.1 (2×)'])
    d.leader((-15.2, 54.4), -12, 13, '', shelf=-1, lines=['Ø30.4 relief'])
    # ---- outer profile table
    rows = profile_rows('body_section', [8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 55, 58, 62, 64])
    S.text(16, 176, 'OUTER PROFILE (from CAD, for inspection)', size=3.2, anchor='start', weight='bold')
    half = (len(rows) + 1) // 2
    for kk, chunk in enumerate((rows[:half], rows[half:])):
        S.table(16 + kk * 46, 179, ['From B', 'Ø'], [('%.1f' % (y + 8.0), '%.2f' % (2 * r)) for y, r in chunk], [22, 22], size=2.5, rh=4.4)
    S.notes(112, 176, 'NOTES', [
        'Stainless steel. 304 is quoted; 316L is the alternative. Alloy not final.',
        'Turn the outer profile, neck, shoulder, collar and M18×1 stub. Mill the two collar flats (18.4 AF).',
        'Bore Ø28 from the nose, then the transition to the Ø12 neck bore. Cut the nose thread and the face-seal gland from the front.',
        'Threads: CAD carries envelopes, not teeth (male M18×1 basic root Ø16.77, female M30×1.5 pilot Ø28.5).',
        'Face-seal gland for a 32 × 1 mm O-ring, 22 % nominal squeeze. No burrs or tool marks in the gland or on the closure face.',
        'Datums: A = Ø12 bore axis. B = rear shoulder face.',
        'Polish skin-contact surfaces. Protect threads, gland, closure face and the Ø19.5 bond land.',
        'Free-form surfaces per MetalBody.step. Tolerances to agree with the machinist (ISO 2768-m proposed).',
    ], width=112, size=2.5, lh=3.7)
    S.title_block({'title': 'Metal body', 'subtitle': 'Turned body: M18×1 rear stub, Ø15 neck, Ø28 nose bore, M30×1.5 nose thread',
                   'number': 'MetalBody', 'material': 'Stainless 304 (316L alt.)', 'finish': 'Polished, see note 7',
                   'scale': '2:1', 'rev': 'EVT1', 'date': DATE, 'sheet': '1 / 3', 'units': 'mm',
                   'source': 'hardware/pcb/evt1/one-board/mech/MetalBody.step'})
    finish_sheet(S, 'metal-body')


# =============================================================== sheet 2: nose cap
def sheet_cap():
    S = Sheet(); S.frame()
    hatch = S.hatch('h45', 45, 1.3)
    v = View(S, 175.0 - 54.75 * 2.5 + 0, 105.0, 2.5, SEC)
    v.ox = 150.0 - 54.75 * 2.5
    v.section(G['cap_section']['loops'], hatch)
    v.edges(G['cap_section']['edges'], THICK)
    v.centerline((0, 54.75), (0, 98.1), ext=5)
    v.centerline((7.8, 76.0), (7.8, 92.0), ext=0)
    S.text(v.P(0, 76.4)[0], 32.0, 'SECTION A–A  (2.5:1)', size=4.0, weight='bold')
    S.text(v.P(0, 76.4)[0], 37.5, 'through the axis and the sensor drill', size=2.8)
    # axial
    vb = v.P(18.2574, 64.0)[1]
    v.dim((13.5, 54.75), (1.27, 98.1), 0, '43.35', 'h', at=vb + 30)
    v.dim((18.2574, 64.0), (1.27, 98.1), 0, '34.1', 'h', at=vb + 21)
    v.dim((14.0799, 55.75), (14.0799, 61.75), -11.5, '6', 'h')
    v.dim((13.8, 61.75), (18.2574, 64.0), -11.5, '2.25', 'h', inside_arrows=False)
    v.dim((-12.25, 54.75), (-12.25, 78.0), 24, '23.25', 'h')
    v.dim((-5.55, 78.0), (-5.55, 93.3), 14, '15.3', 'h')
    v.dim((9.05, 78.0), (9.05, 90.5), -17.5, '12.5', 'h') if False else None
    # diameters
    v.dim((-18.2574, 64.0), (18.2574, 64.0), -2, '', 'v') if False else None
    v.dim((-12.25, 70.0), (12.25, 70.0), 0, '', 'v') if False else None
    v.leader((-12.25, 66.0), -16, -16, '', shelf=-1, lines=['Ø24.5 counterbore'])
    v.leader((-5.55, 86.0), 30, -30, '', lines=['Ø11.1 motor pocket', 'flat bottom = motor stop'])
    v.leader((14.0799, 58.5), -14, 22, '', shelf=-1, lines=['M30×1.5-6g', '(basic root Ø28.16)'])
    v.leader((13.8, 63.0), 26, 20, '', lines=['Ø27.6 runout'])
    v.leader((13.8, 55.25), -26, 12, '', shelf=-1, lines=['C1 chamfer']) if False else None
    v.leader((9.05, 84.0), 26, 13, '', lines=['Ø2.5 sensor drill, 12.5 deep', '140° point, offset 7.8 from axis', '(live-tool operation)'])
    v.dim((0.0, 80.0), (7.8, 80.0), 0, '', 'v') if False else None
    c0 = v.P(0, 91.6); c1 = v.P(7.8, 91.6)
    S.line(c0[0] + 0.8, c0[1], c0[0] + 0.8, c0[1], XTHIN)
    v.dim((0.0, 92.0), (7.8, 92.0), 26, '7.8', 'v')
    v.dim((-18.2574, 64.5), (18.2574, 64.5), -27, 'Ø36.51', 'v')
    datum(v, (18.2574, 64.0), 'B', 6, 22) if False else None
    v.leader((16.0, 64.0), 0.01, 22, '', lines=['Closure shoulder (seats on the body face)']) if False else None
    v.label((15.6, 64.0), 'closure face', dx=10, dy=-0.5, size=2.4, anchor='start') if False else None
    # end view (rear / open end)
    e = View(S, 62.0, 105.0, 2.0, END)
    e.edges(G['cap_rear_view']['edges'], THICK)
    e.centerline((-19.5, 0), (19.5, 0), ext=0); e.centerline((0, -19.5), (0, 19.5), ext=0)
    S.text(62.0, 50.0, 'VIEW FROM REAR  (2:1)', size=4.0, weight='bold')
    cy = 105.0
    for X in (-21.0, 21.0):
        px, py = e.P(X, 0.0)
        S.line(px, py - 2.5 if py < cy else py, px, py if py < cy else py + 2.5, 0.7)
        S.line(px, py, px - 6, py, 0.3); S.arrowhead(px - 6.8, py, math.pi, l=2.4, w=0.8)
        S.text(px - 10.5, py + 1.5, 'A', size=4.2, weight='bold')
    e.centerline((7.8, -2.5), (7.8, 2.5), ext=0)
    e.leader((7.8 + 1.25 * 0.7, 1.25 * 0.7), 16, 16, '', lines=['Ø2.5 sensor drill'])
    e.leader((-5.55 * 0.6, 5.55 * 0.8), 20, -26, '', lines=['Ø11.1 motor pocket'])
    e.leader((-12.25 * 0.8, -12.25 * 0.6), -16, -20, '', shelf=-1, lines=['Ø24.5 counterbore'])
    # ---- profile table
    rows = profile_rows('cap_section', [64, 66, 70, 74, 78, 82, 86, 90, 94, 96, 97, 98])
    S.text(16, 176, 'OUTER PROFILE (from CAD, for inspection)', size=3.2, anchor='start', weight='bold')
    half = (len(rows) + 1) // 2
    for k, chunk in enumerate((rows[:half], rows[half:])):
        S.table(16 + k * 46, 179, ['From shoulder', 'Ø'], [('%.1f' % (y - 64.0), '%.2f' % (2 * r)) for y, r in chunk], [22, 22], size=2.5, rh=4.4)
    S.notes(112, 176, 'NOTES', [
        'Stainless steel, same alloy as the body (304 quoted; 316L alternative).',
        'Turn the dome, closure shoulder and male M30×1.5 spigot. Bore the Ø24.5 counterbore and the flat-bottomed Ø11.1 motor pocket.',
        'Drill the Ø2.5 sensor hole with a live tool, offset 7.8 from the axis, 12.5 deep with a 140° point; 1 mm nominal web to the motor pocket.',
        'Motor: NFP-E1015, Ø11 ±0.1 × 26 mm can, seated on the pocket floor. Pocket fit to the received motors is not yet set.',
        'The closure shoulder seats metal-to-metal on the body face; it sets the O-ring squeeze. Keep it flat and free of burrs.',
        'Polish the dome. Protect the thread and the closure shoulder.',
        'Thread shown as the basic-root envelope, not teeth. Tolerances to be agreed with the machinist.',
    ], width=112, size=2.5, lh=3.7)
    S.title_block({'title': 'Nose cap', 'subtitle': 'Turned cap: motor pocket, offset sensor drill, M30×1.5 spigot',
                   'number': 'MotorThermistorCap', 'material': 'Stainless 304 (316L alt.)', 'finish': 'Polished dome',
                   'scale': '2.5:1', 'rev': 'EVT1', 'date': DATE, 'sheet': '2 / 3', 'units': 'mm',
                   'source': 'hardware/pcb/evt1/one-board/mech/MotorThermistorCap.step'})
    finish_sheet(S, 'nose-cap')


# =============================================================== sheet 3: metal assembly and joints
def sheet_assembly():
    S = Sheet(); S.frame()
    hb = S.hatch('hb', 45, 1.3); hc = S.hatch('hc', 135, 1.3); hn = S.hatch('hn', 45, 0.7)
    hp = S.hatch('hp', 135, 2.0, color='#666')
    D = G['device_z0']
    k = 1.5
    v = View(S, 60.0 + 14.25 * k, 112.0, k, SEC)
    v.section(G['body_section']['loops'], hb)
    v.section(G['cap_section']['loops'], hc)
    v.section(G['nut_section']['loops'], hn)
    v.section(G['oring_section']['loops'], '#000', w=0.1)
    v.edges(G['body_section']['edges'], THIN); v.edges(G['cap_section']['edges'], THIN); v.edges(G['nut_section']['edges'], THIN)
    v.centerline((0, -15), (0, 99), ext=4)
    S.text(v.P(0, 42)[0], 46.0, 'METAL ASSEMBLY, SECTION A–A  (1.5:1)', size=4.0, weight='bold')
    def balloon(view, p, n, dx, dy):
        a = view.P(*p); bx, by = a[0] + dx, a[1] + dy
        S.line(a[0], a[1], bx, by, XTHIN); S.circle(a[0], a[1], 0.5, fill='#000', sw=0)
        S.circle(bx, by, 3.6, sw=0.3, fill='white'); S.text(bx, by + 1.3, str(n), size=3.6, weight='bold')
    balloon(v, (-17.0, 28.0), 1, -8, -14)
    balloon(v, (-14.5, 86.0), 2, 10, -12)
    balloon(v, (16.6, 63.6), 3, 10, 18)
    balloon(v, (11.5, -12.0), 4, -10, 16)
    v.detail_circle((-16.6, 63.6), 2.8, 'D')
    v.detail_circle((-11.0, -8.5), 6.0, 'E')
    # ---- detail D: nose joint at 10:1 (the -X half, above the axis)
    kd = 10.0
    d = View(S, 262.0 - 61.8 * kd, 38.0 + 19.0 * kd, kd, SEC, clip=(61.8, 14.6, 65.6, 19.0))
    d.section(G['body_section']['loops'], hb); d.section(G['cap_section']['loops'], hc)
    d.section(G['oring_section']['loops'], '#000', w=0.1)
    d.edges(G['body_section']['edges'], THICK); d.edges(G['cap_section']['edges'], THICK)
    S.text(d.P(0, 63.7)[0], d.P(-14.6, 0)[1] + 9, 'DETAIL D  (10:1)  nose seal', size=3.8, weight='bold')
    d.leader((-16.75, 63.62), 34, -14, '', lines=['O-ring 32 × 1 (item 3),', 'installed 22 % squeeze'])
    d.leader((-18.0, 64.0), 30, 6, '', lines=['Metal-to-metal closure', 'face sets the squeeze'])
    d.leader((-14.9, 63.4), 36, 30, '', lines=['Thread: not a seal'])
    # ---- detail E: rear joint at 4:1 (the -X half, above the axis)
    ke = 4.0
    e = View(S, 262.0 + 15.5 * ke, 120.0 + 16.5 * ke, ke, SEC, clip=(-15.5, 0.5, -1.0, 16.5))
    e.section(D['tray']['loops'], hp, stroke='#444', w=THIN)
    e.section(G['body_section']['loops'], hb); e.section(G['nut_section']['loops'], hn)
    e.edges(G['body_section']['edges'], THICK); e.edges(G['nut_section']['edges'], THICK)
    S.text(e.P(0, -8.2)[0], e.P(-0.5, 0)[1] + 10, 'DETAIL E  (4:1)  rear joint', size=3.8, weight='bold')
    e.leader((-12.0, -12.0), 76, -14, '', lines=['Thin nut (item 4) clamps the', 'tray root pad to the shoulder'])
    e.leader((-14.8, -9.0), 66, -26, '', lines=['Flange tray root pad (PA12)'])
    e.leader((-10.0, -8.9), 70, 10, '', lines=['Collar flats key the tray'])
    e.leader((-9.75, -5.0), 60, 24, '', lines=['Ø19.5 land: the silicone', 'skin bonds here'])
    # ---- parts list and notes
    y = S.table(16, 196, ['Item', 'Part', 'Spec / source', 'Qty'], [
        ('1', 'Metal body', 'Sheet 1. Stainless, turned', '1'),
        ('2', 'Nose cap', 'Sheet 2. Stainless, turned + live-tool drill', '1'),
        ('3', 'O-ring 32 × 1', 'Silicone 70A, OneMonroe 32 X 1 S-70 (candidate)', '1'),
        ('4', 'Thin nut M18×1, 24 AF × 4', 'Stainless 316Ti, ifm E10028', '1'),
    ], [12, 46, 98, 12], size=2.6, rh=5.2)
    S.notes(16, y + 8, 'ASSEMBLY NOTES', [
        'Fit the flange tray over the collar so the flats engage its keyed socket, then tighten item 4 with the two-jaw driver. Threadlocker candidate: Loctite 243. Torque not yet set.',
        'Seat item 3 dry in the body gland. Thread item 2 on until the shoulders meet. The metal faces, not the O-ring, carry the closure.',
    ], width=190, size=2.6, lh=3.9)
    S.title_block({'title': 'Metal assembly and joints', 'subtitle': 'Body, nose cap, nose O-ring and rear nut',
                   'number': 'compass-device (metal)', 'material': 'See parts list', 'finish': '—',
                   'scale': '1.5:1', 'rev': 'EVT1', 'date': DATE, 'sheet': '3 / 3', 'units': 'mm',
                   'source': 'hardware/pcb/evt1/one-board/mech/compass-device.FCStd'})
    finish_sheet(S, 'metal-assembly')


if __name__ == '__main__':
    which = sys.argv[1:] or ['body', 'cap', 'assembly']
    for w in which:
        {'body': sheet_body, 'cap': sheet_cap, 'assembly': sheet_assembly}[w]()
