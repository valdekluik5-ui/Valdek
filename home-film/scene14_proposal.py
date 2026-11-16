"""
Home - scene 14: the Rainbow Bridge, Kyiv (song 4:35-4:47 - the sudden quiet break, then the peak begins).
A pedestrian bridge over the Dnipro under a great rainbow-coloured arch, at the golden hour.
He kneels with the ring; she says yes.

Shots:  1-96    golden hour over the Dnipro: the wide arch, the two of them small on the bridge
       97-200   close: he kneels and opens a little box; the ring catches the sun
      201-288   yes - heart eyes, a hug, the city glowing behind them
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
from mathutils import Vector, Matrix

SHOTS = dict(a=1, b=97, c=201, end=288)
DECK = 12.0                       # deck height above the river


def arch(coll):
    """The great arch: a half ring in rainbow bands, standing over the bridge (its plane is XZ, the bridge runs along X)."""
    bands = [(.75, .08, .06), (.9, .38, .05), (.95, .78, .1), (.15, .55, .2), (.1, .3, .75), (.35, .15, .6)]
    R0, w, depth = 32.0, .9, 2.4
    for k, col in enumerate(bands):
        m = mat(f'ArchBand{k}', col, rough=.35, metal=.2, haze=True)
        r1, r2 = R0 + k * w, R0 + (k + 1) * w
        V, F = [], []
        n = 96
        for i in range(n + 1):
            a = PI * i / n
            for r in (r1, r2):
                for y in (-depth / 2, depth / 2):
                    V.append((math.cos(a) * r, y + 34, math.sin(a) * r - 6))
        for i in range(n):
            o = i * 4; p = o + 4
            F += [(o, p, p + 1, o + 1), (o + 2, o + 3, p + 3, p + 2), (o, o + 2, p + 2, p), (o + 1, p + 1, p + 3, o + 3)]
        film.mesh_obj(f'Arch{k}', V, F, coll, [m], smooth=True)


def bridge(coll):
    deck = mat('BridgeDeck', (.55, .5, .45), rough=.6, haze=True); glass = mat('BridgeGlass', (.4, .55, .6), rough=.05, transmission=.7, haze=True)
    steel = mat('BridgeSteel', (.6, .6, .62), rough=.3, metal=.9, haze=True)
    box('Deck', (220, 4.5, .6), (0, 0, DECK - .6), deck, coll)
    box('DeckUnder', (220, 3.8, 1.6), (0, 0, DECK - 2.2), steel, coll)
    for sy in (-1, 1):
        box(f'Rail{sy}', (220, .08, .08), (0, sy * 2.2, DECK + 1.05), steel, coll)
        box(f'GlassPanel{sy}', (220, .03, 1.0), (0, sy * 2.2, DECK), glass, coll)
    for i in range(12):
        cylinder(f'Pier{i}', 1.2, DECK - 2.2, (-100 + i * 18, 0, 0), steel, coll, n=16)
    lamp = emit_mat('BridgeLamp', (1, .8, .55), 4)
    for i in range(40):
        for sy in (-1, 1):
            cylinder(f'BLamp{i}{sy}', .04, .9, (-100 + i * 5, sy * 2.2, DECK + 1.1), steel, coll, n=6)
            blob(f'BLampBulb{i}{sy}', (-100 + i * 5, sy * 2.2, DECK + 2.05), (.08, .08, .08), coll, lamp, sub=1)


def river_city(coll):
    river = film.water_material('Dnipro', color=(.03, .05, .06), rough=.06, wave=.2, scale=.15)
    add_haze(river, river.node_tree.nodes, river.node_tree.links, river.node_tree.nodes['Principled BSDF'])
    film.mesh_obj('River', [(-800, -800, 0), (800, -800, 0), (800, 800, 0), (-800, 800, 0)], [(0, 1, 2, 3)], coll, [river])
    # the green right bank hills (Kyiv's old city with golden domes) far behind, and the left bank opposite
    hill = mat('KyivHills', (.08, .14, .05), rough=.9, haze=True)
    xs = np.linspace(-600, 600, 121); ys = np.linspace(120, 700, 59)
    X, Y = np.meshgrid(xs, ys); Z = np.clip((Y - 150) / 60, 0, 1) * (30 + 18 * film.fbm(X / 120, Y / 120, 4)) - 1
    land = film.grid_mesh('RightBank', X, Y, Z, coll, hill)
    film.vgroup(land, 'forest', np.clip((Y - 170) / 20, 0, 1).ravel())
    hi, lib = film.tree_library('KyivTrees')
    film.scatter_instances(land, lib, 'forest', 6000, 14, seed=14)
    gold = mat('GoldDome', (1, .7, .3), rough=.2, metal=1, haze=True); white = mat('ChurchWhite', (.85, .84, .8), rough=.6, haze=True)
    for i, (x, y) in enumerate(((-80, 260), (40, 300), (140, 280))):
        z = float(np.clip((y - 150) / 60, 0, 1) * (30 + 18 * film.fbm(np.array(x / 120), np.array(y / 120), 4))) - 1
        box(f'Church{i}', (14, 14, 18), (x, y, z), white, coll)
        cylinder(f'ChurchDrum{i}', 4, 6, (x, y, z + 18), white, coll, n=20)
        film.dome(f'ChurchDome{i}', 4.5, (x, y, z + 24), gold, coll, zscale=1.5)
    left = mat('LeftBank', (.4, .35, .25), rough=.9, haze=True)
    box('LeftBankLand', (1600, 400, 3), (0, -420, -1), left, coll)


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(1, .7, .45), start=40.0, dist=500.0, strength=.5)
    w, sky, bg, ramp = film.make_sky(elev=6, az=-100, strength=.45, low=(1, .5, .25), mid=(1, .68, .5), high=(.75, .8, 1.0))
    sun = film.make_sun(elev=6, az=-100, energy=3.2, color=(1, .68, .4))
    bpy.context.scene.view_settings.exposure = -.2
    st = film.new_coll('Kyiv'); river_city(st); bridge(st); arch(st)
    film.area_light('ProposalFill', (2.6, -.9, DECK + 1.4), (0, 0, DECK + .5), 120, 1.6, (1, .72, .5))     # warm light on their faces and the ring
    he = bears.build_bear('he'); she = bears.build_bear('she')
    bx = 0.0
    # walking out onto the bridge under the arch, then stopping at the middle
    bears.place(he, 1, (bx - 4.3, -.35, DECK), bears.facing(1, 0)); bears.place(she, 1, (bx - 4.3, .35, DECK), bears.facing(1, 0))
    bears.walk(he, 2, 80, (bx - 4.3, -.35, DECK), (bx - .4, -.35, DECK), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)})
    bears.walk(she, 2, 80, (bx - 4.3, .35, DECK), (bx - .4, .35, DECK), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)}, phase=2)
    # he steps in front of her and kneels; she turns to him
    b_ = SHOTS['b']
    bears.place(she, b_, (bx, .35, DECK), bears.facing(0, -1))
    # on one knee: the left leg forward (thigh level), the right knee down behind; both paws hold the box out to her
    kneel = {'thigh.L': (80, 0, -4), 'shin.L': (-80, 0, 0), 'thigh.R': (-35, 0, 4), 'shin.R': (-60, 0, 0), 'spine': (6, 0, 0),
             'shoulder.L': (82, 0, 18), 'shoulder.R': (82, 0, -18), 'forearm.L': (20, 0, 0), 'forearm.R': (20, 0, 0), 'head': (-18, 0, 0)}
    bears.place(he, b_, (bx, -.45, DECK), bears.facing(0, 1))
    bears.key_pose(he, b_ + 26, kneel)
    bears.hold(he, b_ + 6); he.location.z = DECK - .09; he.location.y = -.5; bears.hold(he, b_ + 26)
    bears.turn_head(she, b_ + 10, nod=6); bears.turn_head(she, b_ + 40, nod=18)
    bears.key_pose(she, b_ + 50, {'shoulder.L': (0, 0, 0), 'shoulder.R': (0, 0, 0)})
    bears.key_pose(she, b_ + 66, {'shoulder.L': (95, 0, -20), 'shoulder.R': (95, 0, 20), 'forearm.L': (60, 0, 0), 'forearm.R': (60, 0, 0)})   # paws to her mouth
    # the ring box in his paws
    velvet = mat('RingBox', (.4, .02, .06), rough=.8); gold = mat('RingGold', (1, .78, .4), rough=.12, metal=1)
    stone = mat('Diamond', (1, 1, 1), rough=0, transmission=1.0)
    rb = film.new_coll('Ring')
    boxo = box('RingBoxBase', (.08, .08, .05), (0, 0, 0), velvet, rb, bevel=.008)
    lid = box('RingBoxLid', (.08, .08, .02), (0, .04, .05), velvet, rb, bevel=.006); lid.parent = boxo
    ring = film.cylinder('Ring', .022, .006, (0, 0, .045), gold, rb, n=24); ring.rotation_euler = (PI / 2, 0, 0); ring.parent = boxo
    gem = blob('RingStone', (0, 0, .072), (.008, .008, .008), rb, stone, sub=2, rough=0); gem.parent = boxo
    film.attach_to_paw(boxo, he, 'forearm.R', (.05, .06, -.05), (PI / 2, 0, 0))
    film.key_visible(boxo, 1, False); film.key_visible(boxo, b_ + 24, True)
    for f, a in ((b_ + 40, 0), (b_ + 54, -1.9)):
        lid.rotation_euler = (a, 0, 0); lid.keyframe_insert('rotation_euler', frame=f)
    lid.location = (0, .04, .05)
    sparkle = film.point_light('RingSparkle', (0, 0, 0), 0, (1, .9, .7), .01)
    sparkle.parent = boxo; sparkle.location = (0, 0, .1)
    for f, e in ((b_ + 54, 0), (b_ + 60, 2.0), (b_ + 66, .4), (b_ + 74, 1.6), (SHOTS['c'], .6)):
        sparkle.data.energy = e; sparkle.data.keyframe_insert('energy', frame=f)
    # yes: she nods, heart eyes; he stands; a hug
    c = SHOTS['c']
    bears.turn_head(she, c, nod=-6); bears.turn_head(she, c + 6, nod=14); bears.turn_head(she, c + 12, nod=-6); bears.turn_head(she, c + 18, nod=10)
    bears.set_eyes(she, 'heart', c + 4); bears.set_eyes(he, 'heart', c + 10)
    bears.key_pose(he, c + 26, kneel); bears.hold(he, c + 26)
    bears.key_pose(he, c + 44, dict(bears.STAND, **{'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (4, 30, -10)}))
    he.location = (bx, -.2, DECK); bears.hold(he, c + 44)
    bears.key_pose(she, c + 44, {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 30, -12)})
    film.key_visible(boxo, c + 30, False)
    bears.set_eyes(she, 'closed', c + 56); bears.set_eyes(he, 'closed', c + 60)
    hug_he = dict(bears.STAND, **{'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (4, 30, -10)})
    hug_she = {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 30, -12)}
    bears.hug_sway(he, c + 50, SHOTS['end'], hug_he); bears.hug_sway(she, c + 50, SHOTS['end'], hug_she, phase=.5)
    # ---- cameras
    A = film.camera('Cam14a_Arch', [(SHOTS['a'], (-2.6, -.75, DECK + .55), (-14, 5.5, DECK + 3.5)), (80, (2.2, -.75, DECK + .55), (-9, 5.5, DECK + 3.5)), (SHOTS['b'] - 1, (2.3, -.75, DECK + .55), (-9, 5.5, DECK + 3.5))], lens=18, fstop=5.6, focus=2.7)
    B = film.camera('Cam14b_Kneel', [(SHOTS['b'], (bx + 2.6, -.2, DECK + .8), (bx, -.05, DECK + .45)), (SHOTS['c'] - 1, (bx + 2.2, -.15, DECK + .75), (bx, -.05, DECK + .45))],
                    lens=32, fstop=2.0, focus=2.2)
    C = film.camera('Cam14c_Yes', [(SHOTS['c'], (bx + 2.6, -.4, DECK + .95), (bx, 0, DECK + .65)), (SHOTS['end'], (bx + 4.2, -.6, DECK + 1.5), (bx, 0, DECK + .85))],
                    lens=28, fstop=2.8, focus=3.8)
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '14', still_frame=170)
