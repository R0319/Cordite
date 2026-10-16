"""
MP5A3（伸縮ストック）のパーツと組み立て（単位 mm、メッシュ版）。

側面形はすべて作者提供の真横写真（右側面）からトレースした輪郭（mp5_outline.py ← trace_mp5.py）を使う。
縮尺は照準半径 340mm（HK 公表値）で合わせた。左右の幅は作者提供の図面の正面図・後面図（3.0mm/px）で測った値を
上限の目安にし、出っ張り（コッキングハンドル・スリング金具）を除いた本体の幅にした（下の HALF_*）。
細部は作者提供の写真による: 照星（リングのフード・中のポスト・左側面のドラム）、照門（ねじ留めの台・傾いた回転ドラム）。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝排莢口の側）、Y=0 グリップ底面、Z=0 トリガー、銃口 -Z。
"""
import math

import ar15_mesh
import materials as M
import sights
import mp5_outline as O
from ak47 import _clip, _yr, _zr
from core import MeshPart, box, extrude_x, extrude_x_beveled, inflate_x, lathe, densify
from m249 import outline_parts, rotated, x_cyl, y_cyl
from rig import add_locators
import ar15_parts

K = 1.0 / ar15_parts.MM_PER_PX
STEEL_BLACK = M.MP5_STEEL  # 小物の鋼（使い込まれた感のある材質。materials の MP5_*）
POLY = M.MP5_POLY
RCV_MAT = M.MP5_RECEIVER_W  # 受け部・チューブ（写真では樹脂部品とほとんど同じ黒っぽい色）

BORE_Y = 153.5          # 銃身の軸（写真の銃口の上下の中点）
SIGHT_Y = 205.0         # 照準線（照星のポストの先端＝フードのリングの中心の少し下）
MUZZLE_Z = -331.0
BOLT_FACE_Z = -106.0    # ボルトの前面＝薬室の後端（銃身 225mm を銃口から逆算）
REAR_SIGHT_Z = 53.0     # 照門ドラムの中心（照準半径 340mm の後ろの端）
FRONT_POST_Z = -285.0   # 照星のポスト（リングの中心）
FRONT_HOOD_HALF = 9.0   # リングのフードの前後の半分（写真の側面で 18mm。7mm の薄い輪にしていた）
FRONT_HOOD_BACK = 0.0   # フードの中心とポストの前後のずれ
# ADS の目は照門の 140mm 後ろ（作者指示: 照門のドラムに近すぎて手前の受け部が画面を覆っていた）。照門の穴と照星の
# ポストは見やすいように誇張し、この距離で大きさを決める（実物は穴 3.2mm・ポスト 2mm。sights の目安）
EYE_RELIEF = 140.0
_EYE = REAR_SIGHT_Z + EYE_RELIEF
REAR_HOLE = sights.HOLE_ANGLE * EYE_RELIEF
POST_W = sights.POST_ANGLE * (_EYE - FRONT_POST_Z)
DRUM_R = 10.5           # ドラムの半径（実物 9mm。誇張した穴の周りに肉を残すため太くした）

# 左右の半幅
HALF_RECEIVER = 17.0    # 受け部 34mm
HALF_HOUSING = 16.0     # トリガーハウジング（樹脂）32mm
HALF_GRIP = 15.0
HALF_GUARD = 7.0
HALF_MAG = 12.0         # 弾倉 24mm
HALF_HG = 20.0          # ハンドガード（前 40mm → 後ろ 46mm に width_fn で広げる）
HALF_BUTT = 13.0        # 床尾板 26mm（作者提供の三面図の後面図: 後端キャップの約 0.65 倍。48mm は板に、31mm でもまだ太く見えた）
ROD_X = 10.0            # ストックの棒の中心の左右位置（左右 2 本）
ROD_HALF = 3.5          # 棒の厚さ 7mm（作者の指摘「ストックが少し太い」）

# 右側面の排莢口（写真の暗い角の丸い長方形）と、その奥で動くボルト
PORT_Z = (-81.0, -42.0)
PORT_Y = (161.0, 181.0)
PORT_CORNER_R = 7.0     # 排莢口の角の丸み（高さ 20mm に対して。実物はほぼ両端が半円の長穴）
PORT_INNER_X = 15.0     # 排莢口から見えるボルトの側面（受け部の右側面から 2mm 奥。実物は板金のすぐ裏にボルトがあり、
                        # 閉鎖時は排莢口がボルトで埋まって見える。6mm 奥だと暗い穴に見えた＝作者の指摘）
