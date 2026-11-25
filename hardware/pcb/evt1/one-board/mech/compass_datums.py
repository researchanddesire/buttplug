"""Shared datums for the Compass EVT1 flange around the 52 x 20 mm one-board.

Device frame (same as hardware/cad/manufacturing-layout): Y is the body axis,
+Y toward the tip, Z up, X across the flange. The flange's dock face faces -Y.
All lengths in mm.
"""
PROJECT = '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board'
MECH = PROJECT + '/mech'
BUILD = PROJECT + '/build/mech'
METAL = MECH               # turned body, cap and thin nut: copies of hardware/cad/manufacturing-layout (DFM study, unchanged)

# --- Metal body rear joint (hardware/cad/manufacturing-layout/review.json) ---
SHOULDER_Y = -8.0          # O24 shoulder face the tray's root pad clamps against
SHOULDER_D = 24.0
COLLAR_Y = (-9.5, -8.0)    # O20 collar with 18.4 AF flats
SOCKET_D, SOCKET_AF = 20.2, 18.6
STUB_TIP_Y = -14.25        # M18x1 stub tip; wires exit the O12 bore here
NUT_Y = (-14.0, -10.0)     # 24 AF x 4 thin nut, bears on the root pad
NUT_AF = 24.0
NUT_WELL_D = 28.6          # rotation clearance for the nut's 27.7 corner circle
ROOT_PAD_T = 2.0           # pad thickness between shoulder and nut face

# --- Flange outline (was 88 x 32 for the 82 x 26 first article) ---
FLANGE_X = 56.0            # board 52 + 2 x (0.4 clearance + 1.6 wall)
FLANGE_Z = 32.0            # set by the nut well, not by the board
FLANGE_R = 8.0             # plan corners: the most the 52 mm board's R 2 corners allow inside 56 x 32 (R 10 would need the board's corners at R 4)
WALL = 1.6
DRAFT_DEG = 0.0            # printed EVT1 parts; set 2.0 for a moulded tray
# Body-side edge round-over (2026-11-18, comfort): large on the X ends, small on the long sides
# (the nut well and the cavity walls leave no room there), blended around the plan corners.
FLANGE_END_R = 10.0        # tray, X ends; the skin's is concentric (FLANGE_END_R + SKIN_T_FACE)
FLANGE_SIDE_R = 1.6        # tray, Z sides: keeps the full 1.6 wall at the cavity's front corners
# Dock-side edge round-over (2026-11-18, Lucy: the square dock edge is "way too hard"). The board goes in through the
# rear opening (52.8 wide) and its corner sits 2 mm inside the end wall and 3.6 mm under the cover face, so the hard
# parts can only take R 3 on the ends; the M2 screw heads sit 1 mm from the long sides, so those stay near-square
# under the silicone. The skin is concentric: R 4.3 on the ends (1.3..1.6 thick), R 5 on the 4 mm thick long sides.
DOCK_END_R = 3.0           # tray + cover, X ends (centre X 25, Y -21.6): 1.25 wide cover seat left at the ends
DOCK_SIDE_R = 0.8          # tray + cover, long sides: the cover-screw counterbores reach Z 15
SKIN_DOCK_END_R = 4.3
SKIN_DOCK_SIDE_R = 5.0
CAVITY_FRONT_Y = -16.0     # cavity floor, 1.0 over the tallest B.Cu part (J4 top at -16.95); the nut well still reaches -10
CAVITY_R = 7.0             # cavity plan corner radius: leaves wall behind the end round-over, 0.36 to the board's R2 corners
CAVITY_CLEAR_B = 1.0       # nominal room over the tallest B.Cu part
CAVITY_BOWL_R = 4.0        # = CAVITY_FRONT_Y - BOARD_B_Y: the cavity walls are vertical only down to the board's B.Cu face, then
                                                      # roll into the floor as one quarter-round (no flat sidewall above the board)
# Rounded trough along the +Z wall where the J3/J5 tails rise out of their plugs and loop toward the neck (to Y -14.7):
# a capsule (cylinder along X with spherical ends) tangent to the Z wall at Z 14.4; X span of the cylinder, centre (Y, Z), radius.
WIRE_TROUGH = {'x': (3.0, 20.6), 'y': -17.8, 'z': 10.0, 'r': 4.4}

