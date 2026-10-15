"""
HK416 D14.5RS（14.5in 銃身・延長レール・HK のストックとグリップ）のパーツと組み立て（単位 mm、メッシュ版）。

AR-15 と同じ規格の部品（上部レシーバー・ボルトキャリア・チャージングハンドル・ダストカバー・トリガー・セレクター・
STANAG 弾倉・バッファチューブ）は ar15_mesh を HK416 の寸法（HKLayout）で呼んで使う。
HK 固有の部品（下部レシーバー・グリップ・ストック・レール付きハンドガード・照準器・銃身と消炎器）は作者提供の
三面図（hk416_outline.py ← trace_hk416.py）の側面形から作る。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面）、Y=0 ≒ グリップ底面、Z=0 トリガー、銃口 -Z。

図面・写真に無い所（推定）: 左右の幅（ハンドガード本体 42mm・レールの外 60mm、ストック 38mm、グリップ 30mm）、
ハンドガードの断面の形（三面図の正面図は簡略で読めない。角を落とした四角＋4 面のレール）。
"""
import math

import ar15_mesh as P
import ar15_parts
import materials as M
import sights
import hk416_outline as O
from ak47 import _clip, _yr, _zr
from ar15_parts import Layout
from core import box, extrude_x, extrude_x_beveled, inflate_x, lathe, densify
from m249 import rotated, x_cyl
from mp5 import extrude_z
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX


class HKLayout(Layout):
    """HK416 の取り合い寸法（三面図・写真から。AR-15 の Layout と違う所だけ）。"""
    upper_front_z = -121.0      # 上部レシーバー前端（図面）
    bolt_face_z = -102.0        # 前端の 19mm 奥（AR-15 と同じ）
    upper_rear_z = 82.0         # 上部・下部の後端（図面。M4A1 の写真より 12mm 後ろ）
    lower_rear_z = 82.0
    upper_top = 27.5            # レールの天面がボア軸の 36.5mm 上（図面 36.3・写真 38）。M4A1 の値（26）より高い
    rail_slots = 15             # 上部の上のレール（図面: 後ろの端 Z 62 から上部の前の端まで）
    buffer_end_z = 262.0        # ストックの中に隠れる
    sight_h = 58.0              # 照準線（図面の照門の穴の中心。AR-15 の 66mm より低い。レールが高く照準器が低いため）


L = HKLayout()
BORE_Y = L.bore_y
RAIL_TOP = L.rail_top_y                     # 191.9
SIGHT_Y = BORE_Y + L.sight_h
MUZZLE_Z = _zr({"outer": [(z, 0) for z, _ in O.MUZZLE_R]})[0]
REAR_SIGHT_Z = 23.0                         # 照門の照準板（図面の塔の中心）
FRONT_SIGHT_Z = -323.0                      # 照星のポスト（図面の塔の中心）
_EYE = sights.eye_z(0.0, REAR_SIGHT_Z)
POST_W = sights.POST_ANGLE * (_EYE - FRONT_SIGHT_Z)
REAR_HOLE = sights.HOLE_ANGLE * (_EYE - REAR_SIGHT_Z)

HALF_LOWER = 12.5
HALF_MAGWELL = 15.0
HALF_GUARD = 7.0
HALF_GRIP = 15.0
HALF_STOCK = 19.0
HALF_BUTT = 20.5

# ハンドガード（HK のレールシステム）: 角を落とした四角の本体の 4 面にピカティニーレール
HG_Z = (-118.0, -351.0)                     # 本体の後ろ・前の端（図面。後ろは上部の前の端に 3mm 重ねる）
HG_HALF = 21.0                              # 本体の半幅
HG_TOP = RAIL_TOP - 9.0                     # 本体の上面（上のレールの首の付け根）
HG_BOTTOM = _yr(O.HANDGUARD)[0] + 9.0       # 本体の下面（下のレールの首の付け根）
HG_CORNER_R = 10.0                         # 本体の角の丸み（作者提供の写真: HK の部品は角が丸い）
SIDE_RAIL_Y = BORE_Y + 1.5                  # 横のレールの中心（図面の縦の刻みの帯 Y 145〜169）
HG_WINDOWS = ((-172.0, -203.0), (-215.0, -246.0), (-259.0, -291.0), (-302.0, -335.0))   # 横の長い穴（図面）
HG_WINDOW_YS = ((BORE_Y - 13.5, BORE_Y - 10.5), (BORE_Y + 14.0, BORE_Y + 17.0))   # 横のレールの下・上（写真）


