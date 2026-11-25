"""Colour the console-generated STEP files with a minimal offscreen GUI.

Avoids the platform's crash when creating live sketch/pocket view providers.
This export document uses read-only shape copies; native editable parts stay.
"""
PART_COLOR = (0.72, 0.73, 0.76)
PIN_COLOR = (0.30, 0.32, 0.36)
import os, traceback
from pathlib import Path
import FreeCAD as App, Part, ImportGui
MECH = Path('/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
BUILD = MECH.parent / 'build' / 'mockup'
output = open(BUILD / 'color_step.log', 'w')
try:
    for name in ['MockupHalfA', 'MockupHalfB', 'MockupAlignmentPin', 'MockupAssembly']:
        source = MECH / (name + '.step')
        shape = Part.Shape(); shape.read(str(source))
        assert shape.isValid()
        doc = App.newDocument('Color' + name)
        objects = []
        for i, solid in enumerate(shape.Solids):
            obj = doc.addObject('Part::Feature', name + str(i))
            obj.Shape = solid
            objects.append(obj)
        doc.recompute()
        for obj in objects:
            obj.ViewObject.ShapeColor = PIN_COLOR if obj.Shape.Volume < 100 else PART_COLOR
        stage = BUILD / (name + '-colored.step')
        ImportGui.export(objects, str(stage))
        check = Part.Shape(); check.read(str(stage))
        assert check.isValid() and len(check.Solids) == len(shape.Solids)
        assert abs(check.Volume - shape.Volume) < shape.Volume * 1e-5
        backup = BUILD / (name + '-before-color.step')
        if not backup.exists():
            backup.write_bytes(source.read_bytes())
        os.replace(stage, source)
        App.closeDocument(doc.Name)
        output.write(name + ' OK\n'); output.flush()
except Exception:
    output.write(traceback.format_exc())
    output.close()
    os._exit(1)
output.close()
os._exit(0)
