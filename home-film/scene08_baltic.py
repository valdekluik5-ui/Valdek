"""
Home - scene 8: the Baltic Sea (song 2:30-2:48).
A grey shore. He throws both hearts into the sea. They click together as they sink, and come to rest together
on the sea floor, still glowing.

Shots:  1-130   the grey shore, wide: he stands alone at the water's edge, the wind flattening the grass
      131-200   side view: he throws; the two halves arc out over the water and splash
      201-330   under the sea: the halves sink through green light, drift together - click - glow
      331-432   they rest together on the sandy sea floor, glowing softly
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

SHOTS = dict(a=1, b=131, c=201, d=331, end=432)
UW = Vector((1200.0, 0.0, 0.0))     # the sea floor set


def sand_material(name, wet_line=None):
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord'); P = tc.outputs['Object']
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; L.new(P, nz.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.25, .22, .17, 1); rp.color_ramp.elements[1].color = (.42, .38, .3, 1)
    L.new(nz.outputs['Fac'], rp.inputs['Fac'])
    col = rp.outputs['Color']
    if wet_line is not None:     # darker, glossier wet sand near the water (toward -Y)
        sep = N.new('ShaderNodeSeparateXYZ'); L.new(P, sep.inputs[0])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = wet_line; mr.inputs['From Max'].default_value = wet_line + 2.5
        L.new(sep.outputs['Y'], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; L.new(mr.outputs['Result'], inv.inputs[1])
        L.new(inv.outputs[0], mx.inputs['Factor']); L.new(col, mx.inputs['A']); mx.inputs['B'].default_value = (.45, .45, .48, 1)
        col = mx.outputs['Result']
        rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = .15; rr.inputs['To Max'].default_value = .9
        L.new(mr.outputs['Result'], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = .9
    L.new(col, b.inputs['Base Color'])
    wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.6; wv.inputs['Distortion'].default_value = 6
    L.new(P, wv.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .25
    L.new(wv.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b)
    return m


def shore(coll):
    film.HAZE.update(color=(.55, .58, .62), start=15.0, dist=180.0, strength=.8)
    sand = sand_material('ShoreSand', wet_line=-3.0)
    xs = np.linspace(-80, 80, 161); ys = np.linspace(-6, 40, 93)
    X, Y = np.meshgrid(xs, ys)
    Z = np.clip(Y + 4, 0, None) * .035 + .25 * film.fbm(X * .08, Y * .08, 3) * np.clip((Y + 2) / 6, 0, 1) + np.clip(Y - 14, 0, None) * .25
    Z = Z - .25
    beach = film.grid_mesh('Beach', X, Y, Z, coll, sand)
    sea = film.water_material('BalticSea', color=(.03, .045, .05), rough=.12, wave=.35, scale=.6)
    add_haze(sea, sea.node_tree.nodes, sea.node_tree.links, sea.node_tree.nodes['Principled BSDF'])
    film.mesh_obj('Sea', [(-400, -2.5, -.3), (400, -2.5, -.3), (400, -500, -.3), (-400, -500, -.3)], [(0, 1, 2, 3)], coll, [sea])
    foam = mat('Foam', (.7, .72, .74), rough=.6, haze=True)
    rng = np.random.default_rng(1)
    for i in range(40):
        blob(f'Foam{i}', (rng.uniform(-30, 30), -2.6 + rng.uniform(-.2, .3), -.29), (rng.uniform(.4, 1.5), rng.uniform(.04, .12), .01), coll, foam, sub=2, seed=i)
    peb = mat('Pebble', (.22, .21, .2), rough=.5, haze=True)
    for i in range(140):
        x = rng.uniform(-14, 14); y = rng.uniform(-2.2, 6)
        z = float(np.clip(y + 4, 0, None) * .035) - .25
        blob(f'Pebble{i}', (x, y, z), (rng.uniform(.03, .12),) * 2 + (rng.uniform(.02, .05),), coll, peb, sub=2, rough=.2, seed=50 + i)
    # dune grass on the rise behind (bent by the wind)
    dg = film.grid_mesh('DuneBed', *np.meshgrid(np.linspace(-30, 30, 61), np.linspace(10, 18, 17)), np.zeros((17, 61)), coll)
    for v in dg.data.vertices:
        v.co.z = float(np.clip(v.co.y + 4, 0, None) * .035 + np.clip(v.co.y - 14, 0, None) * .25) - .26
    gm = mat('DuneGrass', (.32, .3, .18), rough=.7, haze=True); dg.data.materials.append(gm)
    w = np.array([1.0] * len(dg.data.vertices)); film.vgroup(dg, 'g', w)
    mod = dg.modifiers.new('Grass', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 6000; s.use_advanced_hair = True; s.normal_factor = .35; s.object_align_factor = (.25, 0, 0)
    s.factor_random = .1; s.material_slot = 'DuneGrass'; s.child_type = 'INTERPOLATED'; s.rendered_child_count = 6; s.child_percent = 2
    s.radius_scale = .008; s.root_radius = 1; s.tip_radius = 0; s.roughness_2 = .05; s.length_random = .5; s.clump_factor = .5
    # waves: lines of foam rolling in from the grey water, spreading thin up the sand and fading, over and over
    for wv in range(5):
        for i in range(14):
            o = blob(f'Roller{wv}_{i}', (rng.uniform(-34, 34), -8, -.29), (rng.uniform(1.5, 4.0), .12, .02), coll, foam, sub=1, seed=300 + wv * 20 + i)
            off = wv * 26 + rng.integers(0, 8)
            for f0 in range(-130 + off, 450, 130):
                for df, y, sc in ((0, -9.5, .2), (60, -4.5, 1.0), (95, -2.6, 1.2), (125, -2.2, .05)):
                    o.location.y = y + rng.normal(0, .15); o.scale = (sc * rng.uniform(.9, 1.1), sc + .3, 1)
                    o.keyframe_insert('location', frame=f0 + df); o.keyframe_insert('scale', frame=f0 + df)
    # the tide line: dark seaweed, driftwood, shells
    weed = mat('Bladderwrack', (.06, .05, .02), rough=.5, haze=True)
    for i in range(70):
        x = rng.uniform(-30, 30); y = -1.4 + rng.normal(0, .25)
        blob(f'Wrack{i}', (x, y, float(np.clip(y + 4, 0, None) * .035) - .26), (rng.uniform(.1, .5), rng.uniform(.04, .12), .02), coll, weed, sub=1, seed=400 + i)
    drift = mat('Driftwood', (.42, .38, .32), rough=.8, haze=True)
    for i, (x, y, L_, rz) in enumerate(((-6.5, 1.2, 2.6, .4), (8.0, 2.5, 1.8, -.7), (-15, 3.5, 3.4, .1), (17, .8, 1.2, 1.2))):
        lg = cylinder(f'Driftwood{i}', .09 + .02 * i, L_, (x, y, float(np.clip(y + 4, 0, None) * .035) - .2), drift, coll, n=10)
        lg.rotation_euler = (PI / 2, 0, rz)
    shell = mat('Shell', (.85, .8, .72), rough=.4, haze=True)
    for i in range(60):
        x = rng.uniform(-12, 12); y = rng.uniform(-1.8, 3)
        blob(f'Shell{i}', (x, y, float(np.clip(y + 4, 0, None) * .035) - .245), (.025, .02, .008), coll, shell, sub=1, seed=500 + i)
    # an old wooden groyne running out into the water: a line of weathered posts
    post = mat('GroynePost', (.2, .17, .13), rough=.85, haze=True)
    for i in range(26):
        y = 3 - i * .55
        h = .9 + rng.uniform(-.25, .2)
        cylinder(f'Groyne{i}', .11, h, (-22 + rng.normal(0, .03), y, float(np.clip(y + 4, 0, None) * .035) - .55), post, coll, n=10)
    # the dune top: low pines bent by the wind, and a wooden boardwalk over the dune
    hi, lib = film.tree_library('DuneForest')
    for i in range(40):
        x = rng.uniform(-80, 80); y = rng.uniform(20, 38)
        z = float(np.clip(y + 4, 0, None) * .035 + np.clip(y - 14, 0, None) * .25) - .25
        t = film.place_tree(coll, hi['pine'][i % len(hi['pine'])], (x, y, z), rng.uniform(5, 9), rng)
        t.rotation_euler.x += rng.uniform(.05, .12)
    planks = mat('Boardwalk', (.38, .3, .22), rough=.75, haze=True)
    for i in range(30):
        y = 8 + i * .45
        z = float(np.clip(y + 4, 0, None) * .035 + np.clip(y - 14, 0, None) * .25) - .2
        box(f'Board{i}', (1.4, .38, .05), (12.0, y, z), planks, coll)
    return beach


def sea_floor(coll):
    film.HAZE.update(color=(.02, .12, .13), start=0.0, dist=16.0, strength=.92)
    T = lambda x, y, z: (UW.x + x, UW.y + y, UW.z + z)
    sand = sand_material('SeaSand')
    xs = np.linspace(-20, 20, 81); ys = np.linspace(-20, 20, 81)
    X, Y = np.meshgrid(xs, ys); Z = .15 * film.fbm(X * .3, Y * .3, 4)
    film.grid_mesh('SeaFloor', X + UW.x, Y + UW.y, Z + UW.z, coll, sand)
    rock = mat('SeaRock', (.08, .1, .09), rough=.7, haze=True)
    weed = mat('SeaWeed', (.05, .12, .05), rough=.6, haze=True, sss=.2)
    rng = np.random.default_rng(4)
    for i in range(30):
        a = rng.uniform(0, 2 * PI); r = rng.uniform(1.0, 12)
        blob(f'SeaRock{i}', T(math.cos(a) * r, math.sin(a) * r, 0), (rng.uniform(.2, .8), rng.uniform(.2, .7), rng.uniform(.15, .5)), coll, rock, sub=2, rough=.3, seed=i)
    for i in range(60):
        a = rng.uniform(0, 2 * PI); r = rng.uniform(.8, 10); h = rng.uniform(.4, 1.6)
        o = blob(f'Weed{i}', T(math.cos(a) * r, math.sin(a) * r, h / 2), (.03, .03, h / 2), coll, weed, sub=2, rough=.2, seed=100 + i)
        o.rotation_euler = (rng.normal(0, .2), rng.normal(0, .2), 0)
        for f in range(1, SHOTS['end'] + 1, 48):      # sway
            o.rotation_euler.x = rng.normal(0, .2) + .12 * math.sin(f / 30 + i); o.keyframe_insert('rotation_euler', frame=f)
    # light rays from the surface and the shimmering surface far above
    ray = bpy.data.materials.new('GodRay'); ray.use_nodes = True
    N, L = ray.node_tree.nodes, ray.node_tree.links; N.remove(N['Principled BSDF'])
    tr = N.new('ShaderNodeBsdfTransparent'); em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (.5, .9, .8, 1); em.inputs['Strength'].default_value = .5
    mx = N.new('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = .05; L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], N['Material Output'].inputs['Surface'])
    for i in range(8):
        c = cylinder(f'Ray{i}', rng.uniform(.15, .4), 14, T(rng.uniform(-5, 5), rng.uniform(2.5, 8), 0), ray, coll, n=12, r2=rng.uniform(.4, .8), cap=False)
        c.rotation_euler = (rng.uniform(.15, .3), rng.uniform(-.15, .15), 0); c.visible_shadow = False
    film.area_light('SeaSun', T(0, 2, 14), T(0, 0, 0), 2500, 10, (.6, 1.0, .9))
    film.area_light('SeaFill', T(0, -8, 3), T(0, 0, 1), 200, 6, (.2, .6, .6))
    bub = mat('Bubble', (.8, 1, 1), rough=.02, transmission=1.0)
    for i in range(24):
        bb = blob(f'Bubble{i}', T(rng.uniform(-1.5, 1.5), rng.uniform(-1, 2), 0), (.02,) * 3, coll, bub, sub=1)
        f0 = int(rng.uniform(SHOTS['c'], SHOTS['end'] - 40))
        for f, z in ((SHOTS['c'], rng.uniform(0, 2)), (f0, rng.uniform(.2, 2)), (f0 + 60, rng.uniform(4, 8))):
            bb.location.z = UW.z + z; bb.keyframe_insert('location', frame=f)


def build():
    bears = film.import_bears()
    w = bpy.data.worlds.new('Grey'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.5, .52, .55, 1); rp.color_ramp.elements[1].color = (.28, .31, .36, 1)
    rp.color_ramp.elements[1].position = .5; L.new(sep.outputs['Z'], rp.inputs['Fac'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(rp.outputs['Color'], mx.inputs['A']); mx.inputs['B'].default_value = (.01, .07, .08, 1)
    L.new(mx.outputs['Result'], N['Background'].inputs['Color'])
    for f, v in ((1, 0.0), (SHOTS['c'], 1.0)):
        mx.inputs['Factor'].default_value = v; mx.inputs['Factor'].keyframe_insert('default_value', frame=f)
    film._const(w.node_tree)
    film.area_light('Overcast', (0, 20, 30), (0, 0, 0), 9000, 40, (.85, .88, .95))
    sh = film.new_coll('Shore'); shore(sh)
    uw = film.new_coll('SeaFloor'); sea_floor(uw)
    he = bears.build_bear('he')
    she = bears.build_bear('she'); bears.place(she, 1, (2000, 0, 0), 0)       # she is not here
    hearts = film.new_coll('Hearts')
    hm = film.heart_material('SeaHeart', glow=.0)
    hb = hm.node_tree.nodes['Principled BSDF']
    # ---- 8a / 8b: he stands at the water's edge, then throws both halves
    bears.place(he, 1, (0, -1.6, -.18), 0, pose={'head': (14, 0, 0)})
    bears.key_pose(he, SHOTS['b'] + 10, {'shoulder.R': (10, 0, -6), 'head': (6, 0, 0)})
    bears.key_pose(he, SHOTS['b'] + 26, {'shoulder.R': (-70, 0, -12), 'forearm.R': (30, 0, 0), 'spine': (-6, 0, 0), 'head': (-4, 0, 0)})
    bears.key_pose(he, SHOTS['b'] + 32, {'shoulder.R': (150, 0, -8), 'forearm.R': (0, 0, 0), 'spine': (14, 0, 0), 'head': (-12, 0, 0)})
    bears.key_pose(he, SHOTS['b'] + 50, {'shoulder.R': (60, 0, -6), 'forearm.R': (10, 0, 0), 'spine': (8, 0, 0), 'head': (-8, 0, 0)})
    bears.key_pose(he, SHOTS['c'] - 1, {'shoulder.R': (10, 0, -6), 'forearm.R': (10, 0, 0), 'spine': (4, 0, 0), 'head': (4, 0, 0)})
    release = SHOTS['b'] + 31
    held = [film.attach_to_paw(film.heart_half(f'Held{s}', s, .13, hm, hearts), he, 'forearm.R', (sx * .03, .02, -.03), (PI / 2, 0, 0))
            for s, sx in (('L', -1), ('R', 1))]
    for o in held:
        film.key_visible(o, 1, True); film.key_visible(o, release, False)
    bpy.context.scene.frame_set(release)
    p0 = he.matrix_world @ he.pose.bones['forearm.R'].tail
    land = Vector((.3, -9.5, -.3)); splash_f = release + 34
    for k, (s, sx) in enumerate((('L', -1), ('R', 1))):
        o = film.heart_half(f'Flying{s}', s, .13, hm, hearts)
        film.key_visible(o, 1, False); film.key_visible(o, release, True); film.key_visible(o, splash_f, False)
        for i in range(9):
            t = i / 8; f = release + t * (splash_f - release)
            pos = p0.lerp(land + Vector((sx * .15, 0, 0)), t) + Vector((0, 0, 2.2 * 4 * t * (1 - t)))
            o.location = pos; o.rotation_euler = (t * 7, t * 3 * sx, 0)
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)
    spray = mat('Spray', (.85, .88, .9), rough=.3)
    rng = np.random.default_rng(7)
    for i in range(10):
        sp = blob(f'Spray{i}', land, (.04, .04, .06), hearts, spray, sub=1)
        film.key_visible(sp, 1, False); film.key_visible(sp, splash_f, True); film.key_visible(sp, splash_f + 14, False)
        sp.location = land; sp.keyframe_insert('location', frame=splash_f)
        sp.location = land + Vector((rng.normal(0, .25), rng.normal(0, .25), rng.uniform(.3, .7))); sp.keyframe_insert('location', frame=splash_f + 7)
        sp.location.z = land.z; sp.keyframe_insert('location', frame=splash_f + 14)
    # ---- 8c / 8d: under the sea: they sink, drift together, click, rest glowing
    rest = Vector((UW.x, UW.y, UW.z + .1)); click = 300
    for s, sx in (('L', -1), ('R', 1)):
        o = film.heart_half(f'Sinking{s}', s, .13, hm, hearts)
        film.key_visible(o, 1, False); film.key_visible(o, SHOTS['c'], True)
        keys = [(SHOTS['c'], Vector((sx * .22, .1, 5.5)), (.4 * sx, .2, .8 * sx)), (250, Vector((sx * .16, .05, 2.6)), (.2 * sx, .1, .4 * sx)),
                (click - 4, Vector((sx * .03, 0, .9)), (0.02 * sx, 0, .05 * sx)), (click, Vector((0, 0, .85)), (0, 0, 0)),
                (SHOTS['d'], Vector((0, 0, .1)), (-.45, 0, .1)), (SHOTS['end'], Vector((0, 0, .1)), (-.45, 0, .1))]
        for f, p, r in keys:
            o.location = rest + p - Vector((0, 0, .1)); o.rotation_euler = r
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)
    for f, g in ((1, 0.0), (SHOTS['c'], .3), (click - 1, .3), (click, 7.0), (click + 16, 1.6), (SHOTS['d'], 1.2), (370, 1.8), (400, 1.1), (SHOTS['end'], 1.6)):
        hb.inputs['Emission Strength'].default_value = g; hb.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
    glowl = film.point_light('HeartGlow', rest + Vector((0, -.05, .2)), 0, (1, .3, .35), .05)
    for f, e in ((1, 0), (click - 1, 0), (click, 40), (click + 16, 8), (SHOTS['end'], 8)):
        glowl.data.energy = e; glowl.data.keyframe_insert('energy', frame=f)
    # ---- cameras
    A = film.camera('Cam8a_Shore', [(SHOTS['a'], (3.5, 9.0, 1.5), (-.6, -6, .2)), (SHOTS['b'] - 1, (3.1, 8.0, 1.4), (-.5, -6, .2))], lens=28, fstop=5.6,
                    focus=(0, -1.6, .4))
    Bc = film.camera('Cam8b_Throw', [(SHOTS['b'], (3.2, 2.6, 1.3), (.7, -4.5, 1.2)), (SHOTS['c'] - 1, (3.0, 2.3, 1.3), (.5, -6, 1.1))], lens=20, fstop=5.6,
                     focus=(0, -2, .6))
    track = [(SHOTS['c'], 5.4), (250, 2.5), (click - 4, .82), (click, .76), (SHOTS['d'] - 1, .05)]     # follow the sinking halves
    C = film.camera('Cam8c_Sinking', [(f, rest + Vector((.15, -1.7, z + .15)), rest + Vector((0, 0, z))) for f, z in track], lens=40, fstop=2.8,
                    focus=1.7)
    D = film.camera('Cam8d_Rest', [(SHOTS['d'], rest + Vector((.4, -1.3, .45)), rest), (SHOTS['end'], rest + Vector((.25, -.8, .3)), rest)], lens=40, fstop=2.0,
                    focus=tuple(rest))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], Bc), (SHOTS['c'], C), (SHOTS['d'], D)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '08', still_frame=300)
