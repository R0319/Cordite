"""
AK-47（Type 3・木製の固定ストック）のパーツと組み立て（単位 mm、メッシュ版）。

側面形はすべて作者提供の図面（線画）からトレースした輪郭（ak47_outline.py ← trace_ak47.py）を使う。
縮尺は全長 880mm（Type 3 の公表値）で合わせた。左右の幅は同じ図面の上面図から測った値（下の HALF_*）。
座標は M4A1 と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝セレクター・コッキングハンドルの側）、
Y=0 グリップ底面、Z=0 トリガー、銃口 -Z。

2 つのモデルを同じ部品から出す:
  ak_47      … 図面どおりの木製の上下ハンドガード・グリップ・ストック
  ak_47_rail … 下ハンドガードをアルミの四面レール、上ハンドガードとダストカバーを上面レール付きに替えたもの
               （外形は木製と同じ輪郭。レール寸法はプロジェクト規約）
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import ak47_outline as O
from core import MeshPart, Model, box, extrude_x, extrude_x_beveled, inflate_x, lathe
from m249 import outline_parts, x_cyl
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
SLOT_MM = ar15_parts.SLOT_MM
RAIL_W = ar15_parts.RAIL_W_MM
STEEL_BLACK = M.STEEL_DARK
WOOD = M.WOOD

BORE_Y = 133.0          # 銃身の軸（図面の銃身の上下の中点）
SIGHT_Y = 176.0         # 照準線（照星のフードの中のポストの先端）
MUZZLE_Z = -572.0       # 銃口（床尾 +308 から全長 880）
REAR_SIGHT_Z = -132.0   # 照門（照尺の後端の切り欠き）
FRONT_SIGHT_Z = -482.0  # 照星
CHAMBER_Z = -150.0      # 銃身の後端（受け部の前端）

# 左右の半幅（作者提供の図面の上面図から。上面図の全長 880mm で縮尺を合わせ、各位置の幅を測った）
HALF_RECEIVER = 19.0    # 受け部 約 40mm
HALF_COVER = 18.0       # ダストカバー（受け部の外側に被さる）
HALF_TRUNNION = 18.0
HALF_STOCK = 15.0       # ストックは付け根 30mm → 床尾 37mm（width_fn で広げる）
HALF_GRIP = 13.0
HALF_MAG = 13.0
HALF_LOWER_HG = 16.0    # 下ハンドガード 約 46mm（width_fn で 1.45 倍）
HALF_UPPER_HG = 13.0    # 上ハンドガード 約 32mm（width_fn で 1.2 倍）
HALF_GAS = 11.0         # ガスチューブ・ガスブロック 約 22mm


def _zr(o):
    zs = [p[0] for p in o["outer"]]
    return min(zs), max(zs)


def _yr(o):
    ys = [p[1] for p in o["outer"]]
    return min(ys), max(ys)


# ---------------------------------------------------------------- 受け部
def receiver():
    h = HALF_RECEIVER
    out = outline_parts(O.RECEIVER, -h, h, M.RECEIVER, bevel=1.5)
    # Type 3 の軽量化の削り込み（弾倉口の上。図面の角の丸い長方形）: 両側面
    for s in (1, -1):
        x0, x1 = sorted((s * (h - 0.6), s * (h + 0.2)))
        out.append(extrude_x([(-102.0, 114.0), (-72.0, 114.0), (-70.0, 119.0), (-72.0, 124.0), (-102.0, 124.0),
                              (-104.0, 119.0)], x0, x1, M.STEEL_DARK))
    # ピン・リベット（図面の丸）
    for z, y, r in ((-110.0, 120.0, 3.0), (45.0, 124.0, 3.5), (70.0, 135.0, 2.5), (-30.0, 118.0, 2.5),
                    (-50.0, 116.0, 2.5)):
        for s in (1, -1):
            x0, x1 = sorted((s * (h - 0.3), s * (h + 0.9)))
            out.append(x_cyl(z, y, r, x0, x1, STEEL_BLACK, n=10))
    # セレクターレバー（右側面）: 後ろの丸い軸から前へ長く伸びる板（図面: 軸 Z≈+30・Y≈126、先端 Z≈-45・Y≈138）
    out.append(x_cyl(30.0, 126.0, 8.0, -h - 2.0, -h, STEEL_BLACK, n=14))
    out.append(extrude_x([(30.0, 120.0), (30.0, 132.0), (-45.0, 141.0), (-48.0, 137.0)], -h - 2.0, -h - 0.5, STEEL_BLACK))
    return out


def dust_cover(rail=False):
    """ダストカバー（板金の蓋）。図面の側面形を押し出し、上の角を大きく丸める。rail=True で上面にレール。"""
    o = O.DUST_COVER
    out = [extrude_x_beveled(o["outer"], -HALF_COVER, HALF_COVER, 7.0, M.RECEIVER, steps=3)]
    z0, z1 = _zr(o)
    yt = _yr(o)[1]
    if rail:
        slots = 16
        r1 = z1 - 20
        r0 = r1 - slots * SLOT_MM
        out += [box(-8, yt - 1, r0, 8, yt + 3, r1, M.RAIL), box(-RAIL_W / 2, yt + 3, r0, RAIL_W / 2, yt + 8, r1, M.RAIL)]
    return out


def front_trunnion():
    return outline_parts(O.FRONT_TRUNNION, -HALF_TRUNNION, HALF_TRUNNION, STEEL_BLACK, bevel=2.0)


def rear_sight():
    """照門ブロック＋照尺（図面の側面形。照尺は前の軸から後ろへ伸び、後端に V 字の照門）。"""
    out = outline_parts(O.REAR_SIGHT, -10.0, 10.0, STEEL_BLACK, bevel=1.0)
    out.append(box(-1.5, SIGHT_Y + 0.5, REAR_SIGHT_Z - 2.5, 1.5, SIGHT_Y + 8.0, REAR_SIGHT_Z + 2.5, M.BORE))   # V 字の切り欠き
    return out


def trigger_guard():
    return outline_parts(O.TRIGGER_GUARD, -5.0, 5.0, STEEL_BLACK)


def trigger():
    """トリガー（図面: ガードの中で後ろ下へ曲がる板）。"""
    return [extrude_x([(4.0, 100.0), (-4.0, 100.0), (-3.0, 88.0), (2.0, 80.0), (8.0, 77.0), (6.0, 82.0), (2.0, 90.0)],
                      -3.0, 3.0, STEEL_BLACK)]


def pistol_grip():
    def radius(nz, ny):
        return 5.0 if ny < -0.7 else HALF_GRIP
    return [inflate_x(O.GRIP["outer"], HALF_GRIP, WOOD, steps=4, radius_fn=radius)]


def stock():
    z0, z1 = _zr(O.STOCK)

    def width(z, y, f):
        return 1.0 + 0.23 * (z - z0) / (z1 - z0)        # 付け根 30mm → 床尾 37mm

    def radius(nz, ny):
        return 9.0
    out = [inflate_x(O.STOCK["outer"], HALF_STOCK, WOOD, steps=4, width_fn=width, radius_fn=radius)]
    # 鋼の床尾板（図面: 床尾の縦の帯）
    y0, y1 = _yr(O.STOCK)
    out.append(extrude_x_beveled([(z1 - 6, y0 + 2), (z1 + 1, y0 + 2), (z1 + 1, y1 - 2), (z1 - 6, y1 - 2)],
                                 -HALF_STOCK * 1.23 - 0.5, HALF_STOCK * 1.23 + 0.5, 1.0, STEEL_BLACK, steps=1))
    return out


# ---------------------------------------------------------------- 銃身まわり
def barrel():
    br = sorted(O.BARREL_R)
    r_mid = sorted(r for _, r in br)[len(br) // 2]
    pts = [(MUZZLE_Z, 3.81), (MUZZLE_Z, 7.5), (-512.0, 7.5), (-512.0, r_mid - 1.0), (CHAMBER_Z, r_mid - 1.0)]
    return [lathe(0, BORE_Y, pts, ar15_mesh.N_MID, M.STEEL, cap0=False),
            lathe(0, BORE_Y, [(MUZZLE_Z, 3.81), (MUZZLE_Z + 25, 3.81)], ar15_mesh.N_SMALL, M.BORE, cap0=False)]


def muzzle():
    """銃口側（照星の台の前〜銃口ナット）: 図面の太さの分布の回転体。"""
    prof = sorted(O.MUZZLE_R)
    prof = [(z, min(r, 11.0)) for z, r in prof]
    return [lathe(0, BORE_Y, [(prof[0][0], 3.81)] + prof + [(prof[-1][0], 3.81)], ar15_mesh.N_MID, STEEL_BLACK,
                  cap0=False, cap1=False)]


def gas():
    """ガスチューブ〜ガスブロック（図面の側面形。断面は丸める）と、ガスブロックの下の突起。"""
    return [extrude_x_beveled(O.GAS["outer"], -HALF_GAS, HALF_GAS, 9.0, STEEL_BLACK, steps=3),
            *outline_parts(O.GAS_LUG, -7.0, 7.0, STEEL_BLACK, bevel=2.0)]


def cleaning_rod():
    return [lathe(0, 121.5, [(-505.0, 2.2), (-320.0, 2.2)], 6, M.STEEL)]


def front_sight():
    return [*outline_parts(O.FRONT_SIGHT, -6.0, 6.0, STEEL_BLACK, bevel=1.0),
            *outline_parts(O.FRONT_SIGHT_BASE, -11.0, 11.0, STEEL_BLACK, bevel=3.0)]


# ---------------------------------------------------------------- ハンドガード
def lower_handguard_wood():
    def width(z, y, f):
        return 1.45

    def radius(nz, ny):
        return 12.0 if ny < -0.5 else 3.0
    return [inflate_x(O.LOWER_HANDGUARD["outer"], HALF_LOWER_HG, WOOD, steps=4, width_fn=width, radius_fn=radius)]


def upper_handguard_wood():
    def width(z, y, f):
        return 1.2
    return [inflate_x(O.UPPER_HANDGUARD["outer"], HALF_UPPER_HG, WOOD, steps=4, width_fn=width)]


def lower_handguard_rail():
    """四面レールの下ハンドガード（アルミ）。外形は木製と同じ輪郭、下面と左右にレール、側面に放熱穴。"""
    o = O.LOWER_HANDGUARD
    z0, z1 = _zr(o)
    y0, y1 = _yr(o)
    hw = HALF_LOWER_HG * 1.3
    out = [extrude_x_beveled(o["outer"], -hw, hw, 2.0, M.RECEIVER, steps=1)]
    slots = int((z1 - z0 - 14) // SLOT_MM)
    r1 = (z0 + z1) / 2 + slots * SLOT_MM / 2
    r0 = r1 - slots * SLOT_MM
    out += [box(-8, y0 - 2, r0, 8, y0, r1, M.RAIL_DOWN), box(-RAIL_W / 2, y0 - 6, r0, RAIL_W / 2, y0 - 2, r1, M.RAIL_DOWN)]
    yc = (y0 + y1) / 2 - 3
    for s in (1, -1):
        xa, xb = sorted((s * hw, s * (hw + 2)))
        out.append(box(xa, yc - 8, r0, xb, yc + 8, r1, M.RAIL_SIDE))
        xa, xb = sorted((s * (hw + 2), s * (hw + 6)))
        out.append(box(xa, yc - RAIL_W / 2, r0, xb, yc + RAIL_W / 2, r1, M.RAIL_SIDE))
        for k in range(5):
            z = r0 + (r1 - r0) * (k + 0.5) / 5
            xa, xb = sorted((s * (hw - 0.3), s * (hw + 0.3)))
            out.append(x_cyl(z, y1 - 7, 3.0, xa, xb, M.BORE, n=10))
    return out, (r0, r1), y0 - 6, hw + 6, yc


def upper_handguard_rail():
    o = O.UPPER_HANDGUARD
    z0, z1 = _zr(o)
    yt = _yr(o)[1]
    out = [extrude_x_beveled(o["outer"], -HALF_UPPER_HG * 1.2, HALF_UPPER_HG * 1.2, 4.0, M.RECEIVER, steps=2)]
    slots = int((z1 - z0 - 12) // SLOT_MM)
    r1 = (z0 + z1) / 2 + slots * SLOT_MM / 2
    r0 = r1 - slots * SLOT_MM
    out += [box(-8, yt - 1, r0, 8, yt + 3, r1, M.RAIL), box(-RAIL_W / 2, yt + 3, r0, RAIL_W / 2, yt + 8, r1, M.RAIL)]
    return out


# ---------------------------------------------------------------- 機関部の可動部
def bolt_carrier():
    return [box(-12, BORE_Y - 4, -120, 12, BORE_Y + 14, -40, M.STEEL)]


def charging_handle():
    """コッキングハンドル（右側面。図面: Z≈-53〜-67・Y≈137〜147 の丸いつまみ）。"""
    h = HALF_RECEIVER
    return [box(-h - 8, 139.0, -66.0, -h + 1, 145.0, -54.0, STEEL_BLACK),
            x_cyl(-60.0, 142.0, 6.0, -h - 16, -h - 7, STEEL_BLACK, n=12)]


# ---------------------------------------------------------------- 弾倉
def magazine_ak():
    """AK 30 発弾倉（鋼）: 図面の側面形（強く前へ反ったバナナ形）を押し出す。図面の縦のビードを 2 本足す。"""
    out = [extrude_x_beveled(O.MAGAZINE["outer"], -HALF_MAG, HALF_MAG, 1.5, M.MAG_AK, steps=1)]
    return out


def cartridge_762(z_tip, y):
    """7.62×39mm 実包（回転体）: 全長 56mm、薬莢 38.7mm、テーパーの強い胴。"""
    b = z_tip + 56.0
    case = [(b, 5.6), (b - 1.5, 5.6), (b - 1.8, 4.9), (b - 3.0, 4.9), (b - 3.4, 5.55), (b - 30.5, 5.2),
            (b - 33.5, 4.4), (b - 38.7, 4.3)]
    bullet = [(b - 38.7, 3.9), (b - 44.0, 3.85), (b - 50.0, 2.9), (b - 54.5, 1.2), (z_tip, 0.4)]
    return ([lathe(0, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(0, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


# ---------------------------------------------------------------- 組み立て
def build(variant="wood"):
    rail = variant == "rail"
    b = BORE_Y
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "receiver", receiver() + front_trunnion() + dust_cover(rail=rail))
    add("lower_receiver", "receiver", (0, 100.0, 0), "trigger_guard", trigger_guard())
    add("pistol_grip", "receiver", (0, 100.0, 40.0), "pistol_grip", pistol_grip())
    add("trigger", "root", (0, 100.0, 0), "trigger", trigger())
    add("stock", "root", (0, b, 80.0), "stock", stock())

    add("barrel", "root", (0, b, CHAMBER_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, CHAMBER_Z), None, [])
    add("rear_sight", "barrel", (0, b, -150.0), "rear_sight", rear_sight())
    add("gas_block", "barrel", (0, b, -400.0), "gas", gas() + cleaning_rod())
    add("front_sight_base", "barrel", (0, b, -480.0), "front_sight", front_sight())
    add("front_sight_post", "front_sight_base", (0, SIGHT_Y, FRONT_SIGHT_Z), None, [])
    add("muzzle", "root", (0, b, MUZZLE_Z), "muzzle", muzzle())

    if rail:
        lower, (r0, r1), y_bottom, x_side, yc = lower_handguard_rail()
        add("handguard", "root", (0, b, -208.0), "handguard_rail", lower + upper_handguard_rail())
        add("rail_top", "root", (0, _yr(O.DUST_COVER)[1] + 8, _zr(O.DUST_COVER)[1] - 20), None, [])
        add("rail_bottom", "root", (0, y_bottom, r1), None, [])
        add("rail_side", "root", (x_side, yc, r1), None, [])
    else:
        add("handguard", "root", (0, b, -208.0), "handguard_wood", lower_handguard_wood() + upper_handguard_wood())
        add("rail_top", "root", (0, _yr(O.DUST_COVER)[1], 60.0), None, [])
        add("rail_bottom", "root", (0, _yr(O.LOWER_HANDGUARD)[0], -208.0), None, [])
        add("rail_side", "root", (HALF_RECEIVER, b, -208.0), None, [])

    add("bolt", "root", (0, b, -80.0), "bolt_carrier", bolt_carrier())
    add("charging_handle", "bolt", (-HALF_RECEIVER, 142.0, -60.0), "charging_handle", charging_handle())

    add("magazin", "root", (0, 100.0, -90.0), "magazine_ak", magazine_ak())
    case, bullet = cartridge_762(z_tip=-118.0, y=103.0)
    add("mag_ammo", "magazin", (0, 103.0, -88.0), None, case + bullet)

    tip = CHAMBER_Z - 56.0 + 18.0                       # 薬室内の実包（排莢クリップの起点）
    case, bullet = cartridge_762(z_tip=tip, y=b)
    add("ammo", "root", (0, b, tip + 35), None, case)
    add("bullet", "ammo", (0, b, tip + 6), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(O.GRIP["outer"]).centroid
    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K,
                 rear_sight_z=REAR_SIGHT_Z * K, grip_center=(0, c.y * K, c.x * K))
    return m, parts
