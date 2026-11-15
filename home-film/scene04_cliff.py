"""
Home - scene 4, test shot: the first date. Two bears sit on the edge of a cliff among pines,
legs dangling, above a still lake at sunset. His paw creeps to hers; she leans on his shoulder.

HOW TO RUN (Blender 5.3)
  A) In Blender: Scripting tab -> Open -> scene04_cliff.py -> Run Script (Alt+P).
     The scene is built (takes ~30 s) and saved as scene04_cliff.blend next to this file.
     Press F12 to render the current frame (frame 170 is set: she is leaning on him).
     Switch camera: in the Outliner, right-click Cam_Faces -> "Set Active Camera" (or Ctrl+Numpad 0).
  B) From a terminal (Windows: cmd in this folder), builds + renders, prints the time per frame:
     "C:\\Program Files\\Blender Foundation\\Blender 5.3\\blender.exe" -b --python scene04_cliff.py -- --frames 170 --percent 50
     Options after "--":
       --frames 170 | 1-216 | 1-216x8  (every 8th)     --camera wide | faces | establish
       --engine eevee | cycles                          --percent 50 (of 1080x1920)
       --samples N                                      --out renders/scene04/   (existing frames are skipped)
       --gpu    (Cycles on GPU: OptiX/CUDA, for Colab)
"""
import os, sys, math, time, importlib
import bpy
import numpy as np
from mathutils import Vector, Matrix

PI = math.pi


# ---------------------------------------------------------------- find bears.py next to this file
def _here():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    for t in bpy.data.texts:   # run from Blender's text editor
        if t.filepath and t.filepath.endswith('scene04_cliff.py'):
            return os.path.dirname(bpy.path.abspath(t.filepath))
    raise RuntimeError('Save/open scene04_cliff.py from disk so bears.py can be found next to it.')


HERE = _here()
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bears
importlib.reload(bears)

FPS = 24
FRAMES = (1, 216)          # 9 seconds
SUN_ELEV = 3.8             # degrees above the horizon
SUN_AZ = -36.0             # degrees: 0 = straight ahead of the bears (over the lake), + = to their left
LAKE_Z = -28.0             # the lake surface: granite cliffs ~45 m high (1 unit ~ 1.6 m, a bear is about a person tall)
EDGE_Y = -0.12             # the cliff lip in front of the bears


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = dict(frames=None, camera='wide', engine='eevee', percent=100, samples=None, out=os.path.join(HERE, 'renders', 'scene04'), gpu=False)
    i = 0
    while i < len(a):
        k = a[i].lstrip('-')
        if k == 'gpu':
            o['gpu'] = True; i += 1; continue
        o[k] = a[i + 1]; i += 2
    return o


# ---------------------------------------------------------------- utilities
def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.armatures, bpy.data.cameras,
                 bpy.data.lights, bpy.data.particles, bpy.data.worlds, bpy.data.actions, bpy.data.node_groups):
        for d in list(coll):
            coll.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def new_coll(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c


def grid_mesh(name, X, Y, Z, coll, mat=None):
    """Mesh from 2D arrays of vertex positions (a deformed grid)."""
    ny, nx = X.shape
    V = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    i = np.arange(nx - 1); j = np.arange(ny - 1)
    I, J = np.meshgrid(i, j)
    a = (J * nx + I).ravel()
    F = np.stack([a, a + 1, a + 1 + nx, a + nx], 1).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
    me.loops.add(len(F) * 4); me.polygons.add(len(F))
    me.loops.foreach_set('vertex_index', F.ravel()); me.polygons.foreach_set('loop_start', np.arange(len(F), dtype=np.int32) * 4)
    me.update(calc_edges=True); me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    return ob


def vgroup(ob, name, w):
    g = ob.vertex_groups.new(name=name)
    idx = np.nonzero(w > 1e-3)[0]
    for v, x in zip(idx.tolist(), w[idx].tolist()):
        g.add([v], float(x), 'REPLACE')
    return g


# smooth value noise (numpy), for terrain
_rng = np.random.default_rng(7)
_PERM = _rng.random((256, 256))


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


# ---------------------------------------------------------------- materials
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']


def add_haze(m, N, L, bsdf, color=(.95, .55, .45), dist=160.0, strength=.7):
    """Aerial perspective: far things fade into the warm evening haze (works in EEVEE and Cycles)."""
    out = N['Material Output']
    cd = N.new('ShaderNodeCameraData')
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 8; mr.inputs['From Max'].default_value = dist
    mr.inputs['To Max'].default_value = strength; mr.interpolation_type = 'SMOOTHERSTEP'
    L.new(cd.outputs['View Distance'], mr.inputs['Value'])
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = 1
    mix = N.new('ShaderNodeMixShader')
    L.new(mr.outputs['Result'], mix.inputs['Fac']); L.new(bsdf.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])