# ---------------------------------------------------------------- 下部レシーバー
def lower():
    """HK416 の下部レシーバー（図面）: 本体・弾倉の受け（太い）・トリガーガード（細い）に分けて押し出す。
    ガードはグリップの前の面まで延び、中の穴は図面の線の内側。"""
    o = O.LOWER["outer"]
    out = [extrude_x_beveled(p, -HALF_LOWER, HALF_LOWER, 3.5, M.RECEIVER, steps=2)
           for p in _clip(o, -41.0, 84.0, 100.0, 140.0)]
    out += [extrude_x_beveled(p, -HALF_MAGWELL, HALF_MAGWELL, 3.5, M.RECEIVER, steps=2)
            for p in _clip(o, -130.0, 50.0, -40.0, 140.0)]
    out += [extrude_x_beveled(p, -HALF_GUARD, HALF_GUARD, 1.5, M.RECEIVER, steps=1)
            for p in _clip(o, -41.0, 50.0, 10.0, 84.5)]
    for z, y in ((-102.0, 128.0), (64.0, 128.0)):            # 分解ピン（前・後ろ）
        for s in (1, -1):
            xa, xb = sorted((s * (HALF_LOWER - 0.5), s * (HALF_LOWER + 1.0)))
            out.append(x_cyl(z, y, 3.2, xa, xb, M.STEEL_DARK, n=10))
    return out


def pistol_grip():
    """HK のグリップ（図面）: 断面は丸く、上の端は下部レシーバーの幅に収める。"""
    def width(z, y, f):
        return 0.85 + 0.15 * min(1.0, max(0.0, f * 1.3))     # 前（指を掛ける側）を細く

    def radius(nz, ny):
        return 1.5 if ny > 0.6 else (5.0 if ny < -0.7 else HALF_GRIP - 1.0)
    return [inflate_x(densify(O.GRIP["outer"], 6.0), HALF_GRIP, M.POLYMER, steps=4, width_fn=width, radius_fn=radius,
                      cap_grid=10.0)]


RAIL_REAR_Z = 62.0          # 上部の上のレールの後ろの端（図面）
TUBE_Y, TUBE_R = BORE_Y + 1.0, 15.3   # バッファチューブ（図面: AR-15 より太く、中心がボア軸の高さ）
MAG_CATCH = (-40.0, BORE_Y - 28.0)    # 弾倉止めのボタン（右側面。AR-15 と同じ位置）


def buffer_tube():
    """バッファチューブ・キャッスルナット・エンドプレート（図面の太さ・高さ）。"""
    z0 = L.lower_rear_z
    return [lathe(0, TUBE_Y, [(z0, TUBE_R), (L.buffer_end_z, TUBE_R)], P.N_BIG, M.RECEIVER),
            lathe(0, TUBE_Y, [(z0, 18.0), (z0 + 9.0, 18.0)], 8, M.STEEL_DARK),
            box(-16, TUBE_Y - 18, z0 - 1.0, 16, TUBE_Y + 18, z0 + 3.0, M.STEEL_DARK)]


def mag_release():
    """弾倉止めのボタン（ボーン mag_release。右側面の丸いボタン）。"""
    z, y = MAG_CATCH
    return [x_cyl(z, y, 5.0, -HALF_LOWER - 2.5, -HALF_LOWER + 0.5, M.STEEL_DARK, n=12)]


# ---------------------------------------------------------------- ストック
def stock():
    """HK のストック（図面）: 本体と床尾のゴム。バッファチューブに沿って伸縮する（ボーン stock）。"""
    return [extrude_x_beveled(O.STOCK["outer"], -HALF_STOCK, HALF_STOCK, 9.0, M.POLYMER, steps=3),
            extrude_x_beveled(O.BUTT["outer"], -HALF_BUTT, HALF_BUTT, 7.0, M.RUBBER, steps=3)]


