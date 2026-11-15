"""
Home - scene 9: the call (song 2:48-3:04).
Night. Her name lights up his phone: "I'm lost." They meet and talk for hours, and the storm clears.

Shots:  1-110   night, he sits alone on the edge of the bed; the phone lights up: "Alona"
      111-250   the harbour bench (from scene 1) at night: they talk, the hours pass, the sky slowly lightens
      251-384   dawn over the sea, the storm gone: she leans on him
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
from mathutils import Vector

SHOTS = dict(a=1, b=111, c=251, end=384)
NAME = 'Alona'


def phone(coll):
    body = mat('PhoneBody', (.02, .02, .025), rough=.3, metal=.4)
    ph = box('Phone', (.075, .012, .15), (0, 0, 0), body, coll, bevel=.008)
    scr_m = emit_mat('PhoneScreen', (.08, .1, .16), 1.5)
    scr = box('PhoneScreen', (.066, .002, .136), (0, -.0065, .007), scr_m, coll)
    txt_m = emit_mat('PhoneText', (1, 1, 1), 4)
    def text(name, body_, size, z, m=txt_m):
        cu = bpy.data.curves.new(name, 'FONT'); cu.body = body_; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        cu.materials.append(m)
        o = link(bpy.data.objects.new(name, cu), coll); o.location = (0, -.009, z + .075); o.rotation_euler = (PI / 2, 0, 0)
        o.parent = ph
        return o
    text('CallerName', NAME, .013, .03)
    text('CallerSub', 'calling...', .006, .016, emit_mat('PhoneSub', (.7, .75, .8), 2))
    green = emit_mat('PhoneGreen', (.1, .9, .3), 3); red = emit_mat('PhoneRed', (1, .15, .15), 3)
    for x, m in ((-.018, red), (.018, green)):
        c = cylinder(f'PhoneBtn{x}', .007, .001, (x, -.008, .03), m, coll, n=16); c.rotation_euler = (PI / 2, 0, 0); c.parent = ph
    scr.parent = ph
    return ph


def build():
    bears = film.import_bears()
    import scene06_hearts as s6, scene01_helsinki as s1
    importlib.reload(s6); importlib.reload(s1)
    film.HAZE.update(color=(.05, .06, .1), start=30.0, dist=300.0, strength=.5)
    w, sky, bg, ramp = film.make_sky(elev=-8, az=60, strength=.6, low=(1, .55, .4), mid=(.8, .7, .8), high=(.6, .7, 1.0))
    sun = film.make_sun(elev=-8, az=60, energy=0.0, color=(1, .7, .5))
    for f, el, st, en in ((1, -9, .35, 0), (SHOTS['b'], -9, .35, 0), (SHOTS['c'] - 1, -3, .6, 0), (SHOTS['c'], -1, .8, .6), (SHOTS['end'], 2.5, 1.0, 2.4)):
        sky.sun_elevation = math.radians(el); sky.keyframe_insert('sun_elevation', frame=f)
        bg.inputs['Strength'].default_value = st; bg.inputs['Strength'].keyframe_insert('default_value', frame=f)
        film.aim_sun(sun, el, 60); sun.keyframe_insert('rotation_euler', frame=f)
        sun.data.energy = en; sun.data.keyframe_insert('energy', frame=f)
    br = film.new_coll('Bedroom'); s6.bedroom(br)
    bpy.data.objects['Duvet'].location.y += .55          # duvet pulled up the bed, so the phone lies free
    city = film.new_coll('Harbour'); s1.build_cathedral(city); s1.build_city(city)
    for m in bpy.data.materials:
        if m.node_tree and 'Melt' in m.node_tree.nodes:
            m.node_tree.nodes['Melt'].outputs[0].default_value = 1.0
    for o in bpy.data.objects:
        if o.name.startswith(('Snowbank', 'Floe', 'Lamp0_icicle')):
            o.hide_render = True; o.hide_viewport = True
    # the harbour lamps burn through the night and go out at dawn
    gl = bpy.data.materials['LampGlass'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    lamps = [film.point_light(f'HarbourLamp{i}', (x, -146.2, 4.3), 2500, (1, .68, .38), .15) for i, x in enumerate((-4.5, 9))]
    for f, v in ((1, 8), (SHOTS['c'] + 40, 8), (SHOTS['c'] + 70, 0)):
        gl.default_value = v; gl.keyframe_insert('default_value', frame=f)
        for L_ in lamps:
            L_.data.energy = 2500 if v else 0; L_.data.keyframe_insert('energy', frame=f)
    film.area_light('NightFill', (0, -156, 4), (0, -146.8, .5), 350, 4, (.4, .5, .9))
    film.area_light('BenchWarm', (-2.5, -149, 2.5), (0, -146.8, .5), 60, 1.5, (1, .66, .4))
    he = bears.build_bear('he'); she = bears.build_bear('she')
    BR = s6.BR
    # ---- 9a: alone on the edge of the bed; the phone lights up with her name
    bears.place(he, 1, (BR.x, BR.y - 1.1, BR.z + .46), 0, sitting=True, pose={'head': (22, 0, 0)})
    bears.place(she, 1, (2000, 0, 0), 0)
    ph = phone(film.new_coll('Phone'))
    # the phone lies on the bed beside him (to his left), screen up
    pp = Vector((BR.x + .5, BR.y - 1.0, BR.z + .468))
    ph.location = pp; ph.rotation_euler = (-PI / 2, 0, .25)
    bears.turn_head(he, 40, nod=22, yaw=0); bears.turn_head(he, 56, nod=34, yaw=42); bears.turn_head(he, SHOTS['b'] - 1, nod=36, yaw=44)
    scr = bpy.data.materials['PhoneScreen'].node_tree.nodes['Emission'].inputs['Strength']
    for f, v in ((1, 0.0), (40, 0.0), (41, 2.5), (SHOTS['b'] - 1, 2.5)):
        scr.default_value = v; scr.keyframe_insert('default_value', frame=f)
    film._const(bpy.data.materials['PhoneScreen'].node_tree)
    glow = film.point_light('PhoneGlow', (BR.x + .45, BR.y - 1.0, BR.z + .62), 0, (.7, .8, 1.0), .05)
    for f, e in ((1, 0), (40, 0), (41, 3), (SHOTS['b'], 0)):
        glow.data.energy = e; glow.data.keyframe_insert('energy', frame=f)
    film._const(glow.data)
    bears.set_eyes(he, 'open', 1); bears.blink(he, 70)
    # ---- 9b / 9c: the harbour bench through the night until dawn
    b_ = SHOTS['b']; seat = .34
    bears.place(he, b_, (-.38, -146.75, seat), 0, sitting=True); bears.place(she, b_, (.38, -146.75, seat), 0, sitting=True)
    film.key_visible(ph, b_, False)
    talk = [(b_ + 5, 30, -32), (b_ + 30, 34, -30), (b_ + 52, 10, -8), (b_ + 70, 32, -30), (b_ + 100, 26, -26), (b_ + 125, 8, -6)]
    for f, ys, yh in talk:
        bears.turn_head(she, f, yaw=-ys, nod=6 if f % 2 else 2); bears.turn_head(he, f + 6, yaw=-yh, nod=4)
    bears.key_pose(she, b_ + 40, {'shoulder.R': (12, 0, -8), 'forearm.R': (10, 0, 0)}); bears.key_pose(she, b_ + 52, {'shoulder.R': (40, 0, -20), 'forearm.R': (40, 0, 0)})
    bears.key_pose(she, b_ + 66, {'shoulder.R': (12, 0, -8), 'forearm.R': (10, 0, 0)})
    bears.blink(she, b_ + 20); bears.blink(he, b_ + 45); bears.blink(she, b_ + 90)
    c = SHOTS['c']
    bears.key_pose(she, c + 10, {'spine': (6, 0, 0), 'head': (4, -24, 0)})
    bears.key_pose(she, c + 50, {'spine': (8, 0, 12), 'head': (6, -18, 16)}); bears.key_pose(she, SHOTS['end'], {'spine': (8, 0, 12), 'head': (6, -18, 16)})
    bears.hold(she, c + 10); she.location.x -= .08; bears.hold(she, c + 50)
    bears.key_pose(he, c + 20, {'head': (4, 20, 0)}); bears.key_pose(he, c + 60, {'head': (6, 10, -12), 'spine': (6, 0, -4)})
    bears.key_pose(he, SHOTS['end'], {'head': (6, 10, -12), 'spine': (6, 0, -4)})
    bears.set_eyes(she, 'closed', c + 60)
    # ---- cameras
    A0 = film.camera('Cam9a_Alone', [(SHOTS['a'], (BR.x + .55, BR.y - 2.85, BR.z + 1.05), (BR.x + .15, BR.y - 1.0, BR.z + .55)),
                                     (44, (BR.x + .5, BR.y - 2.7, BR.z + 1.0), (BR.x + .15, BR.y - 1.0, BR.z + .55))], lens=30, fstop=2.8,
                     focus=(BR.x, BR.y - 1.1, BR.z + .6))
    A = film.camera('Cam9a_Phone', [(45, pp + Vector((.0, -.05, .42)), pp), (SHOTS['b'] - 1, pp + Vector((.0, -.04, .34)), pp)],
                    lens=40, fstop=2.8, focus=.38)
    Bc = film.camera('Cam9b_Bench', [(SHOTS['b'], (.0, -152.2, .9), (0, -146.75, .55)), (SHOTS['c'] - 1, (.1, -151.6, .85), (0, -146.75, .55))],
                     lens=32, fstop=4, focus=(0, -146.75, .5))
    C = film.camera('Cam9c_Dawn', [(SHOTS['c'], (2.6, -149.5, .9), (-.6, -146.6, .55)), (SHOTS['end'], (2.2, -149.9, .95), (-.8, -146.6, .55))],
                    lens=30, fstop=4, focus=(0, -146.75, .5))
    for f, cam in ((SHOTS['a'], A0), (45, A), (SHOTS['b'], Bc), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '09', still_frame=200)
