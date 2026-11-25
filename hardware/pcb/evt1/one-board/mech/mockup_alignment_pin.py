"""Loose alignment dowel, three per appearance mockup; Z up."""
DIAMETER_MM = 3.0
LENGTH_MM = 8.0
END_CHAMFER_MM = 0.4
import sys
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
from mockup_common import *

def build():
    doc = App.newDocument('MockupAlignmentPin')
    body = doc.addObject('PartDesign::Body', 'AlignmentPin')
    sketch = body.newObject('Sketcher::SketchObject', 'PinProfile')
    r, c = DIAMETER_MM / 2, END_CHAMFER_MM
    pts = [(0, 0), (r-c, 0), (r, c), (r, LENGTH_MM-c), (r-c, LENGTH_MM), (0, LENGTH_MM)]
    sketch.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(1, 0, 0), 90))
    for a, b in zip(pts, pts[1:] + pts[:1]):
        i = sketch.addGeometry(Part.LineSegment(App.Vector(*a, 0), App.Vector(*b, 0)), False)
        sketch.addConstraint(Sketcher.Constraint('Block', i))
    revolution = body.newObject('PartDesign::Revolution', 'TurnedPin')
    revolution.Profile = sketch
    revolution.ReferenceAxis = (sketch, ['V_Axis'])
    revolution.Angle = 360
    doc.recompute()
    if App.GuiUp:
        sketch.ViewObject.Visibility = False
    write_part(doc, body, 'MockupAlignmentPin', body.Shape.copy(), (0.30, 0.32, 0.36), qty=3)

run_logged('MockupAlignmentPin', build)