# ---------------------------------------------------------------- ハンドガード
def _section():
    """本体の断面（X, Y）: 角を丸めた四角（反時計回り）。"""
    h, t, b, r = HG_HALF, HG_TOP, HG_BOTTOM, HG_CORNER_R
    pts = []
    for cx, cy, a0 in ((h - r, t - r, 0), (-h + r, t - r, 90), (-h + r, b + r, 180), (h - r, b + r, 270)):
        pts += [(cx + r * math.cos(math.radians(a0 + 15 * k)), cy + r * math.sin(math.radians(a0 + 15 * k)))
                for k in range(7)]
    return pts


def _rail_y(z0, z1, y_base, up, mat):
    """上（up=1）・下（up=-1）のレール: 首と頭。刻みはテクスチャの縞（規約 0.5px/スロット）。"""
    n0, n1 = sorted((y_base, y_base + up * 4.0))
    h0, h1 = sorted((y_base + up * 4.0, y_base + up * 9.0))
    return [box(-8, n0, z1, 8, n1, z0, mat), box(-12, h0, z1, 12, h1, z0, mat)]


def _rail_x(z0, z1, x_base, side, mat):
    """横のレール（side=1 が左）。"""
    n0, n1 = sorted((x_base, x_base + side * 4.0))
    h0, h1 = sorted((x_base + side * 4.0, x_base + side * 9.0))
    y = SIDE_RAIL_Y
    return [box(n0, y - 8, z1, n1, y + 8, z0, mat), box(h0, y - 12, z1, h1, y + 12, z0, mat)]


def handguard():
    """HK のレールシステム（延長型）: 本体（角を落とした四角の筒）・4 面のレール・横の長い穴・前の端のガスブロックの覆い。"""
    z_rear, z_front = HG_Z
    out = [extrude_z(_section(), z_front, z_rear, M.RECEIVER)]
    out += _rail_y(z_rear + 2.0, z_front + 1.0, HG_TOP - 0.5, 1, M.RAIL)
    out += _rail_y(z_rear + 2.0, z_front + 1.0, HG_BOTTOM + 0.5, -1, M.RAIL_DOWN)
    for s in (1, -1):
        out += _rail_x(z_rear + 2.0, z_front + 1.0, s * (HG_HALF - 0.5), s, M.RAIL_SIDE)
        for (za, zb), (y0, y1) in ((w, y) for w in HG_WINDOWS for y in HG_WINDOW_YS):   # 横の長い穴（暗い板）
            r = (y1 - y0) / 2
            yc = (y0 + y1) / 2
            pts = [(zc + r * math.cos(math.radians(a)), yc + r * math.sin(math.radians(a)))
                   for zc, a0 in ((zb + r, 90), (za - r, 270)) for a in range(a0, a0 + 181, 30)]
            xa, xb = sorted((s * (HG_HALF - 0.1), s * (HG_HALF + 0.15)))
            out.append(extrude_x(pts, xa, xb, M.BORE))
    # 前の端（ガスブロックの覆い。図面の段）
    out.append(lathe(0, BORE_Y, [(z_front - 15.0, 19.0), (z_front - 12.0, 22.0), (z_front + 0.5, 22.0)], P.N_BIG,
                     M.STEEL_DARK))
    return out


