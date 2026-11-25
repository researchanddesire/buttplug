"""Export the device CAD to glTF for the docs renders (FreeCAD GUI, offscreen).

Run: QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD export_device.py
Reads the assembly STEPs in hardware/pcb/evt1/one-board/mech/ (read-only) and writes
developer-docs/.cache/figures/device.glb, device-cutaway.glb and screws.glb.
Screws are not in the CAD; they are modelled here at the datum positions.
"""
import os, sys, json, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MECH = os.path.join(os.environ.get('COMPASS_DESIGN_ROOT', REPO), 'hardware/pcb/evt1/one-board/mech')
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
CACHE = os.path.join(DOCS, '.cache', 'figures')

os.makedirs(CACHE, exist_ok=True)
log = open(os.path.join(CACHE, 'export_device.log'), 'w', buffering=1)
code = 1
try:
    sys.path.insert(0, MECH)
    import FreeCAD as App, Part
    from compass_datums import (COVER_SCREWS, MOUNT_HOLES, BOARD_B_Y, COVER_OUT_Y, COVER_SCREW_HEAD_H)
    App.ParamGet('User parameter:BaseApp/Preferences/Mod/Import').SetInt('ImportMode', 0)
    p = App.ParamGet('User parameter:BaseApp/Preferences/Mod/Part')
    p.SetFloat('MeshDeviation', 0.02); p.SetFloat('MeshAngularDeflection', 4.0)
    import ImportGui

    def export_step(step, glb):
        doc = App.newDocument(os.path.splitext(os.path.basename(glb))[0].replace('-', '_'))
        ImportGui.insert(step, doc.Name)
        doc.recompute()
        roots = [o for o in doc.Objects if not o.InList]
        ImportGui.export(roots, glb)
        log.write('%s -> %s (%d bytes)\n' % (step, glb, os.path.getsize(glb)))
        App.closeDocument(doc.Name)

    export_step(MECH + '/compass-device.step', CACHE + '/device.glb')
    export_step(MECH + '/compass-device-cutaway.step', CACHE + '/device-cutaway.glb')

    # Screws, modelled as socket cap screws at the datum positions (axis, head base, direction).
    V = App.Vector
    def screw(d, length, head_d, head_h, socket_af):
        shank = Part.makeCylinder(d / 2, length, V(0, 0, -length), V(0, 0, 1))
        head = Part.makeCylinder(head_d / 2, head_h, V(0, 0, 0), V(0, 0, 1))
        try:
            head = head.makeFillet(head_h * 0.25, [e for e in head.Edges if abs(e.BoundBox.ZMax - head_h) < 1e-6])
        except Exception:
            pass
        import math
        r = socket_af / 2 / math.cos(math.radians(30))
        hexw = Part.makePolygon([V(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k)), head_h + 0.01) for k in range(7)])
        sock = Part.Face(hexw).extrude(V(0, 0, -head_h * 0.6))
        return shank.fuse(head.cut(sock)).removeSplitter()
    sdoc = App.newDocument('Screws')
    objs = []
    def place(shape, name, base, axis):
        """axis: unit vector pointing from the head toward the tip (insertion direction)."""
        sh = shape.copy()
        rot = App.Rotation(V(0, 0, -1), axis)
        sh.Placement = App.Placement(base, rot)
        o = sdoc.addObject('Part::Feature', name)
        o.Shape = sh
        o.ViewObject.ShapeColor = (0.72, 0.73, 0.75)
        objs.append(o)
    m2x6 = screw(2.0, 6.0, 3.8, COVER_SCREW_HEAD_H, 1.5)
    for i, (x, z) in enumerate(COVER_SCREWS):
        # Head flush with the cover's outer face in its counterbore, tip toward +Y (into the tray bosses).
        place(m2x6, 'CoverScrew_M2x6_%d' % (i + 1), V(x, COVER_OUT_Y + COVER_SCREW_HEAD_H, z), V(0, 1, 0))
    m14x4 = screw(1.4, 4.0, 2.5, 0.9, 0.9)
    for i, (x, z) in enumerate(MOUNT_HOLES):
        # Through the board from its B.Cu side into the cover bosses: head on B.Cu, tip toward -Y.
        place(m14x4, 'PcbScrew_M1_4x4_%d' % (i + 1), V(x, BOARD_B_Y, z), V(0, -1, 0))
    m14x5 = screw(1.4, 5.0, 2.5, 0.9, 0.9)
    for i, (x, y) in enumerate([(-5.0, 29.8), (5.0, 29.8), (-8.0, 66.7), (8.0, 66.7)]):
        # Down through the guide's ears (top Z 4.7) into the cradle bosses.
        place(m14x5, 'GuideScrew_M1_4x5_%d' % (i + 1), V(x, y, 4.7), V(0, 0, -1))
    sdoc.recompute()
    ImportGui.export(objs, CACHE + '/screws.glb')
    log.write('screws -> %d objects\n' % len(objs))
    code = 0
except Exception:
    log.write(traceback.format_exc())
finally:
    log.close()
    os._exit(code)
