"""
FN Five-seveN MK2（黒）のパーツと組み立て（単位 mm、メッシュ版）。拳銃なので一人称の構えは glock に合わせる（rig.add_pistol_locators）。

側面形は作者提供の三面図（右側面・左側面・前・後ろ）から mm 目盛りを重ねて読み取った（写真のトレースではなく、点を手で拾った）。
縮尺は全長 208mm（図面で 0.981px/mm）。照準半径（照門〜照星 178〜183mm）と前後の図の幅（スライド 29mm・グリップ 31mm・
操作レバー込み 36mm＝公表の幅）で確かめた。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝排莢口の側）、Y=0 弾倉の底、Z=0 トリガー、銃口 -Z。

図面に無い所（推定）: 排莢口の大きさ（スライド前側の段の直後から、弾の長さ 40.5mm が抜ける長さ）、弾倉の中の形と弾の並び、
照準器の切り欠きと照星の幅（他の銃と同じく見やすさのために誇張。sights.py）。
"""
import math

from shapely.geometry import Point, Polygon, box as sbox
from shapely.geometry.polygon import orient

import ar15_parts
import materials as M
import sights
from core import extrude_x, extrude_x_beveled, extrude_x_rounded, inflate_x, lathe
from m249 import x_cyl
from mp5 import extrude_z
from rig import PISTOL_IRON_BEHIND, add_pistol_locators

K = 1.0 / ar15_parts.MM_PER_PX
POLY = M.FN_POLY
SLIDE_MAT = M.FN_SLIDE
STEEL = M.FN_STEEL

BORE_Y = 128.0           # 銃身の軸（前の図の銃口の中心）
MUZZLE_Z = -111.0
BREECH_Z = -12.0         # 薬室の後端（排莢口の後ろの端）

# スライド（前の図: 幅 29mm、上の角が丸い。前側は一段細い）
SLIDE_Z = (-112.0, 94.0)
SLIDE_Y = (118.0, 137.5)
HALF_SLIDE = 14.5
HALF_SLIDE_FRONT = 13.2
SLIDE_STEP_Z = -50.0     # 前側の細い所の後ろの端（図面の段）
SLIDE_TOP_R = 4.0
PORT_Z = (-50.0, -14.0)  # 右側面の排莢口（段の直後から。推定）
PORT_Y = 123.5           # 排莢口の下の縁
PORT_X = -2.0            # 排莢口の上面側の縁（ここより右が開く）
SERR_Z = (40.0, 84.0)    # 後ろの滑り止めの溝（図面）
SERR_Y = (120.0, 133.5)
SERR_DEPTH = 0.7
SERR_LEAN = 15.0         # 溝の傾き（上が前。図面）

# 照準器（図面: 照門の刃 Z 76〜81.5・上端 144.5、照星 Z -104 前後）。切り欠き・照星の幅は ADS の目からの見え方で誇張
SIGHT_Y = 144.5
REAR_SIGHT_Z = 79.0
FRONT_SIGHT_Z = -103.0
_EYE = PISTOL_IRON_BEHIND
NOTCH_W = sights.NOTCH_ANGLE * (_EYE - REAR_SIGHT_Z)
POST_W = sights.POST_ANGLE * (_EYE - FRONT_SIGHT_Z)
NOTCH_DEPTH = 4.0

# フレーム・グリップ（前後の図: フレーム 30mm・グリップ 31mm）
HALF_FRAME = 15.2
HALF_GRIP = 15.0         # フレームより 0.2 細く（重なる所で面がちらつかないように）
GRIP_R = 5.0             # グリップの前後の角の丸み
HALF_GUARD = 5.0
GRIP_RAKE = 0.226        # グリップの傾き（Y 1mm あたり Z。約 13°、滑り止めの縁の線から）

# 側面形（Z, Y）。図面から読み取った点
FRAME = [(-111.5, 118.0), (93.5, 118.0), (93.5, 102.0), (92.0, 98.5), (89.0, 96.0), (85.0, 93.6), (80.0, 91.6),
         (76.0, 90.2), (21.0, 95.5), (-30.0, 95.5), (-38.0, 98.0), (-42.0, 101.0), (-97.5, 101.0), (-111.5, 108.0)]
