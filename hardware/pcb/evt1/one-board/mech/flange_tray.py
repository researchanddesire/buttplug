"""FlangeTray: the open plastic tray that clamps to the turned metal body's
rear stub with the thin nut and carries the 52 x 20 mm one-board. Its body-side
edge is rounded over (R 10 on the ends, blending to R 1.6 on the long sides), its
dock-side edge too (R 3 ends, continuing across the cover; R 0.8 sides); the
board cavity is a shallow bowl (floor at Y -16, walls vertical only down to the
board's B.Cu face, then a 4 mm quarter-round into the floor) so that round-over
has wall behind it; a capsule-shaped trough along the +Z wall takes the J3/J5 tails.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/flange_tray.py
Writes mech/FlangeTray.FCStd, mech/FlangeTray.step, mech/FlangeTray.fab.json; log in build/mech/.
"""
import sys, os, math
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

# ---- parameters (mm) -------------------------------------------------------
OUT_HX, OUT_HZ, OUT_R = FLANGE_X / 2, FLANGE_Z / 2, FLANGE_R      # 28, 16, 6
FRONT_Y = SHOULDER_Y                                              # -8: front face on the metal shoulder
REAR_Y = COVER_IN_Y                                               # -23: rear face, cover seats here
IN_HX, IN_HZ = OUT_HX - WALL, OUT_HZ - WALL                       # 26.4, 14.4 cavity
IN_R = CAVITY_R                                                   # 7: wall behind the end round-over; 0.36 to the board's R2 corners
CAV_FRONT_Y = CAVITY_FRONT_Y                                      # -16: cavity floor, 1.0 over J4; the nut well goes on to -10
BOWL_R = CAVITY_BOWL_R                                            # 4: walls roll into the floor from the board's B.Cu face
FRONT_WALL_T = WALL                                               # 1.6 behind the root pad (bosses start here)
LEDGE_Y = BOARD_B_Y + 0.05                                        # board rests on ledges here (B.Cu side)
LEDGE_T = 1.0                                                     # ledge thickness along Y
LEDGE_W = 0.7                                                     # ledge width in from the cavity wall
LEDGE_L = 4.0                                                     # ledge leg length along each edge from the corner
SOCKET_CHAMFER = 0.5
PILOT_DEPTH = 6.0
COLOR = (0.16, 0.16, 0.18)                                        # black PA12
FAB = {"kind": "3dp", "name": "Flange tray (EVT1, 52 x 20 board)", "qty": 3,
       "options": {"process": "mjf", "material": "pa12", "color": "black"}}