# --- PCB: compass-one-board, F.Cu toward the dock (-Y), B.Cu toward the body ---
BOARD_X, BOARD_Z, BOARD_T, BOARD_R = 52.0, 20.0, 1.0, 2.0
BOARD_F_Y = -21.0          # F.Cu face
BOARD_B_Y = BOARD_F_Y + BOARD_T
BOARD_CLEAR = 0.4          # board edge to cavity wall (X); Z has spare room
F_PART_H = 1.68            # tallest F.Cu part other than the dock contacts (SW1/SW2 actuator tops, as placed)
B_PART_H = 3.05            # tallest B.Cu part (J4 housing); J3/J8/J5 ~3.0
CONTACT_H, CONTACT_SQ = 3.13, 3.2   # dock contacts CT1..CT4 above F.Cu
STEP_BOARD_T = 0.91        # board solid thickness in the KiCad STEP export

def dev(kx, ky):
    """KiCad board coordinates -> device (X, Z). Board centre (100, 100) -> (0, 0)."""
    return (kx - 100.0, 100.0 - ky)

CONTACTS = [dev(x, 107.5) for x in (102.0, 108.0, 114.0, 120.0)]   # CT1..CT4, 6 mm pitch
SWITCHES = [dev(83.0, 100.0), dev(91.0, 100.0)]                     # SW1 power, SW2 mode: Omron B3U-1000P, 3 x 2.5 body (4.0 over the leads), 8 mm pitch
MOUNT_HOLES = [dev(96.0, 108.4), dev(124.0, 91.7)]                  # MH1, MH3: O1.6, provisional M1.4
MOUNT_HOLE_D = 1.6
# B.Cu connectors opening toward +Z (the "neck" edge): ref, centre, housing X x Z, height (J8 removed 2026-11-18)
CONNECTORS = {
    'J4': (dev(98.9, 93.6), 8.0, 5.0, 3.05),
    'J3': (dev(106.7, 93.6), 4.0, 5.0, 3.0),
    'J2': (dev(113.0, 93.6), 5.0, 5.0, 3.0),     # battery, JST SM03B side entry (2026-11-19)
    'J5': (dev(119.35, 93.6), 4.0, 5.0, 3.0),    # tip NTC, JST SM02B side entry like J3 (2026-11-20; was a vertical BM02B)
}
CONNECTOR_WITHDRAW = 3.0   # straight +Z withdrawal checked for the mating plug
ANTENNA_END_X = -20.6      # ESP32-C3 antenna end (module X -20.6..-4.4 on B.Cu); keep metal away

# --- Rear cover ---
COVER_T = 1.6
COVER_GAP = 2.0            # cover inner face below the F.Cu face (clears 1.67 parts)
# C30 (47 uF 1210 on F.Cu at kx 101.8, ky 95.6, turned 90) stands 2.5 above F.Cu: a recess in the cover's
# inner face clears it by 0.3 all round (box X, Z extents and depth below COVER_IN_Y).
C30_RECESS = {'x': (0.25, 3.35), 'z': (2.5, 6.3), 'depth': 0.9}
COVER_IN_Y = BOARD_F_Y - COVER_GAP     # -23.0
COVER_OUT_Y = COVER_IN_Y - COVER_T     # -24.6
COVER_SCREWS = [(-20.0, 13.0), (20.0, -13.0)]   # M2 x 6 into tray bosses
COVER_SCREW_BOSS_D = 4.4
COVER_SCREW_PILOT_D = 1.6
COVER_SCREW_PASS_D = 2.3
COVER_SCREW_HEAD_D, COVER_SCREW_HEAD_H = 4.0, 1.2
MOUNT_BOSS_D = 3.4
MOUNT_PILOT_D = 1.15       # thread-forming M1.4 in PA12; or ream for an insert
CONTACT_HOLE_SQ = 3.8      # square opening for the 3.2 mm square contact bodies (0.3 per side)