BOLT_MAT = M.STEEL      # ボルト（受け部より明るい鋼。暗いと空洞と見分けがつかない）
BOLT_TRAVEL_MAX = 70.0  # ボルトの後退量の上限（🟡 実物の値は未確認。ボルトの後端が受け部の後端を越えない長さを決める）
CH_TUBE_Y = 181.8          # コッキングチューブの軸（上の縁 189.4。写真のトレースの上の縁 189〜190 に合わせる。183.6 では 2mm 高かった）
CH_SLOT_Z = (-206.0, -126.0)   # コッキングハンドルの溝（チューブの左側面。前の端が閉鎖位置）
STOCK_TRAVEL = 120.0    # ストックを縮めたときの前進量（HK 公表の全長 700→550mm の差は 150。写真の伸長位置からの量は 🟡 仮）


# ---------------------------------------------------------------- 受け部
def extrude_z(section, z0, z1, mat):
    """断面 section=[(x, y), ...]（単純多角形）を Z 方向 z0〜z1 に押し出す（extrude_x の向き違い）。
    面の向きの決まりは extrude_x と同じ（外積が内向き）。"""
    from core import MeshPart, _area2, _triangulate
    pts = list(section)
    if _area2(pts) < 0:
        pts.reverse()
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces, charts, cuv = [], [], []
    s_ = 0.0
    for i in range(n):
        j = (i + 1) % n
        seg = math.dist(pts[i], pts[j])
        faces.append([i, n + i, n + j, j])
        charts.append(0)
        cuv.append([(s_, 0), (s_, z1 - z0), (s_ + seg, z1 - z0), (s_ + seg, 0)])
        s_ += seg
    for tri in _triangulate(pts):
        faces.append(list(tri))
        charts.append(None)
        cuv.append(None)
        faces.append([n + tri[0], n + tri[2], n + tri[1]])
        charts.append(None)
        cuv.append(None)
    # 帯の端（z0・z1）は受け部を前後に分けたつなぎ目で、実物の角ではないので「角の擦れ」を描かない（"rows" にしない）
    return MeshPart(verts, faces, mat, None, charts, cuv, {0: "band"}).finalize()


RCV_BOTTOM = 130.0       # 受け部の断面の下端（トリガーハウジング・ハンドガードの中に隠れる）
RCV_TOP_R = 15.0         # 上の角の丸み（実物の断面は上がほぼ半円。作者の指摘「角張ったところは弾倉ぐらい」）
RCV_GROOVE = (142.5, 156.5, 1.8)   # 側面の長い溝（上下の範囲・深さ。写真の暗い帯 Y 140〜160）
RCV_GROOVE_Z = (-80.0, 77.0)       # 溝のある前後の範囲（写真）
# 後端キャップの上の部分（作者の指摘「ここの角が取れてない」）。受け部と同じ断面で後ろへ続き、上の角を斜めに落とす
# （写真: Z 114.5 から Z 126 で Y 171 まで下がる平らな面）。トレースの stock_latch は Y 175 で切っていたので漏れていた
CAP_CHAMFER = (116.5, 127.0, 171.0)   # 斜めの面の前の端 z、後ろの端 z、後ろの端の高さ y（自動採点の写真との比較で 2mm 後ろへ）


def _rcv_section(groove=True, port=False):
    """受け部の断面（X, Y）。上の角を RCV_TOP_R で丸め、側面に溝、port=True で右側面に排莢口の窓の切り欠き。"""
    h, top, r = HALF_RECEIVER, _yr(O.RECEIVER)[1], RCV_TOP_R
    g0, g1, gd = RCV_GROOVE
    yc = top - r

    def arc(cx, a0, a1, n=9):
        return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
                 yc + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]

    def side(sgn, upward):
        pts = [(sgn * h, RCV_BOTTOM), (sgn * h, g0 - 1.5)]
        if groove:
            pts += [(sgn * (h - gd), g0), (sgn * (h - gd), g1), (sgn * h, g1 + 1.5)]
        pts.append((sgn * h, yc))
        return pts if upward else pts[::-1]

    left = side(1, True) + arc(h - r, 0.0, 90.0)
    if not port:
        right = arc(-(h - r), 90.0, 180.0) + side(-1, False)
    else:
        py0, py1 = PORT_Y
        a_cut = math.degrees(math.asin((py1 - yc) / r))           # 排莢口の上の縁で丸みを切る角度
        right = arc(-(h - r), 90.0, 180.0 - a_cut, 7)
        right += [(0.0, py1), (0.0, py0), (-h, py0)]
        right += [p for p in side(-1, False) if p[1] < py0]
    pts = []
    for p in left + right:                          # 側面の端と丸みの端が同じ点になるので、重なりを除く
        if not pts or math.dist(pts[-1], p) > 1e-6:
            pts.append(p)
    if math.dist(pts[0], pts[-1]) <= 1e-6:
        pts.pop()
    return pts


