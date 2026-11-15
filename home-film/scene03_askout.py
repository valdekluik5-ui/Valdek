"""
Home - scene 3: asking her out properly (song 0:50-1:02).
Blue hour on a lamp-lit park path in Helsinki (Esplanadi in late spring). He offers his paw; she takes it.
"I asked you out properly." / "And you chose to come."

Shots:  1-110   side two-shot: they face each other, he offers his paw
      111-200   close on their paws: hers comes to rest in his
      201-288   from behind: they walk away down the path, paw in paw, between the lamps
"""
import os, sys, math, importlib
import bpy


def _here():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        for t in bpy.data.texts:
            if t.filepath:
                return os.path.dirname(bpy.path.abspath(t.filepath))
    raise RuntimeError('Open this script from disk (film.py and bears.py must be next to it).')


sys.path.insert(0, _here())
import film
importlib.reload(film)
from film import box, cylinder, blob, mat, emit_mat, link, node_mat, add_haze, PI
import numpy as np
from mathutils import Vector

SHOTS = dict(a=1, b=111, c=201, end=288)


def blue_hour_world():
    w = bpy.data.worlds.new('BlueHour'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = 0; r.elements[0].color = (.5, .3, .32, 1)
    r.elements[1].position = .5; r.elements[1].color = (.02, .045, .14, 1)
    e = r.elements.new(.12); e.color = (.16, .16, .32, 1)
    L.new(sep.outputs['Z'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], N['Background'].inputs['Color'])
    N['Background'].inputs['Strength'].default_value = 1.0


def park(coll):
    import scene01_helsinki as s1
    importlib.reload(s1)
    rng = np.random.default_rng(3)
    gravel = mat('Gravel', (.3, .26, .2), rough=.9, haze=True)
    m, N, L, b = node_mat('ParkGrass')
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.03, .07, .02, 1); rp.color_ramp.elements[1].color = (.08, .14, .03, 1)
    L.new(nz.outputs['Fac'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
    add_haze(m, N, L, b); grass_m = m
    box('Path', (3.2, 140, .02), (0, 50, -.02), gravel, coll)
    lawn = box('Lawn', (80, 140, .01), (0, 50, -.03), grass_m, coll)
    # grass blades close to the camera and the bears
    gx, gy = np.meshgrid(np.linspace(-9, 9, 73), np.linspace(-6, 16, 89))
    gz = np.zeros_like(gx) - .015
    gr = film.grid_mesh('GrassBed', gx, gy, gz, coll, grass_m)
    w = np.clip((np.abs(gx) - 1.7) / .3, 0, 1)
    film.vgroup(gr, 'grass', w.ravel())
    gm = mat('GrassBlade', (.05, .12, .03), rough=.6)
    gr.data.materials.append(gm)
    mod = gr.modifiers.new('Grass', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 12000; s.use_advanced_hair = True; s.normal_factor = .06; s.factor_random = .03
    s.material_slot = 'GrassBlade'; s.child_type = 'INTERPOLATED'; s.rendered_child_count = 8; s.child_percent = 2; s.child_radius = .1
    s.roughness_2 = .02; s.radius_scale = .004; s.root_radius = 1; s.tip_radius = 0; s.length_random = .5
    mod.particle_system.vertex_group_density = 'grass'
    # rows of trees in fresh spring leaf, lamps, benches
    fresh = film.foliage_material('SpringLeaves', (.07, .16, .03), (.2, .32, .07), tint=(.8, .9, .4))
    bark = film.bark_material('LindenBark', (.05, .045, .04), (.09, .08, .07))
    trees = [film.birch(f'Linden{k}', 200 + k, [fresh, bark]) for k in range(3)]
    for i in range(18):
        y = -6 + i * 4.5
        for sx in (-1, 1):
            film.place_tree(coll, trees[(i + sx) % 3], (sx * rng.uniform(3.4, 4.0), y + rng.uniform(-.6, .6), 0), rng.uniform(8, 10), rng)
    iron = mat('Iron', (.02, .025, .025), rough=.35, metal=.6, haze=True)
    glass = mat('LampGlass', (.9, .85, .7), rough=.1, emission=(1, .7, .4), strength=3, transmission=.4)
    for i in range(10):
        y = -2 + i * 7
        for sx in (-1, 1):
            s1.lamp_post(f'Lamp{i}{sx}', (sx * 1.95, y, 0), coll, iron, glass)
            film.point_light(f'LampL{i}{sx}', (sx * 1.95, y, 4.3), 350, (1, .68, .38), .15)
    wood = mat('BenchWood', (.24, .13, .06), rough=.6)
    for i, y in enumerate((5.5, 19.5, 33.5)):
        for sx in (-1, 1):
            box(f'Bench{i}{sx}', (.5, 2.0, .06), (sx * 2.25, y, .3), wood, coll)
            box(f'BenchBack{i}{sx}', (.06, 2.0, .35), (sx * 2.5, y, .38), wood, coll)
    # the end of the esplanade: lit buildings
    for i, x in enumerate((-30, -10, 10, 30)):
        s1.facade_building(f'EspHouse{i}', (19, 14, 15 + 2 * (i % 2)), (x, 92, 0), [(.7, .6, .4), (.75, .7, .6), (.65, .5, .35), (.7, .66, .55)][i], coll, False)
    for m in bpy.data.materials:
        if m.name.endswith('_fx') or m.name.endswith('_fy'):
            N, L = m.node_tree.nodes, m.node_tree.links
            br = next(n for n in N if n.bl_idname == 'ShaderNodeTexBrick'); b = N['Principled BSDF']
            inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; L.new(br.outputs['Fac'], inv.inputs[1])
            k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = 2.5; L.new(inv.outputs[0], k.inputs[0])
            L.new(k.outputs[0], b.inputs['Emission Strength']); b.inputs['Emission Color'].default_value = (1, .62, .3, 1)


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(.08, .09, .18), start=20.0, dist=110.0, strength=.7)
    blue_hour_world()
    film.area_light('SkyFill', (0, -10, 12), (0, 6, 0), 900, 20, (.45, .55, 1.0))
    sets = film.new_coll('Esplanadi'); park(sets)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    # side by side on the path near a lamp, facing the camera; he turns to her and lifts his paw towards her
    y = 6.0
    bears.place(he, 1, (.27, y, 0), 0); bears.place(she, 1, (-.27, y, 0), 0)
    bears.turn_head(she, 1, yaw=0, nod=4); bears.turn_head(he, 1, nod=4)
    bears.turn_head(he, 18, yaw=0); bears.turn_head(he, 36, yaw=-38, nod=8)          # he looks at her
    offer = {'shoulder.R': (34, 0, -52), 'forearm.R': (24, 0, 0)}
    bears.key_pose(he, 40, {'shoulder.R': (0, 0, -6), 'forearm.R': (0, 0, 0)})
    bears.key_pose(he, 76, offer); bears.key_pose(he, SHOTS['c'] - 1, offer)
    # she looks at his paw, then at him... and lays her paw in his
    bears.turn_head(she, 60, yaw=0, nod=4); bears.turn_head(she, 84, yaw=30, nod=24)
    bears.turn_head(she, 112, yaw=40, nod=6, tilt=-8)
    take = {'shoulder.L': (30, 0, 46), 'forearm.L': (20, 0, 0)}
    bears.key_pose(she, 120, {'shoulder.L': (0, 0, 6), 'forearm.L': (0, 0, 0)})
    bears.key_pose(she, 160, take); bears.key_pose(she, SHOTS['c'] - 1, take)
    bears.blink(she, 168); bears.blink(he, 182)
    bears.set_eyes(she, 'heart', 172); bears.set_eyes(she, 'open', 196)
    # paw in paw, they walk away down the path
    c = SHOTS['c']
    bears.place(he, c, (-.27, 6.6, 0), 0 + PI); bears.place(she, c, (.27, 6.6, 0), PI)
    bears.walk(he, c + 2, SHOTS['end'], (-.27, 6.6, 0), (-.27, 10.4, 0), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)})
    bears.walk(she, c + 2, SHOTS['end'], (.27, 6.6, 0), (.27, 10.4, 0), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)}, phase=2)
    bears.turn_head(she, c + 40, yaw=0); bears.turn_head(she, c + 60, yaw=25, tilt=-6)
    # warm key light (as if from the lamp beside them) so their faces read
    film.area_light('BearKey', (.9, 4.0, 1.7), (0, y, .6), 45, 1.2, (1, .7, .45))
    film.area_light('BearRim', (-.6, 8.5, 1.6), (0, y, .6), 30, 1.0, (1, .66, .4))
    # where their paws meet (measured on the posed rig)
    sc = bpy.context.scene; sc.frame_set(185)
    paw = (he.matrix_world @ he.pose.bones['forearm.R'].tail + she.matrix_world @ she.pose.bones['forearm.L'].tail) / 2
    sc.frame_set(1)
    # cameras
    A = film.camera('Cam3a_Offer', [(SHOTS['a'], (.1, 3.3, .72), (0, y, .52)), (SHOTS['b'] - 1, (.05, 3.6, .7), (0, y, .52))], lens=30, fstop=2.8,
                    focus=(0, y, .5))
    B = film.camera('Cam3b_Paws', [(SHOTS['b'], paw + Vector((.15, -1.5, .25)), paw + Vector((0, 0, .18))), (SHOTS['c'] - 1, paw + Vector((.1, -1.3, .22)), paw + Vector((0, 0, .18)))],
                    lens=40, fstop=2.8, focus=1.5)
    C = film.camera('Cam3c_Away', [(SHOTS['c'], (.3, 3.0, 1.05), (0, 14, .5)), (SHOTS['end'], (.25, 4.6, 1.0), (0, 16, .5))], lens=30, fstop=4,
                    focus=(0, 8.5, .5))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '03', still_frame=180)