# --- Buttons: rigid plungers that slide in the cover and are pressed through the silicone ---
# Each plunger is inserted from the cover's inner side: its flange seats in a counterbore on the
# inner face (the switch's own spring holds it seated, so the cast position is defined), its head
# slides in the through bore and stands BUTTON_PROUD into the skin, its nose rests BUTTON_PRETRAVEL
# above the switch actuator. Nothing of the mechanism opens toward the outside but the head.
SWITCH_BODY_H = 1.29       # B3U-1000P body top above F.Cu as placed in the board STEP (1.2 body + 0.085 model standoff)
SWITCH_ACT_H = 1.68        # actuator top above F.Cu as placed (1.59 + 0.085); a switch sitting flat on its pads gives 0.09 more pretravel
SWITCH_ACT_D = 1.5         # actuator diameter
SWITCH_TRAVEL = 0.15       # B3U-1000P pretravel (Omron datasheet)
BUTTON_PRETRAVEL = 0.10    # nose above the actuator at rest; total finger travel = this + SWITCH_TRAVEL
BUTTON_HEAD_D = 5.0        # head, slides in the cover's bore
BUTTON_BORE_D = 5.4        # 0.2 radial for MJF; ream to a free slide at EVT if it binds
BUTTON_PROUD = 0.4         # head above the cover's outer face, into the skin
BUTTON_HEAD_R = 0.4        # round-over of the head's top edge (what the finger feels through the skin)
BUTTON_FLANGE_D = 6.6      # retention flange; pitch 8 leaves a 1.0 web between the counterbores
BUTTON_CBORE_D = 7.0
BUTTON_FLANGE_T = 0.5      # = counterbore depth; the head guide is the remaining COVER_T - 0.5
BUTTON_BOSS_D = 8.6        # inner boss around each counterbore (the two merge), extends the flange guide
BUTTON_BOSS_H = 0.4        # its underside stays 1.6 above F.Cu, clear of the 0805s around the switches
BUTTON_NOSE_D = 2.4
BUTTON_HEAD_TOP_Y = COVER_OUT_Y - BUTTON_PROUD                    # -25.0
BUTTON_NOSE_TIP_Y = BOARD_F_Y - SWITCH_ACT_H - BUTTON_PRETRAVEL   # -22.78
BUTTON_TRAVEL = BUTTON_PRETRAVEL + SWITCH_TRAVEL                  # 0.25
SKIN_DOME_R, SKIN_DOME_H = 3.5, 0.5                               # finger-locating dome in the skin over each button

# --- Silicone skin (process reference, cast over the closed flange) ---
SKIN_T_SIDE = 1.6          # over the flange ends (X)
SKIN_T_Z = 4.0             # over the flange's long sides (Z): room for the ramp to clear the O21 ring
SKIN_T_FACE = 1.3
SKIN_FRONT_Y = -6.4        # 1.6 over the tray's front face
# Body-side hull (2026-11-18, second sketch): no flat body-side face; from SKIN_HULL_Y0 up, the skin's
# side walls curve in and run tangent into the neck ramp as one surface. Two profiles (half size, Y),
# vertical at both ends: the long sides (Z) must clear the tray's front corner (Z 16, Y -8) and cover the
# O21 ring at Y -3 by 1.3; the ends (X) start at the same height and are fuller.
# Each profile is two tangent circular arcs: a convex one of radius `r` leaving the side wall and turning
# through `turn` degrees, then a concave one that turns back the same angle and lands tangent on the neck
# circle (SKIN_NECK_R at SKIN_NECK_Y). The concave radius and the height where the wall ends follow.
SKIN_NECK_R, SKIN_NECK_Y = 8.1, 8.0      # 0.6 lip over the r 7.5 neck
SKIN_SIDE_ARC = {'r': 9.6, 'turn': 65.0}   # long sides (Z): clears the tray's front corner by 3.8, covers the O21 ring
SKIN_END_ARC = {'r': 12.0, 'turn': 80.0}   # ends (X): near-concentric with the tray's R 10 end round-over
CUFF_LAND_R, CUFF_OUTER_R = 9.75, 10.5   # bonds to the O19.5 land, flush with O21 at Y -3
CUFF_END_Y = -3.0
# Raised "this way up" arrow on the dock face (magnetometer calibration reference, as the first
# article's molded back arrow). Since 2026-11-20 (Lucy) it points -X, toward the flange end nearest the
# buttons, which is "up" for the user; it sits on the flat band above the contacts and buttons.
ARROW_Z = 9.5                 # arrow centre line
ARROW_SHAFT_X = (5.0, -1.0)   # shaft X span, tail to head
ARROW_TIP_X = -5.0            # head tip, toward the button end (-X)
ARROW_SHAFT_HW, ARROW_HEAD_HW = 0.8, 2.2   # half widths
ARROW_H = 0.4                 # raised above the dock face

# --- Turned metal body: EVT1 shoulder profile (2026-11-18), built by metal_body.py from the DFM study body ---
BODY_FLARE_Y0 = 8.0        # the neck (r 7.5) starts flaring here, tangent, just past the skin ramp's top
BODY_FLARE_Y1 = 42.0       # rejoins the study's bulb spline here, tangent and curvature-continuous
BODY_FLARE_PTS = [(8.3, 17.0), (12.1, 26.0), (15.8, 34.0)]   # (r, Y) waypoints of the new shoulder (traced from Lucy's sketch)
BODY_WALL_MIN = 2.2        # radial wall kept over the bore where it follows the new outside (O12 -> O28 transition)

