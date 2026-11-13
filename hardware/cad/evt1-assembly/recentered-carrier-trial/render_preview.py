"""Render exact native tessellations; presentation only, no CAD mutation."""
from pathlib import Path
import json, math
import bpy
from mathutils import Vector

OUT=Path(__file__).resolve().parent
inputs=OUT/'preview-meshes-render-source.json'
if not inputs.exists():inputs=OUT/'preview-meshes.json'
items=json.loads(inputs.read_text())
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.device='CPU'
scene.cycles.samples=32; scene.cycles.use_denoising=True
scene.render.resolution_x=1600; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.world.use_nodes=True
background=scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value=(.8,.82,.85,1);background.inputs['Strength'].default_value=.35
scene.view_settings.view_transform='Standard'; scene.view_settings.look='Medium High Contrast'
scene.view_settings.exposure=0; scene.view_settings.gamma=1
def material(name,rgb,metallic=0):
    mat=bpy.data.materials.new(name); mat.diffuse_color=(*rgb,1); mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*rgb,1)
    bs.inputs['Metallic'].default_value=metallic; bs.inputs['Roughness'].default_value=.42
    return mat
objects={}
for item in items:
    mesh=bpy.data.meshes.new(item['name']); mesh.from_pydata(item['vertices'],[],item['triangles']); mesh.update()
    obj=bpy.data.objects.new(item['name'],mesh); scene.collection.objects.link(obj)
    obj.data.materials.append(material(item['name'],item['color'],.55 if 'Pogo' in item['name'] or 'Screw' in item['name'] else .05))
    objects[item['name']]=obj
ground=material('Warm white',(.95,.95,.94))
bpy.ops.mesh.primitive_plane_add(size=200,location=(-17,15,-.2)); bpy.context.object.data.materials.append(ground)
for name,loc,power,size in [('Key',(0,35,105),37500,70),('Fill',(-65,-20,60),22500,60),('Rim',(65,-30,80),30000,55)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=loc
    obj.rotation_euler=(Vector((-17,16,25))-obj.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Native review camera'); camera=bpy.data.objects.new('Native review camera',camera_data)
scene.collection.objects.link(camera); scene.camera=camera; camera_data.type='ORTHO'; camera_data.ortho_scale=96
def render(name,loc,target):
    camera.location=loc; camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/name); bpy.ops.render.render(write_still=True)
render('assembled-preview.png',(52,91,74),(-17,18,26))
for name,obj in objects.items():
    if 'Retainer' in name or 'MagnetSpring' in name: obj.location.y-=14
render('exploded-rear-preview.png',(-68,-94,77),(-17,8,26))
