"""Internals: the 3-wire battery pack (protected, with its own NTC), the
vibration motor, the tip NTC with its potting, and every wire from the board's
B.Cu connectors through the 12 mm neck bore. Provisional geometry carried over from the body pack
trial (hardware/cad/manufacturing-layout/one-board-evt1/body_pack_trial.py)
and extended to the compact board's connectors. Not an ordered part.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/internals.py
Needs the metal STEPs, FlangeTray.step and compass-one-board.step in mech/.
Writes mech/Internals.FCStd, mech/Internals.step (coloured solids) and mech/internals-fit.json.
"""
import sys, os, json, itertools
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

# ---- parameters (mm) -------------------------------------------------------
# Pack: 502030-class protected 1S LiPo with a built-in NTC and three leads (red +, black -, white/yellow NTC),
# BC-PACK-EVT1-002 (one-board/PACK-RFQ.md). Finished maximum 33 x 21 x 6.3, as BC-PACK-EVT1-001, 1 mm off axis.
PACK_MIN, PACK_SIZE = (-10.5, 31.75, -4.15), (21.0, 33.0, 6.3)
PACK_PCM_L = 2.0                                                  # protection board strip at the lead end
PACK_LEADS = {'P': -1.1, 'N': 0.0, 'NTC': 1.1}                    # lead exit X at the pack's lead end, Z -1
PACK_LEAD_Z = -1.0
MOTOR_START_Y, MOTOR_R, MOTOR_L = 67.0, 5.55, 26.3                # NFP-E1015 can, rear face Y67, stop Y93.3
MOTOR_LEAD_Z = 4.2
TIP_NTC = (7.8, 89.1); TIP_NTC_R, TIP_NTC_L = 0.6, 1.2            # head in the offset O2.5 drill
POT_R, POT_Y0, POT_L = 1.25, 88.1, 2.4
NECK_Y = -14.6                                                    # tails cross the stub tip here
PLUG_LEN = 3.0                                                    # mated SH plug beyond the side-entry housing front (Z)
# JST SH crimp plugs (SHR-0nV-S) as envelopes: width (n - 1) x 1.0 + 2.0 along the pins, 2.0 thick; the part
# inside the header is left out (the header model is in the board STEP). Side-entry plugs stand PLUG_LEN out of
# the header front; the vertical J5 plug stands VPLUG_LEN above its 4.32 mm header.
PLUG_T = 2.0
VHEADER_H, VPLUG_LEN = 4.32, 2.5
J5_ZC = 100 - 93.2                                                # J5 footprint centre in device Z
WIRE_OD = {'motor': 0.60, 'sensor': 0.46, 'pack': 0.63}
COLORS = {'pack': (0.62, 0.66, 0.72), 'ntc': (0.21, 0.72, 0.67), 'th3': (0.15, 0.55, 0.50), 'motor': (0.35, 0.36, 0.38),
          'tip': (0.21, 0.72, 0.67), 'pot': (0.90, 0.85, 0.60), 'motor_p': (0.89, 0.40, 0.12), 'motor_n': (0.60, 0.22, 0.09),
          'tip_w': (0.12, 0.56, 0.75), 'pack_p': (0.80, 0.17, 0.18), 'pack_n': (0.20, 0.22, 0.25),
          'pack_ntc': (0.95, 0.85, 0.25), 'pcm': (0.10, 0.35, 0.20), 'plug': (0.93, 0.91, 0.84)}

# Board-side ends (device frame). Connector pins from the layout; J2 and J3 plugs leave their side-entry
# housings toward +Z, as does J5 since it became a side-entry SM02B (2026-11-20).
B = BOARD_B_Y
J3 = [(6.2, 8.9), (7.2, 8.9)]        # pin X, housing top Z (J3 at kx 106.7 since 2026-11-19)
J5 = [(18.85, 8.9), (19.85, 8.9)]    # SM02B side-entry header at kx 119.35, ky 93.6 like J3 (2026-11-20): pin X, housing front Z
J2 = {'P': (12.0, 8.9), 'N': (13.0, 8.9), 'NTC': (14.0, 8.9)}   # JST SH SM03B side-entry header, pins 1..3 (2026-11-19); the pack's own SHR-03V-S plug mates here