# --- PCB STEP placement: STEP (sx, sy, sz) = (kx, -ky, z up from B.Cu) -> device ---
# X = sx - 100 ; Y = -(BOARD_F_Y sign) ... F.Cu face (sz = STEP_BOARD_T) lands on BOARD_F_Y
def pcb_matrix():
    import FreeCAD as App
    y0 = BOARD_F_Y + STEP_BOARD_T   # sz = 0 (B.Cu) -> y0 ; sz = 0.91 -> BOARD_F_Y
    return App.Matrix(1, 0, 0, -100.0,
                      0, 0, -1, y0,
                      0, 1, 0, 100.0,
                      0, 0, 0, 1)


# ----------------------------------------------------------------------------
# Small FreeCAD helpers shared by the part scripts (import FreeCAD lazily).
# ----------------------------------------------------------------------------
def log(name, *parts):
    import os
    os.makedirs(BUILD, exist_ok=True)
    with open(BUILD + '/' + name + '.log', 'a') as f:
        f.write(' '.join(str(p) for p in parts) + '\n')

def rounded_slab(hx, hz, r, y0, y1, cx=0.0, cz=0.0):
    """Rounded rectangle in the XZ plane (half sizes hx, hz, corner r) spanning Y y0..y1."""
    import FreeCAD as App, Part
    ya, yb = min(y0, y1), max(y0, y1)
    box = Part.makeBox(2 * hx, yb - ya, 2 * hz, App.Vector(cx - hx, ya, cz - hz))
    edges = [e for e in box.Edges if e.BoundBox.XLength < 1e-6 and e.BoundBox.ZLength < 1e-6]
    return box.makeFillet(r, edges) if r > 0 else box

def drafted_slab(hx, hz, r, y0, y1, draft_deg, grow_toward_y1=True):
    """Like rounded_slab, but lofted with a draft: the section at y1 is larger
    (or smaller) by tan(draft) x length. draft 0 falls back to the straight slab."""
    import FreeCAD as App, Part, math
    if abs(draft_deg) < 1e-9:
        return rounded_slab(hx, hz, r, y0, y1)
    d = math.tan(math.radians(draft_deg)) * abs(y1 - y0)
    s = 1 if grow_toward_y1 else -1
    w0 = rr_wire(hx, hz, r, y0)
    w1 = rr_wire(hx + s * d, hz + s * d, r + s * d, y1)
    return Part.makeLoft([w0, w1], True, True)

def capped_slab(hx, hz, r, y_front, y_rear, r_end, r_side, thetas=None):
    """rounded_slab (plan half sizes hx, hz, corner r) from y_rear to y_front whose y_front edge is
    rounded over: radius r_end on the X ends, r_side on the Z sides, blended around the plan corners.
    The cap is a loft through rounded-rectangle sections inset by the two circular round-overs."""
    import FreeCAD as App, Part, math
    thetas = thetas or [0, 3, 6, 10, 14, 18, 23, 28, 34, 40, 47, 55, 63, 72, 81, 90]
    sgn = 1 if y_front > y_rear else -1
    wires = []
    for th in reversed(thetas):                     # from the cap's start (full section) to the front face
        a = math.radians(th)
        t = r_end * (1 - math.cos(a))               # depth below the front face
        dx = r_end * (1 - math.sin(a))              # X inset on the end round-over
        dz = r_side - math.sqrt(max(r_side ** 2 - (r_side - t) ** 2, 0.0)) if t < r_side else 0.0
        wires.append(rr_wire(hx - dx, hz - dz, max(r - dz, 0.5), y_front - sgn * t))
    cap = Part.makeLoft(wires, True, False)
    prism = rounded_slab(hx, hz, r, y_rear, y_front - sgn * r_end)
    return prism.fuse(cap).removeSplitter()

def cap_loft(hx, hz, r, y_face, sgn, r_end, r_side, thetas=None):
    """The round-over cap of capped_slab alone: a loft from the full section at y_face - sgn * r_end to the face at y_face."""
    import Part, math
    thetas = thetas or [0, 3, 6, 10, 14, 18, 23, 28, 34, 40, 47, 55, 63, 72, 81, 90]
    wires = []
    for th in reversed(thetas):
        a = math.radians(th)
        t = r_end * (1 - math.cos(a))
        dx = r_end * (1 - math.sin(a))
        dz = r_side - math.sqrt(max(r_side ** 2 - (r_side - t) ** 2, 0.0)) if t < r_side else 0.0
        wires.append(rr_wire(hx - dx, hz - dz, max(r - dz, 0.5), y_face - sgn * t))
    return Part.makeLoft(wires, True, False)