def rock_material():
    """Granite: pale grey-pink with dark mica speckles and feldspar flecks, dark joint cracks, black streaks
    where water runs down, lichen and moss on the glacier-smoothed top."""
    m, N, L, b = node_mat('Granite')
    tc = N.new('ShaderNodeTexCoord'); P = tc.outputs['Object']
    def noise(scale, detail=6, rough=.6):
        n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough; L.new(P, n.inputs['Vector']); return n
    def ramp(fac, stops):
        r = N.new('ShaderNodeValToRGB'); cr = r.color_ramp
        cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
        cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
        for pos, c in stops[1:-1]:
            e = cr.elements.new(pos); e.color = (*c, 1)
        L.new(fac, r.inputs['Fac']); return r
    def mix(fac, a, b_, blend='MIX'):
        x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'; x.blend_type = blend
        if isinstance(fac, float): x.inputs['Factor'].default_value = fac
        else: L.new(fac, x.inputs['Factor'])
        L.new(a, x.inputs['A']); L.new(b_, x.inputs['B']); return x.outputs['Result']
    # base tone: large soft variation, grey to warm pink-grey
    base = ramp(noise(.6, 4).outputs['Fac'], [(.35, (.20, .19, .185)), (.55, (.28, .24, .22)), (.7, (.33, .29, .27))])
    # crystals: dark mica speckles and pinkish feldspar flecks
    vor = N.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 90; L.new(P, vor.inputs['Vector'])
    spk = ramp(vor.outputs['Distance'], [(.0, (.03, .03, .03)), (.18, (.03, .03, .03)), (.24, (1, 1, 1))])
    col = mix(.75, base.outputs['Color'], mix(1.0, base.outputs['Color'], spk.outputs['Color'], 'MULTIPLY'))
    fel = ramp(noise(55, 2).outputs['Fac'], [(.6, (1, 1, 1)), (.7, (1.25, .95, .85))])
    col = mix(1.0, col, fel.outputs['Color'], 'MULTIPLY')
    # dark vertical water streaks on the wall
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, .08); L.new(P, mp.inputs['Vector'])
    st = N.new('ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 1.6; L.new(mp.outputs['Vector'], st.inputs['Vector'])
    stc = ramp(st.outputs['Fac'], [(.5, (1, 1, 1)), (.68, (.45, .42, .4))])
    col = mix(1.0, col, stc.outputs['Color'], 'MULTIPLY')
    # joint cracks
    cr = N.new('ShaderNodeTexVoronoi'); cr.feature = 'DISTANCE_TO_EDGE'; cr.inputs['Scale'].default_value = .9; L.new(P, cr.inputs['Vector'])
    crc = ramp(cr.outputs['Distance'], [(.0, (.08, .08, .08)), (.025, (1, 1, 1))])
    col = mix(1.0, col, crc.outputs['Color'], 'MULTIPLY')
    # lichen (pale grey-green blotches) everywhere, moss on the flat top
    lic = ramp(noise(6, 5).outputs['Fac'], [(.58, (0, 0, 0)), (.64, (1, 1, 1))])
    col = mix(lic.outputs['Color'], col,
              ramp(noise(30, 3).outputs['Fac'], [(.3, (.32, .34, .27)), (.7, (.42, .43, .35))]).outputs['Color'])
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
    flat = N.new('ShaderNodeMapRange'); flat.inputs['From Min'].default_value = .8; flat.inputs['From Max'].default_value = .95
    L.new(sep.outputs['Z'], flat.inputs['Value'])
    patch = N.new('ShaderNodeMath'); patch.operation = 'MULTIPLY'; patch.use_clamp = True
    pn = ramp(noise(1.4, 5).outputs['Fac'], [(.45, (0, 0, 0)), (.55, (1, 1, 1))])
    L.new(flat.outputs['Result'], patch.inputs[0]); L.new(pn.outputs['Color'], patch.inputs[1])
    moss = ramp(noise(14, 6).outputs['Fac'], [(.3, (.035, .045, .012)), (.7, (.14, .13, .04))])
    col = mix(patch.outputs[0], col, moss.outputs['Color'])
    L.new(col, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .78
    # relief: cracks + grain
    h = N.new('ShaderNodeMath'); h.operation = 'ADD'
    L.new(crc.outputs['Color'], h.inputs[0]); L.new(noise(18, 10).outputs['Fac'], h.inputs[1])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .5; bump.inputs['Distance'].default_value = .08
    L.new(h.outputs[0], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b)
    return m


def water_material():
    m, N, L, b = node_mat('Lake')
    b.inputs['Base Color'].default_value = (.005, .012, .02, 1)
    b.inputs['Roughness'].default_value = .035
    b.inputs['IOR'].default_value = 1.33
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 3, 1)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = .35; n.inputs['Detail'].default_value = 3
    L.new(mp.outputs['Vector'], n.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .08
    L.new(n.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def land_material():
    m, N, L, b = node_mat('FarLand')
    b.inputs['Base Color'].default_value = (.02, .025, .012, 1); b.inputs['Roughness'].default_value = 1
    add_haze(m, N, L, b, dist=260, strength=.78)
    return m


def pine_material():
    m, N, L, b = node_mat('Pine')
    oi = N.new('ShaderNodeObjectInfo')
    pi_ = N.new('ShaderNodeParticleInfo')
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = (.008, .022, .012, 1); r.elements[1].color = (.03, .05, .02, 1)
    add = N.new('ShaderNodeMath'); add.operation = 'FRACT'
    s = N.new('ShaderNodeMath'); s.operation = 'ADD'
    L.new(oi.outputs['Random'], s.inputs[0]); L.new(pi_.outputs['Random'], s.inputs[1]); L.new(s.outputs[0], add.inputs[0])
    L.new(add.outputs[0], ramp.inputs['Fac'])
    # needles a touch lighter where they face the sky
    L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .75
    b.inputs['Sheen Weight'].default_value = .4; b.inputs['Sheen Tint'].default_value = (.5, .45, .2, 1)
    tc = N.new('ShaderNodeTexCoord'); n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 40; n.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], n.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .7
    L.new(n.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b, dist=200, strength=.9)
    return m


def bark_material():
    m, N, L, b = node_mat('Bark')
    b.inputs['Base Color'].default_value = (.05, .03, .02, 1); b.inputs['Roughness'].default_value = .9
    add_haze(m, N, L, b, dist=200, strength=.9)
    return m


# ---------------------------------------------------------------- world: evening sky
def make_world():
    w = bpy.data.worlds.new('Sunset'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    bg = N['Background']
    sky = N.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(SUN_ELEV)
    sky.sun_rotation = math.radians(SUN_ROT_SKY)
    sky.air_density = 2.2; sky.aerosol_density = 5.0; sky.ozone_density = 3.0
    sky.sun_size = math.radians(2.2); sky.sun_intensity = .35
    sky.altitude = 200
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -.02; mr.inputs['From Max'].default_value = .45
    L.new(sep.outputs['Z'], mr.inputs['Value'])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = (1.0, .42, .22, 1); r.elements[1].position = 1; r.elements[1].color = (.75, .78, 1.0, 1)
    e = r.elements.new(.25); e.color = (1.0, .62, .55, 1)
    L.new(mr.outputs['Result'], ramp.inputs['Fac'])
    tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1
    L.new(sky.outputs['Color'], tint.inputs['A']); L.new(ramp.outputs['Color'], tint.inputs['B'])
    L.new(tint.outputs['Result'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = .9
    return w


# the sky node puts its sun at direction (sin r, cos r); ours sits over the lake at (sin az, -cos az)
SUN_ROT_SKY = 180 - SUN_AZ


def make_sun():
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = 3.2; ld.color = (1.0, .62, .38); ld.angle = math.radians(1.5)
    sun = bpy.data.objects.new('Sun', ld); bpy.context.scene.collection.objects.link(sun)
    # the light travels from the sun (over the lake, -Y) towards the bears
    sun.rotation_euler = (math.radians(90 - SUN_ELEV), 0, math.radians(SUN_AZ))
    # soft warm fill from behind the camera (the glowing sky behind us)
    fd = bpy.data.lights.new('SkyFill', 'AREA'); fd.energy = 18; fd.size = 4; fd.color = (1, .7, .75)
    fill = bpy.data.objects.new('SkyFill', fd); bpy.context.scene.collection.objects.link(fill)
    fill.location = (0.8, -3.2, 1.6)
    fill.rotation_euler = (Vector((0, 0, .5)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
    # a soft warm bounce from behind the camera of the wide shot, so their backs are not pitch black
    bd = bpy.data.lights.new('BackBounce', 'AREA'); bd.energy = 30; bd.size = 3; bd.color = (1, .62, .5)
    bnc = bpy.data.objects.new('BackBounce', bd); bpy.context.scene.collection.objects.link(bnc)
    bnc.location = (1.6, 3.4, 2.2)
    bnc.rotation_euler = (Vector((0, 0, .45)) - bnc.location).to_track_quat('-Z', 'Y').to_euler()
    return sun


# ---------------------------------------------------------------- the cliff
def edge_y(x):
    """The lip of the cliff curves away behind the bears, so the cliff face shows to the sides."""
    return EDGE_Y + .035 * x * x + .05 * fbm(x * .7, 3.1, 3)


def cliff_height(x, u):
    """u = distance behind the lip (>0 on the top, <0 out over the drop)."""
    near = np.exp(-(x * x) / 1.2 - np.maximum(u - .4, 0) ** 2 / 1.0)        # flat seat where the bears are
    top = .02 * np.maximum(u, 0) + .9 * np.clip(u - 3, 0, None) ** 1.2 * .15 + (1 - near) * .25 * fbm(x * .8, u * .8 + 11)
    top = top + np.clip(np.abs(x) - 5, 0, None) * .08
    lip = .06 * (np.tanh(u / .05) - 1)                                       # rounded lip
    drop = np.where(u < 0, -np.minimum(-u * 9 + (-u) ** 2 * 10, -LAKE_Z + 2.5), 0)     # rounded brow, then near vertical
    face = np.where(u < 0, 1.2 * fbm(x * .9, drop * .12, 6) * np.clip(-u * 6, 0, 1), 0)
    return np.where(u >= 0, top, 0) + lip + drop + face


def face_offset(x, z, u):
    """Sideways relief of the granite wall: stepped ledges, vertical joints and slabs (it may lean in and out)."""
    k = np.clip(-u * 5, 0, 1)
    ledges = .9 * np.sin(np.clip(z, LAKE_Z, 0) * .35 + 2 * fbm(x * .3, 0.0, 2)) ** 7      # horizontal sheeting joints
    joints = 1.1 * np.abs(fbm(x * .45 + 7, z * .05, 3)) ** .5 * np.sign(fbm(x * .45 + 7, z * .05, 3))  # vertical blocks
    slabs = 1.6 * fbm(x * .18 + 2, z * .09 + 5, 4)
    return k * (ledges + joints + slabs + .4 * fbm(x * 2.2, z * 1.3, 5))


def make_cliff(coll, mat):
    s = np.linspace(-1, 1, 361); X1 = 14 * np.sinh(2.6 * s) / np.sinh(2.6)
    t = np.linspace(0, 1, 260); U1 = -0.6 + (28.6) * (np.sinh(3.4 * t - 0.2) - np.sinh(-0.2)) / (np.sinh(3.2) - np.sinh(-0.2))
    U1 = np.concatenate([-0.002 - 1.7 * np.linspace(1, 0, 150) ** 1.6, U1[U1 > -0.002]])
    Xg, Ug = np.meshgrid(X1, U1)
    Yg = edge_y(Xg) + Ug
    Zg = cliff_height(Xg, Ug)
    # the face also leans out a little, and is rough sideways (not only up and down)
    Yg = Yg - face_offset(Xg, Zg, Ug)
    ob = grid_mesh('Cliff', Xg, Yg, Zg, coll, mat)
    # grass and needles only on the flat top near the bears
    w = np.clip(Ug / .25, 0, 1) * np.exp(-(Xg ** 2) / 10 - np.maximum(Ug - 1, 0) ** 2 / 8)
    w = w * np.clip((fbm(Xg * 1.3 + 9, Ug * 1.3, 4) + .05) * 6, 0, 1)        # moss and grass in patches on bare granite
    vgroup(ob, 'grass', w.ravel())
    return ob


def ground_z(x, y):
    """Height of the cliff top at world (x, y) (for placing trees and bears)."""
    u = y - edge_y(np.array(x))
    return float(cliff_height(np.array(x), np.array(u)))


def make_grass(cliff):
    m, N, L, b = node_mat('Grass')
    hi = N.new('ShaderNodeHairInfo'); ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = (.02, .025, .008, 1); r.elements[1].color = (.28, .22, .07, 1)
    L.new(hi.outputs['Intercept'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .7
    cliff.data.materials.append(m)
    mod = cliff.modifiers.new('Grass', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 18000; s.use_advanced_hair = True
    s.normal_factor = .035; s.factor_random = .03; s.object_align_factor = (0, 0, .01)
    s.material_slot = 'Grass'; s.render_step = 3; s.display_step = 2
    s.child_type = 'INTERPOLATED'; s.child_percent = 2; s.rendered_child_count = 6; s.child_radius = .05
    s.roughness_2 = .02; s.roughness_endpoint = .02; s.clump_factor = .4
    s.radius_scale = .004; s.root_radius = 1; s.tip_radius = 0; s.use_close_tip = True
    s.length_random = .6; s.display_percentage = 20
    mod.particle_system.vertex_group_density = 'grass'
    mod.particle_system.vertex_group_length = 'grass'


# ---------------------------------------------------------------- pines
def pine_mesh(name, seed, tiers=11, height=1.0, mats=None):
    """A spruce/pine: trunk + stacked star-shaped drooping branch tiers (jagged silhouette against the sky)."""
    rng = np.random.default_rng(seed)
    V, Fc, Mi = [], [], []

    def add(verts, faces, mi):
        o = len(V); V.extend(verts); Fc.extend([tuple(i + o for i in f) for f in faces]); Mi.extend([mi] * len(faces))

    # trunk
    n = 8; r0, r1 = .022 * height, .006 * height
    vs = [(math.cos(2 * PI * i / n) * r0, math.sin(2 * PI * i / n) * r0, 0) for i in range(n)] + \
         [(math.cos(2 * PI * i / n) * r1, math.sin(2 * PI * i / n) * r1, height * .95) for i in range(n)]
    add(vs, [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)], 1)
    for k in range(tiers):
        f = k / (tiers - 1)
        zb = height * (.12 + .82 * f) + rng.normal(0, .008)
        R = height * (.27 * (1 - f) ** .95 + .03) * rng.uniform(.85, 1.15)
        hgt = height * (.09 + .04 * (1 - f))
        spikes = int(rng.integers(13, 19))
        ring = []
        rot = rng.uniform(0, 2 * PI)
        for i in range(spikes * 2):
            a = rot + PI * i / spikes + rng.normal(0, .08)
            rr = R * (1 if i % 2 == 0 else .42) * rng.uniform(.7, 1.25)
            droop = -.25 * rr if i % 2 == 0 else -.05 * rr
            ring.append((math.cos(a) * rr, math.sin(a) * rr, zb + droop))
        apex = (rng.normal(0, .01 * height), rng.normal(0, .01 * height), zb + hgt)
        inner = [(x * .35, y * .35, z + hgt * .25) for x, y, z in ring]
        m = len(ring)
        verts = ring + inner + [apex]
        faces = [(i, (i + 1) % m, (i + 1) % m + m, i + m) for i in range(m)] + [(i + m, (i + 1) % m + m, 2 * m) for i in range(m)]
        # underside so we never look into a hollow cone
        under = (0, 0, zb - .02 * height)
        verts.append(under)
        faces += [((i + 1) % m, i, 2 * m + 1) for i in range(m)]
        add(verts, faces, 0)
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], Fc); me.update()
    me.polygons.foreach_set('material_index', Mi)
    for mt in mats:
        me.materials.append(mt)
    return me


def make_pines(coll, pine_m, bark_m):
    lib = new_coll('PineLibrary')
    meshes = [pine_mesh(f'Pine{k}', 100 + k, tiers=17 + k % 4, mats=[pine_m, bark_m]) for k in range(4)]
    protos = []
    for k, me in enumerate(meshes):
        o = bpy.data.objects.new(f'PineProto{k}', me); lib.objects.link(o); o.location = (0, 0, -100); protos.append(o)
    bpy.context.view_layer.layer_collection.children[lib.name].exclude = True
    # pines on the cliff top: behind and beside the bears (they frame the sky)
    spots = [(-3.2, 5.0, 8.0), (2.4, 5.6, 8.5), (-5.6, 3.4, 8.0), (4.6, 1.2, 6.5), (-1.6, 6.4, 9.0), (-.9, 12.0, 8.0),
             (4.6, 6.8, 9.5), (-5.2, 7.6, 9.0), (2.6, 9.8, 10), (-4.6, 1.2, 5.5), (5.9, 3.2, 7.0), (-7.0, 4.6, 7.5),
             (6.9, 8.0, 9), (-2.4, 10.0, 10), (1.2, 12.5, 11), (-7.8, 9.4, 10), (8.4, 10.5, 10), (.4, 7.4, 9.5)]
    # keep every camera's view of the bears clear
    sight = [((2.75, 3.75), (0, .06)), ((2.2, 3.0), (0, .06)), ((.1, -2.7), (0, .06))]

    def blocks(x, y, h):
        for (ax, ay), (bx, by) in sight:
            dx, dy = bx - ax, by - ay; t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            if math.hypot(x - ax - dx * t, y - ay - dy * t) < .3 * h + .6:
                return True
        return False
    spots = [sp for sp in spots if not blocks(*sp)]
    rng = np.random.default_rng(3)
    for i, (x, y, h) in enumerate(spots):
        o = bpy.data.objects.new(f'Pine_{i}', meshes[i % 4]); coll.objects.link(o)
        h *= 1.5
        o.location = (x, y, ground_z(x, y) - .05); o.scale = (h * rng.uniform(.9, 1.1), h * rng.uniform(.9, 1.1), h)
        o.rotation_euler = (rng.normal(0, .03), rng.normal(0, .03), rng.uniform(0, 2 * PI))
    return lib


def make_far_land(coll, land_m, lib):
    """Distant shores: forested hills around the lake, fading into the warm haze."""
    xs = np.linspace(-320, 320, 260); ys = np.linspace(-420, 30, 220)
    Xg, Yg = np.meshgrid(xs, ys)
    far = np.clip((-Yg - 110) / 40, 0, 1)                    # the far shore
    side = np.clip((np.abs(Xg + 15 * np.sin(Yg / 60)) - 38 + Yg * .08) / 30, 0, 1)   # side shores, nearer
    hills = 10 * fbm(Xg / 70, Yg / 70, 5) + 6 * fbm(Xg / 25 + 3, Yg / 25, 4)
    H = far * (9 + 1.6 * hills + 12 * np.clip((-Yg - 260) / 140, 0, 1)) - 2.5
    H = np.maximum(H, side * (3.2 + .5 * hills) - 2.5)
    H = np.where((np.abs(Xg) < 16) & (Yg > -12), -8, H)      # keep the water clear below the cliff
    Z = LAKE_Z + H
    ob = grid_mesh('FarShores', Xg, Yg, Z, coll, land_m)
    wood = np.clip((H - .6) / 1.5, 0, 1).ravel()
    vgroup(ob, 'forest', wood)
    mod = ob.modifiers.new('Forest', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 26000; s.hair_length = 1
    s.render_type = 'COLLECTION'; s.instance_collection = lib; s.use_collection_pick_random = True
    s.particle_size = 11; s.size_random = .45
    s.use_rotations = True; s.rotation_mode = 'NONE'; s.use_rotation_instance = True
    s.display_percentage = 15; s.use_emit_random = True; s.distribution = 'RAND'
    mod.particle_system.vertex_group_density = 'forest'
    mod.particle_system.seed = 11
    return ob


def make_lake(coll, mat):
    me = bpy.data.meshes.new('Lake')
    S = 900
    me.from_pydata([(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(mat)
    ob = bpy.data.objects.new('Lake', me); coll.objects.link(ob); ob.location = (0, 0, LAKE_Z)
    return ob


# ---------------------------------------------------------------- the bears and their little story
def place_bears():
    he = bears.build_bear('he', location=(.27, .06, 0))
    she = bears.build_bear('she', location=(-.27, .06, 0))
    for b in (he, she):
        bears.sit(b, ground_z(b.location.x, b.location.y))
    return he, she


def animate(he, she):
    f0, f1 = FRAMES
    sit_legs = {'thigh.L': (88, 0, -4), 'thigh.R': (88, 0, 4), 'shin.L': (-80, 0, 0), 'shin.R': (-80, 0, 0)}
    # arms rest beside them on the rock
    he_rest = dict(sit_legs, **{'spine': (6, 0, 0), 'head': (-4, 0, 0), 'shoulder.L': (12, 0, -10), 'shoulder.R': (12, 0, 10),
                                'forearm.L': (10, 0, 0), 'forearm.R': (10, 0, 0)})
    she_rest = dict(sit_legs, **{'spine': (6, 0, 0), 'head': (-6, 0, 0), 'shoulder.L': (12, 0, -10), 'shoulder.R': (12, 0, 10),
                                 'forearm.L': (10, 0, 0), 'forearm.R': (10, 0, 0)})
    for f in (f0, 40):
        bears.key_pose(he, f, he_rest); bears.key_pose(she, f, she_rest)
    # his near paw (his right) creeps toward hers... a little hesitation... and lands on it
    bears.key_pose(he, 78, {'shoulder.R': (14, 0, 24), 'head': (-4, -6, 0)})
    bears.key_pose(he, 92, {'shoulder.R': (14, 0, 25), 'head': (-4, -10, 0)})
    bears.key_pose(he, 116, {'shoulder.R': (16, 0, 36), 'forearm.R': (14, 0, 0), 'head': (-4, -4, 0)})
    # she leans in and rests her head on his shoulder
    bears.key_pose(she, 112, {'spine': (6, 0, 0), 'head': (-6, 0, 0)})
    bears.key_pose(she, 160, {'spine': (8, 6, -14), 'head': (4, -14, -20), 'shoulder.L': (14, 0, -28)})
    she.keyframe_insert('location', frame=112)
    she.location.x += .07
    she.keyframe_insert('location', frame=160)
    she.location.x -= .07
    # he tilts his head toward hers
    bears.key_pose(he, 140, {'head': (-4, -4, 0), 'spine': (6, 0, 0)})
    bears.key_pose(he, 176, {'head': (2, 8, 10), 'spine': (6, -3, 6)})
    bears.key_pose(he, f1, {'head': (2, 8, 10), 'spine': (6, -3, 6), 'shoulder.R': (16, 0, 36), 'forearm.R': (14, 0, 0)})
    bears.key_pose(she, f1, {'spine': (8, 6, -14), 'head': (4, -14, -20), 'shoulder.L': (14, 0, -28)})
    # eyes: a blink each, then she closes her eyes, content
    bears.set_eyes(he, 'open', f0); bears.set_eyes(she, 'open', f0)
    bears.blink(he, 30); bears.blink(she, 58); bears.blink(he, 128)
    bears.set_eyes(she, 'closed', 164)
    # soft breathing on both (a gentle rise of the spine)
    for b, ph in ((he, 0), (she, 1.3)):
        pb = b.pose.bones['pelvis']
        for f in range(f0, f1 + 1, 24):
            pb.scale = (1, 1 + .012 * math.sin(ph + f / 24 * 2 * PI / 3.6), 1); pb.keyframe_insert('scale', frame=f)
    # ease everything gently
    for ob in (he, she):
        for fc in bears._fcurves(ob):
            if fc.data_path != '["eyes"]':
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'


# ---------------------------------------------------------------- cameras
def look(cam, target):
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()


def make_cameras():
    sc = bpy.context.scene
    # wide: behind them and a little to the side, the lake and the sun beyond; a slow push-in
    cd = bpy.data.cameras.new('Cam_Wide'); cd.lens = 32; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 5.6
    cam = bpy.data.objects.new('Cam_Wide', cd); sc.collection.objects.link(cam)
    tgt = Vector((-3.9, -5.4, -.2))
    for f, p in ((FRAMES[0], (2.75, 3.75, 1.35)), (FRAMES[1], (2.2, 3.0, 1.18))):
        cam.location = p; look(cam, tgt)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
    focus = bpy.data.objects.new('Focus_Bears', None); sc.collection.objects.link(focus); focus.location = (0, 0, .45)
    cd.dof.focus_object = focus
    # faces: out over the drop, looking back at them, sunset light on their fur
    cf = bpy.data.cameras.new('Cam_Faces'); cf.lens = 35; cf.sensor_fit = 'VERTICAL'; cf.sensor_height = 24
    cf.dof.use_dof = True; cf.dof.aperture_fstop = 2.0; cf.dof.focus_object = focus
    cam2 = bpy.data.objects.new('Cam_Faces', cf); sc.collection.objects.link(cam2)
    for f, p in ((FRAMES[0], (.12, -2.75, .62)), (FRAMES[1], (.07, -2.5, .56))):
        cam2.location = p; look(cam2, (.04, 0, .4))
        cam2.keyframe_insert('location', frame=f); cam2.keyframe_insert('rotation_euler', frame=f)
    # establishing: from out over the lake, the whole granite wall with two tiny bears on top (slow rise)
    ce = bpy.data.cameras.new('Cam_Establish'); ce.lens = 30; ce.sensor_fit = 'VERTICAL'; ce.sensor_height = 24
    cam3 = bpy.data.objects.new('Cam_Establish', ce); sc.collection.objects.link(cam3)
    for f, p in ((FRAMES[0], (-7.5, -38, -17)), (FRAMES[1], (-6.5, -36, -13))):
        cam3.location = p; look(cam3, (0, 0, -9))
        cam3.keyframe_insert('location', frame=f); cam3.keyframe_insert('rotation_euler', frame=f)
    sc.camera = cam
    return cam, cam2


# ---------------------------------------------------------------- render settings
def setup_render(engine='eevee', percent=100, samples=None, gpu=False):
    sc = bpy.context.scene; r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, int(percent)
    r.fps = FPS; sc.frame_start, sc.frame_end = FRAMES
    r.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    if engine == 'cycles':
        r.engine = 'CYCLES'; c = sc.cycles
        c.samples = int(samples or 160); c.use_adaptive_sampling = True; c.adaptive_threshold = .02
        c.use_denoising = True
        c.max_bounces = 6; c.transparent_max_bounces = 16
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
            try:
                c.denoiser = 'OPTIX' if prefs.compute_device_type == 'OPTIX' else 'OPENIMAGEDENOISE'
            except Exception:
                pass
    else:
        r.engine = 'BLENDER_EEVEE'; e = sc.eevee
        e.taa_render_samples = int(samples or 48)
        e.use_raytracing = True; e.ray_tracing_method = 'SCREEN'
        e.use_shadows = True; e.shadow_ray_count = 2; e.shadow_step_count = 8
        e.use_fast_gi = True
        r.hair_type = 'STRIP'; r.hair_subdiv = 1


# ---------------------------------------------------------------- build
def build():
    t = time.time()
    clear_scene()
    sc = bpy.context.scene; sc.name = 'S04_FirstDate'
    make_world(); make_sun()
    env = new_coll('Set')
    cliff = make_cliff(env, rock_material()); make_grass(cliff)
    lib = make_pines(env, pine_material(), bark_material())
    make_far_land(env, land_material(), lib)
    make_lake(env, water_material())
    he, she = place_bears()
    animate(he, she)
    make_cameras()
    sc.frame_set(170)
    print(f'Scene 4 built in {time.time() - t:.1f} s')
    return he, she


def parse_frames(s, default):
    if not s:
        return [default]
    step = 1
    if 'x' in s:
        s, st = s.split('x'); step = int(st)
    if '-' in s:
        a, b = map(int, s.split('-')); return list(range(a, b + 1, step))
    return [int(v) for v in s.split(',')]


if __name__ == '__main__':
    o = args()
    build()
    setup_render(o['engine'], o['percent'], o['samples'], o['gpu'])
    sc = bpy.context.scene
    sc.camera = bpy.data.objects['Cam_' + o['camera'].capitalize()]
    try:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'scene04_cliff.blend'))
    except Exception as ex:
        print('Could not save the .blend:', ex)
    if bpy.app.background:
        frames = parse_frames(o['frames'], 170)
        os.makedirs(o['out'], exist_ok=True)
        for f in frames:
            path = os.path.join(o['out'], f"{o['camera']}_{f:04d}.png")
            if os.path.exists(path):
                print('skip', path); continue
            sc.frame_set(f); sc.render.filepath = path
            t = time.time(); bpy.ops.render.render(write_still=True)
            print(f'FRAME {f} rendered in {time.time() - t:.1f} s -> {path}')