def _loft_closed(sections, mat):
    """凸の断面 [(z, [(x, y)...])...]（点の数をそろえる）を前後につないだ閉じた筒。前後の蓋は重心からの扇。"""
    verts, faces, charts, cuv = [], [], [], []
    n = len(sections[0][1])
    for z, pts in sections:
        verts += [(x, y, z) for x, y in pts]
    p0 = sections[0][1]
    per = [0.0]
    for i in range(n):
        per.append(per[-1] + math.dist(p0[i], p0[(i + 1) % n]))
    for j in range(len(sections) - 1):
        za, zb = sections[j][0], sections[j + 1][0]
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            faces.append([a, b, b + n, a + n])
            charts.append(0)
            cuv.append([(per[i], za), (per[i + 1], za), (per[i + 1], zb), (per[i], zb)])
    for j, front in ((0, True), (len(sections) - 1, False)):
        z, pts = sections[j]
        c = len(verts)
        verts.append((sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, z))
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            faces.append([c, b, a] if front else [c, a, b])
            charts.append(None)
            cuv.append(None)
    return MeshPart(verts, faces, mat, None, charts, cuv, {0: "band"}).finalize()


def end_cap():
    """後端キャップの上の部分: 受け部の断面のまま後ろへ伸ばし、CAP_CHAMFER の斜めの面で上を切る。"""
    z0 = _zr(O.RECEIVER)[1]
    c0, c1, yb = CAP_CHAMFER
    top = _yr(O.RECEIVER)[1]
    sec = _rcv_section(groove=False)
    sections = [(z0, sec)]
    for k in range(13):
        yt = top - (top - yb) * k / 12
        sections.append((c0 + (c1 - c0) * k / 12, [(x, min(y, yt)) for x, y in sec]))
    return [_loft_closed(sections, RCV_MAT)]


def receiver():
    """受け部（板金の筒）。断面（上が丸く、側面に長い溝）を前後に押し出して作る。右側面の排莢口は、その区間だけ
    窓を切り欠いた断面にする（前後の区間の端面が窓の前後の壁になる）。奥は暗い面、間をボルトが動く。"""
    h = HALF_RECEIVER
    z_front, z_rear = _zr(O.RECEIVER)
    pz0, pz1 = PORT_Z
    gz0, gz1 = RCV_GROOVE_Z
    out = [extrude_z(_rcv_section(groove=False), z_front, pz0, RCV_MAT),
           extrude_z(_rcv_section(groove=True, port=True), pz0, pz1, RCV_MAT),
           extrude_z(_rcv_section(groove=True), pz1, gz1, RCV_MAT),
           extrude_z(_rcv_section(groove=False), gz1, z_rear, RCV_MAT)]
    out.append(box(-0.3, PORT_Y[0] - 0.3, pz0, 9.0, PORT_Y[1] + 0.3, pz1, M.BORE))   # 排莢口の奥（ボルトを引くと見える）
    # 排莢口の四隅を丸める（実物は両端の丸い長穴）。窓の切り欠きの角に、四角から 1/4 円を抜いた埋め物を置く
    r = PORT_CORNER_R
    for zc, yc, sz, sy in ((pz0 + r, PORT_Y[0] + r, -1, -1), (pz1 - r, PORT_Y[0] + r, 1, -1),
                           (pz0 + r, PORT_Y[1] - r, -1, 1), (pz1 - r, PORT_Y[1] - r, 1, 1)):
        pts = [(zc + sz * r, yc + sy * r)]
        pts += [(zc + sz * r * math.cos(math.radians(a)), yc + sy * r * math.sin(math.radians(a)))
                for a in range(0, 91, 15)]
        x_out = -h + 0.1 if sy < 0 else -h + 0.8          # 上の角は受け部の丸みの内側に収める
        out.append(extrude_x(pts, x_out, -PORT_INNER_X - 0.2, RCV_MAT))
    top = _yr(O.RECEIVER)[1]
    for z0, z1 in CLAW_BUMPS:
        # 前後の端が爪の掛かる高い縁、間が低い（写真。平らな箱では中が 2mm 高かった）
        out.append(extrude_x_beveled([(z0, top - 3.0), (z1, top - 3.0), (z1 - 0.5, top + 2.5), (z1 - 2.5, top + 2.5),
                                      (z1 - 3.5, top + 0.5), (z0 + 3.5, top + 0.5), (z0 + 2.5, top + 2.5),
                                      (z0 + 0.5, top + 2.5)], -5.0, 5.0, 0.6, RCV_MAT, steps=1))
    # 後端キャップ＋ストックの受けと止め金（丸みのある樹脂・金属。角を大きく丸める）
    out += outline_parts(O.STOCK_LATCH, -h + 1.0, h - 1.0, RCV_MAT, bevel=5.0, steps=3) + end_cap()
    return out