def capped_slab2(hx, hz, r, y_front, y_rear, r_end_f, r_side_f, r_end_r, r_side_r):
    """capped_slab with both ends rounded over: (r_end_f, r_side_f) at y_front, (r_end_r, r_side_r) at y_rear.
    One prism between the two caps, so no coincident side faces meet in a boolean."""
    sgn = 1 if y_front > y_rear else -1
    prism = rounded_slab(hx, hz, r, y_rear + sgn * r_end_r, y_front - sgn * r_end_f)
    cap_f = cap_loft(hx, hz, r, y_front, sgn, r_end_f, r_side_f)
    cap_r = cap_loft(hx, hz, r, y_rear, -sgn, r_end_r, r_side_r)
    return prism.fuse(cap_f).fuse(cap_r).removeSplitter()

def rr_wire(hx, hz, r, y):
    import FreeCAD as App, Part, math
    V = lambda x, z: App.Vector(x, y, z)
    q = math.sqrt(0.5)
    seq = [((-hx + r, -hz), (hx - r, -hz), None), ((hx - r, -hz), (hx, -hz + r), (hx - r + r * q, -hz + r - r * q)),
           ((hx, -hz + r), (hx, hz - r), None), ((hx, hz - r), (hx - r, hz), (hx - r + r * q, hz - r + r * q)),
           ((hx - r, hz), (-hx + r, hz), None), ((-hx + r, hz), (-hx, hz - r), (-hx + r - r * q, hz - r + r * q)),
           ((-hx, hz - r), (-hx, -hz + r), None), ((-hx, -hz + r), (-hx + r, -hz), (-hx + r - r * q, -hz + r - r * q))]
    es = [Part.makeLine(V(*a), V(*b)) if m is None else Part.Arc(V(*a), V(*m), V(*b)).toShape() for a, b, m in seq]
    return Part.Wire(es)

def cyl_y(r, y0, y1, x=0.0, z=0.0):
    """Cylinder along Y from y0 to y1 (either order)."""
    import FreeCAD as App, Part
    ya, yb = min(y0, y1), max(y0, y1)
    return Part.makeCylinder(r, yb - ya, App.Vector(x, ya, z), App.Vector(0, 1, 0))

def box_xyz(x0, x1, y0, y1, z0, z1):
    import FreeCAD as App, Part
    return Part.makeBox(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), App.Vector(min(x0, x1), min(y0, y1), min(z0, z1)))

def finish(doc, name, shape, color, fab=None):
    """Validate, save <name>.FCStd, export <name>.step (coloured when the GUI is up),
    write <name>.fab.json features when fab (dict of kind/name/options) is given."""
    import FreeCAD as App, Part, json, os
    assert shape.isValid(), name + ' is not a valid shape'
    if len(shape.Solids) != 1:
        for so in shape.Solids:
            b = so.BoundBox
            log(name, 'solid', round(so.Volume, 3), 'mm3 at', [round(v, 2) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)])
    assert len(shape.Solids) == 1, '%s has %d solids' % (name, len(shape.Solids))
    obj = doc.addObject('Part::Feature', name)
    obj.Shape = shape
    doc.recompute()
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    doc.saveAs(MECH + '/' + name + '.FCStd')
    for f in os.listdir(MECH):                      # FreeCAD's .FCBak copies belong in build/, not here
        if f.endswith('.FCBak'):
            os.replace(MECH + '/' + f, BUILD + '/' + f)
    step = MECH + '/' + name + '.step'
    try:
        import ImportGui
        ImportGui.export([obj], step)
    except ImportError:
        shape.exportStep(step)
    b = shape.BoundBox
    feats = dict(volume_cm3=round(shape.Volume / 1000.0, 3), area_cm2=round(shape.Area / 100.0, 2))
    size = sorted([b.XLength, b.YLength, b.ZLength], reverse=True)
    feats.update(size_x_mm=round(size[0], 2), size_y_mm=round(size[1], 2), size_z_mm=round(size[2], 2))
    log(name, 'valid', shape.isValid(), 'bbox', [round(v, 2) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)], feats)
    if fab is not None:
        fab = dict(fab)
        fab['source'] = name + '.step'
        fab['features'] = feats
        with open(MECH + '/' + name + '.fab.json', 'w') as f:
            f.write(json.dumps(fab, indent=2) + '\n')
    return obj, feats
