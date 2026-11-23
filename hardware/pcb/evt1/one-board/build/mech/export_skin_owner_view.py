import os, traceback
import FreeCAD as App, Part, ImportGui
root='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board'
log_path=root+'/build/mech/skin-owner-view-export.log'
try:
    doc=App.newDocument('SkinColorExport')
    shape=Part.Shape(); shape.read(root+'/mech/FlangeSkin.step'); shape.rotate(App.Vector(),App.Vector(0,1,0),90)
    assert shape.isValid() and len(shape.Solids)==1
    obj=doc.addObject('Part::Feature','FlangeSkin')
    obj.Shape=shape
    doc.recompute()
    obj.ViewObject.ShapeColor=(0.42,0.30,0.55)
    ImportGui.export([obj],root+'/build/mech/skin-icon-owner-view.step')
    with open(log_path,'w') as f:f.write('OK: colored stamped skin STEP exported\n')
except Exception:
    with open(log_path,'w') as f:f.write(traceback.format_exc())
finally:
    os._exit(0)
