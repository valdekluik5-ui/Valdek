"""
Home - scene 14: the Rainbow Bridge, Kyiv (song 4:35-4:47 - the sudden quiet break, then the peak begins).
Evening, after dark, on the hill above the Dnipro: the glass bridge across the wooded ravine leads to the great steel
arch, lit in rainbow bands. Below: the wide river, Trukhaniv island, the lit towers of the left bank and the bridges.
He kneels with the ring; she says yes.

Shots:  1-96    on the glass bridge, walking toward the glowing arch; the city lights spread out to the right
       97-200   close, side-on: he kneels and opens a little box; the ring catches the light; the river below
      201-288   yes - heart eyes, a hug, the rainbow arch glowing behind them
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
from mathutils import Vector, Matrix

SHOTS = dict(a=1, b=97, c=201, end=288)
DECK = 45.0                       # the hill top (plaza and bridge deck) above the river
ARCH = (28.0, -24.0, DECK)        # the arch's centre at plaza level, out on a spur of the hill; its plane faces the river (-Y)
BRIDGE = (-120.0, -12.0)          # the glass bridge runs along X from the far side of the ravine to the plaza
RAVINE = -66.0                    # where the ravine runs down to the river, under the bridge


def lit_windows_material(name, warm=(1, .72, .38), lit=.45, strength=2.2, scale=(1.0, 1.0, 1.0)):
    """Building faces at night: a grid of windows (brick texture: 'mortar' = dark wall), a random share of them lit
    in warm or cool white."""
    m, N, L, b = node_mat(name)
    b.inputs['Base Color'].default_value = (.02, .02, .025, 1); b.inputs['Roughness'].default_value = .6
    tc = N.new('ShaderNodeTexCoord'); sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; L.new(sp.outputs['X'], ad.inputs[0]); L.new(sp.outputs['Y'], ad.inputs[1])
    cb = N.new('ShaderNodeCombineXYZ'); L.new(ad.outputs['Value'], cb.inputs['X']); L.new(sp.outputs['Z'], cb.inputs['Y'])   # facade plane: (along, up)
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = scale
    L.new(cb.outputs['Vector'], mp.inputs['Vector'])
    br = N.new('ShaderNodeTexBrick'); br.offset = 0; br.squash = 1
    br.inputs['Scale'].default_value = .33; br.inputs['Mortar Size'].default_value = .12; br.inputs['Brick Width'].default_value = .5
    br.inputs['Row Height'].default_value = .25
    br.inputs['Color1'].default_value = (*warm, 1); br.inputs['Color2'].default_value = (0, 0, 0, 1); br.inputs['Mortar'].default_value = (0, 0, 0, 1)
    L.new(mp.outputs['Vector'], br.inputs['Vector'])
    # which windows are on: white noise per brick cell via a second, coarse brick texture's colour variation
    on = N.new('ShaderNodeTexBrick'); on.offset = 0; on.squash = 1
    for k in ('Scale', 'Mortar Size', 'Brick Width', 'Row Height'):
        on.inputs[k].default_value = br.inputs[k].default_value
    on.inputs['Mortar Size'].default_value = 0; on.inputs['Color1'].default_value = (1, 1, 1, 1); on.inputs['Color2'].default_value = (0, 0, 0, 1)
    on.inputs['Bias'].default_value = lit * 2 - 1
    L.new(mp.outputs['Vector'], on.inputs['Vector'])
    cut = N.new('ShaderNodeMath'); cut.operation = 'GREATER_THAN'; cut.inputs[1].default_value = .5
    sepc = N.new('ShaderNodeSeparateColor'); L.new(on.outputs['Color'], sepc.inputs['Color']); L.new(sepc.outputs[0], cut.inputs[0])
    mul = N.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs['Fac'].default_value = 1
    L.new(br.outputs['Color'], mul.inputs['Color1']); L.new(cut.outputs['Value'], mul.inputs['Color2'])
    L.new(mul.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = strength
    add_haze(m, N, L, b)
    return m


def arch(coll):
    """The arch above the Dnipro (Kyiv's 'rainbow arch'): a 50 m stainless-steel half ring on the hill, facing the river,
    lit at night with bands of rainbow light along its face."""
    steel = mat('ArchSteel', (.62, .63, .66), rough=.22, metal=1.0, haze=True)
    C = Vector(ARCH)
    R0, w, depth = 25.0, 2.6, 1.7
    n = 120
    V, F = [], []
    for i in range(n + 1):
        a = PI * i / n
        for r, y in ((R0, -depth / 2), (R0 + w, -depth / 2), (R0 + w, depth / 2), (R0, depth / 2)):
            V.append(C + Vector((math.cos(a) * r, y, math.sin(a) * r)))
    for i in range(n):
        o = i * 4; p = o + 4
        for k in range(4):
            F.append((o + k, o + (k + 1) % 4, p + (k + 1) % 4, p + k))
    film.mesh_obj('ArchRibbon', V, F, coll, [steel], smooth=True)
    bands = [(1, .05, .04), (1, .35, .02), (1, .85, .08), (.1, .9, .2), (.05, .35, 1), (.5, .1, .9)]
    for side in (-1, 1):
        for k, col in enumerate(bands):
            m = emit_mat(f'ArchLED{k}', col, 2.2)
            r1 = R0 + .15 + k * (w - .3) / 6; r2 = r1 + (w - .3) / 6 * .8
            V2, F2 = [], []
            for i in range(n + 1):
                a = PI * i / n
                for r in (r1, r2):
                    V2.append(C + Vector((math.cos(a) * r, side * (depth / 2 + .02), math.sin(a) * r)))
            for i in range(n):
                o = 2 * i; F2.append((o, o + 1, o + 3, o + 2))
            film.mesh_obj(f'ArchLEDs{side}{k}', V2, F2, coll, [m])
    # the rainbow light spilling onto the plaza and the hill
    for k, col in enumerate(((1, .2, .1), (1, .8, .1), (.1, .8, .3), (.2, .3, 1))):
        film.point_light(f'ArchGlow{k}', C + Vector((-18 + k * 12, -4, 6 + 10 * math.sin(PI * (k + .5) / 4))), 3000, col, 3)
    # the plaza under it: granite slabs, steps, lamps
    gran = mat('Granite', (.16, .15, .15), rough=.5, haze=True)
    box('ArchPlaza', (90, 44, 30), C + Vector((0, 8, -30)), gran, coll)
    stone_rail = mat('TerraceParapet', (.22, .21, .2), rough=.6, haze=True)
    box('TerraceParapet', (90, .5, 1.0), C + Vector((0, -13.75, 0)), stone_rail, coll)       # the parapet along the river side
    lampm = emit_mat('PlazaLamp', (1, .85, .62), 18)
    pole = mat('LampPole', (.05, .05, .055), rough=.4, metal=.6, haze=True)
    for i in range(10):
        x = C.x - 40 + i * 9
        cylinder(f'PlazaPole{i}', .07, 4.2, (x, C.y - 14, C.z), pole, coll, n=8)
        blob(f'PlazaLampG{i}', (x, C.y - 14, C.z + 4.3), (.22, .22, .22), coll, lampm, sub=1, rough=0)


def bridge(coll):
    """The glass bridge: a slender steel bridge from the arch plaza across the wooded ravine. Wooden deck with glass
    panels let into it, glass balustrades with a wooden handrail, LED strips glowing under the rail, curved steel girders."""
    wood = mat('DeckWood', (.32, .2, .1), rough=.55, haze=True)
    m, N, L, b = node_mat('DeckPlanks')
    tc = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.bands_direction = 'X'; wv.inputs['Scale'].default_value = 4.5
    wv.inputs['Distortion'].default_value = .6; L.new(tc.outputs['Object'], wv.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (.12, .07, .035, 1); rp.color_ramp.elements[1].color = (.36, .22, .11, 1)
    L.new(wv.outputs['Fac'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .5
    add_haze(m, N, L, b)
    glass = mat('BridgeGlass', (.55, .7, .75), rough=.02, transmission=1.0, alpha=.3, haze=True)
    floorglow = emit_mat('GlassFloorGlow', (.5, .8, 1.0), 1.4)
    steel = mat('BridgeSteel', (.55, .56, .6), rough=.3, metal=.9, haze=True)
    led = emit_mat('RailLED', (1, .82, .55), 8.0)
    x0, x1 = BRIDGE
    span = x1 - x0
    nseg = 60
    zc = deck_z
    for i in range(nseg):
        xa = x0 + span * i / nseg; xb = x0 + span * (i + 1) / nseg; xm = (xa + xb) / 2
        z = zc(xm); ang = math.atan2(zc(xb) - zc(xa), xb - xa)
        d = box(f'Deck{i}', (xb - xa + .02, 4.0, .25), (xm, 0, z - .25), m, coll); d.rotation_euler = (0, -ang, 0)
        if i % 3 == 1:                          # the glass panels in the floor, lit from below
            g = box(f'GlassFloor{i}', (xb - xa - .4, 1.2, .02), (xm, 0, z + .005), glass, coll); g.rotation_euler = (0, -ang, 0)
            gg = box(f'GlassFloorLight{i}', (xb - xa - .4, 1.2, .02), (xm, 0, z - .2), floorglow, coll); gg.rotation_euler = (0, -ang, 0)
        for sy in (-1, 1):
            p = box(f'GlassWall{i}{sy}', (xb - xa, .025, 1.05), (xm, sy * 1.95, z), glass, coll); p.rotation_euler = (0, -ang, 0)
            r = box(f'Handrail{i}{sy}', (xb - xa + .02, .14, .06), (xm, sy * 1.95, z + 1.08), wood, coll); r.rotation_euler = (0, -ang, 0)
            l_ = box(f'RailLED{i}{sy}', (xb - xa + .02, .05, .015), (xm, sy * 1.88, z + 1.065), led, coll); l_.rotation_euler = (0, -ang, 0)
            if i % 2 == 0:
                cylinder(f'Post{i}{sy}', .03, 1.08, (xa, sy * 1.97, zc(xa)), steel, coll, n=6)
    # the two curved girders underneath, deepest in the middle, and slim legs down into the ravine
    for sy in (-1, 1):
        V, F = [], []
        for i in range(nseg + 1):
            x = x0 + span * i / nseg; t = (x - x0) / span
            depth = .6 + 2.2 * math.sin(PI * t)
            V += [(x, sy * 1.7, zc(x) - .3), (x, sy * 1.7, zc(x) - .3 - depth), (x, sy * 1.3, zc(x) - .3 - depth), (x, sy * 1.3, zc(x) - .3)]
        for i in range(nseg):
            o = i * 4; p = o + 4
            for k in range(4):
                F.append((o + k, o + (k + 1) % 4, p + (k + 1) % 4, p + k))
        film.mesh_obj(f'Girder{sy}', V, F, coll, [steel])
    for k, x in enumerate((x0 + span * .3, x0 + span * .7)):
        for sy in (-1, 1):
            cylinder(f'Leg{k}{sy}', .35, zc(x) - 3.4 - ground_z(x, 0) + 1, (x, sy * 1.5, ground_z(x, 0) - 1), steel, coll, n=12)


def deck_z(x):
    """Height of the bridge deck: a gentle rise toward the middle."""
    x0, x1 = BRIDGE
    return DECK + 1.2 * math.sin(PI * min(1.0, max(0.0, (x - x0) / (x1 - x0))))


def ground_z(x, y):
    """The right bank: a plateau at deck height, a steep wooded slope down to the river toward -Y, and the ravine the
    bridge crosses (running down to the river)."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    plateau = DECK - .5 + 1.5 * film.fbm(x / 40, y / 40, 3)
    t = np.clip((y + 75) / 60, 0, 1); slope = t * t * (3 - 2 * t)
    z = -1.0 + (plateau + 1) * slope
    rav = np.exp(-((x - RAVINE) / 22) ** 2) * np.clip((y + 90) / 40, 0, 1)
    z = z - rav * (z - 9 - .06 * (y + 60))
    return z


def river_city(coll):
    """Evening on the Dnipro: the wide river below reflecting the lights, Trukhaniv island dark in the middle, the left
    bank's towers with lit windows, the bridges strung with lamps, the embankment roads."""
    river = film.water_material('Dnipro', color=(.004, .007, .012), rough=.035, wave=.12, scale=.08)
    film.mesh_obj('River', [(-5000, -5000, 0), (5000, -5000, 0), (5000, 400, 0), (-5000, 400, 0)], [(0, 1, 2, 3)], coll, [river])
    # the right bank (where they are): the hill, its slope and the ravine, wooded
    hill = mat('KyivHill', (.03, .05, .02), rough=.9, haze=True)
    xs = np.arange(-260, 260.1, 2.0); ys = np.arange(-110, 160.1, 2.0)
    X, Y = np.meshgrid(xs, ys); Z = ground_z(X, Y)
    land = film.grid_mesh('RightBank', X, Y, Z, coll, hill)
    plaza = (np.abs(X - ARCH[0]) < 48) & (Y > ARCH[1] - 20) & (Y < ARCH[1] + 24)
    # trees only down the slope and in the ravine (well below the deck, so the view stays open), and far behind
    forest = ((Z > 3) & (Z < DECK - 9) & (Y < -12)) | ((np.abs(X - RAVINE) < 26) & (Z < DECK - 12) & (np.abs(Y) > 5)) | ((Y > 50) & ~plaza)
    film.vgroup(land, 'forest', forest.astype(float).ravel())
    hi, lib = film.tree_library('KyivTrees')
    film.scatter_instances(land, lib, 'forest', 5000, 13, seed=14)
    # the road down the ravine, under the bridge, with its orange lamps
    asphalt = mat('RavineRoad', (.03, .03, .03), rough=.5, haze=True)
    sodium = emit_mat('Sodium', (1, .55, .2), 25)
    for i in range(30):
        y = -100 + i * 8
        z = float(ground_z(RAVINE, y))
        box(f'RavineRoad{i}', (7, 8.2, .1), (RAVINE, y, z + .1), asphalt, coll)
        if i % 2 == 0:
            blob(f'RavineLamp{i}', (RAVINE + 4.5, y, z + 6), (.18, .18, .12), coll, sodium, sub=1, rough=0)
    # the right-bank embankment road along the water
    for i in range(80):
        blob(f'RightEmbLamp{i}', (-1000 + i * 25, -88, 7), (.25, .25, .25), coll, sodium, sub=1, rough=0)
    box('RightEmbankment', (2200, 14, 1.2), (0, -88, 0), asphalt, coll)
    # Trukhaniv island: low, dark, wooded, a few path lamps
    isle = mat('Trukhaniv', (.01, .018, .01), rough=.9, haze=True)
    blob('Trukhaniv', (120, -420, -2.5), (520, 130, 6), coll, isle, sub=3, rough=.25, seed=51)
    path = emit_mat('IslandPath', (1, .9, .7), 12)
    rng = np.random.default_rng(40)
    for i in range(40):
        blob(f'IslandLamp{i}', (rng.uniform(-300, 500), rng.uniform(-470, -380), 4.5), (.3, .3, .3), coll, path, sub=1, rough=0)
    # the left bank: rows of tall residential blocks with lit windows, their lights doubled in the river
    rng = np.random.default_rng(7)
    wins = [lit_windows_material(f'Windows{k}', warm=c, lit=l) for k, (c, l) in enumerate((((1, .72, .38), .42), ((1, .85, .6), .35), ((.85, .9, 1), .3), ((1, .65, .3), .5)))]
    k = 0
    for row, (y0, n_, hmin, hmax) in enumerate(((-900, 70, 30, 75), (-1050, 70, 40, 95), (-1250, 60, 50, 120), (-1500, 50, 40, 100))):
        for i in range(n_):
            x = -1800 + i * (3600 / n_) + rng.uniform(-15, 15)
            w_ = rng.uniform(18, 34); d_ = rng.uniform(14, 22); h = rng.uniform(hmin, hmax)
            o = box(f'Tower{k}', (w_, d_, h), (x, y0 + rng.uniform(-30, 30), 0), wins[k % 4], coll)
            o.rotation_euler = (0, 0, rng.uniform(-.15, .15))
            if rng.random() < .25:
                blob(f'TowerBeacon{k}', (x, o.location.y, h + 1), (.6, .6, .6), coll, emit_mat('Beacon', (1, .1, .05), 30), sub=1, rough=0)
            k += 1
    box('LeftBank', (5000, 1500, 3), (0, -1600, -1.5), mat('LeftBankGround', (.02, .02, .02), rough=.9, haze=True), coll)
    for i in range(140):
        blob(f'LeftEmbLamp{i}', (-1800 + i * 26, -860, 6), (.3, .3, .3), coll, sodium, sub=1, rough=0)
    # the bridges across the river, strung with lamps: the metro bridge (south) and the park bridge to the island
    conc = mat('BridgeConcrete', (.15, .15, .15), rough=.7, haze=True)
    white = emit_mat('BridgeLamps', (1, .95, .85), 30)
    for name, x, z, y1, n_ in (('MetroBridge', -620, 14, -880, 60), ('ParkBridge', 330, 9, -300, 24)):
        box(name, (16 if name == 'MetroBridge' else 6, -y1 - 60, 1.6), (x, (y1 - 60) / 2, z - 1.6), conc, coll)
        for i in range(n_):
            y = -60 + (y1 + 60) * i / (n_ - 1)
            for sx in (-1, 1):
                blob(f'{name}Lamp{i}{sx}', (x + sx * (7 if name == 'MetroBridge' else 2.6), y, z + 3), (.3, .3, .3), coll, white, sub=1, rough=0)
        for i in range(6 if name == 'MetroBridge' else 3):
            y = -60 + (y1 + 60) * (i + .5) / (6 if name == 'MetroBridge' else 3)
            box(f'{name}Pier{i}', (8, 6, z), (x, y, 0), conc, coll)
    # golden domes of the Lavra far off to the south, floodlit
    gold = mat('GoldDome', (1, .7, .3), rough=.2, metal=1, haze=True); wall = mat('ChurchWhite', (.85, .84, .8), rough=.6, haze=True)
    for i, (x, y) in enumerate(((-1300, 40), (-1380, 90))):
        z = 40
        box(f'Church{i}', (24, 24, 30), (x, y, z), wall, coll)
        cylinder(f'ChurchDrum{i}', 7, 10, (x, y, z + 30), wall, coll, n=20)
        film.dome(f'ChurchDome{i}', 8, (x, y, z + 40), gold, coll, zscale=1.5)
        film.point_light(f'Floodlight{i}', (x + 30, y - 40, z + 20), 2e5, (1, .85, .6), 5)


def build():
    bears = film.import_bears()
    # evening, after sunset: a deep blue sky with the last glow low behind them, moonlight, the city lit below
    film.HAZE.update(color=(.03, .045, .08), start=150.0, dist=4000.0, strength=.25)
    w, sky, bg, ramp = film.make_sky(elev=-3, az=180, strength=.3, low=(.9, .45, .3), mid=(.3, .35, .6), high=(.12, .16, .35), clouds=.25,
                                     cloud_tint=(.5, .5, .6))
    sun = film.make_sun(elev=35, az=30, energy=.18, color=(.55, .65, 1.0))
    bpy.context.scene.view_settings.exposure = .2
    st = film.new_coll('Kyiv'); river_city(st); bridge(st); arch(st)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    bx = -40.0
    DZ = deck_z(bx)
    film.area_light('ProposalFill', (bx + 1.4, 1.6, DZ + 1.9), (bx, 0, DZ + .5), 160, 1.6, (1, .72, .5))
    film.area_light('FaceFill', (bx - 2.6, 1.0, DZ + 1.5), (bx, 0, DZ + .6), 110, 1.6, (1, .78, .58))     # warm light on their faces and the ring
    film.area_light('MoonRim', (bx - 3, 3, DZ + 4), (bx, 0, DZ + .6), 40, 3, (.6, .7, 1.0))                  # a cool rim from behind
    # walking out onto the bridge under the arch, then stopping at the middle
    bears.place(he, 1, (bx - 4.3, -.35, DZ), bears.facing(1, 0)); bears.place(she, 1, (bx - 4.3, .35, DZ), bears.facing(1, 0))
    bears.walk(he, 2, 80, (bx - 4.3, -.35, DZ), (bx - .4, -.35, DZ), hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)})
    bears.walk(she, 2, 80, (bx - 4.3, .35, DZ), (bx - .4, .35, DZ), hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)}, phase=2)
    # he steps in front of her and kneels; she turns to him
    b_ = SHOTS['b']
    bears.place(she, b_, (bx, .35, DZ), bears.facing(0, -1))
    # on one knee: the left leg forward (thigh level), the right knee down behind; both paws hold the box out to her
    # (plush legs are short, so a one-knee kneel barely lowers him: down on both knees, sitting back on his heels)
    kneel = {'thigh.L': (70, 0, -6), 'shin.L': (-110, 0, 0), 'thigh.R': (70, 0, 6), 'shin.R': (-110, 0, 0), 'spine': (14, 0, 0),
             'shoulder.L': (82, 0, 18), 'shoulder.R': (82, 0, -18), 'forearm.L': (20, 0, 0), 'forearm.R': (20, 0, 0), 'head': (-18, 0, 0)}
    bears.place(he, b_, (bx, -.45, DZ), bears.facing(0, 1))
    bears.key_pose(he, b_ + 26, kneel)
    bears.hold(he, b_ + 6); he.location.z = DZ - bears.ground_drop(he, kneel); he.location.y = -.5; bears.hold(he, b_ + 26)
    bears.turn_head(she, b_ + 10, nod=6); bears.turn_head(she, b_ + 40, nod=18)
    bears.key_pose(she, b_ + 50, {'shoulder.L': (0, 0, 0), 'shoulder.R': (0, 0, 0)})
    bears.key_pose(she, b_ + 66, {'shoulder.L': (95, 0, -20), 'shoulder.R': (95, 0, 20), 'forearm.L': (60, 0, 0), 'forearm.R': (60, 0, 0)})   # paws to her mouth
    # the ring box in his paws
    velvet = mat('RingBox', (.4, .02, .06), rough=.8); gold = mat('RingGold', (1, .78, .4), rough=.12, metal=1)
    stone = mat('Diamond', (1, 1, 1), rough=0, transmission=1.0)
    rb = film.new_coll('Ring')
    boxo = box('RingBoxBase', (.08, .08, .05), (0, 0, 0), velvet, rb, bevel=.008)
    lid = box('RingBoxLid', (.08, .08, .02), (0, .04, .05), velvet, rb, bevel=.006); lid.parent = boxo
    ring = film.cylinder('Ring', .022, .006, (0, 0, .045), gold, rb, n=24); ring.rotation_euler = (PI / 2, 0, 0); ring.parent = boxo
    gem = blob('RingStone', (0, 0, .072), (.008, .008, .008), rb, stone, sub=2, rough=0); gem.parent = boxo
    film.attach_to_paw(boxo, he, 'forearm.R', (.05, .06, -.05), (PI / 2, 0, 0))
    film.key_visible(boxo, 1, False); film.key_visible(boxo, b_ + 24, True)
    for f, a in ((b_ + 40, 0), (b_ + 54, -1.9)):
        lid.rotation_euler = (a, 0, 0); lid.keyframe_insert('rotation_euler', frame=f)
    lid.location = (0, .04, .05)
    sparkle = film.point_light('RingSparkle', (0, 0, 0), 0, (1, .9, .7), .01)
    sparkle.parent = boxo; sparkle.location = (0, 0, .1)
    for f, e in ((b_ + 54, 0), (b_ + 60, 2.0), (b_ + 66, .4), (b_ + 74, 1.6), (SHOTS['c'], .6)):
        sparkle.data.energy = e; sparkle.data.keyframe_insert('energy', frame=f)
    # yes: she nods, heart eyes; he stands; a hug
    c = SHOTS['c']
    bears.turn_head(she, c, nod=-6); bears.turn_head(she, c + 6, nod=14); bears.turn_head(she, c + 12, nod=-6); bears.turn_head(she, c + 18, nod=10)
    bears.set_eyes(she, 'heart', c + 4); bears.set_eyes(he, 'heart', c + 10)
    bears.key_pose(he, c + 26, kneel); bears.hold(he, c + 26)
    bears.key_pose(he, c + 44, dict(bears.STAND, **{'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (4, 30, -10)}))
    he.location = (bx, -.2, DZ); bears.hold(he, c + 44)
    bears.key_pose(she, c + 44, {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 30, -12)})
    film.key_visible(boxo, c + 30, False)
    bears.set_eyes(she, 'closed', c + 56); bears.set_eyes(he, 'closed', c + 60)
    hug_he = dict(bears.STAND, **{'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (4, 30, -10)})
    hug_she = {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 30, -12)}
    bears.hug_sway(he, c + 50, SHOTS['end'], hug_he); bears.hug_sway(she, c + 50, SHOTS['end'], hug_she, phase=.5)
    # ---- cameras
    # walking out along the bridge toward the arch, the river and the lit left bank to their right
    A = film.camera('Cam14a_Arch', [(SHOTS['a'], (bx - 10.5, 1.6, DZ + 1.6), (ARCH[0], ARCH[1] - 6, DECK + 8)), (SHOTS['b'] - 1, (bx - 6.0, 1.4, DZ + 1.5), (ARCH[0], ARCH[1] - 6, DECK + 8))],
                    lens=22, fstop=4, focus=7.0)
    # the kneel, side-on: the river and the city lights below to the left
    B = film.camera('Cam14b_Kneel', [(SHOTS['b'], (bx + 3.0, 1.6, DZ + .85), (bx, -.08, DZ + .5)), (SHOTS['c'] - 1, (bx + 2.7, 1.5, DZ + .8), (bx, -.08, DZ + .5))],
                    lens=30, fstop=2.8, focus=(bx, -.05, DZ + .5))
    # yes: the glowing arch behind them, the camera drifting back and up
    C = film.camera('Cam14c_Yes', [(SHOTS['c'], (bx - 3.8, 1.35, DZ + 1.0), (bx + .3, -.05, DZ + .75)), (SHOTS['end'], (bx - 5.6, 2.0, DZ + 2.2), (bx + .3, -.05, DZ + 1.0))],
                    lens=26, fstop=2.8, focus=4.0)
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '14', still_frame=170)
