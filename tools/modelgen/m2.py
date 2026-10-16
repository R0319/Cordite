"""
M2 重機関銃（ブローニング M2HB、.50 BMG、ベルト給弾）のパーツと組み立て（単位 mm、メッシュ版）。

側面形は米陸軍 TM 9-1225（1943、パブリックドメイン）Figure 7「Heavy Barrel, Flexible」の右側面の写真からトレースした
輪郭（m2_outline.py ← trace_m2.py）。縮尺は全長 65 1/8 in（1654mm）で合わせ、銃身の長さ 45in・太さが合うことを確かめた。
部品の構造は FM 23-65（2002）図 1-3〜1-6・2-2 と TC 3-22.50（2017）図 2-1・2-2 の線画で確かめた
（照尺＝起こす板に穴の照門、照星＝刃とそれを覆うアーチの覆い、背板＝縦の両手グリップの間に親指で押す引き金と緩衝筒、
右側面に装填ハンドル、受け部の前に左右へ抜けた給弾口）。
幅は推定（上・前・後ろの図が無い）: 受け部 94mm（TC の後ろからの図の比率）、グリップの外側の幅 約 165mm
（博物館の実物の全幅 16cm と合う）。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面）、Z=0 親指で押す引き金（両手グリップの間）、Y=0 グリップの下端、銃口 -Z。

弾薬箱（M2A1、273×140×184mm）は左側面の金具に付けて、ベルトを左から給弾口へ入れる（パワードスーツで手に持つ前提。
三脚に載せる場合は三脚の弾薬箱の台に置く → m3_tripod.py）。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import sights
import m2_outline as O
from core import box, extrude_x, extrude_x_beveled, lathe
from m249 import arc_ring, clip_y, clip_z, outline_parts, rotated, x_cyl, y_cyl
from m1912 import arc_z
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
STEEL = M.M2_STEEL
CAN = M.M2_CAN

BORE_Y = 61.0
MUZZLE_Z = -1607.0
RCV_HALF = 47.0                  # 受け部の半幅（推定 94mm）
RCV_Z = (-632.0, -36.0)
COVER_Z = (-590.0, -165.0)       # 上蓋（照尺の前〜照星の台の後ろ。前の端が蝶番）
COVER_Y = 125.5                  # 上蓋の下面（受け部の側板の上の縁）
FEEDWAY = (-545.0, -395.0, 87.0, 108.0)   # 給弾口（左右に抜ける）: Z 前・後、Y 下・上（写真の右側面の窓。上端は弾の胴に少し被せる）
TRUNNION_PIN = (-518.0, 23.0)    # 前の取付けピンの穴（三脚の受け金具が入る）

SIGHT_Y = 160.0                  # 照準線（照星の刃の先・照尺の穴の中心）
FRONT_Z = -610.0                 # 照星の刃
LEAF_Z = -111.0                  # 照尺（起こした板。写真の Z -100〜-122）
EYE_RELIEF = 250.0               # ADS の目は照尺の 250mm 後ろ（両手グリップの後ろに立って覗く）
_EYE = LEAF_Z + EYE_RELIEF
LEAF_HOLE = min(12.0, sights.HOLE_ANGLE * EYE_RELIEF)            # 照門の穴（誇張。目から遠いので上限で止める）
BLADE_W = sights.POST_ANGLE * (_EYE - FRONT_Z)                    # 照星の刃（誇張）

GRIP_X, GRIP_Z, GRIP_R, GRIP_Y = 68.0, 34.0, 15.0, (2.0, 132.0)   # 両手グリップ（縦の円柱）
BUFFER_Y, BUFFER_R = 72.0, 13.0                                     # 緩衝筒（背板から後ろへ）

SUPPORT_HOLES_UP = ([-727.0, -770.0, -817.0], 39.0)              # 銃身の支えの穴（Z の列, 水平からの角度）。上の列
SUPPORT_HOLES_LOW = ([-703.0, -747.0, -794.0, -841.0], -17.0)    # 下の列
HOLE_R = 12.0
CARRIER_Z = (-1000.0, -872.0)    # 銃身の留め輪（穴の開いた輪。取っ手の軸が下に付く）
CAN_SIZE = (140.0, 184.0, 273.0)                                  # 弾薬箱 M2A1（幅 X, 高さ Y, 長さ Z）
CAN_CENTER = (RCV_HALF + 18.0 + 70.0, -8.0, -470.0)


def receiver():
    """受け部: 側板（トレース。上蓋の所は側板の上の縁まで）・給弾口（左右に抜ける）・前の取付けピンの穴・下の取付け金具。"""
    o = O.RECEIVER
    hole = [(FEEDWAY[0], FEEDWAY[2]), (FEEDWAY[1], FEEDWAY[2]), (FEEDWAY[1], FEEDWAY[3]), (FEEDWAY[0], FEEDWAY[3])]
    body = clip_y(o, -1e4, COVER_Y + 0.5)
    body["holes"] = [hole]
    out = outline_parts(body, -RCV_HALF, RCV_HALF, STEEL)
    top = clip_y(o, COVER_Y, 1e4)
    for z0, z1 in ((COVER_Z[1] - 0.5, RCV_Z[1] + 10.0), (RCV_Z[0] - 10.0, COVER_Z[0] + 0.5)):
        out.append(extrude_x_beveled(clip_z(top, z0, z1)["outer"], -RCV_HALF, RCV_HALF, 1.5, STEEL, steps=1))
    pz, py = TRUNNION_PIN
    for s in (1, -1):
        xa, xb = sorted((s * (RCV_HALF - 1.0), s * (RCV_HALF + 0.3)))
        out.append(x_cyl(pz, py, 9.0, xa, xb, M.BORE, n=10))
    out.append(extrude_x_beveled(O.BRACKET["outer"], -22.0, 22.0, 2.0, STEEL, steps=1))
    # 給弾口の奥（ベルトの弾が載る台。上下の面は側板の穴の縁と同じ高さ）
    out.append(box(-RCV_HALF + 2.0, FEEDWAY[2] - 2.0, FEEDWAY[0], RCV_HALF - 2.0, FEEDWAY[2], FEEDWAY[1], M.STEEL_DARK))
    # 中央の弾の案内（弾頭の上の隙間から向こうの背景が線に見えないように）
    out.append(box(-2.0, FEEDWAY[2], FEEDWAY[0], 2.0, FEEDWAY[3], FEEDWAY[1], M.STEEL_DARK))
    return out


def feed_cover():
    """上蓋（給弾機構の蓋。前の端の蝶番で上へ開く）。側板の間に載る板。"""
    o = clip_z(clip_y(O.RECEIVER, COVER_Y, 1e4), *COVER_Z)
    return [extrude_x_beveled(o["outer"], -RCV_HALF + 1.0, RCV_HALF - 1.0, 2.0, STEEL, steps=1)]


def cover_latch():
    """上蓋の留め金のつまみ（後ろの端。回して上蓋を開ける）。"""
    return [box(-12.0, 131.0, COVER_Z[1] - 30.0, 12.0, 135.0, COVER_Z[1] - 4.0, M.STEEL_DARK)]


def barrel_support():
    """銃身の支え（受け部の前の穴の開いた筒）: トレースの太さの回転体と、楕円の穴（暗い円で表す。上 3・下 4 個ずつ左右）。"""
    prof = sorted(O.SUPPORT_R)
    out = [lathe(0, BORE_Y, [(prof[0][0], 22.0)] + prof + [(prof[-1][0], 22.0)], ar15_mesh.N_MID, STEEL)]
    for zs, ang in (SUPPORT_HOLES_UP, SUPPORT_HOLES_LOW):
        for z in zs:
            r = min(rr for zz, rr in prof if abs(zz - z) < 20.0)
            for s in (1, -1):
                disc = x_cyl(z, BORE_Y, HOLE_R, r - 1.2, r + 0.3, M.BORE, n=10)
                out += rotated([disc], "z", s * ang if s > 0 else 180.0 - ang, (0.0, BORE_Y, z))
    return out


def front_sight():
    """照星: 台・刃（誇張）・刃を覆うアーチの覆い（FM 23-65 図 1-4）。"""
    o = clip_y(O.FRONT_SIGHT, -1e4, 141.0)
    out = [extrude_x_beveled(o["outer"], -20.0, 20.0, 1.5, STEEL, steps=1)]
    r_in = BLADE_W / 2 + 6.0
    cy = SIGHT_Y + 7.0 - r_in - 3.0                    # アーチの上の外側が写真の覆いの上端（Y 167）に合う
    hz = 17.0                                           # 覆いの前後の半分（写真の照星の幅 Z -592〜-630）
    out.append(arc_z(cy, r_in, r_in + 3.0, FRONT_Z - hz, FRONT_Z + hz, 0.0, 180.0, STEEL, n=14))
    for s in (1, -1):                                   # アーチの脚（台まで）
        xa, xb = sorted((s * r_in, s * (r_in + 3.0)))
        out.append(box(xa, 139.0, FRONT_Z - hz, xb, cy, FRONT_Z + hz, STEEL))
    out.append(sights.post(BLADE_W, 139.0, SIGHT_Y, FRONT_Z, M.STEEL_DARK, depth=4.0))
    return out


def rear_sight():
    """照尺: 受け部の上の台（トレース）と、起こした板（穴の照門。照準線の高さ）・左の風偏つまみ（FM 23-65 図 1-3）。"""
    base = clip_y(O.REAR_SIGHT, -1e4, 152.0)
    out = [extrude_x_beveled(base["outer"], -22.0, 22.0, 1.5, STEEL, steps=1)]
    # 板の前後の盛り上がり（写真 Y 152〜162）は左右の頬板。中央は抜けていて照準線（Y 160）が通る
    cheek = clip_z(clip_y(O.REAR_SIGHT, 151.5, 163.0), -180.0, -95.0)
    for s in (1, -1):
        xa, xb = sorted((s * 9.0, s * 22.0))
        out.append(extrude_x_beveled(cheek["outer"], xa, xb, 1.0, STEEL, steps=1))
    leaf = sights.aperture_plate(SIGHT_Y, LEAF_Z - 2.0, LEAF_Z + 2.0, LEAF_HOLE, 139.0, M.STEEL_DARK, half_w=11.0,
                                 ears=False)
    out += leaf
    top = max(y for _, y in O.REAR_SIGHT["outer"])
    for s in (1, -1):                                   # 板の左右の枠（目盛りの縦の棒。上は写真の照尺の先）
        xa, xb = sorted((s * 9.0, s * 13.0))
        out.append(box(xa, 139.0, LEAF_Z - 8.0, xb, top, LEAF_Z + 8.0, M.STEEL_DARK))
    out.append(box(-13.0, top - 4.0, LEAF_Z - 8.0, 13.0, top, LEAF_Z + 8.0, M.STEEL_DARK))
    out.append(x_cyl(LEAF_Z + 14.0, 131.0, 7.0, 22.0, 32.0, STEEL, n=10))   # 風偏つまみ（左）
    return out


def y_lathe(x, z, profile, n, mat):
    """縦（Y 軸）の回転体。profile は [(y, r)]。Z 軸の回転体を作って Y と Z を入れ替える（m249.y_cyl と同じやり方）。"""
    from core import MeshPart
    m = lathe(x, z, profile, n, mat)
    swap = lambda v: (v[0], v[2], v[1])
    nm = None if m.normals is None else [[swap(v) for v in f] for f in m.normals]
    return MeshPart([swap(v) for v in m.verts], m.faces, m.mat, nm, m.charts, m.chart_uv, m.chart_edge)


def backplate():
    """背板: 縦の板（トレースの前の部分）・左右の縦の両手グリップ・上下の腕・緩衝筒。"""
    plate = clip_z(O.BACKPLATE, -40.0, -18.0)
    out = [extrude_x_beveled(plate["outer"], -RCV_HALF, RCV_HALF, 2.0, STEEL, steps=1)]
    y0, y1 = GRIP_Y
    for s in (1, -1):
        x = s * GRIP_X
        out.append(y_lathe(x, GRIP_Z, [(y0, 3.0), (y0 + 3.0, GRIP_R), (y1 - 3.0, GRIP_R), (y1, 3.0)], 12, M.M2_GRIP))
        xa, xb = sorted((s * (RCV_HALF - 6.0), s * (GRIP_X + 6.0)))
        for ya, yb in ((y1 - 12.0, y1 - 2.0), (y0 + 2.0, y0 + 12.0)):     # 上下の腕（背板からグリップへ）
            out.append(box(xa, ya, -24.0, xb, yb, GRIP_Z + 4.0, STEEL))
    out.append(lathe(0, BUFFER_Y, [(-22.0, BUFFER_R), (22.0, BUFFER_R), (26.0, BUFFER_R - 3.0)], 12, STEEL))
    return out


def thumb_trigger():
    """親指で押す引き金（両手グリップの間の蝶の形の板）。"""
    return [box(-30.0, 94.0, -2.0, 30.0, 102.0, 8.0, M.STEEL_DARK),
            box(-6.0, BUFFER_Y + BUFFER_R - 1.0, -19.0, 6.0, 96.0, 0.0, M.STEEL_DARK)]   # 下は緩衝筒に埋める


def trigger_block():
    """安全装置（背板の上の滑る板。S/F）。"""
    return [box(-9.0, 132.0, -30.0, 9.0, 140.0, -18.0, M.STEEL_DARK),
            box(-3.0, 140.0, -27.0, 3.0, 143.0, -21.0, M.MARK_WHITE)]


def retracting_slide():
    """装填ハンドル（右側面の滑り板とレバー、上の丸いつまみ）。"""
    x = -RCV_HALF
    return [box(x - 6.0, 82.0, -340.0, x + 0.5, 118.0, -250.0, STEEL),
            box(x - 10.0, 25.0, -314.0, x - 5.0, 112.0, -298.0, STEEL),
            x_cyl(-290.0, 116.0, 13.0, x - 24.0, x - 5.5, M.STEEL_DARK, n=12)]


def barrel():
    """銃身（トレースの太さ）・銃口の穴・留め輪の小さな穴。"""
    prof = sorted(O.BARREL_R)
    pts = [(MUZZLE_Z, 6.5), (MUZZLE_Z, prof[0][1])] + [p for p in prof if p[0] > MUZZLE_Z] + [(CARRIER_Z[1], 22.0)]
    out = [lathe(0, BORE_Y, pts, ar15_mesh.N_MID, STEEL, cap0=False),
           lathe(0, BORE_Y, [(MUZZLE_Z - 0.2, 6.4), (MUZZLE_Z + 30.0, 6.4)], ar15_mesh.N_SMALL, M.BORE, cap0=False),
           # 支えの中の銃身（穴から見える）
           lathe(0, BORE_Y, [(-872.0, 22.0), (-632.0, 22.0)], ar15_mesh.N_MID, M.STEEL_DARK)]
    for z in (-950.0, -975.0):
        cr = min(prof, key=lambda p: abs(p[0] - z))[1]          # その位置の留め輪の太さ
        for ang in (25.0, 0.0, -25.0):
            for s in (1, -1):
                d = x_cyl(z, BORE_Y, 4.0, cr - 1.5, cr + 0.2, M.BORE, n=8)
                out += rotated([d], "z", ang if s > 0 else 180.0 - ang, (0.0, BORE_Y, z))
    return out


def carry_handle():
    """運搬用の取っ手（留め輪の下の軸から下がる枠。銃の中心の縦の面。写真に目盛りを重ねて読んだ）。"""
    r = 3.0
    out = [lathe(0, 33.0, [(-998.0, r + 1.0), (-912.0, r + 1.0)], 8, STEEL)]          # 軸（上は留め輪に埋める）
    for za, zb in ((-926.0, -853.0), (-995.0, -1067.0)):
        out.append(box(-r, -14.0, za - r, r, 33.0, za + r, STEEL))                     # 軸から下へ
        out.append(box(-r, -20.0 - r, min(za, zb) - r, r, -20.0 + r, max(za, zb) + r, STEEL))   # 外へ折れる
        out.append(box(-r, -64.0, zb - r, r, -14.0, zb + r, STEEL))                    # 外側を下へ
    out.append(lathe(0, -64.0, [(-1060.0, 6.0), (-863.0, 6.0)], 10, M.M2_GRIP))       # 握り棒
    return out


def cartridge_50(x, y, z_tip, n=8):
    """.50 BMG 実包（回転体。全長 138mm、薬莢 99mm、縁 20.4mm、弾頭 12.9mm）。z_tip が弾頭の先（-Z 側）。"""
    b = z_tip + 138.0
    case = [(b, 10.2), (b - 2.0, 10.2), (b - 2.5, 9.0), (b - 4.5, 9.0), (b - 5.0, 10.4), (b - 77.0, 9.4),
            (b - 84.0, 7.0), (b - 99.0, 6.9)]
    bullet = [(b - 99.0, 6.5), (b - 110.0, 6.4), (b - 125.0, 4.5), (b - 134.0, 1.8), (z_tip, 0.5)]
    return [lathe(x, y, case, n, M.BRASS, cap0=True, cap1=False), lathe(x, y, bullet, n, M.COPPER, cap0=False, cap1=True)]


BELT_X = [112.0, 88.0, 64.0, 36.0, 10.0, -16.0, -40.0]   # ベルトの弾の左右位置（箱の上〜給弾口の中）
BELT_Y = [88.0, 94.0, 99.0, 99.0, 99.0, 99.0, 99.0]
ROUND_TIP_Z = FEEDWAY[0] + 4.0


BELT_RING_Z = (112.0, 128.0)   # リンクの 2 つの輪（弾頭の先から後ろへ）。弾帯の 1 発ごとのボーンの pivot の Z はこの中央


def belt_open_deg(i):
    """i 発目のリンクの開いた側の向き [度]: 隣の 2 発を結ぶ向き（先頭→末尾）を -90° 回した向き（両端は片側の隣で）。
    M249 と同じ定義（アニメーション側は pivot から同じ計算で求める）。水平の所では真下（270°）。"""
    n = len(BELT_X)
    a, b = belt_pivot(max(i - 1, 0)), belt_pivot(min(i + 1, n - 1))
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) - 90.0


def belt_round(i):
    """弾帯の i 発目（先頭＝給弾口の奥が 0。ボーン belt_ii）: 弾とそのリンク（M9。弾ごとに 2 つの輪、開いた側 60°）。"""
    x, y, _ = belt_pivot(i)
    nd = belt_open_deg(i)
    out = cartridge_50(x, y, ROUND_TIP_Z)
    for z in BELT_RING_Z:
        out.append(arc_ring(x, y, ROUND_TIP_Z + z - 4.0, ROUND_TIP_Z + z + 4.0, 9.6, 11.0, nd + 30.0, nd + 330.0,
                            M.STEEL_DARK, n=8))
    return out


def belt_pivot(i):
    j = len(BELT_X) - 1 - i
    return (BELT_X[j], BELT_Y[j], ROUND_TIP_Z + sum(BELT_RING_Z) / 2)


LINK_EJECT = (-RCV_HALF + 8.0, 99.0)   # 飛んでいく空のリンクの静止位置（x, y）: 給弾口の右の出口（Z -545〜-395）の内側


def link_eject():
    """撃つたびに給弾口の右（給弾と反対の側）から飛ぶ空のリンク 1 個。静止位置は受け部の中（見えない）。"""
    x, y = LINK_EJECT
    return [arc_ring(x, y, ROUND_TIP_Z + z - 4.0, ROUND_TIP_Z + z + 4.0, 9.6, 11.0, 300.0, 600.0, M.STEEL_DARK, n=8)
            for z in BELT_RING_Z]


def ammo_can():
    """弾薬箱 M2A1（左側面の金具に付ける）: 箱・蓋の縁・取っ手・受け部への金具。"""
    w, h, ln = CAN_SIZE
    cx, cy, cz = CAN_CENTER
    out = [box(cx - w / 2, cy - h / 2, cz - ln / 2, cx + w / 2, cy + h / 2, cz + ln / 2, CAN),
           box(cx - w / 2 - 2.0, cy + h / 2 - 22.0, cz - ln / 2 - 2.0, cx + w / 2 + 2.0, cy + h / 2 - 16.0,
               cz + ln / 2 + 2.0, CAN),                                                # 蓋の縁
           box(cx - 10.0, cy + h / 2, cz - 60.0, cx + 10.0, cy + h / 2 + 4.0, cz + 60.0, M.STEEL_DARK),   # 取っ手
           box(RCV_HALF - 1.0, 40.0, cz - 45.0, cx - w / 2 + 2.0, 70.0, cz + 45.0, STEEL)]                # 金具
    return out


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

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, -300.0), "receiver", receiver() + barrel_support() + front_sight())
    add("feed_cover", "receiver", (0, COVER_Y, COVER_Z[0]), "feed_cover", feed_cover())     # 前の端の蝶番で開く
    add("mag_release", "feed_cover", (0, 133.0, COVER_Z[1] - 17.0), "cover_latch", cover_latch())
    add("rear_sight", "receiver", (0, 139.0, LEAF_Z), "rear_sight", rear_sight())
    add("stock", "root", (0, BUFFER_Y, -30.0), "backplate", backplate())                     # 背板と両手グリップ
    add("trigger", "stock", (0, 98.0, 0.0), "trigger", thumb_trigger())
    add("selector", "stock", (0, 137.0, -24.0), "trigger_block", trigger_block())
    add("charging_handle", "receiver", (0, 100.0, -295.0), "retracting_slide", retracting_slide())
    add("bolt", "receiver", (0, b, -200.0), None, [box(-20.0, b - 25.0, -380.0, 20.0, b + 25.0, -60.0, M.STEEL_DARK)])
    add("barrel", "root", (0, b, -632.0), "barrel", barrel() + carry_handle())
    add("chamber", "barrel", (0, b, -560.0), None, [])
    add("muzzle", "barrel", (0, b, MUZZLE_Z), None, [])
    add("handguard", "root", (0, b, -750.0), None, [])
    add("rail_top", "root", (0, 133.0, -400.0), None, [])
    add("magazin", "root", CAN_CENTER, "ammo_can", ammo_can())
    add("mag_ammo", "magazin", (0, 99.0, ROUND_TIP_Z), None, [])     # 弾帯を束ねる親（リロード・弾切れで隠す）
    for i in range(len(BELT_X)):            # 1 発ずつ（先頭＝給弾口の奥が belt_00）。発射で隣の静止位置へ送る
        add(f"belt_{i:02d}", "mag_ammo", belt_pivot(i), None, belt_round(i))
    # 薬室の 1 発（排莢で飛ぶ薬莢 ammo と弾頭 bullet）
    rd = cartridge_50(0, b, -598.0)
    add("ammo", "root", (0, b, -510.0), None, rd[:1])
    add("bullet", "ammo", (0, b, -598.0), None, rd[1:])
    add("link_eject", "root", (*LINK_EJECT, ROUND_TIP_Z + sum(BELT_RING_Z) / 2), None, link_eject())

    # 両手で後ろのグリップを握る（手先＝グリップの前の面の少し前）
    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K, rear_sight_z=LEAF_Z * K,
                 grip_center=(0, 70.0 * K, GRIP_Z * K), support_z=-700.0 * K, eye_relief=EYE_RELIEF * K,
                 hands=((-GRIP_X * K, 75.0 * K, (GRIP_Z - 10.0) * K), (GRIP_X * K, 75.0 * K, (GRIP_Z - 10.0) * K)))
    return m, parts