GRIP = [(18.0, 106.0), (18.0, 95.0), (18.5, 82.0), (20.0, 74.0), (23.0, 67.5), (26.6, 61.0), (38.0, 11.4), (39.0, 9.5),
        (92.8, 9.5), (92.3, 15.0), (80.6, 61.4), (74.0, 70.1), (72.6, 78.9), (73.5, 85.0), (75.5, 89.5), (78.0, 92.0),
        (80.0, 106.0)]
GUARD = [(-38.0, 99.0), (-38.0, 75.0), (-36.0, 70.0), (-31.5, 67.5), (26.0, 67.5), (26.0, 99.0)]
GUARD_HOLE = [(-31.5, 95.5), (-31.5, 76.0), (-29.5, 72.5), (-26.0, 71.3), (15.0, 71.3), (17.3, 73.5), (18.0, 78.0),
              (18.0, 95.5)]
# 滑り止めの面（左右の側面。前と後ろの 2 枚。間は FN のロゴのある滑らかな帯）
STIPPLE_FRONT = [(31.5, 59.0), (50.5, 59.0), (59.0, 14.0), (42.5, 14.0)]
STIPPLE_REAR = [(71.5, 59.0), (76.5, 59.0), (87.5, 14.0), (80.0, 14.0)]
RAIL_Z = (-97.0, -43.0)  # 下面のレール（ダストカバーの下）
RAIL_LUGS = [(-95.0, -90.0), (-85.0, -80.0), (-75.0, -70.0), (-65.0, -60.0), (-55.0, -50.0)]
PINS = [(69.6, 110.0), (90.0, 110.0), (8.5, 100.0), (-34.7, 102.5)]

# 弾倉（5.7×28mm の複列 20 発。グリップの傾きに沿って入る）
MAG_FRONT_AT_61 = 29.1   # Y 61 での前の面の Z
MAG_DEPTH = 47.5
MAG_TOP = 106.0
HALF_MAG = 8.5
BASE_PLATE = [(36.5, 1.5), (38.0, 0.0), (93.0, 0.0), (94.8, 2.0), (94.3, 9.6), (39.0, 9.6), (36.5, 5.0)]
HALF_BASE = 11.5


def _mag_z(y):
    """弾倉の前の面の Z（高さ y）。"""
    return MAG_FRONT_AT_61 + (61.0 - y) * GRIP_RAKE


def _rounded_section(half, y0, y1, r_top, r_bot=1.0):
    """スライドの断面（X, Y）: 上の角を r_top、下の角を r_bot で丸めた長方形。"""
    g = sbox(-half + r_top, y0, half - r_top, y1 - r_top).buffer(r_top, quad_segs=3)
    g = g.union(sbox(-half, y0 + r_bot, half, y1 - r_top))
    g = g.union(sbox(-half + r_bot, y0, half - r_bot, y0 + r_bot + 0.01))
    return g.intersection(sbox(-half, y0, half, y1))


def _ext_z(g, z0, z1, mat):
    """shapely の断面（穴なし）を Z 方向に押し出す。"""
    if g.geom_type != "Polygon":
        return [p for q in g.geoms for p in _ext_z(q, z0, z1, mat)]
    return [extrude_z(list(orient(g.simplify(0.02), 1.0).exterior.coords)[:-1], z0, z1, mat)]


