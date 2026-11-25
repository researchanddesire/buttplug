"""FlangeSkin: process reference for the continuous silicone skin cast over the
closed flange (tray + cover). It flares smoothly from the flange face up the
metal neck as one lofted hull: its side walls turn in through a convex arc that
runs straight into a concave arc tangent to the neck (two arcs per direction, set
in the datums), so there is no flat body-side face; its dock-side edge is rounded
over R 4.3 on the ends and R 5 on the long sides. A raised arrow on the dock face points -X (toward the button end)
for magnetometer calibration. Two low domes mark the buttons; the
plunger heads sit in it 0.9 mm under the face. Bonded to the metal from the O19.5 land up the
neck to RAMP_TOP_Y. Not an ordered part. Has a window over the dock contacts and a shallow recessed R+D icon in the lower corner of the dock face.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/flange_skin.py
Needs mech/FlangeTray.step, mech/RearCover.step, mech/ButtonPlunger.step, mech/MetalBody.step. Writes mech/FlangeSkin.FCStd/.step.
"""
import sys, os, math, json, hashlib
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part, Sketcher
from compass_datums import *

# ---- parameters (mm) -------------------------------------------------------
HX, HZ = FLANGE_X / 2 + SKIN_T_SIDE, FLANGE_Z / 2 + SKIN_T_Z      # 29.6, 20 outer half sizes
R = FLANGE_R + SKIN_T_Z
REAR_Y = COVER_OUT_Y - SKIN_T_FACE                                 # -25.9 dock face
EDGE_R_REAR, EDGE_R_REAR_SIDE = SKIN_DOCK_END_R, SKIN_DOCK_SIDE_R  # dock-side edge round-over: ends, long sides
NECK_R = 7.5                                                       # metal neck O15
RAMP_TOP_Y = SKIN_NECK_Y                                           # 8: the hull meets the neck here (r 8.1, 0.6 lip over the metal)
N_SECTIONS = 48                                                    # spaced by profile arc length (2026-11-20)
SECTION_POINTS = 192                                               # rays per section: one periodic B-spline each
WINDOW_MARGIN = 1.5                                                # around the contact row
# Icon reads upright with the arrow/button end at the top, as in the owner's view.
ICON_SIZE = 6.5                                                    # longest side of the original icon
ICON_DEPTH = 0.25                                                  # 1.05 mm silicone remains over the cover
ICON_CENTER_X, ICON_CENTER_Z = 19.0, 8.5                            # lower right, viewed from the dock
ICON_SVG = MECH + '/assets/rd-icon.svg'                              # original brand vector, not text
COLOR = (0.42, 0.30, 0.55)                                         # silicone, plum

def icon_geometry():
    """Exact cubic paths from this original brand asset, in sketch XY.

    The SVG's group flips original Y-up artwork into SVG Y-down. Sketch XY
    is Y-up, so use the original path coordinates, uniformly scaled. Only
    the five commands used by this pinned SVG are accepted.
    """
    import re, xml.etree.ElementTree as ET
    root = ET.parse(ICON_SVG).getroot()
    group = root.find('{http://www.w3.org/2000/svg}g')
    assert group.attrib['transform'] == 'translate(0,800) scale(0.1,-0.1)'
    segments = []
    for path in group.findall('{http://www.w3.org/2000/svg}path'):
        tokens = re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?', path.attrib['d'])
        i, cmd, current, start = 0, None, (0.0, 0.0), None
        while i < len(tokens):
            if tokens[i].isalpha():
                cmd = tokens[i]; i += 1
            assert cmd in ('M', 'm', 'c', 'l', 'z'), ('unsupported icon command', cmd)
            if cmd == 'z':
                if math.dist(current, start) > 1e-8:
                    segments.append(('line', [current, start]))
                current = start; cmd = None
                continue
            count = 6 if cmd == 'c' else 2
            values = list(map(float, tokens[i:i+count])); i += count
            points = [(values[k], values[k+1]) for k in range(0, count, 2)]
            if cmd.islower():
                points = [(current[0] + x, current[1] + y) for x, y in points]
            if cmd in ('M', 'm'):
                current = start = points[0]
                cmd = 'l'  # repeated move pairs are line-to; this asset uses relative commands
                continue
            segments.append(('cubic' if cmd == 'c' else 'line', [current] + points))
            current = points[-1]
    def make(kind, points):
        poles = [App.Vector(x, y, 0) for x, y in points]
        if kind == 'line':
            return Part.LineSegment(*poles)
        curve = Part.BSplineCurve()
        curve.buildFromPolesMultsKnots(poles, [4, 4], [0.0, 1.0], False, 3)
        return curve
    original = [make(kind, points) for kind, points in segments]
    bounds = Part.Compound([g.toShape() for g in original]).BoundBox
    scale = ICON_SIZE / max(bounds.XLength, bounds.YLength)
    cx, cy = (bounds.XMin + bounds.XMax) / 2, (bounds.YMin + bounds.YMax) / 2
    return [make(kind, [((x-cx)*scale, (y-cy)*scale) for x, y in points]) for kind, points in segments]