def cocking_tube():
    """コッキングチューブ（ハンドガードの上で受け部から照星まで）。左側面にハンドルの溝。"""
    zs = [p[0] for p in O.COCKING_TUBE["outer"]]
    z0, z1 = min(zs), max(zs)
    yc, r = CH_TUBE_Y, 7.6
    out = [lathe(0, yc, [(z0, r), (z1 + 4.0, r)], ar15_mesh.N_MID, RCV_MAT)]
    out.append(box(r - 1.5, yc - 1.8, CH_SLOT_Z[0], r + 0.2, yc + 1.8, CH_SLOT_Z[1], M.BORE))   # 溝（左）
    return out


def charging_handle():
    """コッキングハンドル（ボーン charging_handle。チューブの左側面から外へ斜め上に出るレバーと丸いつまみ）。
    非往復式: 引いてボルトを後ろへ掛けたら前へ戻す。写真ではつまみの頭がチューブの上に Z -206〜-195 で見える。"""
    yc = CH_TUBE_Y
    z = CH_SLOT_Z[0] + 2.5                 # つまみの中心（写真では Z -211〜-196 の 15mm。前は 10mm で 5mm 後ろだった）
    out = [extrude_x([(z - 3.0, yc - 1.5), (z + 3.0, yc - 1.5), (z + 3.0, yc + 1.5), (z - 3.0, yc + 1.5)], 5.0, 13.0,
                     STEEL_BLACK)]
    out += rotated([extrude_x([(z - 2.5, yc), (z + 2.5, yc), (z + 2.5, yc + 14.0), (z - 2.5, yc + 14.0)], 11.0, 14.0,
                              STEEL_BLACK)], "z", -35.0, (12.0, yc, z))
    out.append(lathe(20.0, yc + 10.0, [(z - 7.5, 3.5), (z - 6.0, 4.5), (z + 6.0, 4.5), (z + 7.5, 3.5)], ar15_mesh.N_SMALL,
                     POLY))   # つまみ
    return out


def rear_sight():
    """照門（作者提供の写真）: 受け部の上面にねじで留めた台と、その上の回転ドラム（ローレット刻み。
    穴の大きさの違う照門が周りに並ぶ）。ドラムは軸が後ろへ傾いている（写真の側面でも傾いた形）。"""
    base = _clip(O.REAR_SIGHT["outer"], 0.0, 0.0, 200.0, 200.0)
    out = [extrude_x_beveled(p, -9.0, 9.0, 2.5, STEEL_BLACK, steps=2) for p in base]
    out.append(x_cyl(66.0, 196.0, 2.2, -9.6, 9.6, M.STEEL, n=8))        # 台の十字ねじ（写真）
    # ドラムは前後に抜けた穴（中心＝照準線）を持つ。実物のドラムは軸が後ろへ傾いているが、傾けると穴が斜めになって
    # 覗いても向こうが見えないので、軸は垂直にした
    out += sights.drum_aperture(REAR_SIGHT_Z, DRUM_R, 196.0, SIGHT_Y, REAR_HOLE, SIGHT_Y + REAR_HOLE / 2 + 3.0,
                                STEEL_BLACK)
    return out


def front_sight():
    """照星（作者提供の写真）: 銃身を抱く台・塔・その上のリングのフード（銃身の向きに貫く輪）・中のポスト・
    左側面の丸いドラム（ポストの上下調整）。台・塔の側面形はトレース。"""
    o = O.FRONT_SIGHT["outer"]
    out = [extrude_x_beveled(p, -11.0, 11.0, 4.5, STEEL_BLACK, steps=2) for p in _clip(o, -400.0, 0.0, 0.0, 196.0)]
    zc, yc = FRONT_POST_Z, 208.0
    hl = FRONT_HOOD_HALF
    hz = FRONT_POST_Z + FRONT_HOOD_BACK
    k = (12.0 ** 2 - 9.2 ** 2) / hl ** 2                 # 外側は前後の端で半径 9.2 まで丸く細る（写真の側面で丸く見える）
    out.append(lathe(0.0, yc, [(hz + d, math.sqrt(12.0 ** 2 - k * d * d)) for d in (-hl, -hl * 0.66, -hl * 0.33, 0.0,
                                                                                   hl * 0.33, hl * 0.66, hl)],
                     16, STEEL_BLACK, cap0=False, cap1=False))
    out.append(lathe(0.0, yc, [(hz + hl, 8.6), (hz - hl, 8.6)], 16, STEEL_BLACK, cap0=False, cap1=False))     # 内側
    for zz in (hz - hl, hz + hl):                                     # リングの前後の面（輪）
        out.append(_annulus_z(0.0, yc, zz, 8.6, 9.2, STEEL_BLACK))
    out.append(box(-6.0, 195.0, hz - hl + 0.5, 6.0, 200.0, hz + hl - 0.5, STEEL_BLACK))   # フードの下の台（塔の上面とつなぐ）
    out.append(sights.post(POST_W, 194.0, SIGHT_Y, zc, STEEL_BLACK))                     # ポスト（誇張）
    out.append(x_cyl(zc + 2.0, 181.0, 8.0, 10.5, 14.0, STEEL_BLACK, n=16))               # ドラム（左側面）
    return out


