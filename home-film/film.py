"""
Home - shared toolkit for every scene script: the song timeline, scene setup, render settings, sky and sun,
materials, noise, terrain helpers, trees, cameras and the command line.

Each scene script (sceneNN_*.py) calls film.run(build, 'NN') at the bottom.
"""
import os, sys, math, time, importlib
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

PI = math.pi
FPS = 24

# ---------------------------------------------------------------- the film, cut to the song (5:05)
# Song shape: quiet intro 0:00-0:50, slow build, heavier 1:40-2:40, rising 2:40-3:30, strongest 3:30-4:30,
# sudden quiet break 4:35-4:45 (the proposal), big final peak 4:45-5:05.
# (start, end) in seconds of the song; captions: (text, start, end) in seconds of the song.
TIMELINE = {
    '01': dict(name='Helsinki, spring', t=(0.0, 32.0), captions=[
        ("Helsinki in spring never fully lets go of winter.", 2.0, 10.5),
        ("We met a few times that year.", 13.0, 20.0),
        ("Never in a way that defined anything.", 25.5, 31.0)]),
    '02': dict(name='It feels like home', t=(32.0, 50.0), captions=[
        ("“How does it feel?”", 34.0, 38.5), ("“It feels like home.”", 39.0, 43.5),
        ("“It feels like home to me too.”", 44.0, 49.0)]),
    '03': dict(name='Asking her out', t=(50.0, 62.0), captions=[
        ("I asked you out properly.", 51.5, 56.0), ("And you chose to come.", 56.5, 61.0)]),
    '04': dict(name='First date', t=(62.0, 88.0), captions=[
        ("Things didn't become perfect.", 72.0, 86.0), ("But they became real.", 75.0, 86.0)]),
    '05': dict(name='Ordinary evenings', t=(88.0, 104.0), captions=[
        ("Not because they were extraordinary.", 90.0, 96.0), ("Because they felt like peace.", 97.0, 103.0)]),
    '06': dict(name='The magnetic hearts', t=(104.0, 124.0), captions=[
        ("“This is my heart. I'm giving it to you.”", 105.5, 110.5), ("“And this is mine.”", 111.0, 115.0)]),
    '07': dict(name='The storm', t=(124.0, 150.0), captions=[
        ("You believed you were protecting me.", 132.0, 137.0), ("I believed I was fighting for you.", 137.5, 142.0),
        ("Neither of us understood that we were acting from the same place.", 143.0, 147.0), ("Love.", 147.0, 149.5)]),
    '08': dict(name='The Baltic Sea', t=(150.0, 168.0), captions=[]),
    '09': dict(name='The call', t=(168.0, 184.0), captions=[("“I'm lost.”", 171.0, 175.0)]),
    '10': dict(name='Please drive', t=(184.0, 198.0), captions=[
        ("For the first time in a long time, the future didn't feel frightening.", 186.0, 192.0),
        ("It felt possible.", 192.5, 197.0)]),
    '11': dict(name='June, the train to Kyiv', t=(198.0, 214.0), captions=[
        ("You feel like home.", 206.0, 210.0), ("And somehow, you always did.", 210.0, 213.5)]),
    '12': dict(name='The road north', t=(214.0, 244.0), captions=[]),
    '13': dict(name='Through the storms', t=(244.0, 275.0), captions=[
        ("She ran when she was scared. He chased when he was scared.", 252.0, 260.0),
        ("Until they learned to say the scared part out loud.", 262.0, 270.0)]),
    '14': dict(name='The Rainbow Bridge', t=(275.0, 287.0), captions=[]),
    '15': dict(name='The wedding', t=(287.0, 297.0), captions=[]),
    '16': dict(name='Home', t=(297.0, 305.0), captions=[("You feel like home.", 299.5, 304.5)]),
}


def scene_frames(sid):
    a, b = TIMELINE[sid]['t']
    return 1, int(round((b - a) * FPS))


# ---------------------------------------------------------------- noise
_PERM = np.random.default_rng(7).random((256, 256))


def vnoise(x, y):
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    g = lambda a, b: _PERM[a & 255, b & 255]
    return (g(xi, yi) * (1 - u) + g(xi + 1, yi) * u) * (1 - v) + (g(xi, yi + 1) * (1 - u) + g(xi + 1, yi + 1) * u) * v


def fbm(x, y, oct=5):
    s, a, f = 0, .5, 1
    for _ in range(oct):
        s = s + a * (vnoise(x * f, y * f) - .5); a *= .5; f *= 2.03
    return s


# ---------------------------------------------------------------- scene basics
def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.armatures, bpy.data.cameras,
                 bpy.data.lights, bpy.data.particles, bpy.data.worlds, bpy.data.actions, bpy.data.node_groups):
        for d in list(coll):
            coll.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    bpy.context.scene.timeline_markers.clear()