def stamp_icon(doc, skin, envelope):
    # Import the authentic icon curves and keep a native sketch and editable
    # Pocket in the saved skin; the older loft/envelope is its base feature.
    if App.GuiUp:
        import ImportGui
    log(name, 'reading original icon curves')
    geometry = icon_geometry()
    native_body = doc.addObject('PartDesign::Body', 'SiliconeSkin')
    base = native_body.newObject('PartDesign::Feature', 'SkinEnvelope')
    base.Label = 'Continuous silicone before the icon'
    base.Shape = skin
    profile = native_body.newObject('Sketcher::SketchObject', 'RDIconProfile')
    profile.addGeometry(geometry, False)
    profile.Label = 'R+D original icon outline'
    # Sketch X points screen-right (+Z); sketch Y points up (-X); normal is -Y.
    profile.Placement = App.Placement(App.Vector(ICON_CENTER_X, REAR_Y, ICON_CENTER_Z),
                                     App.Rotation(App.Vector(0, 0, 1), App.Vector(-1, 0, 0),
                                                  App.Vector(0, -1, 0), 'ZXY'))
    profile.addProperty('App::PropertyString', 'SourceSVG', 'Brand source')
    profile.SourceSVG = 'assets/rd-icon.svg'
    profile.addProperty('App::PropertyLength', 'IconSize', 'Brand source')
    profile.IconSize = ICON_SIZE
    doc.recompute()
    icon_face = Part.makeFace(profile.Shape.Wires, 'Part::FaceMakerBullseye')
    assert icon_face.isValid() and icon_face.Area > 0, 'invalid icon profile'
    log(name, 'icon sketch', len(profile.Geometry), 'curves, area', icon_face.Area)
    pocket = native_body.newObject('PartDesign::Pocket', 'IconDeboss')
    pocket.Label = 'R+D icon recessed %.2f mm' % ICON_DEPTH
    pocket.Profile = profile
    pocket.Length = ICON_DEPTH
    pocket.Refine = True
    doc.recompute()
    assert not pocket.Shape.isNull(), 'icon pocket failed: ' + str(pocket.State)
    stamped = pocket.Shape
    assert stamped.isValid() and len(stamped.Solids) == 1, 'icon broke the continuous skin'
    removed = skin.Volume - stamped.Volume
    expected = icon_face.Area * ICON_DEPTH
    stamp_volume = icon_face.extrude(App.Vector(0, ICON_DEPTH, 0))
    local_removed = skin.common(stamp_volume).Volume
    log(name, 'volume delta', removed, 'stamp', expected, 'local cut', local_removed)
    assert abs(local_removed - expected) < 1e-4, ('icon is not wholly on the flat dock face', local_removed, expected)
    # Compare the removed and added material directly: whole-skin volumes of the lofted B-spline hull are
    # only integrated to ~1e-4 relative (a few mm3 on 30 000), far coarser than this 0.05 mm3 check.
    cut_away = skin.cut(stamped).Volume
    added = stamped.cut(skin).Volume
    log(name, 'icon removed', cut_away, 'added', added)
    assert abs(cut_away - expected) < 0.05 and added < 0.05, ('unexpected material removed outside icon', cut_away, added)
    floor = icon_face.copy(); floor.translate(App.Vector(0, ICON_DEPTH, 0))
    floor_clearance = floor.distToShape(envelope)[0]
    assert floor_clearance >= SKIN_T_FACE - ICON_DEPTH - 1e-4, 'icon floor too close to rigid cover'
    if App.GuiUp:
        base.ViewObject.Visibility = False
        profile.ViewObject.Visibility = False
        pocket.ViewObject.ShapeColor = COLOR
        native_body.ViewObject.ShapeColor = COLOR
    doc.recompute()
    doc.saveAs(MECH + '/' + name + '.FCStd')
    if App.GuiUp:
        ImportGui.export([native_body], MECH + '/' + name + '.step')
    else:
        stamped.exportStep(MECH + '/' + name + '.step')
    saved = Part.Shape(); saved.read(MECH + '/' + name + '.step')
    assert saved.isValid() and len(saved.Solids) == 1, 'invalid saved skin STEP'
    log(name, 'STEP volume', saved.Volume, 'native volume', stamped.Volume)
    assert abs(saved.Volume - stamped.Volume) < stamped.Volume * 1e-5, 'saved skin STEP differs from native'
    for attr in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax'):
        assert abs(getattr(saved.BoundBox, attr) - getattr(stamped.BoundBox, attr)) < 1e-3, 'saved skin STEP bounds differ'
    for f in os.listdir(MECH):
        if f.endswith('.FCBak'):
            os.replace(MECH + '/' + f, BUILD + '/' + f)
    bb = profile.Shape.BoundBox
    icon_report = {
        'source': 'assets/rd-icon.svg',
        'source_sha256': hashlib.sha256(open(ICON_SVG, 'rb').read()).hexdigest(),
        'center_XZ_mm': [ICON_CENTER_X, ICON_CENTER_Z],
        'size_on_face_mm': [round(bb.ZLength, 6), round(bb.XLength, 6)],
        'depth_mm': ICON_DEPTH,
        'orientation': 'top toward button end (-X), right +Z, dock view -Y',
        'removed_volume_mm3': round(local_removed, 6),
        'whole_skin_volume_delta_mm3': round(removed, 6),
        'remaining_silicone_to_cover_mm': round(floor_clearance, 6),
        'valid_native': stamped.isValid(), 'native_solids': len(stamped.Solids),
        'valid_saved_step': saved.isValid(), 'saved_step_volume_mm3': round(saved.Volume, 6),
        'native_volume_mm3': round(stamped.Volume, 6),
        'step_volume_difference_mm3': round(saved.Volume - stamped.Volume, 6),
        'scope': 'Nominal deboss geometry; mould detail reproduction and physical silicone remain unqualified.',
    }
    with open(MECH + '/skin-icon.json', 'w') as f:
        f.write(json.dumps(icon_report, indent=2) + '\n')
    log(name, 'R+D deboss', json.dumps(icon_report))

