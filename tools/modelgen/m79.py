"""
M79 グレネードランチャー（40mm、中折れ式の単発）のパーツと組み立て（単位 mm、メッシュ版）。

側面形は Wikimedia Commons の真横写真（右側面・照尺を起こした状態。米空軍、パブリックドメイン）からトレースした
輪郭（m79_outline.py ← trace_m79.py）。縮尺は全長 731mm（公表値）で合わせ、銃身 357mm（公表 14in）と太さ 45mm
（口径 40mm）が合うことを確かめた。左右の幅は推定（下の HALF_*。上面図が無い）。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面）、Y=0 トリガーガードの底、Z=0 トリガー、銃口 -Z。

中折れ: ボーン barrel（銃身・先台・照星・照尺・上の台）を蝶番の軸（HINGE、受け部の下の前）まわりに回すと、
銃口が下がって薬室の後ろが受け部の上に出る。留め金のレバー（ボーン charging_handle）を右へ回して外す。
照準器は米陸軍の教範 FM 23-31（1972、パブリックドメイン）の図 9-7・9-8 と、斜め後ろ・左側面の写真で形を確かめた
（真横の写真 1 枚で作った初版は照尺が細い棒になっていた。作者の指摘「サイトは違う形」）:
  照尺（ボーン rear_sight）= 幅 40mm の四角い枠。上の横棒・左の昇降ねじと上の歯車・枠の中を上下する照門の台
  （左に固定ナット、右につまみ）。既定の姿勢は前へ倒した状態（携行・100m までは台の固定照門で狙う）。
  起こすには軸まわりに +90°。台（銃身の帯の上）には固定照門の切り欠きと、右側面の星形の左右調整つまみ。
  照星 = 刃と、その左右の 2 枚のガード（穴の開いた耳）。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import m79_outline as O
from core import box, extrude_x, extrude_x_beveled, extrude_x_rounded, inflate_x, lathe
from m249 import x_cyl
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
WOOD = M.M79_STOCK
FOREND_WOOD = M.M79_FOREND
BLUED = M.M79_BLUED
FRAME_MAT = M.M79_FRAME

BORE_Y = 80.8
BARREL_R = 23.4             # 銃身の外径 47mm（写真）
BORE_R = 20.0               # 口径 40mm
BREECH_Z = -42.0            # 銃身の後端（受け部の前の面）＝薬室の後端
MUZZLE_Z = -398.8
HINGE = (-138.0, 46.0)      # 中折れの蝶番の軸（写真の受け部の下の前の丸い軸。Z, Y）
BREAK_DEG = 45.0            # 折る角度の目安（🟡 実物の値は未確認。弾の出し入れができる角度）

HALF_BUTT = 22.0
HALF_WRIST = 15.5
HALF_FRAME = 25.0           # 受け部の枠（銃身の両脇の板）
HALF_FOREND = 21.0
HALF_GUARD = 4.0
STOCK_H = 15.0
PAD_Z = 304.0               # 床尾板（ゴム）の前の面

# トリガーガードとトリガーの中心線と半幅 (Z, Y, r)。写真に細かい目盛りを重ねて読んだ
GUARD_PATH = [(15.0, 38.5, 1.8), (15.2, 30.0, 1.6), (14.8, 12.0, 1.6), (12.5, 5.0, 1.6), (7.0, 2.0, 1.5),
              (-5.0, 1.3, 1.5), (-20.0, 1.6, 1.5), (-29.0, 3.0, 1.5), (-34.5, 7.0, 1.6), (-36.5, 14.0, 1.7),
              (-37.0, 26.0, 2.2), (-37.0, 38.5, 2.6)]
TRIGGER_PATH = [(2.0, 38.5, 1.8), (0.5, 31.0, 1.5), (-0.8, 25.0, 1.3), (-2.0, 18.0, 1.2), (-4.0, 12.0, 1.0),
                (-6.5, 7.5, 0.9)]
CROSS_SCREW = (-44.0, 30.0)  # トリガーガードの前の、右へ突き出たねじの頭（写真）
LEAF_PIVOT = (-232.0, 116.0)   # 照尺の枠の軸（Z, Y）。写真で枠の足が台に入る所
LEAF_W = 40.0               # 枠の幅（FM 23-31 図 9-7 の枠の縦横比 0.34 × 写真の枠の高さ 118mm）
LEAF_TOP = 241.0            # 起こしたときの枠の上の端（写真）
CARRIER_Y = (199.0, 206.0)  # 照門の台（写真の位置。昇降ねじで上下する）
LEAF_FOLD_DEG = -90.0       # 既定の姿勢（前へ倒す）。起こすとき rear_sight を -90°（+90 だと銃身へ潜る）
SCREW_R, SCREW_GAP = 1.25, -0.3             # 昇降ねじ: 太さ 2.5mm の丸棒、左の縦棒との隙間（負は食い込み。隙間が空くと二重線に見える。作者「この線はなに？」）
BASE_Z = (-248.0, -224.0)   # 照尺の台（左右調整の台）の前後
BASE_Y = (105.0, 124.0)
FIXED_NOTCH_Y = 127.0       # 台の固定照門の切り欠きの底（照尺を倒したときの照準線）
FRONT_Z = (-396.0, -379.5)  # 照星のガードの前後（写真に細かい目盛りを重ねて読んだ）
FRONT_TOP = 130.5


def _ring(q):
    return list(q.exterior.coords)[:-1]


def _poly(o, holes=True):
    from shapely.geometry import Polygon
    return Polygon(o["outer"], o["holes"] if holes else [])


def _lerp(a, b, t):
    return a + (b - a) * min(1.0, max(0.0, t))


# ---------------------------------------------------------------- ストック
def stock_half(z, y):
    if z > 150.0:
        return HALF_BUTT
    if z > 40.0:
        return _lerp(HALF_WRIST, HALF_BUTT, (z - 60.0) / 90.0)
    return _lerp(HALF_WRIST, HALF_FRAME - 1.0, (40.0 - z) / 40.0)     # 受け部の後ろを包む所は受け部の幅へ


def _stock_radius(z, y, nz, ny):
    if z > PAD_Z - 0.5:
        return 3.0               # 床尾板との切り口
    if 20.0 < z < 150.0 and ny < -0.3:
        return 13.0              # 握りの下（丸い）
    if 20.0 < z < 150.0:
        return 11.0              # 握りの上
    if z < -20.0:
        return 2.0               # 受け部と接する前の縁
    if ny > 0.6:
        return 6.0
    return 9.0                   # 床尾の上下の縁


def stock():
    """木のストック（写真の光った所は穴として拾われるので外周だけ使う）と床尾板（ゴム）。"""
    import shapely
    from shapely.geometry import box as sbox
    g = _poly(O.STOCK, holes=False).simplify(0.3)
    wood = g.difference(sbox(PAD_Z, -100.0, 400.0, 300.0))
    pad = g.intersection(sbox(PAD_Z, -100.0, 400.0, 300.0))
    wood = max([q for q in getattr(wood, "geoms", [wood]) if q.geom_type == "Polygon"], key=lambda q: q.area)
    pad = max([q for q in getattr(pad, "geoms", [pad]) if q.geom_type == "Polygon"], key=lambda q: q.area)
    width = lambda z, y, f: stock_half(z, y) / STOCK_H
    out = [inflate_x(_ring(shapely.segmentize(wood, 10.0)), STOCK_H, WOOD, steps=4, width_fn=width,
                     radius_at=_stock_radius, cap_grid=14.0),
           extrude_x_beveled(_ring(pad), -HALF_BUTT, HALF_BUTT, 4.0, M.RUBBER, steps=2)]
    # 負い紐の環（床尾の下）
    out.append(x_cyl(244.0, 19.0, 3.5, -5.0, 5.0, BLUED, n=10))
    return out


# ---------------------------------------------------------------- 受け部（枠）
def frame():
    """受け部の枠（灰色のパーカー処理）: 後ろの縦の部分と銃身の下へ伸びる板。蝶番の軸の頭。"""
    g = _poly(O.FRAME).simplify(0.3)
    out = [extrude_x_rounded(_ring(g), [], lambda z, y: HALF_FRAME, 2.0, FRAME_MAT, steps=2)]
    z, y = HINGE
    out.append(x_cyl(z, y, 4.0, -HALF_FRAME - 0.8, HALF_FRAME + 0.8, BLUED, n=12))
    zc, yc = CROSS_SCREW
    out.append(x_cyl(zc, yc, 3.6, -HALF_FRAME - 7.0, HALF_FRAME, BLUED, n=12))
    return out


def trigger_guard():
    from m24 import _stroke
    return [extrude_x_beveled(_stroke(GUARD_PATH), -HALF_GUARD, HALF_GUARD, 0.8, BLUED, steps=1)]


def trigger():
    from m24 import _stroke
    return [extrude_x_beveled(_stroke(TRIGGER_PATH), -3.0, 3.0, 0.5, BLUED, steps=1)]


def safety():
    """安全装置（床尾の上の突起。前後に滑らせる）。"""
    return [extrude_x_beveled(_ring(_poly(O.SAFETY).simplify(0.2)), -4.0, 4.0, 1.0, BLUED, steps=1)]


def latch():
    """銃身の留め金のレバー（受け部の上の後ろ。右へ回して銃身を外す）。"""
    return [extrude_x_beveled(_ring(_poly(O.LATCH).simplify(0.2)), -6.0, 6.0, 1.5, BLUED, steps=1)]


# ---------------------------------------------------------------- 銃身まわり（中折れで一緒に動く）
def barrel():
    """銃身（太い筒。照尺の台の帯・銃口の帯）と、上の台・照星・先台。"""
    prof = [(MUZZLE_Z, BORE_R + 0.5), (MUZZLE_Z, 25.5), (MUZZLE_Z + 14.0, 25.5), (MUZZLE_Z + 15.0, BARREL_R),
            (-251.0, BARREL_R), (-250.0, 26.0), (-226.0, 26.0), (-225.0, BARREL_R), (BREECH_Z, BARREL_R),
            (BREECH_Z, BORE_R + 1.0)]
    out = [lathe(0, BORE_Y, prof, ar15_mesh.N_MID, BLUED, cap0=False, cap1=False),
           lathe(0, BORE_Y, [(MUZZLE_Z - 0.1, BORE_R + 0.5), (BREECH_Z + 0.1, BORE_R + 0.5)], ar15_mesh.N_MID, M.BORE,
                 cap0=False, cap1=False)]
    out.append(extrude_x_beveled(_ring(_poly(O.TOP_RIB).simplify(0.2)), -9.0, 9.0, 1.2, BLUED, steps=1))
    out += front_sight() + leaf_base()
    # 先台（木）: 銃身の下を包む
    fg = _poly(O.FOREND).simplify(0.3)
    out.append(extrude_x_rounded(_ring(fg), [], lambda z, y: HALF_FOREND, 6.0, FOREND_WOOD, steps=3))
    out.append(x_cyl(-252.0, 33.0, 3.5, -4.0, 4.0, BLUED, n=10))                         # 負い紐の環
    # 銃身の下の蝶番の受け（枠の板の間に入る）
    z, y = HINGE
    out.append(box(-HALF_FRAME + 2.0, y - 6.0, z - 8.0, HALF_FRAME - 2.0, BORE_Y - BARREL_R + 1.0, BREECH_Z - 1.0,
                   BLUED))
    return out


def front_sight():
    """照星: 刃（先が細い）と左右 2 枚のガード（上が丸く、穴と縦の切れ目）。台は銃身の上。"""
    from shapely.geometry import Point, box as sbox
    z0, z1 = FRONT_Z
    top = FRONT_TOP
    ear = sbox(z0, 104.0, z1, top - 5.5).union(sbox(z0 + 5.5, top - 6.0, z1 - 5.5, top)).union(
        Point(z0 + 5.5, top - 5.5).buffer(5.5, quad_segs=4)).union(Point(z1 - 5.5, top - 5.5).buffer(5.5, quad_segs=4))
    ear = ear.difference(Point((z0 + z1) / 2, 118.5).buffer(2.0, quad_segs=3))
    out = []
    for s in (1, -1):
        xa, xb = sorted((s * 4.0, s * 6.0))
        out.append(extrude_x(_ring(ear.simplify(0.1)), xa, xb, BLUED))
    zc = (z0 + z1) / 2
    blade = [(zc - 4.0, 104.0), (zc + 4.0, 104.0), (zc + 1.5, top - 2.5), (zc - 1.5, top - 2.5)]
    out.append(extrude_x_beveled(blade, -1.2, 1.2, 0.3, BLUED, steps=1))
    out.append(box(-6.0, BORE_Y + BARREL_R - 2.5, z0, 6.0, 105.0, z1, BLUED))
    return out


def leaf_base():
    """照尺の台（銃身の帯の上の左右調整の台）: 固定照門の切り欠き、右側面の星形のつまみ、左の目盛りの板。"""
    z0, z1 = BASE_Z
    y0, y1 = BASE_Y
    out = [box(-LEAF_W / 2, y0, z0, LEAF_W / 2, y1, z1, BLUED)]
    # 固定照門（後ろの端の 2 枚の耳の間の切り欠き）
    for s in (1, -1):
        xa, xb = sorted((s * 2.0, s * 8.0))
        out.append(box(xa, y1, z1 - 4.0, xb, FIXED_NOTCH_Y + 2.5, z1, BLUED))
    out.append(box(-2.0, y1, z1 - 4.0, 2.0, FIXED_NOTCH_Y, z1, BLUED))
    # 左右調整のつまみ（星形。6 枚の羽根を角柱で表す）
    zc, yc = -244.0, 117.0
    out.append(x_cyl(zc, yc, 6.0, -LEAF_W / 2 - 9.0, -LEAF_W / 2, BLUED, n=12))
    for k in range(3):
        a = math.pi * k / 3
        dz, dy = 9.5 * math.cos(a), 9.5 * math.sin(a)
        prof = [(zc - dz - 2.2 * math.sin(a), yc - dy + 2.2 * math.cos(a)), (zc + dz - 2.2 * math.sin(a), yc + dy + 2.2 * math.cos(a)),
                (zc + dz + 2.2 * math.sin(a), yc + dy - 2.2 * math.cos(a)), (zc - dz + 2.2 * math.sin(a), yc - dy - 2.2 * math.cos(a))]
        out.append(extrude_x_beveled(prof, -LEAF_W / 2 - 8.0, -LEAF_W / 2 - 2.0, 0.6, BLUED, steps=1))
    return out


def _bar(x0, x1, y0, y1, z0, z1, mat=None):
    """回転させられる角柱（MeshPart）。"""
    return extrude_x([(z0, y0), (z1, y0), (z1, y1), (z0, y1)], x0, x1, mat or BLUED)


def leaf_sight():
    """照尺の枠（起こした姿勢で作り、LEAF_FOLD_DEG だけ前へ倒す）。左右の縦棒・上の横棒・左の昇降ねじと上の歯車・
    照門の台（中央に照門の穴、左に固定ナット、右につまみ）。"""
    from m249 import rotated
    pz, py = LEAF_PIVOT
    w = LEAF_W / 2
    zf, zr = pz - 4.5, pz + 4.0            # 枠の前後（写真の枠の奥行き 8.5mm）
    out = []
    for s in (1, -1):                        # 縦棒
        xa, xb = sorted((s * (w - 4.5), s * w))
        out.append(_bar(xa, xb, py - 4.0, LEAF_TOP - 6.0, zf, zr))
    out.append(_bar(-w, w, LEAF_TOP - 6.0, LEAF_TOP, zf, zr))                 # 上の横棒
    out.append(_bar(-w, w, py - 4.0, py + 4.0, zf + 1.0, zr - 1.0))            # 下の横棒（軸）
    out.append(x_cyl(pz, py, 2.5, -w - 1.0, w + 1.0, BLUED, n=8))             # 軸のピン
    sx = w - 4.5 - SCREW_GAP - SCREW_R       # 昇降ねじの中心（左の縦棒の内側に沿わせる。離すと正体不明の線に見える）
    out.append(_swap_yz(lathe(sx, pz, [(py + 4.0, SCREW_R), (LEAF_TOP - 6.0, SCREW_R)], 8, BLUED)))  # 昇降ねじ（丸棒）
    out.append(_swap_yz(lathe(sx, pz, [(LEAF_TOP - 1.0, 0.5), (LEAF_TOP - 1.0, 5.0), (LEAF_TOP + 4.0, 5.0),
                                       (LEAF_TOP + 4.0, 0.5)], 12, BLUED)))     # 上の歯車（Y 方向の軸）
    cy0, cy1 = CARRIER_Y
    out.append(_bar(-w + 4.5, w - 4.5, cy0, cy1, zf - 1.0, zr + 1.0))          # 照門の台
    out.append(_bar(-3.0, 3.0, cy1, cy1 + 4.0, pz - 1.5, pz + 1.5))            # 照門（穴の開いた小さな板）
    out.append(lathe(0.0, cy1 + 2.0, [(pz - 1.6, 1.2), (pz + 1.6, 1.2)], 8, M.BORE))   # 照門の穴（前後に抜ける暗い円）
    out.append(x_cyl(pz, (cy0 + cy1) / 2, 3.0, w, w + 5.0, BLUED, n=10))      # 左の固定ナット
    out.append(x_cyl(pz - 6.0, 193.5, 4.0, -w - 4.0, -w, BLUED, n=10))        # 右のつまみ
    return rotated(out, "x", LEAF_FOLD_DEG, (0.0, py, pz))


def _swap_yz(m):
    """Z 軸の回転体を Y 軸の回転体にする（lathe(cx=x, cy=z, profile は y の範囲) で作ったものの Y と Z を入れ替える）。"""
    from core import MeshPart
    sw = lambda v: (v[0], v[2], v[1])
    n_ = None if m.normals is None else [[sw(v) for v in f] for f in m.normals]
    return MeshPart([sw(v) for v in m.verts], m.faces, m.mat, n_, m.charts, m.chart_uv, m.chart_edge)


# ---------------------------------------------------------------- 弾
def round_40mm(z_rear, y, x=0.0):
    """40×46mm 擲弾（M406 HE）: 全長 99mm。薬莢（アルミ・46mm）と弾頭（オリーブ色、先が丸い）。後ろの縁が z_rear。"""
    case = [(z_rear, 21.5), (z_rear - 2.0, 21.5), (z_rear - 2.3, 20.4), (z_rear - 46.0, 20.4)]
    head = [(z_rear - 46.0, 19.9), (z_rear - 70.0, 19.9), (z_rear - 82.0, 17.5), (z_rear - 92.0, 12.0),
            (z_rear - 97.5, 5.5), (z_rear - 99.0, 0.5)]
    head = [(z, r) for z, r in reversed(head)]
    case = [(z, r) for z, r in reversed(case)]
    return ([lathe(x, y, case, ar15_mesh.N_MID, M.M79_CASE, cap0=False, cap1=True)],
            [lathe(x, y, head, ar15_mesh.N_MID, M.M79_GRENADE, cap0=True, cap1=False)])


# ---------------------------------------------------------------- 組み立て
def build():
    from core import Model
    b = BORE_Y
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    hz, hy = HINGE
    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, BREECH_Z), "frame", frame())
    add("lower_receiver", "receiver", (0, 30.0, 0), "trigger_guard", trigger_guard())
    add("trigger", "root", (0, 38.0, 1.0), "trigger", trigger())
    add("selector", "receiver", (0, 95.0, 38.0), "safety", safety())
    add("charging_handle", "receiver", (0, 106.0, -10.0), "latch", latch())   # 銃身の留め金（縦の軸で右へ回す）
    add("stock", "root", (0, 60.0, 100.0), "stock", stock())

    add("barrel", "root", (0, hy, hz), "barrel", barrel())                  # 中折れ（蝶番の軸＝X 軸まわり）
    add("rear_sight", "barrel", (0, LEAF_PIVOT[1], LEAF_PIVOT[0]), "leaf_sight", leaf_sight())
    add("chamber", "barrel", (0, b, BREECH_Z), None, [])
    add("muzzle", "barrel", (0, b, MUZZLE_Z), None, [])
    add("handguard", "barrel", (0, 50.0, -230.0), None, [])

    # 弾: 薬室の中の 1 発（ammo＝薬莢、bullet＝弾頭）。装填用の 1 発（mag_ammo）は magazin の位置（薬室の口）
    case, head = round_40mm(BREECH_Z, b)
    add("ammo", "root", (0, b, BREECH_Z - 23.0), None, case)
    add("bullet", "ammo", (0, b, BREECH_Z - 70.0), None, head)
    add("magazin", "root", (0, b, BREECH_Z), None, [])
    c2, h2 = round_40mm(BREECH_Z, b)
    add("mag_ammo", "magazin", (0, b, BREECH_Z - 50.0), None, c2 + h2)

    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=FIXED_NOTCH_Y * K,
                 rear_sight_z=BASE_Z[1] * K, grip_center=(0, 40.0 * K, 70.0 * K))
    return m, parts