def new_coll(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob); return ob


def mesh_obj(name, verts, faces, coll=None, mats=(), smooth=False, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    if smooth:
        me.shade_smooth()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me); ob.location = loc
    return link(ob, coll)


def grid_mesh(name, X, Y, Z, coll=None, mat=None):
    ny, nx = X.shape
    V = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    I, J = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1))
    a = (J * nx + I).ravel()
    F = np.stack([a, a + 1, a + 1 + nx, a + nx], 1).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
    me.loops.add(len(F) * 4); me.polygons.add(len(F))
    me.loops.foreach_set('vertex_index', F.ravel()); me.polygons.foreach_set('loop_start', np.arange(len(F), dtype=np.int32) * 4)
    me.update(calc_edges=True); me.shade_smooth()
    if mat:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), coll)


def vgroup(ob, name, w):
    g = ob.vertex_groups.new(name=name)
    idx = np.nonzero(np.asarray(w) > 1e-3)[0]
    for v, x in zip(idx.tolist(), np.asarray(w)[idx].tolist()):
        g.add([v], float(x), 'REPLACE')
    return g


def box(name, size, loc, mat=None, coll=None, rot=(0, 0, 0), bevel=0.0):
    """Axis box: size (sx, sy, sz) full size, loc = centre of the bottom face."""
    sx, sy, sz = [s / 2 for s in size]
    V = [(-sx, -sy, 0), (sx, -sy, 0), (sx, sy, 0), (-sx, sy, 0), (-sx, -sy, 2 * sz), (sx, -sy, 2 * sz), (sx, sy, 2 * sz), (-sx, sy, 2 * sz)]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, V, F, coll, [mat] if mat else [], loc=loc); ob.rotation_euler = rot
    if bevel:
        m = ob.modifiers.new('Bevel', 'BEVEL'); m.width = bevel; m.segments = 2
    return ob


