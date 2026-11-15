"""
Home - scene 16: back on the cliff (song 4:57-5:05, the last notes).
Kaitalampi at sunset again, now with rings; she leans on his shoulder like on the first date.
The camera sinks down past the granite into the lake... to the sea floor, where the heart still glows.
"You feel like home."

Shots:  1-110   the two of them on the granite lip at sunset (as in scene 4), rings glinting; she leans on him
      111-192   the sea floor: the two halves resting together, glowing; the camera settles; fade out
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
from film import cylinder, mat, PI
from mathutils import Vector

SHOTS = dict(a=1, b=111, end=192)


def build():
    bears = film.import_bears()
    import scene04_cliff as s4, scene08_baltic as s8
    importlib.reload(s4); importlib.reload(s8)
    # the Kaitalampi set from scene 4 (world, sun, knoll, trees, lake)
    w = s4.make_world(); sun = s4.make_sun()
    env = s4.new_coll('Set'); trees = s4.new_coll('Trees')
    knoll = s4.make_knoll(env, s4.rock_material()); s4.make_shrubs(knoll)
    shores = s4.make_shores(env, s4.land_material())
    hi, lib = s4.make_tree_library(); s4.make_forest(shores, lib)
    s4.camera_sights(); s4.plant_trees(trees, hi)
    s4.make_lake(env, s4.water_material())
    he, she = s4.place_bears()
    lean_she = {'spine': (8, 6, -14), 'head': (4, 14, -20), 'shoulder.L': (14, 0, 28)}
    lean_he = {'head': (2, -8, 10), 'spine': (6, -3, 6), 'shoulder.R': (16, 0, -36), 'forearm.R': (14, 0, 0)}
    sit = {'thigh.L': (88, 0, -4), 'thigh.R': (88, 0, 4), 'shin.L': (-80, 0, 0), 'shin.R': (-80, 0, 0)}
    bears.key_pose(he, 1, dict(sit, **lean_he)); bears.key_pose(she, 1, dict(sit, **{'spine': (6, 0, 0), 'head': (-6, 0, 0)}))
    bears.key_pose(she, 40, dict(sit, **lean_she)); bears.key_pose(she, SHOTS['b'] - 1, dict(sit, **lean_she))
    bears.hold(she, 1); she.location.x += .07; bears.hold(she, 40)
    bears.set_eyes(she, 'closed', 48); bears.set_eyes(he, 'closed', 70)
    # rings on their paws
    gold = mat('RingGold16', (1, .78, .4), rough=.12, metal=1)
    for arm, bone in ((he, 'forearm.R'), (she, 'forearm.L')):
        r = cylinder(f'{arm.name}_Ring', .022, .007, (0, 0, 0), gold, n=24)
        film.attach_to_paw(r, arm, bone, (0, -.01, 0), (0, 0, PI / 2))
    # the sea floor from scene 8, far away under its own light
    uw = film.new_coll('SeaFloor'); s8.sea_floor(uw)
    UW = s8.UW
    hm = film.heart_material('Home', glow=1.6)
    hearts = film.new_coll('Hearts')
    rest = Vector((UW.x, UW.y, UW.z + .1))
    for side in ('L', 'R'):
        o = film.heart_half('Home' + side, side, .13, hm, hearts); o.location = rest; o.rotation_euler = (-.45, 0, .1)
    gl = hm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for f, v in ((SHOTS['b'], 1.0), (150, 2.2), (175, 1.4), (SHOTS['end'], 2.0)):
        gl.default_value = v; gl.keyframe_insert('default_value', frame=f)
    film.point_light('HomeGlow', rest + Vector((0, -.05, .2)), 10, (1, .3, .35), .05)
    film.HAZE.update(color=(.95, .55, .45), start=30.0, dist=260.0, strength=.6)
    # under water: the sunset sky and sun switch off at the cut, the sea's own green light takes over
    bgs = w.node_tree.nodes['Background'].inputs['Strength']
    for f, v in ((1, bgs.default_value), (SHOTS['b'], 0.0)):
        bgs.default_value = v; bgs.keyframe_insert('default_value', frame=f)
    film._const(w.node_tree)
    film.key_light(sun, 1, energy=sun.data.energy); film.key_light(sun, SHOTS['b'], energy=0.0)
    for n in ('SkyFill', 'BackBounce'):
        o = bpy.data.objects.get(n)
        if o:
            film.key_light(o, 1, energy=o.data.energy); film.key_light(o, SHOTS['b'], energy=0.0)
    # ---- cameras: on the cliff (like scene 4's wide shot), then down to the heart
    A = film.camera('Cam16a_Cliff', [(SHOTS['a'], (.55, 4.1, 1.35), (-2.4, -16.9, -1.3)), (SHOTS['b'] - 1, (.35, 3.0, 1.0), (-2.0, -16.9, -2.6))], lens=26, fstop=5.6,
                    focus=3.2)
    B = film.camera('Cam16b_Heart', [(SHOTS['b'], rest + Vector((.2, -1.6, 2.2)), rest), (SHOTS['end'], rest + Vector((.15, -.75, .32)), rest)], lens=40, fstop=2.0,
                    focus=.8)
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '16', still_frame=100)
