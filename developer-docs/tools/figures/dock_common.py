"""Dock scene for the docs renders: imports dock.obj (one object per CAD leaf), assigns
product materials by part name and puts the lid on a hinge empty."""
import bpy, json, math, os, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_lib as R

HINGE_Y, HINGE_Z = 164.4, 40.15     # rear hinge axis (dock mm), along X

M = {
    'shell':   dict(base='#2f3237', rough=0.55),
    'orange':  dict(base='#e2632b', rough=0.45),
    'cream':   dict(base='#eee5d1', rough=0.6),
    'bezel':   dict(base='#e6dac0', rough=0.55),
    'blue':    dict(base='#2f80c4', rough=0.45),
    'dark':    dict(base='#3a3d43', rough=0.6),
    'steel':   dict(base='#b7bbc1', metallic=1.0, rough=0.3),
    'alu':     dict(base='#cfd3d8', metallic=1.0, rough=0.38),
    'gold':    dict(base='#d8b04c', metallic=1.0, rough=0.25),
    'brass':   dict(base='#c9a04a', metallic=1.0, rough=0.35),
    'nickel':  dict(base='#c4c7cc', metallic=1.0, rough=0.22),
    'pcb':     dict(base='#2c7d4f', rough=0.5),
    'ic':      dict(base='#1f2023', rough=0.45),
    'cap':     dict(base='#b98d5c', rough=0.5),
    'jst':     dict(base='#f1ede2', rough=0.6),
    'peek':    dict(base='#c8b088', rough=0.55),
    'pad':     dict(base='#d48f8f', rough=0.7),
    'lcd':     dict(base='#a9b9a7', rough=0.25),
    'lcdbord': dict(base='#151617', rough=0.4),
    'glass':   dict(base='#dfe8e4', rough=0.05),
    'flex':    dict(base='#c98a2b', rough=0.4),
    'pet':     dict(base='#dfe6ea', rough=0.3),
    'black':   dict(base='#18191b', rough=0.6),
    'w_gnd':   dict(base='#222222', rough=0.5), 'w_dm': dict(base='#f2f2f2', rough=0.5),
    'w_dp':    dict(base='#2f9b4b', rough=0.5), 'w_5v': dict(base='#d43a2f', rough=0.5),
    'w_uv':    dict(base='#e39a3b', rough=0.5),
    'led':     dict(base='#f4f4f2', rough=0.4),
    'seat':    dict(base='#b9a6d6', rough=0.6),
}


def mat_for(group, label):
    g, l = group.lower(), label.lower()
    if 'screw' in l or l.startswith('nbk') or 'screw' in g or 'accu' in l: return 'steel'
    if g == 'lowershellinstance': return 'shell'
    if g == 'uppershellinstance': return 'orange'
    if g in ('lowerchamberinstance', 'upperchamberinstance'): return 'cream'
    if g == 'scallopedbezelinstance': return 'bezel'
    if g.startswith('dockbutton'):
        return 'steel' if 'spring' in g else 'blue'
    if g in ('contactcarrierinstance', 'contactretainerinstance'): return 'dark'
    if g.startswith('contactpogo'): return 'gold' if 'plunger' in l else 'brass'
    if g.startswith('contactmagnetspring'): return 'steel'
    if g.startswith('contactmagnet'): return 'nickel'
    if g in ('customhingepininstance', 'hingeretainingwasherinstance'): return 'steel'
    if 'thermalmodule' in g:
        if '6061' in l: return 'alu'
        if 'insulator' in l: return 'pad'
        if 'sensata' in l: return 'nickel'
        if 'ntc' in l and 'clip' not in l and 'soft' not in l: return 'black'
        return 'dark'
    if 'hall sensor station' in g:
        if 'support' in l: return 'jst'
        if 'outline' in l: return 'pcb'
        if 'peek' in l: return 'peek'
        return 'ic'
    if 'captive hall magnet' in g:
        return 'nickel' if l.endswith('magnet') else 'peek'
    if g.startswith('j102'):
        if 'ground' in l: return 'w_gnd'
        if 'usbminus' in l: return 'w_dm'
        if 'usbplus' in l: return 'w_dp'
        if 'power' in l: return 'w_5v'
        return 'jst'
    if g.startswith('j401'):
        return 'jst' if 'ghr' in l or 'housing' in l else 'w_uv'
    if g.startswith('j201'): return 'flex'
    if g == 'docklcdinstance':
        if 'ffc' in l: return 'flex'
        if 'border' in l: return 'lcdbord'
        if 'viewing' in l or 'active' in l: return 'lcd'
        return 'glass'
    if g == 'lcdretentionmoduleinstance':
        if 'poron' in l: return 'black'
        if 'pet' in l: return 'pet'
        return 'dark'
    if g == 'lcdsockettrialshimsinstance': return 'jst'
    if g == 'deviceseatingmoduleinstance': return 'pet' if 'pet' in l else 'seat'
    if g.startswith('frontclosure'):
        return 'nickel' if 'k&j' in l else 'dark'
    if 'board' in g:   # PCB assemblies
        if l.startswith('pcb_'): return 'pcb'
        if l.startswith('step_models'): return 'gold'
        if '_r_' in l: return 'ic'
        if '_c_' in l: return 'cap'
        if 'jst' in l or l in ('body', 'lock'): return 'jst'
        if l == 'pins': return 'gold'
        if 'g35uvc' in l:
            return 'glass' if 'glass' in l else 'led'
        if 'sw_spst' in l: return 'ic'
        if 'open cascade' in l: return 'nickel'
        return 'ic'
    return 'dark'