def _annulus_z(cx, cy, z, r0, r1, mat, n=16):
    """Z に垂直な平らな輪（リングの前後の面）。"""
    from core import MeshPart
    verts, faces = [], []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        verts += [(cx + r0 * math.cos(a), cy + r0 * math.sin(a), z), (cx + r1 * math.cos(a), cy + r1 * math.sin(a), z)]
    for k in range(n):
        i, j = 2 * k, 2 * ((k + 1) % n)
        faces.append([i, j, j + 1, i + 1])
        faces.append([i, i + 1, j + 1, j])
    return MeshPart(verts, faces, mat, None, [None] * len(faces), [None] * len(faces), {}).finalize()


def barrel():
    """銃身（ハンドガードの中は見えない）と銃口側（写真の太さの分布。3 つの突起のある先端）。"""
    prof = sorted(O.MUZZLE_R)
    out = [lathe(0, BORE_Y, [(BOLT_FACE_Z - 0.5 - 225.0 + 30.0, 8.0), (BOLT_FACE_Z, 8.0)], ar15_mesh.N_MID, M.STEEL)]
    out.append(lathe(0, BORE_Y, [(prof[0][0], 4.5)] + prof + [(prof[-1][0], 4.5)], ar15_mesh.N_MID, STEEL_BLACK,
                     cap0=False, cap1=False))
    out.append(lathe(0, BORE_Y, [(MUZZLE_Z - 0.2, 4.5), (MUZZLE_Z + 20.0, 4.5)], ar15_mesh.N_SMALL, M.BORE, cap0=False))
    return out


def handguard():
    """ハンドガード（樹脂。後ろが太く前が細い。下面を大きく丸める）。上の面はチューブ・受け部に付くので丸めない。"""
    z0, z1 = _zr(O.HANDGUARD)

    def width(z, y, f):
        return 1.0 + 0.15 * (z - z0) / (z1 - z0)         # 前 40mm → 後ろ 46mm

    def radius(nz, ny):
        if abs(nz) > 0.6:
            return 1.5                     # 前後の端面（受け部・照星に付く）
        if ny > 0.6:
            return 7.0                     # 上の縁もチューブの両脇で丸める（写真）
        return 14.0 if ny < -0.4 else 6.0
    # cap_grid: 幅が場所ごとに変わる平らな面を格子で分ける（扇形の細長い三角形だと放射状の筋に見えた）
    return [inflate_x(densify(O.HANDGUARD["outer"]), HALF_HG, POLY, steps=4, width_fn=width, radius_fn=radius, cap_grid=14.0)]


# ---------------------------------------------------------------- 下部（樹脂のハウジング）
# トリガーハウジングの側面の成形の凹凸（作者提供の写真を 3 倍に拡大して読んだ。Z, Y）: セレクターの周りの後ろが丸い
# 盛り上がった板、その前上の三角、後ろの四角い台。どれも両側面に 0.8mm 盛り上げる
HOUSING_PANEL = ([(14.0 + 21.0 * math.cos(math.radians(a)), 117.0 + 21.0 * math.sin(math.radians(a)))
                  for a in range(-65, 66, 13)] + [(8.6, 135.9), (-45.8, 101.1)])
HOUSING_TRIANGLE = [(-6.4, 130.8), (-38.3, 130.8), (-38.3, 116.1)]
HOUSING_PAD = [(48.0, 112.5), (81.5, 112.5), (81.5, 135.5), (48.0, 135.5)]
PANEL_T = 0.8
CLAW_BUMPS = [(-36.6, -17.5)]     # 受け部の上のスコープの爪を掛ける突起（写真で照門の前に 1 つ見える。前後 z）


