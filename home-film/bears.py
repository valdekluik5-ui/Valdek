"""
Home - the two plush bears from Quiet Moon, rebuilt for Blender 5.3.

This is a faithful port of sculptBear()/buildBear() in quiet-moon/index.html:
the same signed-distance sculpt (one smooth body), the same surface-nets mesh,
the same 12-bone skeleton and skin weights, the same face (small glossy eyes close
together, short snout, rounded nose, stitched mouth), tan paw pads with toe beans,
her blush, three eyelashes and the rose. The shell fur of the app is replaced by
real Blender hair (particle hair: works in EEVEE and Cycles and follows the rig).

Use from another script:
    import bears
    he  = bears.build_bear('he',  location=(0.25, 0, 0))
    she = bears.build_bear('she', location=(-0.25, 0, 0))
    bears.set_eyes(she, 'closed', frame=165)       # 'open' | 'closed' | 'heart'
    bears.key_pose(he, 120, {'shoulder.R': (0, 0, 20)})

Coordinates: the app is Y-up with the bear facing +Z. Blender is Z-up; the bear
faces -Y (it looks at you in Front view, numpad 1). 1 Blender unit = the app unit
(the bear is about 1 unit tall).
"""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

PI = math.pi

# ---------------------------------------------------------------- design settings
# Copied from DEF in quiet-moon/index.html (keep these in sync with the app).
DEF = {
    'he': dict(size=1, headSize=1, bodyW=1, bodyH=1, armLen=1, legLen=1, limbFat=1, earSize=1, earAngle=56, earHeight=50,
               eyeSize=1, eyeGap=17, eyeY=3, muzSize=1, muzY=-15, noseSize=1, tummy=.35, cheekAlpha=0,
               fur='#6b3f24', light='#b5865f', pad='#8f644a', nose='#4a2e24', cheek='#ff8fab', acc='none', accCol='#e7a3a8',
               furLen=1, shag=1),
    'she': dict(size=.94, headSize=1.02, bodyW=.95, bodyH=.96, armLen=1, legLen=.97, limbFat=.95, earSize=.95, earAngle=56,
                earHeight=51, eyeSize=1.05, eyeGap=17, eyeY=3, muzSize=.95, muzY=-15, noseSize=.9, tummy=.35, cheekAlpha=.18,
                fur='#94603a', light='#d0a47a', pad='#a77a5c', nose='#5a372a', cheek='#ff9fb6', acc='rose', accCol='#e7a3a8',
                furLen=1, shag=1),
}

# Fur look (Blender hair). Lengths are in bear units (bear ~1 tall).
FUR = dict(
    length=.014,         # strand length on the body (the app's shells were .014 + droop)
    parents=9000,        # guide hairs on the body
    children=32,         # rendered strands per guide (viewport shows 4)
    root=.0017, tip=.0004,   # strand thickness at root / tip
    droop=.3,            # how much the fur falls downward (the app's "shaggy")
    clump=.35, rough=.004,
)
DETAIL = .0085           # sculpt grid step (app used .0115). Smaller = smoother, slower to build.


def srgb(h):
    """'#rrggbb' -> linear RGB tuple (what Blender stores)."""
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)


def mix_hex(a, b, t):
    a = a.lstrip('#'); b = b.lstrip('#')
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]; cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join('%02x' % round(x + (y - x) * t) for x, y in zip(ca, cb))


def T2B(p):
    """app (x, y-up, z-front) -> Blender (x, y-back, z-up)."""
    return Vector((p[0], -p[2], p[1]))


# ---------------------------------------------------------------- the sculpt (numpy port)
def _ell(X, Y, Z, c, r):
    x = (X - c[0]) / r[0]; y = (Y - c[1]) / r[1]; z = (Z - c[2]) / r[2]
    k0 = np.sqrt(x * x + y * y + z * z)
    k1 = np.sqrt((x / r[0]) ** 2 + (y / r[1]) ** 2 + (z / r[2]) ** 2)
    return np.where(k1 < 1e-6, -min(r), k0 * (k0 - 1) / np.maximum(k1, 1e-6))


def _cap(X, Y, Z, a, b, ra, rb):
    bx, by, bz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    qx, qy, qz = X - a[0], Y - a[1], Z - a[2]
    h = np.clip((qx * bx + qy * by + qz * bz) / (bx * bx + by * by + bz * bz), 0, 1)
    return np.sqrt((qx - bx * h) ** 2 + (qy - by * h) ** 2 + (qz - bz * h) ** 2) - (ra + (rb - ra) * h)


def _smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * .25


def _smax(a, b, k):
    return -_smin(-a, -b, k)


