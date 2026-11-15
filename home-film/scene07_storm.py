"""
Home - scene 7: the storm (song 2:04-2:30). Kept symbolic: no shouting, just distance, rain and a heart going grey.
She gives his heart back - it turns heavy and grey in his paw. A silent drive in the rain. She walks away.
"You believed you were protecting me." / "I believed I was fighting for you." /
"Neither of us understood that we were acting from the same place." / "Love."

Shots:  1-170   the room in a thunderstorm: she holds out his half; he takes it; it greys and sinks
      171-420   the car at night, rain and wipers, streetlights sweeping past; neither speaks
      421-624   a wet street: she walks away under the lamps; he stands by the car with the grey heart
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

SHOTS = dict(a=1, b=171, c=421, end=624)
CAR = Vector((800.0, 0.0, 0.0))        # car interior set
ST = Vector((1000.0, 0.0, 0.0))        # the street


def rain_sheet(name, loc, size, rot, coll, speed=.55, density=.72, strength=.9, tint=(.7, .8, 1.0), fine=55):
    """A transparent sheet of falling rain streaks (a scrolling stretched noise; drives itself by the frame number)."""
    w, h = size
    ob = film.mesh_obj(name, [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [(0, 1, 2, 3)], coll, loc=loc)
    ob.rotation_euler = rot
    m = bpy.data.materials.new(name + '_m'); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links; N.remove(N['Principled BSDF'])
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (fine, fine, 1.6)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    fc = mp.inputs['Location'].driver_add('default_value', 2); fc.driver.expression = f'frame * {speed}'
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 0
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = density; rp.color_ramp.elements[1].position = density + .06
    L.new(nz.outputs['Fac'], rp.inputs['Fac'])
    tr = N.new('ShaderNodeBsdfTransparent'); em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*tint, 1)
    em.inputs['Strength'].default_value = strength
    mix = N.new('ShaderNodeMixShader'); L.new(rp.outputs['Color'], mix.inputs['Fac'])
    L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], N['Material Output'].inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    return ob


def storm_room(coll):
    import scene02_home as s2
    importlib.reload(s2)
    s2.room(coll)
    # no warm cosiness tonight: fairy lights and lamp off, cold blue night through the window
    for n in ('FairyGlow', 'LampLight', 'RoomBounce', 'NightFill', 'FaceWarm'):
        o = bpy.data.objects.get(n)
        if o:
            o.data.energy *= .05
    bpy.data.materials['FairyBulb'].node_tree.nodes['Emission'].inputs['Strength'].default_value = .3
    bpy.data.materials['LampShade'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = .1
    R = s2.R
    cold = film.area_light('StormWindow', (R.x, R.y + 2.0, R.z + 1.3), (R.x, R.y - 1.2, R.z + .6), 260, 2.5, (.45, .55, .85))
    film.area_light('StormFill', (R.x, R.y - 3.5, R.z + 1.8), (R.x, R.y - .8, R.z + .6), 45, 2, (.4, .45, .7))
    flash = film.area_light('Lightning', (R.x - 3, R.y + 14, R.z + 9), (R.x, R.y - 1.2, R.z + .6), 0, 6, (.85, .9, 1.0))
    for f0 in (30, 112, 300, 520):
        for f, e in ((f0 - 1, 0), (f0, 9000), (f0 + 2, 1500), (f0 + 3, 7000), (f0 + 6, 0)):
            flash.data.energy = e; flash.data.keyframe_insert('energy', frame=f)
    film._const(flash.data)
    rain_sheet('RoomRain1', (R.x, R.y + 1.2, R.z + 1.2), (4, 3), (0, 0, 0), coll, strength=.5)
    rain_sheet('RoomRain2', (R.x + .3, R.y + 3.0, R.z + 1.2), (6, 4), (0, 0, 0), coll, speed=.45, strength=.4)
    return R


def car_interior(coll):
    T = lambda x, y, z: (CAR.x + x, CAR.y + y, CAR.z + z)
    trim = mat('CarTrim', (.04, .04, .045), rough=.5); seatm = mat('CarSeat', (.08, .08, .09), rough=.8)
    box('Floorpan', (1.5, 2.4, .05), T(0, .3, 0), trim, coll)
    box('Dash', (1.5, .45, .35), T(0, -.75, .45), trim, coll, bevel=.05)
    for sx in (-1, 1):
        box(f'SeatBase{sx}', (.55, .6, .25), T(sx * .38, .35, .1), seatm, coll, bevel=.05)
        box(f'SeatBack{sx}', (.55, .15, .75), T(sx * .38, .72, .3), seatm, coll, bevel=.05, rot=(.18, 0, 0))
        box(f'Door{sx}', (.06, 2.0, .55), T(sx * .78, .2, .25), trim, coll)
        box(f'APillar{sx}', (.05, .05, .7), T(sx * .72, -.9, .78), trim, coll, rot=(-.6, 0, 0))
    box('Roof', (1.5, 1.6, .05), T(0, .45, 1.32), trim, coll)
    box('WindowFrameTop', (1.5, .06, .06), T(0, -.55, 1.3), trim, coll)
    wheel = mat('Wheel', (.02, .02, .02), rough=.4)
    cylinder('SteeringCol', .03, .3, T(-.38, -.55, .6), wheel, coll, n=8).rotation_euler = (-1.0, 0, 0)
    sw = cylinder('SteeringWheel', .17, .03, T(-.38, -.42, .78), wheel, coll, n=24); sw.rotation_euler = (-1.1, 0, 0)
    glow = emit_mat('Dials', (.3, .6, 1.0), 2)
    box('Dials', (.3, .02, .06), T(-.38, -.55, .8), glow, coll)
    film.area_light('DashGlow', T(0, -.5, .9), T(0, .4, .8), 3, .6, (.3, .5, 1.0))
    # wipers
    wip = mat('Wiper', (.01, .01, .01), rough=.5)
    for i, x in enumerate((-.45, .15)):
        w = box(f'Wiper{i}', (.6, .015, .015), T(x, -1.02, .66), wip, coll)
        for f in range(SHOTS['b'], SHOTS['c'] + 1, 14):
            w.rotation_euler = (0, (.0 if ((f - SHOTS['b']) // 14) % 2 == 0 else -1.6), 0); w.keyframe_insert('rotation_euler', frame=f)
    # streetlights sweeping over the car from the front to the back
    for k in range(3):
        L_ = film.point_light(f'Passing{k}', T(-1.6, -8, 3), 900, (1, .62, .3), .3)
        f = SHOTS['b'] + k * 22
        while f < SHOTS['c']:
            L_.location = T(-1.8, -9, 3.0); L_.keyframe_insert('location', frame=f)
            L_.location = T(-1.8, 6, 3.0); L_.keyframe_insert('location', frame=f + 60)
            f += 66
        for fc in film_fcurves(L_):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    film.area_light('CarNight', T(0, -3, 1.5), T(0, .3, .8), 15, 2, (.35, .45, .8))
    rain_sheet('CarRain1', T(0, -1.25, .9), (2.5, 2.0), (0, 0, 0), coll, strength=.25, density=.78, fine=140)
    rain_sheet('CarRain2', T(0, -1.9, .9), (4, 3), (0, 0, 0), coll, speed=.5, strength=.3, density=.76, fine=110)
    world_dark = None


def film_fcurves(ob):
    import bears
    return bears._fcurves(ob)


def street(coll):
    import scene01_helsinki as s1
    importlib.reload(s1)
    T = lambda x, y, z: (ST.x + x, ST.y + y, ST.z + z)
    wet = mat('WetAsphalt', (.02, .02, .022), rough=.08, haze=True)
    box('Road', (6, 80, .02), T(0, 20, -.02), wet, coll)
    curb = mat('Curb', (.2, .2, .2), rough=.4, haze=True)
    box('Sidewalk', (2.4, 80, .12), T(4.2, 20, -.02), curb, coll)
    for i, y in enumerate(range(-8, 60, 9)):
        s1.facade_building(f'NightHouse{i}', (6, 8.6, 9 + (i % 3) * 2), T(8.6, y, 0), [(.3, .28, .25), (.35, .3, .26), (.28, .27, .26)][i % 3], coll, True)
    for m in bpy.data.materials:
        if m.name.startswith('NightHouse') and (m.name.endswith('_fx') or m.name.endswith('_fy')):
            N, L = m.node_tree.nodes, m.node_tree.links
            br = next(n for n in N if n.bl_idname == 'ShaderNodeTexBrick'); b = N['Principled BSDF']
            inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; L.new(br.outputs['Fac'], inv.inputs[1])
            wn = N.new('ShaderNodeTexWhiteNoise'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (.4, .4, .5)
            L.new(N['Texture Coordinate'].outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], wn.inputs['Vector'])
            on = N.new('ShaderNodeMath'); on.operation = 'GREATER_THAN'; on.inputs[1].default_value = .8; L.new(wn.outputs['Value'], on.inputs[0])
            k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; L.new(inv.outputs[0], k.inputs[0]); L.new(on.outputs[0], k.inputs[1])
            L.new(k.outputs[0], b.inputs['Emission Strength']); b.inputs['Emission Color'].default_value = (1, .6, .3, 1)
    iron = mat('Iron', (.02, .025, .025), rough=.35, metal=.6, haze=True)
    glass = mat('LampGlass', (.9, .85, .7), rough=.1, emission=(1, .7, .4), strength=12, transmission=.4)
    for i, y in enumerate((2, 12, 22, 32, 42)):
        s1.lamp_post(f'StreetLamp{i}', T(3.3, y, 0), coll, iron, glass)
        ld = bpy.data.lights.new(f'StreetCone{i}', 'SPOT'); ld.energy = 6000; ld.color = (1, .66, .38); ld.spot_size = math.radians(80)
        ld.spot_blend = .8; ld.shadow_soft_size = .2
        o = link(bpy.data.objects.new(f'StreetCone{i}', ld), coll); o.location = T(3.3, y, 4.0)
    # the car parked at the curb
    paint = mat('CarPaint', (.05, .07, .1), rough=.2, metal=.6, coat=1)
    win = mat('CarGlass', (.01, .012, .015), rough=.05, metal=.5)
    box('CarBody', (1.15, 2.9, .5), T(2.3, 6.6, .18), paint, coll, bevel=.12)
    box('CarCabin', (1.0, 1.6, .42), T(2.3, 6.75, .66), win, coll, bevel=.1)
    tire = mat('Tire', (.01, .01, .01), rough=.7)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = cylinder(f'CarWheel{sx}{sy}', .2, .14, T(2.3 + sx * .55, 6.6 + sy * .95, .2), tire, coll, n=20)
            c.rotation_euler = (0, PI / 2, 0); c.location.x -= .07 * sx
    tail = emit_mat('TailLight', (1, .05, .03), 6)
    for sx in (-1, 1):
        box(f'Tail{sx}', (.2, .03, .07), T(2.3 + sx * .42, 5.14, .5), tail, coll)
        film.point_light(f'TailGlow{sx}', T(2.3 + sx * .42, 4.9, .5), 6, (1, .1, .05), .05)
    rain_sheet('StreetRain1', T(3.2, -1.0, 1.5), (5, 4), (0, 0, 0), coll, strength=.6)
    rain_sheet('StreetRain2', T(3.4, 4.0, 2.5), (9, 6), (0, 0, 0), coll, speed=.45, strength=.5)
    rain_sheet('StreetRain3', T(3.4, 12.0, 3.5), (14, 9), (0, 0, 0), coll, speed=.4, strength=.4)
    film.area_light('StreetMoon', T(-6, -6, 10), T(3, 6, 0), 3500, 8, (.4, .5, .8))
    film.area_light('StreetBack', T(4, 18, 3), T(4, 4, .5), 900, 4, (1, .65, .4))


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(.02, .025, .04), start=10.0, dist=60.0, strength=.75)
    w = bpy.data.worlds.new('StormNight'); bpy.context.scene.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (.008, .01, .018, 1)
    rm = film.new_coll('StormRoom'); R = storm_room(rm)
    car = film.new_coll('Car'); car_interior(car)
    stc = film.new_coll('Street'); street(stc)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    hearts = film.new_coll('Hearts')
    grey = film.heart_material('HeartHis', glow=.4)
    hb = grey.node_tree.nodes['Principled BSDF']
    for f, col, gl, rough in ((1, (.85, .05, .12), .4, .18), (100, (.85, .05, .12), .4, .18), (130, (.22, .22, .24), 0, .55)):
        hb.inputs['Base Color'].default_value = (*col, 1); hb.inputs['Base Color'].keyframe_insert('default_value', frame=f)
        hb.inputs['Emission Strength'].default_value = gl; hb.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
        hb.inputs['Roughness'].default_value = rough; hb.inputs['Roughness'].keyframe_insert('default_value', frame=f)
    # ---- 7a: in the room. They stand apart; she holds out his half; he takes it; it greys and sinks.
    y0 = R.y - 1.3
    bears.place(he, 1, (R.x - .45, y0, R.z), bears.facing(1, .25)); bears.place(she, 1, (R.x + .45, y0 + .1, R.z), bears.facing(-1, -.25))
    bears.turn_head(he, 1, nod=14); bears.turn_head(she, 1, nod=16)
    give = {'shoulder.L': (58, 0, 14), 'forearm.L': (18, 0, 0)}
    bears.key_pose(she, 30, {'shoulder.L': (10, 0, 6), 'forearm.L': (30, 0, 0)}); bears.key_pose(she, 70, give); bears.key_pose(she, 104, give)
    bears.key_pose(she, 120, {'shoulder.L': (0, 0, 4), 'forearm.L': (0, 0, 0)})
    take = {'shoulder.R': (52, 0, -14), 'forearm.R': (18, 0, 0)}
    bears.key_pose(he, 60, {'shoulder.R': (0, 0, -4)}); bears.key_pose(he, 96, take)
    bears.key_pose(he, 112, take); bears.key_pose(he, 140, {'shoulder.R': (22, 0, -6), 'forearm.R': (24, 0, 0)})     # heavy: the paw sinks
    bears.turn_head(she, 70, nod=6, yaw=0); bears.turn_head(she, 120, nod=20, yaw=0)
    bears.hold(she, 124); she.rotation_euler.z += 2.2; bears.hold(she, 160)                                        # she turns away
    bears.turn_head(he, 100, nod=26); bears.turn_head(he, 150, nod=34)
    h_she = film.attach_to_paw(film.heart_half('HisHalf_she', 'L', .13, grey, hearts), she, 'forearm.L', (0, .02, -.03), (PI / 2, 0, 0))
    h_he = film.attach_to_paw(film.heart_half('HisHalf_he', 'L', .13, grey, hearts), he, 'forearm.R', (0, .02, -.03), (PI / 2, 0, 0))
    film.key_visible(h_she, 1, True); film.key_visible(h_she, 100, False)
    film.key_visible(h_he, 1, False); film.key_visible(h_he, 100, True)
    # ---- 7b: the silent drive (he drives, she looks out of her window)
    b_ = SHOTS['b']; seat = CAR.z + .35
    bears.place(he, b_, (CAR.x - .38, CAR.y + .38, seat), 0, sitting=True, pose={'shoulder.L': (55, 0, 4), 'shoulder.R': (55, 0, -4),
                                                                                    'forearm.L': (20, 0, 0), 'forearm.R': (20, 0, 0)})
    bears.place(she, b_, (CAR.x + .38, CAR.y + .38, seat), 0, sitting=True, pose={'head': (6, -55, 0)})
    bears.blink(he, b_ + 60); bears.turn_head(he, b_ + 120, nod=0, yaw=0); bears.turn_head(he, b_ + 140, yaw=-22)
    bears.turn_head(he, b_ + 175, yaw=-20); bears.turn_head(he, b_ + 195, yaw=0)
    film.key_visible(h_he, b_, False)
    # ---- 7c: the wet street: she walks away under the lamps; he stands by the car
    c = SHOTS['c']
    bears.place(he, c, (ST.x + 3.0, ST.y + .9, ST.z + .1), bears.facing(.15, 1), pose={'shoulder.R': (24, 0, -6), 'forearm.R': (24, 0, 0)})
    film.key_visible(h_he, c, True)
    bears.place(she, c, (ST.x + 3.9, ST.y + 2.0, ST.z + .1), PI)
    bears.walk(she, c + 4, SHOTS['end'], (ST.x + 3.9, ST.y + 2.0, ST.z + .1), (ST.x + 4.1, ST.y + 14.0, ST.z + .1), cycle=20, stride=22)
    bears.turn_head(he, c, nod=10, yaw=0); bears.turn_head(he, c + 120, nod=14, yaw=0); bears.turn_head(he, SHOTS['end'], nod=26)
    # at "Love." the grey heart in his paw glows once, faintly
    for f, gl in ((540, 0), (556, 1.6), (600, .3)):
        hb.inputs['Emission Strength'].default_value = gl; hb.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
    # ---- cameras
    A = film.camera('Cam7a_Room', [(SHOTS['a'], (R.x + .1, y0 - 2.5, R.z + .8), (R.x, y0, R.z + .55)),
                                   (SHOTS['b'] - 1, (R.x + .05, y0 - 2.2, R.z + .78), (R.x, y0, R.z + .55))], lens=30, fstop=2.8,
                    focus=(R.x, y0, R.z + .5))
    Bc = film.camera('Cam7b_Car', [(SHOTS['b'], (CAR.x + .05, CAR.y - 2.6, CAR.z + .95), (CAR.x, CAR.y + .4, CAR.z + .78)),
                                   (SHOTS['c'] - 1, (CAR.x + .02, CAR.y - 2.2, CAR.z + .93), (CAR.x, CAR.y + .4, CAR.z + .78))], lens=30, fstop=2.8,
                     focus=(CAR.x, CAR.y + .4, CAR.z + .8))
    C = film.camera('Cam7c_Street', [(SHOTS['c'], (ST.x + 3.55, ST.y - 1.6, ST.z + .95), (ST.x + 3.9, ST.y + 10, ST.z + .45)),
                                     (SHOTS['end'], (ST.x + 3.5, ST.y - 1.3, ST.z + .92), (ST.x + 3.95, ST.y + 10, ST.z + .45))], lens=26, fstop=4,
                    focus=(ST.x + 2.5, ST.y + 4, ST.z + .5))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], Bc), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '07', still_frame=300)