name = 'FlangeTray'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
doc = App.newDocument(name)
try:
    # Shell: body-side edge rounded over (FLANGE_END_R on the X ends, FLANGE_SIDE_R on the long sides,
    # blended round the corners); shallow straight cavity for the board behind a thick front.
    # The dock-side edge is rounded over too (DOCK_END_R / DOCK_SIDE_R); that round-over runs on across the cover,
    # so it is built on the closed flange's envelope (front face to the cover's outer face) and the tray is the
    # part of it in front of the cover seat.
    envelope = capped_slab2(OUT_HX, OUT_HZ, OUT_R, FRONT_Y, COVER_OUT_Y, FLANGE_END_R, FLANGE_SIDE_R, DOCK_END_R, DOCK_SIDE_R)
    outer = envelope.common(box_xyz(-OUT_HX - 1, OUT_HX + 1, REAR_Y, FRONT_Y + 1, -OUT_HZ - 1, OUT_HZ + 1)).removeSplitter()
    assert outer.isValid(), 'outer shell invalid'
    # Bowl: vertical walls only down to the board's B.Cu face, then one quarter-round (BOWL_R) into the floor all the
    # way round, and a capsule-shaped trough along the +Z wall for the connector tails' loops beside J3/J5.
    cavity = rounded_slab(IN_HX, IN_HZ, IN_R, CAV_FRONT_Y, REAR_Y - 1.0)
    floor_edges = [e for e in cavity.Edges if abs(e.BoundBox.YMin - CAV_FRONT_Y) < 1e-6 and abs(e.BoundBox.YMax - CAV_FRONT_Y) < 1e-6]
    cavity = cavity.makeFillet(BOWL_R, floor_edges)
    (tx0, tx1), ty, tz, tr = WIRE_TROUGH['x'], WIRE_TROUGH['y'], WIRE_TROUGH['z'], WIRE_TROUGH['r']
    trough = Part.makeCylinder(tr, tx1 - tx0, App.Vector(tx0, ty, tz), App.Vector(1, 0, 0))
    trough = trough.fuse(Part.makeSphere(tr, App.Vector(tx0, ty, tz))).fuse(Part.makeSphere(tr, App.Vector(tx1, ty, tz))).removeSplitter()
    cavity = cavity.fuse(trough).removeSplitter()
    tray = outer.cut(cavity)
    cap_faces = [f for f in outer.Faces if f.BoundBox.YMax > FRONT_Y - FLANGE_END_R + 1e-3 and f.BoundBox.YMin < FRONT_Y - 1e-3]

    # Root pad: 2 mm of plastic between the O24 shoulder and the nut face.
    pad = cyl_y(SHOULDER_D / 2, FRONT_Y, FRONT_Y - ROOT_PAD_T)
    tray = tray.fuse(pad)

    # Cover screw bosses, full depth, stopping 2 mm short so the cover's own bosses land on them.
    for (x, z) in COVER_SCREWS:
        tray = tray.fuse(cyl_y(COVER_SCREW_BOSS_D / 2, FRONT_Y - FRONT_WALL_T, REAR_Y + COVER_GAP, x, z))

    # Corner ledges: L-shaped seats for the board's B.Cu face at its four corners
    # (the corners carry no parts; the connector edge and the ends stay open).
    for sx in (-1, 1):
        for sz in (-1, 1):
            x_wall = sx * IN_HX; z_wall = sz * IN_HZ
            x_in = sx * (BOARD_X / 2 - LEDGE_W); z_in = sz * (BOARD_Z / 2 - LEDGE_W)
            leg_x = box_xyz(x_wall, sx * (BOARD_X / 2 - LEDGE_L), LEDGE_Y, LEDGE_Y + LEDGE_T, z_wall, z_in)
            leg_z = box_xyz(x_wall, x_in, LEDGE_Y, LEDGE_Y + LEDGE_T, z_wall, sz * (BOARD_Z / 2 - LEDGE_L))
            tray = tray.fuse(leg_x).fuse(leg_z)
    tray = tray.removeSplitter()

    # Keyed collar socket: double-D (O20.2 / 18.6 AF) through the root pad, chamfered at the entrance.
    def double_d(radius, half_flat, y):
        disc = Part.makeCylinder(radius, 0.1, App.Vector(0, y, 0), App.Vector(0, 1, 0))
        keep = Part.makeBox(2 * radius + 2, 0.1, 2 * half_flat, App.Vector(-radius - 1, y, -half_flat))
        face = min(disc.common(keep).Faces, key=lambda f: abs(f.CenterOfMass.y - y))
        return face.OuterWire
    r, hf = SOCKET_D / 2, SOCKET_AF / 2
    socket = Part.makeLoft([double_d(r, hf, FRONT_Y - ROOT_PAD_T - 0.1), double_d(r, hf, FRONT_Y - SOCKET_CHAMFER),
                            double_d(r + SOCKET_CHAMFER, hf + SOCKET_CHAMFER, FRONT_Y), double_d(r + SOCKET_CHAMFER, hf + SOCKET_CHAMFER, FRONT_Y + 0.1)], True, True)
    tray = tray.cut(socket)

    # Nut rotation well behind the pad (clears the 24 AF nut's corner circle and a two-jaw driver on its X flats).
    tray = tray.cut(cyl_y(NUT_WELL_D / 2, FRONT_Y - ROOT_PAD_T, REAR_Y - 1.0))

    # Cover screw pilots from the boss tops (Y -21) into the tray (toward +Y).
    for (x, z) in COVER_SCREWS:
        tray = tray.cut(cyl_y(COVER_SCREW_PILOT_D / 2, REAR_Y + COVER_GAP - 0.1, REAR_Y + COVER_GAP + PILOT_DEPTH, x, z))
    tray = tray.removeSplitter()

    obj, feats = finish(doc, name, tray, COLOR, FAB)
    # Checks: walls behind the round-over, thinnest wall at the nut well and clearance to the stub tip / nut.
    well = cyl_y(NUT_WELL_D / 2, FRONT_Y - ROOT_PAD_T, REAR_Y - 1.0)
    cap = Part.Compound(cap_faces)
    wall_cavity = min(f.distToShape(cavity)[0] for f in cap_faces)
    wall_well = min(f.distToShape(well)[0] for f in cap_faces)
    pilot_wall = min(f.distToShape(cyl_y(COVER_SCREW_PILOT_D / 2, REAR_Y + COVER_GAP, REAR_Y + COVER_GAP + PILOT_DEPTH, x, z))[0] for f in cap_faces for (x, z) in COVER_SCREWS)
    log(name, 'round-over: ends R', FLANGE_END_R, 'sides R', FLANGE_SIDE_R, '; wall from the rounded front to the cavity', round(wall_cavity, 2), 'to the nut well', round(wall_well, 2), 'to the screw pilots', round(pilot_wall, 2))
    log(name, 'cavity floor at Y', CAV_FRONT_Y, '=', round(CAV_FRONT_Y - (BOARD_B_Y + B_PART_H), 2), 'over the tallest B.Cu part; bowl R', BOWL_R, '; wire trough', WIRE_TROUGH, 'top Y', round(ty + tr, 2), 'Z max', round(tz + tr, 2))
    # Thinnest wall anywhere between the cavity and the outside (every outer face but the open rear).
    skin_faces = [f for f in outer.Faces if f.BoundBox.YMax > REAR_Y + 1e-3]
    log(name, 'thinnest wall between the cavity and the outside', round(min(f.distToShape(cavity)[0] for f in skin_faces), 2))
    seat = [f for f in tray.Faces if abs(f.BoundBox.YMin - REAR_Y) < 1e-6 and abs(f.BoundBox.YMax - REAR_Y) < 1e-6]
    log(name, 'dock-side round-over: ends R', DOCK_END_R, 'sides R', DOCK_SIDE_R, '; cover seat spans X to', round(max(f.BoundBox.XMax for f in seat), 2), 'Z to', round(max(f.BoundBox.ZMax for f in seat), 2), '(cavity', IN_HX, IN_HZ, ')')
    well_wall = IN_HZ - NUT_WELL_D / 2
    log(name, 'nut well leaves', round(well_wall, 2), 'mm beside the cavity wall (plus', WALL, 'wall)')
    log(name, 'nut face', NUT_Y[0], 'to tallest B.Cu part', round(BOARD_B_Y + B_PART_H, 2), 'gap', round(NUT_Y[0] - (BOARD_B_Y + B_PART_H), 2))
    log(name, 'stub tip', STUB_TIP_Y, 'to board B.Cu face', BOARD_B_Y, 'gap', round(STUB_TIP_Y - BOARD_B_Y, 2))
    log(name, 'OK')
except Exception as e:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
    raise
finally:
    os._exit(0)
