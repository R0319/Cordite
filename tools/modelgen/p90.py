"""
FN P90 TR（上面に長いレール、受け部の前の左右に短いレール）のパーツと組み立て（単位 mm、メッシュ版）。

側面形は Wikimedia Commons の真横写真（右側面・FN Herstal の標準型、CC BY-SA 2.0）からトレースした輪郭
（p90_outline.py ← trace_p90.py）。標準型は上に照準器（リングサイト）が付くので、受け部の上面は TR 型の写真
（Commons「FN P90 PDW.jpg」CC0 ほか）から読んだ形に差し替えた（TR_*）。
縮尺はレールの溝の間隔（10.0mm）で合わせ、全長 503mm（FN 公表 505mm）を確かめた。
左右の幅は FN 公表の全幅 55mm を上限に、斜め前の写真から割合で読んだ推定（下の幅の関数・HALF_*）。上面図は無い。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面）、Y=0 グリップの底、Z=0 トリガー、銃口 -Z。

本体（ストック・グリップ・弾倉の受け）は 1 つの樹脂の塊で、親指の穴とトリガーの穴が貫通している。
穴の縁まで丸めるため core.extrude_x_rounded（穴のある側面形を丸めて押し出す）で作る。
排莢は下向き（グリップの中）で、ボルトは外から見えない。コッキングハンドルは受け部の左右の前の玉（ボーン
charging_handle）で、横の棒（ガイド）に沿って後ろへ引く。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import sights
import p90_outline as O
from core import box, extrude_x, extrude_x_beveled, extrude_x_rounded, lathe
from m249 import x_cyl, y_cyl
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
POLY = M.P90_POLY
HOUSING_MAT = M.P90_HOUSING
STEEL_BLACK = M.P90_STEEL

BORE_Y = 102.3
MUZZLE_Z = -166.3
BOLT_FACE_Z = 97.7          # 薬室の後端（銃身 264mm を銃口から逆算。ブルパップなのでトリガーより後ろ）

# 左右の半幅（全幅 55mm が上限。斜め前の写真で、ストックがいちばん幅広く、前のハンドストップが細い）
HALF_STOCK = 27.5
HALF_UPPER = 26.0           # 本体の上半分（弾倉の下）
HALF_GRIP = 24.0            # 親指の穴のまわり
HALF_TRIGGER = 19.0         # トリガーの穴のまわり
HALF_FRONT = 17.5           # 前のハンドストップ
HALF_UNDER_HOUSING = 23.0   # 受け部の下に隠れる所（受け部の側面と同じ面にしない）
BODY_BEVEL = 7.0            # 本体の角の丸み（P90 は角の大きく丸い樹脂の塊。トリガーの穴の下の壁 15mm で 7 が上限）
HALF_HOUSING = 25.0         # 受け部（弾倉 44mm を左右の側板で挟む幅。作者の指摘「サイト周りが太っちょ」で 52 → 50mm）
HALF_MAG = 22.0             # 弾倉 44mm（5.7×28mm 弾 40.5mm を横向きに収める）

# 弾倉（写真）: 後ろの端は本体の段の前、前の端は受け部の前のブロックの手前
MAG_Z = (-82.0, 181.0)
MAG_Y = (115.8, 140.0)           # 下は受け部の溝の底（116）にわずかに埋める（1mm 浮いて下に線が見えていた）
MAG_WALL = 2.5              # 上下の板・前後の端の厚さ
ROTOR_Z, ROTOR_R, ROTOR_H = 160.0, 19.0, 6.5   # 給弾ローター（弾倉の後ろの下。本体の後ろの下のふくらみの中に収まる）
MAG_RIBS = [160.0, 135.0, 110.0, 85.0, 60.0, 35.0, 10.0, -15.0, -40.0, -62.0]   # 側面の縦の補強（写真の縦の筋）
MAG_CHANNEL = (60.0, -86.5, 116.0, 141.5)   # 受け部の中の弾倉の通り道（前後 z, 上下 y）
ARM_Z = 17.0                # 受け部の後ろの腕（弾倉の横を覆う）の前の縁

# TR 型の上面（写真「FN P90 PDW.jpg」（CC0）に mm 目盛りを重ねて読んだ。縮尺はレールの溝の間隔 10mm、
# 原点は銃口の先端。作者の指摘「サイト周りが太っちょすぎる」で読み直した: 上面が 5mm 高く、後ろの端が
# 20mm 後ろへはみ出し、レールが 17mm 後ろにずれていた）
TR_TOP_Y = 170.0            # 受け部の上面（レールの台。レールの頭の上面は 175）
TR_FRONT = [(-109.6, 170.0), (-124.6, 150.4), (-130.9, 127.9)]   # 前の斜めの面
TR_REAR = [(46.6, 118.0), (42.9, 135.4), (35.4, 150.4), (27.9, 161.6), (24.1, 170.0)]   # 後ろの脚の後ろの縁（弾倉をまたぐ）
TR_PANEL = [(-74.0, 154.5), (-18.0, 154.5), (-18.0, 166.0), (-74.0, 166.0)]   # 上の橋の側面の凹んだ枠（写真の暗い長方形）
TR_PANEL_DEPTH = 2.5
TR_TAPER = (145.0, 170.0, 21.0)   # 上の部分は上へ細くなる（作者提供の三面図の後ろの図: 弾倉の上で約 46mm、上面で約 37mm）。
                                  # Y 145 から上面で半幅 21 へ（TR 型の写真では側板が厚めなので三面図より太め）


def housing_half(z, y):
    """受け部の半幅（高さで変わる）。"""
    y0, y1, top = TR_TAPER
    return HALF_HOUSING + (top - HALF_HOUSING) * min(1.0, max(0.0, (y - y0) / (y1 - y0)))
TR_RAIL_Z = (-108.0, 24.0)  # 上面レールの前後
SIDE_RAIL_Z = (-91.0, -67.0)   # 左右の短いレール（前の端）
SIDE_RAIL_Y = 157.5           # 頭（幅 24mm）が上面（TR_TOP_Y）からはみ出さない高さ

# トリガーの穴の後ろ（写真でトリガーの側面が見える所）と、その下のセレクター（回転する円盤）
TRIGGER_WELL = [(17.7, 82.2), (-8.0, 82.2), (-8.0, 52.5), (9.5, 52.5), (13.6, 54.4), (17.7, 62.6), (18.8, 73.5)]
SELECTOR_C = (-1.0, 49.0)   # 円盤の中心 (Z, Y)
SELECTOR_R = 15.0
SELECTOR_SLOT = [(-3.0, 47.5), (-17.5, 47.5), (-17.5, 53.0), (-3.0, 53.0)]   # 前のつまみの所だけ（円盤は本体に埋まる）

MAG_RELEASE = (181.5, 196.0, 117.5, 131.0)    # 弾倉止め（弾倉の後ろの左右のレバー。前後 z, 上下 y）
ROTOR_BULGE = [(178.0, 118.0), (150.0, 118.0), (150.0, 110.0), (156.0, 104.0), (172.0, 103.0), (178.0, 108.0)]

CH_ROD_Z = (-64.0, 18.0)    # コッキングハンドルのガイド（横の棒。写真の灰色の棒）
CH_ROD_Y, CH_ROD_R = 96.5, 4.8
CH_KNOB_Z = -78.0           # 玉（輪）の中心
CH_TRAVEL_MAX = 75.0        # 玉を引ける量（🟡 実物の値は未確認。ガイドの後端を越えない）


def _lerp(a, b, t):
    return a + (b - a) * min(1.0, max(0.0, t))


def body_half(z, y):
    """本体の半幅。上半分（弾倉の下）と下半分（グリップ・穴のまわり）を高さで混ぜる。"""
    if z >= 200.0:
        up = HALF_STOCK
    elif z >= 165.0:
        up = _lerp(HALF_UPPER, HALF_STOCK, (z - 165.0) / 35.0)
    elif z >= 60.0:
        up = HALF_UPPER
    else:
        up = _lerp(HALF_UNDER_HOUSING, HALF_UPPER, (z - 50.0) / 10.0)
    if z >= 215.0:
        lo = HALF_STOCK
    elif z >= 175.0:
        lo = _lerp(HALF_GRIP, HALF_STOCK, (z - 175.0) / 40.0)
    elif z >= 60.0:
        lo = HALF_GRIP
    elif z >= 20.0:
        lo = _lerp(HALF_TRIGGER, HALF_GRIP, (z - 20.0) / 40.0)
    elif z >= -15.0:
        lo = HALF_TRIGGER
    else:
        lo = _lerp(HALF_FRONT, HALF_TRIGGER, (z + 50.0) / 35.0)
    return _lerp(lo, up, (y - 86.0) / 10.0)


def _poly(o):
    from shapely.geometry import Polygon
    return Polygon(o["outer"], o["holes"])


def _parts_of(g):
    return [q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 0.5]


def _ring(q):
    return list(q.exterior.coords)[:-1]


# ---------------------------------------------------------------- 本体
def body_shape():
    """本体の側面形: トレース＋トリガーの穴の後ろ（トリガーの側面）とセレクターの溝を穴に足す。"""
    from shapely.geometry import Polygon
    g = _poly(O.BODY).difference(Polygon(TRIGGER_WELL)).difference(Polygon(SELECTOR_SLOT))
    return max(_parts_of(g), key=lambda q: q.area)


def body():
    """本体（樹脂の 1 つの塊）。穴の縁まで BODY_BEVEL で丸め、場所ごとに body_half の厚み。
    弾倉の後ろの下のふくらみ（回転式の給弾部の収まる所）は少し外へ出る。"""
    g = body_shape()
    out = [extrude_x_rounded(_ring(g), [list(h.coords)[:-1] for h in g.interiors], body_half, BODY_BEVEL, POLY,
                             steps=3)]
    hw = body_half(165.0, 112.0) + 1.2
    out.append(extrude_x_beveled(ROTOR_BULGE, -hw, hw, 2.5, POLY, steps=2))
    return out


def butt_pad():
    """床尾板（ゴム）。"""
    return [extrude_x_beveled(O.BUTT_PAD["outer"], -HALF_STOCK, HALF_STOCK, 5.0, M.RUBBER, steps=2)]


# ---------------------------------------------------------------- 受け部
def housing_shape():
    """受け部（照準器の枠・銃身の覆い）の側面形。標準型のトレースの上を TR 型の上面で置き換える。"""
    from shapely.geometry import Polygon
    g = _poly(O.HOUSING)
    clip = Polygon([(70.0, 0.0), (70.0, 116.0)] + TR_REAR + TR_FRONT + [(-140.0, TR_FRONT[-1][1]), (-140.0, 0.0)])
    g = g.intersection(clip)
    # TR 型は上面の下が詰まっている（標準型は後ろに覗き窓）。弾倉の上のすき間の天井より上だけ埋める
    fill = Polygon([(29.0, 158.0)] + TR_REAR[-2:] + [(-140.0, TR_TOP_Y), (-140.0, 158.0)]).intersection(clip)
    return g.union(fill).difference(Polygon(TR_PANEL))


def housing():
    """受け部: 中央は弾倉の通り道を抜いた形、後ろの腕（Z ARM_Z より後ろ）は弾倉の横も覆う。"""
    from shapely.geometry import box as sbox
    g = housing_shape()
    z0, z1, y0, y1 = MAG_CHANNEL
    main = g.difference(sbox(z1, y0, z0, y1))
    out = []
    for q in _parts_of(main):
        out.append(extrude_x_rounded(_ring(q), [list(h.coords)[:-1] for h in q.interiors],
                                     housing_half, 1.5, HOUSING_MAT, steps=2))
    arm = g.intersection(sbox(ARM_Z, y0, z0, y1))
    for q in _parts_of(arm):
        for s in (1, -1):
            xa, xb = sorted((s * (HALF_MAG + 0.3), s * HALF_HOUSING))
            out.append(extrude_x(_ring(q), xa, xb, HOUSING_MAT))
    # 上の橋の側面の凹み（側面形に抜いた窓の奥の板）
    h = housing_half(0.0, max(y for _, y in TR_PANEL)) - TR_PANEL_DEPTH
    out.append(extrude_x([(z, y) for z, y in TR_PANEL], -h, h, HOUSING_MAT))
    return out


def rails():
    """TR 型のレール: 上面の長いレール（規約の幅 1px・溝 0.5px）と、前の左右の短いレール。"""
    (nw, nh), (hw, hh) = ar15_parts.RAS_NECK, ar15_parts.RAS_HEAD
    z0, z1 = TR_RAIL_Z
    y = TR_TOP_Y
    out = [box(-nw / 2, y - 0.5, z0, nw / 2, y + nh, z1, M.RAIL),
           box(-hw / 2, y + nh, z0, hw / 2, y + nh + hh, z1, M.RAIL)]
    s0, s1 = SIDE_RAIL_Z
    r0 = housing_half(0.0, SIDE_RAIL_Y) - 0.5
    for s in (1, -1):
        xa, xb = sorted((s * r0, s * (r0 + nh + 0.5)))
        out.append(box(xa, SIDE_RAIL_Y - nw / 2, s0, xb, SIDE_RAIL_Y + nw / 2, s1, M.RAIL_SIDE))
        xa, xb = sorted((s * (r0 + nh + 0.5), s * (r0 + nh + 0.5 + hh)))
        out.append(box(xa, SIDE_RAIL_Y - hw / 2, s0, xb, SIDE_RAIL_Y + hw / 2, s1, M.RAIL_SIDE))
    return out


def ch_guides():
    """コッキングハンドルのガイド（左右の横の灰色の棒。受け部の側面の溝に半分埋まる）。"""
    out = []
    for s in (1, -1):
        out.append(_z_rod(s * (HALF_HOUSING - 1.5), CH_ROD_Y, CH_ROD_R, CH_ROD_Z[0], CH_ROD_Z[1], M.P90_GUIDE))
    return out


def _z_rod(x, y, r, z0, z1, mat, n=10):
    return lathe(x, y, [(z0, r), (z1, r)], n, mat)


def barrel():
    """消炎器（トレースの太さの分布）と、受け部の中に隠れる銃身。"""
    prof = sorted(O.MUZZLE_R)                                  # Z 昇順（銃口側から）
    prof = [(z, r) for z, r in prof if r < 13.0]
    out = [lathe(0, BORE_Y, [(MUZZLE_Z, 3.0), (MUZZLE_Z, prof[0][1])] + prof + [(-110.0, prof[-1][1])],
                 ar15_mesh.N_MID, STEEL_BLACK, cap0=False),
           lathe(0, BORE_Y, [(MUZZLE_Z - 0.2, 2.9), (MUZZLE_Z + 20.0, 2.9)], ar15_mesh.N_SMALL, M.BORE, cap0=False)]
    return out


# ---------------------------------------------------------------- 引き金まわり
def trigger_shape():
    from shapely.geometry import Polygon
    holes = [Polygon(h) for h in O.BODY["holes"]]
    hole = min(holes, key=lambda h: h.centroid.distance(Polygon(TRIGGER_WELL).centroid))
    g = Polygon(TRIGGER_WELL).difference(hole.buffer(0.4))
    return max(_parts_of(g), key=lambda q: q.area)


def trigger():
    """トリガー（穴の後ろの幅の広い板。前の面は穴の縁に沿う）。"""
    return [extrude_x_beveled(_ring(trigger_shape()), -8.0, 8.0, 1.5, STEEL_BLACK, steps=2)]


def selector():
    """セレクター（トリガーの下の回転する円盤。ボーン selector は Y 軸まわりに回す）と前のつまみ。"""
    z, y = SELECTOR_C
    return [y_cyl(0.0, z, SELECTOR_R, 47.0, 52.5, STEEL_BLACK, n=20),
            box(-5.0, 47.5, z - SELECTOR_R - 3.0, 5.0, 52.0, z - SELECTOR_R + 2.0, STEEL_BLACK)]


def mag_release():
    """弾倉止め（弾倉の後ろの左右のレバー。本体の側面から少し出る）。"""
    z0, z1, y0, y1 = MAG_RELEASE
    hw = body_half((z0 + z1) / 2, (y0 + y1) / 2) + 1.0
    prof = [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]
    return [extrude_x_beveled(prof, -hw, hw, 1.2, STEEL_BLACK, steps=1)]


def charging_handle():
    """コッキングハンドルの玉（左右。輪の形で、中央に穴）。ガイドに沿って後ろへ動く。"""
    from shapely.geometry import Point, box as sbox
    z, y = CH_KNOB_Z, CH_ROD_Y + 1.0
    g = Point(z, y).buffer(9.0, quad_segs=6).union(sbox(z, y - 7.5, z + 14.0, y + 7.5))
    out = []
    for s in (1, -1):
        xa, xb = sorted((s * (HALF_HOUSING - 0.5), s * (HALF_HOUSING + 5.5)))
        out.append(extrude_x_beveled(_ring(g), xa, xb, 1.2, STEEL_BLACK, steps=1))
        xo = s * (HALF_HOUSING + 5.5)
        out.append(x_cyl(z, y, 4.0, *sorted((xo, xo + s * 0.3)), M.BORE))     # 輪の中の穴（暗い円）
    return out


# ---------------------------------------------------------------- 弾倉
def magazine():
    """50 発弾倉（煙色の樹脂。上面に乗る）。中は透かさず閉じた箱にする（弾 50 発分のポリゴンを省くため。作者指示）。
    側面に縦の補強（写真の縦の筋）。後ろの下に回転式の給弾ローター（装着中は本体の中に隠れ、外すと見える）。"""
    z0, z1 = MAG_Z
    y0, y1 = MAG_Y
    h = HALF_MAG
    mat = M.P90_MAG
    out = [extrude_x_beveled([(z0 + 9.0, y0), (z1 - 9.0, y0), (z1 - 9.0, y1), (z0 + 9.0, y1)], -h, h, 1.0, mat,
                             steps=1),
           # 後ろの端（黒い蓋）・前の端（掛け金の爪が上に出る）
           extrude_x_beveled([(z1 - 9.0, y0), (z1, y0), (z1, y1), (z1 - 9.0, y1)], -h, h, 1.5, M.P90_MAG_CAP, steps=1),
           extrude_x_beveled([(z0, y0), (z0 + 9.0, y0), (z0 + 9.0, y1), (z0 + 4.0, y1 + 3.0), (z0, y1 + 3.0)], -h, h,
                             1.2, M.P90_MAG_CAP, steps=1)]
    for zr in MAG_RIBS:
        for s in (1, -1):
            xa, xb = sorted((s * (h - 0.2), s * (h + 0.6)))
            out.append(box(xa, y0 + 2.5, zr - 0.9, xb, y1 - 2.5, zr + 0.9, mat))
    zc, r = ROTOR_Z, ROTOR_R
    out.append(y_cyl(0.0, zc, r, y0 - ROTOR_H, y0 + 0.3, M.P90_MAG_CAP, n=20))
    return out


def magazine_rounds():
    """弾倉の中の弾（mag_ammo）: 外したときに見える、給弾ローターの溝に乗った 1 発だけ（弾頭が前）。
    下側がローターの底から少し出る。空のときはローターだけが見える。"""
    y = MAG_Y[0] - ROTOR_H + 2.5
    case, bullet = cartridge_57(ROTOR_Z - 20.25, y)
    return case + bullet


def cartridge_57(z_tip, y, x=0.0):
    """5.7×28mm 実包（薬室内。回転体）。"""
    b = z_tip + 40.5
    case = [(b, 3.97), (b - 1.0, 3.97), (b - 1.3, 3.5), (b - 2.2, 3.5), (b - 2.5, 3.97), (b - 25.4, 3.97),
            (b - 28.9, 3.0)]
    bullet = [(b - 28.9, 2.85), (b - 34.0, 2.7), (z_tip, 0.6)]
    return ([lathe(x, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(x, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


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

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "housing", housing() + rails() + ch_guides())
    add("stock", "root", (0, 60.0, 100.0), "body", body() + butt_pad())
    add("lower_receiver", "stock", (0, 60.0, 0), None, [])
    add("selector", "lower_receiver", (0, SELECTOR_C[1], SELECTOR_C[0]), "selector", selector())
    add("trigger", "root", (0, 82.0, 8.0), "trigger", trigger())
    add("mag_release", "stock", (0, MAG_RELEASE[3], MAG_RELEASE[1]), "mag_release", mag_release())

    add("barrel", "root", (0, b, BOLT_FACE_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BOLT_FACE_Z), None, [])
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])
    add("handguard", "root", (0, b, -60.0), None, [])
    add("rail_top", "root", (0, TR_TOP_Y + 5.0, sum(TR_RAIL_Z) / 2), None, [])
    # デフォルトのアイアンサイト（TR 型は照準器が無くレールだけ。折りたたみ式をレールの前後の端に載せる。
    # サイトのアタッチメントを付けるとコードがこのボーンを描かない）
    irons, sight_y = sights.default_irons(TR_TOP_Y + 5.0, TR_RAIL_Z[1] - 13.0, TR_RAIL_Z[0] + 11.0, trigger_z=8.0)
    add("iron_sight", "root", (0, TR_TOP_Y + 5.0, TR_RAIL_Z[1] - 13.0), "iron_sight", irons)
    add("rail_side", "root", (HALF_HOUSING + 5.0, SIDE_RAIL_Y, sum(SIDE_RAIL_Z) / 2), None, [])
    add("rail_bottom", "root", (0, 40.0, -112.0), None, [])          # 下面レールは無い（前のハンドストップの下）

    add("bolt", "root", (0, b, BOLT_FACE_Z), None, [])                # ボルトは外から見えない（位置だけ）
    add("charging_handle", "receiver", (0, CH_ROD_Y, CH_KNOB_Z), "charging_handle", charging_handle())

    zc = sum(MAG_Z) / 2
    add("magazin", "root", (0, MAG_Y[0], zc), "magazine", magazine())
    add("mag_ammo", "magazin", (0, MAG_Y[0] - ROTOR_H, ROTOR_Z), None, magazine_rounds())

    tip = BOLT_FACE_Z - 40.5                                  # 薬室内の実包
    case, bullet = cartridge_57(tip, b)
    add("ammo", "root", (0, b, tip + 30.0), None, case)
    add("bullet", "ammo", (0, b, tip + 6.0), None, bullet)

    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=sight_y * K,
                 rear_sight_z=(TR_RAIL_Z[1] - 13.0) * K, grip_center=(0, 55.0 * K, 40.0 * K), support_z=-84.0 * K)
    return m, parts