# ---------------------------------------------------------------- 銃身
def barrel():
    """銃身（ハンドガードの中は見えない）と、図面の太さの分布の銃口側（ガスブロックの前・段・消炎器）。"""
    b = BORE_Y
    prof = sorted(O.MUZZLE_R)
    fh0 = -466.0                                               # 消炎器の根元（図面の太さが変わる所）
    pipe = [(z, r) for z, r in prof if z > fh0]
    fh = [(z, r) for z, r in prof if z <= fh0]
    pipe.insert(0, (fh[-1][0], pipe[0][1]))                    # 銃身の先を消炎器の根元まで延ばす（間の隙間を無くす）
    out = [lathe(0, b, [(-366.0, 9.5), (L.bolt_face_z, 9.5)], P.N_MID, M.STEEL)]
    out.append(lathe(0, b, pipe, P.N_MID, M.STEEL_DARK))
    out.append(lathe(0, b, [(fh[0][0], 4.0)] + fh + [(fh[-1][0], 4.0)], P.N_MID, M.STEEL_DARK, cap0=False, cap1=False))
    out.append(lathe(0, b, [(fh[0][0] - 0.2, 4.0), (fh[0][0] + 30.0, 4.0)], P.N_SMALL, M.BORE, cap0=False))
    for k in range(4):                                         # 消炎器の溝
        out += rotated([extrude_x([(fh[0][0] + 4.0, b + 9.0), (fh[0][0] + 26.0, b + 9.0), (fh[0][0] + 26.0, b + 12.6),
                                   (fh[0][0] + 4.0, b + 12.6)], -1.4, 1.4, M.BORE)], "z", 45.0 + 90.0 * k, (0.0, b, 0.0))
    return out


# ---------------------------------------------------------------- 照準器
def iron_sights():
    """HK の折りたたみ式の照門・照星を起こした状態（ボーン iron_sight。図面の側面形・正面図・後面図と作者提供の写真）。
    照門: 前後 36mm の箱形の台の上に、穴の板（守りの耳付き）を前後 12mm の塔で立てる。
    照星: 蝶番の台の上に、前後 14mm の左右の高い耳（U 字）と、間のポスト（誇張）。
    サイトのアタッチメントを付けたらコードがこのボーンを描かない（07-model-assets.md）。"""
    mat = M.STEEL_DARK
    sy, rt = SIGHT_Y, RAIL_TOP
    out = []
    # 照門
    out.append(extrude_x_beveled([(0.0, rt - 1.5), (36.0, rt - 1.5), (36.0, rt + 3.0), (33.0, rt + 13.0),
                                  (14.0, rt + 14.0), (2.0, rt + 8.0), (0.0, rt + 5.0)], -10.0, 10.0, 1.5, mat, steps=1))
    out += sights.aperture_plate(sy, REAR_SIGHT_Z - 3.0, REAR_SIGHT_Z + 3.0, REAR_HOLE, rt + 9.0, mat, ears=False)
    r_out = REAR_HOLE / 2 + max(3.0, REAR_HOLE / 2)
    out.append(extrude_x_beveled([(REAR_SIGHT_Z - 6.0, rt + 9.0), (REAR_SIGHT_Z + 6.0, rt + 9.0),
                                  (REAR_SIGHT_Z + 6.0, sy - r_out - 0.5), (REAR_SIGHT_Z - 6.0, sy - r_out - 0.5)],
                                 -r_out, r_out, 1.0, mat, steps=1))             # 塔（穴の板の下）
    # 左右の丸い頬（図面の側面で丸く見える回転ドラムの枠。間の穴の板から覗く）
    rc = r_out + 0.8
    disc = [(REAR_SIGHT_Z + rc * math.cos(math.radians(a)), sy + rc * math.sin(math.radians(a))) for a in range(0, 360, 30)]
    for s_ in (1, -1):
        xa, xb = sorted((s_ * (r_out - 0.5), s_ * (r_out + 2.5)))
        out.append(extrude_x_beveled(disc, xa, xb, 0.6, mat, steps=1))
    # 照星
    zc = FRONT_SIGHT_Z
    out.append(extrude_x_beveled([(-347.0, rt - 1.5), (-316.0, rt - 1.5), (-316.0, rt + 6.0), (-333.0, rt + 9.0),
                                  (-342.0, rt + 7.0), (-347.0, rt + 2.0)], -10.0, 10.0, 1.5, mat, steps=1))
    out.append(x_cyl(-336.0, rt + 4.5, 3.0, -10.6, 10.6, M.STEEL, n=8))         # 蝶番の軸
    gap = POST_W / 2 + 3.0
    top = sy - POST_W * 1.5
    out.append(extrude_x_beveled([(zc - 7.0, rt + 5.0), (zc + 7.0, rt + 5.0), (zc + 7.0, top), (zc - 7.0, top)],
                                 -gap - 3.0, gap + 3.0, 1.0, mat, steps=1))     # 塔
    for s_ in (1, -1):                                                          # 左右の耳（上の角を丸める）
        xa, xb = sorted((s_ * gap, s_ * (gap + 3.0)))
        out.append(extrude_x_beveled([(zc - 10.0, top - 1.0), (zc + 9.0, top - 1.0), (zc + 9.0, sy + 9.0),
                                      (zc + 3.0, sy + 13.0), (zc - 3.0, sy + 13.0), (zc - 6.0, sy + 9.0)],
                                     xa, xb, 0.6, mat, steps=1))                 # 前は斜めに下がる（図面）
    out.append(sights.post(POST_W, top - 1.0, sy, zc, mat))
    return out


