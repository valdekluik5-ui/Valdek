"""
Home - scene 2: "It feels like home" (song 0:32-0:50).
Night. A small warm room above Senate Square; they sit close on a deep window seat under a blanket, fairy lights,
the cathedral glowing across the square. "How does it feel?" / "It feels like home." / "It feels like home to me too."

Shots:  1-150   from inside the room, behind them: two silhouettes against the window and the lit cathedral
      151-280   side two-shot in the lamp glow: she turns to him, he answers
      281-432   close: she rests her head on his shoulder, both close their eyes
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

SHOTS = dict(a=1, b=151, c=281, end=432)
R = Vector((-12.0, -65.0, 10.0))      # the room: window wall on the facade of the south houses, facing the cathedral (+Y)
SILL = .55                             # window seat height (room floor = 0)
WH = 1.4                               # window height


def night_world():
    """Deep blue night with stars and a warm glow of city light low on the horizon."""
    w = bpy.data.worlds.new('Night'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    bg = N['Background']
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = 0; r.elements[0].color = (.12, .07, .06, 1)
    r.elements[1].position = .35; r.elements[1].color = (.004, .008, .025, 1)
    e = r.elements.new(.06); e.color = (.04, .04, .07, 1)
    L.new(sep.outputs['Z'], ramp.inputs['Fac'])
    vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 220; L.new(tc.outputs['Generated'], vo.inputs['Vector'])
    st = N.new('ShaderNodeMapRange'); st.inputs['From Min'].default_value = .06; st.inputs['From Max'].default_value = .0
    st.inputs['To Max'].default_value = 3.0; L.new(vo.outputs['Distance'], st.inputs['Value'])
    hz = N.new('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = .05; hz.inputs['From Max'].default_value = .2
    L.new(sep.outputs['Z'], hz.inputs['Value'])
    sm = N.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'; L.new(st.outputs['Result'], sm.inputs[0]); L.new(hz.outputs['Result'], sm.inputs[1])
    add = N.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
    L.new(sm.outputs[0], add.inputs['Factor']); L.new(ramp.outputs['Color'], add.inputs['A'])
    add.inputs['B'].default_value = (.8, .85, 1, 1)
    L.new(add.outputs['Result'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0


def night_city(coll):
    """Scene 1's square at night: the cathedral floodlit, windows glowing."""
    import scene01_helsinki as s1
    importlib.reload(s1)
    s1.build_cathedral(coll)
    s1.build_city(coll)
    for n in ('SouthHouses1', 'SouthHouses1_cornice', 'SouthHouses1_roof'):   # the room is inside this house
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    for m in bpy.data.materials:
        if m.node_tree and 'Melt' in m.node_tree.nodes:
            m.node_tree.nodes['Melt'].outputs[0].default_value = .7
    # lit windows: every facade's window grid glows warm, some brighter than others
    for m in bpy.data.materials:
        if not (m.name.endswith('_fx') or m.name.endswith('_fy')):
            continue
        N, L = m.node_tree.nodes, m.node_tree.links
        br = next(n for n in N if n.bl_idname == 'ShaderNodeTexBrick'); b = N['Principled BSDF']
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
        L.new(br.outputs['Fac'], inv.inputs[1])
        vo = N.new('ShaderNodeTexWhiteNoise'); vo.noise_dimensions = '3D'
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (.4, .4, .5)
        L.new(N['Texture Coordinate'].outputs['Object'] if 'Texture Coordinate' in N else N.new('ShaderNodeTexCoord').outputs['Object'], mp.inputs['Vector'])
        L.new(mp.outputs['Vector'], vo.inputs['Vector'])
        on = N.new('ShaderNodeMath'); on.operation = 'GREATER_THAN'; on.inputs[1].default_value = .45; L.new(vo.outputs['Value'], on.inputs[0])
        k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; L.new(inv.outputs[0], k.inputs[0]); L.new(on.outputs[0], k.inputs[1])
        k2 = N.new('ShaderNodeMath'); k2.operation = 'MULTIPLY'; k2.inputs[1].default_value = 3.0; L.new(k.outputs[0], k2.inputs[0])
        L.new(k2.outputs[0], b.inputs['Emission Strength']); b.inputs['Emission Color'].default_value = (1, .62, .3, 1)
    # floodlights on the cathedral
    cx, cy = s1.CATH
    for i, (x, y, z, tgt) in enumerate([(-22, 6, 1, (0, 32, 14)), (22, 6, 1, (0, 32, 14)), (0, -4, 1, (0, 30, 10)),
                                        (-30, 20, 3, (0, cy, 32)), (30, 20, 3, (0, cy, 32))]):
        ld = bpy.data.lights.new(f'Flood{i}', 'SPOT'); ld.energy = 3e4; ld.color = (1, .86, .65); ld.spot_size = math.radians(40)
        ld.spot_blend = .6; ld.shadow_soft_size = 1
        o = link(bpy.data.objects.new(f'Flood{i}', ld), coll); o.location = (x, y, z)
        o.rotation_euler = (Vector(tgt) - Vector((x, y, z))).to_track_quat('-Z', 'Y').to_euler()
    # street lamps glow
    for o in bpy.data.objects:
        if o.name.endswith('_lantern'):
            film.point_light(o.name + '_light', o.location + Vector((0, 0, .3)), 400, (1, .7, .4), .2)
    gl = bpy.data.materials.get('LampGlass')
    if gl:
        gl.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 8


