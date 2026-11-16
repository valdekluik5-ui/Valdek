"""
Home - scene 14: the Rainbow Bridge, Kyiv (song 4:35-4:47 - the sudden quiet break, then the peak begins).
Evening, after dark, on the hill above the Dnipro: the glass bridge across the wooded ravine leads to the great steel
arch, lit in rainbow bands. Below: the wide river, Trukhaniv island, the lit towers of the left bank and the bridges.
He kneels with the ring; she says yes.

Shots:  1-96    a flight in from high over the river toward the lit bridge and the arch, landing beside the two of them at the rail
       97-200   at the rail: he kneels and opens a little box; the river, the lights and the blue Podilskyi bridge below
      201-288   yes - heart eyes, a hug; the camera rises up into the night air and the city opens out
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


def lit_windows_material(name, warm=(1, .72, .38), lit=.45, strength=4.0, scale=(1.0, 1.0, 1.0)):
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


BEND_R = 180.0                     # the bridge curves in plan, bulging out toward the river at x = BX
BX = -40.0                         # where they stand: the bridge's outermost point, at the river-side rail
HALF_W = 3.0                       # half the deck width
PLAT_R = 3.6                       # the round viewing platform on the river side at BX, where they stood
PLAT_C = (BX, -HALF_W - 2.0)


def yc(x):
    """The bridge's centre line (plan view): a gentle curve, furthest toward the river (-Y) at BX."""
    return BEND_R - math.sqrt(max(0.0, BEND_R ** 2 - (x - BX) ** 2))


def heading(x):
    return math.atan2(yc(x + .5) - yc(x - .5), 1.0)


