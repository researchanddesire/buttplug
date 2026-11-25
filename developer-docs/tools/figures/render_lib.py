"""Blender helpers for the docs figures: studio scene, CAD materials, ghosting,
exploded offsets, arrows, camera framing and 2D anchor projection.

Used by the render_*.py drivers, run with `blender -b --python <driver>`.
Units: the glTF files from FreeCAD are in metres (1 mm = 0.001).
"""
import bpy, bmesh, math, json, os, re
from mathutils import Vector, Matrix, Euler
from bpy_extras.object_utils import world_to_camera_view

MM = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
CACHE = os.path.join(DOCS, '.cache', 'figures')
STUDIO = '/Applications/Blender.app/Contents/Resources/3.5/datafiles/studiolights/world/'


def srgb(hexstr):
    """'#rrggbb' -> linear RGBA for Blender material inputs."""
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c]
    return (lin[0], lin[1], lin[2], 1.0)


# ---------------------------------------------------------------- scene
def reset(width=1600, height=1000, samples=96, background=None, hdri='studio.exr', hdri_strength=0.55,
          floor=True, exposure=0.0, look='Medium High Contrast'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = 'GPU'
    except Exception as e:
        print('GPU setup failed, CPU render:', e)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    # World: a soft studio gradient (light above, darker below) so metal reflects a horizon;
    # optionally mixed with a Blender studio HDRI for extra reflection detail.
    w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    coord = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.30; ramp.color_ramp.elements[0].color = (0.10, 0.105, 0.115, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.85, 0.86, 0.88, 1)
    mapr = nt.nodes.new('ShaderNodeMapRange')
    mapr.inputs['From Min'].default_value = -1.0; mapr.inputs['From Max'].default_value = 1.0
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = hdri_strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(coord.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
    nt.links.new(mapr.outputs['Result'], ramp.inputs['Fac'])
    if hdri:
        env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(STUDIO + hdri)
        mapping = nt.nodes.new('ShaderNodeMapping'); coord2 = nt.nodes.new('ShaderNodeTexCoord')
        mix = nt.nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs['Fac'].default_value = 0.6
        nt.links.new(coord2.outputs['Generated'], mapping.inputs['Vector'])
        nt.links.new(mapping.outputs['Vector'], env.inputs['Vector'])
        nt.links.new(ramp.outputs['Color'], mix.inputs[1]); nt.links.new(env.outputs['Color'], mix.inputs[2])
        nt.links.new(mix.outputs['Color'], bg.inputs['Color'])
        sc['hdri_mapping'] = mapping.name
    else:
        nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    # Transparent film: the annotate step composes the final image over a flat background,
    # so the background colour is exact (the view transform is not applied to it).
    sc.use_nodes = False
    sc['floor'] = floor
    return sc


def rotate_hdri(deg_z):
    m = bpy.context.scene.world.node_tree.nodes[bpy.context.scene['hdri_mapping']]
    m.inputs['Rotation'].default_value[2] = math.radians(deg_z)


def add_light(name, location, target, power, size, color=(1, 1, 1)):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = power; L.size = size; L.color = color
    o = bpy.data.objects.new(name, L); bpy.context.scene.collection.objects.link(o)
    o.location = Vector(location)
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o


def studio_lights(center, scale, power=1.0):
    """Key, fill and rim softboxes around `center` (m), sized for an object of size `scale` (m)."""
    c = Vector(center); s = scale; k = power * (s / 0.12) ** 2
    add_light('Key', c + Vector((-1.3, -1.5, 2.1)) * s, c, 14.0 * k, 1.4 * s)
    add_light('Fill', c + Vector((2.1, -1.0, 0.8)) * s, c, 5.0 * k, 1.8 * s)
    add_light('Rim', c + Vector((0.5, 2.3, 1.5)) * s, c, 9.0 * k, 1.0 * s)
    add_light('Top', c + Vector((0.0, 0.0, 2.6)) * s, c, 6.0 * k, 2.2 * s)


# ---------------------------------------------------------------- import
def import_glb(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, import_shading='NORMALS', merge_vertices=False)
    new = [o for o in bpy.data.objects if o not in before]
    coll = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(coll)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    return new


def descendants(o):
    out = [o]
    for ch in o.children:
        out += descendants(ch)
    return out


def parts_under(root_name, objects):
    """Top-level parts below an assembly root, as {label: [mesh objects]}."""
    roots = [o for o in objects if o.name == root_name or o.name.startswith(root_name + '.')]
    assert roots, 'no root ' + root_name
    root = roots[0]
    parts = {}
    for ch in root.children:
        parts[ch.name] = [o for o in descendants(ch) if o.type == 'MESH']
    return root, parts


def all_meshes(objects):
    return [o for o in objects if o.type == 'MESH']


# ---------------------------------------------------------------- materials
_mats = {}
def material(key, base, metallic=0.0, rough=0.5, sss=0.0, sheen=0.0, coat=0.0, alpha=1.0, emission=None):
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(base) if isinstance(base, str) else base
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    if sss:
        b.inputs['Subsurface'].default_value = sss
        b.inputs['Subsurface Color'].default_value = srgb(base) if isinstance(base, str) else base
        b.inputs['Subsurface Radius'].default_value = (0.002, 0.001, 0.0015)
    b.inputs['Sheen'].default_value = sheen
    b.inputs['Clearcoat'].default_value = coat
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND'
    if emission:
        b.inputs['Emission'].default_value = srgb(emission)
        b.inputs['Emission Strength'].default_value = 1.0
    _mats[key] = m
    return m


def set_material(objs, mat):
    for o in objs:
        if o.type != 'MESH':
            continue
        o.data.materials.clear()
        o.data.materials.append(mat)


def base_color_of(o):
    """Representative sRGB-linear base colour of a mesh's first material."""
    for m in o.data.materials:
        if m and m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
            return tuple(m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
    return (0.5, 0.5, 0.5, 1.0)


def ghost(objs, amount=0.7, key='ghost'):
    """Light, matte stand-in for parts already installed in earlier steps."""
    for o in objs:
        if o.type != 'MESH':
            continue
        c = base_color_of(o)
        g = tuple(c[i] * (1 - amount) + 0.62 * amount for i in range(3)) + (1.0,)
        k = '%s_%.3f_%.3f_%.3f' % (key, g[0], g[1], g[2])
        if k not in _mats:
            m = bpy.data.materials.new(k); m.use_nodes = True
            b = m.node_tree.nodes['Principled BSDF']
            b.inputs['Base Color'].default_value = g
            b.inputs['Roughness'].default_value = 0.75
            b.inputs['Specular'].default_value = 0.2
            _mats[k] = m
        o.data.materials.clear(); o.data.materials.append(_mats[k])


def smooth_all(objs, angle=35):
    for o in objs:
        if o.type == 'MESH':
            o.data.use_auto_smooth = True
            o.data.auto_smooth_angle = math.radians(angle)


# ---------------------------------------------------------------- placement
def root_transform(root, rot_euler_deg=(0, 0, 0), location=(0, 0, 0)):
    root.rotation_mode = 'XYZ'
    root.rotation_euler = Euler([math.radians(a) for a in rot_euler_deg], 'XYZ')
    root.location = Vector(location)
    bpy.context.view_layer.update()


def offset(objs, vec_mm, frame=None):
    """Move part meshes by vec_mm given in the device frame (applied in world after the root rotation)."""
    v = Vector(vec_mm) * MM
    if frame is not None:
        v = frame.to_3x3() @ v
    for o in objs:
        if o.parent is None:
            o.location += v
        else:
            # move in world space while keeping the parent link
            mw = o.matrix_world.copy(); mw.translation += v
            o.matrix_world = mw
    bpy.context.view_layer.update()


def hide(objs, hidden=True):
    for o in objs:
        o.hide_render = hidden
        o.hide_viewport = hidden


def visible_meshes():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render and not o.get('is_floor')]


def world_bbox(objs):
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi


def add_floor(z, size=2.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    f = bpy.context.active_object; f.name = 'Floor'; f['is_floor'] = True
    f.is_shadow_catcher = True
    # What metal parts see reflected below them: a mid grey table, not a white one.
    f.data.materials.append(material('floor_reflect', '#5d6066', rough=0.6))
    return f


# ---------------------------------------------------------------- arrows and markers
def arrow(start_mm, end_mm, frame, color='#e4572e', shaft_mm=0.6, head_mm=1.8, name='Arrow'):
    """3D arrow from start to end (device-frame mm, transformed by `frame` matrix)."""
    a = frame @ (Vector(start_mm) * MM); b = frame @ (Vector(end_mm) * MM)
    d = b - a; L = d.length; head = min(head_mm * MM * 1.8, L * 0.45)
    mat = material('arrow_' + color, color, rough=0.35, emission=None)
    bpy.ops.mesh.primitive_cylinder_add(radius=shaft_mm * MM / 2, depth=L - head, vertices=24)
    sh = bpy.context.active_object
    bpy.ops.mesh.primitive_cone_add(radius1=head_mm * MM / 2, radius2=0, depth=head, vertices=32)
    hd = bpy.context.active_object
    q = d.to_track_quat('Z', 'Y')
    sh.rotation_mode = hd.rotation_mode = 'QUATERNION'
    sh.rotation_quaternion = q; hd.rotation_quaternion = q
    sh.location = a + d.normalized() * (L - head) / 2
    hd.location = a + d.normalized() * (L - head / 2)
    for o in (sh, hd):
        o.data.materials.append(mat); o.name = name
    return [sh, hd]


def dashed(start_mm, end_mm, frame, dash_mm=2.0, gap_mm=1.4, radius_mm=0.18, color='#7d8792'):
    a = frame @ (Vector(start_mm) * MM); b = frame @ (Vector(end_mm) * MM)
    d = b - a; L = d.length; u = d.normalized(); t = 0.0; objs = []
    mat = material('dash_' + color, color, rough=0.5)
    q = d.to_track_quat('Z', 'Y')
    while t < L:
        seg = min(dash_mm * MM, L - t)
        bpy.ops.mesh.primitive_cylinder_add(radius=radius_mm * MM, depth=seg, vertices=12)
        o = bpy.context.active_object; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q
        o.location = a + u * (t + seg / 2); o.data.materials.append(mat); o.name = 'Dash'
        objs.append(o); t += (dash_mm + gap_mm) * MM
    return objs


# ---------------------------------------------------------------- camera
def camera(direction, lens=85, ortho=False):
    cam = bpy.data.cameras.new('Cam'); cam.lens = lens; cam.clip_start = 0.0005; cam.clip_end = 50
    if ortho:
        cam.type = 'ORTHO'
    o = bpy.data.objects.new('Cam', cam); bpy.context.scene.collection.objects.link(o)
    bpy.context.scene.camera = o
    o['dir'] = list(Vector(direction).normalized())
    return o


def frame_camera(cam, objs=None, margin=0.08, up=(0, 0, 1), target=None, margin_x=None, margin_y=None):
    """Point the camera along its 'dir' at the visible objects and fit them in the frame."""
    sc = bpy.context.scene
    objs = objs or visible_meshes()
    lo, hi = world_bbox(objs)
    pts = []
    for o in objs:
        mw = o.matrix_world
        pts += [mw @ Vector(c) for c in o.bound_box]
    center = Vector(target) if target is not None else (lo + hi) / 2
    d = Vector(cam['dir']).normalized()
    upv = Vector(up)
    if abs(d.dot(upv.normalized())) > 0.999:
        upv = Vector((0, 1, 0))
    rot = (-d).to_track_quat('-Z', 'Y')
    # build a look-at with the requested up vector
    z = d; x = upv.cross(z).normalized(); y = z.cross(x)
    R = Matrix((x, y, z)).transposed()
    cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = R.to_quaternion()
    size = (hi - lo).length
    def extents(dist, c):
        cam.location = c + d * dist
        bpy.context.view_layer.update()
        uv = [world_to_camera_view(sc, cam, p) for p in pts]
        return min(u.x for u in uv), max(u.x for u in uv), min(u.y for u in uv), max(u.y for u in uv)
    if cam.data.type == 'ORTHO':
        cam.location = center + d * size * 3
        cam.data.ortho_scale = size
        bpy.context.view_layer.update()
        for _ in range(3):
            x0, x1, y0, y1 = extents(size * 3, center)
            # recentre
            ax = (x0 + x1) / 2 - 0.5; ay = (y0 + y1) / 2 - 0.5
            center = center + x * ax * cam.data.ortho_scale + y * ay * cam.data.ortho_scale * sc.render.resolution_y / sc.render.resolution_x
            spanx = (x1 - x0); spany = (y1 - y0)
            cam.data.ortho_scale *= max(spanx, spany) / (1 - 2 * margin)
        extents(size * 3, center)
        return cam
    mx = margin if margin_x is None else margin_x
    my = margin if margin_y is None else margin_y
    aspect = sc.render.resolution_y / sc.render.resolution_x
    def search(c):
        a, b = size * 0.2, size * 60
        for _ in range(48):
            m = (a + b) / 2
            x0, x1, y0, y1 = extents(m, c)
            if x0 < mx or y0 < my or x1 > 1 - mx or y1 > 1 - my:
                a = m
            else:
                b = m
        return b
    c = center
    for it in range(5):
        dist = search(c)
        x0, x1, y0, y1 = extents(dist, c)
        fov_w = 2 * dist * math.tan(cam.data.angle_x / 2)
        c = c + x * ((x0 + x1) / 2 - 0.5) * fov_w + y * ((y0 + y1) / 2 - 0.5) * fov_w * aspect
    dist = search(c)
    extents(dist, c)
    return cam


def project(points_world):
    sc = bpy.context.scene; cam = sc.camera
    W, H = sc.render.resolution_x, sc.render.resolution_y
    out = []
    for p in points_world:
        u = world_to_camera_view(sc, cam, Vector(p))
        out.append((u.x * W, (1 - u.y) * H))
    return out


def render(path, floor_z=None, anchors=None):
    """Render to `path` (RGBA PNG). `anchors`: {name: world point} written as pixel
    positions to <path>.json for the annotate step."""
    sc = bpy.context.scene
    if sc.get('floor') and floor_z is not None:
        add_floor(floor_z)
    sc.render.filepath = path
    if anchors:
        names = list(anchors)
        px = project([anchors[n] for n in names])
        meta = {'width': sc.render.resolution_x, 'height': sc.render.resolution_y,
                'anchors': {n: [round(x, 1), round(y, 1)] for n, (x, y) in zip(names, px)}}
        with open(path + '.json', 'w') as f:
            json.dump(meta, f, indent=1)
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path)
