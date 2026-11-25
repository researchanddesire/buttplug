import os, sys
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import MECH, BUILD
out = open(BUILD + '/color_skin.log', 'w')
try:
    s = Part.Shape(); s.read(MECH + '/FlangeSkin.step')
    assert s.isValid() and len(s.Solids) == 1
    doc = App.newDocument('SkinColor')
    o = doc.addObject('Part::Feature', 'FlangeSkin'); o.Shape = s; doc.recompute()
    o.ViewObject.ShapeColor = (0.42, 0.30, 0.55)
    import ImportGui
    ImportGui.export([o], MECH + '/FlangeSkin.step')
    t = Part.Shape(); t.read(MECH + '/FlangeSkin.step')
    out.write('OK volume %.3f -> %.3f valid %s\n' % (s.Volume, t.Volume, t.isValid()))
except Exception:
    import traceback; out.write(traceback.format_exc())
finally:
    out.close(); os._exit(0)
