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

import numpy as np

import ar15_mesh
import ar15_parts
import materials as M
import sights
import ak47_outline as O
from core import MeshPart, Model, box, extrude_x, extrude_x_beveled, inflate_x, lathe, densify
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
FRONT_SIGHT_Z = -488.0  # 照星（ポスト。図面の塔の耳の前後の中央）
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


def _clip(outer, z0, y0, z1, y1):
    """トレースした輪郭の一部（矩形 z0..z1 × y0..y1 との共通部分）を、多角形の頂点列のリストで返す。
    図面のトレースは接している部品が 1 つの影絵になっているので、部品ごとに切り分けるのに使う。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(outer).intersection(sbox(z0, y0, z1, y1))
    return [list(q.exterior.coords)[:-1] for q in getattr(g, "geoms", [g])
            if q.geom_type == "Polygon" and q.area > 0.5]


# ---------------------------------------------------------------- 受け部
# 右側面の開口（図面: 弾倉の真上の Z -60〜-125 に排莢口の枠、その後ろは受け部の上の縁 Y 141 とダストカバーの
# 下の縁の間の溝をコッキングハンドルが通る。安全位置のセレクターがこの溝を覆ってハンドルを止める）
BOLT_TRAVEL_MAX = 110.0          # ボルトキャリアの後退量の上限（🟡 実物の値は未確認。下の溝・排莢口はこの範囲で破綻しない）
PORT_Z = (-122.0, -62.0)         # 排莢口（前の端は照門ブロックの後ろ、後ろの端はハンドルの前）
PORT_Y = (127.0, 152.0)          # 下は軽量化の削り込みの上 3mm、上はダストカバーに食い込む
SLOT_Y = (141.0, 147.0)          # ハンドルの溝（受け部の上の縁〜ダストカバーの下の縁）
HANDLE_Z = (-66.0, -54.0)        # ハンドルの軸の前後（閉鎖位置。図面の四角）
SLOT_Z = (PORT_Z[1] - 1.0, HANDLE_Z[1] + BOLT_TRAVEL_MAX + 2.0)


def _right_cut(outline, cuts):
    """側面形から右側の開口（(z0, y0, z1, y1) の矩形）を除いた多角形の頂点列。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(outline)
    for c in cuts:
        g = g.difference(sbox(*c))
    g = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
    return list(g.exterior.coords)[:-1]


def _split_lr(outline, cuts, half, bevel, mat, steps):
    """左半分は側面形のまま、右半分は開口を抜いた形で押し出す。分けた面（X=0）は丸めない（継ぎ目に溝を出さない）。"""
    return [extrude_x_beveled(outline, 0.0, half, bevel, mat, steps=steps, round0=False),
            extrude_x_beveled(_right_cut(outline, cuts), -half, 0.0, bevel, mat, steps=steps, round1=False)]


def receiver():
    h = HALF_RECEIVER
    out = _split_lr(O.RECEIVER["outer"], [(PORT_Z[0], PORT_Y[0], PORT_Z[1], 300.0)], h, 1.5, M.RECEIVER, 1)
    # 開口の奥（右から覗くと見える受け部の中）: 暗い奥の壁と床。ボルトキャリアが前にいる間はキャリアの側面が見える
    out.append(box(-0.3, PORT_Y[0] - 0.3, PORT_Z[0], 9.0, SLOT_Y[1] + 0.5, SLOT_Z[1] + 2.0, M.BORE))
    out.append(box(-h + 1.2, PORT_Y[0], PORT_Z[0], -0.3, PORT_Y[0] + 0.3, PORT_Z[1], M.BORE))
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
    return out


SELECTOR_PIVOT = (21.0, 127.0)   # セレクターの軸（図面の後ろの大きな丸の中心。半径 約 9mm）


def selector():
    """セレクターレバー（右側面）。後ろの丸い軸から前へ長く伸びる板で、上（安全）では板がダストカバーの下の
    ボルトの通り道を塞ぐ。下げるほど 連発（АВ）→ 単発（ОД）。前端に指を掛ける外向きの爪。
    図面の線: 軸 Z≈+21・Y≈127、先端 Z≈-48（すぐ前がコッキングハンドル）。板は受け部の側面に密着させる（浮くと隙間に見える）。"""
    h = HALF_RECEIVER
    zc, yc = SELECTOR_PIVOT
    out = [x_cyl(zc, yc, 9.0, -h - 2.4, -h + 0.5, STEEL_BLACK, n=18),          # 軸のボス
           x_cyl(zc, yc, 2.8, -h - 3.2, -h - 2.0, M.STEEL, n=10)]              # 軸の頭
    # 板: 軸の側で幅 12mm → 先端 6mm に細る。上の縁はダストカバーの下の縁（Y 140）に沿う
    # 上の縁は安全位置でハンドルの溝（SLOT_Y）を覆う高さ（図面: 軸の上から前へ Y 147〜150 の線）
    top = SLOT_Y[1] + 0.8
    out.append(extrude_x_beveled([(zc, yc - 6.0), (zc - 20.0, yc - 3.0), (-46.0, 135.0), (-48.5, 137.0),
                                  (-47.0, top), (zc - 12.0, top), (zc, yc + 8.0)],
                                 -h - 2.0, -h + 0.5, 0.6, STEEL_BLACK, steps=1))
    # 前端の指掛け（外へ折り曲げた爪）
    out.append(extrude_x_beveled([(-49.0, 133.5), (-43.0, 134.5), (-43.5, top), (-48.5, top)],
                                 -h - 6.5, -h - 1.0, 0.8, STEEL_BLACK, steps=1))
    return out


# ダストカバー（作者の指摘「ダストカバーの形」。米国防総省の AK-47 type II の写真で、天面の丸み・側面の盛り上がった帯・
# 後ろのボタンを確かめた）
COVER_SPLIT_Y = 152.0            # 下の平らな側面と、上の丸い天面の境（右側面の排莢口の上の縁）
COVER_SHOULDER_R = 6.0           # 天面の左右の肩の丸み（作者提供の後ろ上・後ろ斜めの写真: 天面は広くゆるい弧で、左右の肩だけが丸い。
                                 # 以前は左右いっぱいの楕円の弧（高さ 11mm）で、後ろから見ると蒲鉾形の塊に見えた）
COVER_CROWN = 2.5                # 天面の中央の盛り上がり（肩の上の端から中央まで）
COVER_TAPER_Z = 52.0             # ここから後ろは天面が後ろ下がりに傾き、上から見て後ろへ細くなる（写真: 台形の傾いた面）
COVER_RAIL_REAR_Z = 54.0         # レール版のレールの後ろの端（天面が傾き始める COVER_TAPER_Z のすぐ後ろ。以前は 60 で、後ろ 6mm が
                                 # 傾いた天面から最大 3mm 浮いていた）
