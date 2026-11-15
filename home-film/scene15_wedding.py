"""
Home - scene 15: the wedding (song 4:47-4:57, the final peak). A flower arch, petals, rings, a kiss.
(The real place and details can be added later; this is a sunny garden by a lake with a white flower arch.)

Shots:  1-90    the garden: chairs with ribbons, a white flower arch; they stand under it; petals start to fall
       91-170   close: the rings - he slips the ring on her paw; she on his
      171-240   the kiss under the arch; heart eyes; a shower of petals; the camera rises
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

SHOTS = dict(a=1, b=91, c=171, end=240)


def garden(coll):
    lawn = mat('WeddingLawn', (.08, .18, .04), rough=.9, haze=True)
    xs = np.linspace(-120, 120, 121); X, Y = np.meshgrid(xs, xs)
    Z = np.where(Y < -25, -1.0, 0.0) + np.clip((np.hypot(X, Y) - 70) / 30, 0, 1) * (6 + 6 * film.fbm(X / 40, Y / 40, 3))
    land = film.grid_mesh('Lawn', X, Y, Z, coll, lawn)
    film.vgroup(land, 'forest', (np.hypot(X, Y) > 75).astype(float).ravel())
    hi, lib = film.tree_library('WeddingTrees')
    film.scatter_instances(land, lib, 'forest', 2500, 14, seed=15)
    lake = film.water_material('WeddingLake', color=(.04, .07, .09), rough=.05, wave=.15)
    film.mesh_obj('WeddingLake', [(-300, -26, -.6), (300, -26, -.6), (300, -300, -.6), (-300, -300, -.6)], [(0, 1, 2, 3)], coll, [lake])
    film.meadow('WeddingMeadow', (0, 0), (24, 30), coll, keep_clear=[(0, -4, 1.6), (0, 2.5, 1.0)], seed=15)
    # rose bushes and lanterns along the aisle
    bush = mat('RoseBush', (.04, .12, .03), rough=.6); bloom = mat('RoseBloom', (.85, .35, .4), rough=.5, sss=.3)
    lant = film.emit_mat('Lantern', (1, .75, .45), 8)
    for i, y in enumerate((0.0, 2.4, 4.8, 7.2)):
        for sx in (-1, 1):
            blob(f'Bush{i}{sx}', (sx * 3.3, y, .3), (.35, .35, .32), coll, bush, sub=2, rough=.3, seed=i * 2 + (sx > 0))
            for k in range(5):
                blob(f'BushBloom{i}{sx}{k}', (sx * 3.3 + .25 * math.cos(k * 1.3), y + .25 * math.sin(k * 1.3), .45 + .08 * (k % 2)), (.05, .05, .05), coll, bloom, sub=1, seed=k)
            cylinder(f'LanternPole{i}{sx}', .015, .9, (sx * .8, y + 1.2, 0), mat('LanternIron', (.05, .05, .05), rough=.4, metal=.6), coll, n=6)
            blob(f'LanternGlow{i}{sx}', (sx * .8, y + 1.2, .95), (.05, .05, .07), coll, lant, sub=1)
    # the arch: two posts and a curved top, covered in white and blush roses with green leaves
    white = mat('ArchWood', (.85, .84, .8), rough=.6)
    for sx in (-1, 1):
        cylinder(f'ArchPost{sx}', .05, 2.2, (sx * 1.1, -4, 0), white, coll, n=10)
    rose_w = mat('RoseWhite', (.9, .88, .85), rough=.5, sss=.3); rose_p = mat('RoseBlush', (.95, .6, .62), rough=.5, sss=.3)
    leaf = mat('ArchLeaf', (.05, .14, .04), rough=.6)
    rng = np.random.default_rng(3)
    pts = [(x, 2.2 + .5 * math.cos(x / 1.1 * PI / 2)) for x in np.linspace(-1.1, 1.1, 18)]
    for i in range(140):
        if i < 90:
            x, z = pts[rng.integers(len(pts))]
            p = (x + rng.normal(0, .08), -4 + rng.normal(0, .1), z + rng.normal(0, .08))
        else:
            sx = rng.choice([-1, 1]); p = (sx * 1.1 + rng.normal(0, .08), -4 + rng.normal(0, .08), rng.uniform(.2, 2.2))
        m = leaf if rng.random() < .4 else (rose_p if rng.random() < .35 else rose_w)
        r = rng.uniform(.06, .12)
        blob(f'ArchFlower{i}', p, (r, r, r * .8), coll, m, sub=2, rough=.25, seed=i)
    # the aisle: a runner and rows of white chairs with ribbons
    runner = mat('Runner', (.85, .82, .76), rough=.9)
    box('Runner', (1.2, 12, .01), (0, 2.5, 0), runner, coll)
    chair = mat('Chair', (.9, .9, .88), rough=.5); ribbon = mat('Ribbon', (.9, .65, .66), rough=.6)
    for row in range(5):
        for side in (-1, 1):
            for k in range(3):
                x = side * (1.1 + k * .65); y = 1.0 + row * 1.2
                box(f'Seat{row}{side}{k}', (.45, .45, .05), (x, y, .45), chair, coll)
                box(f'Back{row}{side}{k}', (.45, .04, .5), (x, y + .21, .45), chair, coll)
                for lx in (-.2, .2):
                    for ly in (-.2, .2):
                        box(f'Leg{row}{side}{k}{lx}{ly}', (.03, .03, .45), (x + lx, y + ly, 0), chair, coll)
                if k == 0:
                    blob(f'Bow{row}{side}', (x - side * .2, y + .23, .9), (.06, .03, .05), coll, ribbon, sub=1)


def petals(coll, f0, f1, center, n=220, spread=2.5, height=4.0, seed=1):
    pm = [mat('PetalPink', (.95, .55, .6), rough=.5, sss=.2), mat('PetalWhite', (.95, .93, .9), rough=.5, sss=.2)]
    rng = np.random.default_rng(seed)
    for i in range(n):
        o = blob(f'Petal{seed}_{i}', center, (.025, .018, .004), coll, pm[i % 2], sub=1, rough=.1, seed=i)
        start = int(rng.uniform(f0, f1 - 40)); dur = int(rng.uniform(50, 90))
        x0 = Vector((rng.normal(0, spread), rng.normal(0, spread * .6), height + rng.uniform(0, 1.5)))
        film.key_visible(o, 1, False); film.key_visible(o, start, True)
        for k in range(5):
            t = k / 4
            o.location = center + x0 + Vector((.4 * math.sin(t * 6 + i), .3 * math.cos(t * 5 + i), -t * height))
            o.rotation_euler = (t * 9 + i, t * 7, t * 5)
            o.keyframe_insert('location', frame=start + t * dur); o.keyframe_insert('rotation_euler', frame=start + t * dur)


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(1, .9, .8), start=40.0, dist=400.0, strength=.4)
    w, sky, bg, ramp = film.make_sky(elev=20, az=-130, strength=.35, low=(1, .85, .7), mid=(1, .92, .85), high=(.75, .82, 1.0))
    sun = film.make_sun(elev=20, az=-130, energy=2.8, color=(1, .88, .7))
    bpy.context.scene.view_settings.exposure = -.2
    g = film.new_coll('Garden'); garden(g)
    film.area_light('ArchFill', (0, 1.5, 2.2), (0, -4, .8), 150, 3, (1, .85, .7))
    he = bears.build_bear('he'); she = bears.build_bear('she')
    # a tiny bow tie for him (she wears her rose)
    tie = mat('BowTie', (.05, .05, .06), rough=.5)
    bt = blob('BowTie', (0, 0, 0), (.07, .025, .035), film.new_coll('Outfits'), tie, sub=2, rough=.1)
    bt.parent = he; bt.parent_type = 'BONE'; bt.parent_bone = 'spine'; bt.location = (0, .1, -.2)
    # standing under the arch, facing each other
    y = -4.0
    bears.place(he, 1, (-.42, y, 0), bears.facing(1, .25)); bears.place(she, 1, (.42, y, 0), bears.facing(-1, .25))
    bears.turn_head(she, 30, nod=4); bears.turn_head(he, 30, nod=4)
    # rings: he holds her paw, slides the ring on; then she does
    b_ = SHOTS['b']
    hold_he = {'shoulder.R': (70, 0, -6), 'forearm.R': (14, 0, 0), 'shoulder.L': (70, 0, 6), 'forearm.L': (14, 0, 0), 'spine': (10, 0, 0), 'head': (14, 0, 0)}
    hold_she = {'shoulder.L': (68, 0, 4), 'forearm.L': (14, 0, 0), 'shoulder.R': (40, 0, -4), 'forearm.R': (20, 0, 0), 'spine': (10, 0, 0), 'head': (14, 0, 0)}
    bears.key_pose(he, b_, hold_he); bears.key_pose(she, b_, hold_she)
    gold = mat('WeddingGold', (1, .78, .4), rough=.12, metal=1)
    rings = film.new_coll('Rings')
    r1 = cylinder('RingHers', .02, .006, (0, 0, 0), gold, rings, n=24); r1.rotation_euler = (0, PI / 2, 0)
    r2 = cylinder('RingHis', .022, .006, (0, 0, 0), gold, rings, n=24); r2.rotation_euler = (0, PI / 2, 0)
    film.attach_to_paw(r1, she, 'forearm.L', (0, .0, 0), (0, 0, PI / 2))
    film.attach_to_paw(r2, he, 'forearm.R', (0, .0, 0), (0, 0, PI / 2))
    film.key_visible(r1, 1, False); film.key_visible(r1, b_ + 30, True)
    film.key_visible(r2, 1, False); film.key_visible(r2, b_ + 62, True)
    bears.set_eyes(she, 'heart', b_ + 34); bears.set_eyes(she, 'open', b_ + 58); bears.set_eyes(he, 'heart', b_ + 66)
    # the kiss: they lean in, noses touch, eyes close; petals shower down
    c = SHOTS['c']
    bears.set_eyes(he, 'open', c)
    kiss_he = {'spine': (8, 0, 0), 'head': (2, 0, 0), 'shoulder.L': (60, 0, -30), 'shoulder.R': (60, 0, 30), 'forearm.L': (40, 0, 0), 'forearm.R': (40, 0, 0)}
    kiss_she = {'spine': (8, 0, 0), 'head': (-6, 0, 6), 'shoulder.L': (60, 0, -30), 'shoulder.R': (60, 0, 30), 'forearm.L': (40, 0, 0), 'forearm.R': (40, 0, 0)}
    bears.key_pose(he, c + 4, hold_he); bears.key_pose(she, c + 4, hold_she)
    bears.key_pose(he, c + 24, kiss_he); bears.key_pose(she, c + 24, kiss_she)
    bears.hold(he, c + 4); bears.hold(she, c + 4)
    he.location.x = -.39; she.location.x = .39
    bears.hold(he, c + 24); bears.hold(she, c + 24)
    bears.set_eyes(he, 'closed', c + 22); bears.set_eyes(she, 'closed', c + 20)
    petals(film.new_coll('Petals'), 10, SHOTS['end'], Vector((0, y + .5, 0)), n=260)
    # ---- cameras
    A = film.camera('Cam15a_Garden', [(SHOTS['a'], (.4, 9.5, 1.6), (0, -4, 1.1)), (SHOTS['b'] - 1, (.3, 6.0, 1.4), (0, -4, 1.0))], lens=26, fstop=4, focus=11.0)
    sc = bpy.context.scene; sc.frame_set(b_ + 40)
    paws = (he.matrix_world @ he.pose.bones['forearm.R'].tail + she.matrix_world @ she.pose.bones['forearm.L'].tail) / 2
    sc.frame_set(1)
    B = film.camera('Cam15b_Rings', [(SHOTS['b'], Vector((0, paws.y + 1.5, paws.z - .12)), paws + Vector((0, 0, .1))), (SHOTS['c'] - 1, Vector((0, paws.y + 1.3, paws.z - .1)), paws + Vector((0, 0, .1)))], lens=50, fstop=2.8, focus=1.4)
    C = film.camera('Cam15c_Kiss', [(SHOTS['c'], (0, y + 2.3, .8), (0, y, .75)), (SHOTS['end'], (0, y + 4.2, 2.2), (0, y, .9))], lens=36, fstop=2.8, focus=2.3)
    film.area_light('KissFill', (.6, y + 2.0, 1.6), (0, y, .7), 80, 1.5, (1, .8, .65))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '15', still_frame=210)
