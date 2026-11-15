"""
Home - scene 10: "Please drive." (song 3:04-3:18).
A packed car in the morning; an open road into the sunrise.
"For the first time in a long time, the future didn't feel frightening." / "It felt possible."

Shots:  1-110   morning: the packed car at the roadside, the two of them inside, the sun coming up
      111-230   inside the car: she looks at him and rests her paw on his; sunlight flickers through the trees
      231-336   high and wide: the little car on an open road through fields and forest, into the sunrise
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

SHOTS = dict(a=1, b=111, c=231, end=336)
CAR_IN = Vector((800.0, 0.0, 0.0))


def road_land(coll, length=900, forest=True, field_colors=((.16, .2, .05), (.32, .3, .1)), seed=3):
    """A long straight country road along Y (toward -Y), fields and patches of forest on both sides."""
    asphalt = mat('Asphalt', (.05, .05, .055), rough=.6, haze=True)
    line = mat('RoadLine', (.8, .78, .7), rough=.5, haze=True)
    box('Road', (3.4, length, .02), (0, -length / 2 + 40, -.02), asphalt, coll)
    for i in range(int(length / 6)):
        box(f'Dash{i}', (.08, 2.0, .005), (0, 40 - i * 6, 0), line, coll)
    m, N, L, b = node_mat('Fields')
    tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = .018
    L.new(tc.outputs['Object'], vo.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (*field_colors[0], 1); rp.color_ramp.elements[1].color = (*field_colors[1], 1)
    L.new(vo.outputs['Color'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .3; L.new(nz.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b)
    xs = np.linspace(-400, 400, 161); ys = np.linspace(-length + 40, 120, 161)
    X, Y = np.meshgrid(xs, ys)
    Z = 6 * film.fbm(X / 150, Y / 150, 3) * np.clip((np.abs(X) - 4) / 30, 0, 1) - .05
    land = film.grid_mesh('Land', X, Y, Z, coll, m)
    if forest:
        hi, lib = film.tree_library()
        wood = (film.fbm(X / 60 + seed, Y / 60, 4) > .04) & (np.abs(X) > 14)
        film.vgroup(land, 'forest', wood.astype(float).ravel())
        film.scatter_instances(land, lib, 'forest', 9000, 13, seed=seed)
    return land


def build():
    bears = film.import_bears()
    import scene07_storm as s7
    importlib.reload(s7)
    film.HAZE.update(color=(1.0, .78, .6), start=30.0, dist=500.0, strength=.55)
    w, sky, bg, ramp = film.make_sky(elev=3, az=0, strength=1.0, low=(1, .55, .3), mid=(1, .75, .6), high=(.7, .8, 1.0), aerosol=3)
    sun = film.make_sun(elev=3, az=0, energy=3.2, color=(1, .72, .48))
    land = film.new_coll('Road'); road_land(land)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    # ---- the car (exterior) with luggage on the roof; they sit inside
    c_ = film.car('OurCar', (1.0, 0, 0), 0, film.new_coll('Car'), color=(.12, .2, .28), luggage=True)
    for b, x in ((he, .72), (she, 1.28)):
        bears.place(b, 1, (x, .2, .26), 0, sitting=True)
    bears.turn_head(she, 30, yaw=0); bears.turn_head(she, 50, yaw=-30, nod=4); bears.turn_head(he, 60, yaw=0); bears.turn_head(he, 76, yaw=28)
    # ---- inside, driving
    inside = film.new_coll('CarInside'); s7.car_interior(inside)
    for o in list(inside.objects):
        if o.name.startswith(('CarRain', 'Passing', 'CarNight', 'DashGlow')):
            bpy.data.objects.remove(o, do_unlink=True)
    film.area_light('CarSun', CAR_IN + Vector((-1.5, -3.5, 1.5)), CAR_IN + Vector((0, .4, .8)), 300, 2, (1, .75, .5))
    flick = film.area_light('TreeFlicker', CAR_IN + Vector((-2.5, -1.5, 2.0)), CAR_IN + Vector((0, .4, .8)), 200, 1.5, (1, .8, .55))
    rng = np.random.default_rng(5)
    for f in range(SHOTS['b'], SHOTS['c'] + 1, 6):
        flick.data.energy = rng.choice([30, 200, 260, 60, 220]); flick.data.keyframe_insert('energy', frame=f)
    b_ = SHOTS['b']; seat = CAR_IN.z + .35
    bears.place(he, b_, (CAR_IN.x - .38, CAR_IN.y + .38, seat), 0, sitting=True, pose={'shoulder.L': (55, 0, 4), 'shoulder.R': (55, 0, -4),
                                                                                       'forearm.L': (20, 0, 0), 'forearm.R': (20, 0, 0)})
    bears.place(she, b_, (CAR_IN.x + .38, CAR_IN.y + .38, seat), 0, sitting=True)
    bears.turn_head(she, b_ + 20, yaw=0); bears.turn_head(she, b_ + 40, yaw=-38, nod=4); bears.turn_head(she, SHOTS['c'] - 1, yaw=-34, nod=4)
    bears.key_pose(she, b_ + 50, {'shoulder.L': (12, 0, 8), 'forearm.L': (10, 0, 0)})
    bears.key_pose(she, b_ + 80, {'shoulder.L': (40, 0, 40), 'forearm.L': (20, 0, 0)}); bears.key_pose(she, SHOTS['c'] - 1, {'shoulder.L': (40, 0, 40), 'forearm.L': (20, 0, 0)})
    bears.turn_head(he, b_ + 60, yaw=0); bears.turn_head(he, b_ + 80, yaw=20, nod=2); bears.turn_head(he, b_ + 105, yaw=5)
    bears.set_eyes(she, 'heart', b_ + 85); bears.set_eyes(she, 'open', b_ + 110); bears.blink(he, b_ + 95)
    # ---- the open road: the car drives toward the sunrise
    c = SHOTS['c']
    c_.location = (1.0, 0, 0); c_.keyframe_insert('location', frame=1)          # parked at the roadside until the road shot
    film.drive(c_, c, SHOTS['end'], (1.0, -10, 0), (1.0, -70, 0))
    for fc in bears._fcurves(c_):
        for kp in fc.keyframe_points:
            if kp.co.x < 2:
                kp.interpolation = 'CONSTANT'
    for b, x in ((he, .72), (she, 1.28)):
        bears.place(b, c, (x, -9.8, .26), 0, sitting=True)
        bears.hold(b, c); b.location.y = -69.8; bears.hold(b, SHOTS['end'])
        for fc in bears._fcurves(b):
            if fc.data_path == 'location':
                for kp in fc.keyframe_points:
                    if kp.co.x >= c - .5:
                        kp.interpolation = 'LINEAR'
    # ---- cameras
    A = film.camera('Cam10a_Packed', [(SHOTS['a'], (6.6, 2.8, 1.35), (1.0, -.1, .75)), (SHOTS['b'] - 1, (6.2, 2.2, 1.3), (1.0, -.2, .75))], lens=30, fstop=4,
                    focus=(1.0, 0, .7))
    B = film.camera('Cam10b_Inside', [(SHOTS['b'], CAR_IN + Vector((.05, -2.4, .95)), CAR_IN + Vector((0, .4, .78))),
                                      (SHOTS['c'] - 1, CAR_IN + Vector((.02, -2.1, .93)), CAR_IN + Vector((0, .4, .78)))], lens=30, fstop=2.8,
                    focus=CAR_IN + Vector((0, .4, .8)))
    C = film.camera('Cam10c_Road', [(SHOTS['c'], (4, 4, 4), (1, -14, .5)), (SHOTS['end'], (3, -40, 22), (1, -110, 0))], lens=26, fstop=8,
                    focus=30.0)
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '10', still_frame=170)
