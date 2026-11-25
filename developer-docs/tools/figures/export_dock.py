"""Export the wired dock assembly as one OBJ (one object per CAD leaf) for the docs renders.

Run with FreeCAD's console (the GUI crashes opening this assembly offscreen):
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "exec(compile(open('export_dock.py').read(), 'export_dock.py', 'exec'), {'__file__': 'export_dock.py'})"
Reads hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd (read only, lid closed).
Writes .cache/figures/dock.obj and dock-parts.json (object name -> tree path, group, label).
"""
import os, json, traceback
import FreeCAD as App, Part, MeshPart
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(os.environ.get('COMPASS_DESIGN_ROOT', REPO), 'hardware/cad/evt1-assembly/evt1-wired/DockAssembly.FCStd')
CACHE = os.path.join(os.path.dirname(os.path.dirname(HERE)), '.cache', 'figures')

log = open(os.path.join(CACHE, 'export_dock.log'), 'w', buffering=1)
try:
    doc = App.openDocument(SRC)
    root = doc.getObjectsByLabel('DockAssembly')[0]
    leaves = []
    def walk(obj, sub, path, depth):
        subs = []
        try:
            subs = obj.getSubObjects()
        except Exception:
            pass
        if subs and depth < 14:
            for s in subs:
                c, _m = obj.getSubObject(s, 1, App.Matrix())
                if c is None:
                    continue
                walk(c, sub + s, path + '/' + c.Label, depth + 1)
        else:
            leaves.append((path, obj.Label, sub))
    walk(root, '', 'DockAssembly', 0)
    log.write('%d leaves\n' % len(leaves))
    out = open(os.path.join(CACHE, 'dock.obj'), 'w')
    meta = {}
    voff = 1
    n = 0
    for path, label, sub in leaves:
        parts = path.split('/')
        if len(parts) < 3 or parts[1] not in ('BaseAssembly', 'LidAssembly'):
            continue
        if parts[2] == 'DeviceAssembly':           # the old single-flange device: not the current product
            continue
        try:
            shp = Part.getShape(root, sub, needSubElement=False)
        except Exception as e:
            log.write('shape fail %s %s\n' % (path, e)); continue
        if shp.isNull() or not shp.Faces:
            continue
        if not shp.Solids and shp.Area < 1.0:
            continue
        bb = shp.BoundBox
        size = max(bb.XLength, bb.YLength, bb.ZLength)
        defl = min(0.06, max(0.004, size / 400.0))
        try:
            m = MeshPart.meshFromShape(Shape=shp, LinearDeflection=defl, AngularDeflection=0.3, Relative=False)
        except Exception as e:
            log.write('mesh fail %s %s\n' % (path, e)); continue
        if m.CountFacets == 0:
            continue
        name = 'P%04d' % n; n += 1
        meta[name] = {'path': path, 'group': parts[2], 'side': parts[1], 'label': label,
                      'bbox': [round(v, 2) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]}
        out.write('o %s\n' % name)
        pts = m.Topology[0]; facets = m.Topology[1]
        for p in pts:
            out.write('v %.4f %.4f %.4f\n' % (p.x, p.y, p.z))
        for f in facets:
            out.write('f %d %d %d\n' % (f[0] + voff, f[1] + voff, f[2] + voff))
        voff += len(pts)
    out.close()
    json.dump(meta, open(os.path.join(CACHE, 'dock-parts.json'), 'w'), indent=1)
    log.write('wrote %d objects, %d vertices\nOK\n' % (n, voff - 1))
except Exception:
    log.write(traceback.format_exc())
log.close()
