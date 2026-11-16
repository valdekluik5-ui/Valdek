"""
Home - scene 13: through the storms (song 4:04-4:35). Hard times, shown symbolically: storms come and go,
and they always come back to each other.
"She ran when she was scared. He chased when he was scared." / "Until they learned to say the scared part out loud."

Shots:  1-260   a hill with one big tree under a huge sky; they sit together; storm clouds roll in; she runs, he chases
      261-380   the storm at its worst: apart on the open field in the rain, lightning; both stop
      381-520   it clears; they turn to each other; she says the scared part out loud - a small glowing heart floats to him
      521-744   they walk back up to the tree together; a short storm passes over, they stay; warm evening light
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

SHOTS = dict(a=1, b=261, c=381, d=521, end=648)


def hill_z(x, y):
    r2 = x * x + y * y
    return 3.0 * np.exp(-r2 / 260.0) + .4 * film.fbm(x / 20, y / 20, 3)


def gz(x, y):
    return float(hill_z(np.array(float(x)), np.array(float(y))))


def build_world(coll):
    grass = mat('HillGrass', (.06, .14, .03), rough=.9, haze=True)
    xs = np.linspace(-200, 200, 161); X, Y = np.meshgrid(xs, xs)
    Z = hill_z(X, Y) + np.clip((np.hypot(X, Y) - 120) / 40, 0, 1) * 12 * (film.fbm(X / 50, Y / 50, 3) + .5)
    land = film.grid_mesh('Hill', X, Y, Z, coll, grass)
    # grass blades near the tree
    gx, gy = np.meshgrid(np.linspace(-14, 14, 57), np.linspace(-18, 10, 57))
    bed = film.grid_mesh('GrassBed', gx, gy, hill_z(gx, gy) - .01, coll, grass)
    gm = mat('Blades', (.06, .16, .03), rough=.6); bed.data.materials.append(gm)
    film.vgroup(bed, 'g', np.ones(gx.size))
    mod = bed.modifiers.new('Grass', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 14000; s.use_advanced_hair = True; s.normal_factor = .1; s.factor_random = .04; s.object_align_factor = (.03, 0, 0)
    s.material_slot = 'Blades'; s.child_type = 'INTERPOLATED'; s.rendered_child_count = 8; s.child_percent = 2; s.child_radius = .1
    s.roughness_2 = .03; s.radius_scale = .005; s.root_radius = 1; s.tip_radius = 0; s.length_random = .5
    film.meadow('HillMeadow', (2, -6), (22, 26), coll, z_fn=hill_z, density=.6, seed=13, keep_clear=[(0, -1.6, 1.2)])
    # the big tree: a broad old tree (trunk and branches + leafy clumps)
    bark = mat('OakBark', (.06, .045, .035), rough=.9, haze=True)
    leaves = film.foliage_material('OakLeaves', (.04, .1, .02), (.12, .22, .04), tint=(.8, .9, .4))
    me = film.bare_tree('BigTree', 7, [bark])
    tree = link(bpy.data.objects.new('BigTree', me), coll); tree.location = (0, 1.2, gz(0, 1.2) - .1); tree.scale = (8, 8, 6.5)
    rng = np.random.default_rng(5)
    leaves.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = .25     # light glows through the leaves
    film.leafy_crown('Crown', (0, 1.2, gz(0, 1.2) + 5.4), 4.4, coll, leaves, height=3.2, clusters=48000, leaf=.13, seed=5)
    return land


def clouds(coll):
    """Storm clouds: big dark puffs that roll in, hang over the hill, and roll away (twice)."""
    dark = mat('StormCloud', (.08, .085, .095), rough=1.0)
    rng = np.random.default_rng(9)
    puffs = []
    for i in range(60):
        c = Vector((rng.uniform(-60, 60), rng.uniform(-40, 70), rng.uniform(22, 34)))
        o = blob(f'Cloud{i}', c, (rng.uniform(8, 16), rng.uniform(6, 12), rng.uniform(3, 6)), coll, dark, sub=3, rough=.35, seed=i)
        o.visible_shadow = True
        puffs.append((o, c))
    # storm 1: in over 80-200, gone by 470; storm 2 (short): 590-700
    for o, c in puffs:
        off = Vector((160, 0, 0))
        for f, d in ((1, off), (80, off), (200, Vector((0, 0, 0))), (380, Vector((0, 0, 0))), (470, -off),
                     (560, off), (620, Vector((0, 0, 4))), (660, Vector((0, 0, 4))), (720, -off)):
            o.location = c + d; o.keyframe_insert('location', frame=f)
        import bears
        for fc in bears._fcurves(o):
            for kp in fc.keyframe_points:
                if abs(kp.co.x - 470) < 1 or abs(kp.co.x - 560) < 1:
                    kp.interpolation = 'CONSTANT'     # jump back off-screen between the storms


def build():
    bears = film.import_bears()
    import scene07_storm as s7
    importlib.reload(s7)
    film.HAZE.update(color=(.7, .75, .8), start=40.0, dist=300.0, strength=.45)
    w, sky, bg, ramp = film.make_sky(elev=20, az=-40, strength=.35, low=(1, .85, .7), mid=(1, .9, .85), high=(.75, .82, 1.0), aerosol=2)
    sun = film.make_sun(elev=20, az=-40, energy=2.6, color=(1, .9, .75))
    bpy.context.scene.view_settings.exposure = -.3
    # weather: (frame, sun energy, sky strength, sun elevation, sun colour)
    weather = [(1, 2.6, .35, 20, (1, .9, .75)), (80, 2.6, .35, 20, (1, .9, .75)), (200, .25, .06, 20, (.7, .75, .9)), (380, .25, .06, 18, (.7, .75, .9)),
               (470, 2.4, .3, 14, (1, .85, .65)), (590, 2.4, .3, 10, (1, .8, .6)), (630, .6, .1, 9, (.8, .8, .9)), (690, 2.6, .32, 7, (1, .66, .42)),
               (744, 2.8, .35, 5, (1, .6, .38))]
    for f, en, st, el, col in weather:
        sun.data.energy = en; sun.data.color = col; sun.data.keyframe_insert('energy', frame=f); sun.data.keyframe_insert('color', frame=f)
        bg.inputs['Strength'].default_value = st; bg.inputs['Strength'].keyframe_insert('default_value', frame=f)
        film.aim_sun(sun, el, -40); sun.keyframe_insert('rotation_euler', frame=f)
        sky.sun_elevation = math.radians(el); sky.keyframe_insert('sun_elevation', frame=f)
    world = film.new_coll('Hill'); build_world(world)
    cl = film.new_coll('Clouds'); clouds(cl)
    # rain and lightning during the storms
    rain = film.new_coll('Rain')
    sheets = [s7.rain_sheet(f'HillRain{i}', (x, y, 4), (sz, 12), (0, 0, 0), rain, speed=.6, strength=.5, density=.74, fine=90)
              for i, (x, y, sz) in enumerate(((0, -14, 10), (2, -6, 20), (0, 4, 40), (0, 20, 80)))]
    for sh in sheets:
        for f, on in ((1, False), (190, True), (440, False), (615, True), (670, False)):
            film.key_visible(sh, f, on)
    flash = film.area_light('Lightning', (-20, 30, 40), (0, 0, 0), 0, 30, (.85, .9, 1.0))
    for f0 in (230, 300, 345, 640):
        for f, e in ((f0 - 1, 0), (f0, 2e5), (f0 + 2, 3e4), (f0 + 3, 1.5e5), (f0 + 6, 0)):
            flash.data.energy = e; flash.data.keyframe_insert('energy', frame=f)
    film._const(flash.data)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    # ---- 1: under the tree; the storm comes; she runs; he chases
    hx, sx_, sy = -.32, .32, -1.6
    bears.place(he, 1, (hx, sy, gz(hx, sy)), 0, sitting=True); bears.place(she, 1, (sx_, sy, gz(sx_, sy)), 0, sitting=True)
    bears.turn_head(she, 120, yaw=0, nod=-8); bears.turn_head(she, 150, yaw=0, nod=-14)          # she looks up at the sky
    run0 = 170
    bears.stand_up(she, run0, (sx_, sy - .25, gz(sx_, sy - .25)), dur=12)
    path_s = [(sx_, sy - .25), (4.0, -9.0), (6.0, -14.0)]
    bears.walk(she, run0 + 20, SHOTS['b'] + 40, (path_s[0][0], path_s[0][1], gz(*path_s[0])), (path_s[2][0], path_s[2][1], gz(*path_s[2])), cycle=10, stride=38)
    chase0 = 205
    bears.stand_up(he, chase0, (hx, sy - .25, gz(hx, sy - .25)), dur=12)
    bears.walk(he, chase0 + 20, SHOTS['b'] + 60, (hx, sy - .25, gz(hx, sy - .25)), (4.2, -11.5, gz(4.2, -11.5)), cycle=11, stride=36)
    # ---- 2: apart in the rain; both stop. she faces away, he stands behind her
    b_ = SHOTS['b']
    bears.turn_head(she, b_ + 60, nod=20); bears.turn_head(he, b_ + 70, nod=6)
    # ---- 3: it clears; she turns to him; the glowing heart (the scared part, said out loud) floats from her to him
    c = SHOTS['c']
    bears.hold(she, c + 20); she.rotation_euler.z = bears.facing(-1.8, 2.5); bears.hold(she, c + 50)
    bears.turn_head(she, c + 50, nod=4); bears.turn_head(he, c + 60, nod=0)
    pS = Vector((6.0, -14.0, gz(6.0, -14.0))); pH = Vector((4.2, -11.5, gz(4.2, -11.5)))
    hm = film.heart_material('Spoken', glow=4.0)
    hearts = film.new_coll('Spoken')
    for side in ('L', 'R'):
        o = film.heart_half('Spoken' + side, side, .24, hm, hearts)
        film.key_visible(o, 1, False); film.key_visible(o, c + 66, True); film.key_visible(o, SHOTS['d'] - 6, False)
        for f, p, s_ in ((c + 66, pS + Vector((0, 0, .75)), .3), (c + 90, pS.lerp(pH, .4) + Vector((0, 0, 1.0)), 1.0),
                         (c + 120, pS.lerp(pH, .8) + Vector((0, 0, .9)), 1.0), (SHOTS['d'] - 7, pH + Vector((0, 0, .65)), .6)):
            o.location = p; o.scale = (s_,) * 3; o.keyframe_insert('location', frame=f); o.keyframe_insert('scale', frame=f)
        o['_s'] = (1, 1, 1)
    gl = film.point_light('SpokenGlow', pS + Vector((0, 0, .8)), 0, (1, .4, .4), .1)
    for f, p, e in ((c + 65, pS, 0), (c + 66, pS, 30), (c + 120, pS.lerp(pH, .8), 30), (SHOTS['d'] - 6, pH, 0)):
        gl.location = p + Vector((0, 0, .9)); gl.data.energy = e
        gl.keyframe_insert('location', frame=f); gl.data.keyframe_insert('energy', frame=f)
    bears.set_eyes(he, 'heart', SHOTS['d'] - 10); bears.set_eyes(he, 'open', SHOTS['d'] + 20)
    bears.set_eyes(she, 'heart', SHOTS['d'] - 4); bears.set_eyes(she, 'open', SHOTS['d'] + 26)
    # ---- 4: back up the hill together, paw in paw; sit under the tree; the short storm passes; evening
    d = SHOTS['d']
    bears.place(he, d, (pH.x - .3, pH.y, pH.z), bears.facing(-4, 10)); bears.place(she, d, (pH.x + .3, pH.y - .2, pH.z), bears.facing(-4, 10))
    bears.walk(he, d + 4, d + 80, (pH.x - .3, pH.y, pH.z), (hx, sy - .3, gz(hx, sy - .3)), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)})
    bears.walk(she, d + 4, d + 80, (pH.x + .3, pH.y - .2, pH.z), (sx_, sy - .3, gz(sx_, sy - .3)), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)}, phase=2)
    for b, x_, pose in ((he, hx, {'shoulder.R': (14, 0, -30)}), (she, sx_, {'shoulder.L': (14, 0, 30), 'spine': (8, 0, 10), 'head': (6, -14, 14)})):
        b.rotation_euler.z = 0; bears.hold(b, d + 84)                                       # turn to the view, then sit down together
        bears.sit_down(b, d + 86, (x_, sy, gz(x_, sy) - b['sitDrop'] + .1 * b.scale[0]), dur=18)
        bears.key_pose(b, d + 112, pose)
    bears.set_eyes(she, 'closed', d + 116)
    # ---- cameras
    A = film.camera('Cam13a_Hill', [(SHOTS['a'], (7, -14, 4.0), (0, -1, 4.2)), (SHOTS['b'] - 1, (6, -14, 3.8), (2, -5, 3.4))], lens=26, fstop=8, focus=13.0)
    B = film.camera('Cam13b_Apart', [(SHOTS['b'], (9.5, -19.0, gz(9.5, -19) + 1.0), (5.5, -13, gz(5.5, -13) + .5)),
                                     (SHOTS['c'] - 1, (9.0, -18.6, gz(9, -18.6) + .95), (5.5, -13, gz(5.5, -13) + .5))], lens=30, fstop=4, focus=5.0)
    mid = (pS + pH) / 2
    perp = Vector((.81, .59, 0))           # side-on to the line between them
    C = film.camera('Cam13c_Said', [(SHOTS['c'], mid + perp * 7.0 + Vector((0, 0, 2.2)), mid + Vector((0, 0, .5))),
                                    (SHOTS['d'] - 1, mid + perp * 6.2 + Vector((0, 0, 2.0)), mid + Vector((0, 0, .55)))], lens=20, fstop=5.6, focus=6.8)
    D = film.camera('Cam13d_Together', [(SHOTS['d'], (9, -20, 4.0), (1, -4, 2.5)), (SHOTS['end'], (5, -11, 3.2), (0, 0, 3.0))], lens=26, fstop=8, focus=12.0)
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C), (SHOTS['d'], D)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '13', still_frame=450)
