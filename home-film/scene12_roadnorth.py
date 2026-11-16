"""
Home - scene 12: the road north, Kyiv -> Helsinki by car (song 3:34-4:04, the music at its strongest). A montage:

Shots:  1-96    a paper map: a dotted line grows from Kyiv north through Palanga, Riga, Estonia and Tallinn to Helsinki
       97-220   Palanga: a sandy Baltic beach below pine dunes; they walk along the water, paw in paw
      221-300   Latvia: the little car on a forest road
      301-420   Estonia: his parents' countryside farmhouse; his mum and dad wait at the door; hugs
      421-520   the big waterfall (Jagala): a wide curtain of water over a limestone ledge
      521-600   Tallinn old town: gabled houses and towers with red cone roofs
      601-660   berry picking in the forest, a few calm days
      661-720   by ferry into Helsinki: the white cathedral at golden hour
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

SHOTS = dict(map=1, palanga=97, latvia=221, estonia=301, falls=421, tallinn=521, berries=601, helsinki=661, end=720)
MAP = Vector((-3000.0, 0.0, 0.0)); PAL = Vector((3000.0, 0.0, 0.0)); LAT = Vector((0.0, -3000.0, 0.0))
EST = Vector((0.0, 3000.0, 0.0)); FAL = Vector((3000.0, 3000.0, 0.0)); TAL = Vector((-3000.0, 3000.0, 0.0)); BER = Vector((3000.0, -3000.0, 0.0))

# ---------------------------------------------------------------- the map
CITIES = [('Kyiv', 30.52, 50.45), ('Palanga', 21.07, 55.92), ('Riga', 24.11, 56.95), ('Estonia', 26.0, 58.6),
          ('Tallinn', 24.75, 59.44), ('Helsinki', 24.94, 60.17)]
# a rough Baltic coastline (lon, lat) for a hand-drawn look
SEA = [(10.5, 54.3), (12.5, 54.4), (14.2, 53.9), (16.5, 54.6), (18.6, 54.8), (19.6, 54.4), (21.0, 55.3), (21.1, 56.1), (21.0, 57.0),
       (21.6, 57.6), (22.6, 57.75), (23.4, 57.1), (24.1, 57.0), (24.4, 57.3), (24.3, 58.3), (23.5, 58.7), (23.4, 59.2), (24.2, 59.45),
       (25.5, 59.6), (27.2, 59.45), (28.1, 59.5), (29.9, 59.9), (28.5, 60.4), (27.0, 60.5), (25.5, 60.3), (24.0, 60.0), (22.9, 59.85),
       (22.3, 60.4), (21.4, 60.8), (21.3, 61.8), (21.5, 63.0), (22.5, 64.0), (23.0, 66.0), (20.0, 66.0), (17.5, 62.5), (18.0, 60.3),
       (18.8, 59.3), (16.6, 57.0), (16.2, 56.2), (14.3, 55.5), (12.8, 56.2), (10.5, 56.0)]


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
        t = link(bpy.data.objects.new('Label' + name, cu), coll); t.location = p + Vector((.15, .05, .004))
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
def build_farm(coll):
    film.HAZE.update(color=(1, .9, .75), start=40.0, dist=400.0, strength=.4)
    grass = mat('Meadow', (.1, .2, .04), rough=.9, haze=True)
    xs = np.linspace(-120, 120, 121); ys = np.linspace(-120, 120, 121)
    X, Y = np.meshgrid(xs, ys); Z = 2.5 * film.fbm(X / 60, Y / 60, 3) * np.clip((np.hypot(X, Y) - 12) / 30, 0, 1)
    meadow = film.grid_mesh('Meadow', X + EST.x, Y + EST.y, Z, coll, grass)
    film.vgroup(meadow, 'forest', ((np.hypot(X, Y) > 40) & (film.fbm(X / 40, Y / 40, 3) > -.05)).astype(float).ravel())
    hi, lib = film.tree_library('FarmForest')
    film.scatter_instances(meadow, lib, 'forest', 3500, 13, seed=4)
    # the house: ochre-red wooden walls, white window frames, a steep grey roof, a porch
    wall = mat('FarmWall', (.22, .04, .018), rough=.8, haze=True); trim = mat('FarmTrim', (.85, .84, .8), rough=.6, haze=True)
    roof = mat('FarmRoof', (.2, .2, .22), rough=.6, metal=.3, haze=True); win = mat('FarmWin', (.05, .06, .07), rough=.1, haze=True)
    T = lambda x, y, z: EST + Vector((x, y, z))
    box('FarmHouse', (9, 6, 3.2), T(0, 6, 0), wall, coll)
    import scene01_helsinki as s1
    importlib.reload(s1)
    s1.prism('FarmRoofP', 9.8, 3.4, 6.8, T(0, 6, 3.2), roof, coll)
    for x in (-3, -1.2, 2.2, 3.6):
        box(f'FarmWin{x}', (.9, .1, 1.1), T(x, 2.96, 1.2), win, coll)
        box(f'FarmWinFrame{x}', (1.05, .08, 1.25), T(x, 2.98, 1.12), trim, coll)
    box('FarmDoor', (1.1, .1, 2.1), T(.5, 2.96, 0), mat('FarmDoorM', (.25, .15, .08), rough=.6), coll)
    box('Porch', (3.2, 1.6, .25), T(.5, 2.2, 0), mat('PorchWood', (.4, .3, .2), rough=.7), coll)
    film.meadow('FarmMeadow', (EST.x, EST.y - 3), (16, 14), coll, density=.9, seed=12, keep_clear=[(EST.x + .5, EST.y - 2, 1.2)])
    flowers = mat('Lupin', (.14, .05, .45), rough=.6)
    rng = np.random.default_rng(6)
    for i in range(40):
        blob(f'Lupin{i}', T(rng.uniform(-6, 6), rng.uniform(-3, 1.5), .3), (.06, .06, .3), coll, flowers, sub=1, seed=i)


# ---------------------------------------------------------------- the waterfall
def build_falls(coll):
    film.HAZE.update(color=(.85, .9, .95), start=40.0, dist=300.0, strength=.3)
    lime = mat('Limestone', (.22, .19, .15), rough=.8, haze=True)
    T = lambda x, y, z: FAL + Vector((x, y, z))
    box('UpperLedge', (60, 30, 3), T(0, 16, -3), lime, coll)
    box('LowerBank', (60, 20, .5), T(0, -22, -3.5), lime, coll)
    water = film.water_material('Pool', color=(.03, .03, .02), rough=.3, wave=.5)
    film.mesh_obj('Pool', [T(-60, -12, -3.2), T(60, -12, -3.2), T(60, 2, -3.2), T(-60, 2, -3.2)], [(0, 1, 2, 3)], coll, [water])
    film.mesh_obj('River', [T(-60, 1, -.05), T(60, 1, -.05), T(60, 30, -.05), T(-60, 30, -.05)], [(0, 1, 2, 3)], coll, [water])
    # the falling curtain: a curved sheet with streaky white water that runs downward
    fall = bpy.data.materials.new('Fall'); fall.use_nodes = True
    N, L = fall.node_tree.nodes, fall.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6, 6, .6)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    fc = mp.inputs['Location'].driver_add('default_value', 2); fc.driver.expression = 'frame * 0.06'
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; nz.inputs['Detail'].default_value = 6
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.35, .32, .25, 1); rp.color_ramp.elements[1].color = (.95, .95, .92, 1)
    rp.color_ramp.elements[0].position = .4; L.new(nz.outputs['Fac'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .3; b.inputs['Emission Color'].default_value = (1, 1, 1, 1); b.inputs['Emission Strength'].default_value = .12
    xs = np.linspace(-14, 14, 81); zs = np.linspace(-3.2, 0, 13)
    X, Zz = np.meshgrid(xs, zs); Y = 1.0 - .25 * ((Zz + 3.2) / 3.2 - 1) ** 2 * 0 + (1 - (Zz + 3.2) / 3.2) * -.6
    film.grid_mesh('Curtain', X + FAL.x, Y + FAL.y, Zz + FAL.z, coll, fall)
    # the cliff face beside the falls, and pines along the top
    for sx in (-1, 1):
        box(f'LedgeFace{sx}', (25, .8, 3.2), T(sx * 26.5, .7, -3.2), lime, coll)
    box('LedgeBehind', (30, .4, 3.2), T(0, 1.45, -3.2), mat('WetRock', (.06, .055, .05), rough=.4, haze=True), coll)
    pines = [m for m in bpy.data.meshes if m.name.startswith('ScotsPine') and 'Lo' not in m.name]
    spr = [m for m in bpy.data.meshes if m.name.startswith('Spruce') and 'Lo' not in m.name]
    trng = np.random.default_rng(21)
    for k in range(46):
        x = trng.uniform(-40, 40); y = trng.uniform(4, 30)
        film.place_tree(coll, (pines + spr)[k % max(1, len(pines + spr))], T(x, y, -.05), trng.uniform(9, 14), trng, name=f'FallTree{k}')
    foam = mat('FallFoam', (.85, .87, .88), rough=.5, haze=True)
    rng = np.random.default_rng(8)
    for i in range(40):
        blob(f'FallFoam{i}', T(rng.uniform(-13, 13), .2 + rng.uniform(-1.5, .2), -3.2), (rng.uniform(.6, 1.6), rng.uniform(.3, .8), .08), coll, foam, sub=2, seed=i)


# ---------------------------------------------------------------- Tallinn old town
def build_tallinn(coll):
    film.HAZE.update(color=(1, .88, .75), start=30.0, dist=250.0, strength=.45)
    cob = mat('TalCobble', (.25, .23, .21), rough=.7, haze=True)
    T = lambda x, y, z: TAL + Vector((x, y, z))
    box('TalStreet', (8, 120, .02), T(0, 20, -.02), cob, coll)
    colors = [(.85, .65, .35), (.6, .75, .7), (.9, .85, .7), (.75, .45, .35), (.95, .8, .55), (.65, .7, .55), (.85, .55, .5)]
    roofm = mat('TalRoof', (.45, .12, .07), rough=.6, haze=True); win = mat('TalWin', (.05, .05, .06), rough=.1, haze=True)
    import scene01_helsinki as s1
    importlib.reload(s1)
    rng = np.random.default_rng(10)
    for side in (-1, 1):
        y = -10
        k = 0
        while y < 60:
            w = rng.uniform(4, 6); h = rng.uniform(7, 10)
            wall = mat(f'TalWall{side}{k}', colors[(k * 3 + (side > 0)) % len(colors)], rough=.8, haze=True)
            box(f'TalHouse{side}{k}', (5, w - .1, h), T(side * 6.5, y + w / 2, 0), wall, coll)
            g = s1.prism(f'TalGable{side}{k}', w - .1, 3.2, 5, T(side * 6.5, y + w / 2, h), roofm, coll, rot_z=PI / 2)
            for r in range(3):
                for c in range(2):
                    box(f'TalWin{side}{k}{r}{c}', (.1, .7, 1.0), T(side * 3.95, y + w * (.3 + .4 * c), 1.5 + r * 2.4), win, coll)
            y += w; k += 1
    tower = mat('TalTower', (.75, .7, .6), rough=.8, haze=True)
    cylinder('FatMargaret', 3.2, 16, T(-3, 72, 0), tower, coll, n=24)
    c = cylinder('TowerCone', 3.6, 7, T(-3, 72, 16), roofm, coll, n=24, r2=.05)
    cylinder('OleviTower', 2.2, 30, T(10, 95, 0), tower, coll, n=8)
    cylinder('OleviSpire', 2.4, 22, T(10, 95, 30), mat('Spire', (.15, .3, .25), rough=.5, metal=.4, haze=True), coll, n=8, r2=.05)


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
                               (SHOTS['estonia'], 30, -30, 2.6, (1, .92, .8)), (SHOTS['tallinn'], 18, -50, 2.8, (1, .85, .65)),
                               (SHOTS['helsinki'], 5, -80, 3.0, (1, .66, .4))):
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
    build_farm(film.new_coll('Farm'))
    build_falls(film.new_coll('Waterfall'))
    build_tallinn(film.new_coll('Tallinn'))
    build_berries(film.new_coll('Berries'))
    film.HAZE.update(color=(.95, .6, .45), start=40.0, dist=320.0, strength=.45)
    hel = film.new_coll('Helsinki'); s1.build_cathedral(hel); s1.build_city(hel)
    for m in bpy.data.materials:
        if m.node_tree and 'Melt' in m.node_tree.nodes:
            m.node_tree.nodes['Melt'].outputs[0].default_value = 1.0
    for o in bpy.data.objects:
        if o.name.startswith(('Snowbank', 'Floe', 'Lamp0_icicle', 'HarbourRow', 'BareTree')):
            o.hide_render = True; o.hide_viewport = True                  # (open the view from the water to the cathedral)
    # a ferry deck arriving at the harbour
    deck = mat('FerryDeck', (.75, .75, .72), rough=.6); railm = mat('FerryRail', (.85, .85, .85), rough=.4, metal=.5)
    FD = Vector((0, -175, 2.5))
    box('FerryDeck', (8, 6, .3), FD + Vector((0, 0, -.3)), deck, hel)
    box('FerryRail', (8, .06, .06), FD + Vector((0, 2.9, .75)), railm, hel)
    for i in range(16):
        box(f'FerryPost{i}', (.04, .04, .75), FD + Vector((-4 + i * .53, 2.9, 0)), railm, hel)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    dad = bears.build_bear('he', name='Dad', overrides={'fur': '#5d4a3c', 'light': '#a8957f', 'size': 1.05, 'bodyW': 1.08})
    mum = bears.build_bear('she', name='Mum', overrides={'fur': '#8a6a52', 'light': '#cdb59a', 'size': .97, 'acc': 'none', 'cheekAlpha': .1})
    for b in (dad, mum):
        bears.place(b, 1, (5000, 0, 0), 0)
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
    film.drive(c_, SHOTS['latvia'], SHOTS['estonia'] - 1, LAT + Vector((1.0, 0, 0)), LAT + Vector((1.0, -40, 0)))
    # Estonia: his parents wait at the door; the two arrive; hugs
    e = SHOTS['estonia']
    bears.place(dad, e, EST + Vector((1.0, 2.2, .25)), 0); bears.place(mum, e, EST + Vector((.0, 2.2, .25)), 0)
    bears.place(he, e, EST + Vector((.2, -2.0, 0)), bears.facing(0, 1)); bears.place(she, e, EST + Vector((.8, -2.0, 0)), bears.facing(0, 1))
    bears.walk(he, e + 2, e + 64, EST + Vector((.2, -2.0, 0)), EST + Vector((.25, 1.2, .1)))
    bears.walk(she, e + 2, e + 64, EST + Vector((.8, -2.0, 0)), EST + Vector((.85, 1.2, .1)), phase=2)
    hug = {'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0)}
    for b in (dad, mum):
        bears.key_pose(b, e + 50, {'shoulder.L': (0, 0, 0), 'shoulder.R': (0, 0, 0)}); bears.key_pose(b, e + 74, dict(hug, head=(0, 25, -8)))
    bears.key_pose(he, e + 76, dict(hug, head=(0, 25, -8))); bears.key_pose(she, e + 76, dict(hug, head=(0, 25, -8)))
    for k, b in enumerate((he, mum, she, dad)):
        bears.hug_sway(b, e + 80, SHOTS['falls'] - 1, dict(hug, head=(0, 25, -8)), phase=.5 * (k % 2))
    bears.set_eyes(mum, 'heart', e + 64); bears.set_eyes(dad, 'closed', e + 70)
    # the waterfall: they stand on the bank and watch
    fa = SHOTS['falls']
    bears.place(he, fa, FAL + Vector((-.3, -14, -3.0)), PI); bears.place(she, fa, FAL + Vector((.3, -14, -3.0)), PI)
    bears.turn_head(she, fa + 40, yaw=0); bears.turn_head(she, fa + 60, yaw=30, nod=-4)
    # Tallinn: walking up the old street
    t = SHOTS['tallinn']
    bears.place(he, t, TAL + Vector((-.3, -2, 0)), PI); bears.place(she, t, TAL + Vector((.3, -2, 0)), PI)
    bears.walk(he, t + 2, SHOTS['berries'] - 1, TAL + Vector((-.3, -2, 0)), TAL + Vector((-.3, 1.8, 0)), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)})
    bears.walk(she, t + 2, SHOTS['berries'] - 1, TAL + Vector((.3, -2, 0)), TAL + Vector((.3, 1.8, 0)), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)}, phase=2)
    # berries: kneeling among the bushes, a basket between them
    bb = SHOTS['berries']
    kneel = {'thigh.L': (70, 0, -6), 'thigh.R': (70, 0, 6), 'shin.L': (-110, 0, 0), 'shin.R': (-110, 0, 0), 'spine': (25, 0, 0),
             'shoulder.L': (50, 0, 0), 'shoulder.R': (50, 0, 0), 'head': (20, 0, 0)}
    bears.place(he, bb, BER + Vector((-.45, 0, -.12)), bears.facing(.6, -1), pose=kneel); bears.place(she, bb, BER + Vector((.55, 0, -.12)), bears.facing(-.6, -1), pose=kneel)
    bears.set_eyes(she, 'heart', bb + 30); bears.set_eyes(she, 'open', bb + 55)
    for k, f in enumerate(range(bb + 8, SHOTS['helsinki'] - 8, 14)):        # picking: reach into the bush, drop into the basket
        for b, o in ((he, 0), (she, 1)):
            reach = (k + o) % 2 == 0
            bears.key_pose(b, f + 3 * o, {'shoulder.L': (68 if reach else 42, 0, 6 if reach else 0), 'shoulder.R': (42 if reach else 68, 0, 0 if reach else -6),
                                          'head': (24 if reach else 16, 0, 0)})
    # Helsinki by ferry: at the rail, looking at the city
    h = SHOTS['helsinki']
    bears.place(he, h, FD + Vector((-.3, 2.4, 0)), PI); bears.place(she, h, FD + Vector((.3, 2.4, 0)), PI)
    bears.turn_head(she, h + 20, yaw=0); bears.turn_head(she, h + 40, yaw=28, tilt=-10)
    # ---- cameras
    mx = mapxy
    cams = [
        (SHOTS['map'], film.camera('Cam12_Map', [(1, mx(26, 53) + Vector((0, -4.5, 9)), mx(26, 54.5)), (SHOTS['palanga'] - 1, mx(25, 58) + Vector((0, -3.5, 7.5)), mx(25, 58.6))], lens=30)),
        (SHOTS['palanga'], film.camera('Cam12_Palanga', [(SHOTS['palanga'], PAL + Vector((1.5, -6.2, .9)), PAL + Vector((-.5, 8, 1.6))),
                                                          (SHOTS['latvia'] - 1, PAL + Vector((5.5, -6.0, .9)), PAL + Vector((3.5, 8, 1.6)))], lens=26, fstop=5.6, focus=4.5)),
        (SHOTS['latvia'], film.camera('Cam12_Latvia', [(SHOTS['latvia'], LAT + Vector((6, 6, 9)), LAT + Vector((1, -14, 0))), (SHOTS['estonia'] - 1, LAT + Vector((5, -30, 12)), LAT + Vector((1, -50, 0)))], lens=26, fstop=8, focus=20.0)),
        (SHOTS['estonia'], film.camera('Cam12_Farm', [(SHOTS['estonia'], EST + Vector((5.5, -6.5, 1.8)), EST + Vector((.5, 2, 1.2))), (SHOTS['falls'] - 1, EST + Vector((4.5, -5.0, 1.6)), EST + Vector((.5, 2, 1.1)))], lens=24, fstop=5.6, focus=6.0)),
        (SHOTS['falls'], film.camera('Cam12_Falls', [(SHOTS['falls'], FAL + Vector((1.2, -18.2, -1.7)), FAL + Vector((-.5, 0, -1.4))), (SHOTS['tallinn'] - 1, FAL + Vector((.8, -17.4, -1.8)), FAL + Vector((-.5, 0, -1.5)))], lens=22, fstop=8, focus=6.0)),
        (SHOTS['tallinn'], film.camera('Cam12_Tallinn', [(SHOTS['tallinn'], TAL + Vector((.4, -6.5, 1.1)), TAL + Vector((0, 40, 6))), (SHOTS['berries'] - 1, TAL + Vector((.3, -4.5, 1.2)), TAL + Vector((0, 40, 6)))], lens=24, fstop=8, focus=5.0)),
        (SHOTS['berries'], film.camera('Cam12_Berries', [(SHOTS['berries'], BER + Vector((.3, -2.2, .7)), BER + Vector((0, 0, .25))), (SHOTS['helsinki'] - 1, BER + Vector((.2, -1.9, .65)), BER + Vector((0, 0, .25)))], lens=35, fstop=2.8, focus=2.0)),
        (SHOTS['helsinki'], film.camera('Cam12_Ferry', [(SHOTS['helsinki'], FD + Vector((.5, -.8, 1.6)), Vector((0, 40, 20))), (SHOTS['end'], FD + Vector((.3, -.2, 1.5)), Vector((0, 40, 20)))], lens=26, fstop=8, focus=3.0)),
    ]
    for f, cam in cams:
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '12', still_frame=360)
