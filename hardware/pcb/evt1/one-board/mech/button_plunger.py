"""ButtonPlunger: rigid button that slides in the rear cover and is pressed through
the silicone skin onto a B3U-1000P tactile switch (SW1 power, SW2 mode; one part,
two per device). Modelled in the device frame at SW1; the assembly places the
second one 8 mm along +X at SW2.

Inserted from the cover's inner side before the cover goes on the tray: the flange
seats in the counterbore on the inner face, the head passes through the bore and
stands BUTTON_PROUD into the skin, the nose rests BUTTON_PRETRAVEL above the
switch actuator. The switch spring keeps the flange seated, so the plunger's
position while the skin is cast is defined; the silicone bonded over the head is
what keeps it from being pushed back in by the switch afterwards.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/button_plunger.py
Writes mech/ButtonPlunger.FCStd, mech/ButtonPlunger.step, mech/ButtonPlunger.fab.json; log in build/mech/.
"""
import sys, os
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

# ---- parameters (mm) -------------------------------------------------------
X0, Z0 = SWITCHES[0]                                       # SW1 (-17, 0)
HEAD_TOP_Y = BUTTON_HEAD_TOP_Y                             # -25.0
FLANGE_OUT_Y = COVER_IN_Y - BUTTON_FLANGE_T                # -23.5 flange seats here (counterbore floor)
FLANGE_IN_Y = COVER_IN_Y                                   # -23.0 flush with the cover's inner face at rest
NOSE_TIP_Y = BUTTON_NOSE_TIP_Y                             # -22.69
COLOR = (0.82, 0.82, 0.80)                                 # light grey PA12, reads against the black cover
FAB = {"kind": "3dp", "name": "Button plunger (EVT1 flange, 2 per device)", "qty": 8,
       "options": {"process": "mjf", "material": "pa12", "color": "gray"}}

name = 'ButtonPlunger'
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
doc = App.newDocument(name)
try:
    head = cyl_y(BUTTON_HEAD_D / 2, HEAD_TOP_Y, FLANGE_OUT_Y + 0.01, X0, Z0)
    top_edges = [e for e in head.Edges if abs(e.BoundBox.YMin - HEAD_TOP_Y) < 1e-6 and abs(e.BoundBox.YMax - HEAD_TOP_Y) < 1e-6]
    head = head.makeFillet(BUTTON_HEAD_R, top_edges)
    flange = cyl_y(BUTTON_FLANGE_D / 2, FLANGE_OUT_Y, FLANGE_IN_Y, X0, Z0)
    nose = cyl_y(BUTTON_NOSE_D / 2, FLANGE_IN_Y - 0.01, NOSE_TIP_Y, X0, Z0)
    plunger = head.fuse(flange).fuse(nose).removeSplitter()
    obj, feats = finish(doc, name, plunger, COLOR, FAB)
    log(name, 'head top Y', HEAD_TOP_Y, 'proud of cover', BUTTON_PROUD, 'silicone over head', round(HEAD_TOP_Y - (COVER_OUT_Y - SKIN_T_FACE), 2), '+ dome', SKIN_DOME_H)
    log(name, 'flange', FLANGE_OUT_Y, '..', FLANGE_IN_Y, 'nose tip', NOSE_TIP_Y, 'actuator top', round(BOARD_F_Y - SWITCH_ACT_H, 2), 'pretravel', BUTTON_PRETRAVEL)
    log(name, 'total travel', BUTTON_TRAVEL, 'flange face pressed', round(FLANGE_IN_Y + BUTTON_TRAVEL, 2), 'switch body top', round(BOARD_F_Y - SWITCH_BODY_H, 2),
        'clearance', round((BOARD_F_Y - SWITCH_BODY_H) - (FLANGE_IN_Y + BUTTON_TRAVEL), 2))
    log(name, 'length', round(NOSE_TIP_Y - HEAD_TOP_Y, 2), 'head guide in cover', round(COVER_T - BUTTON_FLANGE_T, 2), 'flange guide', BUTTON_FLANGE_T + BUTTON_BOSS_H)
    log(name, 'OK')
except Exception:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
    raise
finally:
    os._exit(0)