COVER_TAPER = 0.42               # 後ろの端での天面の細り（半幅に対する割合）
COVER_LOW_END_Z = 60.0           # 下の平らな側面（排莢口・ハンドルの溝の上の縁）はここまで。後ろは天面と一続きの傾いた面
COVER_REAR = [(52.0, 170.0), (58.5, 167.6), (67.8, 157.4), (71.5, 148.0), (73.0, 142.0)]   # 後ろの傾いた面の上の縁（z, y）
COVER_REAR_BOTTOM = 140.0        # 後ろの傾いた面の下の端（受け部の上面 Y 141 に 1mm 埋める）
COVER_BUTTON = (70.0, 77.0, 141.5, 148.5, 4.5)   # 後ろのボタン（リコイルスプリングのガイド。傾いた面の下の端から後ろへ突き出る。
                                                 # Z0, Z1, Y0, Y1, 半幅）


def _cover_section(half, top, taper, bottom=None):
    """ダストカバーの上の部分の断面（右半分を下から: 縦の側面 → 肩の丸み → ゆるい弧の天面 → 中央、を左右対称に）。
    taper は天面の細り（0〜1。後ろの傾いた所で側面を内側へ倒し、上から見て台形にする）。点の数は一定。"""
    h = top - COVER_SPLIT_Y
    r = max(0.4, min(COVER_SHOULDER_R, h * 0.5))
    crown = max(0.0, min(COVER_CROWN, h * 0.2))
    ht = half * (1.0 - taper)                       # 肩の外側の左右の位置（細った分だけ内側）
    ys = top - crown                                # 肩の上の端
    pts = [(half, COVER_SPLIT_Y if bottom is None else bottom), (half, COVER_SPLIT_Y)]
    n_sh, n_top = 5, 5
    for k in range(n_sh + 1):                       # 肩: 外側の縦の接線から上の水平の接線へ
        a = math.pi / 2 * k / n_sh
        pts.append((ht - r + r * math.cos(a), ys - r + r * math.sin(a)))
    xs = ht - r
    for k in range(1, n_top):                       # 天面: 肩から中央へゆるい弧（放物線）
        t = k / n_top
        x = xs * (1.0 - t)
        pts.append((x, ys + crown * (1.0 - (x / xs) ** 2) if xs > 0 else top))
    pts.append((0.0, top))
    return pts + [(-x, y) for x, y in reversed(pts[:-1])]


def _cover_dome(up, half):
    """ダストカバーの上の部分（COVER_SPLIT_Y より上）。up は側面形の上の部分（shapely）。前後の位置ごとに断面を並べてつなぐ。
    天面の高さは側面形の上の縁。COVER_TAPER_Z より後ろは、後ろの端へ向かって天面を細らせる（後ろの傾いた面が台形になる）。"""
    from shapely.geometry import LineString
    z0 = up.bounds[0]
    z1 = COVER_REAR[-1][0]
    rz, ry = [p[0] for p in COVER_REAR], [p[1] for p in COVER_REAR]
    zs = sorted(set(list(np.linspace(z0, COVER_TAPER_Z, 24)) + list(np.linspace(COVER_TAPER_Z, z1, 14))
                    + [COVER_LOW_END_Z - 0.01, COVER_LOW_END_Z]))
    sections = []
    for z in zs:
        if z >= COVER_TAPER_Z:
            top = float(np.interp(z, rz, ry))
        else:
            zz = min(max(z, z0 + 1e-3), COVER_TAPER_Z)
            hit = up.intersection(LineString([(zz, COVER_SPLIT_Y - 1), (zz, 400)]))
            top = hit.bounds[3] if not hit.is_empty else COVER_SPLIT_Y + 1
        t = max(0.0, (z - COVER_TAPER_Z) / (z1 - COVER_TAPER_Z))
        bottom = COVER_REAR_BOTTOM if z >= COVER_LOW_END_Z else None
        top = max(top, (COVER_SPLIT_Y if bottom is None else bottom) + 0.8)
        sections.append((z, _cover_section(half, top, COVER_TAPER * t, bottom)))
    return _loft(sections, M.RECEIVER)


def _loft(sections, mat):
    """断面 [(z, [(x, y)...])...]（点の数をそろえる。各断面は凸）を前後につないだ筒と、前後の蓋。側面は 1 枚の区画。"""
    verts, faces, charts, cuv = [], [], [], []
    n = len(sections[0][1])
    for z, pts in sections:
        verts += [(x, y, z) for x, y in pts]
    per = [0.0]
    p0 = sections[0][1]
    for i in range(n - 1):
        per.append(per[-1] + math.dist(p0[i], p0[i + 1]))
    for j in range(len(sections) - 1):
        za, zb = sections[j][0], sections[j + 1][0]
        for i in range(n - 1):
            a, b = j * n + i, j * n + i + 1
            faces.append([a, b, b + n, a + n])
            charts.append(0)
            cuv.append([(per[i], za), (per[i + 1], za), (per[i + 1], zb), (per[i], zb)])
    for j, flip in ((0, False), (len(sections) - 1, True)):
        ring = [j * n + i for i in range(n)]
        for k in range(1, n - 1):
            f = [ring[0], ring[k], ring[k + 1]]
            faces.append(f[::-1] if flip else f)
            charts.append(None)
            cuv.append(None)
    return MeshPart(verts, faces, mat, None, charts, cuv, {0: "band"}).finalize()