# ---------------------------------------------------------------- スライド（ボーン bolt）
def slide():
    out = []
    y0, y1 = SLIDE_Y
    # 前側（細い）: 銃身の通る穴を左右の半分の切り欠きで開ける（断面に穴は作れないので X=0 で 2 つに分ける）
    front = _rounded_section(HALF_SLIDE_FRONT, y0, y1, SLIDE_TOP_R).difference(Point(0, BORE_Y).buffer(6.2, quad_segs=4))
    for s_ in (1, -1):
        half = front.intersection(sbox(0, 0, s_ * 30, 200) if s_ > 0 else sbox(-30, 0, 0, 200))
        out += _ext_z(half, SLIDE_Z[0], SLIDE_STEP_Z, SLIDE_MAT)
    full = _rounded_section(HALF_SLIDE, y0, y1, SLIDE_TOP_R)
    # 排莢口: 右側面の上半分と、上面の右側を開ける（奥に銃身の薬室の覆いが見える）
    out += _ext_z(full.intersection(sbox(PORT_X, 0, 30, 200)), PORT_Z[0], PORT_Z[1], SLIDE_MAT)
    out += _ext_z(full.intersection(sbox(-30, 0, PORT_X, PORT_Y)), PORT_Z[0], PORT_Z[1], SLIDE_MAT)
    out += _ext_z(full, PORT_Z[1], SERR_Z[0], SLIDE_MAT)
    # 後ろの滑り止め: 左右の側面を浅く削り、斜めの山を並べる
    s0, s1 = SERR_Y
    recessed = full.difference(sbox(HALF_SLIDE - SERR_DEPTH, s0, 30, s1)).difference(sbox(-30, s0, -HALF_SLIDE + SERR_DEPTH, s1))
    out += _ext_z(recessed, SERR_Z[0], SERR_Z[1], SLIDE_MAT)
    lean = (s1 - s0) * math.tan(math.radians(SERR_LEAN))
    for i in range(12):
        zc = SERR_Z[0] + 4.5 + i * 3.4
        prof = [(zc - 0.8 + lean / 2, s0), (zc + 0.8 + lean / 2, s0), (zc + 0.8 - lean / 2, s1), (zc - 0.8 - lean / 2, s1)]
        if prof[2][0] < SERR_Z[0] + 1.0 or prof[1][0] > SERR_Z[1] - 1.0:
            continue
        for s_ in (1, -1):
            xa, xb = sorted((s_ * (HALF_SLIDE - SERR_DEPTH - 0.1), s_ * HALF_SLIDE))
            out.append(extrude_x(prof, xa, xb, SLIDE_MAT))
    out += _ext_z(full, SERR_Z[1], SLIDE_Z[1] - 3.0, SLIDE_MAT)
    # 後ろの端の上の角の面取り（図面）
    out += _ext_z(_rounded_section(HALF_SLIDE - 0.5, y0, y1 - 3.5, SLIDE_TOP_R), SLIDE_Z[1] - 3.0, SLIDE_Z[1], SLIDE_MAT)
    return out


def sights_parts():
    """照門（台・切り欠きのある刃）と照星（スライドの一部。スライドと一緒に動く）。"""
    y1 = SLIDE_Y[1]
    out = [extrude_x_beveled([(54.0, y1 - 0.5), (81.5, y1 - 0.5), (81.5, y1 + 3.5), (57.0, y1 + 3.5)], -8.0, 8.0, 1.0,
                             STEEL, steps=1)]
    blade = sbox(-11.0, y1 - 0.5, 11.0, SIGHT_Y).difference(sbox(-NOTCH_W / 2, SIGHT_Y - NOTCH_DEPTH, NOTCH_W / 2, SIGHT_Y + 1))
    out += sights.plate_z(blade, REAR_SIGHT_Z - 2.5, REAR_SIGHT_Z + 2.5, STEEL)
    zc = FRONT_SIGHT_Z
    out.append(extrude_x_beveled([(zc - 5.0, y1 - 0.5), (zc + 5.0, y1 - 0.5), (zc + 5.0, y1 + 2.0), (zc - 5.0, y1 + 2.0)],
                                 -3.5, 3.5, 0.8, STEEL, steps=1))
    out.append(extrude_x([(zc - 3.5, y1 + 1.5), (zc + 3.0, y1 + 1.5), (zc + 1.5, SIGHT_Y), (zc - 1.5, SIGHT_Y)],
                         -POST_W / 2, POST_W / 2, STEEL))
    return out


