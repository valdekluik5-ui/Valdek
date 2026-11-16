"""
Home - scene 12: the road north, Kyiv -> Helsinki by car (song 3:34-4:04, the music at its strongest). A montage:

Shots:  1-96    a paper map: a dotted line grows from Kyiv north through Palanga, Riga, Estonia and Tallinn to Helsinki
       97-220   Palanga: a sandy Baltic beach below pine dunes; they walk along the water, paw in paw
      221-290   Latvia: the little car on a forest road
      291-370   Jägala waterfall, wide: the curved limestone ledge, one brown-and-white curtain, the canyon; two tiny bears
      371-450   Jägala, close (as in their photo): on the limestone slabs by the pool, the falls behind; she kisses his cheek
      451-530   Tallinn old town: gabled houses and towers with red cone roofs
      531-590   berry picking in the forest, a few calm days
      591-650   the ferry crossing the Gulf of Finland, Tallinn's spires behind, gulls following
      651-720   at the bow: Helsinki ahead, the white cathedral at golden hour
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

SHOTS = dict(map=1, palanga=97, latvia=221, falls=291, falls2=371, tallinn=451, berries=531, ferry=591, deck=651, end=720)
MAP = Vector((-3000.0, 0.0, 0.0)); PAL = Vector((3000.0, 0.0, 0.0)); LAT = Vector((0.0, -3000.0, 0.0))
FAL = Vector((3000.0, 3000.0, 0.0)); TAL = Vector((-3000.0, 3000.0, 0.0)); BER = Vector((3000.0, -3000.0, 0.0))

# ---------------------------------------------------------------- the map
CITIES = [('Kyiv', 30.52, 50.45), ('Palanga', 21.07, 55.92), ('Riga', 24.11, 56.95), ('Jägala', 25.17, 59.45),
          ('Tallinn', 24.75, 59.44), ('Helsinki', 24.94, 60.17)]
# a rough Baltic coastline (lon, lat) for a hand-drawn look
SEA = [(10.5, 54.3), (12.5, 54.4), (14.2, 53.9), (16.5, 54.6), (18.6, 54.8), (19.6, 54.4), (21.0, 55.3), (21.1, 56.1), (21.0, 57.0),
       (21.6, 57.6), (22.6, 57.75), (23.4, 57.1), (24.1, 57.0), (24.4, 57.3), (24.3, 58.3), (23.5, 58.7), (23.4, 59.2), (24.2, 59.45),
       (25.5, 59.6), (27.2, 59.45), (28.1, 59.5), (29.9, 59.9), (28.5, 60.4), (27.0, 60.5), (25.5, 60.3), (24.0, 60.0), (22.9, 59.85),
       (22.3, 60.4), (21.4, 60.8), (21.3, 61.8), (21.5, 63.0), (22.5, 64.0), (23.0, 66.0), (20.0, 66.0), (17.5, 62.5), (18.0, 60.3),
       (18.8, 59.3), (16.6, 57.0), (16.2, 56.2), (14.3, 55.5), (12.8, 56.2), (10.5, 56.0)]


LABEL_OFF = {'Tallinn': (-1.25, -.3), 'Jägala': (.15, -.32)}


def mapxy(lon, lat):
    return Vector((MAP.x + (lon - 24) * .55, MAP.y + (lat - 56) * 1.0, MAP.z))


def build_map(coll):
    paper = mat('MapPaper', (.78, .68, .5), rough=.9)
    m, N, L, b = node_mat('MapPaperTex'); b.inputs['Roughness'].default_value = .95
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.32, .23, .12, 1); rp.color_ramp.elements[1].color = (.52, .42, .26, 1)
    L.new(nz.outputs['Fac'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color'])
    box('MapSheet', (12, 14, .02), MAP + Vector((0, 1.5, -.02)), m, coll)
    sea = mat('MapSea', (.08, .16, .2), rough=.85)
    pts = [mapxy(lo, la) for lo, la in SEA]
    film.mesh_obj('MapSea', [p + Vector((0, 0, .002)) for p in pts], [tuple(range(len(pts)))], coll, [sea])
    ink = mat('MapInk', (.12, .07, .04), rough=.7); red = mat('MapRed', (.65, .08, .06), rough=.6)
    for name, lo, la in CITIES:
        p = mapxy(lo, la)
        cylinder(f'Dot{name}', .08, .01, p + Vector((0, 0, .003)), ink, coll, n=16)
        cu = bpy.data.curves.new('Label' + name, 'FONT'); cu.body = name; cu.size = .32
        cu.materials.append(ink)
        try:
            cu.font = bpy.data.fonts.load(os.path.join(_here(), 'fonts', 'CormorantGaramond-Italic.ttf'))
        except Exception:
            pass
        t = link(bpy.data.objects.new('Label' + name, cu), coll); t.location = p + Vector(LABEL_OFF.get(name, (.15, .05)) + (.004,))
    # the dotted route, appearing as the car icon travels
    route = [mapxy(lo, la) for _, lo, la in CITIES]
    segs = [(route[i], route[i + 1]) for i in range(len(route) - 1)]
    total = sum((b - a).length for a, b in segs)
    n = 70; dots = []
    for i in range(n):
        d = total * i / (n - 1); acc = 0
        for a, b in segs:
            if acc + (b - a).length >= d:
                p = a.lerp(b, (d - acc) / max((b - a).length, 1e-6)); break
            acc += (b - a).length
        dots.append(p)
    f0, f1 = 8, SHOTS['palanga'] - 10
    for i, p in enumerate(dots):
        o = cylinder(f'RouteDot{i}', .035, .006, p + Vector((0, 0, .004)), red, coll, n=10)
        film.key_visible(o, 1, False); film.key_visible(o, int(f0 + (f1 - f0) * i / (n - 1)), True)
    icon = film.car('MapCar', dots[0], 0, coll, color=(.12, .2, .28))
    icon.scale = (.12, .12, .12)
    for i in range(0, n, 3):
        f = int(f0 + (f1 - f0) * i / (n - 1)); j = min(i + 1, n - 1)
        d = dots[j] - dots[i]
        icon.location = dots[i] + Vector((0, 0, .01)); icon.rotation_euler = (0, 0, math.atan2(d.x, -d.y) if d.length > 1e-6 else 0)
        icon.keyframe_insert('location', frame=f); icon.keyframe_insert('rotation_euler', frame=f)
    film.area_light('MapLight', MAP + Vector((-3, -6, 9)), MAP + Vector((0, 1, 0)), 350, 6, (1, .85, .65))
    return mapxy


# ---------------------------------------------------------------- Palanga: sandy beach, dunes with pines
def build_palanga(coll):
    film.HAZE.update(color=(1, .85, .7), start=30.0, dist=400.0, strength=.45)
    import scene08_baltic as s8
    importlib.reload(s8)
    sand = s8.sand_material('PalangaSand', wet_line=-3.0)
    xs = np.linspace(-90, 90, 181); ys = np.linspace(-6, 60, 133)
    X, Y = np.meshgrid(xs, ys)
    Z = np.clip(Y + 4, 0, None) * .03 + np.clip(Y - 12, 0, None) * .22 + .5 * film.fbm(X * .05, Y * .05, 3) * np.clip((Y - 10) / 6, 0, 1) - .25
    beach = film.grid_mesh('PalangaBeach', X + PAL.x, Y + PAL.y, Z, coll, sand)
    film.vgroup(beach, 'pines', np.clip((Y - 16) / 4, 0, 1).ravel())
    sea = film.water_material('PalangaSea', color=(.02, .06, .08), rough=.06, wave=.25, scale=.5)
    film.mesh_obj('PalangaSea', [PAL + Vector(v) for v in [(-400, -2.5, -.3), (400, -2.5, -.3), (400, -500, -.3), (-400, -500, -.3)]], [(0, 1, 2, 3)], coll, [sea])
    foam = mat('PalFoam', (.85, .87, .88), rough=.5, haze=True)
    rng = np.random.default_rng(2)
    for i in range(40):
        blob(f'PalFoam{i}', PAL + Vector((rng.uniform(-30, 30), -2.6 + rng.uniform(-.2, .3), -.29)), (rng.uniform(.5, 1.6), rng.uniform(.04, .12), .01), coll, foam, sub=2, seed=i)
    hi, lib = film.tree_library('PalangaPines')
    pines = film.new_coll('PalangaPineSet')
    for k in range(60):
        x = rng.uniform(-60, 60); y = rng.uniform(17, 40)
        z = float(np.clip(y + 4, 0, None) * .03 + np.clip(y - 12, 0, None) * .22) - .25
        film.place_tree(pines, hi['pine'][k % 4], PAL + Vector((x, y, z - .1)), rng.uniform(10, 15), rng, name=f'PalPine{k}')
    film.meadow('Dunes', (PAL.x, PAL.y + 15), (60, 7), coll, z_fn=lambda X, Y: np.clip(Y - PAL.y + 4, 0, None) * .03 + np.clip(Y - PAL.y - 12, 0, None) * .22 - .25,
                density=.5, flowers=False, colors=((.3, .28, .15), (.62, .58, .35)), seed=21)
    # the long Palanga pier in the distance
    wood = mat('PierWood', (.35, .25, .17), rough=.7, haze=True)
    box('Pier', (2.2, 120, .25), PAL + Vector((-40, -60, .6)), wood, coll)
    for i in range(30):
        cylinder(f'PierPost{i}', .12, 1.2, PAL + Vector((-40, -2 - i * 4, -.6)), wood, coll, n=8)


# ---------------------------------------------------------------- Estonia: the farmhouse
def _strata_material(name, base=(.46, .4, .3), dark=(.2, .17, .12), moss=(.05, .09, .03), grass=(.1, .17, .04)):
    """Layered limestone on steep faces (horizontal bands that follow the height), moss and grass on flat ground above
    the river, darker wet rock at river level."""
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord')
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = .55; wv.inputs['Distortion'].default_value = 3.0; wv.inputs['Detail'].default_value = 5
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .9; nz.inputs['Detail'].default_value = 10
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = .55
    L.new(wv.outputs['Fac'], mx.inputs[0]); L.new(nz.outputs['Fac'], mx.inputs[2])
    rock = N.new('ShaderNodeValToRGB'); rock.color_ramp.elements[0].color = (*dark, 1); rock.color_ramp.elements[1].color = (*base, 1)
    rock.color_ramp.elements[0].position = .35; rock.color_ramp.elements[1].position = 1.0
    L.new(mx.outputs['Value'], rock.inputs['Fac'])
    # flat ground: moss -> grass; steepness from the normal
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs['Vector'])
    flat = N.new('ShaderNodeMapRange'); flat.inputs['From Min'].default_value = .62; flat.inputs['From Max'].default_value = .9
    L.new(sep.outputs['Z'], flat.inputs['Value'])
    sep2 = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep2.inputs['Vector'])
    high = N.new('ShaderNodeMapRange'); high.inputs['From Min'].default_value = .25; high.inputs['From Max'].default_value = .7
    L.new(sep2.outputs['Z'], high.inputs['Value'])
    veg = N.new('ShaderNodeMath'); veg.operation = 'MULTIPLY'; L.new(flat.outputs['Result'], veg.inputs[0]); L.new(high.outputs['Result'], veg.inputs[1])
    gn = N.new('ShaderNodeTexNoise'); gn.inputs['Scale'].default_value = .4; L.new(tc.outputs['Object'], gn.inputs['Vector'])
    gcol = N.new('ShaderNodeValToRGB'); gcol.color_ramp.elements[0].color = (*moss, 1); gcol.color_ramp.elements[1].color = (*grass, 1)
    L.new(gn.outputs['Fac'], gcol.inputs['Fac'])
    mix = N.new('ShaderNodeMixRGB'); L.new(veg.outputs['Value'], mix.inputs['Fac']); L.new(rock.outputs['Color'], mix.inputs['Color1']); L.new(gcol.outputs['Color'], mix.inputs['Color2'])
    # wet and dark near river level (the riverbed and the canyon floor)
    wet = N.new('ShaderNodeMapRange'); wet.inputs['From Min'].default_value = .2; wet.inputs['From Max'].default_value = -.1
    L.new(sep2.outputs['Z'], wet.inputs['Value'])
    low = N.new('ShaderNodeMapRange'); low.inputs['From Min'].default_value = -7.2; low.inputs['From Max'].default_value = -7.9
    L.new(sep2.outputs['Z'], low.inputs['Value'])
    wsum = N.new('ShaderNodeMath'); wsum.operation = 'MAXIMUM'; L.new(wet.outputs['Result'], wsum.inputs[0]); L.new(low.outputs['Result'], wsum.inputs[1])
    dk = N.new('ShaderNodeMixRGB'); dk.blend_type = 'MULTIPLY'; dk.inputs['Color2'].default_value = (.45, .42, .38, 1)
    L.new(wsum.outputs['Value'], dk.inputs['Fac']); L.new(mix.outputs['Color'], dk.inputs['Color1'])
    L.new(dk.outputs['Color'], b.inputs['Base Color'])
    rg = N.new('ShaderNodeMapRange'); rg.inputs['To Min'].default_value = .85; rg.inputs['To Max'].default_value = .3
    L.new(wsum.outputs['Value'], rg.inputs['Value']); L.new(rg.outputs['Result'], b.inputs['Roughness'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .7; bump.inputs['Distance'].default_value = .15
    L.new(mx.outputs['Value'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b)
    return m


def _masked_grid(name, X, Y, Z, keep, coll, mat):
    """A grid mesh keeping only the cells whose four corners are all in `keep`."""
    ny, nx = X.shape
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    I, J = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1))
    a = (J * nx + I).ravel()
    F = np.stack([a, a + 1, a + 1 + nx, a + nx], 1)
    k = keep.ravel()
    F = F[k[F].all(1)]
    o = film.mesh_obj(name, V, F, coll, [mat], smooth=True)
    return o


# Jägala: Estonia's widest waterfall. A curved limestone ledge about 50 m across and 8 m high; the brown, peaty river
# pours over it in one wide curtain into a canyon of layered limestone, with pines and birches along the top.
FALL_R, FALL_H, FALL_A = 26.0, 8.0, math.radians(58)
SHELF_Z = -7.72          # the flat limestone shelf where they stand, beside the pool


def build_falls(coll):
    film.HAZE.update(color=(.85, .9, .95), start=40.0, dist=300.0, strength=.3)
    T = lambda x, y, z: FAL + Vector((x, y, z))
    R, H, A0 = FALL_R, FALL_H, FALL_A
    rock = _strata_material('JagalaRock')
    # ---- one terrain: the upper river bed and its banks, the curved drop, the canyon below
    xs = np.arange(-90, 90.01, .5); ys = np.arange(-80, 170.01, .5)
    X, Y = np.meshgrid(xs, ys)
    d = np.hypot(X, Y - R)
    w = 13.5 + 8.5 * np.clip((Y + 30) / 42, 0, 1)                     # canyon half-width, widening toward the falls
    jag = 1.2 * film.fbm(X / 6 + 3, Y / 6, 3)                           # ragged rock edges
    canyon = ((d > R) & (np.abs(X) < w + jag) & (Y < R * (1 - math.cos(A0)) + 1.5)) | ((d > R) & (np.abs(X) < R * math.sin(A0)) & (Y < 14))
    river = (d <= R) & (np.abs(X) < R * math.sin(A0) + 1.0 * film.fbm(X / 8, Y / 8, 2))
    bend = 9 * np.clip((Y - 50) / 60, 0, 1) ** 2                       # the river bends away to the left upstream
    river |= (Y > R) & (np.abs(X + bend) < np.maximum(8.0, 21 - (Y - R) * .2) + 2 * film.fbm(Y / 30, 1.0, 2)) & (Y < 150)
    bank = .9 + 1.6 * np.clip((np.abs(X) - 20) / 30, 0, 1) + .5 * film.fbm(X / 14, Y / 14, 3)
    Z = np.where(canyon, -H - .45 + .25 * film.fbm(X / 3, Y / 3, 2), np.where(river, -.05 + .12 * film.fbm(X / 4, Y / 4, 2), bank))
    Xj = X + .25 * film.fbm(X / 2 + 7, Y / 2, 2); Yj = Y + .25 * film.fbm(X / 2, Y / 2 + 7, 2)
    terr = film.grid_mesh('JagalaTerrain', Xj + FAL.x, Yj + FAL.y, Z + FAL.z, coll, rock)
    # trees on the banks, back from the edges
    edge = canyon | river
    near = edge.copy()
    for _ in range(8):
        near = near | np.roll(near, 1, 0) | np.roll(near, -1, 0) | np.roll(near, 1, 1) | np.roll(near, -1, 1)
    film.vgroup(terr, 'forest', ((~near) & (film.fbm(X / 25 + 4, Y / 25, 3) > -.25)).astype(float).ravel())
    hi, lib = film.tree_library('FallsForest')
    film.scatter_instances(terr, lib, 'forest', 2600, 14, seed=31)
    # a few big single trees right at the rim (hi-res), leaning a little over the canyon
    trng = np.random.default_rng(21)
    allt = hi['pine'] + hi['birch'] + hi['spruce']
    for k in range(26):
        sx = -1 if k % 2 else 1; y = trng.uniform(-45, 20)
        x = sx * (13.5 + 8.5 * np.clip((y + 30) / 42, 0, 1) + trng.uniform(2.5, 6))
        film.place_tree(coll, allt[k % len(allt)], T(x, y, 1.0), trng.uniform(8, 15), trng, name=f'RimTree{k}')
    # ---- water: the river above, brown and smooth, sliding toward the lip
    up = film.water_material('JagalaRiver', color=(.06, .035, .015), rough=.12, wave=.25, scale=.6)
    keep = river.copy()
    for _ in range(2):
        keep = keep | np.roll(keep, 1, 1) | np.roll(keep, -1, 1)
    keep &= ~canyon
    _masked_grid('JagalaRiverSurface', X + FAL.x, Y + FAL.y, np.full_like(X, .12) + FAL.z, keep & (d < R + .2) | (keep & (Y > R)), coll, up)
    pool = film.water_material('JagalaPool', color=(.035, .025, .012), rough=.2, wave=.6, scale=.8)
    film.mesh_obj('JagalaPool', [T(-30, -80, -H + .05), T(30, -80, -H + .05), T(30, 16, -H + .05), T(-30, 16, -H + .05)], [(0, 1, 2, 3)], coll, [pool])
    # ---- the curtain: two layers. Behind: amber, nearly solid. In front: white streaks that run down, with gaps.
    def curtain(name, off, m):
        aa = np.linspace(-A0 - .02, A0 + .02, 220); tt = np.linspace(0, 1, 26)
        Aa, Tt = np.meshgrid(aa, tt)
        r = R + off + 1.35 * np.sqrt(Tt) + .15 * np.sin(Aa * 9) * Tt
        Xc = r * np.sin(Aa); Yc = R - r * np.cos(Aa); Zc = .12 - (H + .1) * Tt
        return film.grid_mesh(name, Xc + FAL.x, Yc + FAL.y, Zc + FAL.z, coll, m)
    back, N, L, b = node_mat('FallBack')
    b.inputs['Base Color'].default_value = (.3, .17, .06, 1); b.inputs['Roughness'].default_value = .2
    b.inputs['Alpha'].default_value = .55
    try:
        back.surface_render_method = 'DITHERED'
    except Exception:
        pass
    add_haze(back, N, L, b)
    curtain('FallCurtainBack', .05, back)
    front, N, L, b = node_mat('FallFront')
    tc = N.new('ShaderNodeTexCoord'); off = N.new('ShaderNodeVectorMath'); off.operation = 'SUBTRACT'; off.inputs[1].default_value = tuple(FAL)
    L.new(tc.outputs['Object'], off.inputs[0])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (2.2, 2.2, .18)
    L.new(off.outputs['Vector'], mp.inputs['Vector'])
    fc = mp.inputs['Location'].driver_add('default_value', 2); fc.driver.expression = 'frame * 0.035'
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = .65
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    lace = N.new('ShaderNodeTexVoronoi'); lace.feature = 'DISTANCE_TO_EDGE'; lace.inputs['Scale'].default_value = 9
    L.new(mp.outputs['Vector'], lace.inputs['Vector'])
    mixl = N.new('ShaderNodeMath'); mixl.operation = 'MULTIPLY_ADD'; mixl.inputs[1].default_value = 1.6
    L.new(lace.outputs['Distance'], mixl.inputs[0]); L.new(nz.outputs['Fac'], mixl.inputs[2])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = .82; rp.color_ramp.elements[1].position = 1.05
    rp.color_ramp.elements[0].color = (0, 0, 0, 1); rp.color_ramp.elements[1].color = (1, 1, 1, 1)
    L.new(mixl.outputs['Value'], rp.inputs['Fac'])
    st = N.new('ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 1.0; st.inputs['Detail'].default_value = 2
    stm = N.new('ShaderNodeMapping'); stm.inputs['Scale'].default_value = (.12, .12, .004); L.new(off.outputs['Vector'], stm.inputs['Vector']); L.new(stm.outputs['Vector'], st.inputs['Vector'])
    sc_ = N.new('ShaderNodeValToRGB'); sc_.color_ramp.elements[0].position = .52; sc_.color_ramp.elements[1].position = .62
    sc_.color_ramp.elements[0].color = (.92, .88, .8, 1); sc_.color_ramp.elements[1].color = (.62, .33, .09, 1)
    L.new(st.outputs['Fac'], sc_.inputs['Fac']); L.new(sc_.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .45
    b.inputs['Emission Color'].default_value = (1, .97, .9, 1); b.inputs['Emission Strength'].default_value = .08
    L.new(rp.outputs['Color'], b.inputs['Alpha'])
    try:
        front.surface_render_method = 'DITHERED'
    except Exception:
        pass
    add_haze(front, N, L, b)
    curtain('FallCurtainFront', .25, front)
    # ---- foam: painted into the pool's surface, thick and white at the foot of the falls, breaking up into drifting
    # lace further down the canyon (the pattern slides downstream)
    Np, Lp = pool.node_tree.nodes, pool.node_tree.links; bp = Np['Principled BSDF']
    tcp = Np.new('ShaderNodeTexCoord'); mpp = Np.new('ShaderNodeMapping'); mpp.inputs['Scale'].default_value = (.35, .12, .35)
    Lp.new(tcp.outputs['Object'], mpp.inputs['Vector'])
    fcp = mpp.inputs['Location'].driver_add('default_value', 1); fcp.driver.expression = 'frame * 0.0025'
    lace = Np.new('ShaderNodeTexNoise'); lace.inputs['Scale'].default_value = 6; lace.inputs['Detail'].default_value = 10; lace.inputs['Roughness'].default_value = .7
    Lp.new(mpp.outputs['Vector'], lace.inputs['Vector'])
    near = Np.new('ShaderNodeSeparateXYZ'); Lp.new(tcp.outputs['Object'], near.inputs['Vector'])
    ny_ = Np.new('ShaderNodeMapRange'); ny_.inputs['From Min'].default_value = FAL.y - 40; ny_.inputs['From Max'].default_value = FAL.y + 8
    Lp.new(near.outputs['Y'], ny_.inputs['Value'])
    thr = Np.new('ShaderNodeMath'); thr.operation = 'SUBTRACT'; Lp.new(lace.outputs['Fac'], thr.inputs[0])
    inv = Np.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = .9; Lp.new(ny_.outputs['Result'], inv.inputs[1])
    inv2 = Np.new('ShaderNodeMath'); inv2.operation = 'MULTIPLY'; inv2.inputs[1].default_value = .8; Lp.new(inv.outputs['Value'], inv2.inputs[0])
    Lp.new(inv2.outputs['Value'], thr.inputs[1])
    fm = Np.new('ShaderNodeMapRange'); fm.inputs['From Min'].default_value = .45; fm.inputs['From Max'].default_value = .6
    Lp.new(thr.outputs['Value'], fm.inputs['Value'])
    mixc = Np.new('ShaderNodeMixRGB'); mixc.inputs['Color1'].default_value = (.035, .025, .012, 1); mixc.inputs['Color2'].default_value = (.85, .84, .8, 1)
    Lp.new(fm.outputs['Result'], mixc.inputs['Fac']); Lp.new(mixc.outputs['Color'], bp.inputs['Base Color'])
    rgh = Np.new('ShaderNodeMapRange'); rgh.inputs['To Min'].default_value = .15; rgh.inputs['To Max'].default_value = .7
    Lp.new(fm.outputs['Result'], rgh.inputs['Value']); Lp.new(rgh.outputs['Result'], bp.inputs['Roughness'])
    rng = np.random.default_rng(8)
    # rock buttresses breaking the curtain into wide veils, like the real ledge
    for k, a in enumerate((-A0 * .78, -A0 * .35, A0 * .12, A0 * .55, A0 * .9)):
        r = R + .3
        blob(f'LipRock{k}', T(r * math.sin(a), R - r * math.cos(a), -H * .55), (1.0 + .4 * k % 2, .9, H * .5), coll, rock, sub=2, rough=.35, seed=800 + k)
    # ---- spray: a soft mist hanging over the pool at the foot of the falls
    mist = bpy.data.materials.new('FallMist'); mist.use_nodes = True
    Nm = mist.node_tree.nodes; Nm.remove(Nm['Principled BSDF'])
    vol = Nm.new('ShaderNodeVolumePrincipled'); vol.inputs['Density'].default_value = .035; vol.inputs['Color'].default_value = (1, 1, 1, 1)
    gr = Nm.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
    tcm = Nm.new('ShaderNodeTexCoord'); mist.node_tree.links.new(tcm.outputs['Object'], gr.inputs['Vector'])
    mul = Nm.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = .06
    mist.node_tree.links.new(gr.outputs['Fac'], mul.inputs[0]); mist.node_tree.links.new(mul.outputs['Value'], vol.inputs['Density'])
    mist.node_tree.links.new(vol.outputs['Volume'], Nm['Material Output'].inputs['Volume'])
    for k, a in enumerate(np.linspace(-A0 * .85, A0 * .85, 6)):
        r = R + 2.5
        blob(f'FallMist{k}', T(r * math.sin(a), R - r * math.cos(a), -H + 1.2), (7.5, 4.5, 3.2), coll, mist, sub=2, seed=500 + k)
    # ---- where they stand: a flat limestone shelf at the pool's edge, boulders along the canyon walls
    slab = mat('Slab', (.3, .28, .24), rough=.8, haze=True); gravel = mat('Gravel', (.22, .2, .16), rough=.9, haze=True)
    box('JagalaShelfBase', (9, 9, .5), T(-12.5, -17, SHELF_Z - .52), gravel, coll).rotation_euler = (0, 0, .35)
    for i in range(26):
        sx_, sy_ = rng.uniform(-16.5, -8.5), rng.uniform(-21, -13)
        o = box(f'Slab{i}', (rng.uniform(.6, 1.8), rng.uniform(.5, 1.4), rng.uniform(.04, .1)), T(sx_, sy_, SHELF_Z - .05), slab, coll, bevel=.03)
        o.rotation_euler = (rng.normal(0, .02), rng.normal(0, .02), rng.uniform(0, PI))
    for i in range(160):
        blob(f'Pebble{i}', T(rng.uniform(-17, -8), rng.uniform(-21.5, -12.5), SHELF_Z - .01), (rng.uniform(.02, .07),) * 2 + (.02,), coll, slab, sub=1, seed=900 + i)
    film.mesh_obj('ShelfPuddle', [T(-15.6, -19.4, SHELF_Z + .005), T(-14.4, -19.9, SHELF_Z + .005), T(-14.2, -18.6, SHELF_Z + .005), T(-15.4, -18.2, SHELF_Z + .005)],
                  [(0, 1, 2, 3)], coll, [film.water_material('Puddle', color=(.05, .04, .03), rough=.05, wave=.02)])
    film.meadow('ShelfTufts', (FAL.x - 12.5, FAL.y - 17), (9, 9), coll, z_fn=lambda x, y: np.full_like(x, SHELF_Z + FAL.z - .02), density=.18, seed=41,
                keep_clear=[(FAL.x - 12.0, FAL.y - 16.0, 1.6)])
    rng = np.random.default_rng(81)
    for i in range(60):
        sx = -1 if i % 2 else 1; y = rng.uniform(-70, 10)
        x = sx * (13.5 + 8.5 * np.clip((y + 30) / 42, 0, 1) - rng.uniform(.3, 2.5))
        s_ = rng.uniform(.4, 1.6)
        blob(f'Boulder{i}', T(x, y, -H - .2), (s_ * rng.uniform(.8, 1.4), s_, s_ * .6), coll, rock, sub=2, rough=.35, seed=700 + i)


# ---------------------------------------------------------------- the ferry across the Gulf of Finland
FER = Vector((-3000.0, -3000.0, 0.0))


def _hull_material(name):
    """White topsides, a navy band along the waterline, red antifouling below."""
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.interpolation = 'CONSTANT'
    rp.color_ramp.elements[0].position = 0; rp.color_ramp.elements[0].color = (.3, .04, .03, 1)
    rp.color_ramp.elements[1].position = .42; rp.color_ramp.elements[1].color = (.03, .06, .16, 1)
    e = rp.color_ramp.elements.new(.6); e.color = (.86, .87, .88, 1)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -3; mr.inputs['From Max'].default_value = 7
    L.new(sep.outputs['Z'], mr.inputs['Value']); L.new(mr.outputs['Result'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .3; b.inputs['Coat Weight'].default_value = .3
    add_haze(m, N, L, b)
    return m


def build_ship(name, origin, coll, length=150.0, beam=26.0, rz=0.0):
    """A big white car ferry, bow toward +Y: a lofted hull, stacked decks with window bands, a funnel and lifeboats."""
    root = bpy.data.objects.new(name, None); link(root, coll); root.location = origin; root.rotation_euler = (0, 0, rz)
    hm = _hull_material(name + 'Hull')
    S = 34; verts = []; faces = []
    prof = [(1.0, 11.0), (1.0, 4.0), (.96, 0.0), (.8, -4.5), (.35, -6.5)]           # (half-width factor, z) down the side
    for i in range(S):
        s = i / (S - 1)
        wf = 1 - max(0.0, (s - .66) / .34) ** 1.8 * .985
        wf *= 1 - max(0.0, (.06 - s) / .06) * .08
        y = -length / 2 + s * length
        rise = 2.0 * max(0.0, (s - .8) / .2) ** 2                        # the bow rises a little
        for k, (f, z) in enumerate(prof):
            verts.append(((beam / 2) * wf * f, y, z + rise * (1 if z > 0 else .3)))
        for k, (f, z) in reversed(list(enumerate(prof))):
            verts.append((-(beam / 2) * wf * f, y, z + rise * (1 if z > 0 else .3)))
    P = 2 * len(prof)
    for i in range(S - 1):
        for k in range(P - 1):
            a = i * P + k; faces.append((a, a + 1, a + 1 + P, a + P))
    faces.append(tuple(range(P))[::-1])                              # transom
    faces.append(tuple((S - 1) * P + k for k in range(P)))            # stem
    hull = film.mesh_obj(name + 'HullMesh', verts, faces, coll, [hm]); hull.parent = root
    deckm = mat(name + 'Deck', (.55, .55, .52), rough=.7, haze=True)
    film.mesh_obj(name + 'DeckTop', [(-(beam / 2) * .98, -length / 2, 11), ((beam / 2) * .98, -length / 2, 11), ((beam / 2) * .3, length * .45, 12.5), (-(beam / 2) * .3, length * .45, 12.5)],
                  [(0, 1, 2, 3)], coll, [deckm]).parent = root
    white = mat(name + 'White', (.88, .89, .9), rough=.35, haze=True); glass = mat(name + 'Glass', (.02, .03, .05), rough=.05, haze=True)
    navy = mat(name + 'Navy', (.03, .06, .16), rough=.35, haze=True)
    z = 11.0
    for k, (L_, W_, y0) in enumerate(((length * .78, beam * .96, -length * .1), (length * .7, beam * .92, -length * .12), (length * .6, beam * .88, -length * .14),
                                      (length * .48, beam * .84, -length * .16), (length * .3, beam * .7, -length * .2))):
        o = box(f'{name}Deck{k}', (W_, L_, 2.9), (0, y0, z), white, coll, bevel=.3); o.parent = root
        g = box(f'{name}Win{k}', (W_ + .1, L_ * .94, 1.1), (0, y0, z + 1.1), glass, coll); g.parent = root
        z += 2.9
    br = box(f'{name}Bridge', (beam * .9, 5, 2.4), (0, -length * .2 + length * .16, z), white, coll, bevel=.2); br.parent = root
    bw = box(f'{name}BridgeWin', (beam * .9 + .1, 5.1, 1.0), (0, -length * .2 + length * .16, z + .9), glass, coll); bw.parent = root
    fun = box(f'{name}Funnel', (6, 10, 8), (0, -length * .3, z), white, coll, bevel=.8); fun.parent = root
    ft = box(f'{name}FunnelTop', (6.1, 10.1, 2.2), (0, -length * .3, z + 6), navy, coll, bevel=.6); ft.parent = root
    orange = mat(name + 'Lifeboat', (.9, .32, .04), rough=.4, haze=True)
    for sx in (-1, 1):
        for k in range(6):
            o = blob(f'{name}Boat{sx}{k}', (sx * beam * .5, -length * .25 + k * 9, 17.5), (1.4, 3.6, 1.2), coll, orange, sub=1, rough=.1, seed=k)
            o.parent = root
    return root


def build_ferry_sea(coll):
    """The gulf between Tallinn and Helsinki: open sea, the ferry with its wake, Tallinn's towers far behind, gulls."""
    T = lambda x, y, z: FER + Vector((x, y, z))
    sea = film.water_material('GulfSea', color=(.012, .025, .035), rough=.06, wave=.25, scale=.12)
    film.mesh_obj('GulfSea', [T(-4000, -4000, 0), T(4000, -4000, 0), T(4000, 4000, 0), T(-4000, 4000, 0)], [(0, 1, 2, 3)], coll, [sea])
    ship = build_ship('Ferry', T(0, 0, 0), coll)
    ship.keyframe_insert('location', frame=SHOTS['ferry']); ship.location.y += 22; ship.keyframe_insert('location', frame=SHOTS['deck'])
    for fcv in bears_fcurves(ship):
        for kp in fcv.keyframe_points:
            kp.interpolation = 'LINEAR'
    # wake: white water peeling off the bow and a churned trail behind
    foam = mat('WakeFoam', (.85, .87, .88), rough=.6, haze=True)
    rng = np.random.default_rng(14)
    for i in range(140):
        t = rng.uniform(0, 1); side = -1 if i % 2 else 1
        y = 75 - t * 260; x = side * (13 + t * 60 * rng.uniform(.8, 1.1)) if i % 3 else rng.normal(0, 6 + 10 * t)
        o = blob(f'Wake{i}', T(x, y if i % 3 else -75 - t * 200, .05), (rng.uniform(.8, 2.4), rng.uniform(1.5, 5), .05), coll, foam, sub=1, seed=i)
        o.parent = ship; o.matrix_parent_inverse = ship.matrix_world.inverted()
    # Tallinn far behind: a low coast with the old town's spires
    land = mat('FarCoast', (.12, .14, .12), rough=.9, haze=True); tower = mat('FarTower', (.35, .33, .3), rough=.8, haze=True)
    spire = mat('FarSpire', (.1, .16, .14), rough=.6, haze=True)
    blob('TallinnCoast', T(0, -2600, -10), (2400, 260, 28), coll, land, sub=3, rough=.2, seed=900)
    for i, (x, h) in enumerate(((-260, 40), (-120, 55), (-40, 120), (60, 70), (180, 45), (320, 38), (-400, 30), (480, 60))):
        cylinder(f'FarTower{i}', 9, h, T(x, -2420, 0), tower, coll, n=8)
        cylinder(f'FarSpire{i}', 10, h * .6, T(x, -2420, h), spire, coll, n=8, r2=.3)
    for i in range(14):
        cylinder(f'FarBlock{i}', rng.uniform(15, 30), rng.uniform(25, 70), T(rng.uniform(-900, 900), -2480, 0), tower, coll, n=4)
    # gulls following the ship, wings flapping
    gull = mat('SeaGull', (.92, .92, .92), rough=.6, haze=True)
    for i in range(10):
        g = blob(f'SeaGull{i}', T(rng.uniform(-30, 30), rng.uniform(-60, 40), rng.uniform(22, 36)), (.15, .35, .1), coll, gull, sub=1, seed=40 + i)
        wing = box(f'SeaGullWing{i}', (1.4, .25, .03), (0, 0, 0), gull, coll); wing.parent = g
        for f in range(SHOTS['ferry'], SHOTS['deck'], 6):
            wing.rotation_euler = (0, .45 if (f // 6 + i) % 2 else -.35, 0); wing.keyframe_insert('rotation_euler', frame=f)
        g.keyframe_insert('location', frame=SHOTS['ferry']); g.location.y += 24 + rng.uniform(-4, 4); g.location.x += rng.uniform(-6, 6)
        g.keyframe_insert('location', frame=SHOTS['deck'])


def bears_fcurves(ob):
    import bears
    return bears._fcurves(ob)


# ---------------------------------------------------------------- Tallinn old town
def cobble_material(name, color=(.24, .22, .2), scale=3.2):
    """Rounded granite setts with dark gaps between them."""
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = scale
    L.new(tc.outputs['Object'], vo.inputs['Vector'])
    vc = N.new('ShaderNodeTexVoronoi'); vc.inputs['Scale'].default_value = scale; L.new(tc.outputs['Object'], vc.inputs['Vector'])
    gap = N.new('ShaderNodeMapRange'); gap.inputs['From Min'].default_value = .02; gap.inputs['From Max'].default_value = .12
    L.new(vo.outputs['Distance'], gap.inputs['Value'])
    tint = N.new('ShaderNodeValToRGB'); tint.color_ramp.elements[0].color = (color[0] * .6, color[1] * .6, color[2] * .6, 1)
    tint.color_ramp.elements[1].color = (color[0] * 1.35, color[1] * 1.3, color[2] * 1.25, 1)
    L.new(vc.outputs['Color'], tint.inputs['Fac'])
    mul = N.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs['Fac'].default_value = 1
    L.new(tint.outputs['Color'], mul.inputs['Color1']); L.new(gap.outputs['Result'], mul.inputs['Color2'])
    L.new(mul.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .65
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .8; bump.inputs['Distance'].default_value = .05
    L.new(gap.outputs['Result'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    add_haze(m, N, L, b)
    return m


def build_tallinn(coll):
    """Tallinn's old town: a cobbled lane between tall, narrow merchant houses in pastel plaster, gable ends to the street
    (some stepped), white-framed windows, heavy doors, iron signs and lamps, flower boxes; at the end, the town hall's
    slender tower and St Olaf's green spire."""
    film.HAZE.update(color=(1, .88, .75), start=30.0, dist=250.0, strength=.45)
    T = lambda x, y, z: TAL + Vector((x, y, z))
    box('TalStreet', (8.2, 120, .02), T(0, 20, -.02), cobble_material('TalCobble'), coll)
    curb = mat('TalCurb', (.35, .33, .3), rough=.7, haze=True)
    for sx in (-1, 1):
        box(f'TalCurb{sx}', (.25, 120, .12), T(sx * 2.9, 20, 0), curb, coll)
        box(f'TalPavement{sx}', (1.0, 120, .1), T(sx * 3.5, 20, 0), mat('TalFlag', (.4, .38, .34), rough=.7, haze=True), coll)
    colors = [(.85, .65, .35), (.6, .75, .7), (.9, .85, .7), (.75, .45, .35), (.95, .8, .55), (.65, .7, .55), (.85, .55, .5), (.8, .78, .85)]
    roofm = mat('TalRoof', (.45, .12, .07), rough=.6, haze=True)
    frame = mat('TalFrame', (.9, .88, .82), rough=.5, haze=True); glassm = mat('TalGlass', (.04, .05, .06), rough=.05, haze=True)
    doorm = mat('TalDoor', (.22, .1, .05), rough=.6, haze=True); iron = mat('TalIron', (.03, .03, .03), rough=.5, metal=.6, haze=True)
    flower = mat('TalGeranium', (.7, .05, .06), rough=.6, haze=True); leaf = mat('TalLeaf', (.05, .14, .03), rough=.7, haze=True)
    import scene01_helsinki as s1
    importlib.reload(s1)
    rng = np.random.default_rng(10)
    for side in (-1, 1):
        y = -10; k = 0
        while y < 60:
            w = rng.uniform(4.5, 6.5); floors = int(rng.integers(3, 5)); fh = 2.7; h = floors * fh + .6
            col = colors[(k * 3 + (side > 0)) % len(colors)]
            wall = film.plaster_material(f'TalWall{side}{k}', col, grime=.35, scale=1.5) if hasattr(film, 'plaster_material') else mat(f'TalWall{side}{k}', col, rough=.8, haze=True)
            cy = y + w / 2; fx = side * 4.0
            box(f'TalHouse{side}{k}', (5, w - .12, h), T(side * 6.5, cy, 0), wall, coll)
            box(f'TalPlinth{side}{k}', (5.04, w - .1, .7), T(side * 6.5, cy, 0), mat('TalPlinth', (.3, .28, .25), rough=.8, haze=True), coll)
            # the gable end: plain triangle or stepped
            if rng.random() < .45:
                steps = 4
                for st in range(steps):
                    sw = (w - .12) * (1 - st / steps)
                    box(f'TalStep{side}{k}{st}', (5, sw, 3.6 / steps), T(side * 6.5, cy, h + st * 3.6 / steps), wall, coll)
                s1.prism(f'TalGable{side}{k}', w - .4, 3.4, 4.6, T(side * 6.7, cy, h), roofm, coll, rot_z=PI / 2)
            else:
                s1.prism(f'TalGable{side}{k}', w - .1, 3.6, 5, T(side * 6.5, cy, h), roofm, coll, rot_z=PI / 2)
                g = s1.prism(f'TalGableFace{side}{k}', w - .3, 3.3, .1, T(fx + side * .02, cy, h), wall, coll, rot_z=PI / 2)
            # a cornice between ground floor and the rest, and under the gable
            for zc in (fh + .6, h - .05):
                box(f'TalCornice{side}{k}{zc:.0f}', (.25, w - .1, .16), T(fx - side * .06, cy, zc), frame, coll)
            # windows: framed, with glazing bars; a door on the ground floor
            ncol = 2 if w < 5.5 else 3
            for f_ in range(1, floors):
                for c in range(ncol):
                    wy = y + w * (c + .5) / ncol; wz = .6 + f_ * fh + .55
                    box(f'TalWF{side}{k}{f_}{c}', (.1, .95, 1.4), T(fx - side * .01, wy, wz), frame, coll)
                    box(f'TalWG{side}{k}{f_}{c}', (.1, .75, 1.2), T(fx - side * .03, wy, wz + .1), glassm, coll)
                    box(f'TalWM{side}{k}{f_}{c}', (.1, .05, 1.2), T(fx - side * .05, wy, wz + .1), frame, coll)
                    box(f'TalWT{side}{k}{f_}{c}', (.1, .75, .05), T(fx - side * .05, wy, wz + .75), frame, coll)
                    if f_ == 1 and rng.random() < .5:
                        box(f'TalFlowerBox{side}{k}{c}', (.3, .8, .2), T(fx - side * .15, wy, wz - .25), doorm, coll)
                        for q in range(5):
                            blob(f'TalFl{side}{k}{c}{q}', T(fx - side * .2, wy - .32 + q * .16, wz - .02), (.09, .09, .08), coll, flower if q % 2 else leaf, sub=1, rough=.3, seed=q)
            dy = y + w * (.3 if k % 2 else .7)
            box(f'TalDoorF{side}{k}', (.12, 1.4, 2.4), T(fx - side * .01, dy, .1), frame, coll)
            box(f'TalDoor{side}{k}', (.12, 1.1, 2.2), T(fx - side * .04, dy, .1), doorm, coll)
            box(f'TalStepS{side}{k}', (.6, 1.6, .18), T(fx - side * .3, dy, 0), curb, coll)
            # ground-floor shop window on some houses, with an iron sign on a bracket
            if k % 3 == 1:
                sy_ = y + w * (.7 if k % 2 else .3)
                box(f'TalShop{side}{k}', (.1, 1.6, 1.6), T(fx - side * .02, sy_, .8), glassm, coll)
                box(f'TalBracket{side}{k}', (1.0, .04, .04), T(fx - side * .5, sy_, 3.1), iron, coll)
                box(f'TalSign{side}{k}', (.04, .7, .5), T(fx - side * .85, sy_, 2.55), mat(f'TalSignM{k}', colors[(k + 4) % len(colors)], rough=.5, haze=True), coll)
            # wall lamps
            if k % 2 == 0:
                box(f'TalLampArm{side}{k}', (.5, .04, .04), T(fx - side * .25, y + .3, 3.6), iron, coll)
                blob(f'TalLamp{side}{k}', T(fx - side * .5, y + .3, 3.35), (.12, .12, .2), coll, mat('TalLampGlass', (.9, .8, .6), rough=.2, haze=True), sub=1, rough=.1)
            y += w; k += 1
    # the end of the lane: the town hall's tower with its stacked spire, and St Olaf's tall green spire beyond
    stone = mat('TalTower', (.75, .7, .6), rough=.8, haze=True); green = mat('Spire', (.15, .3, .25), rough=.5, metal=.4, haze=True)
    box('TownHall', (16, 10, 12), T(0, 70, 0), stone, coll)
    for i in range(7):
        box(f'TownHallArch{i}', (2.0, .2, 3.2), T(-6 + i * 2, 64.95, 0), mat('TalArcade', (.15, .13, .11), rough=.8, haze=True), coll)
    s1.prism('TownHallRoof', 16.4, 4, 10.4, T(0, 70, 12), roofm, coll)
    cylinder('TownHallTower', 2.0, 26, T(5, 69, 0), stone, coll, n=8)
    cylinder('TownHallSpire1', 2.2, 4, T(5, 69, 26), green, coll, n=8, r2=1.2)
    cylinder('TownHallLantern', 1.2, 3, T(5, 69, 30), green, coll, n=8, r2=.9)
    cylinder('TownHallSpire2', 1.0, 6, T(5, 69, 33), green, coll, n=8, r2=.05)
    cylinder('FatMargaret', 3.2, 16, T(-14, 82, 0), stone, coll, n=24)
    cylinder('TowerCone', 3.6, 7, T(-14, 82, 16), roofm, coll, n=24, r2=.05)
    cylinder('OleviTower', 2.2, 30, T(10, 95, 0), stone, coll, n=8)
    cylinder('OleviSpire', 2.4, 22, T(10, 95, 30), green, coll, n=8, r2=.05)


# ---------------------------------------------------------------- berry picking
def build_berries(coll):
    film.HAZE.update(color=(.6, .7, .5), start=10.0, dist=120.0, strength=.5)
    floor = mat('ForestFloor', (.08, .07, .04), rough=.9, haze=True)
    T = lambda x, y, z: BER + Vector((x, y, z))
    xs = np.linspace(-40, 40, 81); X, Y = np.meshgrid(xs, xs)
    fl = film.grid_mesh('ForestFloor', X + BER.x, Y + BER.y, .2 * film.fbm(X / 5, Y / 5, 3), coll, floor)
    film.vgroup(fl, 'forest', (np.hypot(X, Y) > 4).astype(float).ravel())
    hi, lib = film.tree_library('BerryForest')
    film.scatter_instances(fl, lib, 'forest', 900, 14, seed=6)
    leaf = mat('BlueberryLeaf', (.05, .13, .04), rough=.6, haze=True); berry = mat('Blueberry', (.06, .07, .2), rough=.3, coat=.4)
    rng = np.random.default_rng(12)
    for i in range(70):
        x, y = rng.uniform(-3.5, 3.5), rng.uniform(-3.5, 3.5)
        blob(f'Bush{i}', T(x, y, .08), (rng.uniform(.18, .3), rng.uniform(.18, .3), .12), coll, leaf, sub=2, rough=.3, seed=i)
        for k in range(4):
            blob(f'Berry{i}{k}', T(x + rng.normal(0, .12), y + rng.normal(0, .12), .17), (.02,) * 3, coll, berry, sub=1)
    film.area_light('SunPatch', T(2, -3, 8), T(0, 0, 0), 2500, 3, (1, .9, .65))
    basket = mat('Basket', (.45, .3, .15), rough=.8)
    cylinder('Basket', .12, .14, T(.15, -.35, 0), basket, coll, n=14, r2=.15)
    for k in range(9):
        blob(f'BasketBerry{k}', T(.15 + rng.normal(0, .05), -.35 + rng.normal(0, .05), .14), (.02,) * 3, coll, berry, sub=1)


# ---------------------------------------------------------------- build
def build():
    bears = film.import_bears()
    import scene01_helsinki as s1, scene10_drive as s10
    importlib.reload(s1); importlib.reload(s10)
    w, sky, bg, ramp = film.make_sky(elev=25, az=-40, strength=.3, low=(1, .85, .7), mid=(1, .9, .85), high=(.75, .82, 1.0), aerosol=2)
    sun = film.make_sun(elev=25, az=-40, energy=2.6, color=(1, .9, .75))
    bpy.context.scene.view_settings.exposure = -.3
    for f, el, az, en, col in ((SHOTS['map'], 25, -40, 2.6, (1, .9, .75)), (SHOTS['palanga'], 12, -60, 2.8, (1, .8, .6)),
                               (SHOTS['falls'], 34, -20, 2.6, (1, .94, .84)), (SHOTS['tallinn'], 18, -50, 2.8, (1, .85, .65)),
                               (SHOTS['ferry'], 11, -70, 2.9, (1, .8, .58)), (SHOTS['deck'], 5, -80, 3.0, (1, .66, .4))):
        film.aim_sun(sun, el, az); sun.keyframe_insert('rotation_euler', frame=f)
        sun.data.energy = en; sun.data.color = col; sun.data.keyframe_insert('energy', frame=f); sun.data.keyframe_insert('color', frame=f)
        sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(180 - az)
        sky.keyframe_insert('sun_elevation', frame=f); sky.keyframe_insert('sun_rotation', frame=f)
    for idb in (sun, sun.data, w.node_tree):
        film._const(idb)
    build_map(film.new_coll('Map'))
    build_palanga(film.new_coll('Palanga'))
    lat = film.new_coll('Latvia'); land = s10.road_land(lat, length=300, seed=9)
    for o in lat.objects:
        if o.parent is None:
            o.location += LAT
    build_falls(film.new_coll('Waterfall'))
    build_tallinn(film.new_coll('Tallinn'))
    build_berries(film.new_coll('Berries'))
    build_ferry_sea(film.new_coll('Gulf'))
    film.HAZE.update(color=(.95, .6, .45), start=40.0, dist=320.0, strength=.45)
    hel = film.new_coll('Helsinki'); s1.build_cathedral(hel); s1.build_city(hel)
    for m in bpy.data.materials:
        if m.node_tree and 'Melt' in m.node_tree.nodes:
            m.node_tree.nodes['Melt'].outputs[0].default_value = 1.0
    for o in bpy.data.objects:
        if o.name.startswith(('Snowbank', 'Floe', 'Lamp0_icicle', 'HarbourRow', 'BareTree')):
            o.hide_render = True; o.hide_viewport = True                  # (open the view from the water to the cathedral)
    # the ferry's bow, arriving in Helsinki harbour: a pointed deck, white bulwarks and rails, bollards, a lifebuoy
    deck = mat('FerryDeck', (.42, .44, .42), rough=.7); railm = mat('FerryRail', (.85, .85, .85), rough=.4, metal=.5)
    hullw = mat('FerryBowHull', (.86, .87, .88), rough=.35, coat=.3, haze=True)
    FD = Vector((0, -175, 2.5))
    bow = [(-4, -6), (4, -6), (4, .5), (2.6, 3.0), (0, 4.6), (-2.6, 3.0), (-4, .5)]
    film.mesh_obj('FerryBowDeck', [FD + Vector((x, y, 0)) for x, y in bow], [tuple(range(len(bow)))], hel, [deck])
    n = len(bow)
    side = [FD + Vector((x, y, 0)) for x, y in bow] + [FD + Vector((x * 1.02, y, -4.6)) for x, y in bow] + [FD + Vector((x, y, .55)) for x, y in bow]
    faces = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(1, n)] + [(i + 2 * n, (i + 1) % n + 2 * n, (i + 1) % n, i) for i in range(1, n)]
    film.mesh_obj('FerryBowHull', side, faces, hel, [hullw])
    for i in range(1, n):
        a = Vector(bow[i]); b = Vector(bow[(i + 1) % n])
        L_ = (b - a).length; m_ = (a + b) / 2
        r = box(f'FerryRail{i}', (.07, L_, .07), FD + Vector((m_.x, m_.y, 1.0)), railm, hel)
        r.rotation_euler = (0, 0, math.atan2(-(b - a).x, (b - a).y))
        for k in range(int(L_ / .6) + 1):
            q = a.lerp(b, k / max(1, int(L_ / .6)))
            box(f'FerryPost{i}_{k}', (.035, .035, .45), FD + Vector((q.x, q.y, .55)), railm, hel)
    iron = mat('Bollard', (.05, .05, .055), rough=.4, metal=.7)
    for x, y in ((-2.2, -1.5), (2.2, -1.5)):
        cylinder(f'Bollard{x}', .14, .35, FD + Vector((x, y, 0)), iron, hel, n=14)
    buoy = bpy.data.objects.new('Lifebuoy', bpy.data.meshes.new('Lifebuoy')); link(buoy, hel)
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=.3, radius2=.3, depth=.08); bm.to_mesh(buoy.data); bm.free()
    buoy.data.materials.append(mat('LifebuoyOrange', (.9, .3, .05), rough=.4))
    buoy.location = FD + Vector((3.95, -2.5, .85)); buoy.rotation_euler = (0, PI / 2, 0)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    for ps in bpy.data.particles:              # in a montage the bears are small: lighter fur saves memory
        if ps.type == 'HAIR' and ps.render_type == 'PATH' and ps.child_type == 'INTERPOLATED' and ps.rendered_child_count > 20:
            ps.rendered_child_count = 14
    # map: bears away
    bears.place(he, 1, (5100, 0, 0), 0); bears.place(she, 1, (5102, 0, 0), 0)
    # Palanga: they walk along the water's edge, paw in paw
    p = SHOTS['palanga']
    bears.place(he, p, PAL + Vector((-.3, -1.6, -.18)), bears.facing(1, 0)); bears.place(she, p, PAL + Vector((-.3, -2.1, -.2)), bears.facing(1, 0))
    bears.walk(he, p + 2, SHOTS['latvia'] - 1, PAL + Vector((-.3, -1.6, -.18)), PAL + Vector((4.5, -1.6, -.18)), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)})
    bears.walk(she, p + 2, SHOTS['latvia'] - 1, PAL + Vector((-.3, -2.1, -.2)), PAL + Vector((4.5, -2.1, -.2)), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)}, phase=2)
    # Latvia: the car on the forest road
    c_ = film.car('RoadCar', LAT + Vector((1.0, 0, 0)), 0, film.new_coll('Car'), color=(.12, .2, .28), luggage=True)
    c_.keyframe_insert('location', frame=1)
    film.drive(c_, SHOTS['latvia'], SHOTS['falls'] - 1, LAT + Vector((1.0, 0, 0)), LAT + Vector((1.0, -40, 0)))
    # Jägala: paw in paw out onto the shelf by the pool; then they stand in the spray, she leans on him
    fa = SHOTS['falls']; f2 = SHOTS['falls2']
    dv = Vector((12.0, 26.0, 0)).normalized(); lv = Vector((-dv.y, dv.x, 0))           # toward the falls; the bears' left
    P1 = FAL + Vector((-12.0, -16.0, SHELF_Z)); P0 = P1 - dv * 2.4
    rz = bears.facing(dv.x, dv.y)
    bears.place(he, fa, P0 + lv * .3, rz); bears.place(she, fa, P0 - lv * .3, rz)
    bears.walk(he, fa + 18, f2 - 6, P0 + lv * .3, P1 + lv * .3, hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)})
    bears.walk(she, fa + 18, f2 - 6, P0 - lv * .3, P1 - lv * .3, hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)}, phase=2)
    # close: like the photo - they stand on the slabs with the falls behind them, facing the camera; his arm goes
    # around her, she turns and kisses his cheek, his eyes turn to hearts
    rb = bears.facing(-dv.x, -dv.y)
    bears.place(he, f2, P1 + lv * .3, rb); bears.place(she, f2, P1 - lv * .3, rb)
    arm_l = {'shoulder.L': (38, 0, 78), 'forearm.L': (58, 0, 0), 'spine': (2, 0, -3)}
    bears.key_pose(he, f2 + 16, arm_l); bears.key_pose(he, SHOTS['tallinn'] - 1, arm_l)
    bears.turn_head(she, f2 + 24, yaw=0, nod=-2); bears.turn_head(she, f2 + 36, yaw=-28, nod=0)
    kiss = {'head': (-4, -40, 12), 'spine': (4, 0, 8)}
    bears.key_pose(she, f2 + 46, kiss); bears.key_pose(she, f2 + 66, kiss); bears.set_eyes(she, 'closed', f2 + 44)
    bears.key_pose(she, f2 + 76, {'head': (0, -20, 4), 'spine': (2, 0, 3)}); bears.set_eyes(she, 'heart', f2 + 74)
    bears.set_eyes(he, 'heart', f2 + 50); bears.turn_head(he, f2 + 56, yaw=12, tilt=-6)
    lean = {'head': (2, -10, -16), 'spine': (4, 0, -7)}
    around = {'shoulder.R': (38, 0, -78), 'forearm.R': (58, 0, 0), 'spine': (2, 0, 4), 'head': (-4, 12, 6)}
    leafm = mat('AshLeaf', (.08, .2, .04), rough=.5, sss=.2, haze=True); twig = mat('AshTwig', (.12, .1, .07), rough=.8, haze=True)
    cpos = P1 - dv * 3.4 + Vector((0, 0, .75)); lrng = np.random.default_rng(33)
    for k in range(3):                                   # three twigs reaching in from the top of the frame, hung with leaflets
        a0 = cpos + dv * (1.0 + .3 * k) + lv * (1.4 - k * .9) + Vector((0, 0, 1.25 + .1 * k)); a1 = a0 - lv * 1.6 + dv * .4 - Vector((0, 0, .35))
        d = a1 - a0; tw = cylinder(f'AshTwig{k}', .012, d.length, a0, twig, film.new_coll('AshBranch') if k == 0 else bpy.data.collections['AshBranch'], n=6)
        tw.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        for j in range(26):
            q = a0.lerp(a1, j / 25) + Vector((lrng.normal(0, .05), lrng.normal(0, .05), -lrng.uniform(.02, .12)))
            lf = blob(f'AshLeaf{k}_{j}', q, (.09, .028, .006), bpy.data.collections['AshBranch'], leafm, sub=1, seed=j + 30 * k)
            lf.rotation_euler = (lrng.uniform(-.6, .6), lrng.uniform(-.4, .4), lrng.uniform(0, PI))
            film.key_visible(lf, 1, False); film.key_visible(lf, f2, True); film.key_visible(lf, SHOTS['tallinn'], False)
        film.key_visible(tw, 1, False); film.key_visible(tw, f2, True); film.key_visible(tw, SHOTS['tallinn'], False)
    # Tallinn: walking up the old street
    t = SHOTS['tallinn']
    bears.place(he, t, TAL + Vector((-.3, -2, 0)), PI); bears.place(she, t, TAL + Vector((.3, -2, 0)), PI)
    bears.walk(he, t + 2, SHOTS['berries'] - 1, TAL + Vector((-.3, -2, 0)), TAL + Vector((-.3, 1.8, 0)), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)})
    bears.walk(she, t + 2, SHOTS['berries'] - 1, TAL + Vector((.3, -2, 0)), TAL + Vector((.3, 1.8, 0)), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)}, phase=2)
    # berries: kneeling among the bushes, a basket between them
    bb = SHOTS['berries']
    kneel = {'thigh.L': (70, 0, -6), 'thigh.R': (70, 0, 6), 'shin.L': (-110, 0, 0), 'shin.R': (-110, 0, 0), 'spine': (25, 0, 0),
             'shoulder.L': (50, 0, 0), 'shoulder.R': (50, 0, 0), 'head': (20, 0, 0)}
    bears.place(he, bb, BER + Vector((-.45, 0, -bears.ground_drop(he, kneel))), bears.facing(.6, -1), pose=kneel); bears.place(she, bb, BER + Vector((.55, 0, -bears.ground_drop(she, kneel))), bears.facing(-.6, -1), pose=kneel)
    bears.set_eyes(she, 'heart', bb + 30); bears.set_eyes(she, 'open', bb + 55)
    for k, f in enumerate(range(bb + 8, SHOTS['ferry'] - 8, 14)):        # picking: reach into the bush, drop into the basket
        for b, o in ((he, 0), (she, 1)):
            reach = (k + o) % 2 == 0
            bears.key_pose(b, f + 3 * o, {'shoulder.L': (68 if reach else 42, 0, 6 if reach else 0), 'shoulder.R': (42 if reach else 68, 0, 0 if reach else -6),
                                          'head': (24 if reach else 16, 0, 0)})
    # the crossing: bears away (the ship is seen from far off)
    bears.place(he, SHOTS['ferry'], (5100, 0, 0), 0); bears.place(she, SHOTS['ferry'], (5102, 0, 0), 0)
    # at the bow: Helsinki ahead; she leans on him again, he points at the cathedral
    h = SHOTS['deck']
    bears.place(he, h, FD + Vector((-.3, 2.0, 0)), PI); bears.place(she, h, FD + Vector((.3, 2.0, 0)), PI)
    bears.turn_head(he, h + 10, nod=-6); bears.key_pose(he, h + 22, {'shoulder.L': (95, 0, 6), 'forearm.L': (8, 0, 0)})
    bears.key_pose(he, h + 44, {'shoulder.L': (95, 0, 6), 'forearm.L': (8, 0, 0)}); bears.key_pose(he, h + 56, {'shoulder.L': (0, 0, 0), 'forearm.L': (0, 0, 0)})
    bears.turn_head(she, h + 24, yaw=0, nod=-6); bears.set_eyes(she, 'heart', h + 34)
    bears.key_pose(she, h + 50, {'head': (2, -10, -16), 'spine': (4, 0, -7)}); bears.key_pose(she, SHOTS['end'], {'head': (2, -10, -16), 'spine': (4, 0, -7)})
    bears.key_pose(he, h + 60, around); bears.key_pose(he, SHOTS['end'], around)
    # ---- cameras
    mx = mapxy
    cams = [
        (SHOTS['map'], film.camera('Cam12_Map', [(1, mx(26, 53) + Vector((0, -4.5, 9)), mx(26, 54.5)), (SHOTS['palanga'] - 1, mx(25, 58) + Vector((0, -3.5, 7.5)), mx(25, 58.6))], lens=30)),
        (SHOTS['palanga'], film.camera('Cam12_Palanga', [(SHOTS['palanga'], PAL + Vector((1.5, -6.2, .9)), PAL + Vector((-.5, 8, 1.6))),
                                                          (SHOTS['latvia'] - 1, PAL + Vector((5.5, -6.0, .9)), PAL + Vector((3.5, 8, 1.6)))], lens=26, fstop=5.6, focus=4.5)),
        (SHOTS['latvia'], film.camera('Cam12_Latvia', [(SHOTS['latvia'], LAT + Vector((6, 6, 9)), LAT + Vector((1, -14, 0))), (SHOTS['falls'] - 1, LAT + Vector((5, -30, 12)), LAT + Vector((1, -50, 0)))], lens=26, fstop=8, focus=20.0)),
        (SHOTS['falls'], film.camera('Cam12_FallsWide', [(SHOTS['falls'], FAL + Vector((14, -48, 7)), FAL + Vector((-4.5, 4, -3.8))), (SHOTS['falls2'] - 1, FAL + Vector((6, -35, 2.5)), FAL + Vector((-5.5, 3, -4.8)))], lens=24, fstop=8, focus=30.0)),
        (SHOTS['falls2'], film.camera('Cam12_FallsClose', [(SHOTS['falls2'], P1 - dv * 3.6 + Vector((0, 0, .75)), P1 + dv * 6 + Vector((0, 0, 2.4))),
                                                          (SHOTS['tallinn'] - 1, P1 - dv * 3.1 + Vector((0, 0, .72)), P1 + dv * 6 + Vector((0, 0, 2.3)))], lens=22, fstop=5.6, focus=3.3)),
        (SHOTS['tallinn'], film.camera('Cam12_Tallinn', [(SHOTS['tallinn'], TAL + Vector((.4, -6.5, 1.1)), TAL + Vector((0, 40, 6))), (SHOTS['berries'] - 1, TAL + Vector((.3, -4.5, 1.2)), TAL + Vector((0, 40, 6)))], lens=24, fstop=8, focus=5.0)),
        (SHOTS['berries'], film.camera('Cam12_Berries', [(SHOTS['berries'], BER + Vector((.3, -3.4, 1.0)), BER + Vector((0, 0, .25))), (SHOTS['ferry'] - 1, BER + Vector((.2, -3.0, .95)), BER + Vector((0, 0, .25)))], lens=30, fstop=2.8, focus=2.0)),
        (SHOTS['ferry'], film.camera('Cam12_Gulf', [(SHOTS['ferry'], FER + Vector((70, 120, 5)), FER + Vector((0, 0, 10))), (SHOTS['deck'] - 1, FER + Vector((62, 128, 5.5)), FER + Vector((0, 15, 10)))], lens=30, fstop=8, focus=100.0)),
        (SHOTS['deck'], film.camera('Cam12_Ferry', [(SHOTS['deck'], FD + Vector((.05, -1.7, 1.9)), FD + Vector((0, 6, .6))), (SHOTS['end'], FD + Vector((.0, -1.1, 1.8)), FD + Vector((0, 6, .75)))], lens=26, fstop=8, focus=3.0)),
    ]
    for f, cam in cams:
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '12', still_frame=360)