def sculpt(c):
    """Returns F: the bear's key points (app coordinates) and F['sdf'](X,Y,Z,tags=False)."""
    sin, cos = math.sin, math.cos
    hs, bw, bh, fat, ll, al = c['headSize'], c['bodyW'], c['bodyH'], c['limbFat'], c['legLen'], c['armLen']
    hipY = .25 * ll; beltY = hipY + .05; chestY = hipY + .28 * bh; neckY = hipY + .42 * bh
    head = [0, neckY + .215 * hs, .01]; HR = [.275 * hs, .25 * hs, .255 * hs]

    def dirOn(az, el):
        a, e = az * PI / 180, el * PI / 180
        return [sin(a) * cos(e), sin(e), cos(a) * cos(e)]

    def onH(az, el, k=1):
        d = dirOn(az, el)
        return [head[0] + d[0] * HR[0] * k, head[1] + d[1] * HR[1] * k, head[2] + d[2] * HR[2] * k]

    mzD = dirOn(0, c['muzY'])
    muz = [head[0], head[1] + mzD[1] * HR[1] * .8, head[2] + mzD[2] * HR[2] * .95]
    MR = [.11 * c['muzSize'] * hs, .085 * c['muzSize'] * hs, .105 * c['muzSize'] * hs]
    ears = [dict(p=onH(s * c['earAngle'], c['earHeight'], 1.02), s=s,
                 r=[.095 * c['earSize'] * hs, .088 * c['earSize'] * hs, .052 * c['earSize'] * hs]) for s in (1, -1)]
    eyes = [onH(s * c['eyeGap'], c['eyeY'], 1.0) for s in (1, -1)]
    sh = [[.19 * bw, neckY - .055, 0], [-.19 * bw, neckY - .055, 0]]
    arm = []
    for i, p in enumerate(sh):
        s = -1 if i else 1
        arm.append(dict(sh=p, el=[p[0] + s * .085, p[1] - .12 * al, p[2] + .04], wr=[p[0] + s * .1, p[1] - .23 * al, p[2] + .1], s=s))
    legs = [dict(hip=[s * .1 * bw, hipY + .02, 0], knee=[s * .11 * bw, hipY * .5, .02], ank=[s * .115 * bw, .07, .02],
                 foot=[s * .115 * bw, .058, .055], s=s) for s in (1, -1)]
    tail = [0, beltY + .02, -.2 * bw]
    F = dict(hs=hs, bw=bw, bh=bh, hipY=hipY, chestY=chestY, neckY=neckY, head=head, HR=HR, muz=muz, MR=MR,
             ears=ears, eyes=eyes, arm=arm, legs=legs, tail=tail)
    eyeS = c['eyeSize']; earA = c['earAngle']

    def sdf(X, Y, Z, tags=False):
        main = _ell(X, Y, Z, [0, beltY + .08 * bh, 0], [.21 * bw, .2 * bh, .19 * bw]); d = main
        chest = _ell(X, Y, Z, [0, chestY, -.005], [.17 * bw, .17 * bh, .15 * bw]); d = _smin(d, chest, .09)
        bel = _ell(X, Y, Z, [0, beltY + .07 * bh, .05], [.17 * bw, .15 * bh, .15 * bw]); d = _smin(d, bel, .05)
        hd = _ell(X, Y, Z, head, HR)
        h = _smin(hd, _ell(X, Y, Z, [head[0], head[1] - .06 * hs, head[2] + .04], [.21 * hs, .15 * hs, .19 * hs]), .06)
        m = _ell(X, Y, Z, muz, MR); h = _smin(h, m, .04)
        er = np.full(X.shape, 1e9); ei = np.full(X.shape, 1e9)
        for e in ears:
            p, r = e['p'], e['r']
            dx, dy, dz = X - p[0], Y - p[1], Z - p[2]
            a = -e['s'] * earA * PI / 180 * .55; ca, sa = math.cos(a), math.sin(a)
            lx = dx * ca - dz * sa; lz = dx * sa + dz * ca
            ed = _ell(lx, dy, lz, [0, 0, 0], r)
            cup = _ell(lx, dy, lz, [0, -.008, r[2] * 1.05], [r[0] * .62, r[1] * .6, r[2] * .7])
            ed = _smax(ed, -cup, .012)
            er = np.minimum(er, ed); ei = np.minimum(ei, cup)
        h = _smin(h, er, .025)
        for p in eyes:
            h = _smax(h, -_ell(X, Y, Z, p, [.03 * eyeS, .032 * eyeS, .02]), .015)
        d = _smin(d, h, .07)
        a_all = np.full(X.shape, 1e9)
        for A in arm:
            q = _cap(X, Y, Z, A['sh'], A['el'], .062 * fat, .056 * fat)
            q = _smin(q, _cap(X, Y, Z, A['el'], A['wr'], .056 * fat, .05 * fat), .025)
            q = _smin(q, _ell(X, Y, Z, [A['wr'][0], A['wr'][1] - .012, A['wr'][2] + .005], [.055 * fat, .06 * fat, .05 * fat]), .025)
            ds = np.sqrt((X - A['sh'][0]) ** 2 + (Y - A['sh'][1]) ** 2 + (Z - A['sh'][2]) ** 2)
            k = .004 + .045 * np.clip(1 - ds / .1, 0, 1)
            # smin with a per-point k
            hh = np.maximum(k - np.abs(d - q), 0) / k
            d = np.minimum(d, q) - hh * hh * k * .25
            a_all = np.minimum(a_all, q)
        lg = np.full(X.shape, 1e9)
        for L in legs:
            q = _cap(X, Y, Z, L['hip'], L['knee'], .085 * fat, .078 * fat)
            q = _smin(q, _cap(X, Y, Z, L['knee'], L['ank'], .078 * fat, .07 * fat), .03)
            q = _smin(q, _ell(X, Y, Z, L['foot'], [.075 * fat, .058, .1 * fat]), .04)
            lg = np.minimum(lg, q)
        lg = _smax(lg, -(Y - .004), .012); d = _smin(d, lg, .06)
        tl = _ell(X, Y, Z, tail, [.05, .05, .045]); d = _smin(d, tl, .03)
        if not tags:
            return d
        parts = np.stack([np.minimum(np.minimum(main, bel), chest), hd, m, er, a_all, lg, tl])
        return d, dict(part=np.argmin(parts, axis=0), cup=ei, bel=bel)   # 0 body 1 head 2 muz 3 ear 4 arm 5 leg 6 tail

    F['sdf'] = sdf
    return F