def cylinder(name, r, h, loc, mat=None, coll=None, n=24, r2=None, cap=True, smooth=True):
    r2 = r if r2 is None else r2
    V = [(math.cos(2 * PI * i / n) * r, math.sin(2 * PI * i / n) * r, 0) for i in range(n)] + \
        [(math.cos(2 * PI * i / n) * r2, math.sin(2 * PI * i / n) * r2, h) for i in range(n)]
    F = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    if cap:
        F += [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    ob = mesh_obj(name, V, F, coll, [mat] if mat else [], loc=loc)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = len(p.vertices) == 4
    return ob


def dome(name, r, loc, mat=None, coll=None, zscale=1.0, n=32, rings=12, ribs=0):
    """Half sphere (onion-free classical dome) sitting at loc."""
    V, F = [], []
    for j in range(rings + 1):
        a = (PI / 2) * j / rings
        for i in range(n):
            u = 2 * PI * i / n
            rr = r * math.cos(a) * (1 + (.03 if ribs and i % (n // ribs) == 0 else 0))
            V.append((math.cos(u) * rr, math.sin(u) * rr, r * math.sin(a) * zscale))
    for j in range(rings):
        for i in range(n):
            a = j * n + i; b = j * n + (i + 1) % n
            F.append((a, b, b + n, a + n))
    ob = mesh_obj(name, V, F, coll, [mat] if mat else [], smooth=True, loc=loc)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(ob.data); bm.free()
    ob.data.shade_smooth()
    return ob


def blob(name, center, radii, coll=None, mat=None, sub=3, rough=.25, seed=0):
    """Lumpy organic blob (snowbanks, bushes, boulders)."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1)
    rng = np.random.default_rng(seed)
    off = rng.random(3) * 50
    for v in bm.verts:
        n = fbm(np.array(v.co.x * 2 + off[0]), np.array(v.co.y * 2 + v.co.z * 1.3 + off[1]), 4)
        k = 1 + rough * float(n) * 2
        v.co = Vector((v.co.x * radii[0] * k, v.co.y * radii[1] * k, v.co.z * radii[2] * k))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = center
    return link(ob, coll)


# ---------------------------------------------------------------- materials
HAZE = dict(color=(.95, .55, .45), start=30.0, dist=260.0, strength=.6)


def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']


def add_haze(m, N, L, bsdf, color=None, dist=None, strength=None):
    """Aerial perspective: far things fade into the haze colour (EEVEE and Cycles)."""
    color = color or HAZE['color']; dist = dist or HAZE['dist']; strength = HAZE['strength'] if strength is None else strength
    out = N['Material Output']
    cd = N.new('ShaderNodeCameraData')
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = HAZE['start']; mr.inputs['From Max'].default_value = dist
    mr.inputs['To Max'].default_value = strength; mr.interpolation_type = 'SMOOTHERSTEP'
    L.new(cd.outputs['View Distance'], mr.inputs['Value'])
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = 1
    mix = N.new('ShaderNodeMixShader')
    L.new(mr.outputs['Result'], mix.inputs['Fac']); L.new(bsdf.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])
    m['haze_emission'] = em.name
    return em


def mat(name, color, rough=.5, metal=0.0, emission=None, strength=0.0, coat=0.0, alpha=1.0, haze=False, transmission=0.0, sss=0.0):
    m, N, L, b = node_mat(name)
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1); b.inputs['Emission Strength'].default_value = strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    if haze:
        add_haze(m, N, L, b)
    return m


def emit_mat(name, color, strength=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.remove(N['Principled BSDF'])
    e = N.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*color, 1); e.inputs['Strength'].default_value = strength
    L.new(e.outputs[0], N['Material Output'].inputs['Surface'])
    return m


def water_material(name='Water', color=(.005, .012, .02), rough=.035, wave=.08, scale=.35):
    m, N, L, b = node_mat(name)
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['IOR'].default_value = 1.33
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 3, 1)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 3
    L.new(mp.outputs['Vector'], n.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = wave
    L.new(n.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def snow_material(name='Snow', wet=.0):
    m, N, L, b = node_mat(name)
    b.inputs['Base Color'].default_value = (.82, .85, .9, 1); b.inputs['Roughness'].default_value = .45 - .3 * wet
    b.inputs['Subsurface Weight'].default_value = .4; b.inputs['Subsurface Radius'].default_value = (.4, .5, .7)
    tc = N.new('ShaderNodeTexCoord'); n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 30; n.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], n.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .25
    L.new(n.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


# ---------------------------------------------------------------- sky and light
def make_sky(elev=4.0, az=0.0, strength=.9, low=(1.0, .42, .22), mid=(1.0, .62, .55), high=(.75, .78, 1.0),
             air=2.2, aerosol=5.0, ozone=3.0, sun_disc=True):
    """Physical sky with a colour tint near the horizon. az: degrees, 0 = sun toward -Y, + = toward +X.
    Returns (world, sky node, background node, ramp) so a scene can animate them."""
    w = bpy.data.worlds.new('Sky'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    bg = N['Background']
    sky = N.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(elev); sky.sun_rotation = math.radians(180 - az)
    sky.air_density = air; sky.aerosol_density = aerosol; sky.ozone_density = ozone
    sky.sun_size = math.radians(2.2); sky.sun_intensity = .35; sky.altitude = 200; sky.sun_disc = sun_disc
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -.02; mr.inputs['From Max'].default_value = .45
    L.new(sep.outputs['Z'], mr.inputs['Value'])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = (*low, 1); r.elements[1].position = 1; r.elements[1].color = (*high, 1)
    e = r.elements.new(.25); e.color = (*mid, 1)
    L.new(mr.outputs['Result'], ramp.inputs['Fac'])
    tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1
    L.new(sky.outputs['Color'], tint.inputs['A']); L.new(ramp.outputs['Color'], tint.inputs['B'])
    L.new(tint.outputs['Result'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    return w, sky, bg, ramp


def make_sun(elev=4.0, az=0.0, energy=2.5, color=(1.0, .7, .5), angle=1.5):
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = energy; ld.color = color; ld.angle = math.radians(angle)
    sun = link(bpy.data.objects.new('Sun', ld))
    aim_sun(sun, elev, az)
    return sun


def aim_sun(sun, elev, az):
    sun.rotation_euler = (math.radians(90 - elev), 0, math.radians(az))


def area_light(name, loc, target, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size; ld.color = color
    o = link(bpy.data.objects.new(name, ld)); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def point_light(name, loc, energy, color=(1, .8, .6), radius=.1):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = color; ld.shadow_soft_size = radius
    o = link(bpy.data.objects.new(name, ld)); o.location = loc
    return o


def key_light(lamp, frame, **vals):
    """Keyframe light data values (energy, color) at a frame, constant (for changes at cuts)."""
    for k, v in vals.items():
        setattr(lamp.data, k, v); lamp.data.keyframe_insert(k, frame=frame)
    _const(lamp.data)


def key_value(owner, path, frame, value, const=True):
    setattr(owner, path, value); owner.keyframe_insert(path, frame=frame)
    if const:
        _const(owner)


def _const(idb):
    ad = idb.animation_data if hasattr(idb, 'animation_data') else None
    if not ad or not ad.action:
        return
    import bears
    for fc in bears._fcurves(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'


# ---------------------------------------------------------------- cameras
def look(cam, target):
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()


def camera(name, keys, lens=35, fstop=None, focus=None):
    """keys: [(frame, location, target), ...] (a slow move between them). Returns the camera object."""
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
    cam = link(bpy.data.objects.new(name, cd))
    for f, loc, tgt in keys:
        cam.location = loc; look(cam, tgt)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    if fstop:
        cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
        if isinstance(focus, (int, float)):
            cd.dof.focus_distance = focus
        elif focus is not None:
            if isinstance(focus, bpy.types.Object):
                cd.dof.focus_object = focus
            else:
                e = link(bpy.data.objects.new(name + '_focus', None)); e.location = focus; cd.dof.focus_object = e
    import bears
    for fc in bears._fcurves(cam):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'
    return cam


def cut(frame, cam):
    """At `frame` the film cuts to camera `cam` (timeline marker bound to the camera)."""
    mk = bpy.context.scene.timeline_markers.new(cam.name, frame=frame); mk.camera = cam
    if frame <= 1:
        bpy.context.scene.camera = cam


# ---------------------------------------------------------------- trees (Nuuksio forest: Scots pine, spruce, birch)
def _cyl(V, F, M, p0, p1, r0, r1, n, mi):
    p0, p1 = np.array(p0, float), np.array(p1, float); d = p1 - p0; d /= np.linalg.norm(d)
    a = np.array([1., 0, 0]) if abs(d[0]) < .9 else np.array([0, 1., 0])
    u = np.cross(d, a); u /= np.linalg.norm(u); w = np.cross(d, u)
    o = len(V)
    for p, r in ((p0, r0), (p1, r1)):
        for i in range(n):
            t = 2 * PI * i / n; V.append(tuple(p + r * (math.cos(t) * u + math.sin(t) * w)))
    for i in range(n):
        F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i)); M.append(mi)


def _clump(V, F, M, c, r, squash, rng, mi, sub):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1)
    bm.verts.ensure_lookup_table(); bm.verts.index_update()
    o = len(V)
    for v in bm.verts:
        k = 1 + rng.uniform(-.3, .3)
        V.append((c[0] + v.co.x * r * k, c[1] + v.co.y * r * k, c[2] + v.co.z * r * squash * k))
    for f in bm.faces:
        F.append(tuple(o + v.index for v in f.verts)); M.append(mi)
    bm.free()


def _finish(name, V, F, M, mats):
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
    me.polygons.foreach_set('material_index', M)
    for mt in mats:
        me.materials.append(mt)
    me.shade_smooth()
    return me


def scots_pine(name, seed, mats, lod=0):
    rng = np.random.default_rng(seed)
    V, F, M = [], [], []
    lean = rng.normal(0, .035, 2)
    zs = np.linspace(0, .97, 7)
    pts = [(lean[0] * z + .01 * math.sin(z * 9 + seed), lean[1] * z + .01 * math.cos(z * 7 + seed), z) for z in zs]
    n = 8 if lod == 0 else 5
    for a, b_, z in zip(pts[:-1], pts[1:], zs[:-1]):
        _cyl(V, F, M, a, b_, .02 * (1 - z * .78), .02 * (1 - (z + .16) * .78), n, 1)
    trunk_at = lambda z: np.array([lean[0] * z, lean[1] * z, z])
    c0 = rng.uniform(.6, .72); nb = 10 if lod == 0 else 6
    for k in range(nb):
        z = c0 + (.94 - c0) * k / (nb - 1) + rng.normal(0, .015)
        az = k * 2.4 + rng.normal(0, .4)
        L = (.07 + .17 * (1 - (z - c0) / (1 - c0))) * rng.uniform(.7, 1.25)
        base = trunk_at(z); end = base + L * np.array([math.cos(az), math.sin(az), rng.uniform(.15, .55)])
        if lod == 0:
            _cyl(V, F, M, base, end, .006, .0025, 5, 1)
        _clump(V, F, M, end + [0, 0, .015], rng.uniform(.05, .075), .72, rng, 0, 2 if lod == 0 else 1)
        if lod == 0:
            _clump(V, F, M, end + rng.normal(0, .03, 3) + [0, 0, .03], rng.uniform(.035, .05), .8, rng, 0, 1)
    _clump(V, F, M, trunk_at(.98) + [0, 0, .02], .06, .7, rng, 0, 2 if lod == 0 else 1)
    return _finish(name, V, F, M, mats)


def spruce(name, seed, mats, lod=0):
    rng = np.random.default_rng(seed)
    V, F, M = [], [], []
    _cyl(V, F, M, (0, 0, 0), (0, 0, .95), .02, .005, 6, 1)
    tiers = 18 if lod == 0 else 8
    for k in range(tiers):
        f = k / (tiers - 1)
        zb = .1 + .84 * f + rng.normal(0, .006)
        R = (.21 * (1 - f) ** .95 + .025) * rng.uniform(.85, 1.15)
        hgt = .09 + .04 * (1 - f)
        spikes = int(rng.integers(13, 19)) if lod == 0 else 8
        ring = []; rot = rng.uniform(0, 2 * PI)
        for i in range(spikes * 2):
            a = rot + PI * i / spikes + rng.normal(0, .08)
            rr = R * (1 if i % 2 == 0 else .42) * rng.uniform(.7, 1.25)
            ring.append((math.cos(a) * rr, math.sin(a) * rr, zb - (.25 if i % 2 == 0 else .05) * rr))
        m = len(ring); o = len(V)
        V.extend(ring); V.extend([(x * .35, y * .35, z + hgt * .25) for x, y, z in ring])
        V.append((rng.normal(0, .008), rng.normal(0, .008), zb + hgt)); V.append((0, 0, zb - .02))
        for i in range(m):
            F.append((o + i, o + (i + 1) % m, o + (i + 1) % m + m, o + i + m)); M.append(0)
            F.append((o + i + m, o + (i + 1) % m + m, o + 2 * m)); M.append(0)
            F.append((o + (i + 1) % m, o + i, o + 2 * m + 1)); M.append(0)
    return _finish(name, V, F, M, mats)


def birch(name, seed, mats, lod=0):
    rng = np.random.default_rng(seed)
    V, F, M = [], [], []
    lean = rng.normal(0, .05, 2)
    _cyl(V, F, M, (0, 0, 0), (lean[0] * .9, lean[1] * .9, .9), .012, .004, 7 if lod == 0 else 5, 1)
    for k in range(12 if lod == 0 else 6):
        z = rng.uniform(.45, .95); rr = .16 * (1 - (z - .45) / .6) + .04
        a = rng.uniform(0, 2 * PI)
        c = (lean[0] * z + math.cos(a) * rr * rng.uniform(.3, 1), lean[1] * z + math.sin(a) * rr * rng.uniform(.3, 1), z)
        _clump(V, F, M, c, rng.uniform(.05, .08), .75, rng, 0, 2 if lod == 0 else 1)
    return _finish(name, V, F, M, mats)


def bare_tree(name, seed, mats, lod=0):
    """Leafless deciduous tree (early spring city trees): trunk and forked branches."""
    rng = np.random.default_rng(seed)
    V, F, M = [], [], []

    def grow(p, d, L, r, depth):
        e = p + d * L
        _cyl(V, F, M, p, e, r, r * .7, 6 if lod == 0 else 4, 0)
        if depth == 0:
            return
        for _ in range(2 if depth > 1 else 3):
            nd = d + rng.normal(0, .55, 3); nd[2] = abs(nd[2]) + .3; nd /= np.linalg.norm(nd)
            grow(e, nd, L * rng.uniform(.6, .8), r * .65, depth - 1)
    grow(np.array([0., 0, 0]), np.array([0., 0, 1]), .35, .03, 4 if lod == 0 else 3)
    return _finish(name, V, F, M, mats)


def foliage_material(name, c0, c1, tint=(.6, .55, .25)):
    m, N, L, b = node_mat(name)
    oi = N.new('ShaderNodeObjectInfo'); pi_ = N.new('ShaderNodeParticleInfo')
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'; fr = N.new('ShaderNodeMath'); fr.operation = 'FRACT'
    L.new(oi.outputs['Random'], add.inputs[0]); L.new(pi_.outputs['Random'], add.inputs[1]); L.new(add.outputs[0], fr.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 25
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = .6
    L.new(fr.outputs[0], mx.inputs[0]); L.new(nz.outputs['Fac'], mx.inputs[2])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = (*c0, 1); r.elements[1].color = (*c1, 1)
    L.new(mx.outputs[0], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .7
    b.inputs['Sheen Weight'].default_value = .5; b.inputs['Sheen Tint'].default_value = (*tint, 1)
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .8
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 120; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    L.new(n2.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b)
    return m


def bark_material(name='PineBark', low=(.045, .035, .028), high=(.36, .14, .05)):
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = .35; r.elements[0].color = (*low, 1)
    r.elements[1].position = .6; r.elements[1].color = (*high, 1)
    L.new(sep.outputs['Z'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .85
    add_haze(m, N, L, b)
    return m


def birch_bark_material():
    m, N, L, b = node_mat('BirchBark')
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6, 6, 60)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.5; L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = .62; r.elements[0].color = (.55, .54, .5, 1)
    r.elements[1].position = .66; r.elements[1].color = (.03, .03, .03, 1)
    L.new(nz.outputs['Fac'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .6
    add_haze(m, N, L, b)
    return m


def tree_library(lo_coll_name='ForestLibrary'):
    """Hi-res tree meshes (for single trees) and a hidden collection of low-res ones (for particle forests)."""
    pn = foliage_material('PineNeedles', (.02, .04, .012), (.07, .095, .03))
    sn = foliage_material('SpruceNeedles', (.008, .02, .01), (.025, .045, .018), tint=(.3, .4, .2))
    bl = foliage_material('BirchLeaves', (.06, .13, .025), (.17, .26, .05), tint=(.8, .8, .3))
    pb, bb = bark_material(), birch_bark_material()
    hi = {'pine': [scots_pine(f'ScotsPine{k}', 10 + k, [pn, pb]) for k in range(4)],
          'spruce': [spruce(f'Spruce{k}', 20 + k, [sn, pb]) for k in range(3)],
          'birch': [birch(f'Birch{k}', 30 + k, [bl, bb]) for k in range(3)]}
    lib = new_coll(lo_coll_name)
    for me in [scots_pine('ScotsPineLo0', 50, [pn, pb], 1), scots_pine('ScotsPineLo1', 51, [pn, pb], 1),
               spruce('SpruceLo0', 60, [sn, pb], 1), spruce('SpruceLo1', 61, [sn, pb], 1), spruce('SpruceLo2', 62, [sn, pb], 1),
               birch('BirchLo0', 70, [bl, bb], 1)]:
        lib.objects.link(bpy.data.objects.new(me.name, me))
    bpy.context.view_layer.layer_collection.children[lib.name].exclude = True
    return hi, lib


def scatter_instances(emitter, lib, group, count, size, size_random=.4, seed=11):
    mod = emitter.modifiers.new('Scatter_' + group, 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = count; s.hair_length = 1
    s.render_type = 'COLLECTION'; s.instance_collection = lib; s.use_collection_pick_random = True
    s.particle_size = size; s.size_random = size_random
    s.use_rotations = True; s.rotation_mode = 'NONE'; s.use_rotation_instance = True
    s.display_percentage = 10; s.use_emit_random = True; s.distribution = 'RAND'
    mod.particle_system.vertex_group_density = group; mod.particle_system.seed = seed
    return mod


def place_tree(coll, me, loc, h, rng, name='Tree'):
    o = link(bpy.data.objects.new(name, me), coll)
    o.location = loc; o.scale = (h * rng.uniform(.85, 1.15), h * rng.uniform(.85, 1.15), h)
    o.rotation_euler = (rng.normal(0, .03), rng.normal(0, .03), rng.uniform(0, 2 * PI))
    return o


# ---------------------------------------------------------------- render settings and the command line
def setup_render(engine='eevee', percent=100, samples=None, gpu=False, frames=(1, 24)):
    sc = bpy.context.scene; r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, int(percent)
    r.fps = FPS; sc.frame_start, sc.frame_end = frames
    r.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    if engine == 'cycles':
        r.engine = 'CYCLES'; c = sc.cycles
        c.samples = int(samples or 160); c.use_adaptive_sampling = True; c.adaptive_threshold = .02
        c.use_denoising = True; c.max_bounces = 6; c.transparent_max_bounces = 16
        sc.cycles_curves.shape = 'THICK'
        if gpu:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for dev in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI', 'METAL'):
                try:
                    prefs.compute_device_type = dev; prefs.get_devices()
                    if any(d.type == dev for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = d.type == dev
                        c.device = 'GPU'; print('Cycles on', dev); break
                except Exception:
                    continue
    else:
        r.engine = 'BLENDER_EEVEE'; e = sc.eevee
        e.taa_render_samples = int(samples or 48)
        e.use_raytracing = True; e.ray_tracing_method = 'SCREEN'
        e.use_shadows = True; e.shadow_ray_count = 2; e.shadow_step_count = 8
        e.use_fast_gi = True
        r.hair_type = 'STRIP'; r.hair_subdiv = 1


def parse_args(sid):
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    here = os.path.dirname(os.path.abspath(sys.modules['film'].__file__))
    o = dict(frames=None, camera='edit', engine='eevee', percent=100, samples=None,
             out=os.path.join(here, 'renders', 'scene' + sid), gpu=False, save=True)
    i = 0
    while i < len(a):
        k = a[i].lstrip('-')
        if k in ('gpu',):
            o[k] = True; i += 1; continue
        if k == 'nosave':
            o['save'] = False; i += 1; continue
        o[k] = a[i + 1]; i += 2
    return o


def parse_frames(s, default):
    if not s:
        return [default]
    step = 1
    if 'x' in s:
        s, st = s.split('x'); step = int(st)
    if '-' in s:
        a, b = map(int, s.split('-')); return list(range(a, b + 1, step))
    return [int(v) for v in s.split(',')]


def run(build, sid, still_frame=None):
    """Build the scene, set up rendering, save the .blend and (in background mode) render the requested frames."""
    o = parse_args(sid)
    f0, f1 = scene_frames(sid)
    t = time.time()
    clear_scene()
    bpy.context.scene.name = f"S{sid}_{TIMELINE[sid]['name']}"
    build()
    setup_render(o['engine'], o['percent'], o['samples'], o['gpu'], (f0, f1))
    sc = bpy.context.scene
    if o['camera'] != 'edit':
        sc.timeline_markers.clear(); sc.camera = bpy.data.objects[o['camera']]
    sc.frame_set(still_frame or (f0 + f1) // 2)
    print(f"Scene {sid} built in {time.time() - t:.1f} s ({f1} frames)")
    here = os.path.dirname(os.path.abspath(sys.modules['film'].__file__))
    if o['save']:
        try:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(here, f'scene{sid}.blend'))
        except Exception as ex:
            print('Could not save the .blend:', ex)
    if bpy.app.background:
        frames = parse_frames(o['frames'], still_frame or (f0 + f1) // 2)
        os.makedirs(o['out'], exist_ok=True)
        for f in frames:
            path = os.path.join(o['out'], f"{f:04d}.png")
            if os.path.exists(path):
                print('skip', path); continue
            sc.frame_set(f); sc.render.filepath = path
            t = time.time(); bpy.ops.render.render(write_still=True)
            print(f'FRAME {f} rendered in {time.time() - t:.1f} s -> {path}')


def import_bears():
    here = os.path.dirname(os.path.abspath(sys.modules['film'].__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import bears
    importlib.reload(bears)
    return bears


# ---------------------------------------------------------------- the magnetic hearts (scenes 6, 7, 8, 16)
def heart_material(name='MagnetHeart', color=(.85, .05, .12), glow=0.0):
    """Glossy red enamel heart; its 'Glow' emission strength can be keyframed (the click, the sea floor)."""
    m, N, L, b = node_mat(name)
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = .18
    b.inputs['Coat Weight'].default_value = 1; b.inputs['Coat Roughness'].default_value = .05
    b.inputs['Emission Color'].default_value = (1, .25, .3, 1); b.inputs['Emission Strength'].default_value = glow
    return m


def heart_half(name, side, size, mat_, coll=None):
    """One half of a heart (side 'L' or 'R'); both halves share the same origin on the join line, so placing them at the
    same location and rotation makes a whole heart. The heart stands up in the XZ plane, facing -Y."""
    # classic heart half: a round lobe (circle) over the top, then a straight edge down to the point
    sgn = 1 if side == 'R' else -1
    r = .27; cx, cz = .25, .18                      # lobe circle (heart is ~1 wide, ~1 tall, origin at the centre line)
    pts = [(0.0, cz + .02)]
    a0 = math.atan2(.02, -cx)                       # start where the circle meets the centre line, near the notch
    for i in range(1, 25):
        a = a0 - (a0 + math.radians(48)) * i / 24  # sweep over the top and down the outer side
        pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    pts.append((0.0, -.5))                          # the point at the bottom
    pts = [(sgn * x * size, z * size) for x, z in pts]
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = .16 * size; cu.bevel_depth = .022 * size; cu.bevel_resolution = 3
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (x, z) in zip(sp.points, pts):
        p.co = (x, z, 0, 1)
    sp.use_cyclic_u = True
    tmp = bpy.data.objects.new(name + '_tmp', cu); bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    me.transform(Matrix.Rotation(PI / 2, 4, 'X'))          # stand it up: curve Y -> Z, facing -Y
    me.materials.clear(); me.materials.append(mat_); me.shade_smooth()
    return link(bpy.data.objects.new(name, me), coll)


def key_visible(ob, frame, on):
    """Show/hide an object from a frame on (scale 0 hides in every engine; constant keys)."""
    s = ob.get('_s', None)
    if s is None:
        ob['_s'] = tuple(ob.scale); s = ob['_s']
    import bears as _b
    if frame > 0 and not any(fc.data_path == 'scale' for fc in _b._fcurves(ob)):
        ob.scale = tuple(s) if not on else (1e-4, 1e-4, 1e-4)        # before the first change it is in the other state
        ob.keyframe_insert('scale', frame=0)
    ob.scale = tuple(s) if on else (1e-4, 1e-4, 1e-4)
    ob.keyframe_insert('scale', frame=frame)
    import bears
    for fc in bears._fcurves(ob):
        if fc.data_path == 'scale':
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'


def attach_to_paw(ob, arm, bone, offset=(0, .03, 0), rot=(0, 0, 0)):
    """Parent an object to a bear's paw (the tail of its forearm bone); offset is in the bone's space."""
    ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = bone
    ob.location = offset; ob.rotation_euler = rot
    return ob


# ---------------------------------------------------------------- their car (scenes 7, 10, 12, 13)
def car(name, loc, rot_z=0.0, coll=None, color=(.05, .07, .1), luggage=False, lights=False):
    """A small, friendly hatchback (about 2.9 long). Front points to -Y in its local space. Returns its root empty."""
    root = link(bpy.data.objects.new(name, None), coll); root.location = loc; root.rotation_euler = (0, 0, rot_z)
    paint = mat(name + '_paint', color, rough=.22, metal=.5, coat=1, haze=True)
    glass = mat(name + '_glass', (.02, .03, .035), rough=.04, metal=.5, haze=True)
    tire = mat(name + '_tire', (.01, .01, .01), rough=.7); rim = mat(name + '_rim', (.5, .5, .52), rough=.3, metal=1)
    parts = [box(name + '_body', (1.2, 2.9, .5), (0, 0, .2), paint, coll, bevel=.14),
             box(name + '_roof', (1.06, 1.45, .06), (0, .25, 1.06), paint, coll, bevel=.03)]
    for sx in (-1, 1):            # open window frames (pillars), so the bears inside can be seen
        for py, tilt in ((-.62, .5), (.35, 0), (.98, -.35)):
            parts.append(box(f'{name}_pillar{sx}{py}', (.06, .07, .42), (sx * .5, py, .66), paint, coll, rot=(tilt, 0, 0)))
    parts.append(box(name + '_windshield', (1.0, .03, .45), (0, -.72, .64), glass, coll, rot=(.55, 0, 0)))
    wheels = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            w = cylinder(f'{name}_wheel{sx}{sy}', .22, .16, (sx * .6, sy * .95, .22), tire, coll, n=20)
            w.rotation_euler = (0, PI / 2, 0); w.location.x -= .08 * sx; parts.append(w); wheels.append(w)
            h = cylinder(f'{name}_hub{sx}{sy}', .12, .17, (sx * .6, sy * .95, .22), rim, coll, n=12)
            h.rotation_euler = (0, PI / 2, 0); h.location.x -= .085 * sx; parts.append(h)
    head = emit_mat(name + '_head', (1, .95, .85), 6 if lights else .3); tail = emit_mat(name + '_tail', (1, .06, .04), 5 if lights else .8)
    for sx in (-1, 1):
        parts.append(box(f'{name}_headlight{sx}', (.22, .04, .08), (sx * .4, -1.44, .48), head, coll))
        parts.append(box(f'{name}_taillight{sx}', (.2, .04, .07), (sx * .42, 1.44, .52), tail, coll))
    if luggage:
        rack = mat(name + '_rack', (.05, .05, .05), rough=.4, metal=.6)
        parts.append(box(name + '_rack', (.95, 1.2, .03), (0, .25, 1.1), rack, coll))
        cols = [(.35, .18, .1), (.2, .3, .45), (.55, .45, .3), (.4, .1, .12)]
        for i, (sz, p) in enumerate((((.5, .7, .25), (-.2, .1)), ((.38, .5, .3), (.25, .35)), ((.42, .4, .18), (-.15, .62)), ((.3, .3, .16), (.25, -.2)))):
            parts.append(box(f'{name}_bag{i}', sz, (p[0], p[1], 1.13), mat(f'{name}_bagm{i}', cols[i], rough=.8), coll, bevel=.04))
    for p in parts:
        p.parent = root
    root['wheels'] = [w.name for w in wheels]
    return root


def drive(car_root, f0, f1, p0, p1):
    """Move the car in a straight line between two frames, wheels turning."""
    car_root.location = p0; car_root.keyframe_insert('location', frame=f0)
    car_root.location = p1; car_root.keyframe_insert('location', frame=f1)
    import bears
    for fc in bears._fcurves(car_root):
        for kp in fc.keyframe_points:
            if f0 - .5 <= kp.co.x <= f1 + .5:
                kp.interpolation = 'LINEAR'
    turns = (Vector(p1) - Vector(p0)).length / (2 * PI * .22)
    for n in car_root.get('wheels', []):
        w = bpy.data.objects[n]
        w.keyframe_insert('rotation_euler', frame=f0)
        w.rotation_euler.x -= turns * 2 * PI; w.keyframe_insert('rotation_euler', frame=f1)
        for fc in bears._fcurves(w):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
