"""MetalBody: the turned body of the DFM study (hardware/cad/manufacturing-layout/MetalBody.step,
unchanged there) with the EVT1 shoulder profile asked for on 2026-11-18: the r 7.5 neck no longer
meets the bulb with a kink at Y 20 but flares from BODY_FLARE_Y0, tangent to the neck, through
BODY_FLARE_PTS and rejoins the bulb spline at BODY_FLARE_Y1 with matching tangent and curvature,
revolved all round. The bore keeps its O12 neck and O28 nose, but its transition now follows the
new outside at BODY_WALL_MIN radial wall instead of the study's short cone, so the pack keeps its
room. Everything else (rear stub, collar flats, nose thread pilot, seal gland) is the study's.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/metal_body.py
Reads the study body and mech/Internals.step (for the clearance report); writes mech/MetalBody.FCStd/.step/.fab.json.
"""
import sys, os, math, json
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

STUDY = '/Users/lucianchapar/Backplane/buttplug-compass/hardware/cad/manufacturing-layout/MetalBody.step'
NECK_R_BODY, NECK_BORE_R, NOSE_BORE_R = 7.5, 6.0, 14.0
Y0, Y1 = BODY_FLARE_Y0, BODY_FLARE_Y1
COLOR = (0.76, 0.77, 0.79)
FAB = {"kind": "cnc", "name": "Turned metal body (EVT1 shoulder profile)", "qty": 3, "order": False,
       "options": {"material": "stainless_304", "finish": "none", "tolerance": "standard"}}

