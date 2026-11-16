"""
Home - scene 5: ordinary evenings (song 1:28-1:44).
A balcony over the city at sunset; movies on the sofa; falling asleep together.
"Not because they were extraordinary." / "Because they felt like peace."

Shots:  1-130   their glazed balcony at sunset: two chairs, two mugs, the business park and the forest line below, the sky on fire
      131-260   evening on the sofa: a movie, the TV light flickering on their faces, a bowl of popcorn
      261-384   asleep on each other under the blanket, the film still playing; the camera drifts back
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

SHOTS = dict(a=1, b=131, c=261, end=384)
B = Vector((0.0, 0.0, 20.0))          # their glazed balcony, seven floors up, looking over the business park to the sunset
LR = Vector((400.0, 0.0, 0.0))        # the living room (its own little world, far from the city)


def balcony(coll):
    """Their glazed balcony high up (as in his photos): frameless glass panels with thin seams from the rail to the
    ceiling, a pale frame and posts, the dark ceiling overhead. Below: a business park - flat-roofed warehouses with
    skylights, wall lamps and lit signs, parking lots full of cars, a road curving away on the left with traffic,
    birches, then the dark spruce forest line, a chimney with a plume, and the sunset blazing over it all."""
    T = lambda x, y, z: Vector((B.x + x, B.y + y, B.z + z))
    plaster = mat('BalconyPlaster', (.78, .74, .68), rough=.8); ceil = mat('BalconyCeiling', (.12, .11, .1), rough=.9)
    frame = mat('GlazingFrame', (.82, .78, .7), rough=.4, metal=.2)
    glass = mat('BalconyGlass', (.75, .8, .82), rough=.02, transmission=1.0, alpha=.12)
    tile = mat('BalconyFloor', (.35, .32, .3), rough=.7)
    box('BalconySlab', (3.4, 1.7, .2), T(0, 0, -.2), tile, coll)
    box('BalconyCeil', (3.6, 1.9, .25), T(0, 0, 2.45), ceil, coll)
    box('HouseWall', (8, .3, 3.0), T(0, -1.0, -.2), plaster, coll)
    box('BalconyDoor', (.9, .05, 2.0), T(-1.0, -.84, 0), mat('DoorGlass', (.15, .2, .22), rough=.05, metal=.3), coll)
    box('DoorFrame', (1.0, .06, 2.1), T(-1.0, -.86, 0), frame, coll)
    for sx in (-1, 1):
        box(f'SideWall{sx}', (.2, 1.9, 2.5), T(sx * 1.8, 0, -.2), plaster, coll)
    # the front: a low rail with posts, then glass from the floor to the ceiling in narrow panels with thin seams
    box('ParapetRail', (3.4, .06, .06), T(0, .82, .95), frame, coll)
    box('ParapetBottom', (3.4, .08, .08), T(0, .82, 0), frame, coll)
    box('GlazingTop', (3.4, .08, .08), T(0, .84, 2.36), frame, coll)
    for i in range(7):
        box(f'ParapetPost{i}', (.05, .05, .95), T(-1.65 + i * .55, .82, 0), frame, coll)
    for i in range(6):
        x = -1.7 + .2 + i * .58
        box(f'GlassPanel{i}', (.56, .012, 2.32), T(x + .29 - .2, .86, .02), glass, coll)
        box(f'GlassSeam{i}', (.008, .02, 2.32), T(x - .2, .86, .02), mat('Seam', (.2, .22, .22), rough=.3), coll)
    # two chairs, a little table, mugs, a potted plant
    wood = mat('ChairWood', (.35, .2, .1), rough=.6); rail = mat('ChairMetal', (.05, .05, .05), rough=.4, metal=.7)
    for sx in (-1, 1):
        box(f'ChairSeat{sx}', (.5, .45, .04), T(sx * .4, -.05, .3), wood, coll)
        box(f'ChairBack{sx}', (.5, .04, .4), T(sx * .4, -.29, .3), wood, coll, rot=(-.15, 0, 0))
        for lx in (-.22, .22):
            for ly in (-.2, .18):
                box(f'ChairLeg{sx}{lx}{ly}', (.03, .03, .3), T(sx * .4 + lx, -.05 + ly, 0), rail, coll)
    cylinder('BalTable', .17, .02, T(0, .12, .4), wood, coll, n=20)
    cylinder('BalTableLeg', .02, .4, T(0, .12, 0), rail, coll, n=8)
    mug = mat('Mug2', (.85, .82, .75), rough=.3, coat=.5)
    for x in (-.06, .07):
        cylinder(f'BalMug{x}', .04, .08, T(x, .1, .42), mug, coll, n=14)
    pot = mat('TerraPot', (.5, .24, .12), rough=.8); leaf = mat('Geranium', (.05, .14, .04), rough=.6); red = mat('Bloom', (.8, .08, .1), rough=.5)
    cylinder('BalPot', .13, .22, T(1.45, .5, 0), pot, coll, n=14, r2=.16)
    for k in range(10):
        blob(f'BalLeaf{k}', T(1.45 + .1 * math.cos(k * 2.4), .5 + .1 * math.sin(k * 2.4), .27 + .02 * k), (.06, .06, .04), coll, leaf, sub=2, seed=k)
    for k in range(5):
        blob(f'BalBloom{k}', T(1.45 + .08 * math.cos(k * 1.3 + 1), .5 + .08 * math.sin(k * 1.3 + 1), .38 + .02 * k), (.03, .03, .03), coll, red, sub=1, seed=k)
    # ---- the view
    G = Vector((B.x, B.y, 0.0))                          # ground level below
    ground = mat('ParkGround', (.12, .12, .1), rough=.9, haze=True)
    xs = np.linspace(-1500, 1500, 121); ys = np.linspace(0, 2500, 101)
    X, Y = np.meshgrid(xs, ys)
    Z = 4 * film.fbm(X / 300, Y / 300, 3) * np.clip((Y - 300) / 300, 0, 1) - .1
    land = film.grid_mesh('ParkLand', X + G.x, Y + G.y, Z, coll, ground)
    film.vgroup(land, 'forest', ((Y > 420) & (film.fbm(X / 120, Y / 120, 3) > -.25)).astype(float).ravel())
    hi, lib = film.tree_library('ForestLine')
    film.scatter_instances(land, lib, 'forest', 9000, 16, seed=5)
    asphalt = mat('ParkAsphalt', (.06, .06, .065), rough=.6, haze=True); line = mat('ParkLine', (.8, .8, .78), rough=.6, haze=True)
    roofm = mat('WarehouseRoof', (.09, .09, .1), rough=.8, haze=True); sky_l = mat('Skylight', (.8, .82, .85), rough=.1, haze=True)
    walls = [mat('WarehouseWhite', (.75, .76, .78), rough=.6, haze=True), mat('WarehouseGrey', (.35, .36, .38), rough=.6, haze=True),
             mat('WarehouseDark', (.12, .13, .14), rough=.6, haze=True), mat('WarehouseBrick', (.45, .2, .15), rough=.8, haze=True)]
    lampm = emit_mat('WallLamp', (1, .85, .6), 25); signs = [emit_mat('SignBlue', (.2, .45, 1), 8), emit_mat('SignRed', (1, .15, .1), 8), emit_mat('SignWhite', (1, 1, 1), 6)]
    carm = [mat(f'Car{k}', c, rough=.25, coat=.6, haze=True) for k, c in enumerate(((.85, .85, .85), (.6, .62, .65), (.05, .05, .06), (.2, .25, .35), (.5, .1, .08)))]
    glassc = mat('CarGlass', (.03, .04, .05), rough=.05, haze=True)
    rng = np.random.default_rng(11)
    for i in range(34):                                  # the warehouses, rows of them toward the trees
        row = i // 7; x = -260 + (i % 7) * 85 + rng.uniform(-15, 15); y = 60 + row * 85 + rng.uniform(-10, 10)
        L_ = rng.uniform(45, 75); W_ = rng.uniform(25, 40); H_ = rng.uniform(8, 13)
        rz = rng.uniform(-.06, .06)
        wb = box(f'Warehouse{i}', (L_, W_, H_), G + Vector((x, y, 0)), walls[(i * 3) % 4] if i % 5 else walls[0], coll); wb.rotation_euler = (0, 0, rz)
        rf = box(f'WarehouseRoof{i}', (L_ + .4, W_ + .4, .4), G + Vector((x, y, H_)), roofm, coll); rf.rotation_euler = (0, 0, rz)
        for k in range(3):
            sl = box(f'Skylight{i}{k}', (L_ * .7, 1.2, .3), G + Vector((x, y - W_ * .25 + k * W_ * .25, H_ + .4)), sky_l, coll); sl.rotation_euler = (0, 0, rz)
        for k in range(int(L_ // 12)):
            blob(f'WallLamp{i}{k}', G + Vector((x - L_ / 2 + 6 + k * 12, y - W_ / 2 - .3, H_ * .6)), (.25, .15, .15), coll, lampm, sub=1, rough=0)
        if i % 4 == 1:
            box(f'Sign{i}', (rng.uniform(6, 12), .2, 1.6), G + Vector((x + rng.uniform(-10, 10), y - W_ / 2 - .25, H_ * .72)), signs[i % 3], coll)
        # its parking lot in front, lines and cars
        py = y - W_ / 2 - 14
        box(f'Lot{i}', (L_, 24, .05), G + Vector((x, py, 0)), asphalt, coll)
        for k in range(int(L_ // 3)):
            box(f'LotLine{i}{k}', (.12, 5, .02), G + Vector((x - L_ / 2 + 1.5 + k * 3, py - 4, .05)), line, coll)
            if rng.random() < .55:
                cx = x - L_ / 2 + 3 + k * 3; cy = py - 4 + rng.uniform(-.3, .3)
                cb = box(f'Car{i}_{k}', (1.8, 4.3, .8), G + Vector((cx, cy, .2)), carm[int(rng.integers(0, 5))], coll, bevel=.15)
                cg = box(f'CarTop{i}_{k}', (1.6, 2.2, .55), G + Vector((cx, cy + .2, 1.0)), glassc, coll, bevel=.15)
    # right below the balcony: a big white warehouse with its roof lights, and a full parking lot in front of it
    box('NearWarehouse', (70, 30, 11), G + Vector((25, 52, 0)), walls[0], coll)
    box('NearRoof', (70.4, 30.4, .4), G + Vector((25, 52, 11)), roofm, coll)
    for k in range(4):
        box(f'NearSky{k}', (50, 1.4, .3), G + Vector((25, 42 + k * 6, 11.4)), sky_l, coll)
    for k in range(6):
        blob(f'NearLamp{k}', G + Vector((-5 + k * 12, 36.7, 7)), (.3, .2, .2), coll, lampm, sub=1, rough=0)
    box('NearSign', (10, .2, 1.8), G + Vector((40, 36.7, 8.2)), signs[0], coll)
    box('NearLot', (90, 34, .05), G + Vector((10, 18, 0)), asphalt, coll)
    for r_ in range(2):
        for k in range(28):
            x = -30 + k * 3; y = 10 + r_ * 14
            box(f'NearLine{r_}{k}', (.12, 5, .02), G + Vector((x - 1.5, y, .05)), line, coll)
            if rng.random() < .7:
                cb = box(f'NearCar{r_}{k}', (1.8, 4.3, .8), G + Vector((x, y, .2)), carm[int(rng.integers(0, 5))], coll, bevel=.15)
                box(f'NearCarTop{r_}{k}', (1.6, 2.2, .55), G + Vector((x, y + .2, 1.0)), glassc, coll, bevel=.15)
    # the road curving away on the left, with street lamps and cars driving with their lights on
    def road(t):                                         # t 0..1, near-left to far
        return G + Vector((-330 - 120 * t + 90 * math.sin(t * 2.2), -40 + 900 * t, .1))
    head = emit_mat('Headlight', (1, .95, .85), 40); tail = emit_mat('Taillight', (1, .08, .05), 30)
    for i in range(120):
        t = i / 119; p = road(t); q = road(min(1, t + .009)); a = math.atan2(q.y - p.y, q.x - p.x)
        sg = box(f'Road{i}', (9, 8.5, .08), p, asphalt, coll); sg.rotation_euler = (0, 0, a - PI / 2)
        if i % 4 == 0:
            cylinder(f'StreetPole{i}', .12, 9, p + Vector((6, 0, 0)), mat('Pole', (.3, .3, .3), rough=.5, metal=.5, haze=True), coll, n=8)
            blob(f'StreetLamp{i}', p + Vector((5, 0, 9)), (.5, .3, .2), coll, lampm, sub=1, rough=0)
    for k in range(14):                                  # traffic both ways
        car = bpy.data.objects.new(f'Traffic{k}', None); link(car, coll)
        body = box(f'TrafficBody{k}', (1.8, 4.3, .9), (0, 0, .2), carm[k % 5], coll, bevel=.15); body.parent = car
        towards = k % 2 == 0
        lights = head if towards else tail
        for sx in (-.6, .6):
            l_ = blob(f'TrafficLight{k}{sx}', (sx, -2.2, .6), (.18, .08, .1), coll, lights, sub=1, rough=0); l_.parent = car
        t0 = (k / 14 + .03) % 1; lane = -2 if towards else 2
        for f in range(1, SHOTS['b'] + 1, 10):
            t = (t0 + (f / 24) * (.012 if towards else -.012)) % 1
            p = road(t); q = road(min(1, t + .005)); a = math.atan2(q.y - p.y, q.x - p.x)
            car.location = p + Vector((math.cos(a + PI / 2) * lane, math.sin(a + PI / 2) * lane, 0))
            car.rotation_euler = (0, 0, a - PI / 2 + (PI if towards else 0)); car.keyframe_insert('location', frame=f); car.keyframe_insert('rotation_euler', frame=f)
    # birches between the lots, distant buildings on the horizon, a chimney with its white plume
    for k in range(40):
        t_ = film.place_tree(coll, hi['birch'][k % len(hi['birch'])], G + Vector((rng.uniform(-420, 380), rng.uniform(20, 380), 0)), rng.uniform(9, 15), rng)
    farm_ = mat('FarBuilding', (.3, .3, .32), rough=.7, haze=True)
    for k in range(30):
        box(f'FarBlock{k}', (rng.uniform(20, 60), rng.uniform(15, 30), rng.uniform(10, 35)), G + Vector((rng.uniform(-1300, 1300), rng.uniform(1100, 2000), 0)), farm_, coll)
    cylinder('Chimney', 2.5, 70, G + Vector((-120, 1500, 0)), mat('ChimneyRed', (.5, .25, .2), rough=.7, haze=True), coll, n=16, r2=1.8)
    plume = mat('Plume', (1, .92, .85), rough=.9, alpha=.55, haze=True)
    for k in range(6):
        blob(f'Plume{k}', G + Vector((-120 + k * 9, 1500 + k * 3, 74 + k * 4)), (5 + k * 2.5, 5 + k * 2, 4 + k), coll, plume, sub=2, rough=.4, seed=700 + k)


def living_room(coll):
    T = lambda x, y, z: (LR.x + x, LR.y + y, LR.z + z)
    wall = mat('LRWall', (.5, .42, .36), rough=.85); floor = mat('LRFloor', (.2, .11, .05), rough=.45)
    box('LRFloor', (7, 7, .1), T(0, 0, -.1), floor, coll)
    box('LRBack', (7, .1, 2.4), T(0, 2.2, 0), wall, coll)
    box('LRSideL', (.1, 7, 2.4), T(-3.0, 0, 0), wall, coll); box('LRSideR', (.1, 7, 2.4), T(3.0, 0, 0), wall, coll)
    box('LRFront', (7, .1, 2.4), T(0, -3.4, 0), wall, coll)
    box('LRCeil', (7, 7, .1), T(0, 0, 2.4), wall, coll)
    rug = mat('Rug', (.45, .2, .15), rough=1.0)
    box('Rug', (2.6, 1.8, .015), T(0, -.6, 0), rug, coll)
    # the sofa (bears sit on it facing -Y, towards the TV)
    fabric = mat('SofaFabric', (.28, .33, .38), rough=.95, sss=.05)
    box('SofaBase', (2.0, .8, .32), T(0, 1.3, 0), fabric, coll, bevel=.05)
    box('SofaBack', (2.0, .25, .5), T(0, 1.65, .32), fabric, coll, bevel=.06)
    for sx in (-1, 1):
        box(f'SofaArm{sx}', (.22, .8, .55), T(sx * 1.1, 1.3, 0), fabric, coll, bevel=.06)
    for sx in (-1, 1):
        blob(f'SofaCushion{sx}', T(sx * .5, 1.25, .38), (.45, .36, .07), coll, fabric, sub=3, rough=.05, seed=sx + 3)
    knit = mat('Throw', (.62, .48, .36), rough=1.0)
    blob('Throw', T(0, 1.05, .5), (.7, .32, .1), coll, knit, sub=4, rough=.2, seed=7)
    # TV on a low stand, its screen changes colour with the film
    stand = mat('TVStand', (.12, .08, .05), rough=.5)
    box('TVStand', (1.6, .4, .4), T(0, -2.6, 0), stand, coll)
    box('TVBody', (1.3, .06, .76), T(0, -2.6, .42), mat('TVBlack', (.01, .01, .01), rough=.2), coll)
    scr_m = emit_mat('TVScreen', (.5, .6, .9), 6)
    box('TVScreen', (1.22, .01, .68), T(0, -2.565, .46), scr_m, coll)
    tvl = film.area_light('TVLight', T(0, -2.45, .8), T(0, 1.2, .5), 30, 1.2, (.5, .6, .9))
    em = scr_m.node_tree.nodes['Emission']
    rng = np.random.default_rng(9)
    palette = [(.45, .6, 1.0), (1.0, .7, .45), (.6, .9, .7), (.9, .5, .6), (.75, .8, 1.0), (1.0, .85, .6)]
    for f in range(SHOTS['b'] - 5, SHOTS['end'] + 1, 18):
        c = palette[rng.integers(len(palette))]; k = rng.uniform(.7, 1.2)
        em.inputs['Color'].default_value = (*c, 1); em.inputs['Strength'].default_value = 6 * k
        em.inputs['Color'].keyframe_insert('default_value', frame=f); em.inputs['Strength'].keyframe_insert('default_value', frame=f)
        tvl.data.color = c; tvl.data.energy = 30 * k
        tvl.data.keyframe_insert('color', frame=f); tvl.data.keyframe_insert('energy', frame=f)
    # a warm lamp and the popcorn
    film.point_light('LRLamp', T(1.6, 1.6, 1.3), 40, (1, .6, .3), .15)
    shade = mat('LRShade', (1, .8, .55), rough=.9, emission=(1, .6, .3), strength=3)
    cylinder('LRLampShade', .2, .25, T(1.6, 1.6, 1.2), shade, coll, n=20, r2=.13, cap=False)
    cylinder('LRLampPole', .015, 1.2, T(1.6, 1.6, 0), mat('Brass', (.6, .45, .25), rough=.3, metal=1), coll, n=8)
    bowl = mat('Bowl', (.75, .2, .15), rough=.3, coat=.5); corn = mat('Popcorn', (.95, .88, .65), rough=.8)
    cylinder('Bowl', .12, .08, T(0, 1.08, .58), bowl, coll, n=16, r2=.16)
    for i in range(30):
        a = rng.uniform(0, 2 * PI); r = rng.uniform(0, .12)
        blob(f'Corn{i}', T(math.cos(a) * r, 1.08 + math.sin(a) * r, .66 + rng.uniform(0, .04)), (.022, .022, .02), coll, corn, sub=1, rough=.3, seed=i)
    film.area_light('LRFill', T(0, -1.0, 2.2), T(0, 1.2, .5), 12, 2, (1, .7, .5))
    # a lived-in living room: plants, a coffee table with candles and books, a wall of pictures, a window with the dusk
    pot = mat('LRPot', (.55, .28, .15), rough=.8); leaf = mat('LRLeaf', (.04, .12, .03), rough=.6, sss=.1)
    rng = np.random.default_rng(21)
    for i, (x, y, h) in enumerate(((-2.4, 1.7, 1.2), (2.5, -2.6, .9), (-2.5, -2.4, .6))):
        cylinder(f'LRPlantPot{i}', .18, .3, T(x, y, 0), pot, coll, n=16, r2=.22)
        for k in range(14):
            a = rng.uniform(0, 6.3); r = rng.uniform(.05, .3)
            blob(f'LRPlantLeaf{i}{k}', T(x + math.cos(a) * r, y + math.sin(a) * r, .3 + rng.uniform(.1, h)), (.12, .05, .03), coll, leaf, sub=1, seed=k + i * 20)
    wood = mat('CoffeeTable', (.3, .17, .08), rough=.4)
    box('CoffeeTable', (1.0, .5, .04), T(0, -.2, .36), wood, coll)
    for x in (-.45, .45):
        for y in (-.4, 0):
            box(f'CTLeg{x}{y}', (.04, .04, .36), T(x, y, 0), wood, coll)
    for i, (c, h) in enumerate((((.7, .2, .15), .05), ((.15, .3, .45), .04), ((.8, .75, .6), .035))):
        box(f'CTBook{i}', (.24, .17, h), T(-.25, -.2, .4 + sum(x[1] for x in [(0, .05), (0, .04)][:i])), mat(f'CTBookM{i}', c, rough=.6), coll)
    flame = emit_mat('LRFlame', (1, .6, .25), 30); candle = mat('LRCandle', (.95, .9, .8), rough=.6)
    for i, x in enumerate((.15, .28, .4)):
        cylinder(f'LRCandle{i}', .03, .06 + .03 * i, T(x, -.15, .4), candle, coll, n=10)
        blob(f'LRFlame{i}', T(x, -.15, .48 + .03 * i), (.01, .01, .022), coll, flame, sub=1)
    film.point_light('LRCandleGlow', T(.28, -.15, .6), 10, (1, .6, .3), .05)
    for i, (x, z, w_, h_) in enumerate(((-.6, 1.55, .45, .35), (0, 1.6, .55, .45), (.6, 1.5, .4, .5), (-.3, 1.15, .3, .22), (.35, 1.1, .3, .25))):
        box(f'LRFrame{i}', (w_, .03, h_), T(x, 2.13, z), mat('LRPicFrame', (.6, .45, .25), rough=.4, metal=.5), coll)
        box(f'LRPic{i}', (w_ - .05, .03, h_ - .05), T(x, 2.12, z + .025), mat(f'LRPicM{i}', [(.5, .4, .3), (.3, .45, .55), (.6, .5, .35), (.4, .3, .4), (.35, .5, .35)][i], rough=.5), coll)
    knit2 = mat('Pillow2', (.65, .45, .2), rough=.95)
    for sx in (-1, 1):
        blob(f'SofaPillow{sx}', T(sx * .82, 1.45, .62), (.16, .1, .16), coll, knit2, sub=2, rough=.1, seed=sx + 30)
    # rug pattern: stripes
    m, N, L, b = film.node_mat('RugPattern')
    tcn = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 3; wv.inputs['Distortion'].default_value = 1
    L.new(tcn.outputs['Object'], wv.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.45, .18, .12, 1); rp.color_ramp.elements[1].color = (.75, .6, .4, 1)
    L.new(wv.outputs['Fac'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 1
    bpy.data.objects['Rug'].data.materials[0] = m


def build():
    bears = film.import_bears()
    # the sunset straight ahead over the forest line: a blazing orange-yellow band, pink and grey clouds above
    film.HAZE.update(color=(1, .62, .38), start=150.0, dist=1800.0, strength=.5)
    w, sky, bg, ramp = film.make_sky(elev=.6, az=178, strength=1.25, low=(1, .42, .06), mid=(1, .58, .42), high=(.55, .7, 1.0), aerosol=6,
                                     clouds=.55, cloud_tint=(1, .62, .55))
    sun = film.make_sun(elev=.6, az=178, energy=3.4, color=(1, .55, .22))
    bpy.context.scene.view_settings.exposure = .4
    bal = film.new_coll('Balcony'); balcony(bal)
    lr = film.new_coll('LivingRoom'); living_room(lr)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    # balcony: sitting on the chairs facing the city (+Y)
    bears.place(he, 1, (B.x - .4, B.y - .02, B.z + .34), PI, sitting=True)
    bears.place(she, 1, (B.x + .4, B.y - .02, B.z + .34), PI, sitting=True)
    bears.turn_head(she, 40, yaw=0); bears.turn_head(she, 64, yaw=30, nod=4); bears.turn_head(she, 100, yaw=28, nod=4); bears.turn_head(she, 118, yaw=6)
    bears.turn_head(he, 70, yaw=0); bears.turn_head(he, 90, yaw=-26, nod=2); bears.turn_head(he, 126, yaw=-24)
    bears.blink(he, 50); bears.blink(she, 110)
    # the sofa, the film (facing the TV = -Y)
    b_ = SHOTS['b']; seat = LR.z + .4
    bears.place(he, b_, (LR.x + .3, LR.y + 1.18, seat), 0, sitting=True, pose={'head': (-4, 0, 0)})
    bears.place(she, b_, (LR.x - .3, LR.y + 1.18, seat), 0, sitting=True, pose={'head': (-4, 0, 0), 'shoulder.R': (30, 0, -10)})
    bears.blink(she, b_ + 40); bears.blink(he, b_ + 70); bears.blink(she, b_ + 100)
    # falling asleep: heads sink onto each other
    c = SHOTS['c']
    bears.key_pose(she, c, {'head': (-4, 0, 0), 'spine': (6, 0, 0)}); bears.key_pose(he, c, {'head': (-4, 0, 0), 'spine': (6, 0, 0)})
    bears.key_pose(she, c + 50, {'head': (14, 12, -22), 'spine': (8, 0, -10)}); bears.key_pose(she, SHOTS['end'], {'head': (16, 12, -24), 'spine': (8, 0, -10)})
    bears.key_pose(he, c + 70, {'head': (12, -10, 18), 'spine': (6, 0, 6)}); bears.key_pose(he, SHOTS['end'], {'head': (14, -10, 20), 'spine': (6, 0, 6)})
    bears.set_eyes(she, 'closed', c + 30); bears.blink(he, c + 40); bears.set_eyes(he, 'closed', c + 62)
    # cameras
    A = film.camera('Cam5a_Balcony', [(SHOTS['a'], (B.x + .05, B.y - .84, B.z + 2.1), (B.x - .1, B.y + 20, B.z - 4.6)),
                                      (SHOTS['b'] - 1, (B.x + .0, B.y - .72, B.z + 2.0), (B.x - .1, B.y + 20, B.z - 4.8))], lens=17, fstop=5.6,
                    focus=(B.x, B.y, B.z + .5))
    Bc = film.camera('Cam5b_Movie', [(SHOTS['b'], (LR.x + .35, LR.y - 1.4, LR.z + .78), (LR.x, LR.y + 1.18, LR.z + .72)),
                                     (SHOTS['c'] - 1, (LR.x + .25, LR.y - 1.25, LR.z + .78), (LR.x, LR.y + 1.18, LR.z + .72))], lens=35, fstop=2.8,
                     focus=(LR.x, LR.y + 1.18, LR.z + .7))
    C = film.camera('Cam5c_Asleep', [(SHOTS['c'], (LR.x - .2, LR.y - .9, LR.z + .8), (LR.x, LR.y + 1.18, LR.z + .72)),
                                     (SHOTS['end'], (LR.x - .3, LR.y - 1.9, LR.z + .95), (LR.x, LR.y + 1.18, LR.z + .7))], lens=35, fstop=2.8,
                    focus=(LR.x, LR.y + 1.18, LR.z + .7))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], Bc), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '05', still_frame=200)
