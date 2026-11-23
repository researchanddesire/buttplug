"""FlangeSkin: process reference for the continuous silicone skin cast over the
closed flange (tray + cover). It flares smoothly from the flange face up the
metal neck as one lofted hull: its side walls turn in through a convex arc that
runs straight into a concave arc tangent to the neck (two arcs per direction, set
in the datums), so there is no flat body-side face; its dock-side edge is rounded
over R 4.3 on the ends and R 5 on the long sides. A raised arrow on the dock face points -X (toward the button end)
(device up) for magnetometer calibration. Two low domes mark the buttons; the
plunger heads sit in it 0.9 mm under the face. Bonded to the metal from the O19.5 land up the
neck to RAMP_TOP_Y. Not an ordered part. Has a window over the dock contacts.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/flange_skin.py
Needs mech/FlangeTray.step, mech/RearCover.step, mech/ButtonPlunger.step, mech/MetalBody.step. Writes mech/FlangeSkin.FCStd/.step.
"""
import sys, os, math
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

# ---- parameters (mm) -------------------------------------------------------
HX, HZ = FLANGE_X / 2 + SKIN_T_SIDE, FLANGE_Z / 2 + SKIN_T_Z      # 29.6, 20 outer half sizes
R = FLANGE_R + SKIN_T_Z
REAR_Y = COVER_OUT_Y - SKIN_T_FACE                                 # -25.9 dock face
EDGE_R_REAR, EDGE_R_REAR_SIDE = SKIN_DOCK_END_R, SKIN_DOCK_SIDE_R  # dock-side edge round-over: ends, long sides
NECK_R = 7.5                                                       # metal neck O15
RAMP_TOP_Y = SKIN_NECK_Y                                           # 8: the hull meets the neck here (r 8.1, 0.6 lip over the metal)
N_SECTIONS = 48
WINDOW_MARGIN = 1.5                                                # around the contact row
COLOR = (0.42, 0.30, 0.55)                                         # silicone, plum