def bridge(coll):
    """The glass pedestrian bridge: a long curving deck high over the ravine, a red cycle lane between pale walkways,
    stainless V-shaped posts leaning outward with horizontal cables between them, a round steel handrail with LEDs that
    light the deck at night, a white box girder underneath on slim piers."""
    x0, x1 = BRIDGE
    n = 140
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    def strip(name, o1, o2, dz, m, thick=0.0):
        V, F = [], []
        for x in xs:
            a = heading(x); nx, ny = -math.sin(a), math.cos(a)            # left normal (toward +Y side)
            z = deck_z(x) + dz
            for o in (o1, o2):
                V.append((x + nx * o, yc(x) + ny * o, z))
        for i in range(n):
            q = 2 * i; F.append((q, q + 2, q + 3, q + 1))
        return film.mesh_obj(name, V, F, coll, [m])
    pale, N, L, b = node_mat('DeckPale')                                   # light grey stone with dark and white specks
    tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 90
    L.new(tc.outputs['Object'], vo.inputs['Vector'])
    rp = N.new('ShaderNodeValToRGB'); rp.color_ramp.interpolation = 'CONSTANT'
    rp.color_ramp.elements[0].color = (.18, .18, .18, 1); rp.color_ramp.elements[1].position = .3; rp.color_ramp.elements[1].color = (.6, .59, .57, 1)
    e = rp.color_ramp.elements.new(.85); e.color = (.85, .85, .83, 1)
    L.new(vo.outputs['Color'], rp.inputs['Fac']); L.new(rp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .6
    add_haze(pale, N, L, b)
    red = mat('CycleLane', (.33, .1, .07), rough=.6, haze=True)
    curb = mat('DeckCurb', (.75, .74, .72), rough=.5, haze=True)
    white = mat('GirderWhite', (.78, .79, .8), rough=.4, metal=.3, haze=True)
    steel = mat('RailSteel', (.8, .81, .83), rough=.18, metal=1.0, haze=True)
    led = emit_mat('RailLED', (1, .84, .6), 10.0)
    strip('DeckLeft', 1.1, HALF_W, 0, pale); strip('DeckRight', -HALF_W, -1.1, 0, pale); strip('CycleLane', -1.1, 1.1, .003, red)
    for side in (-1, 1):
        strip(f'CurbTop{side}', side * (HALF_W - .25), side * HALF_W, .12, curb)
        strip(f'DeckEdge{side}', side * HALF_W, side * (HALF_W + .02), -1.1, white)
    strip('GirderBottom', -2.2, 2.2, -1.6, white)
    for side in (-1, 1):                                                   # the girder's sloping sides
        V, F = [], []
        for x in xs:
            a = heading(x); nx, ny = -math.sin(a), math.cos(a)
            V += [(x + nx * side * HALF_W, yc(x) + ny * side * HALF_W, deck_z(x) - .05), (x + nx * side * 2.2, yc(x) + ny * side * 2.2, deck_z(x) - 1.6)]
        for i in range(n):
            q = 2 * i; F.append((q, q + 2, q + 3, q + 1))
        film.mesh_obj(f'GirderSide{side}', V, F, coll, [white])
    # balustrades: V posts every 2.2 m along each edge, leaning outward, 7 cables, the handrail tube with its LED strip
    L_total = sum(math.hypot(xs[i + 1] - xs[i], yc(xs[i + 1]) - yc(xs[i])) for i in range(n))
    npost = int(L_total / 2.2)
    for side in (-1, 1):
        pts = []
        for k in range(npost + 1):
            x = x0 + (x1 - x0) * k / npost
            if side == -1 and abs(x - BX) < PLAT_R - .3:
                pts.append(None); continue
            a = heading(x); nx, ny = -math.sin(a), math.cos(a)
            base = Vector((x + nx * side * (HALF_W - .12), yc(x) + ny * side * (HALF_W - .12), deck_z(x) + .12))
            top = base + Vector((nx * side * .22, ny * side * .22, 1.05))
            pts.append((base, top, a))
            for lean in (-.35, .35):                                       # the two arms of the V
                foot = base + Vector((math.cos(a) * lean, math.sin(a) * lean, 0))
                d = top - foot; L_ = d.length
                o = box(f'Post{side}_{k}_{lean}', (.05, .05, L_), foot, steel, coll)
                o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        for k in range(npost):
            if pts[k] is None or pts[k + 1] is None:
                continue
            b0, t0, a0 = pts[k]; b1, t1, a1 = pts[k + 1]
            mid = (t0 + t1) / 2; d = t1 - t0
            r = cylinder(f'Handrail{side}_{k}', .045, d.length, t0, steel, coll, n=10)
            r.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
            l_ = box(f'RailLED{side}_{k}', (.03, .03, d.length), t0 + Vector((0, 0, -.06)) - Vector((-math.sin(a0) * side * .03, math.cos(a0) * side * .03, 0)), led, coll)
            l_.rotation_euler = r.rotation_euler
            for c in range(7):
                f = .12 + c * .13
                p0 = b0.lerp(t0, f); p1 = b1.lerp(t1, f); dd = p1 - p0
                w_ = box(f'Cable{side}_{k}_{c}', (.008, .008, dd.length), p0, steel, coll)
                w_.rotation_euler = Vector((0, 0, 1)).rotation_difference(dd.normalized()).to_euler()
    # the round viewing platform: a half disc of the same speckled stone, its own curved rail, a pier beneath
    pc = Vector((PLAT_C[0], PLAT_C[1], deck_z(BX)))
    nseg = 40
    V = [tuple(pc)] + [tuple(pc + Vector((PLAT_R * math.cos(a), PLAT_R * math.sin(a), 0))) for a in np.linspace(0, -PI, nseg + 1)]
    film.mesh_obj('PlatformFloor', V, [(0, i, i + 1) for i in range(1, nseg + 1)], coll, [pale])
    box('PlatformFill', (2 * PLAT_R, 2.2, .02), pc + Vector((0, 1.0, -.01)), pale, coll)
    rim = [pc + Vector(((PLAT_R + .02) * math.cos(a), (PLAT_R + .02) * math.sin(a), 0)) for a in np.linspace(0, -PI, nseg + 1)]
    film.mesh_obj('PlatformEdge', [tuple(p) for p in rim] + [tuple(p + Vector((0, 0, -1.4))) for p in rim],
                  [(i, i + 1, i + nseg + 2, i + nseg + 1) for i in range(nseg)], coll, [white])
    cylinder('PlatformPier', 1.0, deck_z(BX) - float(ground_z(pc.x, pc.y)) + 1, (pc.x, pc.y, float(ground_z(pc.x, pc.y)) - 1), white, coll, n=16)
    ppts = []
    for k, a in enumerate(np.linspace(-.05, -PI + .05, 13)):
        base = pc + Vector(((PLAT_R - .12) * math.cos(a), (PLAT_R - .12) * math.sin(a), .12))
        top = base + Vector((.22 * math.cos(a), .22 * math.sin(a), 1.05)); ppts.append((base, top))
        for lean in (-.35, .35):
            tang = Vector((-math.sin(a), math.cos(a), 0))
            foot = base + tang * lean; d = top - foot
            o = box(f'PPost{k}_{lean}', (.05, .05, d.length), foot, steel, coll)
            o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    for k in range(len(ppts) - 1):
        (b0, t0), (b1, t1) = ppts[k], ppts[k + 1]; d = t1 - t0
        r = cylinder(f'PRail{k}', .05, d.length, t0, steel, coll, n=10); r.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        l_ = box(f'PRailLED{k}', (.03, .03, d.length), t0 + Vector((0, 0, -.07)), led, coll); l_.rotation_euler = r.rotation_euler
        for c in range(7):
            f = .12 + c * .13; p0 = b0.lerp(t0, f); p1 = b1.lerp(t1, f); dd = p1 - p0
            w_ = box(f'PCable{k}_{c}', (.008, .008, dd.length), p0, steel, coll); w_.rotation_euler = Vector((0, 0, 1)).rotation_difference(dd.normalized()).to_euler()
        g = box(f'PGlass{k}', (.02, d.length, .9), (b0 + b1) / 2 + Vector((0, 0, .1)), mat('PlatformGlass', (.6, .7, .75), rough=.02, transmission=1.0, alpha=.25, haze=True), coll)
        g.rotation_euler = (0, 0, math.atan2(d.y, d.x) - PI / 2)
    # slim piers down into the ravine
    for k, x in enumerate((x0 + (x1 - x0) * .22, x0 + (x1 - x0) * .5, x0 + (x1 - x0) * .78)):
        gz = float(ground_z(x, yc(x)))
        cylinder(f'Pier{k}', .7, deck_z(x) - 1.6 - gz + 1, (x, yc(x), gz - 1), white, coll, n=16)
    # lamps along the bridge (warm), every 18 m on the land side
    lampm = emit_mat('BridgeLampGlow', (1, .82, .55), 20.0)
    for k in range(7):
        x = x0 + 8 + k * 16
        a = heading(x); nx, ny = -math.sin(a), math.cos(a)
        p = Vector((x + nx * (HALF_W - .3), yc(x) + ny * (HALF_W - .3), deck_z(x) + .12))
        cylinder(f'BridgeLampPole{k}', .06, 4.2, p, steel, coll, n=8)
        blob(f'BridgeLamp{k}', p + Vector((0, 0, 4.3)), (.2, .2, .1), coll, lampm, sub=1, rough=0)
        film.point_light(f'BridgeLampL{k}', p + Vector((0, 0, 4.1)), 150, (1, .8, .55), .2)


def deck_z(x):
    """Height of the bridge deck: a gentle rise toward the middle."""
    x0, x1 = BRIDGE
    return DECK + .6 * math.sin(PI * min(1.0, max(0.0, (x - x0) / (x1 - x0))))


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
    """The view from the bridge at night, as it really looks from there: the Dnipro below running away from the hill;
    Trukhaniv island dark on the right with its pale sand shore; the Podil embankment curving off to the left under
    orange lamps whose light streaks across the water; the lit towers of the left bank; far off, the great arch of the
    Podilskyi bridge glowing blue, and beyond it the pylon of the next bridge; a little lit river boat."""
    river = film.water_material('Dnipro', color=(.003, .005, .009), rough=.025, wave=.1, scale=.06)
    film.mesh_obj('River', [(-6000, -6000, 0), (6000, -6000, 0), (6000, 400, 0), (-6000, 400, 0)], [(0, 1, 2, 3)], coll, [river])
    # our bank: the hill, its wooded slope and the ravine
    hill = mat('KyivHill', (.03, .05, .02), rough=.9, haze=True)
    xs_ = np.arange(-300, 300.1, 2.0); ys_ = np.arange(-130, 160.1, 2.0)
    X, Y = np.meshgrid(xs_, ys_); Z = ground_z(X, Y)
    land = film.grid_mesh('RightBank', X, Y, Z, coll, hill)
    plaza = (np.abs(X - ARCH[0]) < 48) & (Y > ARCH[1] - 20) & (Y < ARCH[1] + 30)
    forest = ((Z > 3) & (Z < DECK - 9) & (Y < -12)) | ((np.abs(X - RAVINE) < 26) & (Z < DECK - 12)) | ((Y > 50) & ~plaza)
    film.vgroup(land, 'forest', forest.astype(float).ravel())
    hi, lib = film.tree_library('KyivTrees')
    film.scatter_instances(land, lib, 'forest', 5500, 13, seed=14)
    sodium = emit_mat('Sodium', (1, .55, .2), 60); white = emit_mat('WhiteLamps', (1, .93, .8), 60)
    asphalt = mat('Asphalt', (.03, .03, .03), rough=.5, haze=True)
    # the road down the ravine under the bridge, its lamps glowing through the trees
    for i in range(30):
        y = -110 + i * 8; z = float(ground_z(RAVINE, y))
        box(f'RavineRoad{i}', (7, 8.2, .1), (RAVINE, y, z + .1), asphalt, coll)
        if i % 2 == 0:
            blob(f'RavineLamp{i}', (RAVINE + 4.5, y, z + 6), (.3, .3, .2), coll, sodium, sub=1, rough=0)
            film.point_light(f'RavineLampL{i}', (RAVINE + 4.5, y, z + 5.8), 600, (1, .55, .2), .3)
    # the embankment below: a road along the water at the foot of the hill, curving away to the left (north-west)
    def emb(t):                                   # t 0..1 along the embankment
        return Vector((-260 + 1100 * t, -95 - 900 * t ** 1.6, 4.0))
    for i in range(160):
        t = i / 159; p = emb(t)
        blob(f'EmbLamp{i}', p + Vector((0, 0, 7)), (1.1, 1.1, 1.1), coll, sodium, sub=1, rough=0)
        if i % 2 == 0:
            box(f'EmbRoad{i}', (16, 12, 1.0), p + Vector((0, 0, -4)), asphalt, coll).rotation_euler = (0, 0, math.atan2(emb(min(1, t + .01)).y - p.y, emb(min(1, t + .01)).x - p.x))
    for i in range(40):                           # a row of brighter white lights along the river station / promenade
        t = .05 + i * .006; p = emb(t)
        blob(f'Promenade{i}', p + Vector((-4, -6, 3)), (1.0, 1.0, 1.0), coll, white, sub=1, rough=0)
    # Trukhaniv island on the right: low dark woods, a pale sandy shore all along the water, a few path lamps
    isle = mat('Trukhaniv', (.008, .014, .008), rough=.9, haze=True); sand = mat('IslandSand', (.32, .29, .22), rough=.9, haze=True)
    blob('TrukhanivSand', (-620, -1000, -3.4), (430, 820, 4.2), coll, sand, sub=3, rough=.15, seed=51)
    blob('Trukhaniv', (-660, -1000, -4.5), (400, 790, 11), coll, isle, sub=3, rough=.25, seed=52)
    path = emit_mat('IslandPath', (1, .9, .7), 14)
    rng = np.random.default_rng(40)
    for i in range(50):
        blob(f'IslandLamp{i}', (rng.uniform(-950, -300), rng.uniform(-1700, -300), 5.5), (1.0, 1.0, 1.0), coll, path, sub=1, rough=0)
    # the left bank: towers with lit windows, crowded along the horizon on the left and beyond the far bridge
    wins = [lit_windows_material(f'Windows{k}', warm=c, lit=l) for k, (c, l) in enumerate((((1, .72, .38), .42), ((1, .85, .6), .35), ((.85, .9, 1), .3), ((1, .65, .3), .5)))]
    beacon = emit_mat('Beacon', (1, .1, .05), 40)
    k = 0
    for i in range(170):
        if i < 70:                               # the left bank, beyond the island
            x = rng.uniform(-3600, -800); y = rng.uniform(-4200, -2000)
        elif i < 120:                            # beyond the far bridge
            x = rng.uniform(-900, 1600); y = rng.uniform(-4300, -2400)
        else:                                    # Podil and the city on our side, to the right
            x = rng.uniform(700, 3200); y = rng.uniform(-3000, -500)
        w_ = rng.uniform(20, 40); d_ = rng.uniform(15, 24); h = rng.uniform(30, 110) * (1.3 if rng.random() < .15 else 1)
        o = box(f'Tower{k}', (w_, d_, h), (x, y, 0), wins[k % 4], coll); o.rotation_euler = (0, 0, rng.uniform(-.3, .3))
        if rng.random() < .3:
            blob(f'TowerBeacon{k}', (x, y, h + 1.5), (.8, .8, .8), coll, beacon, sub=1, rough=0)
        k += 1
    box('LeftBank', (8000, 3000, 3), (-1800, -3500, -1.5), mat('LeftBankGround', (.015, .015, .015), rough=.9, haze=True), coll)
    box('Podil', (4000, 4000, 3), (2600, -1600, -1.5), mat('PodilGround', (.02, .02, .02), rough=.9, haze=True), coll).rotation_euler = (0, 0, -.35)
    glow = emit_mat('CityGlow', (1, .75, .45), 40)
    for i in range(1600):                         # street lights spread across the far city
        x = rng.uniform(-3500, 3200); y = rng.uniform(-4300, -400)
        if (x < 600 and y > -2250) or (x < 1100 and y > -95 - 900 * max(0.0, min(1.0, (x + 260) / 1100)) ** 1.6 - 40 and y > -2250):
            continue                             # (the river, the island)
        blob(f'CityLight{i}', (x, y, 4), (3.0, 3.0, 3.0), coll, glow, sub=1, rough=0)
    # the Podilskyi bridge: a 340 m arch lit blue, its deck strung with lamps, long approach viaducts
    PB = -2100.0
    conc = mat('BridgeConcrete', (.12, .12, .12), rough=.7, haze=True)
    blue = emit_mat('ArchBlue', (.25, .35, 1.0), 14.0); blue2 = emit_mat('HangerBlue', (.5, .6, 1.0), 4.0)
    box('PodilskyiDeck', (1900, 24, 3), (-150, PB, 15), conc, coll)
    for i in range(95):
        x = -1100 + i * 20
        for sy in (-1, 1):
            blob(f'PodilLamp{i}{sy}', (x, PB + sy * 12, 22), (2.2, 2.2, 2.2), coll, white if i % 3 else sodium, sub=1, rough=0)
    for i in range(10):
        box(f'PodilPier{i}', (14, 10, 15), (-1000 + i * 200, PB, 0), conc, coll)
    V, F = [], []
    n = 80; half = 170.0; H = 78.0
    for i in range(n + 1):
        t = -1 + 2 * i / n; x = t * half; z = 18 + H * (1 - t * t)
        for dy, dz in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
            V.append((x - 60, PB + dy, z + dz))
    for i in range(n):
        o = i * 4; q = o + 4
        for j in range(4):
            F.append((o + j, o + (j + 1) % 4, q + (j + 1) % 4, q + j))
    film.mesh_obj('PodilskyiArch', V, F, coll, [blue])
    for i in range(1, 28):
        t = -1 + 2 * i / 28; x = t * half - 60; z = 18 + H * (1 - t * t)
        box(f'Hanger{i}', (.5, .5, z - 18), (x, PB, 18), blue2, coll)
    film.point_light('ArchBlueGlow', (-60, PB + 60, 60), 4e5, (.3, .4, 1.0), 40)
    # beyond: the next bridge's tall pylon with its fan of cables, lit white
    pyl = emit_mat('PylonLight', (.9, .92, 1.0), 3.0)
    box('NorthPylon', (8, 8, 120), (420, -3300, 0), pyl, coll)
    for i in range(10):
        for sx in (-1, 1):
            d = Vector((sx * (40 + i * 22), 0, 20 - 108 - i * 0)); top = Vector((420, -3300, 112 - i * 3))
            end = Vector((420 + sx * (40 + i * 24), -3300, 18)); dd = end - top
            c_ = box(f'Stay{i}{sx}', (.4, .4, dd.length), top, pyl, coll); c_.rotation_euler = Vector((0, 0, 1)).rotation_difference(dd.normalized()).to_euler()
    box('NorthDeck', (1600, 20, 3), (300, -3300, 15), conc, coll)
    for i in range(70):
        blob(f'NorthLamp{i}', (-500 + i * 23, -3300, 22), (2.2, 2.2, 2.2), coll, white, sub=1, rough=0)
    # the park footbridge to the island: a white pylon, its cables fanned out, lit; and the white column with the golden top
    pylm = emit_mat('ParkBridgeLight', (.95, .95, 1.0), 4.0)
    a0_, b0_ = Vector((-150, -100, 8)), Vector((-330, -330, 8)); mid = a0_.lerp(b0_, .35); dd = b0_ - a0_
    dk = box('ParkBridgeDeck', (5, dd.length, 1.2), a0_, conc, coll); dk.rotation_euler = (0, 0, math.atan2(-dd.x, dd.y))
    box('ParkPylon', (2, 2, 60), mid, pylm, coll)
    for i in range(8):
        for t in (-1, 1):
            end = mid.lerp(a0_ if t < 0 else b0_, .2 + i * .1); top = mid + Vector((0, 0, 58 - i * 2.5)); d_ = end - top
            c_ = box(f'ParkStay{i}{t}', (.2, .2, d_.length), top, pylm, coll); c_.rotation_euler = Vector((0, 0, 1)).rotation_difference(d_.normalized()).to_euler()
    for i in range(16):
        blob(f'ParkLamp{i}', a0_.lerp(b0_, i / 15) + Vector((0, 0, 3)), (.8, .8, .8), coll, white, sub=1, rough=0)
    stonew = mat('ColumnWhite', (.85, .84, .8), rough=.5, haze=True); goldm = mat('ColumnGold', (1, .72, .3), rough=.2, metal=1, haze=True)
    cylinder('MagdeburgColumn', 2.2, 20, (40, -112, 4), stonew, coll, n=20)
    film.dome('MagdeburgDome', 2.6, (40, -112, 24), goldm, coll, zscale=1.3)
    film.point_light('MagdeburgFlood', (40, -100, 10), 3e4, (1, .85, .6), 2)
    # a river boat gliding along with its windows lit
    hull = mat('BoatHull', (.85, .85, .83), rough=.4, haze=True); win = emit_mat('BoatWindows', (1, .8, .5), 6.0)
    boat = bpy.data.objects.new('RiverBoat', None); link(boat, coll); boat.location = (40, -420, 0)
    for o in (box('BoatHullB', (9, 38, 2.4), (0, 0, -.6), hull, coll, bevel=.6), box('BoatDeck1', (7.5, 30, 2.2), (0, -1, 1.8), hull, coll, bevel=.3),
              box('BoatWin1', (7.6, 28, .9), (0, -1, 2.4), win, coll), box('BoatDeck2', (6, 18, 1.8), (0, -3, 4.0), hull, coll, bevel=.3),
              box('BoatWin2', (6.1, 16, .7), (0, -3, 4.5), win, coll)):
        o.parent = boat
    boat.rotation_euler = (0, 0, .25)
    boat.keyframe_insert('location', frame=1); boat.location = (60, -500, 0); boat.keyframe_insert('location', frame=SHOTS['end'])
    import bears as _b
    for fc in _b._fcurves(boat):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def build():
    bears = film.import_bears()
    # evening, after sunset: a deep blue sky with the last glow low behind them, moonlight, the city lit below
    film.HAZE.update(color=(.03, .045, .08), start=150.0, dist=4000.0, strength=.25)
    w, sky, bg, ramp = film.make_sky(elev=-3, az=180, strength=.3, low=(.9, .45, .3), mid=(.3, .35, .6), high=(.12, .16, .35), clouds=.25,
                                     cloud_tint=(.5, .5, .6))
    sun = film.make_sun(elev=35, az=30, energy=.4, color=(.55, .65, 1.0))
    bpy.context.scene.view_settings.exposure = .9
    st = film.new_coll('Kyiv'); river_city(st); bridge(st); arch(st)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    bx = BX
    DZ = deck_z(bx)
    RY = PLAT_C[1] - PLAT_R + .55                        # standing at the rail of the round platform, its outermost point
    film.area_light('ProposalFill', (bx + 1.2, .4, DZ + 1.9), (bx, RY, DZ + .5), 160, 1.6, (1, .72, .5))
    film.area_light('FaceFill', (bx - 1.2, RY - 2.2, DZ + 1.3), (bx, RY, DZ + .6), 90, 1.6, (1, .78, .58))     # warm light on their faces and the ring
    film.area_light('MoonRim', (bx - 3, 2, DZ + 4), (bx, RY, DZ + .6), 40, 3, (.6, .7, 1.0))                  # a cool rim from behind
    # paw in paw along the curving bridge to the rail at its outermost point, then they turn to the view
    p0h, p1h = Vector((bx - 2.2, -2.6, DZ)), Vector((bx - .35, RY, DZ)); p0s, p1s = Vector((bx - 1.6, -3.1, DZ)), Vector((bx + .35, RY, DZ))
    bears.place(he, 1, p0h, bears.facing(*(p1h - p0h).xy)); bears.place(she, 1, p0s, bears.facing(*(p1s - p0s).xy))
    bears.walk(he, 4, 72, p0h, p1h, hold={'shoulder.L': (8, 0, 22), 'forearm.L': (6, 0, 0)})
    bears.walk(she, 4, 72, p0s, p1s, hold={'shoulder.R': (8, 0, -22), 'forearm.R': (6, 0, 0)}, phase=2)
    for b in (he, she):                                   # turn to face the river
        bears.hold(b, 74); b.rotation_euler.z = bears.facing(0, -1); bears.hold(b, 86)
    bears.turn_head(she, 88, nod=-4); bears.turn_head(she, SHOTS['b'] - 1, yaw=-10, nod=-4)
    # he steps round in front of her and kneels; she turns to him, the city behind them
    b_ = SHOTS['b']
    bears.place(she, b_, (bx + .35, RY, DZ), bears.facing(-1, 0))
    # (plush legs are short, so a one-knee kneel barely lowers him: down on both knees, sitting back on his heels)
    kneel = {'thigh.L': (70, 0, -6), 'shin.L': (-110, 0, 0), 'thigh.R': (70, 0, 6), 'shin.R': (-110, 0, 0), 'spine': (14, 0, 0),
             'shoulder.L': (82, 0, 18), 'shoulder.R': (82, 0, -18), 'forearm.L': (20, 0, 0), 'forearm.R': (20, 0, 0), 'head': (-18, 0, 0)}
    bears.place(he, b_, (bx - .45, RY, DZ), bears.facing(1, 0))
    bears.key_pose(he, b_ + 26, kneel)
    bears.hold(he, b_ + 6); he.location.z = DZ - bears.ground_drop(he, kneel); he.location.x = bx - .5; bears.hold(he, b_ + 26)
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
    he.location = (bx - .2, RY, DZ); bears.hold(he, c + 44)
    bears.key_pose(she, c + 44, {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 30, -12)})
    film.key_visible(boxo, c + 30, False)
    bears.set_eyes(she, 'closed', c + 56); bears.set_eyes(he, 'closed', c + 60)
    hug_he = dict(bears.STAND, **{'shoulder.L': (75, 0, -30), 'shoulder.R': (75, 0, 30), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (4, 30, -10)})
    hug_she = {'shoulder.L': (80, 0, -32), 'shoulder.R': (80, 0, 32), 'forearm.L': (35, 0, 0), 'forearm.R': (35, 0, 0), 'head': (-6, 30, -12)}
    bears.hug_sway(he, c + 50, SHOTS['end'], hug_he); bears.hug_sway(she, c + 50, SHOTS['end'], hug_she, phase=.5)
    # ---- cameras
    # flying in: from high over the river, toward the lit bridge and the arch on the hill, down to the two of them
    A = film.camera('Cam14a_FlyIn', [(SHOTS['a'], (170, -330, 105), (bx, -3, DZ)), (40, (bx + 70, -110, DZ + 30), (bx, RY, DZ + .4)),
                                     (68, (bx + 14, -14, DZ + 8), (bx, RY, DZ + .45)), (84, (bx + 4, RY - .5, DZ + 3.4), (bx, RY, DZ + .4)),
                                     (SHOTS['b'] - 1, (bx + 2.6, RY + 1.4, DZ + 1.5), (bx - 2.2, RY - 2.0, DZ + .35))], lens=24, fstop=5.6, focus=(bx, RY, DZ + .5))
    # the proposal at the rail: the river, the lights and the blue bridge spread out below behind them
    B = film.camera('Cam14b_Kneel', [(SHOTS['b'], (bx - .08, RY + 4.2, DZ + 1.75), (bx - .08, RY - 14, DZ - 2.6)), (SHOTS['c'] - 1, (bx - .08, RY + 3.8, DZ + 1.7), (bx - .08, RY - 14, DZ - 2.4))],
                    lens=28, fstop=2.8, focus=(bx, RY, DZ + .5))
    # yes: the camera rises up behind them into the night air, the whole city opening out
    C = film.camera('Cam14c_Rise', [(SHOTS['c'], (bx + .3, RY + 3.65, DZ + 1.2), (bx - .1, RY, DZ + .7)), (SHOTS['c'] + 40, (bx - .1, RY + 5.2, DZ + 3.2), (bx - .1, RY - 4, DZ + .2)),
                                    (SHOTS['end'], (bx + 1.5, RY + 20, DZ + 22), (bx - 1.5, RY - 400, DZ - 40))], lens=26, fstop=5.6, focus=(bx, RY, DZ + .5))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '14', still_frame=170)