def room(coll):
    """The little room: walls with a deep window, a window seat with cushions, a blanket, fairy lights, a lamp."""
    wall = mat('RoomWall', (.36, .26, .2), rough=.85)
    wood = mat('Floor', (.22, .12, .06), rough=.5)
    frame = mat('WindowFrame', (.75, .72, .66), rough=.5)
    seat = mat('SeatWood', (.4, .28, .18), rough=.55)
    T = lambda x, y, z: (R.x + x, R.y + y, R.z + z)
    box('RoomFloor', (6, 4.2, .1), T(0, -2.1, -.1), wood, coll)
    box('RoomCeil', (6, 4.2, .1), T(0, -2.1, 2.25), wall, coll)
    box('RoomBack', (6, .1, 2.35), T(0, -4.2, -.05), wall, coll)
    box('RoomLeft', (.1, 4.2, 2.35), T(-3, -2.1, -.05), wall, coll)
    box('RoomRight', (.1, 4.2, 2.35), T(3, -2.1, -.05), wall, coll)
    # window wall (thick, with an opening x -0.75..0.75, z SILL..SILL+1.05)
    ww, wd = 1.3, .35
    box('WallL', (3 - ww, wd, 2.35), T(-(3 + ww) / 2, wd / 2 - .02, -.05), wall, coll)
    box('WallR', (3 - ww, wd, 2.35), T((3 + ww) / 2, wd / 2 - .02, -.05), wall, coll)
    box('WallBelow', (2 * ww, wd, SILL + .05), T(0, wd / 2 - .02, -.05), wall, coll)
    box('WallAbove', (2 * ww, wd, 2.3 - SILL - WH), T(0, wd / 2 - .02, SILL + WH), wall, coll)
    # the window seat sticks out into the room
    box('WindowSeat', (2 * ww + .3, .62, .05), T(0, -.12, SILL - .05), seat, coll)
    box('SeatFront', (2 * ww + .3, .05, SILL - .05), T(0, -.42, 0), seat, coll)
    # window frame and mullions (open window: no glass, so the city is crisp)
    for x in (-ww, ww):
        box(f'Jamb{x}', (.07, .08, WH), T(x, .3, SILL), frame, coll)
    for z in (SILL, SILL + WH - .05):
        box(f'Frame{z}', (2 * ww + .07, .08, .05), T(0, .3, z), frame, coll)
    # cushions, blanket, a mug, a plant
    cush = mat('Cushion', (.55, .25, .2), rough=.9); cush2 = mat('Cushion2', (.7, .6, .45), rough=.9)
    blob('CushionL', T(-1.05, -.05, SILL + .18), (.14, .2, .2), coll, cush, rough=.12, seed=1)
    blob('CushionR', T(1.05, -.05, SILL + .18), (.14, .2, .2), coll, cush2, rough=.12, seed=2)
    knit = mat('Blanket', (.42, .2, .16), rough=1.0, sss=.1)
    bl = blob('Blanket', T(0, -.08, SILL + .07), (.7, .3, .1), coll, knit, sub=4, rough=.18, seed=3)
    blob('BlanketDrape', T(.15, -.43, SILL - .12), (.5, .06, .18), coll, knit, sub=3, rough=.2, seed=4)
    mug = mat('Mug', (.7, .2, .15), rough=.3, coat=.5)
    cylinder('Mug', .05, .1, T(1.0, .14, SILL), mug, coll, n=16)
    pot = mat('Pot', (.45, .22, .12), rough=.7); leaf = mat('PlantLeaf', (.05, .14, .04), rough=.6)
    cylinder('Pot', .09, .14, T(-1.05, .14, SILL), pot, coll, n=16, r2=.11)
    for i in range(7):
        blob(f'Leaf{i}', T(-1.05 + .06 * math.cos(i * 2.4), .14 + .06 * math.sin(i * 2.4), SILL + .2 + .03 * i), (.05, .02, .08), coll, leaf, sub=2, seed=10 + i)
    # curtains framing the window, a bookshelf, pictures and a rug: a lived-in room
    cloth = mat('Curtain', (.55, .32, .25), rough=.95, sss=.15)
    for sx in (-1, 1):
        for k in range(5):
            blob(f'Curtain{sx}{k}', T(sx * (ww + .12 + k * .07), -.12, 1.15), (.06, .05, 1.15), coll, cloth, sub=3, rough=.08, seed=k + (sx > 0) * 10)
    shelf = mat('Shelf', (.3, .18, .1), rough=.6)
    for i, z in enumerate((.3, .75, 1.2, 1.65)):
        box(f'Shelf{i}', (1.6, .3, .03), T(-1.7, -4.0, z), shelf, coll)
    box('ShelfSideL', (.03, .3, 1.75), T(-2.5, -4.0, 0), shelf, coll); box('ShelfSideR', (.03, .3, 1.75), T(-.9, -4.0, 0), shelf, coll)
    bookc = [(.5, .12, .1), (.1, .25, .35), (.6, .5, .25), (.2, .3, .15), (.7, .65, .55), (.35, .1, .2)]
    rngb = np.random.default_rng(3)
    for i, z in enumerate((.33, .78, 1.23)):
        x = -2.45
        while x < -1.0:
            w_ = rngb.uniform(.03, .07); h_ = rngb.uniform(.22, .34)
            box(f'Book{i}_{x:.2f}', (w_, .2, h_), T(x + w_ / 2, -3.98, z), mat(f'BookM{i}{int(x * 100)}', bookc[rngb.integers(6)], rough=.6), coll)
            x += w_ + .005
    for i, (x, z, w_, h_) in enumerate(((.6, 1.2, .5, .4), (1.3, 1.35, .35, .45), (.95, .8, .3, .25))):
        box(f'Frame{i}', (w_, .03, h_), T(x, -4.13, z), mat('PicFrame', (.6, .45, .25), rough=.4, metal=.5), coll)
        box(f'Picture{i}', (w_ - .06, .03, h_ - .06), T(x, -4.12, z + .03), mat(f'Pic{i}', [(.4, .5, .6), (.6, .45, .3), (.3, .45, .3)][i], rough=.5), coll)
    rugm = mat('RoomRug', (.4, .12, .1), rough=1.0)
    box('RoomRug', (2.4, 1.6, .012), T(0, -1.6, 0), rugm, coll)
    candle = mat('Candle', (.95, .9, .8), rough=.6); flame = emit_mat('Flame', (1, .6, .25), 30)
    for i, x in enumerate((-.25, .25)):
        cylinder(f'Candle{i}', .025, .08 + i * .03, T(x * 3.2, .18, SILL), candle, coll, n=10)
        blob(f'Flame{i}', T(x * 3.2, .18, SILL + .1 + i * .03), (.008, .008, .018), coll, flame, sub=1)
    film.point_light('CandleGlow', T(0, .1, SILL + .2), 6, (1, .6, .3), .05)
    # fairy lights around the window
    bulb = emit_mat('FairyBulb', (1, .65, .3), 25)
    pts = []
    for i in range(26):
        t = i / 25
        x = -ww - .06 + (2 * ww + .12) * t; z = SILL + WH + .04 + .07 * math.sin(t * PI * 4) - .08 * math.sin(t * PI)
        pts.append((x, z))
    for i in range(12):
        t = i / 11; pts.append((-ww - .08, SILL + WH - t * 1.1)); pts.append((ww + .08, SILL + WH - t * 1.1))
    for i, (x, z) in enumerate(pts):
        blob(f'Bulb{i}', T(x, -.02, z), (.012, .012, .015), coll, bulb, sub=1, rough=0)
    film.area_light('FairyGlow', T(0, -.25, SILL + WH + .05), T(0, -.6, SILL + .3), 30, 2.6, (1, .62, .3))
    # table lamp beside the window seat
    shade = mat('LampShade', (1, .8, .55), rough=.9, emission=(1, .6, .3), strength=3, transmission=.3)
    cylinder('LampBase', .06, .02, T(1.75, -.35, SILL), mat('LampMetal', (.6, .45, .25), rough=.3, metal=1), coll, n=16)
    cylinder('LampStem', .012, .35, T(1.75, -.35, SILL), bpy.data.materials['LampMetal'], coll, n=8)
    box('SideTable', (.4, .4, SILL), T(1.75, -.35, 0), seat, coll)
    cylinder('LampShade', .14, .16, T(1.75, -.35, SILL + .32), shade, coll, n=24, r2=.09, cap=False)
    film.point_light('LampLight', T(1.75, -.35, SILL + .4), 60, (1, .58, .28), .1)
    film.area_light('RoomBounce', T(0, -3.5, 1.5), T(0, 0, .8), 15, 2.5, (1, .6, .35))
    film.area_light('NightFill', T(-.4, 1.8, 1.3), T(0, -.2, SILL + .35), 9, 1.5, (.55, .65, 1.0))      # cool city glow on their faces
    film.area_light('FaceWarm', T(.5, .9, SILL + 1.2), T(0, -.2, SILL + .35), 7, .6, (1, .6, .3))      # the fairy lights from the front