def dust_cover(rail=False):
    """ダストカバー（板金の蓋）。作者提供の写真（後ろ上・後ろ斜め上）: 側面は平らで帯は無く、天面は広くゆるい弧で肩だけが
    丸い。後ろの端は天面から下の縁まで一続きの傾いた面で、上から見て後ろへ細る台形。その下の端の中央から
    リコイルスプリングのガイドのボタンが突き出る。
    下の平らな側面は受け部の中へ 8mm 差し込み、少しだけ外へ張り出させる（実物のカバーは受け部の外側に被さって面一）。
    右側面は排莢口とハンドルの溝の上の縁になるので、そこだけ下の縁を上げる（左右を X=0 で分けて作る）。
    rail=True で上面にレール。"""
    from shapely.geometry import Polygon, box as sbox
    o = O.DUST_COVER
    y_bottom = _yr(o)[0]
    half = HALF_RECEIVER + 0.4
    # 側面形: 後ろの端の膨らみ（ボタン）は別の部品にするので、後ろの面を Z 77 の縦にする
    outer = [(min(z, 77.0), y - 8.0 if y <= y_bottom + 0.5 else y) for z, y in o["outer"]]
    g = Polygon(outer).buffer(0)
    low = g.intersection(sbox(-1e3, -1e3, COVER_LOW_END_Z, COVER_SPLIT_Y))
    up = g.intersection(sbox(-1e3, COVER_SPLIT_Y, 1e3, 1e3))
    ring = lambda q: list(q.exterior.coords)[:-1]
    low_pts = ring(low.simplify(0.05))
    cuts = [(PORT_Z[0], 0.0, PORT_Z[1], PORT_Y[1]), (SLOT_Z[0], 0.0, SLOT_Z[1], SLOT_Y[1])]
    out = [extrude_x(low_pts, 0.0, half, M.RECEIVER), extrude_x(_right_cut(low_pts, cuts), -half, 0.0, M.RECEIVER)]
    # 天面: 縦の側面＋丸い肩＋ゆるい弧の断面を前後に並べ、後ろの傾いた所では細らせる（_cover_dome）
    out.append(_cover_dome(up, half))
    # 後ろのボタン
    bz0, bz1, by0, by1, bh = COVER_BUTTON
    out.append(extrude_x_beveled([(bz0, by0), (bz1 - 1.0, by0), (bz1, by0 + 1.5), (bz1, by1 - 1.5), (bz1 - 1.0, by1),
                                  (bz0, by1)], -bh, bh, 1.5, STEEL_BLACK, steps=2))
    z0, z1 = _zr(o)
    yt = _yr(o)[1]
    if rail:
        slots = 16
        r1 = COVER_RAIL_REAR_Z
        r0 = r1 - slots * SLOT_MM
        out += [box(-8, yt - 1, r0, 8, yt + 3, r1, M.RAIL), box(-RAIL_W / 2, yt + 3, r0, RAIL_W / 2, yt + 8, r1, M.RAIL)]
    return out


def front_trunnion():
    return outline_parts(O.FRONT_TRUNNION, -HALF_TRUNNION, HALF_TRUNNION, STEEL_BLACK, bevel=2.0)


REAR_LEAF_HINGE = (-203.0, 175.5)      # 照尺の前の蝶番（図面の照門ブロックの前上の角）
REAR_SLIDER_Z = (-194.0, -181.0)       # スライダー（図面の照尺の上の前寄りの膨らみ。「П」の位置）
REAR_NOTCH_Z = (-140.0, -133.0)        # 照尺の後端の照門（図面の後ろの膨らみ。後端 -133）
# 照門の切り欠きと照星のポストは見やすいように誇張する（実物は切り欠き 2.6mm・ポスト 2.2mm。sights の目安で
# ADS の目からの距離で決める。トリガーは Z=0）
_EYE = sights.eye_z(0.0, REAR_SIGHT_Z)
NOTCH_HALF = sights.NOTCH_ANGLE * (_EYE - REAR_SIGHT_Z) / 2
POST_HALF = sights.POST_ANGLE * (_EYE - FRONT_SIGHT_Z) / 2


def rear_sight():
    """照門ブロック＋照尺（作者提供の写真: ブロックの前の蝶番ピンで照尺が起き、照尺の上をスライダーが前後する。
    スライダーは左右のボタンをつまんで動かす。照尺の後端に照門の切り欠き）。
    高さ・前後の位置は図面のトレース（REAR_SIGHT）、ブロックの上面 Y 173 から上を照尺とスライダーに分けた。
    照尺の目盛り（1〜8・П）は 1 テクセル（約 3mm）より細かいので形にしない。"""
    out = [extrude_x_beveled(p, -11.0, 11.0, 1.2, STEEL_BLACK, steps=1)
           for p in _clip(O.REAR_SIGHT["outer"], -300.0, 0.0, -100.0, 173.5)]
    zh, yh = REAR_LEAF_HINGE
    nz0, nz1 = REAR_NOTCH_Z
    # 照尺（厚さ 6mm の板。ブロックの上面に 1mm 食い込ませて隙間を作らない）
    out.append(extrude_x_beveled([(zh - 1.0, 172.5), (nz0, 172.5), (nz0, 178.0), (zh - 1.0, 179.5)],
                                 -7.0, 7.0, 0.8, STEEL_BLACK, steps=1))
    out.append(x_cyl(zh, yh, 3.2, -11.6, 11.6, M.STEEL, n=12))                  # 蝶番のピン
    # 後端の照門: 左右 2 本の爪の間の切り欠きの底が照準線（SIGHT_Y）
    out.append(extrude_x_beveled([(nz0, 172.5), (nz1, 172.5), (nz1, SIGHT_Y), (nz0, SIGHT_Y)],
                                 -(NOTCH_HALF + 5.7), NOTCH_HALF + 5.7, 0.5, STEEL_BLACK, steps=1))
    for s in (1, -1):
        x0, x1 = sorted((s * NOTCH_HALF, s * (NOTCH_HALF + 5.7)))
        out.append(extrude_x_beveled([(nz0, SIGHT_Y - 0.5), (nz1, SIGHT_Y - 0.5), (nz1, 184.0), (nz0 + 1.5, 184.0)],
                                     x0, x1, 0.5, STEEL_BLACK, steps=1))
    # スライダー（照尺を抱く箱）と左右のボタン
    sz0, sz1 = REAR_SLIDER_Z
    out.append(extrude_x_beveled([(sz0, 171.0), (sz1, 171.0), (sz1 + 1.5, 184.0), (sz0, 184.0)],
                                 -9.0, 9.0, 1.0, STEEL_BLACK, steps=1))
    for s in (1, -1):
        x0, x1 = sorted((s * 8.5, s * 11.2))
        out.append(x_cyl((sz0 + sz1) / 2, 178.0, 2.7, x0, x1, M.STEEL, n=12))
    return out


# 図面のトレース TRIGGER_GUARD は、トリガーガード・その中のトリガー・前のマガジンキャッチが 1 つの影絵になっている。
# 矩形で切り分けて、それぞれの厚みで作る
TRIGGER_BOX = (-16.0, 75.5, 5.5, 101.0)       # ガードの中のトリガー（ガードの下の帯 Y≦74・後ろの柱 Z≧6 は含まない）
MAG_CATCH_BOX = (-53.0, 50.0, -44.5, 101.0)   # ガードの前に垂れるマガジンキャッチ（弾倉の後ろの縁に 0.5mm 掛かる）
MAG_CATCH_PIN = (-41.0, 95.0)                 # マガジンキャッチの軸（ガードの前の付け根）
GUARD_REAR_FILL = (14.0, 74.5, 17.5, 100.0)    # ガードの後ろの脚とグリップの間を埋める範囲（Z0, Y0, Z1, Y1）