def surface_nets(F, step):
    """Vectorised version of mesh() in the app: one vertex per surface cell, quads across sign changes,
    then each vertex is snapped onto the true surface."""
    X0, X1, Y0, Y1, Z0, Z1 = -.42, .42, -.01, F['head'][1] + F['HR'][1] + .12, -.32, .42
    xs = X0 + np.arange(int(math.ceil((X1 - X0) / step)) + 1) * step
    ys = Y0 + np.arange(int(math.ceil((Y1 - Y0) / step)) + 1) * step
    zs = Z0 + np.arange(int(math.ceil((Z1 - Z0) / step)) + 1) * step
    GX, GY, GZ = np.meshgrid(xs, ys, zs, indexing='ij')
    val = F['sdf'](GX, GY, GZ)
    inside = val < 0
    nx, ny, nz = val.shape
    O = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    E = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    cv = [val[o[0]:nx - 1 + o[0], o[1]:ny - 1 + o[1], o[2]:nz - 1 + o[2]] for o in O]
    ci = [v < 0 for v in cv]
    cnt = sum(c.astype(np.int8) for c in ci)
    active = (cnt > 0) & (cnt < 8)
    S = np.zeros(active.shape + (3,)); n = np.zeros(active.shape)
    for a, b in E:
        cr = ci[a] != ci[b]
        t = np.where(cr, cv[a] / np.where(cr, cv[a] - cv[b], 1), 0)
        for ax in range(3):
            S[..., ax] += np.where(cr, O[a][ax] + (O[b][ax] - O[a][ax]) * t, 0)
        n += cr
    idx = np.argwhere(active)
    vid = np.full(active.shape, -1, dtype=np.int64); vid[tuple(idx.T)] = np.arange(len(idx))
    off = S[active] / n[active][:, None]
    P = np.stack([X0 + (idx[:, 0] + off[:, 0]) * step, Y0 + (idx[:, 1] + off[:, 1]) * step, Z0 + (idx[:, 2] + off[:, 2]) * step], 1)
    quads = []
    s = slice(1, None)
    # x-edges
    cr = inside[:-1, 1:-1, 1:-1] != inside[1:, 1:-1, 1:-1]
    I, J, K = np.nonzero(cr); J = J + 1; K = K + 1; fl = ~inside[I, J, K]
    q = np.stack([vid[I, J - 1, K - 1], vid[I, J, K - 1], vid[I, J, K], vid[I, J - 1, K]], 1); quads.append((q, fl))
    # y-edges
    cr = inside[1:-1, :-1, 1:-1] != inside[1:-1, 1:, 1:-1]
    I, J, K = np.nonzero(cr); I = I + 1; K = K + 1; fl = ~inside[I, J, K]
    q = np.stack([vid[I - 1, J, K - 1], vid[I - 1, J, K], vid[I, J, K], vid[I, J, K - 1]], 1); quads.append((q, fl))
    # z-edges
    cr = inside[1:-1, 1:-1, :-1] != inside[1:-1, 1:-1, 1:]
    I, J, K = np.nonzero(cr); I = I + 1; J = J + 1; fl = ~inside[I, J, K]
    q = np.stack([vid[I - 1, J - 1, K], vid[I, J - 1, K], vid[I, J, K], vid[I - 1, J, K]], 1); quads.append((q, fl))
    faces = []
    for q, fl in quads:
        ok = (q >= 0).all(1)
        q, fl = q[ok], fl[ok]
        q[fl] = q[fl][:, ::-1]
        faces.append(q)
    faces = np.concatenate(faces)
    # snap to the surface
    e = step * .5
    x, y, z = P[:, 0].copy(), P[:, 1].copy(), P[:, 2].copy()
    sd = F['sdf']
    for _ in range(3):
        d = sd(x, y, z)
        gx = sd(x + e, y, z) - sd(x - e, y, z); gy = sd(x, y + e, z) - sd(x, y - e, z); gz = sd(x, y, z + e) - sd(x, y, z - e)
        gl = np.sqrt(gx * gx + gy * gy + gz * gz); gl[gl == 0] = 1
        x -= d * gx / gl; y -= d * gy / gl; z -= d * gz / gl
    return np.stack([x, y, z], 1), faces


# ---------------------------------------------------------------- materials
def _mat(name, color, rough=.5, emission=None, emit_strength=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = .03
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1); b.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    return m