def plug_exit(pin, neck, loop_y=-15.6):
    """Nodes from a mated side-entry plug up, over and down into the neck bore."""
    x, zt = pin; xn, zn = neck
    return [(x, B + 1.5, zt + PLUG_LEN), (x, B + 3.0, zt + PLUG_LEN + 1.3), ((x + xn) / 2 + 1.0, loop_y, (zt + zn) / 2 + 3.0),
            (xn, NECK_Y, zn)]

def vplug_exit(pin, neck):
    """Nodes from the top of a mated vertical plug, bending over toward the neck bore."""
    x, zc = pin; xn, zn = neck; yt = B + VHEADER_H + VPLUG_LEN
    return [(x, yt, zc), (x, yt + 0.8, zc + 0.2), ((x + xn) / 2, yt + 1.4, (zc + zn) / 2 + 0.6), (xn, -12.0, zn)]

def side_plug(pins_x, zt):
    x0, x1 = min(pins_x) - 1.0, max(pins_x) + 1.0
    return Part.makeBox(x1 - x0, PLUG_T, PLUG_LEN, V(x0, B + 1.5 - PLUG_T / 2, zt))

def vertical_plug(pins_x, zc):
    x0, x1 = min(pins_x) - 1.0, max(pins_x) + 1.0
    return Part.makeBox(x1 - x0, VPLUG_LEN, PLUG_T, V(x0, B + VHEADER_H, zc - PLUG_T / 2))

def land_exit(land, neck):
    """Nodes from a solder land on B.Cu, rising off the board and gathering into the bore."""
    x, z = land; xn, zn = neck
    return [(x, B, z), (x, B + 1.0, z + 0.3), ((x + xn) / 2, -17.0, (z + zn) / 2), (xn, NECK_Y, zn)]

# The four upper wires follow CradleWireGuide. The three pack wires use the
# lower part of the neck bore. End/connector coordinates remain unchanged.
def guided(pin, xn, kind='motor'):
    return plug_exit(pin,(xn,3.45),-15.0)[:-1]+[(xn,NECK_Y,3.45),(xn,18.0,3.45),(xn,30.4,5.15),(xn,63.0,5.15)]
WIRES = [
    ('Motor P','motor','motor_p',guided(J3[0],-1.35)+[(-1.35,65.9,5.15),(-0.52,MOTOR_START_Y,MOTOR_LEAD_Z)]),
    ('Motor N','motor','motor_n',guided(J3[1],-0.45)+[(-0.45,65.9,5.15),(0.52,MOTOR_START_Y,MOTOR_LEAD_Z)]),
    ('Tip NTC S','sensor','tip_w',guided(J5[0],0.45,'sensor')+[(0.45,65.6,5.15),(1.0,67.0,6.5),(7.43,73.0,5.4),(7.43,78.0,0),(7.43,TIP_NTC[1],0)]),
    ('Tip NTC R','sensor','tip_w',guided(J5[1],1.35,'sensor')+[(1.35,65.6,5.15),(1.9,67.0,6.5),(8.17,73.0,5.4),(8.17,78.0,0),(8.17,TIP_NTC[1],0)]),
    ('Pack P','pack','pack_p',plug_exit(J2['P'],(-1.1,-1.0),-16.0)+[(-1.1,0,-1.0),(-1.1,16,-1.0),(-1.1,PACK_MIN[1],-1.0)]),
    ('Pack N','pack','pack_n',plug_exit(J2['N'],(0.0,-1.0),-16.0)+[(0.0,0,-1.0),(0.0,16,-1.0),(0.0,PACK_MIN[1],-1.0)]),
    ('Pack NTC','sensor','pack_ntc',plug_exit(J2['NTC'],(1.1,-1.0),-16.0)+[(1.1,0,-1.0),(1.1,16,-1.0),(1.1,PACK_MIN[1],-1.0)]),
]