def build():
    bears = film.import_bears()
    film.HAZE.update(color=(.03, .035, .06), start=40.0, dist=260.0, strength=.55)
    night_world()
    city = film.new_coll('NightCity'); night_city(city)
    rm = film.new_coll('Room'); room(rm)
    he = bears.build_bear('he'); she = bears.build_bear('she')
    rz = PI                                     # facing the window (+Y)
    by = R.y - .16; bz = R.z + SILL
    bears.place(he, 1, (R.x - .3, by, bz), rz, sitting=True)
    bears.place(she, 1, (R.x + .3, by, bz), rz, sitting=True)
    # "How does it feel?" - she turns to him
    bears.turn_head(she, 40, yaw=0); bears.turn_head(she, 62, yaw=35, nod=4); bears.turn_head(she, 150, yaw=38, nod=4)
    # "It feels like home." - he turns to her
    bears.turn_head(he, 160, yaw=0); bears.turn_head(he, 182, yaw=-32, nod=4); bears.turn_head(he, 270, yaw=-30, nod=6)
    bears.blink(he, 120); bears.blink(she, 210)
    # "It feels like home to me too." - she rests her head on his shoulder, they close their eyes
    lean = {'spine': (8, 0, -12), 'head': (6, 18, -16)}
    bears.key_pose(she, 290, {'spine': (6, 0, 0), 'head': (4, 38, 0)})
    bears.key_pose(she, 330, lean); bears.key_pose(she, SHOTS['end'], lean)
    bears.hold(she, 290); she.location.x -= .06; bears.hold(she, 330)
    bears.key_pose(he, 300, {'head': (6, -30, 0)}); bears.key_pose(he, 350, {'head': (6, -12, 12), 'spine': (6, 0, 4)})
    bears.key_pose(he, SHOTS['end'], {'head': (6, -12, 12), 'spine': (6, 0, 4)})
    bears.set_eyes(she, 'closed', 338); bears.set_eyes(he, 'closed', 362)
    # cameras
    A = film.camera('Cam2a_Behind', [(SHOTS['a'], (R.x + 1.6, R.y - 3.6, R.z + 1.35), (R.x - .3, R.y + 6, R.z + 1.0)),
                                     (SHOTS['b'] - 1, (R.x + 1.2, R.y - 3.0, R.z + 1.3), (R.x - .2, R.y + 6, R.z + 1.0))], lens=18, fstop=4,
                    focus=(R.x, R.y - .2, R.z + .9))
    B = film.camera('Cam2b_Window', [(SHOTS['b'], (R.x - .8, R.y + 2.7, R.z + 1.2), (R.x, R.y - .16, R.z + 1.02)),
                                     (SHOTS['c'] - 1, (R.x - .65, R.y + 2.45, R.z + 1.18), (R.x, R.y - .16, R.z + 1.02))], lens=30, fstop=2.8,
                    focus=(R.x, R.y - .16, R.z + .85))
    C = film.camera('Cam2c_Close', [(SHOTS['c'], (R.x + .35, R.y + 2.4, R.z + 1.05), (R.x - .02, R.y - .16, R.z + .92)),
                                    (SHOTS['end'], (R.x + .3, R.y + 2.15, R.z + 1.03), (R.x - .02, R.y - .16, R.z + .92))], lens=36, fstop=2.0,
                    focus=(R.x, R.y - .16, R.z + .9))
    for f, cam in ((SHOTS['a'], A), (SHOTS['b'], B), (SHOTS['c'], C)):
        film.cut(f, cam)


if __name__ == '__main__':
    film.run(build, '02', still_frame=300)
