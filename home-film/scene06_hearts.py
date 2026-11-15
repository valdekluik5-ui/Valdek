"""
Home - scene 6: the magnetic hearts (song 1:44-2:04).
On the balcony at dusk he gives her one half of a magnetic heart: "This is my heart. I'm giving it to you."
She gives him the other: "And this is mine." Click. They sleep with them, and trade them back in the morning.

Shots:  1-170   the balcony at dusk, from beyond the railing: he offers his half, she takes it
      171-300   close on the two halves: they come together - click - a warm glow
      301-400   night: asleep side by side, each holding the other's half on the chest
      401-480   morning sun: they wake, look at each other, and trade the halves back
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
from film import box, cylinder, blob, mat, emit_mat, link, PI
import numpy as np
from mathutils import Vector, Matrix

SHOTS = dict(a=1, b=171, c=301, d=401, end=480)
BR = Vector((600.0, 0.0, 0.0))     # the bedroom
HS = .13                           # heart size


def bedroom(coll):
    T = lambda x, y, z: (BR.x + x, BR.y + y, BR.z + z)
    wall = mat('BRWall', (.52, .46, .42), rough=.85); floor = mat('BRFloor', (.2, .11, .05), rough=.45)
    box('BRFloor', (6, 6, .1), T(0, 0, -.1), floor, coll); box('BRCeil', (6, 6, .1), T(0, 0, 2.4), wall, coll)
    box('BRBack', (6, .1, 2.4), T(0, 1.4, 0), wall, coll); box('BRFront', (6, .1, 2.4), T(0, -3, 0), wall, coll)
    box('BRLeft', (.1, 6, 2.4), T(-2.2, 0, 0), wall, coll)
    # right wall with a window
    box('BRRightA', (.1, 2.4, 2.4), T(2.2, -1.8, 0), wall, coll); box('BRRightB', (.1, 1.6, 2.4), T(2.2, 1.0, 0), wall, coll)
    box('BRRightLow', (.1, 1.0, .9), T(2.2, -.1, 0), wall, coll); box('BRRightHigh', (.1, 1.0, .6), T(2.2, -.1, 1.8), wall, coll)
    # the bed
    wood = mat('BedWood', (.3, .17, .08), rough=.5)
    sheet = mat('Sheet', (.75, .72, .68), rough=.9, sss=.05)
    box('BedFrame', (1.7, 2.3, .3), T(0, -.1, 0), wood, coll)
    box('Headboard', (1.7, .08, .9), T(0, 1.06, 0), wood, coll, bevel=.02)
    box('Mattress', (1.6, 2.2, .16), T(0, -.1, .3), sheet, coll, bevel=.04)
    pil = mat('Pillow', (.85, .82, .78), rough=.9, sss=.05)
    for sx in (-1, 1):
        blob(f'Pillow{sx}', T(sx * .38, .68, .52), (.34, .2, .08), coll, pil, sub=3, rough=.08, seed=sx + 5)
    duvet = mat('Duvet', (.62, .5, .42), rough=.95, sss=.05)
    blob('Duvet', T(0, -.55, .55), (.82, .62, .14), coll, duvet, sub=4, rough=.12, seed=8)
    # night table, little lamp
    box('NightTable', (.45, .4, .5), T(-1.15, .7, 0), wood, coll)
    shade = mat('BRShade', (1, .8, .55), rough=.9, emission=(1, .6, .3), strength=2)
    cylinder('BRLampShade', .11, .14, T(-1.15, .7, .72), shade, coll, n=16, r2=.07, cap=False)
    cylinder('BRLampStem', .01, .22, T(-1.15, .7, .5), mat('BRBrass', (.6, .45, .25), rough=.3, metal=1), coll, n=8)
    # window light: moonlight, then morning sun
    win = film.area_light('WindowLight', T(2.6, -.1, 1.4), T(0, -.1, .6), 250, 1.0, (.45, .55, 1.0))
    fill = film.area_light('BRFill', T(0, -2.5, 2.2), T(0, 0, .6), 8, 2, (.4, .5, .9))
    lamp = film.point_light('BRLamp', T(-1.15, .7, .85), 0, (1, .6, .3), .1)
    for f, (we, wc, fe, fc, le) in ((SHOTS['c'], (700, (.45, .55, 1.0), 60, (.4, .5, .9), 25)),
                                    (SHOTS['d'], (900, (1, .8, .55), 40, (1, .8, .65), 0))):
        film.key_light(win, f, energy=we, color=wc); film.key_light(fill, f, energy=fe, color=fc); film.key_light(lamp, f, energy=le)


def lying(bears, arm, frame, x, y, z):
    """Lay a bear on its back on the bed, head toward +Y, paws resting on its chest."""
    arm.location = (x, y, z); arm.rotation_euler = (-PI / 2, 0, 0)
    arm.keyframe_insert('location', frame=frame); arm.keyframe_insert('rotation_euler', frame=frame)
    bears.key_pose(arm, frame, dict(bears.STAND, **{'shoulder.L': (55, 0, -22), 'shoulder.R': (55, 0, 22),
                                                    'forearm.L': (40, 0, 0), 'forearm.R': (40, 0, 0)}))
    bears._constant_at(arm, frame)


def chest_point(arm, frame):
    bpy.context.scene.frame_set(frame)
    return arm.matrix_world @ Vector((0, -.24, .42))


def build():
    bears = film.import_bears()
    import scene05_evenings as s5
    importlib.reload(s5)
    film.HAZE.update(color=(.9, .5, .45), start=40.0, dist=320.0, strength=.45)
    w, sky, bg, ramp = film.make_sky(elev=1.0, az=-85, strength=.8, low=(1, .38, .25), mid=(.9, .5, .55), high=(.45, .5, .9))
    sun = film.make_sun(elev=1.5, az=-85, energy=2.0, color=(1, .55, .35))
    bal = film.new_coll('Balcony'); s5.balcony(bal)
    bed = film.new_coll('Bedroom'); bedroom(bed)
    B = s5.B
    film.point_light('BalconyGlow', (B.x - .9, B.y - .6, B.z + 1.2), 25, (1, .65, .35), .2)      # warm light from the door
    film.area_light('BalFaceFill', (B.x, B.y + 2.2, B.z + 1.2), (B.x, B.y, B.z + .6), 25, 1.5, (1, .6, .5))
    he = bears.build_bear('he'); she = bears.build_bear('she')
    hm = film.heart_material('HeartRed', glow=.0)
    hearts = film.new_coll('Hearts')

    def half(name, side):
        return film.heart_half(name, side, HS, hm, hearts)

    # ---- 6a: the balcony. He offers his half (left half) with his right paw; she takes it in her left paw.
    bears.place(he, 1, (B.x - .4, B.y - .02, B.z + .34), PI, sitting=True)
    bears.place(she, 1, (B.x + .4, B.y - .02, B.z + .34), PI, sitting=True)
    bears.turn_head(he, 10, yaw=0); bears.turn_head(he, 30, yaw=-35, nod=6)
    bears.turn_head(she, 30, yaw=0); bears.turn_head(she, 55, yaw=32, nod=10)
    offer_he = {'shoulder.R': (36, 0, -50), 'forearm.R': (24, 0, 0)}
    bears.key_pose(he, 20, {'shoulder.R': (12, 0, -8), 'forearm.R': (10, 0, 0)}); bears.key_pose(he, 60, offer_he)
    bears.key_pose(he, 128, offer_he); bears.key_pose(he, 150, {'shoulder.R': (14, 0, -10), 'forearm.R': (14, 0, 0)})
    take_she = {'shoulder.L': (32, 0, 46), 'forearm.L': (22, 0, 0)}
    bears.key_pose(she, 90, {'shoulder.L': (12, 0, 8), 'forearm.L': (10, 0, 0)}); bears.key_pose(she, 122, take_she)
    bears.key_pose(she, 150, {'shoulder.L': (30, 0, 10), 'forearm.L': (40, 0, 0)})
    h1_he = film.attach_to_paw(half('H1_he', 'L'), he, 'forearm.R', (0, .02, -.03), (PI / 2, 0, 0))
    h1_she = film.attach_to_paw(half('H1_she', 'L'), she, 'forearm.L', (0, .02, -.03), (PI / 2, 0, 0))
    film.key_visible(h1_he, 1, True); film.key_visible(h1_he, 126, False)
    film.key_visible(h1_she, 1, False); film.key_visible(h1_she, 126, True); film.key_visible(h1_she, SHOTS['b'], False)
    bears.blink(she, 140); bears.set_eyes(she, 'heart', 132); bears.set_eyes(she, 'open', 160)
    # ---- 6b: close on the halves: hers comes to his, click
    b_ = SHOTS['b']
    bears.key_pose(he, b_, {'shoulder.R': (38, 0, -44), 'forearm.R': (24, 0, 0)})
    bears.key_pose(she, b_, {'shoulder.L': (34, 0, 42), 'forearm.L': (22, 0, 0)})
    bpy.context.scene.frame_set(b_ + 60)
    meet = (he.matrix_world @ he.pose.bones['forearm.R'].tail + she.matrix_world @ she.pose.bones['forearm.L'].tail) / 2 + Vector((0, .1, .06))
    face = Matrix.Rotation(PI, 4, 'Z')              # the hearts face the camera (which looks from beyond the railing, -Y)
    hL = half('H1_free', 'L'); hR = half('H2_free', 'R')
    for o, sx in ((hL, -1), (hR, 1)):
        o.rotation_euler = (0, 0, PI); o.scale = (1.5, 1.5, 1.5)
        for f, d in ((b_, .16), (b_ + 40, .1), (b_ + 70, .03), (b_ + 76, 0.0), (SHOTS['c'] - 1, 0.0)):
            o.location = meet + Vector((-sx * d, 0, 0)); o.keyframe_insert('location', frame=f)
        film.key_visible(o, 1, False); film.key_visible(o, b_, True); film.key_visible(o, SHOTS['c'], False)
    click = b_ + 76
    glow = hm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for f, v in ((1, 0.0), (click - 1, 0.0), (click, 6.0), (click + 14, 1.2), (SHOTS['c'] - 1, .6), (SHOTS['c'], .6), (SHOTS['d'], .25)):
        glow.default_value = v; glow.keyframe_insert('default_value', frame=f)
    spark = emit_mat('Spark', (1, .75, .55), 20)
    rng = np.random.default_rng(2)
    for i in range(14):
        sp = blob(f'Spark{i}', meet, (.006, .006, .006), hearts, spark, sub=1, rough=0)
        d = Vector(rng.normal(0, 1, 3)).normalized() * rng.uniform(.08, .18)
        film.key_visible(sp, 1, False); film.key_visible(sp, click, True); film.key_visible(sp, click + 18, False)
        sp.location = meet; sp.keyframe_insert('location', frame=click)
        sp.location = meet + d; sp.keyframe_insert('location', frame=click + 18)
    bears.set_eyes(he, 'heart', click + 4); bears.set_eyes(she, 'heart', click + 6)
    bears.set_eyes(he, 'open', SHOTS['c'] - 1); bears.set_eyes(she, 'open', SHOTS['c'] - 1)
    # ---- 6c: night in bed, each holding the other's half on the chest
    c = SHOTS['c']; mz = BR.z + .66
    lying(bears, he, c, BR.x + .38, BR.y - .2, mz); lying(bears, she, c, BR.x - .38, BR.y - .2, mz)
    bears.set_eyes(he, 'closed', c); bears.set_eyes(she, 'closed', c)
    ph, ps = chest_point(he, c + 2), chest_point(she, c + 2)
    on_he = half('H1_bed', 'L'); on_she = half('H2_bed', 'R')        # she sleeps with his half, he with hers -> swapped
    for o in (on_he, on_she):
        o.rotation_euler = (-PI / 2, 0, 0)
    on_he.location = ps + Vector((0, 0, .02)); on_she.location = ph + Vector((0, 0, .02))
    for o in (on_he, on_she):
        o.keyframe_insert('location', frame=c); film.key_visible(o, 1, False); film.key_visible(o, c, True)
    # ---- 6d: morning - they wake, look at each other, and trade the halves back
    d = SHOTS['d']
    bears.set_eyes(he, 'open', d + 10); bears.set_eyes(she, 'open', d + 16)
    bears.turn_head(he, d + 14, yaw=0); bears.turn_head(he, d + 30, yaw=-40); bears.turn_head(she, d + 20, yaw=0); bears.turn_head(she, d + 36, yaw=40)
    bears.set_eyes(he, 'heart', d + 48); bears.set_eyes(she, 'heart', d + 52)
    for o, a, b2 in ((on_he, ps, ph), (on_she, ph, ps)):
        o.location = a + Vector((0, 0, .02)); o.keyframe_insert('location', frame=d + 44)
        o.location = (a + b2) / 2 + Vector((0, 0, .18)); o.keyframe_insert('location', frame=d + 56)
        o.location = b2 + Vector((0, 0, .02)); o.keyframe_insert('location', frame=d + 68)
    # ---- cameras
    A = film.camera('Cam6a_Balcony', [(SHOTS['a'], (B.x + .1, B.y + 2.6, B.z + .95), (B.x, B.y, B.z + .62)),
                                      (SHOTS['b'] - 1, (B.x + .05, B.y + 2.3, B.z + .92), (B.x, B.y, B.z + .62))], lens=30, fstop=2.8,
                    focus=(B.x, B.y, B.z + .6))
    Bc = film.camera('Cam6b_Click', [(SHOTS['b'], meet + Vector((.04, 1.0, .08)), meet), (SHOTS['c'] - 1, meet + Vector((.02, .85, .06)), meet)],
                     lens=55, fstop=2.0, focus=tuple(meet))
    C = film.camera('Cam6c_Night', [(SHOTS['c'], (BR.x + .4, BR.y - 2.3, BR.z + 1.9), (BR.x, BR.y + .3, BR.z + .6)),
                                    (SHOTS['d'] - 1, (BR.x + .3, BR.y - 2.0, BR.z + 1.8), (BR.x, BR.y + .25, BR.z + .65))], lens=28, fstop=4,
                    focus=(BR.x, BR.y + .2, BR.z + .7))
    D = film.camera('Cam6d_Morning', [(SHOTS['d'], (BR.x, BR.y + .38, BR.z + 2.7), (BR.x, BR.y + .4, BR.z + .6)),
                                      (SHOTS['end'], (BR.x, BR.y + .38, BR.z + 2.45), (BR.x, BR.y + .4, BR.z + .6))], lens=26, fstop=4,
                    focus=(BR.x, BR.y + .1, BR.z + .7))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], Bc), (SHOTS['c'], C), (SHOTS['d'], D)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '06', still_frame=250)