name = 'MetalBody'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
doc = App.newDocument(name)
V = lambda r, y: App.Vector(r, y, 0)
try:
    old = Part.Shape(); old.read(STUDY)
    assert len(old.Solids) == 1 and old.isValid()

    # The study's meridian in the XY half plane (x = r > 0): outer and bore radii at a given Y.
    sec = old.section(Part.makePlane(200, 200, App.Vector(-100, -100, 0), App.Vector(0, 0, 1)))
    def radii_at(y):
        line = Part.makeLine(App.Vector(0, y, 0), App.Vector(60, y, 0))
        hits = []
        for e in sec.Edges:
            if e.BoundBox.YMin - 1e-6 <= y <= e.BoundBox.YMax + 1e-6 and e.BoundBox.XMax > 0:
                d, pts, _ = e.distToShape(line)
                if d < 1e-5:
                    hits += [(p[0].x, e) for p in pts if p[0].x > 1e-6]
        return sorted(hits, key=lambda h: h[0])
    r_in1, outer1 = radii_at(Y1)[0][0], radii_at(Y1)[-1]
    r_out1, e_out1 = outer1[0], outer1[1]
    assert abs(radii_at(Y0)[-1][0] - NECK_R_BODY) < 1e-3 and abs(radii_at(Y0)[0][0] - NECK_BORE_R) < 1e-3, 'study neck changed'
    assert abs(r_in1 - NOSE_BORE_R) < 1e-3, 'study nose bore changed at Y1'
    # Tangent of the study's bulb spline at Y1 (pointing +Y).
    p1 = V(r_out1, Y1)
    u = e_out1.Curve.parameter(p1)
    t1 = e_out1.Curve.tangent(u)[0]
    if t1.y < 0:
        t1 = -t1
    t1.normalize()

    # New outer meridian: tangent to the neck at Y0, through the sketch waypoints, tangent to the bulb at Y1.
    pts = [V(NECK_R_BODY, Y0)] + [V(r, y) for r, y in BODY_FLARE_PTS] + [p1]
    outer = Part.BSplineCurve()
    outer.interpolate(Points=pts, InitialTangent=App.Vector(0, 1, 0), FinalTangent=t1)
    def r_outer(y):
        lo, hi = outer.FirstParameter, outer.LastParameter
        for _ in range(60):
            mid = (lo + hi) / 2
            if outer.value(mid).y < y:
                lo = mid
            else:
                hi = mid
        return outer.value((lo + hi) / 2).x
    # Inner meridian: O12 until the outside is BODY_WALL_MIN bigger, then follows it, then O28.
    def y_where_outer_is(r_target):
        lo, hi = Y0, Y1
        for _ in range(60):
            mid = (lo + hi) / 2
            if r_outer(mid) < r_target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    yi0 = y_where_outer_is(NECK_BORE_R + BODY_WALL_MIN)
    yi1 = y_where_outer_is(NOSE_BORE_R + BODY_WALL_MIN)
    n = max(8, int((yi1 - yi0) / 0.5))
    inner_pts = [V(NOSE_BORE_R, yi1)] + [V(r_outer(y) - BODY_WALL_MIN, y) for y in (yi1 - (yi1 - yi0) * k / n for k in range(1, n))] + [V(NECK_BORE_R, yi0)]
    inner = Part.BSplineCurve()
    inner.interpolate(Points=inner_pts)

    # Annular zone between Y0 and Y1, revolved; it replaces that slice of the study body.
    wire = Part.Wire([outer.toShape(),
                      Part.makeLine(p1, V(NOSE_BORE_R, Y1)),
                      Part.makeLine(V(NOSE_BORE_R, Y1), V(NOSE_BORE_R, yi1)),
                      inner.toShape(),
                      Part.makeLine(V(NECK_BORE_R, yi0), V(NECK_BORE_R, Y0)),
                      Part.makeLine(V(NECK_BORE_R, Y0), V(NECK_R_BODY, Y0))])
    assert wire.isClosed()
    zone = Part.Face(wire).revolve(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 360)
    body = old.cut(cyl_y(30.0, Y0, Y1)).fuse(zone).removeSplitter()
    assert body.isValid() and len(body.Solids) == 1, 'body fuse failed'

    # Checks: the new profile against the old and the bore, and the internals' room.
    sec2 = body.section(Part.makePlane(200, 200, App.Vector(-100, -100, 0), App.Vector(0, 0, 1)))
    def new_radii(y):
        line = Part.makeLine(App.Vector(0, y, 0), App.Vector(60, y, 0))
        xs = []
        for e in sec2.Edges:
            if e.BoundBox.YMin - 1e-6 <= y <= e.BoundBox.YMax + 1e-6:
                d, p, _ = e.distToShape(line)
                if d < 1e-5:
                    xs += [q[0].x for q in p if q[0].x > 1e-6]
        return (min(xs), max(xs)) if xs else (None, None)
    table = []
    min_wall = 99.0
    for y in [Y0 + k * 1.0 for k in range(int(Y1 - Y0) + 1)]:
        ri, ro = new_radii(y)
        oi, oo = radii_at(y)[0][0], radii_at(y)[-1][0]
        min_wall = min(min_wall, ro - ri)
        table.append({'Y': y, 'r_out': round(ro, 2), 'r_bore': round(ri, 2), 'wall': round(ro - ri, 2), 'study_r_out': round(oo, 2), 'study_r_bore': round(oi, 2)})
    gaps = []
    if os.path.exists(MECH + '/Internals.step'):
        intr = Part.Shape(); intr.read(MECH + '/Internals.step')
        for s in intr.Solids:
            bb = s.BoundBox
            if bb.YMax < Y0 - 5 or bb.YMin > Y1 + 5:
                continue
            d = s.distToShape(body)[0]
            gaps.append({'item_bbox': [round(v, 1) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)], 'gap_to_body_mm': round(d, 2)})
    obj, feats = finish(doc, name, body, COLOR, FAB)
    report = {'source': 'hardware/cad/manufacturing-layout/MetalBody.step (DFM study, unchanged)',
              'flare': {'Y0': Y0, 'Y1': Y1, 'waypoints_r_Y': BODY_FLARE_PTS, 'bulb_tangent_at_Y1': [round(t1.x, 4), round(t1.y, 4)], 'r_out_at_Y1': round(r_out1, 3)},
              'bore': {'neck_r': NECK_BORE_R, 'nose_r': NOSE_BORE_R, 'follows_outside_from_Y': round(yi0, 2), 'to_Y': round(yi1, 2), 'radial_wall': BODY_WALL_MIN,
                       'study_cone_Y': [26.12, 33.18]},
              'min_radial_wall_in_zone_mm': round(min_wall, 2), 'profile': table, 'internals_gaps': gaps,
              'volume_cm3': feats['volume_cm3'], 'study_volume_cm3': round(old.Volume / 1000.0, 3)}
    with open(MECH + '/body-profile.json', 'w') as f:
        f.write(json.dumps(report, indent=2) + '\n')
    log(name, json.dumps(report))
    log(name, 'OK')
except Exception:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
    raise
finally:
    os._exit(0)