def trigger_guard():
    """トリガーガード（プレス鋼板）。図面の輪郭からトリガーとマガジンキャッチを除いた残り。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(O.TRIGGER_GUARD["outer"]).difference(sbox(*TRIGGER_BOX)).difference(sbox(*MAG_CATCH_BOX))
    # 後ろの脚をグリップの前の縁（Z 17）まで広げる。図面のトレースでは 2mm 空いて背景が抜けていたが、実物の写真
    # （米国防総省 AK-47 type II）ではガードの後ろの端はグリップに直接つながり、隙間は無い
    g = g.union(sbox(*GUARD_REAR_FILL))
    out = [extrude_x_beveled(list(q.exterior.coords)[:-1], -5.5, 5.5, 1.0, STEEL_BLACK, steps=1)
           for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 0.5]
    out.append(x_cyl(*MAG_CATCH_PIN, 1.8, -6.4, 6.4, M.STEEL, n=8))              # マガジンキャッチの軸のピン
    return out


def trigger():
    """トリガー（図面: ガードの中の、前へ反って下端が前へ出る板。幅 6.5mm）。"""
    return [extrude_x_beveled(p, -3.2, 3.2, 0.8, STEEL_BLACK, steps=1) for p in _clip(O.TRIGGER_GUARD["outer"], *TRIGGER_BOX)]


def mag_release():
    """マガジンキャッチ（弾倉の後ろに垂れるパドル。前へ押すと弾倉の後ろの突起が外れる）。幅 13mm の板。"""
    return [extrude_x_beveled(p, -6.5, 6.5, 1.0, STEEL_BLACK, steps=1) for p in _clip(O.TRIGGER_GUARD["outer"], *MAG_CATCH_BOX)]


def pistol_grip():
    def radius(nz, ny):
        if ny > 0.6:
            return 1.0          # 上端（受け部の下面に付く面）は丸めない。丸めると付け根が細って溝になる
        return 5.0 if ny < -0.7 else HALF_GRIP
    return [inflate_x(O.GRIP["outer"], HALF_GRIP, WOOD, steps=4, radius_fn=radius)]


def stock():
    z0, z1 = _zr(O.STOCK)

    def width(z, y, f):
        return 1.0 + 0.23 * (z - z0) / (z1 - z0)        # 付け根 30mm → 床尾 37mm

    def radius(nz, ny):
        return 1.0 if nz < -0.6 else 9.0     # 前の端面（受け部の後端に付く面）は丸めない
    # cap_grid: 幅が場所ごとに変わる平らな面を格子で分ける（扇形の細長い三角形だと放射状の筋に見えた）
    out = [inflate_x(densify(O.STOCK["outer"]), HALF_STOCK, WOOD, steps=4, width_fn=width, radius_fn=radius, cap_grid=14.0)]
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


# ガスチューブ（実物の写真で確認: 米国防総省「AK-47 type II Part DM-ST-89-01131.jpg」、2.55px/mm）。
# 図面のトレース GAS は銃身の上に載った 1 枚の板だったが、実物はガスブロックより後ろで銃身から離れた丸い管で、
# 管と銃身の間に背景が抜ける。管の後ろの端には上ハンドガードの前端を包む金具（カップ）、その前に細長い穴が 4 つ
GAS_BLOCK_REAR_Z = -384.0                  # ガスブロック（図面の斜めの部分）の後ろの端。これより後ろは管
GAS_TUBE_Y, GAS_TUBE_R = 157.6, 9.4        # 管の中心の高さ・半径（写真: 太さ 18.8mm、銃身との隙間 6.7mm）
GAS_COLLAR_Z = (-412.0, -388.0)            # ガスブロックの銃身を抱く輪の前後（図面のブロックの前端〜斜めの部分の下）
GAS_COLLAR_R = 12.4                        # 輪の半径（下端がクリーニングロッドに当たる太さ。写真ではブロックとロッドの間に隙間が無い）
GAS_TUBE_REAR_Z = -296.0                   # 管の後ろの端（上ハンドガードの中に隠れる）
# ハンドガードの前端（写真を 5 倍に拡大して読んだ。上の木の前端 Z -312 を基準に、写真の中の前後関係で置く）
UPPER_CAP_Z = (-318.3, -311.0)             # 上の木の前端を包む金具（枠）。後ろの 1mm は木に被さる
UPPER_CAP_Y = (144.6, 173.0)               # 枠の上下（上は写真: 木より少し低い所まで。下は下ハンドガードの上の縁 145 に食い込ませる）
UPPER_CAP_HALF, UPPER_CAP_R = 15.6, 7.0    # 枠の半幅・角の丸み
GAS_SLEEVE = (-331.6, -318.0, 10.0)        # ガス管の後ろの少し太い部分（Z の前・後ろ、半径）
LOWER_HG_FRONT_Z = -313.6                  # 下ハンドガードの木の前端（写真: 上の木の前端より 1.6mm 後ろ）
LOWER_HG_STEP_Z = -297.0                   # 下ハンドガードの上の縁の段（写真）。ここより後ろは上ハンドガードとの隙間が広い
LOWER_HG_TOP = (143.0, 141.0)              # 上の縁の高さ（段の前・後ろ。写真の隙間 約 2mm・4mm）。上ハンドガードの下の面は 145
LOWER_RIM_Z = (-316.7, -313.0)             # 下の金具の後ろの縁（木の前端の板。高さは木と同じ）
LOWER_RIM_Y = (113.5, 146.3)
LOWER_BODY_Z = (-333.9, -316.0)            # 下の金具の本体（銃身を抱く。写真では銃身の中心より上に寄り、下端 123.2・上端 146.5）
LOWER_BODY_Y = (123.2, 148.4)              # 上はガス管の太い部分の下（147.6）まで（写真ではここに隙間が無い）
LOWER_BODY_HALF = 12.5                     # 本体の半幅（🟡 写真は真横だけなので推定）
LOWER_PIN = (-326.1, 141.4, 1.4)           # 輪の左の側面の丸いピンの頭（Z, Y, 半径）
ROD_HANGER = (-320.5, -314.4, 113.5)       # 縁から下へ伸びてクリーニングロッドを抱く部分（Z の前・後ろ、下端。前は写真で白く抜け始める所）
CLEANING_ROD_Y, CLEANING_ROD_R = 118.9, 1.8   # 写真: 太さ 3.6mm、銃身の下の面との隙間 3.9mm
GAS_VENTS = [-358.0, -350.0, -342.0, -334.5]   # 側面の細長い穴の中心 Z（写真。長さ 5.5mm・幅 2.2mm。太い部分の前）


def gas():
    """ガスブロック（図面の側面形の前の部分。断面は丸める）・その下の突起と、後ろへ延びる丸いガスチューブ・
    上ハンドガードの前端を包む金具・チューブ側面の穴。"""
    from shapely.geometry import Polygon, box as sbox
    blk = Polygon(O.GAS["outer"]).intersection(sbox(-500.0, 0.0, GAS_BLOCK_REAR_Z, 300.0))
    out = [extrude_x_beveled(list(blk.exterior.coords)[:-1], -HALF_GAS, HALF_GAS, 6.0, STEEL_BLACK, steps=3),   # 丸め 6mm（短く切ったので 9mm だと潰れる）
           *outline_parts(O.GAS_LUG, -7.0, 7.0, STEEL_BLACK, bevel=2.0)]
    # ガスブロックの下の輪（銃身を抱く。銃身の穴 → ブロック → 管とガスが通るので、横から見て銃身と管の間がつながる）
    c0, c1 = GAS_COLLAR_Z
    out.append(lathe(0, BORE_Y, [(c0, GAS_COLLAR_R), (c1, GAS_COLLAR_R)], ar15_mesh.N_MID, STEEL_BLACK))
    y, r = GAS_TUBE_Y, GAS_TUBE_R
    out.append(lathe(0, y, [(GAS_BLOCK_REAR_Z - 3.0, r), (GAS_TUBE_REAR_Z, r)], ar15_mesh.N_MID, STEEL_BLACK))
    z0, z1, rs = GAS_SLEEVE
    out.append(lathe(0, y, [(z0, r), (z0 + 1.0, rs), (z1, rs)], ar15_mesh.N_MID, STEEL_BLACK))
    out.append(upper_cap())
    for z in GAS_VENTS:                    # 穴（暗い長円の板を左右の面に。管の中心より 4.5mm 上。写真）
        ts = [math.pi * (k / 6 - 0.5) for k in range(7)]          # -90°〜90°
        hole = ([(z + 1.65 + 1.1 * math.cos(t), y + 4.5 + 1.1 * math.sin(t)) for t in ts] +     # 前後の半円
                [(z - 1.65 - 1.1 * math.cos(t), y + 4.5 - 1.1 * math.sin(t)) for t in ts])
        xs = math.sqrt(r * r - 4.5 * 4.5)
        for sg in (1, -1):
            xa, xb = sorted((sg * (xs - 0.6), sg * (xs + 0.15)))
            out.append(extrude_x(hole, xa, xb, M.BORE))
    return out


def cleaning_rod():
    return [lathe(0, CLEANING_ROD_Y, [(-505.0, CLEANING_ROD_R), (LOWER_RIM_Z[1], CLEANING_ROD_R)], 6, M.STEEL)]


def _rounded_rect(x0, y0, x1, y1, r_top, r_bot, n=4):
    """角を丸めた長方形の断面（X, Y）。上の角と下の角で丸みを変えられる。"""
    pts = []
    for cx, cy, rr, a0 in ((x1 - r_bot, y0 + r_bot, r_bot, -90), (x1 - r_top, y1 - r_top, r_top, 0),
                           (x0 + r_top, y1 - r_top, r_top, 90), (x0 + r_bot, y0 + r_bot, r_bot, 180)):
        for k in range(n + 1):
            t = math.radians(a0 + 90 * k / n)
            pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return pts


def upper_cap():
    """上ハンドガードの木の前端を包む金具（ガス管の後ろの端の枠。断面は木に沿った角の丸い四角）。"""
    from mp5 import extrude_z
    y0, y1 = UPPER_CAP_Y
    sec = _rounded_rect(-UPPER_CAP_HALF, y0, UPPER_CAP_HALF, y1, UPPER_CAP_R, 3.0)
    return extrude_z(sec, *UPPER_CAP_Z, STEEL_BLACK)


def lower_front_retainer():
    """下ハンドガードの前の留め金（写真）: 木の前端に当たる縁の板、銃身を抱く輪（左の側面に丸いピンの頭）、
    縁から下へ伸びてクリーニングロッドを抱く部分。"""
    from mp5 import extrude_z
    hw = HALF_LOWER_HG * 1.45 + 0.8
    y0, y1 = LOWER_RIM_Y
    out = [extrude_z(_rounded_rect(-hw, y0, hw, y1, 3.0, 10.0), *LOWER_RIM_Z, STEEL_BLACK)]
    by0, by1 = LOWER_BODY_Y
    bh = LOWER_BODY_HALF
    out.append(extrude_z(_rounded_rect(-bh, by0, bh, by1, 4.0, 9.0), *LOWER_BODY_Z, STEEL_BLACK))
    hz0, hz1, hy = ROD_HANGER
    out.append(box(-4.5, hy, hz0, 4.5, by0 + 2.0, hz1, STEEL_BLACK))
    pz, py, pr = LOWER_PIN
    out.append(x_cyl(pz, py, pr, bh - 0.8, bh + 0.8, M.STEEL, n=10))
    return out


FRONT_EARS_Y = 166.0                  # 照星の塔の上の左右の耳（ポストを守る）の下端
FRONT_DRUM = (FRONT_SIGHT_Z, 163.0, 5.0)   # ポストのドラム（Z, Y, 半径。側面に丸く見える）
FRONT_WINDOW = [(-494.0, 147.5), (-481.0, 147.5), (-481.0, 155.5), (-494.0, 155.5)]   # 塔の窓（横に抜ける）


def front_sight():
    """照星（作者提供の写真）: 銃身を抱く筒の台・その下の突起（清掃棒が通る）・窓の抜けた三角の塔・
    上の左右の耳・その間のポスト・塔を貫く丸いドラム（ポストの上下調整）。輪郭は図面のトレース。"""
    o = O.FRONT_SIGHT["outer"]
    out = []
    lower = _clip(o, -600.0, 0.0, -400.0, FRONT_EARS_Y)
    out += outline_parts({"outer": lower[0], "holes": [FRONT_WINDOW]}, -6.0, 6.0, STEEL_BLACK)
    for ear in _clip(o, -600.0, FRONT_EARS_Y - 0.5, -400.0, 300.0):
        for s in (1, -1):
            x0, x1 = sorted((s * (POST_HALF + 1.2), s * (POST_HALF + 4.2)))   # ポストとの間 1.2mm
            out.append(extrude_x_beveled(ear, x0, x1, 0.8, STEEL_BLACK, steps=1))
    zd, yd, rd = FRONT_DRUM
    out.append(x_cyl(zd, yd, rd, -7.0, 7.0, STEEL_BLACK, n=16))
    out.append(x_cyl(zd, yd, 1.2, -7.4, 7.4, M.BORE, n=8))                      # ドラムの中心の穴（調整工具）
    out.append(sights.post(2 * POST_HALF, yd + rd - 0.5, SIGHT_Y, zd, STEEL_BLACK))       # ポスト（誇張）
    # 台: 銃身を抱く筒（銃口ナットと同じ太さ）＋図面の下の突起
    z0, z1 = _zr(O.FRONT_SIGHT_BASE)
    out.append(lathe(0, BORE_Y, [(z0, 12.0), (z1 - 1.0, 12.0)], ar15_mesh.N_MID, STEEL_BLACK))
    out += [extrude_x_beveled(p, -6.5, 6.5, 1.5, STEEL_BLACK, steps=1)
            for p in _clip(O.FRONT_SIGHT_BASE["outer"], -600.0, 0.0, -400.0, 126.0)]
    for z in (z0 + 7.0, z1 - 9.0):                                              # 銃身に留めるピン
        out.append(x_cyl(z, 127.5, 1.6, -10.9, 10.9, M.STEEL, n=8))
    out.append(lathe(-7.5, 128.5, [(z0 - 2.0, 1.3), (z0 + 1.0, 1.3)], 8, M.STEEL))   # 銃口ナットの止めピン（右前）
    return out


# ---------------------------------------------------------------- ハンドガード
def _clip_z_outline(o, z0, z1):
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(o["outer"]).intersection(sbox(z0, -1e4, z1, 1e4))
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda q: q.area)
    return list(g.exterior.coords)[:-1]


HG_RETAINERS = ((-214.0, -206.0),)   # 下ハンドガードの後ろの留め金（前は lower_front_retainer。写真で作り直した）


def handguard_retainers():
    """下ハンドガードの前後の鋼の留め金。木より 1mm 太い輪で、木の端面（受け部より幅広いので横から見える）を覆う。"""
    # 幅 8〜14mm の薄い輪なので inflate_x は使えない（半幅が輪郭の厚みを超えて内側オフセットが潰れる）
    hw = HALF_LOWER_HG * 1.45 + 1.0
    out = []
    for z0, z1 in HG_RETAINERS:
        prof = _clip_z_outline(O.LOWER_HANDGUARD, z0 - 0.5, z1 + 0.5)
        # 木の端面と同じ Z だと面が重なって木が透ける（z-fighting）ので、端は 0.8mm 外へ出して隣の部品に食い込ませる
        lo, hi = min(z for z, _ in prof), max(z for z, _ in prof)
        top = max(y for _, y in prof)
        # 上面も木の上面（上ハンドガードとの合わせ目）と同じ高さだと透けるので 0.8mm 上げる。下面は 1mm 下へ
        prof = [(lo - 0.8 if z == lo else hi + 0.8 if z == hi else z,
                 top + 0.8 if y == top else y - 1.0 if y < 120 else y) for z, y in prof]
        out.append(extrude_x_beveled(prof, -hw, hw, 1.5, STEEL_BLACK, steps=2))
    return out


def lower_handguard_wood():
    def width(z, y, f):
        return 1.45

    def radius(nz, ny):
        # 前後の端面（照門ブロック・ガス部に付く）と上面（上ハンドガードとの合わせ目）は丸めない
        if abs(nz) > 0.6 or ny > 0.6:
            return 1.5
        return 12.0 if ny < -0.5 else 3.0
    from shapely.geometry import Polygon, box as sbox
    # 前端は写真の位置（金具の縁の後ろ）。上の縁は上ハンドガードとの間に隙間を開ける（写真: 全長に 2〜3mm の白い線が
    # 抜け、前寄りの段から前は狭い）
    g = Polygon(_clip_z_outline(O.LOWER_HANDGUARD, LOWER_HG_FRONT_Z, 1e4))
    zs, (y_front, y_rear) = LOWER_HG_STEP_Z, LOWER_HG_TOP
    g = g.difference(sbox(zs, y_rear, 0.0, 300.0)).difference(sbox(-400.0, y_front, zs, 300.0))
    prof = [(round(z, 3), round(y, 3)) for z, y in list(g.exterior.coords)[:-1]]
    return [inflate_x(prof, HALF_LOWER_HG, WOOD, steps=4, width_fn=width, radius_fn=radius)]


def upper_handguard_wood():
    def width(z, y, f):
        return 1.2

    def radius(nz, ny):
        # 後ろの端面（照門ブロックに付く）と下面（下ハンドガードとの合わせ目）は丸めない。
        # 前の端は金具（upper_cap）に収まるので、丸めを小さくする（写真: 前端は斜めに面取りされて金具に入る）
        if nz < -0.6:
            return 4.0
        return 1.5 if (nz > 0.6 or ny < -0.6) else HALF_UPPER_HG
    return [inflate_x(O.UPPER_HANDGUARD["outer"], HALF_UPPER_HG, WOOD, steps=4, width_fn=width, radius_fn=radius)]


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
    # レールの台は上をハンドガードに 4mm 埋める（輪郭の下の縁は反っているので、一番低い所に合わせると隙間が見えた）
    out += [box(-8, y0 - 2, r0, 8, y0 + 4, r1, M.RAIL_DOWN), box(-RAIL_W / 2, y0 - 6, r0, RAIL_W / 2, y0 - 2, r1, M.RAIL_DOWN)]
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
    # レールの台は下をハンドガードに埋める（輪郭の上の縁は前下がりなので、一番高い所に合わせると隙間が見えた）
    out += [box(-8, yt - 6, r0, 8, yt + 3, r1, M.RAIL), box(-RAIL_W / 2, yt + 3, r0, RAIL_W / 2, yt + 8, r1, M.RAIL)]
    return out


# ---------------------------------------------------------------- 機関部の可動部
BOLT_FACE_Z = CHAMBER_Z + 18.0          # ボルトの前面＝薬室の実包の底（ammo ボーンの薬莢の底と同じ）


def bolt_carrier():
    """ボルトキャリア＋ボルトの頭。排莢口から側面が見え、後退すると奥（暗い壁）と薬室の後ろが見える。
    後ろの端は BOLT_TRAVEL_MAX 下がっても受け部の後端（Z +75）を越えない長さ。"""
    rear = 75.0 - BOLT_TRAVEL_MAX - 2.0
    return [box(-10, BORE_Y - 4, BOLT_FACE_Z + 12.0, 10, SLOT_Y[1] - 0.5, rear, M.STEEL),
            lathe(0, BORE_Y, [(BOLT_FACE_Z, 7.5), (BOLT_FACE_Z + 12.5, 7.5)], ar15_mesh.N_MID, M.STEEL)]


def charging_handle():
    """コッキングハンドル（右側面。図面: Z≈-53〜-67 の四角＋丸いつまみ）。軸はキャリアの側面から溝（SLOT_Y）を
    通って外へ出る（溝の上下の縁に触れないよう 0.5mm 空ける）。"""
    h = HALF_RECEIVER
    z0, z1 = HANDLE_Z
    return [box(-h - 8, SLOT_Y[0] + 0.5, z0, -9.5, SLOT_Y[1] - 0.5, z1, STEEL_BLACK),
            x_cyl((z0 + z1) / 2, 144.0, 6.0, -h - 16, -h - 7, STEEL_BLACK, n=12)]


# ---------------------------------------------------------------- 弾倉
MAG_REAR_Z = MAG_CATCH_BOX[0] + 0.5     # 弾倉の後ろの縁（図面ではマガジンキャッチと 1 つの影絵なので、ここで切る）
MAG_RIBS = (0.30, 0.68)                 # 側面の補強リブ（前の縁→後ろの縁の割合。図面の縦の 4 本線＝リブ 2 本の両縁）
MAG_TOP_Y = 124.0                       # 弾倉の上端（給弾リップの上面）。受け部の下面（Y 99）から 25mm 中へ入る。ボルト（ボア軸 133 から
                                        # 半径 7.5 → 下面 125.5）がリップの上を通って上の弾を押し出すので、その直下に置く 🟡 推定
                                        # （以前は 100 で 1mm しか入らず、差したときに下へ貼り付けたように見えた。作者の指摘）
MAG_SHELL_Y = 110.0                     # ここから上は中空（壁と給弾リップ）。下は詰まった本体で、その上面が送り板
MAG_REAR_LUG_Y = 86.0                   # 後ろの掛け金の突起（マガジンキャッチが掛かる）の基準の高さ
MAG_WALL = 1.0                          # 上部の壁の厚さ
MAG_LIP = (5.6, 2.4, 46.0)              # 給弾リップ（内側の縁の X、上下の厚さ、後ろの壁から前への長さ）
MAG_ROUND_X = 2.7                       # 中の弾の左右のずれ（複列。上の弾と次の弾が互い違い）
MAG_ROUND_Y = (118.3, 108.6)            # 上の弾・次の弾の軸の高さ（上の弾の頂部がリップの上面に揃う）


def _mag_edges():
    """弾倉の輪郭を前の縁・後ろの縁・底に分ける（図面の輪郭の点の並びから）。"""
    pts = O.MAGAZINE["outer"]
    i_rb = max(range(len(pts)), key=lambda i: (pts[i][0] < -140 and pts[i][1] < -50, -pts[i][1], pts[i][0]))  # 後ろ下の角
    i_fb = min(range(len(pts)), key=lambda i: pts[i][0])                                                        # 前下の角
    i_ft = min(range(len(pts)), key=lambda i: (abs(pts[i][1] - 100.0) > 0.5, pts[i][0]))                        # 前上の角
    rear = [(MAG_REAR_Z, 100.0)] + [p for p in pts[:i_rb + 1] if p[0] <= MAG_REAR_Z]   # 上端から
    front = pts[i_fb:i_ft + 1][::-1]          # 上 → 下
    return front, rear, (pts[i_rb], pts[i_fb])


def _resample(line, n):
    from shapely.geometry import LineString
    ls = LineString(line)
    return [ls.interpolate(k / (n - 1), normalized=True).coords[0] for k in range(n)]


def magazine_ak():
    """AK 30 発弾倉（鋼）: 図面の側面形（強く前へ反ったバナナ形）。後ろの縁はマガジンキャッチの前で切る。
    側面に湾曲に沿った補強リブ 2 本（図面の縦の線）、底に一回り大きい底板。"""
    from shapely.geometry import LineString, Polygon, box as sbox
    body = Polygon(O.MAGAZINE["outer"]).intersection(sbox(-400.0, -200.0, MAG_REAR_Z, 200.0))
    body = max(getattr(body, "geoms", [body]), key=lambda q: q.area)
    # 図面の影絵は受け部の下面（Y 100）で切れているので、受け部の中へ入る上の部分を前後の縁の延長で足す
    zf_top = min(z for z, y in O.MAGAZINE["outer"] if y >= 99.5)
    body = body.union(sbox(zf_top, 99.0, MAG_REAR_Z, MAG_TOP_Y))
    # 詰まった本体は MAG_SHELL_Y まで。その上は中空の箱（外したときに上から弾と送り板が見える）
    solid = body.intersection(sbox(-400.0, -200.0, 0.0, MAG_SHELL_Y + 0.5))
    solid = max(getattr(solid, "geoms", [solid]), key=lambda q: q.area)
    out = [extrude_x_beveled(list(solid.exterior.coords)[:-1], -HALF_MAG, HALF_MAG, 1.5, M.MAG_AK, steps=1)]
    out += magazine_top(body)
    front, rear, (rb, fb) = _mag_edges()
    F, R = _resample(front, 40), _resample(rear, 40)
    for f in MAG_RIBS:
        mid = [(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f) for a, b in zip(F, R)][6:34]   # 受け部の中・底板は避ける
        rib = LineString(mid).buffer(2.8, cap_style=1).intersection(body)
        for q in getattr(rib, "geoms", [rib]):
            if q.geom_type == "Polygon" and q.area > 1.0:
                out.append(extrude_x_beveled(list(q.simplify(0.2).exterior.coords)[:-1], -HALF_MAG - 1.4, HALF_MAG + 1.4,
                                             0.9, M.MAG_AK, steps=1))
    # 底板: 底の縁から 4mm の帯を、本体より 0.8mm 大きく
    plate = LineString([rb, fb]).buffer(4.5, cap_style=2).intersection(body.buffer(0.8, join_style=2))
    plate = max(getattr(plate, "geoms", [plate]), key=lambda q: q.area)
    out.append(extrude_x_beveled(list(plate.simplify(0.2).exterior.coords)[:-1], -HALF_MAG - 0.8, HALF_MAG + 0.8,
                                 1.0, M.MAG_AK, steps=1))
    return out


def magazine_top(body):
    """弾倉の上部（MAG_SHELL_Y〜上端）: 左右・前後の壁、内側へ巻き込んだ給弾リップ、送り板、前後の掛け金の突起。
    実物の AK の弾倉は上が開いていて、2 枚のリップの間から一番上の弾が見える。"""
    from shapely.geometry import box as sbox
    top = body.intersection(sbox(-400.0, MAG_SHELL_Y, 0.0, MAG_TOP_Y))
    top = max(getattr(top, "geoms", [top]), key=lambda q: q.area)
    z0, _, z1, _ = top.bounds
    prof = list(top.exterior.coords)[:-1]
    h, w = HALF_MAG, MAG_WALL
    out = []
    for s in (1, -1):                                                              # 左右の壁
        xa, xb = sorted((s * (h - w), s * h))
        out.append(extrude_x_beveled(prof, xa, xb, 0.4, M.MAG_AK, steps=1))
    for zz0, zz1 in ((z0 - 1.0, z0 + w + 0.5), (z1 - w, z1)):                       # 前後の壁
        for q in [top.intersection(sbox(zz0, MAG_SHELL_Y, zz1, MAG_TOP_Y))]:
            out.append(extrude_x_beveled(list(q.exterior.coords)[:-1], -h, h, 0.4, M.MAG_AK, steps=1))
    lx, lt, ll = MAG_LIP
    for s in (1, -1):                                                              # 給弾リップ（後ろの壁から前へ）
        xa, xb = sorted((s * lx, s * (h - w + 0.3)))
        out.append(extrude_x_beveled([(z1 - ll, MAG_TOP_Y - lt), (z1 - w + 0.3, MAG_TOP_Y - lt),
                                      (z1 - w + 0.3, MAG_TOP_Y), (z1 - ll + 4.0, MAG_TOP_Y)],
                                     xa, xb, 0.6, M.MAG_AK, steps=1))
    # 送り板（本体の上面に載る板。片側の段で 1 発目を互い違いの位置へ寄せる）。弾が空のときはこれが見える
    out.append(box(-h + w, MAG_SHELL_Y, z0 + w, h - w, MAG_SHELL_Y + 1.5, z1 - w, M.STEEL))
    out.append(box(-h + w, MAG_SHELL_Y + 1.5, z0 + 8.0, -0.5, MAG_SHELL_Y + 3.5, z1 - 6.0, M.STEEL))
    # 掛け金の突起: 前（受け部の前の溝に掛かる）・後ろ（マガジンキャッチが掛かる）。差すと受け部の中
    zf = min(z for z, y in prof if y >= MAG_TOP_Y - 0.5)                          # 上端での前の縁
    out.append(extrude_x_beveled([(zf - 3.0, MAG_TOP_Y - 1.0), (zf + w + 0.5, MAG_TOP_Y - 6.0), (zf + w + 0.5, MAG_TOP_Y + 2.5),
                                  (zf - 2.0, MAG_TOP_Y + 2.5)], -6.0, 6.0, 0.6, M.MAG_AK, steps=1))
    ly = MAG_REAR_LUG_Y
    out.append(extrude_x_beveled([(z1 - 0.5, ly - 2.0), (z1 + 2.5, ly - 1.0), (z1 + 2.5, ly + 6.0),
                                  (z1 - 0.5, ly + 6.0)], -4.5, 4.5, 0.6, M.MAG_AK, steps=1))
    return out


def magazine_rounds():
    """弾倉の中の弾（mag_ammo ボーン）: 上の 2 発を互い違いに。薬莢の底を後ろの壁に当てる。"""
    z_tip = MAG_REAR_Z - MAG_WALL - 0.5 - 56.0
    out = []
    # 次の弾は 5mm 前へ（弾倉の後ろの縁は下ほど前へ反るので、同じ位置だと薬莢の底が外へ出る）
    for x, y, dz in ((MAG_ROUND_X, MAG_ROUND_Y[0], 0.0), (-MAG_ROUND_X, MAG_ROUND_Y[1], -5.0)):
        case, bullet = cartridge_762(z_tip + dz, y, x)
        out += case + bullet
    return out


def cartridge_762(z_tip, y, x=0.0):
    """7.62×39mm 実包（回転体）: 全長 56mm、薬莢 38.7mm、テーパーの強い胴。"""
    b = z_tip + 56.0
    case = [(b, 5.6), (b - 1.5, 5.6), (b - 1.8, 4.9), (b - 3.0, 4.9), (b - 3.4, 5.55), (b - 30.5, 5.2),
            (b - 33.5, 4.4), (b - 38.7, 4.3)]
    bullet = [(b - 38.7, 3.9), (b - 44.0, 3.85), (b - 50.0, 2.9), (b - 54.5, 1.2), (z_tip, 0.4)]
    return ([lathe(x, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(x, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


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
    add("selector", "receiver", (-HALF_RECEIVER, SELECTOR_PIVOT[1], SELECTOR_PIVOT[0]), "selector", selector())
    add("lower_receiver", "receiver", (0, 100.0, 0), "trigger_guard", trigger_guard())
    add("mag_release", "lower_receiver", (0, MAG_CATCH_PIN[1], MAG_CATCH_PIN[0]), "mag_release", mag_release())
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
        add("rail_top", "root", (0, _yr(O.DUST_COVER)[1] + 8, COVER_RAIL_REAR_Z), None, [])
        add("rail_bottom", "root", (0, y_bottom, r1), None, [])
        add("rail_side", "root", (x_side, yc, r1), None, [])
    else:
        add("handguard", "root", (0, b, -208.0), "handguard_wood",
            lower_handguard_wood() + upper_handguard_wood() + handguard_retainers() + lower_front_retainer())
        add("rail_top", "root", (0, _yr(O.DUST_COVER)[1], 60.0), None, [])
        add("rail_bottom", "root", (0, _yr(O.LOWER_HANDGUARD)[0], -208.0), None, [])
        add("rail_side", "root", (HALF_RECEIVER, b, -208.0), None, [])

    add("bolt", "root", (0, b, -80.0), "bolt_carrier", bolt_carrier())
    add("charging_handle", "bolt", (-HALF_RECEIVER, 144.0, sum(HANDLE_Z) / 2), "charging_handle", charging_handle())

    add("magazin", "root", (0, 100.0, -90.0), "magazine_ak", magazine_ak())
    add("mag_ammo", "magazin", (0, MAG_ROUND_Y[0], -88.0), None, magazine_rounds())

    tip = CHAMBER_Z - 56.0 + 18.0                       # 薬室内の実包（排莢クリップの起点）
    case, bullet = cartridge_762(z_tip=tip, y=b)
    add("ammo", "root", (0, b, tip + 35), None, case)
    add("bullet", "ammo", (0, b, tip + 6), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(O.GRIP["outer"]).centroid
    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K,
                 rear_sight_z=REAR_SIGHT_Z * K, grip_center=(0, c.y * K, c.x * K), support_z=-265.0 * K)
    return m, parts