def load():
    """Import the dock; returns (parts list of dicts with obj/group/side/label, lid hinge empty)."""
    meta = json.load(open(os.path.join(R.CACHE, 'dock-parts.json')))
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(R.CACHE, 'dock.obj'), forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    hinge = bpy.data.objects.new('LidHinge', None); bpy.context.scene.collection.objects.link(hinge)
    hinge.location = Vector((0, HINGE_Y, HINGE_Z)) * R.MM
    root = bpy.data.objects.new('DockRoot', None); bpy.context.scene.collection.objects.link(root)
    parts = []
    inv = Matrix.Translation(-hinge.location)        # hinge has no rotation at load: parent without moving the part
    for o in new:
        info = meta.get(o.name.split('.')[0])
        if info is None or o.type != 'MESH':
            continue
        o.scale = (R.MM, R.MM, R.MM)
        k = mat_for(info['group'], info['label'])
        R.set_material([o], R.material('dock_' + k, **M[k]))
        if info['side'] == 'LidAssembly':
            o.parent = hinge; o.matrix_parent_inverse = inv
        parts.append(dict(obj=o, **info))
    bpy.context.view_layer.update()
    R.smooth_all([p['obj'] for p in parts], angle=40)
    screen(parts)
    return parts, hinge


def screen(parts):
    """Show example status text on the LCD's active area (image from lcd_screen.svg)."""
    png = os.path.join(R.CACHE, 'lcd_screen.png')
    for p in parts:
        l = p['label'].lower()
        if p['group'] != 'DockLCDInstance':
            continue
        if l.startswith('active area') and os.path.exists(png):
            m = bpy.data.materials.new('lcd_screen'); m.use_nodes = True
            nt = m.node_tree; b = nt.nodes['Principled BSDF']
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(png)
            tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); comb = nt.nodes.new('ShaderNodeCombineXYZ')
            nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
            nt.links.new(sep.outputs['X'], comb.inputs['X']); nt.links.new(sep.outputs['Y'], comb.inputs['Y'])
            nt.links.new(comb.outputs['Vector'], tex.inputs['Vector'])
            nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
            b.inputs['Roughness'].default_value = 0.35
            p['obj'].data.materials.clear(); p['obj'].data.materials.append(m)
            p['obj'].location.z += 0.02 * R.MM
        elif l.startswith('oem 44x24 viewing'):
            R.set_material([p['obj']], R.material('lcd_bg', base='#b8c4ae', rough=0.35))
            p['obj'].location.z += 0.01 * R.MM


def open_lid(hinge, deg):
    hinge.rotation_euler = (-math.radians(deg), 0, 0)
    bpy.context.view_layer.update()


def select(parts, groups=None, side=None, labels=None):
    out = []
    for p in parts:
        if side and p['side'] != side: continue
        if groups and not any(p['group'].lower().startswith(g.lower()) for g in groups): continue
        if labels and not any(s.lower() in p['label'].lower() for s in labels): continue
        out.append(p['obj'])
    return out


def show_only(parts, objs):
    keep = set(objs)
    for p in parts:
        p['obj'].hide_render = p['obj'].hide_viewport = p['obj'] not in keep


def move(objs, vec_mm):
    for o in objs:
        mw = o.matrix_world.copy(); mw.translation += Vector(vec_mm) * R.MM; o.matrix_world = mw
    bpy.context.view_layer.update()
