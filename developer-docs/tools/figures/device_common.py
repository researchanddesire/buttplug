"""Device scene for the docs renders: imports device.glb (+ screws), applies the
product materials and exposes the parts by name."""
import bpy, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_lib as R

# Product materials (sRGB hex).
MAT = {
    'metal':    dict(base='#c4c7cc', metallic=1.0, rough=0.12),
    'nut':      dict(base='#8e9298', metallic=1.0, rough=0.32),
    'pa12':     dict(base='#2a2b2e', rough=0.62),
    'silicone': dict(base='#6c3f99', rough=0.45, sheen=0.2),
    'button':   dict(base='#d9d9d4', rough=0.55),
    'rubber':   dict(base='#121214', rough=0.55),
    'cradle':   dict(base='#e07a26', rough=0.6),
    'guide':    dict(base='#f0b13c', rough=0.6),
    'screw':    dict(base='#b9bcc2', metallic=1.0, rough=0.3),
}

# Short names for the parts in device.glb (FreeCAD labels -> key).
def key_for(label):
    l = label.lower()
    if l.startswith('metalbody'): return 'body'
    if l.startswith('motorthermistorcap'): return 'cap'
    if l.startswith('thinrearnut'): return 'nut'
    if l.startswith('flangetray'): return 'tray'
    if l.startswith('rearcover'): return 'cover'
    if l.startswith('flangeskin'): return 'skin'
    if l.startswith('buttonsw1'): return 'button1'
    if l.startswith('buttonsw2'): return 'button2'
    if l.startswith('pcb'): return 'pcb'
    if l.startswith('internals'): return 'internals'
    if l.startswith('cap face seal') or l.startswith('capfaceseal'): return 'oring'
    if l.startswith('internal cradle'): return 'cradle'
    if l.startswith('removable four-wire guide'): return 'guide'
    return None

MAT_FOR = {'body': 'metal', 'cap': 'metal', 'nut': 'nut', 'tray': 'pa12', 'cover': 'pa12', 'skin': 'silicone',
           'button1': 'button', 'button2': 'button', 'oring': 'rubber', 'cradle': 'cradle', 'guide': 'guide'}


def internals_split(objs):
    """Split the Internals meshes into pack, motor, tip sensor, plugs, wires, pads."""
    groups = {'pack': [], 'motor': [], 'tip': [], 'plugs': [], 'wires': [], 'pads': []}
    for o in objs:
        n = o.name.lower()
        if 'pad' in n and 'support' in n: groups['pads'].append(o)
        elif n.split('.')[0] in ('pack p', 'pack n', 'pack ntc'): groups['wires'].append(o)
        elif n.startswith('pack') : groups['pack'].append(o)
        elif n.startswith('motor nfp') or n.startswith('motor_nfp'): groups['motor'].append(o)
        elif n.startswith('tip ntc head') or n.startswith('tip ntc potting') or n.startswith('tip_ntc_head') or n.startswith('tip_ntc_potting'): groups['tip'].append(o)
        elif 'plug' in n: groups['plugs'].append(o)
        else: groups['wires'].append(o)
    return groups


def _load_set(glb, suffix, coll):
    objs = R.import_glb(os.path.join(R.CACHE, glb), coll)
    root, by_label = R.parts_under('CompassDevice', objs)
    parts = {}
    for label, meshes in by_label.items():
        k = key_for(label)
        if k is None:
            continue
        parts.setdefault(k + suffix, []).extend(meshes)
    for k, m in MAT_FOR.items():
        if k + suffix in parts:
            R.set_material(parts[k + suffix], R.material(m, **MAT[m]))
    if 'internals' + suffix in parts:
        for gk, gv in internals_split(parts['internals' + suffix]).items():
            parts['int_' + gk + suffix] = gv
    return root, parts


def load(screws=True, cut=False, whole=True, frame_rot=(90, 0, 0)):
    """Import the device; returns (roots, parts dict key -> [meshes], frame matrix).
    whole: device.glb parts (keys 'body', 'cap', ...); cut: device-cutaway.glb parts with
    keys suffixed '_cut' (enclosure halved at Z = 0, +Z half removed).
    frame_rot rotates the device frame (Y = axis to the tip, Z up) into the world.
    The default (90, 0, 0) stands the device on its dock face, tip up."""
    roots, parts = [], {}
    if whole:
        r, p = _load_set('device.glb', '', 'device'); roots.append(r); parts.update(p)
    if cut:
        r, p = _load_set('device-cutaway.glb', '_cut', 'device_cut'); roots.append(r); parts.update(p)
    if screws:
        sobjs = R.import_glb(os.path.join(R.CACHE, 'screws.glb'), 'screws')
        for o in sobjs:
            if o.parent is None:
                o.parent = roots[0]
        meshes = [o for o in sobjs if o.type == 'MESH']
        R.set_material(meshes, R.material('screw', **MAT['screw']))
        for o in meshes:
            n = o.name.lower()
            k = 'screws_cover' if n.startswith('coverscrew') else 'screws_pcb' if n.startswith('pcbscrew') else 'screws_guide'
            parts.setdefault(k, []).append(o)
    R.smooth_all([o for v in parts.values() for o in v])
    for r in roots:
        R.root_transform(r, frame_rot)
    frame = roots[0].matrix_world.copy()
    return roots, parts, frame


def dev_point(frame, p_mm):
    """Device-frame point (mm) -> world (m)."""
    return frame @ (Vector(p_mm) * R.MM)
