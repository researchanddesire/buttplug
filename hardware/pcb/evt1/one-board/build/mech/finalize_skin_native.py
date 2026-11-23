import FreeCAD as App, Part, ImportGui, os, traceback
root='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board'
try:
    doc=App.openDocument(root+'/mech/FlangeSkin.FCStd', hidden=True)
    body=doc.getObject('SiliconeSkin'); pocket=doc.getObject('IconDeboss')
    assert body is not None and pocket is not None and pocket.Shape.isValid()
    assert len(pocket.Shape.Solids)==1 and abs(pocket.Length.Value-0.25)<1e-8
    for obj in (body,pocket):
        assert obj.ViewObject is not None
        obj.ViewObject.ShapeColor=(0.42,0.30,0.55)
        obj.ViewObject.Visibility=True
    doc.getObject('SkinEnvelope').ViewObject.Visibility=False
    doc.getObject('RDIconProfile').ViewObject.Visibility=False
    doc.recompute()
    doc.save()
    with open(root+'/build/mech/skin-native-final.log','w') as f:f.write('OK: native icon sketch/pocket restored, colored, visibility saved\n')
except Exception:
    with open(root+'/build/mech/skin-native-final.log','w') as f:f.write(traceback.format_exc())
finally:
    os._exit(0)