name = 'Internals'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
doc = App.newDocument(name)
V = App.Vector
try:
    items = []   # (label, kind, shape, colour)
    pcm = Part.makeBox(PACK_SIZE[0], PACK_PCM_L, PACK_SIZE[2], V(*PACK_MIN))
    pack = Part.makeBox(PACK_SIZE[0], PACK_SIZE[1] - PACK_PCM_L, PACK_SIZE[2], V(PACK_MIN[0], PACK_MIN[1] + PACK_PCM_L, PACK_MIN[2]))
    items.append(('Pack 3-wire PCM+NTC 21x33x6.3', 'pack', pack, COLORS['pack']))
    items.append(('Pack PCM strip', 'pcm', pcm, COLORS['pcm']))
    # Cut soft support envelopes, material/compression unqualified. Their
    # installed thickness fills the nominal shelf-to-pouch gap; growth uses
    # their compliance and must be validated with the actual pack.
    for i,y in enumerate([36.0,51.0],1):
        items.append(('Battery support pad '+str(i)+' (unselected soft stock)','cushion',
                      Part.makeBox(14.0,4.0,1.2,V(-7.0,y,-5.35)),(0.86,0.83,0.70)))
    items.append(('Motor NFP-E1015', 'motor', Part.makeCylinder(MOTOR_R, MOTOR_L, V(0, MOTOR_START_Y, 0), V(0, 1, 0)), COLORS['motor']))
    tip = Part.makeCylinder(TIP_NTC_R, TIP_NTC_L, V(TIP_NTC[0], TIP_NTC[1], 0), V(0, 1, 0))
    pot = Part.makeCylinder(POT_R, POT_L, V(TIP_NTC[0], POT_Y0, 0), V(0, 1, 0)).cut(tip)
    items.append(('Tip NTC head', 'tip', tip, COLORS['tip']))
    items.append(('Tip NTC potting', 'pot', pot, COLORS['pot']))
    items.append(('J3 plug SHR-02V-S (motor)', 'plug', side_plug([p[0] for p in J3], J3[0][1]), COLORS['plug']))
    items.append(('J2 plug SHR-03V-S (pack, factory)', 'plug', side_plug([p[0] for p in J2.values()], J2['P'][1]), COLORS['plug']))
    items.append(('J5 plug SHR-02V-S (tip NTC)', 'plug', side_plug([p[0] for p in J5], J5[0][1]), COLORS['plug']))

    def make_wire(nodes, od):
        # Lines and tangent circular arcs avoid interpolation overshoot into
        # adjacent wires or the trough. Actual radii are recorded, not assumed.
        import math
        ps=[V(*p) for p in nodes]
        fillets=[];radii=[]
        for i in range(1,len(ps)-1):
            u=ps[i]-ps[i-1];v=ps[i+1]-ps[i]
            lu,lv=u.Length,v.Length;u.normalize();v.normalize()
            angle=math.acos(max(-1,min(1,u.dot(v))))
            if angle<1e-5:
                fillets.append(None);continue
            cut=min(1.5*math.tan(angle/2),(0.95 if i==1 else 0.45)*lu,(0.95 if i==len(ps)-2 else 0.45)*lv)
            radius=cut/math.tan(angle/2);radii.append(radius)
            aa=ps[i]-u*cut;bb=ps[i]+v*cut
            bis=-u+v;bis.normalize()
            mid=ps[i]+bis*(radius/math.cos(angle/2)-radius)
            fillets.append((aa,mid,bb))
        edges=[];last=ps[0]
        for i,fillet in enumerate(fillets,1):
            if fillet is None:continue
            aa,mid,bb=fillet
            if (aa-last).Length>1e-7:edges.append(Part.makeLine(last,aa))
            edges.append(Part.Arc(aa,mid,bb).toShape());last=bb
        if (ps[-1]-last).Length>1e-7:edges.append(Part.makeLine(last,ps[-1]))
        path=Part.Wire(edges);t=ps[1]-ps[0];t.normalize()
        section=Part.Wire([Part.makeCircle(od/2,ps[0],t)])
        sh=path.makePipeShell([section],True,False)
        assert sh.isValid() and len(sh.Solids)==1,'pipe failed'
        return sh,path.Length,min(radii)

    wire_len = {}; wire_radii = {}
    for label, kind, ck, nodes in WIRES:
        sh, L, radius = make_wire(nodes, WIRE_OD[kind])
        wire_radii[label] = round(radius,3)
        items.append((label, 'wire', sh, COLORS[ck]))
        wire_len[label] = round(L, 1)
    log(name, 'wire lengths mm', wire_len)

    # Fit checks against the hard parts and among the internals themselves.
    hard = {}
    for n in ('MetalBody', 'MotorThermistorCap', 'ThinRearNut', 'FlangeTray', 'InternalCradle', 'CradleWireGuide'):
        s = Part.Shape(); s.read(MECH + '/' + n + '.step'); hard[n] = s
    pcb = Part.Shape(); pcb.read(MECH + '/compass-one-board.step'); pcb.transformShape(pcb_matrix(), True); hard['PCB'] = pcb

    def common_volume(a, b):
        total = 0.0
        for s in (b.Solids or [b]):
            if a.BoundBox.intersect(s.BoundBox):
                try:
                    total += a.common(s).Volume
                except Exception as e:
                    log(name, 'common failed', str(e))
        return total

    overlaps = []
    for label, kind, sh, _ in items:
        for hn, hs in hard.items():
            v = common_volume(sh, hs)
            if v > 1e-3:
                overlaps.append({'a': label, 'b': hn, 'mm3': round(v, 3)})
    for (la, ka, sa, _), (lb, kb, sb, _) in itertools.combinations(items, 2):
        if 'pot' in (ka, kb) or 'tip' in (ka, kb) and 'wire' in (ka, kb):
            continue   # the tip leads run through the potting and head by design
        if {ka, kb} == {'plug', 'wire'}:
            plug, wire = (la, lb) if ka == 'plug' else (lb, la)
            if plug.split('(')[1].split()[0].split(',')[0].lower() in wire.lower():
                continue   # each lead starts inside its own plug
        v = common_volume(sa, sb)
        if v > 0.05:
            overlaps.append({'a': la, 'b': lb, 'mm3': round(v, 3)})
    log(name, 'overlaps', json.dumps(overlaps))

    objs = []
    for label, kind, sh, color in items:
        o = doc.addObject('Part::Feature', label.replace(' ', '_').replace('.', '_'))
        o.Label = label; o.Shape = sh
        doc.recompute()
        if o.ViewObject is not None:
            o.ViewObject.ShapeColor = color
        objs.append(o)
    doc.saveAs(MECH + '/' + name + '.FCStd')
    for f in os.listdir(MECH):
        if f.endswith('.FCBak'):
            os.replace(MECH + '/' + f, BUILD + '/' + f)
    import ImportGui
    ImportGui.export(objs, MECH + '/' + name + '.step')
    report = {'pack': 'Protected 502030-class 1S LiPo with built-in NTC, three leads (P, N, NTC), e.g. EEMB LP502030-PCM-NTC-LD; finished maximum 33 x 21 x 6.3',
              'board_interface': 'J2 JST SH 3-pin side-entry header (SM03B-SRSS-TB) on B.Cu, 1 PACK_P / 2 GND / 3 PACK_NTC; the pack plugs in with its factory SHR-03V-S plug (2026-11-19, replaced the solder lands)',
              'items': [l for l, _, _, _ in items], 'wire_lengths_mm': wire_len, 'minimum_bend_radius_mm': wire_radii, 'battery_support': 'Two 14 x 4 x 1.2 mm soft pad envelopes; material, compression, ageing and pack swelling response unqualified. Guide captures the pouch above; band slots provide optional secondary restraint.', 'overlaps': overlaps,
              'scope': 'Provisional component envelopes and guided seven-wire paths. Radii are nominal geometry, not cable supplier approval. Slack, restraint, cap rotation/free tails, received terminal shape and physical installation need trial.'}
    with open(MECH + '/internals-fit.json', 'w') as f:
        f.write(json.dumps(report, indent=2) + '\n')
    log(name, 'OK')
except Exception:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
finally:
    os._exit(0)