def lower_housing():
    from shapely.geometry import Polygon
    out = [extrude_x_beveled(O.LOWER_HOUSING["outer"], -HALF_HOUSING, HALF_HOUSING, 6.0, POLY, steps=3)]
    for poly, r in ((HOUSING_PANEL, 3.0), (HOUSING_TRIANGLE, 2.5), (HOUSING_PAD, 3.0)):
        g = Polygon(poly).buffer(-r).buffer(r, quad_segs=3)
        pts = list(g.exterior.coords)[:-1]
        for s_ in (1, -1):
            xa, xb = sorted((s_ * (HALF_HOUSING - 0.4), s_ * (HALF_HOUSING + PANEL_T)))
            out.append(extrude_x_beveled(pts, xa, xb, 0.4, POLY, steps=1))
    # 押しピン（写真の丸）: 後ろ 1 本・前（弾倉口の後ろ）2 本、両側面
    out += selector_marks()
    for z, y, r in ((92.8, 127.4, 4.0), (-58.0, 116.0, 3.5), (-58.0, 98.0, 3.0)):
        for s in (1, -1):
            xa, xb = sorted((s * (HALF_HOUSING - 0.5), s * (HALF_HOUSING + 1.0)))
            out.append(x_cyl(z, y, r, xa, xb, STEEL_BLACK, n=10))
    out += [extrude_x_beveled(p, -HALF_GUARD, HALF_GUARD, 2.5, POLY, steps=2)
            for p in [O.TRIGGER_GUARD["outer"]]]
    return out


SELECTOR_PIVOT = (13.8, 114.0)    # セレクターの軸（写真の S-E-F の文字の中心）


SELECTOR_MARKS = ((20.3, 123.2, M.MARK_WHITE), (22.3, 114.7, M.MARK_RED), (15.8, 106.3, M.MARK_RED))
# セレクターの表記（写真: 白い S、赤い E・F）。Z, Y と色。文字は 1 テクセル（約 3mm）より細かいので、文字の位置に色の印を置く


def selector_marks():
    """セレクターの表記の色の印（ハウジングの両側面に貼る薄い板）。MP5 の見た目の特徴（作者の指摘）。"""
    out = []
    for z, y, mat in SELECTOR_MARKS:
        for s in (1, -1):
            xa, xb = sorted((s * (HALF_HOUSING + PANEL_T - 0.1), s * (HALF_HOUSING + PANEL_T + 0.15)))   # 盛り上がった板の上
            out.append(box(xa, y - 2.6, z - 2.2, xb, y + 2.6, z + 2.2, mat))
    return out


def selector():
    """セレクター（ボーン selector。右側面）: 丸い台と、文字を指す細いレバー。写真では S（安全）を指している。"""
    zc, yc = SELECTOR_PIVOT
    h = HALF_HOUSING
    out = [x_cyl(zc, yc, 4.5, -h - 1.5, -h + 0.5, STEEL_BLACK, n=12)]
    out.append(extrude_x([(zc - 1.2, yc), (zc + 1.2, yc), (zc + 3.5, yc + 12.0), (zc + 1.0, yc + 12.5)],
                         -h - 2.5, -h - 1.0, STEEL_BLACK))
    return out


def pistol_grip():
    def radius(nz, ny):
        return 1.0 if ny > 0.6 else (5.0 if ny < -0.7 else HALF_GRIP)
    return [inflate_x(O.GRIP["outer"], HALF_GRIP, POLY, steps=4, radius_fn=radius)]


def trigger():
    return [extrude_x_beveled(O.TRIGGER["outer"], -3.2, 3.2, 0.8, STEEL_BLACK, steps=1)]


MAG_CATCH_PIN = (-55.0, 86.0)


def mag_release():
    """弾倉止めのレバー（ボーン mag_release。弾倉の後ろに垂れる爪。前へ押すと外れる）。"""
    return [extrude_x_beveled(O.MAG_RELEASE["outer"], -4.0, 4.0, 0.6, STEEL_BLACK, steps=1)]


# ---------------------------------------------------------------- ストック
def stock():
    """伸縮ストック（ボーン stock。前へ STOCK_TRAVEL 動かすと縮む）: 左右 2 本の棒と床尾板（後ろの面に刻み）。"""
    out = []
    for s in (1, -1):
        out += [extrude_x_beveled(p, s * ROD_X - ROD_HALF, s * ROD_X + ROD_HALF, 3.5, STEEL_BLACK, steps=2)
                for p in [O.STOCK_RODS["outer"]]]
    # 床尾板は前後に薄い（下のほうで 15mm 程度）ので膨らませずに角を丸めて押し出す
    out.append(extrude_x_beveled(O.STOCK_BUTT["outer"], -HALF_BUTT, HALF_BUTT, 8.0, POLY, steps=3))
    return out


