"""
Home - scene 11: June, the train to Kyiv (song 3:18-3:34).
Summer fields, the platform, a run into a hug. "You feel like home." / "And somehow, you always did."

Shots:  1-110   a blue-and-yellow train crosses golden wheat and sunflower fields
      111-190   the platform in Kyiv: the train stands; he steps out; she is waiting further down
      191-300   they run to each other - into a hug
      301-384   close on the hug, eyes closed
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

SHOTS = dict(a=1, b=111, c=191, d=301, end=384)
ST = Vector((0.0, 0.0, 0.0))          # the station (platform along Y, tracks at x < 0)
FIELD = Vector((0.0, 3000.0, 0.0))    # the fields


def train(name, loc, coll, cars=4):
    """Intercity train: blue carriages with a yellow stripe and a row of windows; front points to -Y."""
    root = link(bpy.data.objects.new(name, None), coll); root.location = loc
    blue = mat(name + '_blue', (.04, .12, .38), rough=.3, metal=.3, coat=.5, haze=True)
    yel = mat(name + '_yellow', (.9, .7, .05), rough=.4, haze=True)
    win = mat(name + '_win', (.03, .04, .05), rough=.05, metal=.5, haze=True)
    grey = mat(name + '_under', (.08, .08, .08), rough=.6, haze=True)
    parts = []
    for k in range(cars):
        y = k * 16.4
        parts += [box(f'{name}_car{k}', (2.9, 16, 3.0), (0, y, .9), blue, coll, bevel=.25),
                  box(f'{name}_stripe{k}', (2.94, 15.6, .25), (0, y, 1.55), yel, coll),
                  box(f'{name}_under{k}', (2.6, 15, .9), (0, y, 0), grey, coll)]
        for i in range(9):
            for sx in (-1, 1):
                parts.append(box(f'{name}_w{k}{i}{sx}', (.02, 1.1, .7), (sx * 1.46, y - 6.4 + i * 1.6, 2.1), win, coll))
        for sx in (-1, 1):
            parts.append(box(f'{name}_door{k}{sx}', (.02, .9, 2.0), (sx * 1.46, y - 7.3, 1.0), win, coll))
        for by in (-5.4, 5.4):                                  # bogies with their wheels
            parts.append(box(f'{name}_bogie{k}{by}', (2.4, 3.0, .45), (0, y + by, .2), grey, coll))
            for wy in (-.9, .9):
                for sx in (-1, 1):
                    w_ = cylinder(f'{name}_wheel{k}{by}{wy}{sx}', .42, .12, (sx * .78, y + by + wy, .42), grey, coll, n=16)
                    w_.rotation_euler = (0, PI / 2, 0); parts.append(w_)
        if k < cars - 1:
            parts.append(box(f'{name}_gangway{k}', (2.2, .5, 2.6), (0, y + 8.2, 1.0), grey, coll))   # the bellows between carriages
        parts.append(box(f'{name}_roofbox{k}', (1.4, 3.0, .3), (0, y + 3, 3.9), grey, coll, bevel=.1))
    parts.append(box(f'{name}_nose', (2.9, 2.2, 2.6), (0, -9.0, .9), blue, coll, bevel=.6))
    parts.append(box(f'{name}_cab', (2.5, .05, .9), (0, -10.05, 2.3), win, coll, rot=(-.35, 0, 0)))
    for p in parts:
        p.parent = root
    return root


def track(coll, x, y0, y1):
    rail = mat('Rail', (.25, .24, .23), rough=.3, metal=.8, haze=True); sleeper = mat('Sleeper', (.12, .09, .07), rough=.9, haze=True)
    ballast = mat('Ballast', (.22, .2, .18), rough=1, haze=True)
    L = y1 - y0
    box(f'Ballast{x}', (3.6, L, .3), (x, (y0 + y1) / 2, -.3), ballast, coll)
    for sx in (-.72, .72):
        box(f'Rail{x}{sx}', (.08, L, .12), (x + sx, (y0 + y1) / 2, 0), rail, coll)
    # sleepers as one mesh
    V, F = [], []
    y = y0
    while y < y1:
        o = len(V)
        V += [(x - 1.2, y, -.02), (x + 1.2, y, -.02), (x + 1.2, y + .25, -.02), (x - 1.2, y + .25, -.02),
              (x - 1.2, y, .03), (x + 1.2, y, .03), (x + 1.2, y + .25, .03), (x - 1.2, y + .25, .03)]
        F += [(o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 2, o + 3, o + 7, o + 6)]
        y += .8
    film.mesh_obj(f'Sleepers{x}', V, F, coll, [sleeper])


def station(coll):
    conc = mat('Platform', (.55, .53, .5), rough=.8, haze=True)
    edge = mat('PlatformEdge', (.85, .7, .1), rough=.6, haze=True)
    box('Platform', (6, 120, 1.0), (ST.x + 3.0, ST.y + 20, 0), conc, coll)
    box('PlatformLine', (.25, 120, .005), (ST.x + .35, ST.y + 20, 1.0), edge, coll)
    track(coll, ST.x - 1.9, -80, 120); track(coll, ST.x - 7.0, -80, 120)
    # canopy on columns
    roof = mat('Canopy', (.25, .3, .32), rough=.5, metal=.5, haze=True); col = mat('CanopyCol', (.6, .58, .52), rough=.6, haze=True)
    box('CanopyRoof', (5.2, 90, .25), (ST.x + 3.2, ST.y + 20, 4.6), roof, coll)
    for i in range(16):
        cylinder(f'CanopyCol{i}', .14, 3.6, (ST.x + 3.6, ST.y - 22 + i * 6, 1.0), col, coll, n=12)
    # the station building behind the platform (warm sand colour, tall arched windows)
    import scene01_helsinki as s1
    importlib.reload(s1)
    s1.facade_building('KyivStation', (10, 70, 16), (ST.x + 11.5, ST.y + 20, 0), (.78, .66, .45), coll, True)
    # platform paving in square slabs, a white safety line and a yellow tactile strip by the edge
    m, N, L, b = node_mat('PlatformSlabs')
    tc = N.new('ShaderNodeTexCoord'); br = N.new('ShaderNodeTexBrick'); br.offset = 0; br.squash = 1
    br.inputs['Scale'].default_value = 1.0; br.inputs['Brick Width'].default_value = .5; br.inputs['Row Height'].default_value = .5
    br.inputs['Mortar Size'].default_value = .012; br.inputs['Color1'].default_value = (.5, .48, .45, 1); br.inputs['Color2'].default_value = (.6, .58, .54, 1)
    br.inputs['Mortar'].default_value = (.25, .24, .22, 1)
    L.new(tc.outputs['Object'], br.inputs['Vector']); L.new(br.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .75
    add_haze(m, N, L, b)
    box('PlatformTop', (5.3, 120, .01), (ST.x + 3.35, ST.y + 20, 1.0), m, coll)
    box('SafetyLine', (.12, 120, .006), (ST.x + .75, ST.y + 20, 1.0), mat('SafetyWhite', (.9, .9, .88), rough=.6, haze=True), coll)
    # under the canopy: roof beams, column capitals, lights; benches, bins, a hanging clock and departure boards
    beam = mat('CanopyBeam', (.2, .23, .25), rough=.5, metal=.5, haze=True)
    lightm = film.emit_mat('CanopyLight', (1, .93, .8), 3.0)
    iron = mat('StationIron', (.06, .07, .07), rough=.4, metal=.6, haze=True); wood = mat('BenchWood', (.35, .2, .1), rough=.6, haze=True)
    for i in range(46):
        y = ST.y - 25 + i * 2
        box(f'CanopyBeam{i}', (5.2, .12, .3), (ST.x + 3.2, y, 4.3), beam, coll)
        if i % 2 == 0:
            box(f'CanopyLight{i}', (.12, 1.2, .04), (ST.x + 2.2, y + 1, 4.25), lightm, coll)
    for i in range(16):
        y = ST.y - 22 + i * 6
        cylinder(f'CanopyCap{i}', .3, .25, (ST.x + 3.6, y, 4.35), col, coll, n=12, r2=.15)
        if i % 2 == 1:
            for k in range(3):
                box(f'BenchSlat{i}{k}', (.12, 1.8, .04), (ST.x + 4.6 + k * .14, y + 3, 1.45), wood, coll)
                box(f'BenchBack{i}{k}', (.04, 1.8, .1), (ST.x + 4.95, y + 3, 1.6 + k * .14), wood, coll)
            for by in (-.8, .8):
                box(f'BenchLeg{i}{by}', (.45, .06, .45), (ST.x + 4.75, y + 3 + by, 1.0), iron, coll)
            cylinder(f'Bin{i}', .22, .8, (ST.x + 4.9, y + 1.2, 1.0), iron, coll, n=12)
    for cy_ in (ST.y + 2.0, ST.y + 26.0):
        box(f'ClockRod{cy_}', (.04, .04, .9), (ST.x + 2.6, cy_, 3.4), iron, coll)
        face = cylinder(f'ClockFace{cy_}', .42, .12, (ST.x + 2.66, cy_, 3.0), mat('ClockWhite', (.92, .92, .9), rough=.4), coll, n=32)
        face.rotation_euler = (0, PI / 2, 0)
        rim = cylinder(f'ClockRim{cy_}', .46, .1, (ST.x + 2.61, cy_, 3.0), iron, coll, n=32); rim.rotation_euler = (0, PI / 2, 0)
        for sx in (-1, 1):
            box(f'ClockHandH{cy_}{sx}', (.02, .04, .26), (ST.x + 2.66 + sx * .07, cy_, 3.0), iron, coll, rot=(.9, 0, 0))
            box(f'ClockHandM{cy_}{sx}', (.02, .03, .36), (ST.x + 2.66 + sx * .07, cy_, 3.0), iron, coll, rot=(-2.4, 0, 0))
    board = mat('DepartureBoard', (.02, .02, .03), rough=.3, haze=True); amber = film.emit_mat('BoardText', (1, .6, .15), 4.0)
    for by in (ST.y - 8.0, ST.y + 14.0):
        box(f'Board{by}', (.1, 2.4, .7), (ST.x + 2.7, by, 3.2), board, coll)
        for r in range(3):
            box(f'BoardLine{by}{r}', (.11, 1.4 + .3 * (r % 2), .07), (ST.x + 2.7, by - .3 + .1 * r, 3.32 + r * .17), amber, coll)
        box(f'BoardRod{by}', (.04, .04, .45), (ST.x + 2.7, by, 3.9), iron, coll)
    # overhead lines above the tracks: masts, cross arms, wires
    for i in range(7):
        y = -70 + i * 30
        box(f'CatMast{i}', (.3, .3, 7.2), (ST.x - 10.0, y, 0), iron, coll)
        box(f'CatArm{i}', (8.0, .12, .12), (ST.x - 6.2, y, 6.6), iron, coll)
    for tx in (ST.x - 1.9, ST.x - 7.0):
        box(f'CatWire{tx}', (.02, 210, .02), (tx, 20, 6.0), iron, coll)
        box(f'CatWireTop{tx}', (.02, 210, .02), (tx, 20, 6.6), iron, coll)
    film.area_light('PlatformBounce', (ST.x + 2, ST.y - 10, 3.5), (ST.x + 2, ST.y + 5, 1.5), 800, 8, (1, .85, .65))


def fields(coll):
    import scene10_drive as s10
    importlib.reload(s10)
    land = s10.road_land(coll, length=700, forest=False, field_colors=((.38, .26, .04), (.55, .4, .07)))
    land.location = FIELD
    for o in list(coll.objects):
        if o.name.startswith(('Road', 'Dash')):
            bpy.data.objects.remove(o, do_unlink=True)
    track(coll, FIELD.x, FIELD.y - 600, FIELD.y + 120)
    # a few sunflowers near the camera
    stem = mat('SunStem', (.08, .2, .04), rough=.6); petal = mat('SunPetal', (.95, .7, .05), rough=.5); disc = mat('SunDisc', (.15, .08, .02), rough=.8)
    rng = np.random.default_rng(3)
    for i in range(160):
        x = FIELD.x + rng.uniform(4, 22) * (1 if i % 2 else -1); y = FIELD.y + rng.uniform(-60, 10)
        h = rng.uniform(1.0, 1.4)
        cylinder(f'SunStem{i}', .02, h, (x, y, 0), stem, coll, n=6)
        c = cylinder(f'SunHead{i}', .17, .04, (x, y - .02, h), petal, coll, n=14); c.rotation_euler = (1.3, 0, 0)
        d = cylinder(f'SunDiscC{i}', .09, .05, (x, y - .04, h), disc, coll, n=12); d.rotation_euler = (1.3, 0, 0)


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(1.0, .9, .75), start=60.0, dist=700.0, strength=.3)
    w, sky, bg, ramp = film.make_sky(elev=35, az=-30, strength=.3, low=(1, .9, .8), mid=(1, .95, .9), high=(.8, .88, 1.0), aerosol=1.5)
    sun = film.make_sun(elev=35, az=-30, energy=2.6, color=(1, .92, .8))
    bpy.context.scene.view_settings.exposure = -.3          # bright June midday: a touch darker so the colours stay rich
    st = film.new_coll('Station'); station(st)
    fc = film.new_coll('Fields'); fields(fc)
    tr = film.new_coll('Train')
    t1 = train('TrainField', (FIELD.x, FIELD.y + 60, .9), tr)
    t1.location.y = FIELD.y + 60; t1.keyframe_insert('location', frame=1)
    t1.location.y = FIELD.y - 60; t1.keyframe_insert('location', frame=SHOTS['b'] - 1)
    t2 = train('TrainStation', (ST.x - 1.9, ST.y - 4, .9), tr)
    for t in (t1,):
        for fcv in bears._fcurves(t):
            for kp in fcv.keyframe_points:
                kp.interpolation = 'LINEAR'
    he = bears.build_bear('he'); she = bears.build_bear('she')
    pz = 1.0
    # ---- the platform: he steps down from the carriage door; she is waiting
    b_ = SHOTS['b']
    door_y = ST.y - 4 + 16.4 * 1 - 7.3          # second carriage, its door
    bears.place(he, 1, (2000, 0, 0), 0); bears.place(she, 1, (2002, 0, 0), 0)
    bears.place(he, b_, (ST.x - .3, door_y, pz + .1), bears.facing(1, 0))
    bears.walk(he, b_ + 6, b_ + 40, (ST.x - .3, door_y, pz + .1), (ST.x + 1.2, door_y, pz))
    bears.place(she, b_, (ST.x + 1.6, door_y - 7.0, pz), bears.facing(0, 1))
    bears.turn_head(he, b_ + 42, yaw=0); bears.turn_head(he, b_ + 54, yaw=-70, nod=-2)        # he looks down the platform... there she is
    bears.turn_head(she, b_ + 40, yaw=0, nod=-4); bears.set_eyes(she, 'heart', b_ + 60); bears.set_eyes(he, 'heart', b_ + 66)
    bears.set_eyes(she, 'open', SHOTS['c']); bears.set_eyes(he, 'open', SHOTS['c'])
    # ---- the run into the hug
    c = SHOTS['c']; meet = door_y - 3.6
    bears.place(he, c, (ST.x + 1.2, door_y, pz), bears.facing(0, -1)); bears.place(she, c, (ST.x + 1.6, door_y - 7.0, pz), bears.facing(0, 1))
    bears.walk(he, c + 2, c + 62, (ST.x + 1.2, door_y, pz), (ST.x + 1.4, meet + .3, pz), cycle=10, stride=44)
    bears.walk(she, c + 2, c + 62, (ST.x + 1.6, door_y - 7.0, pz), (ST.x + 1.4, meet - .3, pz), cycle=10, stride=44, phase=1)
    hug_he = {'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (4, 35, -12), 'spine': (6, 0, 0)}
    hug_she = {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 35, -14), 'spine': (4, 0, 0)}
    bears.key_pose(he, c + 70, hug_he); bears.key_pose(she, c + 70, hug_she)
    bears.hold(he, c + 64); bears.hold(she, c + 64)
    he.location.y = meet + .24; she.location.y = meet - .24
    bears.hold(he, c + 72); bears.hold(she, c + 72)
    bears.key_pose(he, c + 84, hug_he); bears.key_pose(she, c + 84, hug_she)
    bears.hug_sway(he, c + 84, SHOTS['end'], hug_he); bears.hug_sway(she, c + 84, SHOTS['end'], hug_she, phase=.5)
    bears.set_eyes(he, 'closed', c + 80); bears.set_eyes(she, 'closed', c + 76)
    # ---- cameras
    A = film.camera('Cam11a_Fields', [(SHOTS['a'], (FIELD.x + 14, FIELD.y - 30, 2.2), (FIELD.x, FIELD.y + 10, 2.5)),
                                      (SHOTS['b'] - 1, (FIELD.x + 13, FIELD.y - 34, 2.6), (FIELD.x, FIELD.y - 20, 2.0))], lens=24, fstop=8, focus=20.0)
    B = film.camera('Cam11b_Platform', [(SHOTS['b'], (ST.x + 3.3, door_y - 12.8, pz + 1.35), (ST.x + 1.2, door_y - 3.0, pz + .6)),
                                        (SHOTS['c'] - 1, (ST.x + 3.1, door_y - 12.2, pz + 1.3), (ST.x + 1.2, door_y - 3.0, pz + .6))], lens=28, fstop=4,
                    focus=(ST.x + 1, door_y - 3, pz + .5))
    # (in front of the station wall at x+6.5, between two canopy columns, so nothing blocks the run)
    # behind her as she runs up the platform; he comes running toward the camera
    C = film.camera('Cam11c_Run', [(SHOTS['c'], (ST.x + 2.3, door_y - 10.0, pz + .85), (ST.x + 1.4, meet + 2, pz + .5)),
                                   (SHOTS['c'] + 66, (ST.x + 2.4, meet - 4.0, pz + .8), (ST.x + 1.4, meet, pz + .5)),
                                   (SHOTS['d'] - 1, (ST.x + 2.6, meet - 3.0, pz + .8), (ST.x + 1.4, meet, pz + .55))], lens=30, fstop=4,
                    focus=(ST.x + 1.4, meet, pz + .5))
    D = film.camera('Cam11d_Hug', [(SHOTS['d'], (ST.x + 3.5, meet - .7, pz + .9), (ST.x + 1.4, meet, pz + .62)),
                                   (SHOTS['end'], (ST.x + 3.2, meet - .55, pz + .88), (ST.x + 1.4, meet, pz + .62))], lens=35, fstop=2.0,
                    focus=(ST.x + 1.4, meet, pz + .7))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C), (SHOTS['d'], D)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '11', still_frame=280)
