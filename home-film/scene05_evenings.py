"""
Home - scene 5: ordinary evenings (song 1:28-1:44).
A balcony over the city at sunset; movies on the sofa; falling asleep together.
"Not because they were extraordinary." / "Because they felt like peace."

Shots:  1-130   the balcony at sunset: two chairs, two mugs, the rooftops and the cathedral domes
      131-260   evening on the sofa: a movie, the TV light flickering on their faces, a bowl of popcorn
      261-384   asleep on each other under the blanket, the film still playing; the camera drifts back
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
from film import box, cylinder, blob, mat, emit_mat, link, node_mat, PI
import numpy as np
from mathutils import Vector

SHOTS = dict(a=1, b=131, c=261, end=384)
B = Vector((34.0, -58.0, 16.0))       # the balcony (high above the south-east corner of Senate Square)
LR = Vector((400.0, 0.0, 0.0))        # the living room (its own little world, far from the city)


def balcony(coll):
    import scene01_helsinki as s1
    importlib.reload(s1)
    s1.build_cathedral(coll); s1.build_city(coll)
    for m in bpy.data.materials:
        if m.node_tree and 'Melt' in m.node_tree.nodes:
            m.node_tree.nodes['Melt'].outputs[0].default_value = 1.0      # summer now: no snow
    # turn the snowbanks and ice floes off (it's summer)
    for o in bpy.data.objects:
        if o.name.startswith(('Snowbank', 'Floe', 'Lamp0_icicle')):
            o.hide_render = True; o.hide_viewport = True
    conc = mat('BalconyConcrete', (.45, .42, .4), rough=.8)
    rail = mat('Railing', (.03, .03, .03), rough=.35, metal=.7)
    wall = mat('HouseWall', (.68, .55, .38), rough=.8)
    T = lambda x, y, z: (B.x + x, B.y + y, B.z + z)
    box('BalconySlab', (3.2, 1.6, .15), T(0, 0, -.15), conc, coll)
    box('HouseWall', (8, .3, 4), T(0, -1.0, -2), wall, coll)
    box('BalconyDoor', (1.0, .05, 1.4), T(-.9, -.84, 0), mat('DoorGlass', (.15, .2, .22), rough=.05, metal=.3), coll)
    box('RailTop', (3.2, .05, .04), T(0, .78, .62), rail, coll)
    for i in range(17):
        box(f'RailBar{i}', (.02, .02, .62), T(-1.6 + i * .2, .78, 0), rail, coll)
    for sx in (-1, 1):
        box(f'RailSide{sx}', (.05, 1.6, .04), T(sx * 1.58, 0, .62), rail, coll)
    # two little chairs, a tiny table, mugs, potted flowers
    wood = mat('ChairWood', (.35, .2, .1), rough=.6)
    for sx in (-1, 1):
        box(f'ChairSeat{sx}', (.5, .45, .04), T(sx * .4, -.05, .3), wood, coll)
        box(f'ChairBack{sx}', (.5, .04, .4), T(sx * .4, -.29, .3), wood, coll, rot=(-.15, 0, 0))
        for lx in (-.22, .22):
            for ly in (-.2, .18):
                box(f'ChairLeg{sx}{lx}{ly}', (.03, .03, .3), T(sx * .4 + lx, -.05 + ly, 0), rail, coll)
    cylinder('BalTable', .17, .02, T(0, .12, .4), wood, coll, n=20)
    cylinder('BalTableLeg', .02, .4, T(0, .12, 0), rail, coll, n=8)
    mug = mat('Mug2', (.85, .82, .75), rough=.3, coat=.5)
    for x in (-.06, .07):
        cylinder(f'BalMug{x}', .04, .08, T(x, .1, .42), mug, coll, n=14)
    pot = mat('TerraPot', (.5, .24, .12), rough=.8); leaf = mat('Geranium', (.05, .14, .04), rough=.6); red = mat('Bloom', (.8, .08, .1), rough=.5)
    for i, x in enumerate((-1.35, 1.35)):
        cylinder(f'BalPot{i}', .13, .22, T(x, .55, 0), pot, coll, n=14, r2=.16)
        for k in range(8):
            blob(f'BalLeaf{i}{k}', T(x + .1 * math.cos(k * 2.4), .55 + .1 * math.sin(k * 2.4), .27 + .02 * k), (.06, .06, .04), coll, leaf, sub=2, seed=k + 10 * i)
        for k in range(5):
            blob(f'BalBloom{i}{k}', T(x + .08 * math.cos(k * 1.3 + 1), .55 + .08 * math.sin(k * 1.3 + 1), .38 + .02 * k), (.03, .03, .03), coll, red, sub=1, seed=k)


def living_room(coll):
    T = lambda x, y, z: (LR.x + x, LR.y + y, LR.z + z)
    wall = mat('LRWall', (.5, .42, .36), rough=.85); floor = mat('LRFloor', (.2, .11, .05), rough=.45)
    box('LRFloor', (7, 7, .1), T(0, 0, -.1), floor, coll)
    box('LRBack', (7, .1, 2.4), T(0, 2.2, 0), wall, coll)
    box('LRSideL', (.1, 7, 2.4), T(-3.0, 0, 0), wall, coll); box('LRSideR', (.1, 7, 2.4), T(3.0, 0, 0), wall, coll)
    box('LRFront', (7, .1, 2.4), T(0, -3.4, 0), wall, coll)
    box('LRCeil', (7, 7, .1), T(0, 0, 2.4), wall, coll)
    rug = mat('Rug', (.45, .2, .15), rough=1.0)
    box('Rug', (2.6, 1.8, .015), T(0, -.6, 0), rug, coll)
    # the sofa (bears sit on it facing -Y, towards the TV)
    fabric = mat('SofaFabric', (.28, .33, .38), rough=.95, sss=.05)
    box('SofaBase', (2.0, .8, .32), T(0, 1.3, 0), fabric, coll, bevel=.05)
    box('SofaBack', (2.0, .25, .5), T(0, 1.65, .32), fabric, coll, bevel=.06)
    for sx in (-1, 1):
        box(f'SofaArm{sx}', (.22, .8, .55), T(sx * 1.1, 1.3, 0), fabric, coll, bevel=.06)
    for sx in (-1, 1):
        blob(f'SofaCushion{sx}', T(sx * .5, 1.25, .38), (.45, .36, .07), coll, fabric, sub=3, rough=.05, seed=sx + 3)
    knit = mat('Throw', (.62, .48, .36), rough=1.0)
    blob('Throw', T(0, 1.05, .5), (.7, .32, .1), coll, knit, sub=4, rough=.2, seed=7)
    # TV on a low stand, its screen changes colour with the film
    stand = mat('TVStand', (.12, .08, .05), rough=.5)
    box('TVStand', (1.6, .4, .4), T(0, -2.6, 0), stand, coll)
    box('TVBody', (1.3, .06, .76), T(0, -2.6, .42), mat('TVBlack', (.01, .01, .01), rough=.2), coll)
    scr_m = emit_mat('TVScreen', (.5, .6, .9), 6)
    box('TVScreen', (1.22, .01, .68), T(0, -2.565, .46), scr_m, coll)
    tvl = film.area_light('TVLight', T(0, -2.45, .8), T(0, 1.2, .5), 30, 1.2, (.5, .6, .9))
    em = scr_m.node_tree.nodes['Emission']
    rng = np.random.default_rng(9)
    palette = [(.45, .6, 1.0), (1.0, .7, .45), (.6, .9, .7), (.9, .5, .6), (.75, .8, 1.0), (1.0, .85, .6)]
    for f in range(SHOTS['b'] - 5, SHOTS['end'] + 1, 18):
        c = palette[rng.integers(len(palette))]; k = rng.uniform(.7, 1.2)
        em.inputs['Color'].default_value = (*c, 1); em.inputs['Strength'].default_value = 6 * k
        em.inputs['Color'].keyframe_insert('default_value', frame=f); em.inputs['Strength'].keyframe_insert('default_value', frame=f)
        tvl.data.color = c; tvl.data.energy = 30 * k
        tvl.data.keyframe_insert('color', frame=f); tvl.data.keyframe_insert('energy', frame=f)
    # a warm lamp and the popcorn
    film.point_light('LRLamp', T(1.6, 1.6, 1.3), 40, (1, .6, .3), .15)
    shade = mat('LRShade', (1, .8, .55), rough=.9, emission=(1, .6, .3), strength=3)
    cylinder('LRLampShade', .2, .25, T(1.6, 1.6, 1.2), shade, coll, n=20, r2=.13, cap=False)
    cylinder('LRLampPole', .015, 1.2, T(1.6, 1.6, 0), mat('Brass', (.6, .45, .25), rough=.3, metal=1), coll, n=8)
    bowl = mat('Bowl', (.75, .2, .15), rough=.3, coat=.5); corn = mat('Popcorn', (.95, .88, .65), rough=.8)
    cylinder('Bowl', .12, .08, T(0, 1.08, .58), bowl, coll, n=16, r2=.16)
    for i in range(30):
        a = rng.uniform(0, 2 * PI); r = rng.uniform(0, .12)
        blob(f'Corn{i}', T(math.cos(a) * r, 1.08 + math.sin(a) * r, .66 + rng.uniform(0, .04)), (.022, .022, .02), coll, corn, sub=1, rough=.3, seed=i)
    film.area_light('LRFill', T(0, -1.0, 2.2), T(0, 1.2, .5), 12, 2, (1, .7, .5))


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(.95, .6, .45), start=40.0, dist=320.0, strength=.45)
    w, sky, bg, ramp = film.make_sky(elev=5, az=-80, strength=.95, low=(1, .45, .22), mid=(1, .65, .5))
    sun = film.make_sun(elev=5, az=-80, energy=3.0, color=(1, .66, .4))
    bal = film.new_coll('Balcony'); balcony(bal)
    lr = film.new_coll('LivingRoom'); living_room(lr)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    # balcony: sitting on the chairs facing the city (+Y)
    bears.place(he, 1, (B.x - .4, B.y - .02, B.z + .34), PI, sitting=True)
    bears.place(she, 1, (B.x + .4, B.y - .02, B.z + .34), PI, sitting=True)
    bears.turn_head(she, 40, yaw=0); bears.turn_head(she, 64, yaw=30, nod=4); bears.turn_head(she, 100, yaw=28, nod=4); bears.turn_head(she, 118, yaw=6)
    bears.turn_head(he, 70, yaw=0); bears.turn_head(he, 90, yaw=-26, nod=2); bears.turn_head(he, 126, yaw=-24)
    bears.blink(he, 50); bears.blink(she, 110)
    # the sofa, the film (facing the TV = -Y)
    b_ = SHOTS['b']; seat = LR.z + .4
    bears.place(he, b_, (LR.x + .3, LR.y + 1.18, seat), 0, sitting=True, pose={'head': (-4, 0, 0)})
    bears.place(she, b_, (LR.x - .3, LR.y + 1.18, seat), 0, sitting=True, pose={'head': (-4, 0, 0), 'shoulder.R': (30, 0, -10)})
    bears.blink(she, b_ + 40); bears.blink(he, b_ + 70); bears.blink(she, b_ + 100)
    # falling asleep: heads sink onto each other
    c = SHOTS['c']
    bears.key_pose(she, c, {'head': (-4, 0, 0), 'spine': (6, 0, 0)}); bears.key_pose(he, c, {'head': (-4, 0, 0), 'spine': (6, 0, 0)})
    bears.key_pose(she, c + 50, {'head': (14, 12, -22), 'spine': (8, 0, -10)}); bears.key_pose(she, SHOTS['end'], {'head': (16, 12, -24), 'spine': (8, 0, -10)})
    bears.key_pose(he, c + 70, {'head': (12, -10, 18), 'spine': (6, 0, 6)}); bears.key_pose(he, SHOTS['end'], {'head': (14, -10, 20), 'spine': (6, 0, 6)})
    bears.set_eyes(she, 'closed', c + 30); bears.blink(he, c + 40); bears.set_eyes(he, 'closed', c + 62)
    # cameras
    A = film.camera('Cam5a_Balcony', [(SHOTS['a'], (B.x + .25, B.y - .72, B.z + 1.25), (B.x - 1.5, B.y + 12, B.z - 1.0)),
                                      (SHOTS['b'] - 1, (B.x + .15, B.y - .7, B.z + 1.15), (B.x - 1.5, B.y + 12, B.z - 1.1))], lens=18, fstop=5.6,
                    focus=(B.x, B.y, B.z + .5))
    Bc = film.camera('Cam5b_Movie', [(SHOTS['b'], (LR.x + .35, LR.y - 1.4, LR.z + .78), (LR.x, LR.y + 1.18, LR.z + .72)),
                                     (SHOTS['c'] - 1, (LR.x + .25, LR.y - 1.25, LR.z + .78), (LR.x, LR.y + 1.18, LR.z + .72))], lens=35, fstop=2.8,
                     focus=(LR.x, LR.y + 1.18, LR.z + .7))
    C = film.camera('Cam5c_Asleep', [(SHOTS['c'], (LR.x - .2, LR.y - .9, LR.z + .8), (LR.x, LR.y + 1.18, LR.z + .72)),
                                     (SHOTS['end'], (LR.x - .3, LR.y - 1.9, LR.z + .95), (LR.x, LR.y + 1.18, LR.z + .7))], lens=35, fstop=2.8,
                    focus=(LR.x, LR.y + 1.18, LR.z + .7))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], Bc), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '05', still_frame=200)
