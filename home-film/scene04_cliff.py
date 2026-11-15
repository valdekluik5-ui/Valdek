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
       --frames 170 | 1-216 | 1-216x8  (every 8th)     --camera wide | faces | establish | edit (cuts between all three)
       --engine eevee | cycles                          --percent 50 (of 1080x1920)
       --samples N                                      --out renders/scene04/   (existing frames are skipped)
       --gpu    (Cycles on GPU: OptiX/CUDA, for Colab)
"""
import os, sys, math, time, importlib
import bpy
import bmesh
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
SUN_AZ = -8.0              # degrees: 0 = straight ahead of the bears (over the lake), + = to their left
LAKE_Z = -28.0             # the lake surface, ~45 m below the granite knoll (1 unit ~ 1.6 m, a bear is about a person tall)
EDGE_Y = -0.12             # the granite lip in front of the bears


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


def add_haze(m, N, L, bsdf, color=(.95, .55, .45), dist=260.0, strength=.6):
    """Aerial perspective: far things fade into the warm evening haze (works in EEVEE and Cycles)."""
    out = N['Material Output']
    cd = N.new('ShaderNodeCameraData')
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 30; mr.inputs['From Max'].default_value = dist
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
    base = ramp(noise(.6, 4).outputs['Fac'], [(.35, (.17, .17, .17)), (.55, (.24, .225, .215)), (.7, (.29, .27, .26))])
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
    # a few long joints: big blocks stretched vertically (granite splits in tall slabs)
    cm = N.new('ShaderNodeMapping'); cm.inputs['Scale'].default_value = (1.0, 1.0, .22); L.new(P, cm.inputs['Vector'])
    cr = N.new('ShaderNodeTexVoronoi'); cr.feature = 'DISTANCE_TO_EDGE'; cr.inputs['Scale'].default_value = .16
    cr.inputs['Randomness'].default_value = .8; L.new(cm.outputs['Vector'], cr.inputs['Vector'])
    crc = ramp(cr.outputs['Distance'], [(.0, (.12, .12, .12)), (.012, (1, 1, 1))])
    col = mix(1.0, col, crc.outputs['Color'], 'MULTIPLY')
    # lichen (pale grey-green blotches) everywhere, moss on the flat top
    lic = ramp(noise(6, 5).outputs['Fac'], [(.58, (0, 0, 0)), (.64, (1, 1, 1))])
    col = mix(lic.outputs['Color'], col,
              ramp(noise(30, 3).outputs['Fac'], [(.3, (.32, .34, .27)), (.7, (.42, .43, .35))]).outputs['Color'])
    # sandy soil with pine needles, moss patches; the 'rock' attribute (from the terrain build) says where granite shows
    soil = ramp(noise(7, 6).outputs['Fac'], [(.3, (.07, .045, .025)), (.55, (.15, .1, .055)), (.75, (.22, .15, .08))])
    needles = N.new('ShaderNodeTexWave'); needles.inputs['Scale'].default_value = 60; needles.inputs['Distortion'].default_value = 12
    L.new(P, needles.inputs['Vector'])
    ndl = ramp(needles.outputs['Fac'], [(.4, (.6, .5, .4)), (.6, (1, 1, 1))])
    soil_c = mix(1.0, soil.outputs['Color'], ndl.outputs['Color'], 'MULTIPLY')
    moss = ramp(noise(14, 6).outputs['Fac'], [(.3, (.03, .04, .012)), (.7, (.11, .11, .035))])
    mpatch = ramp(noise(.9, 4).outputs['Fac'], [(.5, (0, 0, 0)), (.6, (1, 1, 1))])
    soil_c = mix(mpatch.outputs['Color'], soil_c, moss.outputs['Color'])
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'rock'
    edge = ramp(at.outputs['Fac'], [(.35, (0, 0, 0)), (.55, (1, 1, 1))])
    col = mix(edge.outputs['Color'], soil_c, col)
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
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .15; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    add = N.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 2.0
    L.new(nz.outputs['Fac'], add.inputs[0]); L.new(sep.outputs['Z'], add.inputs[2])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = 0; r.elements[0].color = (.16, .15, .14, 1)        # granite at the water's edge
    r.elements[1].position = 1; r.elements[1].color = (.02, .025, .012, 1)      # dark forest floor
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = LAKE_Z + 1.0; mr.inputs['From Max'].default_value = LAKE_Z + 3.0
    L.new(add.outputs[0], mr.inputs['Value']); L.new(mr.outputs['Result'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
    add_haze(m, N, L, b, dist=260, strength=.78)
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
    ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = 2.5; ld.color = (1.0, .7, .5); ld.angle = math.radians(1.5)
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


# ---------------------------------------------------------------- the land: Lake Kaitalampi (Nuuksio)
# The bears sit on the bare granite lip of a knoll at the head of a long, narrow forest lake. In front of them a steep
# slope with granite outcrops and pines, spruces and birches falls ~45 m to the water; the lake runs away from them
# between forested shores, and the sun sets at its far end.
def edge_y(x):
    """The lip of the knoll curves back on both sides of the bears."""
    return EDGE_Y + .03 * x * x + .06 * fbm(x * .7, 3.1, 3)


def knoll_height(x, y):
    u = y - edge_y(x)
    s = np.maximum(-u, 0)                                         # distance out from the lip
    seat = np.exp(-(x * x) / 1.5)
    r = .7 - .6 * seat                                            # a crisp edge where they sit, rounded brows elsewhere
    brow = 1.25 * (s - r * (1 - np.exp(-s / r)))
    terr = 1.1 * np.sin(.9 * s + 3 * fbm(x * .15, 1.0, 2)) * (1 - np.exp(-s / 2.5))     # granite steps and ledges
    step = .6 * seat * np.clip((s - .06) / .12, 0, 1)              # a little drop under their feet so the legs dangle
    down = -(brow + terr + step) + .9 * fbm(x * .45, s * .45 + 4, 5) * np.clip(s / 2, 0, 1)
    up = np.maximum(u, 0)
    calm = np.exp(-(x * x) / 2.5 - up * up / 2)                    # keep the seat flat
    top = .02 * up + .4 * fbm(x * .45, up * .45 + 11, 5) * (1 - calm) + .18 * np.clip(up - 6, 0, None)
    side = -.45 * np.clip(np.abs(x) - 7, 0, None)
    return np.maximum(side + np.where(u >= 0, top, down), LAKE_Z - 8)


def shore_height(x, y):
    """The other shores: the lake is a long channel running away from the bears (-Y), forest hills on both sides."""
    xc = 14 * np.sin(-y / 90) * np.clip((-y - 10) / 40, 0, 1)
    W = 30 + 8 * np.sin(-y / 55 + 1)
    dist = np.abs(x - xc)
    rise = np.clip((dist - W) / 9, 0, 1) + np.clip((y - 12) / 15, 0, 1) + np.clip((-y - 380) / 40, 0, 1)
    hills = 16 + 9 * fbm(x / 40, y / 40, 4) + 6 * fbm(x / 14 + 5, y / 14, 4)
    return LAKE_Z - 3 + np.clip(rise, 0, 1) * hills


def land_z(x, y):
    return np.maximum(knoll_height(x, y), shore_height(x, y))


def ground_z(x, y):
    return float(land_z(np.array(float(x)), np.array(float(y))))


def in_knoll(x, y, margin=0.0):
    u = y - edge_y(x)
    return (np.abs(x) < 30 - margin) & (u > -45 + margin) & (u < 30 - margin)


def color_attr(ob, name, vals):
    a = ob.data.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    v = np.repeat(np.asarray(vals, np.float32)[:, None], 4, 1); v[:, 3] = 1
    a.data.foreach_set('color', v.ravel())


def make_knoll(coll, mat):
    s = np.linspace(-1, 1, 401); X1 = 30 * np.sinh(3 * s) / np.sinh(3)
    t1 = np.linspace(0, 1, 230); t2 = np.linspace(0, 1, 140)
    U1 = np.concatenate([-45 * t1[::-1] ** 2.2, 30 * t2[1:] ** 2.2])
    Xg, Ug = np.meshgrid(X1, U1)
    Yg = edge_y(Xg) + Ug
    Zg = land_z(Xg, Yg)
    ob = grid_mesh('Knoll', Xg, Yg, Zg, coll, mat)
    # bare granite where it is steep, big glacier-smoothed slabs on the top, sandy soil, needles and moss elsewhere
    e = .05
    gx = (land_z(Xg + e, Yg) - land_z(Xg - e, Yg)) / (2 * e); gy = (land_z(Xg, Yg + e) - land_z(Xg, Yg - e)) / (2 * e)
    g = np.sqrt(gx * gx + gy * gy)
    rock = np.clip((g - 1.7) / .6, 0, 1) * np.clip((fbm(Xg * .3, Yg * .3 + 7, 3) + .12) * 6, 0, 1) + np.clip((g - 2.6) / .5, 0, 1)
    rock = np.clip(rock, 0, 1)
    slabs = np.clip((fbm(Xg * .22 + 3, Yg * .22, 4) + .03) * 7, 0, 1) * np.clip((1.0 - g) / .4, 0, 1)
    seat = np.exp(-(Xg ** 2) / 3 - (np.maximum(Ug, 0) - .3) ** 2 / 1.2) * (Ug > -1.5)
    rock = np.maximum(np.maximum(rock, slabs), np.clip(seat * 1.6, 0, 1))
    color_attr(ob, 'rock', rock.ravel())
    near = np.exp(-((Xg - .3) ** 2 + (Yg - 1.5) ** 2) / 120)
    patch = np.clip((fbm(Xg * 1.1 + 9, Yg * 1.1, 4) + .08) * 5, 0, 1)
    vgroup(ob, 'shrubs', ((1 - rock) * patch * near).ravel())
    return ob


def make_shores(coll, mat):
    xs = np.linspace(-230, 230, 231); ys = np.linspace(-430, 130, 281)
    Xg, Yg = np.meshgrid(xs, ys)
    Zg = land_z(Xg, Yg)
    Zg = np.where(in_knoll(Xg, Yg, 1.0), np.minimum(Zg, LAKE_Z - 1) , Zg)      # the detailed knoll mesh covers this part
    ob = grid_mesh('Shores', Xg, Yg, Zg, coll, mat)
    wood = np.clip((Zg - LAKE_Z - .8) / 1.2, 0, 1) * (~in_knoll(Xg, Yg, -2.0))
    vgroup(ob, 'forest', wood.ravel())
    return ob


def make_shrubs(knoll):
    """Low blueberry and heather between the rocks on the knoll."""
    m, N, L, b = node_mat('Shrubs')
    hi = N.new('ShaderNodeHairInfo'); ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].color = (.015, .02, .008, 1); r.elements[1].color = (.1, .12, .035, 1)
    e = r.elements.new(.8); e.color = (.16, .09, .04, 1)
    L.new(hi.outputs['Intercept'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .6
    knoll.data.materials.append(m)
    mod = knoll.modifiers.new('Shrubs', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 9000; s.use_advanced_hair = True
    s.normal_factor = .05; s.factor_random = .04; s.object_align_factor = (0, 0, .02)
    s.material_slot = 'Shrubs'; s.render_step = 3; s.display_step = 2
    s.child_type = 'INTERPOLATED'; s.child_percent = 2; s.rendered_child_count = 14; s.child_radius = .09
    s.roughness_2 = .03; s.roughness_endpoint = .03; s.clump_factor = .5; s.kink = 'CURL'; s.kink_amplitude = .01
    s.radius_scale = .005; s.root_radius = 1; s.tip_radius = .3
    s.length_random = .6; s.display_percentage = 20
    mod.particle_system.vertex_group_density = 'shrubs'
    mod.particle_system.vertex_group_length = 'shrubs'


# ---------------------------------------------------------------- trees
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
    """A lumpy ball of needles/leaves."""
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
    """Scots pine as in Nuuksio: a tall bare trunk (dark below, orange above) and a high, airy crown of needle clumps."""
    rng = np.random.default_rng(seed)
    V, F, M = [], [], []
    lean = rng.normal(0, .035, 2)
    zs = np.linspace(0, .97, 7)
    pts = [(lean[0] * z + .01 * math.sin(z * 9 + seed), lean[1] * z + .01 * math.cos(z * 7 + seed), z) for z in zs]
    n = 8 if lod == 0 else 5
    for a, b_, z in zip(pts[:-1], pts[1:], zs[:-1]):
        _cyl(V, F, M, a, b_, .02 * (1 - z * .78), .02 * (1 - (z + .16) * .78), n, 1)
    def trunk_at(z):
        return np.array([lean[0] * z, lean[1] * z, z])
    c0 = rng.uniform(.6, .72)
    nb = 10 if lod == 0 else 6
    for k in range(nb):
        z = c0 + (.94 - c0) * k / (nb - 1) + rng.normal(0, .015)
        az = k * 2.4 + rng.normal(0, .4)
        L = (.07 + .17 * (1 - (z - c0) / (1 - c0))) * rng.uniform(.7, 1.25)
        up = rng.uniform(.15, .55)
        base = trunk_at(z); end = base + L * np.array([math.cos(az), math.sin(az), up])
        if lod == 0:
            _cyl(V, F, M, base, end, .006, .0025, 5, 1)
        _clump(V, F, M, end + [0, 0, .015], rng.uniform(.05, .075), .72, rng, 0, 2 if lod == 0 else 1)
        if lod == 0:
            _clump(V, F, M, end + rng.normal(0, .03, 3) + [0, 0, .03], rng.uniform(.035, .05), .8, rng, 0, 1)
        if lod == 0 and L > .12:
            mid = base + .6 * (end - base)
            _clump(V, F, M, mid + [0, 0, .02], rng.uniform(.045, .06), .55, rng, 0, 1)
    _clump(V, F, M, trunk_at(.98) + [0, 0, .02], .06, .7, rng, 0, 2 if lod == 0 else 1)
    return _finish(name, V, F, M, mats)


def spruce(name, seed, mats, lod=0):
    """Norway spruce: dense dark cone of drooping star-shaped branch tiers."""
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
    """Slender birch: white trunk, airy light-green crown."""
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


def pine_bark_material():
    """Scots pine bark: grey-brown and furrowed low down, thin flaky orange high up."""
    m, N, L, b = node_mat('PineBark')
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = .35; r.elements[0].color = (.045, .035, .028, 1)
    r.elements[1].position = .6; r.elements[1].color = (.36, .14, .05, 1)
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


def make_tree_library():
    pn = foliage_material('PineNeedles', (.02, .04, .012), (.07, .095, .03))
    sn = foliage_material('SpruceNeedles', (.008, .02, .01), (.025, .045, .018), tint=(.3, .4, .2))
    bl = foliage_material('BirchLeaves', (.06, .13, .025), (.17, .26, .05), tint=(.8, .8, .3))
    rust = foliage_material('DryNeedles', (.25, .06, .015), (.5, .16, .04), tint=(1, .5, .2))
    pb, bb = pine_bark_material(), birch_bark_material()
    hi = {
        'pine': [scots_pine(f'ScotsPine{k}', 10 + k, [pn, pb]) for k in range(4)],
        'spruce': [spruce(f'Spruce{k}', 20 + k, [sn, pb]) for k in range(3)],
        'birch': [birch(f'Birch{k}', 30 + k, [bl, bb]) for k in range(3)],
        'rust': [scots_pine('DryPine', 41, [rust, pb])],
    }
    lib = new_coll('ForestLibrary')
    lo = [scots_pine('ScotsPineLo0', 50, [pn, pb], 1), scots_pine('ScotsPineLo1', 51, [pn, pb], 1),
          spruce('SpruceLo0', 60, [sn, pb], 1), spruce('SpruceLo1', 61, [sn, pb], 1), spruce('SpruceLo2', 62, [sn, pb], 1),
          birch('BirchLo0', 70, [bl, bb], 1)]
    for k, me in enumerate(lo):
        o = bpy.data.objects.new(me.name, me); lib.objects.link(o)
    bpy.context.view_layer.layer_collection.children[lib.name].exclude = True
    return hi, lib


SIGHTS = []     # (camera position, target) pairs whose view must stay clear; filled by make_cameras()


def tree_blocks(x, y, z0, h):
    top = z0 + h
    for a, b_ in SIGHTS:
        ax, ay, az = a; bx, by, bz = b_
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        if math.hypot(x - ax - dx * t, y - ay - dy * t) < .22 * h + .8 and top > az + (bz - az) * t - .5:
            return True
    return False


def plant_trees(coll, hi):
    """Trees on the knoll top and down the slope (individual objects; the far shores use particles)."""
    rng = np.random.default_rng(5)
    n = 0; rusty = False
    xs = np.arange(-29, 29, 2.4); ys = np.arange(-40, 30, 2.4)
    for gx in xs:
        for gy in ys:
            x = gx + rng.uniform(-1, 1); y = gy + rng.uniform(-1, 1)
            if not in_knoll(np.array(x), np.array(y), 1.0):
                continue
            z = ground_z(x, y)
            if z < LAKE_Z + .6:
                continue
            u = y - float(edge_y(np.array(x)))
            if abs(x) < 2.2 and -1 < u < 2.5:      # their seat on the rock
                continue
            top_area = u > 0
            if rng.random() > (.33 if top_area else .7):
                continue
            r = rng.random()
            if top_area:
                kind = 'pine' if r < .82 else ('spruce' if r < .93 else 'birch'); h = rng.uniform(12, 17)
            else:
                kind = 'pine' if r < .42 else ('spruce' if r < .74 else 'birch'); h = rng.uniform(8, 15)
                if rng.random() < .18:
                    h = rng.uniform(1.5, 5)      # young trees
            if kind == 'birch':
                h *= .8
            # keep the bears' view down the lake open: trees in front must stay below their eye line
            sd = max(-u, 0)
            if not top_area and abs(x) < 4 + .6 * sd:
                limit = (.3 - .55 * sd) - z - .6
                if limit < 1.5:
                    continue
                h = min(h, limit)
            if tree_blocks(x, y, z, h):
                continue
            meshes = hi[kind]
            if kind == 'pine' and not rusty and not top_area and z < -8:
                rusty = True
                meshes = hi['rust']                   # one dry, rust-coloured pine (like in the photo)
            o = bpy.data.objects.new(f'Tree_{n:03d}', meshes[n % len(meshes)]); coll.objects.link(o)
            o.location = (x, y, z - .15)
            o.scale = (h * rng.uniform(.85, 1.15), h * rng.uniform(.85, 1.15), h)
            o.rotation_euler = (rng.normal(0, .03), rng.normal(0, .03), rng.uniform(0, 2 * PI))
            n += 1
    print('trees on the knoll:', n)


def make_forest(shores, lib):
    mod = shores.modifiers.new('Forest', 'PARTICLE_SYSTEM'); s = mod.particle_system.settings
    s.type = 'HAIR'; s.count = 16000; s.hair_length = 1
    s.render_type = 'COLLECTION'; s.instance_collection = lib; s.use_collection_pick_random = True
    s.particle_size = 13; s.size_random = .4
    s.use_rotations = True; s.rotation_mode = 'NONE'; s.use_rotation_instance = True
    s.display_percentage = 10; s.use_emit_random = True; s.distribution = 'RAND'
    mod.particle_system.vertex_group_density = 'forest'
    mod.particle_system.seed = 11


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
    cd = bpy.data.cameras.new('Cam_Wide'); cd.lens = 26; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 5.6
    cam = bpy.data.objects.new('Cam_Wide', cd); sc.collection.objects.link(cam)
    tgt = Vector((-2.4, -16.9, -1.3))
    for f, p in ((FRAMES[0], (.75, 5.0, 1.55)), (FRAMES[1], (.55, 4.1, 1.35))):
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
    for f, p in ((FRAMES[0], (-9, -80, -19)), (FRAMES[1], (-8, -74, -15))):
        cam3.location = p; look(cam3, (0, 0, -8))
        cam3.keyframe_insert('location', frame=f); cam3.keyframe_insert('rotation_euler', frame=f)
    sc.camera = cam
    return cam, cam2


def camera_sights():
    """Lines from each camera to the bears that trees must not block (used before planting)."""
    bears_at = (0, .06, .45)
    SIGHTS[:] = [((.75, 5.0, 1.55), bears_at), ((.55, 4.1, 1.35), bears_at), ((.12, -2.75, .62), bears_at),
                 ((-9, -80, -19), bears_at), ((-8, -74, -15), bears_at)]


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
    env = new_coll('Set'); trees = new_coll('Trees')
    ground = rock_material()
    knoll = make_knoll(env, ground); make_shrubs(knoll)
    shores = make_shores(env, land_material())
    hi, lib = make_tree_library()
    make_forest(shores, lib)
    camera_sights(); plant_trees(trees, hi)
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
    if o['camera'] == 'edit':
        # a little cut: establishing -> wide -> faces (timeline markers switch the camera)
        for f, name in ((FRAMES[0], 'Cam_Establish'), (64, 'Cam_Wide'), (150, 'Cam_Faces')):
            mk = sc.timeline_markers.new(name, frame=f); mk.camera = bpy.data.objects[name]
        sc.camera = bpy.data.objects['Cam_Establish']
    else:
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
