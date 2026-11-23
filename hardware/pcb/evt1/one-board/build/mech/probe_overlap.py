import FreeCAD as App, Part
M='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech'
tray=Part.Shape(); tray.read(M+'/FlangeTray.step')
intr=Part.Shape(); intr.read(M+'/Internals.step')
for s in intr.Solids:
    if not s.BoundBox.intersect(tray.BoundBox): continue
    c=s.common(tray)
    if c.Volume>1e-4:
        bb=c.BoundBox; print('overlap', round(c.Volume,3), 'at X %.1f..%.1f Y %.1f..%.1f Z %.1f..%.1f'%(bb.XMin,bb.XMax,bb.YMin,bb.YMax,bb.ZMin,bb.ZMax))
    # where is the wire between Y -16 and -8 ?
    for y in (-16,-14,-12,-10):
        sl=s.common(Part.makeBox(80,0.2,80,App.Vector(-40,y-0.1,-40)))
        if sl.Volume>1e-6:
            bb=sl.BoundBox; print('   solid X %.1f..%.1f Z %.1f..%.1f at Y %d'%(bb.XMin,bb.XMax,bb.ZMin,bb.ZMax,y), 'r %.1f'%max((bb.XMin**2+bb.ZMin**2)**.5,(bb.XMax**2+bb.ZMax**2)**.5,(bb.XMin**2+bb.ZMax**2)**.5,(bb.XMax**2+bb.ZMin**2)**.5))