# ---------------------------------------------------------------- ボルト
def bolt():
    """ボルト（ボーン bolt）: ボルトの頭と本体。排莢口からは本体の平らな側面とエキストラクターが見え、引くと
    ボルトの頭→奥（暗い面）が見える。
    後ろの端は BOLT_TRAVEL_MAX 下がっても受け部の後端キャップを越えない長さ。"""
    rear = 100.0 - BOLT_TRAVEL_MAX
    zh = BOLT_FACE_Z + 22.0
    x_side = -PORT_INNER_X                                  # 排莢口から見えるボルトの平らな側面
    y_top = PORT_Y[1] + 2.0
    return [lathe(0, BORE_Y, [(BOLT_FACE_Z, 8.5), (zh, 8.5)], ar15_mesh.N_MID, BOLT_MAT),
            # 本体: 平らな側面を持つ角柱（以前は丸棒で、上面だけが明るい棚に見えた）
            extrude_x_beveled([(zh, BORE_Y - 12.0), (rear, BORE_Y - 12.0), (rear, y_top), (zh, y_top)],
                              -11.0, 11.0, 1.0, BOLT_MAT, steps=1),
            # 右側面の張り出し: 排莢口の高さだけ受け部の表面の 2mm 奥まで出し、閉鎖時に排莢口を埋める。
            # 受け部の側面の溝（Y 156.5 まで）より上に限る（溝の底の面と重ならないように）
            extrude_x_beveled([(zh, PORT_Y[0] - 2.0), (rear, PORT_Y[0] - 2.0), (rear, y_top), (zh, y_top)],
                              x_side, -10.5, 0.8, BOLT_MAT, steps=1),
            # エキストラクター（ボルトの頭の側面の短い爪。閉鎖時は排莢口の前の端に見える）。以前は 24mm の細長い
            # 暗い板で、ボルトの側面に入ったひびのように見えた（作者の指摘「閉鎖時のこれなに？」）。ボルトと同じ鋼で、
            # 0.6mm 浮かせて縁の陰影だけで見せる
            extrude_x_beveled([(PORT_Z[0] + 1.0, BORE_Y + 12.0), (PORT_Z[0] + 13.0, BORE_Y + 12.5),
                               (PORT_Z[0] + 14.0, BORE_Y + 15.0), (PORT_Z[0] + 1.0, BORE_Y + 16.0)],
                              x_side - 0.6, x_side + 0.5, 0.3, BOLT_MAT, steps=1)]


# ---------------------------------------------------------------- 弾倉
MAG_TOP_Y = 134.0       # 弾倉の上端（差すと受け部の下＝弾倉口の中に隠れる）
MAG_SHELL = 10.0        # 上部の中空の深さ
MAG_WALL = 1.0
MAG_LIP = (4.2, 2.0, 22.0)
MAG_ROUND_X = 2.8
MAG_ROUND_DY = 8.4


def _mag_body():
    """トレースした弾倉（弾倉口の下に見える部分）に、弾倉口の中に隠れる上部（前後の縁をまっすぐ上へ）を足す。"""
    from shapely.geometry import Polygon, box as sbox
    from shapely.ops import unary_union
    g = Polygon(O.MAGAZINE["outer"])
    top = max(p[1] for p in O.MAGAZINE["outer"])
    zs = [p[0] for p in O.MAGAZINE["outer"] if p[1] >= top - 1.0]
    zf, zr = min(zs), max(zs)
    return unary_union([g, sbox(zf, top - 2.0, zr, MAG_TOP_Y)]), (zf, zr)


def magazine():
    """MP5 の 30 発弾倉（鋼）: 下へいくほど前へ反る。上部は中空で、2 枚のリップの間から一番上の弾が見える
    （外したときに装填済みに見える）。弾が空のときは送り板が見える。"""
    from shapely.geometry import box as sbox
    body, (zf, zr) = _mag_body()
    solid = body.intersection(sbox(-400.0, -200.0, 0.0, MAG_TOP_Y - MAG_SHELL + 0.5))
    out = [extrude_x_beveled(list(solid.exterior.coords)[:-1], -HALF_MAG, HALF_MAG, 1.2, M.MP5_MAG, steps=1)]
    y0, w, h = MAG_TOP_Y - MAG_SHELL, MAG_WALL, HALF_MAG
    for s in (1, -1):
        xa, xb = sorted((s * (h - w), s * h))
        out.append(box(xa, y0, zf, xb, MAG_TOP_Y, zr, M.MP5_MAG))
    out += [box(-h, y0, zf, h, MAG_TOP_Y, zf + w, M.MP5_MAG), box(-h, y0, zr - w, h, MAG_TOP_Y, zr, M.MP5_MAG)]
    lx, lt, ll = MAG_LIP
    for s in (1, -1):
        xa, xb = sorted((s * lx, s * (h - w + 0.3)))
        out.append(extrude_x([(zr - ll, MAG_TOP_Y - lt), (zr - w + 0.3, MAG_TOP_Y - lt), (zr - w + 0.3, MAG_TOP_Y),
                              (zr - ll + 3.0, MAG_TOP_Y)], xa, xb, M.MP5_MAG))
    out += [box(-h + w, y0, zf + w, h - w, y0 + 1.0, zr - w, M.FOLLOWER),
            box(-h + w, y0 + 1.0, zf + 5.0, -0.5, y0 + 3.0, zr - 4.0, M.FOLLOWER)]
    # 底板（一回り大きい）
    from shapely.geometry import LineString
    pts = O.MAGAZINE["outer"]
    bottom = min(pts, key=lambda p: p[1])
    plate = body.intersection(sbox(-400.0, -200.0, 0.0, bottom[1] + 6.0)).buffer(0.8, join_style=2)
    plate = max(getattr(plate, "geoms", [plate]), key=lambda q: q.area)
    out.append(extrude_x_beveled(list(plate.simplify(0.2).exterior.coords)[:-1], -h - 0.8, h + 0.8, 0.8, M.MP5_MAG,
                                 steps=1))
    return out


