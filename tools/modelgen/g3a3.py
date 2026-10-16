"""
G3A3（固定ストック・細身のハンドガード・オリーブ色の樹脂部品）のパーツと組み立て（単位 mm、メッシュ版）。

側面形は作者提供の真横写真（左側面）からトレースした輪郭（g3_outline.py ← trace_g3.py）を使う。縮尺は全長 1025mm。
同じ HK のローラー遅延式の MP5（mp5.py）と構造が同じなので、受け部の断面の押し出し・回転ドラムの照門・リングの照星・
排莢口とボルトの作りは MP5 にならった。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝排莢口の側）、Y=0 グリップ底面、Z=0 トリガー、銃口 -Z。

写真に無い所（推定）: 右側面（排莢口の位置・大きさは MP5 の比率と弾の長さから）、左右の幅（公表の幅 45mm を上限に、
受け部 41mm・ハンドガード 48mm・ストック 44mm）。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import sights
import g3_outline as O
from ak47 import _clip, _yr, _zr
from core import box, extrude_x, extrude_x_beveled, inflate_x, lathe, densify
from m249 import ring_z, rotated, slotted_flash_hider, x_cyl
from mp5 import _annulus_z, extrude_z
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
STEEL_BLACK = M.G3_STEEL
RCV_MAT = M.G3_RECEIVER
OD = M.G3_OD             # オリーブ色の樹脂（ハンドガード・グリップ・ストック）

BORE_Y = 177.0           # 銃身の軸
MUZZLE_Y = 175.7         # 照星より前の銃身・消炎器の中心（写真の上下の中点 175.3〜176.4）
SIGHT_Y = 225.0          # 照準線（照星のリングのフードの中心の少し下）
MUZZLE_Z = -605.0
BOLT_FACE_Z = -155.0     # ボルトの前面＝薬室の後端（銃身 450mm を銃口から逆算）
REAR_SIGHT_Z = 77.0      # 照門ドラムの中心（写真）
FRONT_POST_Z = -483.5    # 照星のポスト（フードの中心。照準半径 561mm、公表値 572mm）
_EYE = sights.eye_z(0.0, REAR_SIGHT_Z)
REAR_HOLE = sights.HOLE_ANGLE * (_EYE - REAR_SIGHT_Z)
POST_W = sights.POST_ANGLE * (_EYE - FRONT_POST_Z)
DRUM_R = 11.0

# 左右の半幅（推定。公表の幅 45mm が一番広い所）
HALF_RECEIVER = 20.5
HALF_HOUSING = 19.0      # トリガーハウジング
HALF_GRIP = 16.0
HALF_GUARD = 6.0
HALF_MAG = 14.5          # 20 発弾倉（7.62×51mm の複列）
HALF_MAGWELL = 16.0
HALF_HG = 18.0           # ハンドガードの丸み（高さ 38〜46mm に収まる半径。幅は width_fn で 1.3〜1.2 倍＝後ろ 47mm → 前 43mm）
HALF_STOCK = 22.0
HALF_BUTT = 23.0

RCV_FRONT_Z = -205.0     # 受け部の前の端（ハンドガードの後ろの端）
RCV_REAR_Z = 100.0       # 押し出しの後ろの端（ここから後ろは後端キャップ）
RCV_BOTTOM = 158.0       # 受け部の断面の下端（写真の受け部の下の縁 Y 160。ハウジング・弾倉の受けに 2mm 重ねる）
RCV_TOP = 209.5
RCV_FRONT_BOTTOM = 151.0
RCV_TOP_R = 16.0
RCV_GROOVE = (171.0, 178.0, 2.0)   # 側面の長い溝（写真の暗い帯）
RCV_GROOVE_Z = (-110.0, 92.0)

# 右側面の排莢口（写真に無い。MP5 の位置の比率と、7.62×51mm 弾 71mm が抜ける長さから推定）と、奥で動くボルト
PORT_Z = (-135.0, -62.0)
PORT_Y = (180.0, 197.0)
PORT_CORNER_R = 7.0
PORT_INNER_X = 18.5
BOLT_MAT = M.STEEL
BOLT_TRAVEL_MAX = 100.0  # 🟡 実物の値は未確認（後端キャップの中に収まる長さ）

TUBE_Y, TUBE_R = 203.5, 7.7       # コッキングチューブ（写真の上の縁 211.2）
TUBE_Z = (-205.0, -493.0)
CH_SLOT_Z = (-378.0, -243.0)      # コッキングハンドルの溝（チューブの左側面。前の端が閉鎖位置＝写真のハンドルの位置）
CH_ANGLE = 72.0
CH_Z = -369.5                    # 写真の明るい箱 Z -357〜-382（上の縁 214.4）
CARRY_LOOP = (-96.5, -202.0, 177.0, 211.3)   # 針金の上の縁 213.3（写真）   # 折りたたんだ運搬用ハンドル（針金の輪。左側面）の Z, Y の範囲


# ---------------------------------------------------------------- 受け部
def _rcv_section(groove=True, port=False, bottom=None):
    """受け部の断面（X, Y）。mp5._rcv_section と同じ作り（上の角を丸め、側面に溝、port=True で右側面に排莢口）。"""
    h, top, r = HALF_RECEIVER, RCV_TOP, RCV_TOP_R
    bottom = RCV_BOTTOM if bottom is None else bottom
    g0, g1, gd = RCV_GROOVE
    yc = top - r

    def arc(cx, a0, a1, n=9):
        return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
                 yc + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]

    def side(sgn, upward):
        pts = [(sgn * h, bottom), (sgn * h, g0 - 1.5)]
        if groove:
            pts += [(sgn * (h - gd), g0), (sgn * (h - gd), g1), (sgn * h, g1 + 1.5)]
        pts.append((sgn * h, yc))
        return pts if upward else pts[::-1]

    left = side(1, True) + arc(h - r, 0.0, 90.0)
    if not port:
        right = arc(-(h - r), 90.0, 180.0) + side(-1, False)
    else:
        py0, py1 = PORT_Y
        a_cut = math.degrees(math.asin((py1 - yc) / r))
        right = arc(-(h - r), 90.0, 180.0 - a_cut, 7)
        right += [(0.0, py1), (0.0, py0), (-h, py0)]
        right += [p for p in side(-1, False) if p[1] < py0]
    pts = []
    for p in left + right:
        if not pts or math.dist(pts[-1], p) > 1e-6:
            pts.append(p)
    if math.dist(pts[0], pts[-1]) <= 1e-6:
        pts.pop()
    return pts


def receiver():
    """受け部（板金の筒）。断面を前後に押し出し、右側面の排莢口の区間だけ窓を切り欠く（mp5.receiver と同じ）。
    後ろは写真の輪郭の後端キャップ（ストックの受け。下に 2 本のピン）。"""
    h = HALF_RECEIVER
    pz0, pz1 = PORT_Z
    gz0, gz1 = RCV_GROOVE_Z
    # 弾倉の受けより前（Z -160 まで）は写真で受け部の下の縁が Y 152 まで下がる（ハンドガードの後ろの端を受ける所）
    out = [extrude_z(_rcv_section(groove=False, bottom=RCV_FRONT_BOTTOM), RCV_FRONT_Z, -158.0, RCV_MAT),
           extrude_z(_rcv_section(groove=False), -158.0, gz0, RCV_MAT),
           extrude_z(_rcv_section(groove=True), gz0, pz0, RCV_MAT),
           extrude_z(_rcv_section(groove=True, port=True), pz0, pz1, RCV_MAT),
           extrude_z(_rcv_section(groove=True), pz1, gz1, RCV_MAT),
           extrude_z(_rcv_section(groove=False), gz1, RCV_REAR_Z, RCV_MAT)]
    out.append(box(-0.3, PORT_Y[0] - 0.3, pz0, 12.0, PORT_Y[1] + 0.3, pz1, M.BORE))   # 排莢口の奥
    r = PORT_CORNER_R
    for zc, yc, sz, sy in ((pz0 + r, PORT_Y[0] + r, -1, -1), (pz1 - r, PORT_Y[0] + r, 1, -1),
                           (pz0 + r, PORT_Y[1] - r, -1, 1), (pz1 - r, PORT_Y[1] - r, 1, 1)):
        pts = [(zc + sz * r, yc + sy * r)]
        pts += [(zc + sz * r * math.cos(math.radians(a)), yc + sy * r * math.sin(math.radians(a)))
                for a in range(0, 91, 15)]
        x_out = -h + 0.1 if sy < 0 else -h + 0.8
        out.append(extrude_x(pts, x_out, -PORT_INNER_X - 0.2, RCV_MAT))
    # 後端キャップ（写真の輪郭。上の角は受け部の丸みに合わせて大きく丸める）
    out.append(extrude_x_beveled(O.END_CAP["outer"], -h, h, 6.0, RCV_MAT, steps=3))
    for z in (100.5, 128.0):                                   # 後端キャップの下の 2 本のピン（写真）
        for s in (1, -1):
            xa, xb = sorted((s * (h - 0.5), s * (h + 1.2)))
            out.append(x_cyl(z, 151.0, 5.0, xa, xb, STEEL_BLACK, n=12))
    return out


def magwell():
    """弾倉の受け（受け部と一体の板金。前の端が斜め）と、左側面の弾倉止めの台（写真の四角い出っ張り）。"""
    out = [extrude_x_beveled(O.MAGWELL["outer"], -HALF_MAGWELL, HALF_MAGWELL, 3.5, RCV_MAT, steps=2)]
    out.append(extrude_x_beveled([(-78.0, 126.0), (-62.0, 126.0), (-62.0, 141.0), (-78.0, 141.0)],
                                 -HALF_MAGWELL - 2.0, HALF_MAGWELL + 2.0, 1.0, STEEL_BLACK, steps=1))
    return out


def cocking_tube():
    """コッキングチューブ（ハンドガードの上で受け部から照星まで）。左側面にハンドルの溝。受け部の上の前の端に
    チューブの後ろの金具（写真の Z -150〜-205 の段）。"""
    out = [lathe(0, TUBE_Y, [(TUBE_Z[1], TUBE_R), (TUBE_Z[0] + 55.0, TUBE_R)], ar15_mesh.N_MID, RCV_MAT)]
    out.append(box(TUBE_R - 1.5, TUBE_Y - 2.0, CH_SLOT_Z[0], TUBE_R + 0.2, TUBE_Y + 2.0, CH_SLOT_Z[1], M.BORE))
    out.append(extrude_x_beveled([(-138.0, RCV_TOP - 3.0), (-210.0, RCV_TOP - 3.0), (-210.0, 211.5), (-204.0, 213.5),
                                  (-196.0, 216.0), (-150.0, 216.0)], -TUBE_R - 2.0, TUBE_R + 2.0, 2.0, RCV_MAT, steps=2))   # 写真の上の段
    return out


def charging_handle():
    """コッキングハンドル（ボーン charging_handle。チューブの左側面から左へ出るレバーと、その先のつまみ）。
    非往復式で、閉鎖位置ではチューブの前の切り欠きに掛けておく。写真では Z -362〜-388 にチューブの上へ出て見える。"""
    z = CH_Z
    out = [extrude_x_beveled([(z - 13.5, TUBE_Y - 3.0), (z + 12.5, TUBE_Y - 3.0), (z + 12.5, TUBE_Y + 11.0),
                              (z - 13.5, TUBE_Y + 11.0)], TUBE_R - 4.0, TUBE_R + 5.0, 1.0, STEEL_BLACK, steps=1)]
    a = CH_ANGLE                                   # レバーの傾き（つまみの上の縁が写真の箱の上の縁 214.4 を越えない）
    out += rotated([extrude_x([(z - 3.0, TUBE_Y), (z + 3.0, TUBE_Y), (z + 3.0, TUBE_Y + 18.0), (z - 3.0, TUBE_Y + 18.0)],
                              TUBE_R + 1.0, TUBE_R + 5.0, STEEL_BLACK)], "z", -a, (TUBE_R + 3.0, TUBE_Y, z))
    tip = (TUBE_R + 3.0 + 18.0 * math.sin(math.radians(a)), TUBE_Y + 18.0 * math.cos(math.radians(a)))
    out.append(lathe(tip[0], tip[1], [(z - 7.0, 5.0), (z + 7.0, 5.0)], ar15_mesh.N_SMALL, STEEL_BLACK))   # つまみ
    return out


def carry_handle():
    """運搬用ハンドル（ボーン carry_handle。針金の輪をチューブの金具に留め、左右どちらかの側面へ倒しておく。
    写真は左側面へ倒した状態）。輪の角は丸め、前の上の端をチューブの留め金に差す。"""
    z0, z1, y0, y1 = CARRY_LOOP
    rw, rc = 2.0, 7.0
    x = HALF_RECEIVER + rw + 0.3
    out = []
    path = []
    for zc, yc, a0 in ((z0 - rc, y1 - rc, 0), (z1 + rc, y1 - rc, 90), (z1 + rc, y0 + rc, 180), (z0 - rc, y0 + rc, 270)):
        for k in range(4):
            a = math.radians(a0 + 90 * k / 3)
            path.append((zc + rc * math.cos(a), yc + rc * math.sin(a)))
    from shapely.geometry import LineString
    ring = LineString(path + [path[0]]).buffer(rw, quad_segs=3)
    for poly in (ring,):
        outer = list(poly.exterior.coords)[:-1]
        holes = [list(h.coords)[:-1] for h in poly.interiors]
        from m249 import outline_parts
        out += outline_parts({"outer": outer, "holes": holes}, x - rw, x + rw, M.STEEL)   # 写真では明るい鋼の針金
    out.append(extrude_x_beveled([(z1 + 6.0, TUBE_Y - 4.0), (z1 - 6.0, TUBE_Y - 4.0), (z1 - 6.0, TUBE_Y + TUBE_R + 2.0),
                                  (z1 + 6.0, TUBE_Y + TUBE_R + 2.0)], -TUBE_R - 2.0, x + rw, 1.5, STEEL_BLACK, steps=1))
    return out


def rear_sight():
    """照門: 受け部の上面に留めた台と、その上の回転ドラム（MP5 と同じ形式。穴の大きさの違う照門と V 字の照門が周りに並ぶ）。
    ドラムは前後に抜けた穴（中心＝照準線）を持ち、軸は垂直にした（傾けると穴が斜めになり向こうが見えない。mp5.rear_sight）。"""
    # 台はドラムの前後に照準線のすぐ下まで立ち上がる（写真。照準線の穴の下の縁 221.9 より下で切って覗く邪魔をしない）
    base = _clip(O.REAR_SIGHT["outer"], 0.0, 0.0, 200.0, 221.0)
    out = [extrude_x_beveled(p, -11.0, 11.0, 2.5, STEEL_BLACK, steps=2) for p in base]
    out.append(x_cyl(92.0, 211.5, 2.2, -11.6, 11.6, M.STEEL, n=8))     # 台のねじ
    out += sights.drum_aperture(REAR_SIGHT_Z, DRUM_R, 213.0, SIGHT_Y, REAR_HOLE, SIGHT_Y + REAR_HOLE / 2 + 3.0,
                                STEEL_BLACK)
    return out


def front_sight():
    """照星: 銃身とコッキングチューブの先をまとめて抱く台（写真の輪郭）・その上のリングのフード・中のポスト（誇張）。"""
    o = O.FRONT_SIGHT["outer"]
    out = [extrude_x_beveled(p, -12.0, 12.0, 3.5, STEEL_BLACK, steps=2) for p in _clip(o, -510.0, 150.0, -475.0, 214.0)]
    zc, yc = FRONT_POST_Z, 227.0
    hl = 7.5                                                   # フードの前後の半分の長さ（写真 Z -476〜-491）
    out.append(lathe(0.0, yc, [(zc - hl, 13.5), (zc + hl, 13.5)], 16, STEEL_BLACK, cap0=False, cap1=False))
    out.append(lathe(0.0, yc, [(zc + hl, 10.0), (zc - hl, 10.0)], 16, STEEL_BLACK, cap0=False, cap1=False))
    for zz in (zc - hl, zc + hl):
        out.append(_annulus_z(0.0, yc, zz, 10.0, 13.5, STEEL_BLACK))
    out.append(extrude_x_beveled([(zc - hl, 212.0), (zc + hl, 212.0), (zc + hl, 217.5), (zc - hl, 217.5)],
                                 -9.0, 9.0, 1.0, STEEL_BLACK, steps=1))   # フードの根元（リングと台をつなぐ）
    out.append(sights.post(POST_W, 215.0, SIGHT_Y, zc, STEEL_BLACK))
    return out


def barrel():
    """銃身（ハンドガードの中は見えない）と銃口側（写真の太さの分布）。先端の消炎器は溝付きの筒（写真: 前の縁は閉じ、
    4 本の溝が貫通して中の暗い穴が見える。後ろに 2 本の帯）。"""
    prof = sorted(O.MUZZLE_R)
    fh_rear = -566.0                                           # 消炎器の後ろの端（写真の太さが変わる所）
    pipe = [(z, r) for z, r in prof if z > fh_rear]
    out = [lathe(0, BORE_Y, [(-500.0, 9.0), (BOLT_FACE_Z, 9.0)], ar15_mesh.N_MID, M.STEEL)]
    my = MUZZLE_Y                                              # 照星より前は写真の上下の中点（銃身の軸より 1.3mm 下に写る）
    out.append(lathe(0, my, [(fh_rear, pipe[0][1])] + pipe, ar15_mesh.N_MID, STEEL_BLACK))
    out += slotted_flash_hider(my, MUZZLE_Z, fh_rear, 10.2, 6.5, (-599.0, -577.0), (0, 90, 180, 270), 26.0,
                               STEEL_BLACK, ribs=((-571.5, -569.0, 0.6), (-575.5, -573.0, 0.6)))
    return out


HG_SLOTS_Z = (-222.0, -250.0, -278.0, -405.0, -432.0, -459.0)   # ハンドガードの楕円の凹み（写真。上下 2 列）
HG_SLOTS_Y = (186.0, 171.0)


def handguard():
    """ハンドガード（オリーブ色の樹脂。断面は丸く、後ろが太く前が細い）と、左右の 2 列の楕円の凹み（暗い色の板）。"""
    z0, z1 = _zr(O.HANDGUARD)

    def width(z, y, f):
        return 1.2 + 0.1 * (z - z0) / (z1 - z0)

    def radius(nz, ny):
        if abs(nz) > 0.6:
            return 2.0
        if ny > 0.6:
            return 8.0
        return 16.0 if ny < -0.4 else 6.0
    out = [inflate_x(densify(O.HANDGUARD["outer"]), HALF_HG, OD, steps=4, width_fn=width, radius_fn=radius,
                     cap_grid=14.0)]
    for zc in HG_SLOTS_Z:
        w = HALF_HG * width(zc, 0, 0)
        for yc in HG_SLOTS_Y:
            pts = [(zc + 7.0 * math.cos(math.radians(a)) + (5.0 if math.cos(math.radians(a)) > 0 else -5.0),
                    yc + 3.2 * math.sin(math.radians(a))) for a in range(0, 360, 30)]
            for s in (1, -1):
                xa, xb = sorted((s * (w - 0.1), s * (w + 0.15)))
                out.append(extrude_x(pts, xa, xb, M.G3_OD_DARK))
    return out


# ---------------------------------------------------------------- 下部
SELECTOR_PIVOT = (8.0, 132.0)
SELECTOR_MARKS = ((38.0, 151.0, M.MARK_WHITE), (42.0, 140.0, M.MARK_RED), (40.0, 125.0, M.MARK_RED))   # S・E・F（左側面）


def lower_housing():
    out = [extrude_x_beveled(O.LOWER_HOUSING["outer"], -HALF_HOUSING, HALF_HOUSING, 6.0, STEEL_BLACK, steps=3)]
    for z, y, mat in SELECTOR_MARKS:
        xa, xb = HALF_HOUSING - 0.1, HALF_HOUSING + 0.15
        out.append(box(xa, y - 3.0, z - 2.4, xb, y + 3.0, z + 2.4, mat))
    for z, y, r in ((-48.0, 112.0, 3.5), (75.0, 150.0, 3.5)):        # 押しピン（両側面）
        for s in (1, -1):
            xa, xb = sorted((s * (HALF_HOUSING - 0.5), s * (HALF_HOUSING + 1.0)))
            out.append(x_cyl(z, y, r, xa, xb, STEEL_BLACK, n=10))
    out.append(extrude_x_beveled(O.TRIGGER_GUARD["outer"], -HALF_GUARD, HALF_GUARD, 1.5, STEEL_BLACK, steps=1))
    return out


def selector():
    """セレクター（ボーン selector。左側面）: 丸い台と、表記を指すレバー。写真では S（安全）を指している。"""
    zc, yc = SELECTOR_PIVOT
    h = HALF_HOUSING
    mat = RCV_MAT                                  # ハウジング（黒い鋼）より明るい塗装・角の擦れで見分けられるように（写真の光り）
    out = [x_cyl(zc, yc, 6.0, h - 0.5, h + 1.5, mat, n=12)]
    out.append(extrude_x_beveled([(zc - 3.5, yc), (zc + 3.5, yc - 1.0), (zc + 25.0, yc + 15.0), (zc + 19.0, yc + 20.0)],
                                 h + 1.0, h + 3.2, 0.6, mat, steps=1))
    return out


GRIP_SPLIT_Y = 106.0     # グリップの握る所（下）と、ハウジングの下に入る付け根（上）の境目


def pistol_grip():
    """グリップ: 握る所は膨らませ（断面が丸い）、ハウジングの下の付け根は角を丸めた押し出し（付け根は前後 20mm と細く、
    膨らませると丸みの半径より薄くて潰れる）。"""
    def radius(nz, ny):
        return 1.0 if ny > 0.6 else (5.0 if ny < -0.7 else HALF_GRIP)
    out = []
    for p in _clip(O.GRIP["outer"], -400.0, -50.0, 400.0, GRIP_SPLIT_Y):
        out.append(inflate_x(densify(p, 6.0), HALF_GRIP, OD, steps=4, radius_fn=radius))
    for p in _clip(O.GRIP["outer"], -400.0, GRIP_SPLIT_Y - 3.0, 400.0, 200.0):
        out.append(extrude_x_beveled(p, -HALF_GRIP + 1.5, HALF_GRIP - 1.5, 4.0, OD, steps=2))
    return out


def trigger():
    return [extrude_x_beveled(O.TRIGGER["outer"], -3.5, 3.5, 0.8, STEEL_BLACK, steps=1)]


MAG_CATCH_PIN = (-70.0, 106.0)


def mag_release():
    """弾倉止めのレバー（ボーン mag_release。弾倉の後ろに垂れる爪。前へ押すと外れる）。"""
    return [extrude_x_beveled(O.MAG_RELEASE["outer"], -5.0, 5.0, 0.6, STEEL_BLACK, steps=1)]


# ---------------------------------------------------------------- ストック
def stock():
    """固定ストック（ボーン stock。オリーブ色の樹脂）と黒いゴムの床尾板、左側面のスリングの金具・2 つのねじ穴（写真）。"""
    out = [extrude_x_beveled(O.STOCK["outer"], -HALF_STOCK, HALF_STOCK, 10.0, OD, steps=4)]   # 縁は大きく丸い（HK の樹脂部品）
    out.append(extrude_x_beveled(O.BUTT["outer"], -HALF_BUTT, HALF_BUTT, 8.0, M.RUBBER, steps=3))
    h = HALF_STOCK
    for s in (1, -1):                                            # スリングの金具（上下の台と縦の棒）
        xa, xb = sorted((s * (h - 1.0), s * (h + 3.0)))
        for y in (119.0, 148.0):
            out.append(extrude_x_beveled([(296.0, y - 2.5), (331.0, y - 2.5), (331.0, y + 2.5), (296.0, y + 2.5)],
                                         xa, xb, 1.0, OD, steps=1))
        out.append(_y_rod(s * (h + 1.2), 313.0, 1.6, 120.0, 147.0))
        for z, y in ((372.0, 140.0), (370.0, 100.0)):           # ねじ穴（暗い丸）
            xa, xb = sorted((s * (h - 0.2), s * (h + 0.2)))
            out.append(x_cyl(z, y, 5.0, xa, xb, M.G3_OD_DARK, n=12))
    return out


def _y_rod(x, z, r, y0, y1):
    from m249 import y_cyl
    return y_cyl(x, z, r, y0, y1, STEEL_BLACK, n=8)


# ---------------------------------------------------------------- ボルト
def bolt():
    """ボルト（ボーン bolt）: 排莢口から見える平らな側面と、ボルトの頭（mp5.bolt と同じ作り）。"""
    rear = 95.0 - BOLT_TRAVEL_MAX
    zh = BOLT_FACE_Z + 26.0
    x_side = -PORT_INNER_X
    y_top = PORT_Y[1] + 2.0
    return [lathe(0, BORE_Y, [(BOLT_FACE_Z, 10.5), (zh, 10.5)], ar15_mesh.N_MID, BOLT_MAT),
            extrude_x_beveled([(zh, BORE_Y - 14.0), (rear, BORE_Y - 14.0), (rear, y_top), (zh, y_top)],
                              -14.0, 14.0, 1.0, BOLT_MAT, steps=1),
            extrude_x_beveled([(zh, PORT_Y[0] - 2.0), (rear, PORT_Y[0] - 2.0), (rear, y_top), (zh, y_top)],
                              x_side, -13.5, 0.8, BOLT_MAT, steps=1),
            extrude_x_beveled([(PORT_Z[0] + 1.0, BORE_Y + 14.0), (PORT_Z[0] + 15.0, BORE_Y + 14.5),
                               (PORT_Z[0] + 16.0, BORE_Y + 17.0), (PORT_Z[0] + 1.0, BORE_Y + 18.0)],
                              x_side - 0.6, x_side + 0.5, 0.3, BOLT_MAT, steps=1)]


# ---------------------------------------------------------------- 弾倉
MAG_TOP_Y = 158.0        # 弾倉の上端（弾倉の受けの中に隠れる）
MAG_SHELL = 12.0
MAG_WALL = 1.0
MAG_LIP = (5.0, 2.0, 30.0)
MAG_ROUND_X = 3.4
MAG_ROUND_DY = 10.5
MAG_RIB_ROWS = (92.0, 72.0, 52.0, 33.0, 15.0)    # 側面の押し出しの横リブ（写真）
MAG_RIB_Z = ((-89.0, -103.0), (-112.0, -116.0), (-127.0, -147.0))


def _mag_body():
    from shapely.geometry import Polygon, box as sbox
    from shapely.ops import unary_union
    g = Polygon(O.MAGAZINE["outer"])
    top = max(p[1] for p in O.MAGAZINE["outer"])
    zs = [p[0] for p in O.MAGAZINE["outer"] if p[1] >= top - 1.0]
    zf, zr = min(zs), max(zs)
    return unary_union([g, sbox(zf, top - 2.0, zr, MAG_TOP_Y)]), (zf, zr)


def magazine():
    """G3 の 20 発弾倉（鋼。まっすぐ）: 上部は中空で、2 枚のリップの間から一番上の弾が見える。側面に横リブ。"""
    from shapely.geometry import box as sbox
    body, (zf, zr) = _mag_body()
    solid = body.intersection(sbox(-400.0, -200.0, 0.0, MAG_TOP_Y - MAG_SHELL + 0.5))
    out = [extrude_x_beveled(list(solid.exterior.coords)[:-1], -HALF_MAG, HALF_MAG, 1.5, M.G3_MAG, steps=1)]
    y0, w, h = MAG_TOP_Y - MAG_SHELL, MAG_WALL, HALF_MAG
    for s in (1, -1):
        xa, xb = sorted((s * (h - w), s * h))
        out.append(box(xa, y0, zf, xb, MAG_TOP_Y, zr, M.G3_MAG))
    out += [box(-h, y0, zf, h, MAG_TOP_Y, zf + w, M.G3_MAG), box(-h, y0, zr - w, h, MAG_TOP_Y, zr, M.G3_MAG)]
    lx, lt, ll = MAG_LIP
    for s in (1, -1):
        xa, xb = sorted((s * lx, s * (h - w + 0.3)))
        out.append(extrude_x([(zr - ll, MAG_TOP_Y - lt), (zr - w + 0.3, MAG_TOP_Y - lt), (zr - w + 0.3, MAG_TOP_Y),
                              (zr - ll + 3.0, MAG_TOP_Y)], xa, xb, M.G3_MAG))
    out += [box(-h + w, y0, zf + w, h - w, y0 + 1.0, zr - w, M.FOLLOWER),
            box(-h + w, y0 + 1.0, zf + 5.0, -0.5, y0 + 3.0, zr - 4.0, M.FOLLOWER)]
    for y in MAG_RIB_ROWS:                                       # 横リブ（両側面に 0.8mm 出す）
        for za, zb in MAG_RIB_Z:
            for s in (1, -1):
                xa, xb = sorted((s * (h - 0.3), s * (h + 0.8)))
                out.append(extrude_x_beveled([(za, y - 1.3), (zb, y - 1.3), (zb, y + 1.3), (za, y + 1.3)], xa, xb,
                                             0.3, M.G3_MAG, steps=1))
    return out


def cartridge_762(z_tip, y, x=0.0):
    """7.62×51mm 実包（回転体）: 全長 71.1mm、薬莢 51.2mm。"""
    b = z_tip + 71.1
    case = [(b, 6.0), (b - 1.3, 6.0), (b - 1.6, 5.2), (b - 2.8, 5.2), (b - 3.2, 5.97), (b - 39.0, 5.7),
            (b - 43.0, 4.4), (b - 51.2, 4.35)]
    bullet = [(b - 51.2, 3.9), (b - 56.0, 3.9), (b - 63.0, 3.0), (b - 68.5, 1.6), (z_tip, 0.4)]
    return ([lathe(x, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(x, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


def magazine_rounds():
    _, (zf, zr) = _mag_body()
    z_tip = zr - MAG_WALL - 0.5 - 71.1
    out = []
    for x, y in ((MAG_ROUND_X, MAG_TOP_Y - 6.0), (-MAG_ROUND_X, MAG_TOP_Y - 6.0 - MAG_ROUND_DY)):
        case, bullet = cartridge_762(z_tip, y, x)
        out += case + bullet
    return out


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
    add("receiver", "root", (0, b, 0), "receiver", receiver() + magwell() + cocking_tube())
    add("selector", "receiver", (HALF_HOUSING, SELECTOR_PIVOT[1], SELECTOR_PIVOT[0]), "selector", selector())
    add("lower_receiver", "receiver", (0, 120.0, 0), "lower_housing", lower_housing())
    add("mag_release", "lower_receiver", (0, MAG_CATCH_PIN[1], MAG_CATCH_PIN[0]), "mag_release", mag_release())
    add("pistol_grip", "receiver", (0, 70.0, 80.0), "pistol_grip", pistol_grip())
    add("trigger", "root", (0, 100.0, 0), "trigger", trigger())
    add("stock", "root", (0, b, _zr(O.STOCK)[0]), "stock", stock())
    add("carry_handle", "receiver", (0, TUBE_Y, CARRY_LOOP[1]), "carry_handle", carry_handle())

    add("barrel", "root", (0, b, BOLT_FACE_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BOLT_FACE_Z), None, [])
    add("rear_sight", "receiver", (0, RCV_TOP, REAR_SIGHT_Z), "rear_sight", rear_sight())
    add("front_sight_base", "barrel", (0, b, FRONT_POST_Z), "front_sight", front_sight())
    add("front_sight_post", "front_sight_base", (0, SIGHT_Y, FRONT_POST_Z), None, [])
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])
    add("handguard", "root", (0, b, _zr(O.HANDGUARD)[1]), "handguard", handguard())
    add("rail_top", "root", (0, RCV_TOP, 0.0), None, [])
    add("rail_bottom", "root", (0, 157.0, -340.0), None, [])
    add("rail_side", "root", (HALF_HG * 1.25, 180.0, -340.0), None, [])

    add("bolt", "root", (0, b, BOLT_FACE_Z + 40.0), "bolt", bolt())
    add("charging_handle", "receiver", (TUBE_R, TUBE_Y, CH_Z), "charging_handle", charging_handle())

    _, (zf, zr) = _mag_body()
    add("magazin", "root", (0, 100.0, (zf + zr) / 2), "magazine", magazine())
    add("mag_ammo", "magazin", (0, MAG_TOP_Y - 6.0, (zf + zr) / 2), None, magazine_rounds())

    tip = BOLT_FACE_Z - 71.1
    case, bullet = cartridge_762(tip, b)
    add("ammo", "root", (0, b, tip + 50.0), None, case)
    add("bullet", "ammo", (0, b, tip + 10.0), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(O.GRIP["outer"]).centroid
    add_locators(m, muzzle=(0, MUZZLE_Y * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K,
                 rear_sight_z=REAR_SIGHT_Z * K, grip_center=(0, c.y * K, c.x * K), support_z=-330.0 * K)
    return m, parts