# ---------------------------------------------------------------- フレーム（ボーン receiver）
def frame():
    out = [extrude_x_beveled(FRAME, -HALF_FRAME, HALF_FRAME, 1.8, POLY, steps=2)]
    out.append(inflate_x(GRIP, HALF_GRIP, POLY, steps=4, radius_fn=lambda nz, ny: GRIP_R))
    out.append(extrude_x_rounded(GUARD, [GUARD_HOLE], lambda z, y: HALF_GUARD, 1.5, POLY, steps=2))
    for poly in (STIPPLE_FRONT, STIPPLE_REAR):
        for s_ in (1, -1):
            xa, xb = sorted((s_ * (HALF_GRIP - 0.4), s_ * (HALF_GRIP + 0.35)))
            out.append(extrude_x_beveled(poly, xa, xb, 0.3, M.FN_STIPPLE, steps=1))
    # 下面のレール（ダストカバーの下。横溝の山）
    out.append(extrude_x([(RAIL_Z[0], 99.0), (RAIL_Z[1], 99.0), (RAIL_Z[1], 101.5), (RAIL_Z[0], 101.5)], -10.5, 10.5, POLY))
    for z0, z1 in RAIL_LUGS:
        out.append(extrude_x_beveled([(z0, 97.0), (z1, 97.0), (z1, 99.5), (z0, 99.5)], -10.5, 10.5, 0.5, POLY, steps=1))
    # 左右のピン・分解レバー（左）
    for z, y in PINS:
        for s_ in (1, -1):
            xa, xb = sorted((s_ * (HALF_FRAME - 0.5), s_ * (HALF_FRAME + 0.4)))
            out.append(x_cyl(z, y, 1.8, xa, xb, STEEL, n=8))
    out.append(extrude_x_beveled([(-43.0, 106.0), (-37.0, 106.0), (-37.0, 116.5), (-43.0, 116.5)],
                                 HALF_FRAME - 0.5, HALF_FRAME + 1.0, 0.4, POLY, steps=1))
    return out


def safety():
    """手動の安全装置（左右。トリガーの上のレバー。軸は Z 0。ボーンは M24 の安全装置と同じ selector）。"""
    out = []
    prof = [(-10.5, 105.0), (2.5, 105.0), (2.5, 110.0), (-8.0, 110.5), (-10.5, 108.5)]
    for s_ in (1, -1):
        xa, xb = sorted((s_ * (HALF_FRAME - 0.5), s_ * (HALF_FRAME + 1.6)))
        out.append(extrude_x_beveled(prof, xa, xb, 0.5, POLY, steps=1))
    return out


def slide_stop():
    """スライドストップ（左のみ）。"""
    prof = [(31.0, 102.0), (44.0, 102.0), (44.0, 109.5), (41.0, 112.5), (31.0, 112.5)]
    return [extrude_x_beveled(prof, HALF_FRAME - 0.5, HALF_FRAME + 1.5, 0.5, POLY, steps=1)]


def mag_release():
    """弾倉の留め金のボタン（左右に出る。トリガーガードの後ろの付け根）。"""
    prof = [(21.5, 67.0), (32.5, 67.0), (33.0, 70.5), (32.0, 74.5), (22.0, 74.5), (21.0, 71.0)]
    return [extrude_x_beveled(prof, -HALF_GRIP - 1.2, HALF_GRIP + 1.2, 1.0, POLY, steps=1)]


def trigger():
    prof = [(4.0, 96.0), (-0.5, 96.0), (-2.5, 89.0), (-4.5, 81.0), (-6.5, 74.0), (-5.0, 71.8), (-3.5, 73.0), (-1.0, 80.0),
            (1.5, 87.0), (3.5, 92.0)]
    return [extrude_x_beveled(prof, -3.5, 3.5, 1.0, POLY, steps=1)]