def magazine_rounds():
    """弾倉の中の弾（mag_ammo）: 上の 2 発を互い違いに。薬莢の底を後ろの壁に当てる。"""
    _, (zf, zr) = _mag_body()
    z_tip = zr - MAG_WALL - 0.5 - 29.7
    out = []
    for x, y in ((MAG_ROUND_X, MAG_TOP_Y - 4.95), (-MAG_ROUND_X, MAG_TOP_Y - 4.95 - MAG_ROUND_DY)):
        case, bullet = cartridge_9mm(z_tip, y, x)
        out += case + bullet
    return out


def cartridge_9mm(z_tip, y, x=0.0):
    """9×19mm 実包（回転体）: 全長 29.7mm、薬莢 19.15mm。"""
    b = z_tip + 29.7
    case = [(b, 4.95), (b - 1.2, 4.95), (b - 1.5, 4.4), (b - 2.4, 4.4), (b - 2.7, 4.95), (b - 19.15, 4.82)]
    bullet = [(b - 19.15, 4.5), (b - 23.0, 4.45), (b - 27.0, 3.3), (b - 29.2, 1.6), (z_tip, 0.4)]
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
    add("receiver", "root", (0, b, 0), "receiver", receiver() + cocking_tube())
    add("selector", "receiver", (-HALF_HOUSING, SELECTOR_PIVOT[1], SELECTOR_PIVOT[0]), "selector", selector())
    add("lower_receiver", "receiver", (0, 100.0, 0), "lower_housing", lower_housing())
    add("mag_release", "lower_receiver", (0, MAG_CATCH_PIN[1], MAG_CATCH_PIN[0]), "mag_release", mag_release())
    add("pistol_grip", "receiver", (0, 60.0, 60.0), "pistol_grip", pistol_grip())
    add("trigger", "root", (0, 88.0, 0), "trigger", trigger())
    add("stock", "root", (0, b, _zr(O.STOCK_RODS)[0]), "stock", stock())

    add("barrel", "root", (0, b, BOLT_FACE_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BOLT_FACE_Z), None, [])
    add("rear_sight", "receiver", (0, 191.0, REAR_SIGHT_Z), "rear_sight", rear_sight())
    add("front_sight_base", "barrel", (0, b, FRONT_POST_Z), "front_sight", front_sight())
    add("front_sight_post", "front_sight_base", (0, SIGHT_Y, FRONT_POST_Z), None, [])
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])
    add("handguard", "root", (0, b, _zr(O.HANDGUARD)[1]), "handguard", handguard())
    add("rail_top", "root", (0, 191.5, 0.0), None, [])
    add("rail_bottom", "root", (0, _yr(O.HANDGUARD)[0], -200.0), None, [])
    add("rail_side", "root", (HALF_HG, b, -200.0), None, [])

    add("bolt", "root", (0, b, BOLT_FACE_Z + 40.0), "bolt", bolt())
    add("charging_handle", "receiver", (8.0, CH_TUBE_Y, CH_SLOT_Z[0] + 6.0), "charging_handle", charging_handle())

    _, (zf, zr) = _mag_body()
    add("magazin", "root", (0, 90.0, (zf + zr) / 2), "magazine", magazine())
    add("mag_ammo", "magazin", (0, MAG_TOP_Y - 5.0, (zf + zr) / 2), None, magazine_rounds())

    tip = BOLT_FACE_Z - 29.7                                  # 薬室内の実包（排莢クリップの起点）
    case, bullet = cartridge_9mm(tip, b)
    add("ammo", "root", (0, b, tip + 20.0), None, case)
    add("bullet", "ammo", (0, b, tip + 5.0), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(O.GRIP["outer"]).centroid
    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K,
                 rear_sight_z=REAR_SIGHT_Z * K, grip_center=(0, c.y * K, c.x * K), support_z=-192.0 * K,
                 eye_relief=EYE_RELIEF * K)
    return m, parts
