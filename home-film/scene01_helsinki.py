"""
Home - scene 1: Helsinki, spring (song 0:00-0:32).
Melting snow on Senate Square below the white cathedral with its green domes. They meet a few times that year,
never in a way that defined anything; the colours warm with each glimpse.

Shots:  1-144   the cathedral at a cold dawn (slow push-in)
      145-288   an icicle on a lamp post drips (the thaw)
      289-456   glimpse 1: he sits on the cathedral steps, she walks past below; a glance
      457-600   glimpse 2: they cross paths on the square in the afternoon; both look back
      601-768   glimpse 3: the harbour at golden hour, ice floes; a bench with a gap between them; she walks away
Run: Blender Scripting tab -> open this file -> Run Script, or
     blender -b --python scene01_helsinki.py -- --frames 1-768x2 --percent 50
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
from film import box, cylinder, dome, blob, mat, link, node_mat, add_haze, PI
import numpy as np
from mathutils import Vector

SHOTS = dict(a=1, b=145, c=289, d=457, e=601, end=768)
Z0 = 7.6                        # top of the cathedral platform (the steps rise 40 x 0.19)
CATH = (0, 53.25)               # cathedral centre
STEP_RISE, STEP_RUN, STEP_Y0 = .19, .35, 17.5


def step_top(k):
    return (k + 1) * STEP_RISE, STEP_Y0 + STEP_RUN * k        # (z of the tread, y of its front edge)


# ---------------------------------------------------------------- materials
def snowy(name, base, rough=.6, noise_scale=1.0, speck=None, cobbles=False, bias=0.0):
    """Ground-type material with melting snow patches and wet puddles. A 'Melt' value node (0 = lots of snow,
    1 = almost none) is keyframed over the scene."""
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord'); P = tc.outputs['Object']
    col = N.new('ShaderNodeValToRGB'); r = col.color_ramp
    r.elements[0].color = (*[c * .7 for c in base], 1); r.elements[1].color = (*[min(1, c * 1.2) for c in base], 1)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3 * noise_scale; nz.inputs['Detail'].default_value = 6
    L.new(P, nz.inputs['Vector']); L.new(nz.outputs['Fac'], col.inputs['Fac'])
    base_col = col.outputs['Color']
    if cobbles:
        vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = 11
        L.new(P, vo.inputs['Vector'])
        vc = N.new('ShaderNodeTexVoronoi'); vc.inputs['Scale'].default_value = 11; L.new(P, vc.inputs['Vector'])
        sc_ = N.new('ShaderNodeMapRange'); sc_.inputs['To Min'].default_value = .7; sc_.inputs['To Max'].default_value = 1.25
        L.new(vc.outputs['Distance'], sc_.inputs['Value'])
        jr = N.new('ShaderNodeValToRGB'); jr.color_ramp.elements[0].color = (.12, .12, .12, 1); jr.color_ramp.elements[1].position = .05
        stone = N.new('ShaderNodeMix'); stone.data_type = 'RGBA'; stone.blend_type = 'MULTIPLY'; stone.inputs['Factor'].default_value = 1
        L.new(base_col, stone.inputs['A']); L.new(vc.outputs['Color'], stone.inputs['B'])
        st2 = N.new('ShaderNodeMix'); st2.data_type = 'RGBA'; st2.inputs['Factor'].default_value = .75
        L.new(stone.outputs['Result'], st2.inputs['A']); L.new(base_col, st2.inputs['B']); base_col = st2.outputs['Result']
        L.new(vo.outputs['Distance'], jr.inputs['Fac'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
        L.new(base_col, mx.inputs['A']); L.new(jr.outputs['Color'], mx.inputs['B']); base_col = mx.outputs['Result']
        bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .3; bump.inputs['Distance'].default_value = .02
        L.new(vo.outputs['Distance'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    L.new(base_col, b.inputs['Base Color'])
    # puddles: wet and glossy
    pn = N.new('ShaderNodeTexNoise'); pn.inputs['Scale'].default_value = .35 * noise_scale; L.new(P, pn.inputs['Vector'])
    pr = N.new('ShaderNodeMapRange'); pr.inputs['From Min'].default_value = .52; pr.inputs['From Max'].default_value = .56
    pr.inputs['To Min'].default_value = rough; pr.inputs['To Max'].default_value = .04
    L.new(pn.outputs['Fac'], pr.inputs['Value']); L.new(pr.outputs['Result'], b.inputs['Roughness'])
    # snow on flat parts, in patches that shrink as 'Melt' rises
    snow = N.new('ShaderNodeBsdfPrincipled')
    snow.inputs['Base Color'].default_value = (.8, .83, .88, 1); snow.inputs['Roughness'].default_value = .5
    snow.inputs['Subsurface Weight'].default_value = .3
    sn = N.new('ShaderNodeTexNoise'); sn.inputs['Scale'].default_value = .9 * noise_scale; sn.inputs['Detail'].default_value = 8
    L.new(P, sn.inputs['Vector'])
    melt = N.new('ShaderNodeValue'); melt.name = 'Melt'; melt.outputs[0].default_value = .5
    lo = N.new('ShaderNodeMath'); lo.operation = 'MULTIPLY_ADD'; lo.inputs[1].default_value = .25; lo.inputs[2].default_value = .42 + bias
    L.new(melt.outputs[0], lo.inputs[0])
    hi_ = N.new('ShaderNodeMath'); hi_.operation = 'ADD'; hi_.inputs[1].default_value = .03; L.new(lo.outputs[0], hi_.inputs[0])
    sm = N.new('ShaderNodeMapRange'); L.new(sn.outputs['Fac'], sm.inputs['Value'])
    L.new(lo.outputs[0], sm.inputs['From Min']); L.new(hi_.outputs[0], sm.inputs['From Max'])
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
    fl = N.new('ShaderNodeMapRange'); fl.inputs['From Min'].default_value = .7; fl.inputs['From Max'].default_value = .9
    L.new(sep.outputs['Z'], fl.inputs['Value'])
    fac = N.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'
    L.new(sm.outputs['Result'], fac.inputs[0]); L.new(fl.outputs['Result'], fac.inputs[1])
    mix = N.new('ShaderNodeMixShader'); L.new(fac.outputs[0], mix.inputs['Fac'])
    L.new(b.outputs[0], mix.inputs[1]); L.new(snow.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], N['Material Output'].inputs['Surface'])
    add_haze(m, N, L, mix)
    return m


def facade_material(name, wall, axis):
    """Neoclassical facade: pastel plaster with framed, reflective windows in a grid, a cornice band at every floor,
    and a darker plinth. axis 'x' = the wall faces +-X. (The Brick texture lays out the window grid.)"""
    m, N, L, b = node_mat(name)
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    cmb = N.new('ShaderNodeCombineXYZ')
    L.new(sep.outputs['Y' if axis == 'x' else 'X'], cmb.inputs['X']); L.new(sep.outputs['Z'], cmb.inputs['Y'])
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (.42, .42, 1); mp.inputs['Location'].default_value = (0, -.25, 0)
    L.new(cmb.outputs['Vector'], mp.inputs['Vector'])

    def grid(mortar):
        br = N.new('ShaderNodeTexBrick'); br.offset = 0; br.squash = 1
        br.inputs['Scale'].default_value = 1; br.inputs['Brick Width'].default_value = 1.1; br.inputs['Row Height'].default_value = 1.9
        br.inputs['Mortar Size'].default_value = mortar; br.inputs['Mortar Smooth'].default_value = 0
        br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (1, 1, 1, 1); br.inputs['Mortar'].default_value = (0, 0, 0, 1)
        L.new(mp.outputs['Vector'], br.inputs['Vector'])
        return br
    glass = grid(.68); frame = grid(.6)                        # Fac: 1 = mortar (wall), 0 = brick (window)
    win = N.new('ShaderNodeMath'); win.operation = 'SUBTRACT'; win.inputs[0].default_value = 1; L.new(glass.outputs['Fac'], win.inputs[1])
    fr = N.new('ShaderNodeMath'); fr.operation = 'SUBTRACT'; fr.inputs[0].default_value = 1; L.new(frame.outputs['Fac'], fr.inputs[1])
    # plaster with a soft variation and a cornice line at each floor
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .8; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    pl = N.new('ShaderNodeValToRGB'); pl.color_ramp.elements[0].color = (*[c * .85 for c in wall], 1); pl.color_ramp.elements[1].color = (*[min(1, c * 1.08) for c in wall], 1)
    L.new(nz.outputs['Fac'], pl.inputs['Fac'])
    band = N.new('ShaderNodeMath'); band.operation = 'PINGPONG'; band.inputs[1].default_value = 2.26
    L.new(sep.outputs['Z'], band.inputs[0])
    bl = N.new('ShaderNodeMath'); bl.operation = 'LESS_THAN'; bl.inputs[1].default_value = .12; L.new(band.outputs[0], bl.inputs[0])
    trim = [min(1, c * 1.22) for c in wall]
    col = N.new('ShaderNodeMix'); col.data_type = 'RGBA'; L.new(bl.outputs[0], col.inputs['Factor'])
    L.new(pl.outputs['Color'], col.inputs['A']); col.inputs['B'].default_value = (*trim, 1)
    # plinth (ground floor up to 1 m) darker
    pz = N.new('ShaderNodeMath'); pz.operation = 'LESS_THAN'; pz.inputs[1].default_value = 1.0; L.new(sep.outputs['Z'], pz.inputs[0])
    col2 = N.new('ShaderNodeMix'); col2.data_type = 'RGBA'; L.new(pz.outputs[0], col2.inputs['Factor'])
    L.new(col.outputs['Result'], col2.inputs['A']); col2.inputs['B'].default_value = (.18, .17, .16, 1)
    # window frame (white) and glass (dark, glossy, a hint of warm reflection)
    c3 = N.new('ShaderNodeMix'); c3.data_type = 'RGBA'; L.new(fr.outputs[0], c3.inputs['Factor'])
    L.new(col2.outputs['Result'], c3.inputs['A']); c3.inputs['B'].default_value = (.82, .8, .76, 1)
    c4 = N.new('ShaderNodeMix'); c4.data_type = 'RGBA'; L.new(win.outputs[0], c4.inputs['Factor'])
    L.new(c3.outputs['Result'], c4.inputs['A']); c4.inputs['B'].default_value = (.02, .025, .035, 1)
    L.new(c4.outputs['Result'], b.inputs['Base Color'])
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = .8; rr.inputs['To Max'].default_value = .06
    L.new(win.outputs[0], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    mt = N.new('ShaderNodeMapRange'); mt.inputs['To Max'].default_value = .6; L.new(win.outputs[0], mt.inputs['Value']); L.new(mt.outputs['Result'], b.inputs['Metallic'])
    # relief: windows set back, frames proud
    hsum = N.new('ShaderNodeMath'); hsum.operation = 'SUBTRACT'; L.new(fr.outputs[0], hsum.inputs[0]); L.new(win.outputs[0], hsum.inputs[1])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .6; bump.inputs['Distance'].default_value = .05
    L.new(hsum.outputs[0], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    # keep a node named like the old Brick texture, so night scenes can light the windows
    br_old = N.new('ShaderNodeTexBrick'); br_old.label = 'window grid'
    L.new(mp.outputs['Vector'], br_old.inputs['Vector'])
    for k, v in (('Brick Width', 1.1), ('Row Height', 1.9), ('Mortar Size', .68), ('Scale', 1)):
        br_old.inputs[k].default_value = v
    br_old.offset = 0; br_old.squash = 1
    add_haze(m, N, L, b)
    return m


# ---------------------------------------------------------------- the cathedral
def prism(name, width, height, depth, loc, m, coll, rot_z=0.0, parent=None):
    """Triangular pediment / gable: width along X, depth along Y, apex up."""
    w, d = width / 2, depth / 2
    V = [(-w, -d, 0), (w, -d, 0), (0, -d, height), (-w, d, 0), (w, d, 0), (0, d, height)]
    F = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    ob = film.mesh_obj(name, V, F, coll, [m], loc=loc); ob.rotation_euler = (0, 0, rot_z)
    if parent:
        ob.parent = parent
    return ob


def build_cathedral(coll):
    white = mat('Plaster', (.78, .79, .77), rough=.65, haze=True)
    granite = mat('GraniteBase', (.3, .29, .28), rough=.7, haze=True)
    green = mat('Verdigris', (.13, .34, .28), rough=.45, metal=.25, haze=True)
    gold = mat('Gold', (1, .72, .32), rough=.25, metal=1)
    dark = mat('WindowDark', (.02, .025, .03), rough=.15, haze=True)
    zinc = mat('ZincStatue', (.12, .13, .13), rough=.5, metal=.6, haze=True)
    cx, cy = CATH
    # platform and the great steps
    stairs_m = snowy('Steps', (.24, .23, .22), rough=.5, noise_scale=1.6, bias=.0)
    box('Platform', (62, 43.5, Z0), (cx, cy, 0), granite, coll)
    box('PlatformTop', (62, 43.5, .02), (cx, cy, Z0), stairs_m, coll)
    for k in range(40):
        z, y = step_top(k)
        box(f'Step{k:02d}', (61, 31.5 - y, z), (0, y + (31.5 - y) / 2, 0), stairs_m, coll)
    for sx in (-1, 1):
        box(f'StairWall{sx}', (1.0, 14.4, Z0 + .3), (sx * 30.9, STEP_Y0 + 7.0, 0), granite, coll)
    # core, cornice, drum, dome, lantern, cross
    box('Core', (24, 24, 16), (cx, cy, Z0), white, coll)
    box('Cornice', (25.2, 25.2, .9), (cx, cy, Z0 + 15.3), white, coll)
    cylinder('Drum', 7, 7.6, (cx, cy, Z0 + 16), white, coll, n=48)
    for i in range(24):
        a = 2 * PI * i / 24
        cylinder(f'DrumCol{i}', .28, 6.6, (cx + math.cos(a) * 7.55, cy + math.sin(a) * 7.55, Z0 + 16.3), white, coll, n=10)
    for i in range(12):
        a = 2 * PI * (i + .5) / 12
        box(f'DrumWin{i}', (1.0, .3, 2.6), (cx + math.cos(a) * 6.95, cy + math.sin(a) * 6.95, Z0 + 18.6), dark, coll, rot=(0, 0, a + PI / 2))
    cylinder('DrumRing', 8.0, .9, (cx, cy, Z0 + 22.9), white, coll, n=48)
    dome('Dome', 7.3, (cx, cy, Z0 + 23.8), green, coll, zscale=1.12, n=48, rings=16, ribs=16)
    top = Z0 + 23.8 + 7.3 * 1.12
    cylinder('Lantern', 1.15, 2.4, (cx, cy, top - .2), white, coll, n=24)
    dome('LanternDome', 1.3, (cx, cy, top + 2.2), green, coll, zscale=1.1, n=24, rings=8)
    box('CrossV', (.16, .16, 1.9), (cx, cy, top + 3.6), gold, coll)
    box('CrossH', (.95, .16, .16), (cx, cy, top + 4.75), gold, coll)
    cylinder('CrossBall', .22, .3, (cx, cy, top + 3.55), gold, coll, n=12)
    # four corner domes
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = cx + sx * 9.6, cy + sy * 9.6
            cylinder(f'TurretDrum{sx}{sy}', 2.05, 2.8, (px, py, Z0 + 16), white, coll, n=24)
            for i in range(8):
                a = 2 * PI * (i + .5) / 8
                box(f'TurretWin{sx}{sy}{i}', (.45, .2, 1.3), (px + math.cos(a) * 2.0, py + math.sin(a) * 2.0, Z0 + 16.7), dark, coll, rot=(0, 0, a + PI / 2))
            cylinder(f'TurretRing{sx}{sy}', 2.3, .4, (px, py, Z0 + 18.7), white, coll, n=24)
            dome(f'TurretDome{sx}{sy}', 2.15, (px, py, Z0 + 19.1), green, coll, zscale=1.15, n=24, rings=10)
            t2 = Z0 + 19.1 + 2.15 * 1.15
            cylinder(f'TurretLantern{sx}{sy}', .35, .7, (px, py, t2 - .1), white, coll, n=12)
            box(f'TurretCross{sx}{sy}', (.08, .08, .9), (px, py, t2 + .55), gold, coll)
            box(f'TurretCrossH{sx}{sy}', (.45, .08, .08), (px, py, t2 + 1.1), gold, coll)
    # four arms with porticos (south = towards the square, east, west), north arm plain
    for name, rz in (('S', 0), ('E', PI / 2), ('W', -PI / 2), ('N', PI)):
        e = link(bpy.data.objects.new('Arm' + name, None), coll); e.location = (cx, cy, Z0); e.rotation_euler = (0, 0, rz)
        parts = [box(f'ArmBody{name}', (16, 6.2, 14), (0, -15, 0), white, coll),
                 prism(f'ArmGable{name}', 16.4, 2.6, 6.2, (0, -15, 14), mat('Roof' + name, (.2, .3, .27), rough=.5, metal=.3, haze=True), coll)]
        if name != 'N':
            parts.append(box(f'Stylobate{name}', (17.5, 3.6, .8), (0, -19.6, 0), white, coll))
            for i in range(6):
                x = -6 + i * 2.4
                parts.append(cylinder(f'Col{name}{i}', .52, 11.2, (x, -20.2, .8), white, coll, n=16, r2=.44))
                parts.append(box(f'Cap{name}{i}', (1.3, 1.3, .45), (x, -20.2, 12.0), white, coll))
                parts.append(box(f'Base{name}{i}', (1.3, 1.3, .35), (x, -20.2, .8), white, coll))
            parts.append(box(f'Entab{name}', (16.8, 3.8, 1.5), (0, -19.6, 12.45), white, coll))
            parts.append(prism(f'Pediment{name}', 16.8, 3.0, 3.8, (0, -19.6, 13.95), white, coll))
            parts.append(box(f'Door{name}', (2.6, .3, 5.2), (0, -18.15, .8), dark, coll))
            for x in (-4.8, 4.8):
                parts.append(box(f'Win{name}{x}', (1.4, .3, 3.0), (x, -18.15, 6.5), dark, coll))
            for x, h in ((0, 17.3), (-7.8, 14.2), (7.8, 14.2)):     # zinc apostles on the pediment
                parts.append(blob(f'Apostle{name}{x}', (x, -19.6, h + .6), (.32, .32, .85), coll, zinc, sub=2, rough=.12, seed=int(x + 9)))
        for p in parts:
            p.parent = e
    return dict(white=white, granite=granite, green=green, gold=gold, dark=dark)


# ---------------------------------------------------------------- the square, the city, the harbour
def lamp_post(name, loc, coll, m_iron, m_glass, icicles=0, rng=None):
    x, y, z = loc
    cylinder(name + '_base', .2, .6, (x, y, z), m_iron, coll, n=12, r2=.12)
    cylinder(name + '_pole', .08, 3.4, (x, y, z + .6), m_iron, coll, n=10, r2=.06)
    cylinder(name + '_lantern', .22, .55, (x, y, z + 4.0), m_glass, coll, n=8, r2=.3)
    cylinder(name + '_cap', .34, .18, (x, y, z + 4.55), m_iron, coll, n=8, r2=.05)
    cylinder(name + '_bottom', .26, .08, (x, y, z + 3.93), m_iron, coll, n=8)
    obs = []
    ice = mat('Ice', (.85, .93, 1.0), rough=.08, transmission=1.0)
    ice.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value = 1.31
    for i in range(icicles):
        a = 2 * PI * i / max(icicles, 1)
        L = .25 + .2 * (rng.random() if rng is not None else .5) + (.12 if i == 0 else 0)
        obs.append(cylinder(f'{name}_icicle{i}', .045 if i else .055, L, (x + math.cos(a) * .2, y + math.sin(a) * .2, z + 3.93 - L), ice, coll, n=8, r2=.0))
    # flip icicles so they point down: a cone wide at the top
    for o in obs:
        o.scale.z = -1; o.location.z += o.dimensions.z
    return obs


def facade_building(name, size, loc, wall, coll, face_x):
    mx = facade_material(name + '_fx', wall, 'x'); my = facade_material(name + '_fy', wall, 'y')
    ob = box(name, size, loc, None, coll)
    ob.data.materials.append(mx); ob.data.materials.append(my)
    for p in ob.data.polygons:
        p.material_index = 0 if abs(p.normal.x) > .5 else 1
    roof = mat(name + '_roof', (.12, .13, .14), rough=.5, metal=.4, haze=True)
    box(name + '_cornice', (size[0] + .6, size[1] + .6, .7), (loc[0], loc[1], size[2] - .3), mat(name + '_trim', [min(1, c * 1.15) for c in wall], rough=.6, haze=True), coll)
    box(name + '_roof', (size[0] - .4, size[1] - .4, 1.4), (loc[0], loc[1], size[2] + .4), roof, coll)
    return ob


def build_city(coll):
    ground = snowy('Cobbles', (.2, .19, .18), rough=.55, cobbles=True)
    sq = film.grid_mesh('Square', *np.meshgrid(np.linspace(-120, 120, 3), np.linspace(-220, 120, 3)), np.zeros((3, 3)), coll, ground)
    # buildings around the square (Government Palace, University, the old merchants' houses on the south side)
    facade_building('EastPalace', (16, 92, 15), (57, -14, 0), (.66, .55, .32), coll, True)
    facade_building('WestUniversity', (16, 92, 15), (-57, -14, 0), (.72, .62, .4), coll, True)
    facade_building('SouthHouses1', (40, 14, 12), (-26, -72, 0), (.62, .42, .3), coll, False)
    facade_building('SouthHouses2', (40, 14, 11), (26, -72, 0), (.55, .55, .5), coll, False)
    facade_building('NorthLib', (26, 18, 13), (44, 70, 0), (.6, .6, .55), coll, False)
    facade_building('NorthWest', (26, 18, 13), (-44, 70, 0), (.7, .58, .38), coll, False)
    # the market side by the harbour (behind the south houses)
    facade_building('HarbourRow', (70, 12, 14), (-10, -112, 0), (.66, .5, .36), coll, False)
    # melt water: a wide shallow puddle in front of the low camera
    film.mesh_obj('MeltPuddle', [(-24, -34, .004), (-4, -34, .004), (-4, -18, .004), (-24, -18, .004)], [(0, 1, 2, 3)], coll,
                  [film.water_material('MeltWater', color=(.02, .022, .025), rough=.02, wave=.04, scale=2)])
    # the statue in the middle of the square
    granite = bpy.data.materials['GraniteBase']; bronze = mat('Bronze', (.05, .08, .07), rough=.4, metal=.7, haze=True)
    box('StatueBase', (6, 6, 1.2), (0, -2, 0), granite, coll)
    box('Pedestal', (2.6, 2.6, 4.2), (0, -2, 1.2), granite, coll)
    cylinder('StatueBody', .55, 1.9, (0, -2, 5.4), bronze, coll, n=12, r2=.38)
    blob('StatueHead', (0, -2, 7.55), (.32, .32, .38), coll, bronze, sub=2, rough=.05)
    blob('StatueCoat', (0, -2, 5.6), (.85, .7, .9), coll, bronze, sub=2, rough=.15)
    # snowbanks along the edges and beside the steps
    snow = film.snow_material('Snowbank')
    rng = np.random.default_rng(4)
    banks = [(-20.5, 16 - i * 2.1) for i in range(5)] + [(20.5, 16 - i * 2.1) for i in range(5)] + \
            [(-47 + rng.uniform(-1, 1), -40 + i * 7) for i in range(10)] + [(47 + rng.uniform(-1, 1), -40 + i * 7) for i in range(10)] + \
            [(-30 + i * 6, -63) for i in range(11)]
    for i, (x, y) in enumerate(banks):
        blob(f'Snowbank{i}', (x, y, -.1), (rng.uniform(1.0, 1.8), rng.uniform(.8, 1.2), rng.uniform(.35, .6)), coll, snow, sub=3, rough=.3, seed=i)
    # lamp posts
    iron = mat('Iron', (.02, .025, .025), rough=.35, metal=.6, haze=True)
    glass = mat('LampGlass', (.9, .85, .7), rough=.1, emission=(1, .75, .45), strength=0, transmission=.6)
    posts = [(-20.3, 14.0)] + [(x, y) for x in (-14, 14) for y in (-14, 6)] + [(x, -146.2) for x in (-4.5, 9)]
    for i, (x, y) in enumerate(posts):
        lamp_post(f'Lamp{i}', (x, y, 0), coll, iron, glass, icicles=5 if i == 0 else 0, rng=rng)
    # harbour: quay edge, sea, ice floes, a bench, bare trees
    quay = mat('QuayGranite', (.3, .29, .28), rough=.7, haze=True)
    box('QuayEdge', (240, 2.0, 2.4), (0, -151, -2.4), quay, coll)
    film.mesh_obj('Sea', [(-400, -152, -1.6), (400, -152, -1.6), (400, -700, -1.6), (-400, -700, -1.6)], [(0, 1, 2, 3)], coll,
                  [film.water_material('Sea', color=(.01, .018, .025), rough=.05, wave=.12)])
    # boats moored along the quay and out on the water, and the islands on the horizon
    hullc = [(.75, .74, .7), (.12, .2, .35), (.55, .12, .1), (.85, .84, .8)]
    for i, (x, y, L_, rz) in enumerate(((-26, -156, 7, .05), (-14, -158, 5, -.04), (18, -157, 9, .02), (32, -159, 6, 0), (-60, -210, 22, .3), (40, -260, 30, -.2))):
        hm_ = mat(f'Hull{i}', hullc[i % 4], rough=.35, coat=.4, haze=True)
        hull = box(f'Hull{i}', (L_ * .32, L_, L_ * .12), (x, y, -1.75), hm_, coll, bevel=L_ * .05); hull.rotation_euler = (0, 0, PI / 2 + rz)
        cab = box(f'Cabin{i}', (L_ * .2, L_ * .35, L_ * .1), (x, y, -1.75 + L_ * .12), mat(f'Cabin{i}', (.85, .84, .8), rough=.5, haze=True), coll, bevel=L_ * .02)
        cab.rotation_euler = (0, 0, PI / 2 + rz)
        if L_ < 12:
            cylinder(f'Mast{i}', .04, L_ * .9, (x, y, -1.75 + L_ * .12), mat('Mast', (.8, .8, .78), rough=.4, haze=True), coll, n=6)
    isle = mat('Island', (.06, .08, .05), rough=.9, haze=True)
    for i, (x, w_, h_) in enumerate(((-140, 120, 9), (30, 160, 12), (190, 110, 7))):
        blob(f'Island{i}', (x, -520, -2.5), (w_ / 2, 30, h_), coll, isle, sub=3, rough=.3, seed=300 + i)
    gull = mat('Gull', (.9, .9, .9), rough=.6, haze=True)
    for i in range(12):
        g = blob(f'Gull{i}', (rng.uniform(-30, 30), rng.uniform(-170, -160), -1.5), (.12, .3, .1), coll, gull, sub=1)
    floe = mat('Floe', (.75, .8, .86), rough=.35, sss=.3, haze=True)
    for i in range(70):
        x = rng.uniform(-60, 60); y = -154 - rng.exponential(25)
        blob(f'Floe{i}', (x, y, -1.62), (rng.uniform(.6, 3), rng.uniform(.5, 2.4), .12), coll, floe, sub=2, rough=.35, seed=100 + i)
    wood = mat('BenchWood', (.24, .13, .06), rough=.6); cast = mat('BenchIron', (.02, .02, .02), rough=.4, metal=.6)
    for k in range(4):
        box(f'BenchSeat{k}', (2.4, .1, .04), (0, -146.85 + k * .12, .3), wood, coll)
    for k in range(3):
        box(f'BenchBack{k}', (2.4, .04, .09), (0, -146.4, .42 + k * .13), wood, coll, rot=(.2, 0, 0))
    for x in (-1.05, 1.05):
        box(f'BenchLeg{x}', (.06, .55, .3), (x, -146.7, 0), cast, coll)
        box(f'BenchArm{x}', (.06, .5, .05), (x, -146.75, .48), cast, coll)
        box(f'BenchLegBack{x}', (.06, .06, .8), (x, -146.38, 0), cast, coll)
    bark = mat('CityBark', (.05, .045, .04), rough=.85, haze=True)
    for i, (x, y) in enumerate([(-14, -120), (-6, -121), (4, -120), (14, -121), (22, -120), (-22, -121), (30, -120)]):
        me = film.bare_tree(f'BareTree{i}', 80 + i, [bark])
        film.place_tree(coll, me, (x, y, 0), rng.uniform(8, 11), rng, name=f'BareTree{i}')


# ---------------------------------------------------------------- light that warms with every glimpse
def build_light():
    w, sky, bg, ramp = film.make_sky(elev=3, az=95, strength=.55, low=(.75, .8, .95), mid=(.8, .85, 1.0), high=(.7, .78, 1.0),
                                     aerosol=2.0)
    sun = film.make_sun(elev=3, az=95, energy=1.6, color=(.9, .9, 1.0))
    film.area_light('Fill', (0, -60, 40), (0, 0, 0), 4000, 60, (.8, .85, 1.0))
    # (shot start, sun elevation, azimuth, sun energy, sun colour, sky strength, horizon low, mid)
    looks = [(SHOTS['a'], 3, 95, 1.6, (.9, .9, 1.0), .55, (.75, .8, .95), (.8, .85, 1.0)),
             (SHOTS['c'], 14, 70, 2.6, (1, .93, .85), .75, (1, .85, .75), (.95, .9, .95)),
             (SHOTS['d'], 22, -35, 3.2, (1, .85, .68), .85, (1, .72, .5), (1, .8, .7)),
             (SHOTS['e'], 5, -72, 3.4, (1, .66, .38), .95, (1, .45, .22), (1, .65, .5))]
    for f, el, az, en, col, st, lo, mi in looks:
        film.aim_sun(sun, el, az); sun.keyframe_insert('rotation_euler', frame=f)
        sun.data.energy = en; sun.data.color = col
        sun.data.keyframe_insert('energy', frame=f); sun.data.keyframe_insert('color', frame=f)
        sky.sun_elevation = math.radians(el); sky.sun_rotation = math.radians(180 - az)
        sky.keyframe_insert('sun_elevation', frame=f); sky.keyframe_insert('sun_rotation', frame=f)
        bg.inputs['Strength'].default_value = st; bg.inputs['Strength'].keyframe_insert('default_value', frame=f)
        ramp.color_ramp.elements[0].color = (*lo, 1); ramp.color_ramp.elements[0].keyframe_insert('color', frame=f)
        ramp.color_ramp.elements[2].color = (*mi, 1); ramp.color_ramp.elements[2].keyframe_insert('color', frame=f)
    for idb in (sun, sun.data, w.node_tree):
        film._const(idb)
    # snow melts through the scene
    for m in bpy.data.materials:
        if m.node_tree and 'Melt' in m.node_tree.nodes:
            v = m.node_tree.nodes['Melt'].outputs[0]
            for f, val in ((SHOTS['a'], .0), (SHOTS['c'], .35), (SHOTS['d'], .6), (SHOTS['e'], .85)):
                v.default_value = val; v.keyframe_insert('default_value', frame=f)
            film._const(m.node_tree)


# ---------------------------------------------------------------- the icicle drips
def drops(coll):
    water = mat('Drop', (.8, .9, 1.0), rough=.02, transmission=1.0)
    tip = bpy.data.objects['Lamp0_icicle0']
    bpy.context.view_layer.update()
    tx, ty = tip.location.x, tip.location.y
    tz = min((tip.matrix_world @ Vector(c)).z for c in tip.bound_box)
    for i, f0 in enumerate(range(SHOTS['b'] - 10, SHOTS['c'], 40)):
        d = film.blob(f'Drop{i}', (tx, ty, tz - .02), (.022, .022, .028), coll, water, sub=2, rough=.02)
        for f, s, z in ((f0, .001, tz - .01), (f0 + 26, 1.0, tz - .025), (f0 + 30, 1.0, tz - .03), (f0 + 34, 1.0, tz - .4),
                        (f0 + 38, 1.0, tz - 1.6), (f0 + 39, .001, tz - 1.6)):
            d.scale = (s, s, s * (1.3 if f > f0 + 28 else 1)); d.location.z = z
            d.keyframe_insert('scale', frame=f); d.keyframe_insert('location', frame=f)
    return tx, ty, tz


# ---------------------------------------------------------------- the bears' three glimpses
def animate_bears(bears):
    he = bears.build_bear('he'); she = bears.build_bear('she')
    off = (300, 300, 0)
    bears.place(he, 1, off, 0); bears.place(she, 1, (302, 300, 0), 0)
    # glimpse 1: he sits on the steps, she walks along a lower step
    c = SHOTS['c']
    zs, ys = step_top(11)
    bears.place(he, c, (-2.0, ys + .24, zs), 0, sitting=True)
    zw, yw = step_top(3)
    bears.place(she, c, (8.5, yw + .17, zw), bears.facing(-1, 0))
    bears.walk(she, c + 4, SHOTS['d'] - 6, (8.5, yw + .17, zw), (-8.0, yw + .17, zw))
    bears.turn_head(he, c, yaw=35, nod=8); bears.turn_head(he, c + 60, yaw=40, nod=10)
    bears.turn_head(he, c + 95, yaw=5, nod=12); bears.turn_head(he, c + 140, yaw=-35, nod=10)
    bears.turn_head(she, c + 60, yaw=0); bears.turn_head(she, c + 80, yaw=-55, nod=-18); bears.turn_head(she, c + 104, yaw=-50, nod=-15)
    bears.turn_head(she, c + 122, yaw=0, nod=0)
    bears.blink(he, c + 30); bears.blink(she, c + 110)
    # glimpse 2: they cross paths on the square and both look back
    d = SHOTS['d']
    bears.place(he, d, (-7.5, -12.0, 0), bears.facing(1, 0)); bears.place(she, d, (7.5, -10.3, 0), bears.facing(-1, 0))
    bears.walk(he, d + 2, SHOTS['e'] - 2, (-7.5, -12.0, 0), (5.5, -11.8, 0))
    bears.walk(she, d + 2, SHOTS['e'] - 2, (7.5, -10.3, 0), (-5.5, -10.6, 0))
    for b in (he, she):
        bears.turn_head(b, d + 30, yaw=0); bears.turn_head(b, d + 62, yaw=35); bears.turn_head(b, d + 92, yaw=95, nod=-4)
        bears.turn_head(b, d + 130, yaw=100, nod=-4)
    # glimpse 3: the harbour bench at golden hour, a gap between them; she gets up and walks away
    e = SHOTS['e']; seat = .34
    bears.place(he, e, (-.62, -146.75, seat), 0, sitting=True); bears.place(she, e, (.62, -146.75, seat), 0, sitting=True)
    bears.turn_head(he, e + 30, yaw=0); bears.turn_head(he, e + 42, yaw=28, nod=4); bears.turn_head(he, e + 62, yaw=26, nod=4)
    bears.turn_head(he, e + 72, yaw=0)
    bears.turn_head(she, e + 66, yaw=0); bears.turn_head(she, e + 76, yaw=-30, nod=4); bears.turn_head(she, e + 92, yaw=-28, nod=4)
    bears.turn_head(she, e + 100, yaw=0)
    stand = e + 104
    bears.key_pose(she, stand, bears.SIT); bears.hold(she, stand)
    she.location = (.62, -147.25, 0)          # up off the bench, onto the quay
    bears.hold(she, stand + 14); bears.key_pose(she, stand + 14, bears.STAND)
    bears.walk(she, stand + 20, SHOTS['end'], (.62, -147.25, 0), (7.0, -147.6, 0))
    bears.turn_head(he, stand + 10, yaw=20); bears.turn_head(he, stand + 40, yaw=55, nod=4); bears.turn_head(he, SHOTS['end'], yaw=70, nod=6)
    bears.blink(he, e + 20); bears.blink(she, e + 50)
    return he, she


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(.75, .78, .85), start=40.0, dist=320.0, strength=.4)
    bpy.context.scene.view_settings.exposure = -.6
    sets = film.new_coll('Helsinki')
    build_cathedral(sets)
    build_city(sets)
    build_light()
    tx, ty, tz = drops(sets)
    he, she = animate_bears(bears)
    # the jump down from the platform for bears walking on the square uses ground z = 0
    # ---- cameras
    A = film.camera('Cam1a_Cathedral', [(SHOTS['a'], (2.0, -62, 1.3), (0, 40, 15)), (SHOTS['b'] - 1, (1.0, -50, 1.6), (0, 40, 16))], lens=24)
    # the thaw: low over the wet cobbles, the cathedral mirrored in the melt water, drifting slowly sideways
    B = film.camera('Cam1b_Reflection', [(SHOTS['b'], (-16.0, -33, .2), (-3.0, 40, 10)), (SHOTS['c'] - 1, (-12.5, -33, .24), (-1.0, 40, 10))],
                    lens=30, fstop=2.8, focus=40.0)
    zs, ys = step_top(11)
    C = film.camera('Cam1c_Steps', [(SHOTS['c'], (2.2, 11.6, 1.25), (-1.2, 20.0, 1.55)), (SHOTS['d'] - 1, (1.4, 12.2, 1.2), (-1.6, 20.0, 1.55))],
                    lens=26, fstop=4, focus=(-1, 19, 1.2))
    D = film.camera('Cam1d_Square', [(SHOTS['d'], (5.5, -24.5, .9), (0, -10.8, 1.6)), (SHOTS['e'] - 1, (4.6, -23.5, .9), (0, -10.8, 1.6))],
                    lens=40, fstop=4, focus=(0, -11, .6))
    E = film.camera('Cam1e_Harbour', [(SHOTS['e'], (.1, -142.4, 1.2), (0, -170, .1)), (SHOTS['end'], (1.6, -141.6, 1.3), (2.6, -170, .1))],
                    lens=20, fstop=4, focus=(0, -146.8, .5))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C), (SHOTS['d'], D), (SHOTS['e'], E)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '01', still_frame=400)