name = 'FlangeSkin'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
# A cosmetic update can reuse the saved, valid envelope without re-solving
# the unchanged loft. A normal run still regenerates the whole skin below.
if os.environ.get('COMPASS_STAMP_EXISTING') == '1':
    try:
        log(name, 'reusing saved native envelope')
        previous = App.openDocument(MECH + '/' + name + '.FCStd')
        source = previous.getObject('SkinEnvelope') or previous.getObject(name)
        assert source is not None and source.Shape.isValid()
        skin = source.Shape.copy()
        App.closeDocument(previous.Name)
        doc = App.newDocument(name)
        envelope = capped_slab2(FLANGE_X / 2, FLANGE_Z / 2, FLANGE_R, SHOULDER_Y, COVER_OUT_Y,
                                FLANGE_END_R, FLANGE_SIDE_R, DOCK_END_R, DOCK_SIDE_R)
        stamp_icon(doc, skin, envelope)
        log(name, 'OK')
    except Exception:
        import traceback
        log(name, 'ERROR', traceback.format_exc())
    finally:
        os._exit(0)

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
    # Smooth hull (2026-11-20): every section is one periodic B-spline through the rounded rectangle, sampled
    # on the same fixed rays (so matching points line up radially from section to section, no twist), and
    # the sections are spaced by arc length along the profile, so they bunch where the profile turns fastest.
    # The former 8-edge wires at even Y steps lofted with up to 0.11 mm bulges and dips (visible wrinkles)
    # around the convex-to-concave turn; this stays within about 0.004 mm of the two-arc profile.
    def ray_rr(hx, hz, r, th):
        c, s_ = math.cos(th), math.sin(th); ac, as_ = abs(c), abs(s_)
        t = min(hx / ac if ac > 1e-12 else 1e9, hz / as_ if as_ > 1e-12 else 1e9)
        cx, cz = hx - r, hz - r
        if t * ac > cx and t * as_ > cz:
            b = ac * cx + as_ * cz
            t = b + math.sqrt(max(b * b - (cx * cx + cz * cz - r * r), 0.0))
        return t
    def section(y):
        hx, hz = hx_at(y), hz_at(y); rc = min(R, hx, hz)
        pts = []
        for i in range(SECTION_POINTS):
            th = 2 * math.pi * i / SECTION_POINTS; t = ray_rr(hx, hz, rc, th)
            pts.append(App.Vector(t * math.cos(th), y, t * math.sin(th)))
        cu = Part.BSplineCurve()
        cu.interpolate(Points=pts, PeriodicFlag=True, Parameters=[i / SECTION_POINTS for i in range(SECTION_POINTS + 1)])
        return Part.Wire(cu.toShape())
    fine = [HULL_Y0 + (RAMP_TOP_Y - HULL_Y0) * k / 4000 for k in range(4001)]
    acc = [0.0]
    for a, b in zip(fine, fine[1:]):
        acc.append(acc[-1] + math.hypot(b - a, math.hypot(hx_at(b) - hx_at(a), hz_at(b) - hz_at(a))))
    ys, j = [], 0
    for k in range(N_SECTIONS + 1):
        target = acc[-1] * k / N_SECTIONS
        while j < len(acc) - 1 and acc[j + 1] <= target: j += 1
        ys.append(fine[j])
    ys = sorted(set(ys)); ys[0], ys[-1] = HULL_Y0, RAMP_TOP_Y
    hull = Part.makeLoft([section(y) for y in ys], True, False)
    assert hull.isValid(), 'hull loft invalid'
    # Straight-walled slab from the dock face up to HULL_Y0, its dock-side edge rounded over (EDGE_R_REAR on the
    # ends, EDGE_R_REAR_SIDE on the long sides, blended round the plan corners), concentric with the hard parts'.
    # (Built as prism + hull first, then the cap: fusing a ready capped slab onto the hull fails in OCC.)
    prism = rounded_slab(HX, HZ, R, HULL_Y0, REAR_Y + EDGE_R_REAR)
    cap = cap_loft(HX, HZ, R, REAR_Y, -1, EDGE_R_REAR, EDGE_R_REAR_SIDE)
    dock_faces = Part.Compound([f for f in cap.Faces if f.BoundBox.YMin < REAR_Y + EDGE_R_REAR - 1e-3])
    skin = prism.fuse(hull, 0.01).fuse(cap).removeSplitter()                  # fuzzy: the B-spline base meets the exact prism within ~0.004
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
    stamp_icon(doc, skin, envelope)
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