# ---------------------------------------------------------------- 銃身（ボーン barrel・chamber）
def barrel():
    out = [lathe(0, BORE_Y, [(MUZZLE_Z, 5.6), (-48.0, 5.6)], 12, STEEL)]
    out.append(lathe(0, BORE_Y, [(MUZZLE_Z - 0.05, 2.9), (MUZZLE_Z + 10.0, 2.9)], 8, M.BORE, cap1=False))
    return out


def chamber():
    """薬室の覆い（排莢口から見える四角い塊）。"""
    return [extrude_x_beveled([(PORT_Z[0] + 2.0, 121.0), (BREECH_Z, 121.0), (BREECH_Z, 136.8), (PORT_Z[0] + 2.0, 136.8)],
                              -11.0, 11.0, 1.0, STEEL, steps=1)]


# ---------------------------------------------------------------- 弾倉・弾（ボーン magazin・mag_ammo・ammo・bullet）
def cartridge_57(x, y, z_tip):
    """5.7×28mm 実包（回転体）: 全長 40.5mm、薬莢 28.9mm（ボトルネック）。"""
    b = z_tip + 40.5
    case = [(b, 3.9), (b - 1.2, 3.9), (b - 1.4, 3.3), (b - 2.0, 3.3), (b - 2.3, 3.95), (b - 22.0, 3.85),
            (b - 24.5, 3.15), (b - 28.9, 3.15)]
    bullet = [(b - 28.9, 2.85), (b - 31.5, 2.8), (b - 36.0, 2.0), (b - 39.5, 0.8), (z_tip, 0.3)]
    return [lathe(x, y, case, 8, M.BRASS, cap0=True, cap1=False), lathe(x, y, bullet, 8, M.COPPER, cap0=False, cap1=True)]


def magazine():
    zf0, zf1 = _mag_z(9.0), _mag_z(MAG_TOP)
    body = [(zf0, 9.0), (zf0 + MAG_DEPTH, 9.0), (zf1 + MAG_DEPTH, MAG_TOP), (zf1, MAG_TOP)]
    return [extrude_x_beveled(body, -HALF_MAG, HALF_MAG, 1.0, POLY, steps=1),
            extrude_x_beveled(BASE_PLATE, -HALF_BASE, HALF_BASE, 2.0, POLY, steps=2)]


def mag_rounds():
    """弾倉の上の 2 発（互い違い。弾倉を抜いたときに見える）。"""
    out = []
    for i, (x, y) in enumerate(((2.0, MAG_TOP - 3.0), (-2.0, MAG_TOP - 9.5))):
        out += cartridge_57(x, y, _mag_z(y) + 1.5)
    return out


# ---------------------------------------------------------------- 組み立て
def build():
    from core import Model
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    b = BORE_Y
    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, 110.0, 0), "frame", frame())
    add("selector", "receiver", (0, 107.5, 0.0), "safety", safety())
    add("slide_stop", "receiver", (HALF_FRAME, 107.0, 40.0), "slide_stop", slide_stop())
    add("mag_release", "receiver", (0, 71.0, 27.0), "mag_release", mag_release())
    add("trigger", "root", (0, 96.0, 1.5), "trigger", trigger())
    add("bolt", "root", (0, b, SLIDE_Z[1]), "slide", slide() + sights_parts())
    add("barrel", "root", (0, b, BREECH_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BREECH_Z), "chamber", chamber())
    add("magazin", "root", (0, 50.0, 62.0), "magazine", magazine())
    add("mag_ammo", "magazin", (0, MAG_TOP - 6.0, 40.0), None, mag_rounds())
    tip = BREECH_Z - 40.5
    case, bullet = cartridge_57(0, b, tip)
    add("ammo", "root", (0, b, tip + 26.0), None, [case])
    add("bullet", "ammo", (0, b, tip + 6.0), None, [bullet])
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])
    add("rail_bottom", "root", (0, 97.0, RAIL_Z[1]), None, [])
    c = Polygon(GRIP).centroid
    add_pistol_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K, bore_y=b * K,
                        grip_center=(0, c.y * K, c.x * K))
    return m, parts