name = 'FlangeSkin'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
doc = App.newDocument(name)
try:
    body = Part.Shape(); body.read(METAL + '/MetalBody.step')
    tray = Part.Shape(); tray.read(MECH + '/FlangeTray.step')
    cover = Part.Shape(); cover.read(MECH + '/RearCover.step')

    # Body-side hull: one loft from the flange outline up to a circle at the neck. Its half sizes in X and Z
    # each follow two tangent arcs (convex off the side wall, concave onto the neck), so the long sides and
    # the ends rise and turn into the neck ramp in one gentle curve; the plan corners stay R 10 until the
    # section is narrower than that, then the sections are stadiums and finally a circle.
    def arc_profile(H, spec):
        rc, phi = spec['r'], math.radians(spec['turn'])
        c, sn = math.cos(phi), math.sin(phi)
        rk = (H - rc + rc * c - SKIN_NECK_R) / (1 - c)             # concave radius that lands on the neck
        y_s = SKIN_NECK_Y - (rc + rk) * sn                          # height where the straight wall ends
        c1 = (H - rc, y_s)                                          # convex centre
        p = (c1[0] + rc * c, c1[1] + rc * sn)                       # the two arcs' tangent point
        c2 = (p[0] + rk * c, p[1] + rk * sn)                        # concave centre (its leftmost point is the neck)
        assert rk > 0 and y_s > REAR_Y + 4, ('arc profile does not fit', H, spec, rk, y_s)
        def h_at(y):
            if y <= y_s:
                return H
            if y <= p[1]:
                return c1[0] + math.sqrt(max(rc * rc - (y - y_s) ** 2, 0.0))
            return c2[0] - math.sqrt(max(rk * rk - (y - c2[1]) ** 2, 0.0))
        return h_at, {'wall_ends_Y': round(y_s, 2), 'convex_r': rc, 'concave_r': round(rk, 2), 'tangent_point': [round(p[0], 2), round(p[1], 2)]}
    hx_at, x_info = arc_profile(HX, SKIN_END_ARC)
    hz_at, z_info = arc_profile(HZ, SKIN_SIDE_ARC)
    HULL_Y0 = min(x_info['wall_ends_Y'], z_info['wall_ends_Y'])
    log(name, 'end (X) profile', x_info, 'side (Z) profile', z_info)
    wires = []
    for k in range(N_SECTIONS + 1):
        t = k / N_SECTIONS
        y = HULL_Y0 + (RAMP_TOP_Y - HULL_Y0) * t
        hx, hz = hx_at(y), hz_at(y)
        rc = min(R, hx - 0.05, hz - 0.05)                           # 0.1 mm flats keep every section an 8-edge wire
        wires.append(rr_wire(hx, hz, rc, y))
    hull = Part.makeLoft(wires, True, False)
    # Straight-walled slab from the dock face up to HULL_Y0, its dock-side edge rounded over (EDGE_R_REAR on the
    # ends, EDGE_R_REAR_SIDE on the long sides, blended round the plan corners), concentric with the hard parts'.
    # (Built as prism + hull first, then the cap: fusing a ready capped slab onto the hull fails in OCC.)
    prism = rounded_slab(HX, HZ, R, HULL_Y0, REAR_Y + EDGE_R_REAR)
    cap = cap_loft(HX, HZ, R, REAR_Y, -1, EDGE_R_REAR, EDGE_R_REAR_SIDE)
    dock_faces = Part.Compound([f for f in cap.Faces if f.BoundBox.YMin < REAR_Y + EDGE_R_REAR - 1e-3])
    skin = prism.fuse(hull, 1e-4).fuse(cap).removeSplitter()                 # fuzzy: the exact coincident-face fuse fails at R 12
    assert skin.Volume > prism.Volume + cap.Volume, 'slab/hull fuse failed'
    # Side-profile sanity: the hull must stay outside the body's O24 shoulder / O21 ring and inside the outline.
    for y, need in ((CUFF_END_Y, CUFF_OUTER_R + 1.3), (SHOULDER_Y, SHOULDER_D / 2 + 1.0)):
        assert hz_at(y) >= need and hx_at(y) >= need, ('hull too tight at Y', y, hz_at(y), hx_at(y))

    # Finger-locating domes over the two buttons (spherical caps, SKIN_DOME_R base, SKIN_DOME_H high).
    dome_sphere_r = (SKIN_DOME_R ** 2 + SKIN_DOME_H ** 2) / (2 * SKIN_DOME_H)
    for (x, z) in SWITCHES:
        sph = Part.makeSphere(dome_sphere_r, App.Vector(x, REAR_Y - SKIN_DOME_H + dome_sphere_r, z))
        clip = box_xyz(x - SKIN_DOME_R - 1, x + SKIN_DOME_R + 1, REAR_Y - SKIN_DOME_H - 0.1, REAR_Y + 0.5, z - SKIN_DOME_R - 1, z + SKIN_DOME_R + 1)
        skin = skin.fuse(sph.common(clip))

    # Raised "this way up" arrow on the dock face, pointing -X toward the button end (calibration reference).
    x0, x1 = ARROW_SHAFT_X
    arrow_xz = [(x0, -ARROW_SHAFT_HW), (x0, ARROW_SHAFT_HW), (x1, ARROW_SHAFT_HW), (x1, ARROW_HEAD_HW),
                (ARROW_TIP_X, 0.0), (x1, -ARROW_HEAD_HW), (x1, -ARROW_SHAFT_HW)]
    arrow_wire = Part.makePolygon([App.Vector(x, REAR_Y + 0.2, ARROW_Z + z) for x, z in arrow_xz + arrow_xz[:1]])
    arrow = Part.Face(arrow_wire).extrude(App.Vector(0, -(ARROW_H + 0.2), 0))
    skin = skin.fuse(arrow)

    # Root cuff on the O19.5 bond land is inside the ramp already. Cut the metal, the closed flange's
    # outer envelope (tray + cover, with the tray's rounded body-side edge; the silicone only wraps the
    # outside, so the cavity, bores and counterbores stay out of the skin) and the two button plunger
    # heads that stand proud of the cover.
    envelope = capped_slab2(FLANGE_X / 2, FLANGE_Z / 2, FLANGE_R, SHOULDER_Y, COVER_OUT_Y, FLANGE_END_R, FLANGE_SIDE_R, DOCK_END_R, DOCK_SIDE_R)
    skin = skin.cut(body).cut(envelope)
    skin = skin.cut(cyl_y(NECK_R - 1.0, SHOULDER_Y - 0.5, RAMP_TOP_Y + 0.5))   # nothing inside the body's O12 wire bore
    skin = skin.removeSplitter()
    beyond = lambda sh, y: sh.common(box_xyz(-40, 40, y - 5, y, -25, 25)).Volume   # STEP-read lofted faces have loose boxes: test by volume
    assert beyond(tray, COVER_IN_Y - 0.02) < 1e-3 and beyond(cover, COVER_OUT_Y - 0.02) < 1e-3, 'flange parts stick out of the envelope'
    plunger = Part.Shape(); plunger.read(MECH + '/ButtonPlunger.step')
    for (x, z) in SWITCHES:
        inst = plunger.copy(); inst.translate(App.Vector(x - SWITCHES[0][0], 0, z - SWITCHES[0][1]))
        skin = skin.cut(inst)
    xs = [c[0] for c in CONTACTS]; zs = [c[1] for c in CONTACTS]
    window = box_xyz(min(xs) - CONTACT_SQ / 2 - WINDOW_MARGIN, max(xs) + CONTACT_SQ / 2 + WINDOW_MARGIN,
                     COVER_OUT_Y + 0.1, REAR_Y - 0.1, min(zs) - CONTACT_SQ / 2 - WINDOW_MARGIN, max(zs) + CONTACT_SQ / 2 + WINDOW_MARGIN)
    skin = skin.cut(window).removeSplitter()
    obj, feats = finish(doc, name, skin, COLOR)
    wb = window.BoundBox
    log(name, 'skin outer', [2 * HX, 2 * HZ], 'Y', HULL_Y0, '..', round(REAR_Y, 2), 'then the hull to r', SKIN_NECK_R, 'at Y', RAMP_TOP_Y,
        '; side (Z) half size at Y -8', round(hz_at(-8.0), 2), 'at Y -3', round(hz_at(-3.0), 2), '; end (X) at Y -8', round(hx_at(-8.0), 2),
        'contact window X', [round(wb.XMin, 1), round(wb.XMax, 1)], 'Z', [round(wb.ZMin, 1), round(wb.ZMax, 1)])
    log(name, 'button domes', SKIN_DOME_H, 'high over', [list(map(round, sw)) for sw in SWITCHES], 'silicone over plunger heads', round(BUTTON_HEAD_TOP_Y - REAR_Y, 2), 'flat +', SKIN_DOME_H, 'dome')
    # Skin thickness over the tray's body side (its rounded ends, flat front and long-side edges): sample the
    # tray's surface above Y -14 against the skin's outer hull faces.
    tray_top = [f for f in tray.Faces if f.BoundBox.YMax > HULL_Y0 and f.BoundBox.YMin > COVER_IN_Y + 0.5 and not (f.BoundBox.XLength < 2 * (FLANGE_X / 2 - FLANGE_END_R) - 1 and f.BoundBox.ZLength < NUT_WELL_D and f.BoundBox.YLength < 1e-3)]
    hull_faces = Part.Compound([f for f in skin.Faces if f.BoundBox.YMax > HULL_Y0 + 1e-3 and f.BoundBox.YMin >= HULL_Y0 - 1e-3 and (max(abs(f.BoundBox.XMax), abs(f.BoundBox.XMin)) > FLANGE_X / 2 + 0.3 or max(abs(f.BoundBox.ZMax), abs(f.BoundBox.ZMin)) > FLANGE_Z / 2 + 0.3)])
    thin, where = 99.0, None
    for f in tray_top:
        for p in f.tessellate(0.5)[0]:
            if p.y > HULL_Y0 - 1e-3 and math.hypot(p.x, p.z) > SHOULDER_D / 2 + 0.5:
                d = Part.Vertex(p).distToShape(hull_faces)[0]
                if d < thin:
                    thin, where = d, [round(p.x, 1), round(p.y, 1), round(p.z, 1)]
    log(name, 'skin over the tray above Y', HULL_Y0, ': thinnest', round(thin, 2), 'mm at', where)
    log(name, 'dock-side edge: ends R', EDGE_R_REAR, 'sides R', EDGE_R_REAR_SIDE, '; thinnest silicone over the dock edge and face', round(dock_faces.distToShape(envelope)[0], 2))
    ab = arrow.BoundBox
    log(name, 'arrow -X raised', ARROW_H, 'X', [round(ab.XMin, 1), round(ab.XMax, 1)], 'Z', [round(ab.ZMin, 1), round(ab.ZMax, 1)], 'face Y', round(REAR_Y - ARROW_H, 2))
    log(name, 'OK')
except Exception:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
    raise
finally:
    os._exit(0)