def _body_material(name):
    """Skin under the fur: the vertex colours painted from the sculpt regions."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'Col'; at.location = (-400, 200)
    nt.links.new(at.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .85
    return m


def _fur_material(name, color_hex, root_dark=.7, tip_light=1.25, var=.3):
    """Fur strands: darker at the root, lighter at the tip, each strand a shade lighter or darker."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    hi = N.new('ShaderNodeHairInfo'); hi.location = (-900, 200)
    base = srgb(color_hex)
    # root -> tip gradient
    ramp = N.new('ShaderNodeValToRGB'); ramp.location = (-650, 300)
    ramp.color_ramp.elements[0].color = (*[c * root_dark for c in base], 1)
    ramp.color_ramp.elements[1].color = (*[min(1, c * tip_light) for c in base], 1)
    ramp.color_ramp.elements[0].position = .05
    L.new(hi.outputs['Intercept'], ramp.inputs['Fac'])
    # per-strand variation
    mr = N.new('ShaderNodeMapRange'); mr.location = (-650, 0)
    mr.inputs['To Min'].default_value = 1 - var / 2; mr.inputs['To Max'].default_value = 1 + var / 2
    L.new(hi.outputs['Random'], mr.inputs['Value'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.location = (-350, 200)
    mul.inputs['Factor'].default_value = 1
    L.new(ramp.outputs['Color'], mul.inputs['A'])
    cm = N.new('ShaderNodeCombineColor'); cm.location = (-480, 0)
    for k in ('Red', 'Green', 'Blue'):
        L.new(mr.outputs['Result'], cm.inputs[k])
    L.new(cm.outputs['Color'], mul.inputs['B'])
    L.new(mul.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .55
    b.inputs['Specular IOR Level'].default_value = .35
    # soft light through the fur tips (lovely against the sunset)
    b.inputs['Subsurface Weight'].default_value = .0
    b.inputs['Sheen Weight'].default_value = .6
    b.inputs['Sheen Tint'].default_value = (*[min(1, c * 1.6) for c in base], 1)
    return m


# ---------------------------------------------------------------- helpers to make objects
def _link(obj, coll):
    coll.objects.link(obj)
    return obj


def _mesh_obj(name, verts, faces, coll, mat=None, smooth=True, origin=None):
    origin = Vector(origin) if origin is not None else Vector()
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(Vector(v) - origin) for v in verts], [], [tuple(f) for f in faces])
    me.validate(); me.update()
    if smooth:
        me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = origin
    return _link(ob, coll)


def _ellipsoid(name, center, radii, frame, coll, mat, seg=24, ring=16, taper=0.0):
    """Ellipsoid in a local frame (3x3 Matrix: columns = local x,y,z in Blender world), centre in world."""
    verts, faces = [], []
    for j in range(ring + 1):
        v = PI * j / ring
        for i in range(seg):
            u = 2 * PI * i / seg
            x, y, z = math.sin(v) * math.cos(u), math.cos(v), math.sin(v) * math.sin(u)
            x *= 1 + taper * y
            verts.append(Vector(center) + frame @ Vector((x * radii[0], y * radii[1], z * radii[2])))
    for j in range(ring):
        for i in range(seg):
            a = j * seg + i; b = j * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    ob = _mesh_obj(name, verts, faces, coll, mat, origin=center)
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free(); me.shade_smooth()
    return ob


def _tube(name, pts, radius, coll, mat, origin=None):
    """A soft round tube through world points (used for lashes, mouth stitches, closed eyes)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1)
    origin = Vector(origin) if origin is not None else Vector(pts[0])
    for p, q in zip(sp.points, pts):
        v = Vector(q) - origin; p.co = (v.x, v.y, v.z, 1)
    sp.use_endpoint_u = True; sp.order_u = min(3, len(pts))
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu); ob.location = origin
    return _link(ob, coll)


def _heart(name, center, size, frame, coll, mat):
    """Glossy puffy heart (the heart eyes): a 2D heart filled, extruded and bevelled."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    cu.extrude = .12 * size; cu.bevel_depth = .09 * size; cu.bevel_resolution = 4
    # classic heart curve, without the sharp notch at the top (it made a spike once bevelled)
    ts = [2 * PI * i / 56 for i in range(56)]
    ts = [t for t in ts if .22 < t < 2 * PI - .22]
    sp = cu.splines.new('POLY'); sp.points.add(len(ts) - 1)
    for t, p in zip(ts, sp.points):
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        p.co = (x / 34 * size, (y + 2) / 34 * size, 0, 1)
    sp.use_cyclic_u = True
    tmp = bpy.data.objects.new(name + '_tmp', cu); coll.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    me.transform(Matrix.Translation(Vector(center)).to_3x3().to_4x4())  # no-op, keep local
    R = frame.to_4x4()
    me.transform(R)
    me.materials.clear(); me.materials.append(mat); me.shade_smooth()
    ob = bpy.data.objects.new(name, me); ob.location = Vector(center)
    return _link(ob, coll)


def _frame_facing(d_app, up_app=(0, 1, 0)):
    """three.js lookAt for an object: local +Z points along d, local X = up x d. Returned in Blender axes."""
    z = Vector(d_app).normalized(); up = Vector(up_app)
    x = up.cross(z).normalized(); y = z.cross(x)
    X, Y, Z = T2B(x), T2B(y), T2B(z)
    return Matrix((X, Y, Z)).transposed()


def _parent_keep(ob, parent, bone=None):
    bpy.context.view_layer.update()          # make sure matrix_world is current before we keep it
    mw = ob.matrix_world.copy()
    ob.parent = parent
    if bone:
        ob.parent_type = 'BONE'; ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw


def _empty(name, location, frame, coll, size=.02):
    e = bpy.data.objects.new(name, None); e.empty_display_size = size; e.empty_display_type = 'SPHERE'
    e.matrix_world = Matrix.Translation(location) @ frame.to_4x4()
    return _link(e, coll)


# ---------------------------------------------------------------- the bear
BONES = ['root', 'pelvis', 'spine', 'head', 'shoulder.L', 'shoulder.R', 'forearm.L', 'forearm.R', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R']
PARENT = [-1, 0, 1, 2, 2, 2, 4, 5, 1, 1, 8, 9]


def build_bear(who, location=(0, 0, 0), rotation_z=0.0, name=None, fur=True, overrides=None):
    """Build one bear. Returns its armature object (move/rotate/pose that).
    The armature has a custom property 'eyes': 0 open, 1 closed, 2 heart (keyframe it, or use set_eyes)."""
    c = dict(DEF[who]); c.update(overrides or {})
    girl = who == 'she'
    name = name or ('He' if who == 'he' else 'She')
    coll = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(coll)
    F = sculpt(c)
    P, faces = surface_nets(F, DETAIL)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    _, tg = F['sdf'](x, y, z, tags=True)
    part, cup, bel = tg['part'], tg['cup'], tg['bel']
    nV = len(P)

    # ---- regions -> colours and fur
    cFur = np.array(srgb(c['fur'])); cSn = np.array(srgb(mix_hex(c['fur'], c['light'], .8)))
    cBel = np.array(srgb(mix_hex(c['fur'], c['light'], c['tummy']))); cEar = np.array(srgb(mix_hex(c['fur'], '#2a160c', .3)))
    cPad = np.array(srgb(c['pad']))
    col = np.tile(cFur * .7, (nV, 1))
    g_main = np.ones(nV); g_light = np.zeros(nV); g_belly = np.zeros(nV); g_ear = np.zeros(nV); g_blush = np.zeros(nV)
    flen = np.ones(nV)
    muz = part == 2
    col[muz] = cSn; g_main[muz] = 0; g_light[muz] = 1; flen[muz] = .3
    earc = (part == 3) & (cup < .006)
    col[earc] = cEar * .8; g_main[earc] = 0; g_ear[earc] = 1; flen[earc] = .35
    flen[part == 3] = np.minimum(flen[part == 3], .6)   # ears clipped short so their round shape reads
    belly = (part == 0) & (bel < .004) & (z > .02)
    col[belly] = cBel * .8; g_main[belly] = 0; g_belly[belly] = 1
    # paw pads with toe beans on the soles
    for i, L in enumerate(F['legs']):
        side = (x > 0) if i == 0 else (x <= 0)
        sole = (part == 5) & (y < .03) & side
        lx = (x - L['foot'][0]) / .06; lz = (z - L['foot'][2] + .01) / .075
        pad = lx * lx * 1.2 + lz * lz < .55
        bean = np.zeros(nV, bool)
        for bx, bz in [(-.55, .9), (-.18, 1.08), (.18, 1.08), (.55, .9)]:
            bean |= (lx - bx) ** 2 + (lz - bz) ** 2 < .06
        pp = sole & (pad | bean)
        col[pp] = cPad; g_main[pp] = 0; g_belly[pp] = 0
        flen[sole & ~pp & (y < .012)] = .3
    # palm pads on the front of the paws
    for A in F['arm']:
        w = A['wr']; pc = np.array([w[0], w[1] - .03, w[2] + .045])
        dd = np.sqrt((x - pc[0]) ** 2 + (y - pc[1]) ** 2 + (z - pc[2]) ** 2)
        pp = (part == 4) & (dd < .028)
        col[pp] = cPad; g_main[pp] = 0
    # short fur and no fur around the eyes, so the glossy eyes stay visible
    for p in F['eyes']:
        dd = np.sqrt((x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2) / c['eyeSize']
        flen = np.minimum(flen, np.clip((dd - .03) / .05, 0, 1) * .8 + .2)
        bald = dd < .036
        g_main[bald] = 0; col[bald] = cFur * .45
    # face fur a little shorter overall (a plush face is clipped short)
    hd = F['head']; face = (part == 1) & (z > hd[2] + .1) & (y < hd[1] + .08)
    flen[face] = np.minimum(flen[face], .45)
    # her blush: pink-tinted fur on the cheeks
    if c['cheekAlpha'] > .01:
        for s in (1, -1):
            a, e = s * 38 * PI / 180, -12 * PI / 180
            d = [math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)]
            cp = [hd[0] + d[0] * F['HR'][0], hd[1] + d[1] * F['HR'][1], hd[2] + d[2] * F['HR'][2]]
            dd = np.sqrt((x - cp[0]) ** 2 + (y - cp[1]) ** 2 + (z - cp[2]) ** 2)
            wgt = np.clip(1 - dd / .05, 0, 1) ** .7 * (part == 1)
            g_blush = np.maximum(g_blush, wgt)
        pink = np.array(srgb(c['cheek']))
        col = col * (1 - g_blush[:, None] * .5) + pink * (g_blush[:, None] * .5)
        g_main = g_main * (1 - g_blush)

    # ---- the mesh (in Blender axes)
    PB = np.stack([x, -z, y], 1)
    me = bpy.data.meshes.new(name + '_body')
    me.vertices.add(nV); me.vertices.foreach_set('co', PB.astype(np.float32).ravel())
    nF = len(faces)
    me.loops.add(nF * 4); me.polygons.add(nF)
    me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    me.polygons.foreach_set('loop_start', (np.arange(nF) * 4).astype(np.int32))
    me.update(calc_edges=True); me.validate()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    me.shade_smooth()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.concatenate([col, np.ones((nV, 1))], 1).astype(np.float32).ravel())
    body = bpy.data.objects.new(name + '_body', me); coll.objects.link(body)

    # ---- skin weights (same rule as the app: 1/(d+.012)^5 to the nearest bone segments of the part)
    BP = [[0, 0, 0], [0, F['hipY'], 0], [0, F['hipY'] + .03, 0], [0, F['neckY'], 0], F['arm'][0]['sh'], F['arm'][1]['sh'],
          F['arm'][0]['el'], F['arm'][1]['el'], F['legs'][0]['hip'], F['legs'][1]['hip'], F['legs'][0]['knee'], F['legs'][1]['knee']]

    def seg(a, b):
        return _cap(x, y, z, a, b, 0, 0)

    INF = np.full(nV, 1e3)
    D = np.tile(INF, (12, 1))
    isH = (part == 1) | (part == 2) | (part == 3); isA = part == 4; isL = part == 5; isB = ~(isH | isA | isL)
    D[3] = np.where(isH, seg(BP[3], F['head']), D[3]); D[2] = np.where(isH, seg(BP[2], BP[3]) * 1.6, D[2])
    for i in (0, 1):
        A = F['arm'][i]; side = (x > 0) if i == 0 else (x <= 0); m = isA & side
        D[4 + i] = np.where(m, seg(A['sh'], A['el']), D[4 + i]); D[6 + i] = np.where(m, seg(A['el'], A['wr']), D[6 + i])
        D[2] = np.where(m, seg(BP[2], BP[3]) * 1.8, D[2])
        L = F['legs'][i]; m = isL & side
        D[8 + i] = np.where(m, seg(L['hip'], L['knee']), D[8 + i])
        D[10 + i] = np.where(m, np.minimum(seg(L['knee'], L['ank']), seg(L['ank'], L['foot'])), D[10 + i])
        D[1] = np.where(m, seg(BP[1], BP[2]) * 2.2, D[1])
    D[1] = np.where(isB, seg([0, 0, 0], BP[1]), D[1]); D[2] = np.where(isB, seg(BP[2], BP[3]), D[2])
    D[3] = np.where(isB, seg(BP[3], F['head']) * 1.4, D[3])
    W = 1 / (D + .012) ** 5; W[D >= 1e3] = 0
    top = np.argsort(-W, axis=0)[:4]
    Wt = np.take_along_axis(W, top, 0); Wt = Wt / Wt.sum(0)
    groups = [body.vertex_groups.new(name=b) for b in BONES]
    for k in range(4):
        for bi in range(12):
            sel = np.nonzero((top[k] == bi) & (Wt[k] > 1e-4))[0]
            for v, wv in zip(sel.tolist(), Wt[k][sel].tolist()):
                groups[bi].add([v], wv, 'REPLACE')
    for gname, arr in (('fur_main', g_main), ('fur_light', g_light), ('fur_belly', g_belly), ('fur_ear', g_ear),
                       ('fur_blush', g_blush), ('fur_len', flen)):
        g = body.vertex_groups.new(name=gname)
        nz_ = np.nonzero(arr > 1e-4)[0]
        for v, wv in zip(nz_.tolist(), arr[nz_].tolist()):
            g.add([v], wv, 'REPLACE')

    # ---- armature
    ad = bpy.data.armatures.new(name + '_rig'); ad.display_type = 'STICK'
    arm = bpy.data.objects.new(name, ad); coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    tails = {0: [0, .08, 0], 1: BP[2], 2: BP[3], 3: [0, F['head'][1] + .12, F['head'][2]],
             4: BP[6], 5: BP[7], 6: F['arm'][0]['wr'], 7: F['arm'][1]['wr'],
             8: BP[10], 9: BP[11], 10: F['legs'][0]['ank'], 11: F['legs'][1]['ank']}
    ebs = []
    for i, bn in enumerate(BONES):
        eb = ad.edit_bones.new(bn); eb.head = T2B(BP[i]); eb.tail = T2B(tails[i])
        if i == 1:
            eb.tail = T2B([0, F['hipY'] + .06, 0])
        eb.align_roll(Vector((0, -1, 0)) if i not in (0, 1, 2, 3) else Vector((0, -1, 0)))
        ebs.append(eb)
    for i, p in enumerate(PARENT):
        if p >= 0:
            ebs[i].parent = ebs[p]
    # spine/head point up: give them a forward-facing Z as well
    for i in (0, 1, 2, 3):
        ebs[i].align_roll(Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    body.parent = arm
    mod = body.modifiers.new('Rig', 'ARMATURE'); mod.object = arm
    arm['eyes'] = 0.0
    arm.id_properties_ui('eyes').update(min=0, max=2, description='0 open, 1 closed, 2 heart eyes')
    arm['who'] = who

    # ---- materials
    m_body = _body_material(name + '_skin'); me.materials.append(m_body)
    fur_mats = {
        'fur_main': _fur_material(name + '_fur', c['fur']),
        'fur_light': _fur_material(name + '_fur_snout', mix_hex(c['fur'], c['light'], .8), root_dark=.75, var=.15),
        'fur_belly': _fur_material(name + '_fur_belly', mix_hex(c['fur'], c['light'], c['tummy'])),
        'fur_ear': _fur_material(name + '_fur_ear', mix_hex(c['fur'], '#2a160c', .3)),
        'fur_blush': _fur_material(name + '_fur_blush', mix_hex(c['fur'], c['cheek'], .38)),
    }
    for m in fur_mats.values():
        me.materials.append(m)

    # ---- fur (particle hair; sits after the Armature modifier so it follows every pose)
    if fur:
        area_frac = {'fur_main': 1, 'fur_light': .12, 'fur_belly': .18, 'fur_ear': .06, 'fur_blush': .05}
        for gname, m in fur_mats.items():
            if gname == 'fur_blush' and c['cheekAlpha'] <= .01:
                continue
            add_fur(body, gname, m.name, int(FUR['parents'] * area_frac[gname] * c['furLen'] ** 0), c)
        sub = body.modifiers.new('Smooth', 'SUBSURF'); sub.levels = 0; sub.render_levels = 1

    # ---- face parts, riding on the head bone
    hp = F['head']
    eyeM = _mat('BearEye', (.004, .003, .002), rough=.05, coat=1)
    ringM = _mat(name + '_eyering', srgb('#3a2216'), rough=.3)
    whiteM = _mat('BearHighlight', (1, 1, 1), rough=.2, emission=(1, 1, 1), emit_strength=3)
    noseM = _mat(name + '_nose', srgb(c['nose']), rough=.3, coat=.6)
    heartM = _mat('BearHeart', srgb('#ff4f86'), rough=.15, emission=srgb('#ff2a6a'), emit_strength=.6, coat=1)
    lashM = _mat('BearLash', srgb('#1c100a'), rough=.6)
    es = c['eyeSize']
    eye_parts = []
    for i, p in enumerate(F['eyes']):
        side = 'L' if i == 0 else 'R'
        d = [p[0] - hp[0], p[1] - hp[1], p[2] - hp[2]]
        fr = _frame_facing(d)
        cen = T2B(p)
        root_e = _empty(f'{name}_eye.{side}', cen, fr, coll)
        st = {}
        for state in ('open', 'closed', 'heart'):
            st[state] = _empty(f'{name}_eye.{side}.{state}', cen, fr, coll, size=.01)
        L = lambda v: cen + fr @ Vector(v)
        obs = [
            _ellipsoid(f'{name}_eyering.{side}', L((0, 0, 0)), (.03 * es, .031 * es, .016), fr, coll, ringM),
            _ellipsoid(f'{name}_eyeball.{side}', L((0, 0, .004)), (.026 * es, .027 * es, .019), fr, coll, eyeM),
            _ellipsoid(f'{name}_glint1.{side}', L((.008 * es, .01 * es, .02)), (.0065 * es, .0065 * es, .003), fr, coll, whiteM, 12, 8),
            _ellipsoid(f'{name}_glint2.{side}', L((-.008 * es, -.008 * es, .02)), (.003 * es, .003 * es, .002), fr, coll, whiteM, 10, 6),
        ]
        if girl:   # three soft curved lashes on the outer upper edge
            sd = 1 if i == 0 else -1
            for k in range(3):
                a0 = (55 + k * 22) * PI / 180; r0 = .031 * es; bx, by = sd * math.cos(a0) * r0, math.sin(a0) * r0
                pts = [L((bx, by, .006)), L((bx + sd * .008 * es, by + .006 * es, .012)), L((bx + sd * .017 * es, by + .008 * es, .01))]
                obs.append(_tube(f'{name}_lash{k}.{side}', pts, .0022 * es, coll, lashM, origin=cen))
        for o in obs:
            _parent_keep(o, st['open'])
        # closed: a soft curved line
        arc = [L((math.cos(t) * .02 * es, -math.sin(t) * .02 * es + .005, .012)) for t in np.linspace(.15, PI - .15, 7)]
        _parent_keep(_tube(f'{name}_eyeclosed.{side}', arc, .0035, coll, ringM, origin=cen), st['closed'])
        # heart eyes
        hrt = _heart(f'{name}_eyeheart.{side}', L((0, -.004, .012)), .05 * es, fr, coll, heartM)
        g = _ellipsoid(f'{name}_heartglint.{side}', L((-.012 * es, .006 * es, .022)), (.005 * es, .0035 * es, .002), fr, coll, whiteM, 10, 6)
        _parent_keep(hrt, st['heart']); _parent_keep(g, st['heart'])
        for s_ in st.values():
            _parent_keep(s_, root_e)
        _parent_keep(root_e, arm, 'head')
        eye_parts.append(st)
    # drivers: 'eyes' property switches which set is visible (scale 0 hides it in every engine)
    for st in eye_parts:
        for k, state in enumerate(('open', 'closed', 'heart')):
            for ax in range(3):
                fc = st[state].driver_add('scale', ax); dr = fc.driver; dr.type = 'SCRIPTED'
                v = dr.variables.new(); v.name = 'e'; v.type = 'SINGLE_PROP'
                v.targets[0].id = arm; v.targets[0].data_path = '["eyes"]'
                dr.expression = f'max(0.0001, 1 - abs(round(e) - {k}))'

    # nose: soft rounded triangle, glossy
    sc_ = c['noseSize'] * c['headSize']
    mzF = [F['muz'][0], F['muz'][1] + F['MR'][1] * .35, F['muz'][2] + F['MR'][2] * .92]
    nfr = Matrix.Rotation(-.25, 3, 'X')    # app rotation.x=-.25 (app axes)
    nfrB = _frame_facing((0, math.sin(.25), math.cos(.25)))
    nose = _ellipsoid(f'{name}_nose', T2B(mzF), (.04 * sc_, .028 * sc_, .028 * sc_), nfrB, coll, noseM, 32, 20, taper=.35)
    _parent_keep(nose, arm, 'head')
    ng = _ellipsoid(f'{name}_noseglint', T2B(mzF) + nfrB @ Vector((-.01 * sc_, .013 * sc_, .024 * sc_)), (.008 * sc_, .004 * sc_, .002),
                    nfrB, coll, whiteM, 10, 6)
    ng.data.materials[0] = _mat('BearNoseGlint', (1, 1, 1), rough=.2, emission=(1, 1, 1), emit_strength=.8)
    _parent_keep(ng, arm, 'head')
    # stitched mouth (a touch further out than in the app so it shows through the short snout fur)
    mo = [F['muz'][0], F['muz'][1] - F['MR'][1] * .15, F['muz'][2] + F['MR'][2] * 1.04]
    M = lambda v: T2B([mo[0] + v[0], mo[1] + v[1], mo[2] + v[2]])
    for k, pts in enumerate([[(0, .028, 0), (0, .016, .002), (0, .004, .002)],
                             [(0, .004, .002), (-.012, -.006, -.002), (-.024, -.002, -.008)],
                             [(0, .004, .002), (.012, -.006, -.002), (.024, -.002, -.008)]]):
        t = _tube(f'{name}_mouth{k}', [M(p) for p in pts], .0028, coll, noseM)
        _parent_keep(t, arm, 'head')

    # her rose
    if c['acc'] == 'rose':
        a, e = -36 * PI / 180, 46 * PI / 180
        hpnt = [hp[0] + math.sin(a) * math.cos(e) * F['HR'][0] * 1.17, hp[1] + math.sin(e) * F['HR'][1] * 1.17,
                hp[2] + math.cos(a) * math.cos(e) * F['HR'][2] * 1.17]
        r = build_rose(f'{name}_rose', c['accCol'], coll)
        r.scale = (1.3,) * 3
        r.rotation_euler = (-.5, .4, 0)   # tilt outward like in the app
        r.rotation_euler = (math.radians(90) - .5, 0, .4)
        r.location = T2B(hpnt)
        bpy.context.view_layer.update()
        _parent_keep(r, arm, 'head')

    # ---- place and scale the whole bear
    arm.scale = (c['size'],) * 3
    arm.location = location
    arm.rotation_euler = (0, 0, rotation_z)
    arm['sitDrop'] = (F['hipY'] - .075 + .1) * c['size']   # how far to lower the rig to sit on the ground
    bpy.context.view_layer.update()
    return arm


def add_fur(body, group, mat_name, count, c):
    mod = body.modifiers.new('Fur_' + group, 'PARTICLE_SYSTEM')
    ps = mod.particle_system
    s = ps.settings
    s.name = body.name + '_' + group
    s.type = 'HAIR'; s.count = count; s.hair_length = FUR['length'] * c['furLen']
    s.emit_from = 'FACE'; s.use_emit_random = True; s.distribution = 'JIT'; s.use_even_distribution = True
    s.use_advanced_hair = True
    # with advanced hair the strand length comes from these velocities (not hair_length)
    L = FUR['length'] * c['furLen']
    s.normal_factor = L
    s.object_align_factor = (0, 0, -FUR['droop'] * c['shag'] * L)   # fur falls downward a little (shaggy plush)
    s.factor_random = .25 * L
    s.material_slot = mat_name
    s.use_hair_bspline = True; s.display_step = 3; s.render_step = 4
    s.child_type = 'INTERPOLATED'; s.child_percent = 4; s.rendered_child_count = FUR['children']
    s.child_radius = .02; s.child_roundness = .3
    s.clump_factor = FUR['clump']; s.clump_shape = -.2
    s.roughness_1 = FUR['rough'] * .4; s.roughness_1_size = 1.2
    s.roughness_2 = FUR['rough']; s.roughness_2_size = 1; s.roughness_2_threshold = .1
    s.roughness_endpoint = FUR['rough'] * .5; s.roughness_end_shape = 1.5
    s.child_length = 1; s.child_length_threshold = .3
    s.radius_scale = FUR['root']; s.root_radius = 1; s.tip_radius = FUR['tip'] / FUR['root']; s.use_close_tip = True
    s.display_percentage = 40
    ps.vertex_group_density = group
    ps.vertex_group_length = 'fur_len'
    ps.seed = hash(group) % 1000
    return mod


def build_rose(name, col_hex, coll):
    """A little rose: cupped petals in a spiral and two leaves (the app's rose, a bit richer)."""
    pet = _mat('RosePetal', srgb(col_hex), rough=.45)
    pet_dark = _mat('RosePetalDeep', srgb(mix_hex(col_hex, '#7a2b3a', .35)), rough=.45)
    pet.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = .3
    leaf = _mat('RoseLeaf', srgb('#8a9a6a'), rough=.6)
    root = bpy.data.objects.new(name, None); root.empty_display_size = .03; coll.objects.link(root)
    for i in range(13):
        a = i * 2.4; r = .004 + i * .0026
        size = .011 + i * .0012
        ctr = Vector((math.cos(a) * r, math.sin(a) * r, .006 - i * .0011))
        fr = Matrix.Rotation(a + PI / 2, 3, 'Z') @ Matrix.Rotation(.25 + i * .07, 3, 'X')
        p = _ellipsoid(f'{name}_petal{i}', ctr, (size, size * .85, size * .38), fr, coll, pet_dark if i < 4 else pet, 16, 10)
        p.parent = root
    for s in (-1, 1):
        fr = Matrix.Rotation(s * .6 + (PI if s < 0 else 0), 3, 'Z')
        l = _ellipsoid(f'{name}_leaf{s}', Vector((s * .03, -.016, -.006)), (.02, .009, .003), fr, coll, leaf, 14, 8)
        l.parent = root
    return root


# ---------------------------------------------------------------- posing and animation helpers
def sit(arm, ground_z=0.0):
    """Lower the rig so the bear sits on a surface at ground_z, legs forward."""
    arm.location.z = ground_z - arm['sitDrop'] + .1 * arm.scale[0]


def key_pose(arm, frame, rot=None, interp='BEZIER'):
    """rot: {bone: (x, y, z) degrees}. Bones' local axes: Y runs along the bone, Z points to the bear's front.
    So for an arm/leg: +X swings it forward; Z swings it sideways (shoulder.L: +Z out to the side, shoulder.R: -Z out);
    for spine/head: X nods forward, Z leans sideways (- = toward the bear's left), Y turns (+ = to its left)."""
    for bn, (rx, ry, rz) in (rot or {}).items():
        pb = arm.pose.bones[bn]
        pb.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
        pb.keyframe_insert('rotation_euler', frame=frame)


def set_eyes(arm, state, frame):
    v = {'open': 0, 'closed': 1, 'heart': 2}[state]
    if frame > 0 and not any(fc.data_path == '["eyes"]' for fc in _fcurves(arm)):
        arm['eyes'] = 0.0; arm.keyframe_insert('["eyes"]', frame=0)      # eyes start open
    arm['eyes'] = float(v)
    arm.keyframe_insert('["eyes"]', frame=frame)
    if arm.animation_data and arm.animation_data.action:
        for fc in _fcurves(arm):
            if fc.data_path == '["eyes"]':
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'


def _fcurves(ob):
    """F-curves of an object's action (Blender 5 layered actions, with a fallback for older files)."""
    act = ob.animation_data.action if ob.animation_data else None
    if not act:
        return []
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, 'layers', []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def blink(arm, frame, length=4):
    set_eyes(arm, 'closed', frame); set_eyes(arm, 'open', frame + length)


# ---------------------------------------------------------------- movement helpers used by all scenes
STAND = {'spine': (0, 0, 0), 'head': (0, 0, 0), 'shoulder.L': (0, 0, 0), 'shoulder.R': (0, 0, 0),
         'forearm.L': (0, 0, 0), 'forearm.R': (0, 0, 0), 'thigh.L': (0, 0, 0), 'thigh.R': (0, 0, 0),
         'shin.L': (0, 0, 0), 'shin.R': (0, 0, 0), 'pelvis': (0, 0, 0)}
SIT = dict(STAND, **{'thigh.L': (88, 0, -4), 'thigh.R': (88, 0, 4), 'shin.L': (-80, 0, 0), 'shin.R': (-80, 0, 0),
                     'spine': (6, 0, 0), 'shoulder.L': (12, 0, 8), 'shoulder.R': (12, 0, -8),
                     'forearm.L': (10, 0, 0), 'forearm.R': (10, 0, 0)})


def facing(dx, dy):
    """rotation_z that makes a bear (front = -Y) face the direction (dx, dy)."""
    return math.atan2(dx, -dy)


def place(arm, frame, loc, rot_z=None, sitting=False, pose=None):
    """Put the bear somewhere at a frame (a hard jump: use at shot starts). Keys location/rotation and a full pose."""
    x, y, z = loc
    if sitting:
        z = z - arm['sitDrop'] + .1 * arm.scale[0]
    arm.location = (x, y, z)
    if rot_z is not None:
        arm.rotation_euler = (0, 0, rot_z)
    arm.keyframe_insert('location', frame=frame); arm.keyframe_insert('rotation_euler', frame=frame)
    key_pose(arm, frame, dict(SIT if sitting else STAND, **(pose or {})))
    _constant_at(arm, frame)


def hold(arm, frame):
    """Key the current transform again (so motion starts from here)."""
    arm.keyframe_insert('location', frame=frame); arm.keyframe_insert('rotation_euler', frame=frame)


def _constant_at(ob, frame):
    """Make the key just BEFORE `frame` jump (no blending across a cut)."""
    for fc in _fcurves(ob):
        prev = [kp for kp in fc.keyframe_points if kp.co.x < frame - .5]
        if prev:
            max(prev, key=lambda k: k.co.x).interpolation = 'CONSTANT'


def walk(arm, f0, f1, p0, p1, cycle=18, stride=26, ground=None, hold=None, phase=0):
    """Walk from p0 to p1 (x, y, z) between frames f0 and f1: legs and arms swing, the body bobs gently."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rz = facing(d.x, d.y)
    arm.rotation_euler = (0, 0, rz); arm.location = p0
    arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('rotation_euler', frame=f0)
    q = cycle / 4
    f = f0; k = 0
    while f <= f1 + .01:
        t = (f - f0) / max(f1 - f0, 1)
        ph = ((k + phase) % 4) * PI / 2
        s = math.sin(ph)
        pos = p0 + d * t
        bob = .012 * abs(math.cos(ph)) * arm.scale[0]
        arm.location = (pos.x, pos.y, pos.z + bob)
        arm.keyframe_insert('location', frame=f)
        key_pose(arm, f, {'thigh.L': (stride * s, 0, 0), 'thigh.R': (-stride * s, 0, 0),
                          'shin.L': (-max(0, -s) * 30, 0, 0), 'shin.R': (-max(0, s) * 30, 0, 0),
                          'shoulder.L': (-14 * s, 0, 6), 'shoulder.R': (14 * s, 0, -6),
                          'forearm.L': (8, 0, 0), 'forearm.R': (8, 0, 0),
                          'spine': (4, 0, 3 * s), 'pelvis': (0, 0, -2 * s)})
        if hold:
            key_pose(arm, f, hold)
        f += q; k += 1
    arm.location = p1; arm.keyframe_insert('location', frame=f1)
    key_pose(arm, f1, {'thigh.L': (0, 0, 0), 'thigh.R': (0, 0, 0), 'shin.L': (0, 0, 0), 'shin.R': (0, 0, 0),
                       'shoulder.L': (0, 0, 0), 'shoulder.R': (0, 0, 0), 'spine': (0, 0, 0), 'pelvis': (0, 0, 0)})
    if hold:
        key_pose(arm, f1, hold)
    for fc in _fcurves(arm):
        if fc.data_path == 'location':
            for kp in fc.keyframe_points:
                if f0 - .5 <= kp.co.x <= f1 + .5:
                    kp.interpolation = 'LINEAR'


def turn_head(arm, frame, yaw=0, nod=0, tilt=0):
    """Head turn in degrees: yaw + = to the bear's left, nod + = down, tilt + = toward its right shoulder."""
    key_pose(arm, frame, {'head': (nod, yaw, tilt)})
