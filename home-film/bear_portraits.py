"""
Home - reference portraits of the two bears (for AI video tools: "image to video" / character reference).
Plain warm backdrop, soft studio light. Renders into renders/portraits/ next to this file.

  blender -b --python bear_portraits.py -- [--samples 96] [--engine cycles|eevee]
"""
import os, sys, math, importlib
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bears
importlib.reload(bears)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = dict(samples='96', engine='cycles', out=os.path.join(HERE, 'renders', 'portraits'))
for i in range(0, len(argv) - 1, 2):
    opt[argv[i].lstrip('-')] = argv[i + 1]
os.makedirs(opt['out'], exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---- backdrop: a soft curved warm-cream sweep
me = bpy.data.meshes.new('Sweep')
verts, faces = [], []
for j in range(25):
    t = j / 24
    y = -30 + 33 * min(t / .7, 1)
    z = 0 if t < .7 else 4 * (1 - math.cos((t - .7) / .3 * math.pi / 2))
    if t >= .7:
        y = 3 + 1.2 * math.sin((t - .7) / .3 * math.pi / 2)
    verts += [(-30, y, z), (30, y, z)]
for j in range(24):
    a = 2 * j
    faces.append((a, a + 1, a + 3, a + 2))
me.from_pydata(verts, [], faces); me.shade_smooth()
mat = bpy.data.materials.new('Backdrop'); mat.use_nodes = True
b = mat.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (.62, .5, .4, 1); b.inputs['Roughness'].default_value = 1
me.materials.append(mat)
sweep = bpy.data.objects.new('Sweep', me); sc.collection.objects.link(sweep)

w = bpy.data.worlds.new('Studio'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (.9, .82, .75, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = .5


def area(name, loc, energy, size, color, target=(0, 0, .5)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size; ld.color = color
    o = bpy.data.objects.new(name, ld); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


area('Key', (-2.2, -2.6, 2.6), 260, 2.5, (1, .9, .8))
area('Fill', (2.6, -2.2, 1.2), 90, 3, (.9, .9, 1))
area('Rim', (1.2, 2.4, 2.4), 220, 1.5, (1, .85, .7))

he = bears.build_bear('he', location=(.29, 0, 0), rotation_z=math.radians(-12))
she = bears.build_bear('she', location=(-.29, 0, 0), rotation_z=math.radians(12))

cd = bpy.data.cameras.new('Cam'); cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
cam = bpy.data.objects.new('Cam', cd); sc.collection.objects.link(cam); sc.camera = cam

r = sc.render
r.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'
try:
    sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
if opt['engine'] == 'cycles':
    r.engine = 'CYCLES'; sc.cycles.samples = int(opt['samples']); sc.cycles.use_denoising = True
    sc.cycles_curves.shape = 'THICK'
else:
    r.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = int(opt['samples']); sc.eevee.use_raytracing = True
    r.hair_type = 'STRIP'; r.hair_subdiv = 1


def shot(name, loc, target, lens, res, eyes=0, show=('he', 'she')):
    for arm, key in ((he, 'he'), (she, 'she')):
        arm['eyes'] = float(eyes)
        for o in arm.users_collection[0].objects:
            o.hide_render = key not in show
    cam.location = loc; cd.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    r.resolution_x, r.resolution_y = res
    bpy.context.view_layer.update()
    r.filepath = os.path.join(opt['out'], name)
    bpy.ops.render.render(write_still=True)
    print('saved', r.filepath)


shot('bears_together.png', (0, -4.3, .8), (0, 0, .5), 50, (1024, 1536))
shot('bear_him.png', (1.0, -3.0, .75), (.29, 0, .5), 50, (1024, 1024), show=('he',))
shot('bear_her.png', (-1.0, -3.0, .72), (-.29, 0, .47), 50, (1024, 1024), show=('she',))
shot('bears_heart_eyes.png', (0, -3.0, .8), (0, 0, .7), 60, (1024, 1024), eyes=2)
shot('bears_side.png', (4.0, -.9, .6), (0, 0, .48), 50, (1536, 1024))
