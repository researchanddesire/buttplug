"""RearCover: dock-side cover for the flange tray, its outer edge carrying the end
of the flange's dock-side round-over. Carries the two M1.4
board bosses (MH1, MH3), the dock-contact openings, the bores, counterbores and
inner guide boss for the two sliding button plungers, and the two M2 screws into
the tray.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/rear_cover.py
Writes mech/RearCover.FCStd, mech/RearCover.step, mech/RearCover.fab.json; log in build/mech/.
"""
import sys, os
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

# ---- parameters (mm) -------------------------------------------------------
OUT_HX, OUT_HZ, OUT_R = FLANGE_X / 2, FLANGE_Z / 2, FLANGE_R
PLATE_IN_Y, PLATE_OUT_Y = COVER_IN_Y, COVER_OUT_Y          # -23.0 .. -24.6
BOSS_TOP_Y = BOARD_F_Y                                     # board bosses meet the F.Cu face
MOUNT_PILOT_DEPTH = 3.0                                    # M1.4 x 4 through a 1.0 board
SCREW_BOSS_H = COVER_GAP                                   # 2.0 inner bosses sit on the tray's bosses
COLOR = (0.16, 0.16, 0.18)
FAB = {"kind": "3dp", "name": "Rear cover (EVT1 flange)", "qty": 3,
       "options": {"process": "mjf", "material": "pa12", "color": "black"}}

name = 'RearCover'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
doc = App.newDocument(name)
try:
    # The plate is the dock-side end of the closed flange's envelope: its outer edge carries the end of the
    # dock-side round-over the tray starts (DOCK_END_R on the X ends, DOCK_SIDE_R on the long sides).
    shell = capped_slab2(OUT_HX, OUT_HZ, OUT_R, SHOULDER_Y, PLATE_OUT_Y, FLANGE_END_R, FLANGE_SIDE_R, DOCK_END_R, DOCK_SIDE_R)
    cover = shell.common(box_xyz(-OUT_HX - 1, OUT_HX + 1, PLATE_OUT_Y - 1, PLATE_IN_Y, -OUT_HZ - 1, OUT_HZ + 1)).removeSplitter()
    for (x, z) in MOUNT_HOLES:
        cover = cover.fuse(cyl_y(MOUNT_BOSS_D / 2, PLATE_IN_Y - 0.01, BOSS_TOP_Y, x, z))
    # Inner screw bosses sit on the tray's bosses; clip them to the tray cavity so they clear its walls.
    cavity = rounded_slab(OUT_HX - WALL - 0.1, OUT_HZ - WALL - 0.1, CAVITY_R - 0.1, PLATE_IN_Y - 0.02, PLATE_IN_Y + SCREW_BOSS_H + 0.02)
    for (x, z) in COVER_SCREWS:
        boss = cyl_y(COVER_SCREW_BOSS_D / 2, PLATE_IN_Y - 0.01, PLATE_IN_Y + SCREW_BOSS_H, x, z).common(cavity)
        cover = cover.fuse(boss)
    cover = cover.removeSplitter()
    for (x, z) in MOUNT_HOLES:                                             # blind pilots for the board screws
        cover = cover.cut(cyl_y(MOUNT_PILOT_D / 2, BOSS_TOP_Y + 0.1, BOSS_TOP_Y - MOUNT_PILOT_DEPTH, x, z))
    for (x, z) in COVER_SCREWS:                                            # M2 passage + head counterbore
        cover = cover.cut(cyl_y(COVER_SCREW_PASS_D / 2, PLATE_IN_Y + SCREW_BOSS_H + 0.1, PLATE_OUT_Y - 0.1, x, z))
        cover = cover.cut(cyl_y(COVER_SCREW_HEAD_D / 2, PLATE_OUT_Y - 0.1, PLATE_OUT_Y + COVER_SCREW_HEAD_H, x, z))
    for (x, z) in CONTACTS:                                                # dock contacts show through (square bodies)
        h = CONTACT_HOLE_SQ / 2
        cover = cover.cut(box_xyz(x - h, x + h, PLATE_IN_Y + 0.1, PLATE_OUT_Y - 0.1, z - h, z + h))
    # Button plungers (ButtonPlunger.step) slide here: a boss on the inner face around each switch
    # (the two merge at 8 mm pitch), a counterbore for the retention flange, a through bore for the head.
    for (x, z) in SWITCHES:
        cover = cover.fuse(cyl_y(BUTTON_BOSS_D / 2, PLATE_IN_Y - 0.01, PLATE_IN_Y + BUTTON_BOSS_H, x, z))
    cover = cover.removeSplitter()
    for (x, z) in SWITCHES:
        cover = cover.cut(cyl_y(BUTTON_CBORE_D / 2, PLATE_IN_Y + BUTTON_BOSS_H + 0.1, PLATE_IN_Y - BUTTON_FLANGE_T, x, z))
        cover = cover.cut(cyl_y(BUTTON_BORE_D / 2, PLATE_IN_Y + 0.1, PLATE_OUT_Y - 0.1, x, z))
    cover = cover.removeSplitter()
    # Recess over C30, the 2.5 mm tall 1210 on F.Cu (the cover gap clears 1.68 mm parts only).
    r = C30_RECESS
    cover = cover.cut(box_xyz(r['x'][0], r['x'][1], PLATE_IN_Y + 0.1, PLATE_IN_Y - r['depth'], r['z'][0], r['z'][1])).removeSplitter()
    log(name, 'C30 recess', r, 'web left', round(COVER_T - r['depth'], 2))
    obj, feats = finish(doc, name, cover, COLOR, FAB)
    tip = BOARD_F_Y - CONTACT_H
    log(name, 'contact tips at Y', round(tip, 2), 'cover outer face', PLATE_OUT_Y, '-> tips', round(PLATE_OUT_Y - tip, 2), 'mm inside the cover face (negative = proud)')
    log(name, 'button boss underside at Y', round(PLATE_IN_Y + BUTTON_BOSS_H, 2), '=', round(BOARD_F_Y - (PLATE_IN_Y + BUTTON_BOSS_H), 2), 'above F.Cu; head guide', round(COVER_T - BUTTON_FLANGE_T, 2),
        'web between the counterbores', round(abs(SWITCHES[1][0] - SWITCHES[0][0]) - BUTTON_CBORE_D, 2))
    log(name, 'web under the M1.4 pilots', round(COVER_T + SCREW_BOSS_H - 0 - (MOUNT_PILOT_DEPTH - (BOSS_TOP_Y - PLATE_IN_Y)), 2),
        '; at the dock-side round-over', round(min(cyl_y(MOUNT_PILOT_D / 2, BOSS_TOP_Y, BOSS_TOP_Y - MOUNT_PILOT_DEPTH, x, z).distToShape(Part.Compound([f for f in cover.Faces if f.BoundBox.YMin < PLATE_OUT_Y + 0.05]))[0] for (x, z) in MOUNT_HOLES), 2))
    cb_rim = max(abs(z) + COVER_SCREW_HEAD_D / 2 for (x, z) in COVER_SCREWS)
    log(name, 'screw-head counterbore rim at Z', cb_rim, '; the side round-over starts at Z', OUT_HZ - DOCK_SIDE_R)
    log(name, 'OK')
except Exception:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
    raise
finally:
    os._exit(0)
