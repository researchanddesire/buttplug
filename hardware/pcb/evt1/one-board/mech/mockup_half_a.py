"""Positive-Z appearance half; run with FreeCAD GUI offscreen."""
HOLE_DIAMETER_MM = 3.3
HOLE_DEPTH_MM = 4.3
HOLE_CENTERS_XY_MM = [(-15.0, -14.0), (15.0, -14.0), (0.0, 55.0)]
import sys
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
from mockup_common import build_half, run_logged
run_logged('MockupHalfA', lambda: build_half('MockupHalfA', 1,
    HOLE_DIAMETER_MM, HOLE_DEPTH_MM, HOLE_CENTERS_XY_MM))