# ---------------------------------------------------------------- 組み立て
def build():
    from core import Model
    l = L
    b = BORE_Y
    m = Model()
    parts: dict[str, list] = {}

    recolor = {M.RECEIVER: M.HK_RECEIVER, M.POLYMER: M.HK_POLY, M.STEEL_DARK: M.HK_STEEL}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        for c in items:                                       # AR-15 部品の灰色を HK の黒い仕上げに
            c.mat = recolor.get(c.mat, c.mat)
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "upper_receiver", P.upper_receiver(l))
    add("lower_receiver", "receiver", (0, b + l.lower_bottom, 0), "lower_receiver", lower())
    add("selector", "lower_receiver", (13.3, b + ar15_parts.SELECTOR_PIVOT[1], ar15_parts.SELECTOR_PIVOT[0]),
        "selector", P.selector(l))
    add("pistol_grip", "receiver", (0, 60.0, 50.0), "pistol_grip", pistol_grip())
    add("buffer_tube", "receiver", (0, TUBE_Y, l.lower_rear_z), "buffer_tube", buffer_tube())
    add("mag_release", "lower_receiver", (-HALF_LOWER, MAG_CATCH[1], MAG_CATCH[0]), "mag_release", mag_release())
    add("stock", "root", (0, b, _zr(O.STOCK)[0]), "stock", stock())

    add("rail_top", "root", (0, RAIL_TOP, RAIL_REAR_Z), "rail", P.rail(l, z_rear=RAIL_REAR_Z))
    add("handguard", "root", (0, b, HG_Z[0]), "handguard", handguard())
    add("rail_bottom", "root", (0, HG_BOTTOM - 9.0, HG_Z[0] - 10.0), None, [])
    add("rail_side", "root", (HG_HALF + 9.0, SIDE_RAIL_Y, HG_Z[0] - 10.0), None, [])
    add("iron_sight", "root", (0, RAIL_TOP, REAR_SIGHT_Z), "iron_sight", iron_sights())

    add("barrel", "root", (0, b, l.bolt_face_z), "barrel", barrel())
    add("chamber", "barrel", (0, b, l.bolt_face_z), "barrel_extension", P.barrel_extension(l))
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])

    add("bolt", "root", (0, b, l.bolt_face_z + 37), "bolt_carrier", P.bolt_carrier(l))
    add("charging_handle", "root", (0, b + 18, l.upper_rear_z), "charging_handle", P.charging_handle(l))
    add("port_cover", "receiver", (-14.6, b + ar15_parts.PORT_Y[0] - 1, l.bolt_face_z + sum(ar15_parts.PORT_Z) / 2),
        "port_cover", P.port_cover(l))
    add("trigger", "root", (0, b + l.lower_bottom, -2), "trigger", P.trigger(l))

    mz = l.mag_center_z
    add("magazin", "root", (0, b - 95, mz), "magazine_stanag", P.magazine_stanag(l))
    ry = b - l.mag_top_below_bore - 5
    add("mag_ammo", "magazin", (0, ry, mz + 2), None, P.magazine_rounds(l))

    tip = l.bolt_face_z - 57.4
    case, bullet = P.cartridge_556(z_tip=tip, y=b)
    add("ammo", "root", (0, b, tip + 35), None, case)
    add("bullet", "ammo", (0, b, tip + 6), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(O.GRIP["outer"]).centroid
    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K, rear_sight_z=REAR_SIGHT_Z * K,
                 grip_center=(0, c.y * K, c.x * K), support_z=-250.0 * K)
    return m, parts
