"""
Accuracy International AWM（.338 Lapua Magnum。折りたたみストック・マズルブレーキ付き）のパーツと組み立て（単位 mm、メッシュ版）。

側面形は Wikimedia Commons の英軍 L115A3（AWM .338 の英軍型）の真横写真（左側面。英国防省、OGL v1.0）からトレースした
輪郭（awm_outline.py ← trace_awm.py）。写真はタン色だが、作者の指定でオリーブ色にした。消音器・二脚・後ろの一脚・
スコープはアタッチメント扱いで外し、銃口には AWM のマズルブレーキを付けた（作者の指定）。
縮尺はレールの溝の間隔（10.0mm）で合わせ、スコープの長さ（公表 400mm に対して 413mm）を確かめた。
左右の幅は推定（下の HALF_*。上面図が無い）。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝ボルトハンドル・排莢口の側）、Y=0 グリップの底、
Z=0 トリガー、銃口 -Z。

ボルトの動き（アニメーション用）: ボーン charging_handle（ボルト本体とハンドル）を銃身の軸まわりに 60° 起こし、
ボーン bolt（後ろの覆いを含む全体）を後ろへ BOLT_TRAVEL 引く。ストックはボーン butt（蝶番の軸＝左側面の縦の軸）で
左へ折りたためる。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import sights
import awm_outline as O
from core import MeshPart, box, extrude_x, extrude_x_beveled, extrude_x_rounded, inflate_x, lathe
from m249 import x_cyl
from mp5 import extrude_z
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
STOCK_MAT = M.AWM_STOCK
STEEL_BLACK = M.AWM_STEEL
BOLT_MAT = M.AWM_BOLT

BORE_Y = 145.5
MUZZLE_Z = -808.0           # 銃口（消音器の取付部の中。銃身 686mm を薬室から数えた位置）
BRAKE_Z = (-888.0, -803.0)  # マズルブレーキ（AWM の標準。長さ 85mm）
BRAKE_R = 14.5
RCV_FRONT_Z = -200.0        # 受け部の前の端（写真）
RCV_REAR_Z = -2.0           # 受け部の後ろの端（ボルトの覆いの前）
RCV_R = 17.5                # 受け部の半径（写真の上の縁 Y 163）
BOLT_R = 9.5
BOLT_FACE_Z = -122.0        # ボルトの前面（薬室の後端。銃身 686mm から逆算）
BOLT_TRAVEL = 130.0         # ボルトを引く量（.338 LM 93.5mm を出し入れできる長さ。🟡 実物の値は未確認）
PORT_Z = (-118.0, -30.0)    # 右側面の排莢口（🟡 写真の反対側なので長さは実包から決めた）
PORT_Y = (141.5, 156.0)     # 下の縁はストックの上の縁（Y 141）
HANDLE_ROOT_Z = 4.0         # ボルトハンドルの付け根（受け部の後ろの端の後ろ）
KNOB = (-46.0, 140.0, 22.0)   # ハンドルの玉の中心（X, Y, Z）。🟡 写真（斜め後ろの AWM の写真）から推定
SAFETY_Z = 18.0
RAIL_Z = (-235.0, 10.0)     # 受け部の上のレール（写真）
RAIL_Y = 163.0

# 左右の半幅（推定）
HALF_FOREND = 25.0
HALF_ACTION = 24.0
HALF_GRIP = 16.0
HALF_BUTT = 21.0
HALF_PAD = 22.5
FOLD = [(400.0, -60.0), (400.0, 300.0), (105.0, 300.0), (105.0, 97.0), (100.0, 75.0), (93.0, 54.0), (79.0, -60.0)]
HINGE_PIVOT = (HALF_ACTION, 115.0, 105.0)   # 折りたたみの蝶番の軸（左側面の縦の軸。X, Y, Z）

MAG_TOP_Y = 128.0           # 弾倉の上の端（ストックの中）
HALF_MAG = 14.0
MAG_SHELL = 12.0            # 上の中空の高さ（外したときに弾が見える）
MAG_WALL = 1.4


def _lerp(a, b, t):
    return a + (b - a) * min(1.0, max(0.0, t))


def _ring(q):
    return list(q.exterior.coords)[:-1]


def _poly(o):
    from shapely.geometry import Polygon
    return Polygon(o["outer"], o["holes"])


def _parts_of(g):
    return [q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 0.5]


# ---------------------------------------------------------------- ストック
# 実物（AWM・G22 の写真）: グリップは断面が楕円に近い丸い握り（手のひらの膨らみ）、親指の穴・床尾の縁も大きく丸い。
# 先台・受け部の下は平らな側面で角だけ丸い。トリガーガードはストックと一体だが細い輪。
# 以前は全体を平らな板の角を 4mm 丸めただけで、グリップが角張っていた（作者の指摘「グリップとストックの作り込みが甘い」）。
# トリガーガードの下の縁（5.4mm）が丸みの大きさを縛っていたので、ガードを別の部品に分け、本体は M24 と同じく
# 膨らませる作り（inflate_x）で場所ごとに丸みを変える。
STOCK_H = 16.0              # 膨らませる量（丸みの半径の上限＝グリップの半幅）
GRIP_R = 14.0               # グリップの丸み（ほぼ丸い断面）
GUARD_CUT = [(-38.0, 40.0), (21.0, 40.0), (21.0, 86.0), (-38.0, 86.0)]   # 本体から切り出すトリガーガードの範囲
HALF_GUARD = 12.0
PALM = (55.0, 42.0, 1.6)    # 手のひらの膨らみ（中心 Z, Y と、半幅の増し）
FOREND_GROOVE = (-395.0, -60.0, 126.0, 129.5)   # 先台の横の長い溝（G22 の写真。前後 z, 上下 y）
SCREWS = [(73.0, 113.0, 3.4), (5.0, 112.0, 4.2), (-44.0, 108.0, 3.4), (-159.0, 104.0, 3.4), (-270.0, 112.0, 3.4),
          (-377.0, 112.0, 3.4), (63.0, 33.0, 3.4)]                      # ストックの前のボルトの頭（写真）
BUTT_SCREWS = [(239.0, 113.0, 3.4), (201.0, 113.0, 6.5), (125.0, 113.0, 3.4), (274.0, 60.0, 3.4), (191.0, 60.0, 3.4)]


def stock_half(z, y):
    """ストック（シャーシ）の半幅。先台 → 受け部の下 → グリップ（手のひらの膨らみ） → 床尾。"""
    if z < -40.0:
        w = _lerp(HALF_FOREND, HALF_ACTION, (z + 200.0) / 160.0)
    elif z < 110.0:
        w = HALF_ACTION if y > 100.0 else _lerp(HALF_GRIP, HALF_ACTION, (y - 70.0) / 30.0)
        pz, py, pw = PALM
        d = math.hypot((z - pz) / 30.0, (y - py) / 35.0)
        if y < 100.0 and d < 1.0:
            w += pw * (1.0 - d * d)
    else:
        w = _lerp(HALF_ACTION, HALF_BUTT, (z - 110.0) / 60.0)
    return w


def _stock_pieces():
    from shapely.geometry import Polygon
    g = _poly(O.STOCK)
    fold = Polygon(FOLD)
    front = max(_parts_of(g.difference(fold)), key=lambda q: q.area)
    rear = max(_parts_of(g.intersection(fold)), key=lambda q: q.area)
    guard = max(_parts_of(front.intersection(Polygon(GUARD_CUT))), key=lambda q: q.area)
    body = max(_parts_of(front.difference(Polygon(GUARD_CUT))), key=lambda q: q.area)
    return body, guard, rear


def _dense(q, step=10.0):
    """輪郭を間隔 step 以下に点を足す（側面の平らな面を格子点で分けるとき、輪郭の点が疎だと三角形が外へはみ出すため）。"""
    import shapely
    return _ring(shapely.segmentize(q.simplify(0.3), step))


def _near(z, y, line, tol=0.6):
    from shapely.geometry import LineString, Point
    return LineString(line).distance(Point(z, y)) < tol


def _body_radius(z, y, nz, ny):
    """ストックの前（本体）の丸み: 切り口（折りたたみの継ぎ目・ガードの切り出し）は小さく、グリップは大きく。"""
    if _near(z, y, FOLD[2:]) or _near(z, y, GUARD_CUT + GUARD_CUT[:1]):
        return 1.5
    if 20.0 < z < 110.0 and y < 98.0:
        return GRIP_R
    if ny > 0.6:
        return 3.0               # 上の面（受け部が載る）
    if ny < -0.5:
        return 8.0               # 先台・弾倉の前後の下の縁
    return 5.0


def _butt_radius(z, y, nz, ny):
    if _near(z, y, FOLD[2:]):
        return 1.5
    if ny > 0.6:
        return 4.0               # 上の面（ほお当ての下）
    if ny < -0.5:
        return 10.0              # 床尾の下の縁
    return 9.0                   # 親指の穴の後ろの縁・床尾の後ろ


def stock():
    """ストックの前（先台・受け部の下・グリップ）とトリガーガード・折りたたみの蝶番・ボルトの頭・先台の溝。"""
    body, guard, _ = _stock_pieces()
    hinge = _poly(O.HINGE).simplify(0.3)
    width = lambda z, y, f: stock_half(z, y) / STOCK_H
    out = [inflate_x(_dense(body), STOCK_H, STOCK_MAT, steps=4, width_fn=width, radius_at=_body_radius,
                     cap_grid=14.0),
           extrude_x_rounded(_ring(guard.simplify(0.3)), [list(h.coords)[:-1] for h in guard.simplify(0.3).interiors],
                             lambda z, y: HALF_GUARD, 2.0, STOCK_MAT, steps=2),
           extrude_x_beveled(_ring(hinge), -HALF_ACTION - 1.5, HALF_ACTION + 1.5, 1.5, STEEL_BLACK, steps=1)]
    # 先台の上の銃身の溝（実物は銃身が浮いている溝。上面の銃身の両脇を暗くして溝に見せる）
    for s in (1, -1):
        xa, xb = sorted((s * 13.0, s * 17.0))
        out.append(box(xa, 145.3, -409.0, xb, 145.7, -205.0, M.BORE))
    z0, z1, y0, y1 = FOREND_GROOVE
    for s in (1, -1):
        w = stock_half((z0 + z1) / 2, (y0 + y1) / 2)
        xa, xb = sorted((s * (w - 0.3), s * (w + 0.25)))
        out.append(box(xa, y0, z0, xb, y1, z1, M.AWM_STOCK_DARK))
    out += _screws(SCREWS, stock_half)
    return out


def _screws(points, half_fn):
    out = []
    for z, y, r in points:
        w = half_fn(z, y)
        for s in (1, -1):
            xa, xb = sorted((s * (w - 0.5), s * (w + 0.7)))
            out.append(x_cyl(z, y, r, xa, xb, STEEL_BLACK, n=10))
    return out


def butt():
    """床尾（ボーン butt。蝶番で左へ折りたためる）: ストックの後ろ・ほお当て・床尾板（ゴム）。"""
    _, _, rear = _stock_pieces()
    cheek = _poly(O.CHEEK).simplify(0.3)
    pad = _poly(O.BUTT_PAD).simplify(0.3)
    width = lambda z, y, f: stock_half(z, y) / STOCK_H
    out = [inflate_x(_dense(rear), STOCK_H, STOCK_MAT, steps=4, width_fn=width, radius_at=_butt_radius,
                     cap_grid=14.0),
           extrude_x_beveled(_ring(cheek), -HALF_BUTT + 3.0, HALF_BUTT - 3.0, 3.0, STEEL_BLACK, steps=2),
           extrude_x_beveled(_ring(pad), -HALF_PAD, HALF_PAD, 3.5, M.RUBBER, steps=2)]
    out += _screws(BUTT_SCREWS, lambda z, y: stock_half(z, y))
    return out


# ---------------------------------------------------------------- 受け部・銃身
def _rcv_section(port=False, n=28):
    """受け部の断面（丸）。port=True で右側面に排莢口の窓（M24 と同じ作り。窓は軸の向こうまで切り欠く）。"""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = RCV_R * math.cos(a), BORE_Y + RCV_R * math.sin(a)
        if port and x < 0 and PORT_Y[0] < y < PORT_Y[1]:
            continue
        pts.append((x, y))
    if port:
        top = (-math.sqrt(RCV_R ** 2 - (PORT_Y[1] - BORE_Y) ** 2), PORT_Y[1])
        bot = (-math.sqrt(RCV_R ** 2 - (PORT_Y[0] - BORE_Y) ** 2), PORT_Y[0])
        inner = 3.0
        i = next(j for j, p in enumerate(pts) if p[0] < 0 and p[1] < PORT_Y[0])
        pts[i:i] = [top, (inner, PORT_Y[1]), (inner, PORT_Y[0]), bot]
    return pts


def receiver():
    """受け部（丸い筒）と上のレール（スコープの台。規約の幅 1px・溝 0.5px）。右側面に排莢口。"""
    pz0, pz1 = PORT_Z
    out = [extrude_z(_rcv_section(), RCV_FRONT_Z, pz0, STEEL_BLACK),
           extrude_z(_rcv_section(port=True), pz0, pz1, STEEL_BLACK),
           extrude_z(_rcv_section(), pz1, RCV_REAR_Z, STEEL_BLACK)]
    (nw, nh), (hw, hh) = ar15_parts.RAS_NECK, ar15_parts.RAS_HEAD
    z0, z1 = RAIL_Z
    # 台の下は 159（受け部より前へ張り出す所で銃身の上端 159.3 に載せる。160 だと 0.7mm 浮いて線が見えた）
    out += [box(-nw / 2, RAIL_Y - 4.0, z0, nw / 2, RAIL_Y + nh, z1, M.RAIL),
            box(-hw / 2, RAIL_Y + nh, z0, hw / 2, RAIL_Y + nh + hh, z1, M.RAIL)]
    return out


def fluted_z(cy, prof, mat, flutes=6, depth=1.3, per=4):
    """溝（フルート）のある銃身: Z 方向の回転体で、周に flutes 本の浅い溝。prof=[(z, r)]（z 昇順）。"""
    n = flutes * per
    verts, faces = [], []
    for z, r in prof:
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            rr = r - depth if (k % per) in (1, 2) else r
            verts.append((rr * math.cos(a), cy + rr * math.sin(a), z))
    for i in range(len(prof) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            faces.append([i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k])
    return MeshPart(verts, faces, mat).finalize()


def barrel():
    """銃身（先台の前から溝のある重い銃身。太さはトレース）とマズルブレーキ。"""
    prof = sorted((z, r) for z, r in O.BARREL_R if z < -420.0)             # 先台より前（先台の中は写真で隠れる）
    r_rear = 14.0
    plain = [(MUZZLE_Z, prof[0][1]), (prof[0][0] + 30.0, prof[0][1])]       # 銃口の前 30mm は溝の無い円筒
    flute = ([(prof[0][0] + 30.0, prof[0][1])] + [(z, r) for z, r in prof if z > prof[0][0] + 30.0]
             + [(RCV_FRONT_Z - 60.0, r_rear)])
    out = [lathe(0, BORE_Y, plain, ar15_mesh.N_MID, STEEL_BLACK, cap0=False, cap1=False),
           fluted_z(BORE_Y, flute, STEEL_BLACK),
           lathe(0, BORE_Y, [(RCV_FRONT_Z - 60.0, r_rear), (RCV_FRONT_Z + 1.0, r_rear)], ar15_mesh.N_MID, STEEL_BLACK)]
    out += muzzle_brake()
    return out


def muzzle_brake():
    """マズルブレーキ（円筒に左右 3 つずつの大きな窓。窓は暗い面で表す）。"""
    z0, z1 = BRAKE_Z
    out = [lathe(0, BORE_Y, [(z0, 5.5), (z0, BRAKE_R - 1.0), (z0 + 2.0, BRAKE_R), (z1, BRAKE_R), (z1, 11.0)],
                 ar15_mesh.N_MID, STEEL_BLACK, cap0=False, cap1=True),
           lathe(0, BORE_Y, [(z0 - 0.2, 5.4), (z0 + 20.0, 5.4)], ar15_mesh.N_SMALL, M.BORE, cap0=False)]
    for i in range(3):
        za = z0 + 10.0 + i * 22.0
        for s in (1, -1):
            xa, xb = sorted((s * (BRAKE_R - 4.0), s * (BRAKE_R + 0.4)))
            out.append(box(xa, BORE_Y - 6.5, za, xb, BORE_Y + 6.5, za + 15.0, M.BORE))
    return out


# ---------------------------------------------------------------- ボルト
def bolt_shroud():
    """ボルトの後ろの覆い（トレース）。ボルトと一緒に前後する。"""
    # 後ろの端は Z 29.5 の垂直な面で、そこから細いピン（コッキングピースの指示）が出る（写真を 8 倍に拡大して読んだ。
    # トレースはピンと覆いの角をつないで丸く膨らんでいた）
    from shapely.geometry import box as sbox
    g = _poly(O.SHROUD).intersection(sbox(-50.0, 100.0, 29.5, 200.0)).simplify(0.3)
    return [extrude_x_beveled(_ring(g), -11.0, 11.0, 2.5, STEEL_BLACK, steps=2),
            lathe(0.0, 141.5, [(28.0, 1.6), (34.0, 1.6)], 8, STEEL_BLACK)]


def bolt_body():
    """ボルト本体（排莢口から見える明るい鋼の筒）とボルトハンドル（右側面。大きな玉）。ボーン charging_handle。"""
    out = [lathe(0, BORE_Y, [(BOLT_FACE_Z, BOLT_R), (RCV_REAR_Z + 4.0, BOLT_R)], ar15_mesh.N_MID, BOLT_MAT),
           lathe(0, BORE_Y, [(BOLT_FACE_Z - 0.3, 3.0), (BOLT_FACE_Z + 1.0, 3.0)], 8, M.BORE)]
    kx, ky, kz = KNOB
    zr = HANDLE_ROOT_Z
    out.append(box(-RCV_R - 3.0, BORE_Y - 4.0, zr - 5.0, -BOLT_R + 1.0, BORE_Y + 5.0, zr + 5.0, STEEL_BLACK))
    # 腕: 付け根から右へ出て、後ろ下へ向かう（上から見て斜め後ろ）
    from shapely.geometry import LineString
    arm = LineString([(-RCV_R - 2.0, zr), (kx + 6.0, kz - 4.0)]).buffer(3.2, cap_style=1, quad_segs=3)
    pts = list(arm.exterior.coords)[:-1]
    out.append(_y_extrude([(x, z) for x, z in pts], ky - 3.0, BORE_Y + 3.0, STEEL_BLACK))
    out.append(lathe(kx, ky, [(kz - 11.0, 0.5), (kz - 9.0, 7.0), (kz - 4.0, 10.5), (kz + 4.0, 10.5), (kz + 9.0, 7.0),
                              (kz + 11.0, 0.5)], ar15_mesh.N_MID, STEEL_BLACK))
    return out


def _y_extrude(section_xz, y0, y1, mat):
    """XZ 平面の形を Y 方向に押し出す（ハンドルの腕。上から見た形）。y0 側を下にして斜めの腕は y を線形に変える代わりに
    単純な板にする。"""
    from core import _area2, _triangulate
    pts = list(section_xz)
    if _area2(pts) > 0:
        pts.reverse()
    n = len(pts)
    verts = [(x, y0, z) for x, z in pts] + [(x, y1, z) for x, z in pts]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    for t in _triangulate(list(reversed(pts))):
        a, b, c = (n - 1 - t[0], n - 1 - t[1], n - 1 - t[2])
        faces.append([a, b, c])
        faces.append([n + c, n + b, n + a])
    return MeshPart(verts, faces, mat).finalize()


# ---------------------------------------------------------------- 引き金まわり・弾倉
TRIGGER_PATH = [(4.5, 82.5, 1.7), (3.5, 76.0, 1.4), (1.5, 70.0, 1.2), (-1.0, 65.5, 1.0), (-4.0, 62.5, 0.9)]


def trigger():
    from m24 import _stroke
    return [extrude_x_beveled(_stroke(TRIGGER_PATH), -3.5, 3.5, 0.5, STEEL_BLACK, steps=1)]


def safety():
    """安全装置（右側面の後ろの 3 位置のレバー。ボーン selector）。"""
    x = -RCV_R
    return [box(x - 3.0, 148.0, SAFETY_Z - 3.0, x + 1.0, 153.0, SAFETY_Z + 3.0, STEEL_BLACK),
            box(x - 4.5, 149.0, SAFETY_Z - 10.0, x - 2.5, 152.0, SAFETY_Z + 1.0, STEEL_BLACK)]


def mag_release():
    """弾倉止め（トリガーガードの前に下がるレバー。前へ押すと外れる）。"""
    # 写真: 細い棒（Z -43〜-45.5）が Y 66 から 44 まで垂れ、先は丸い
    return [extrude_x_beveled([(-43.0, 76.0), (-45.5, 76.0), (-45.5, 45.5), (-44.8, 44.3), (-43.7, 44.3), (-43.0, 45.5)],
                              -2.5, 2.5, 0.6, STEEL_BLACK, steps=1)]


def magazine():
    """5 発弾倉（鋼。側面に縦の窓 2 本）。上の端はストックの中。上部は中空で、外したときに一番上の弾が見える。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(O.MAGAZINE["outer"]).simplify(0.3)
    zs = [p[0] for p in O.MAGAZINE["outer"]]
    zf, zr = min(zs) + 1.0, max(zs) - 1.0
    body = g.union(sbox(zf, 70.0, zr, MAG_TOP_Y - MAG_SHELL))
    h, w = HALF_MAG, MAG_WALL
    out = [extrude_x_beveled(_ring(body), -h, h, 1.0, M.AWM_MAG, steps=1)]
    y0 = MAG_TOP_Y - MAG_SHELL
    for s in (1, -1):
        xa, xb = sorted((s * (h - w), s * h))
        out.append(box(xa, y0, zf, xb, MAG_TOP_Y, zr, M.AWM_MAG))
        for zc in (-72.0, -118.0):                                        # 側面の縦の窓（暗い面）
            xa, xb = sorted((s * (h - 0.4), s * (h + 0.3)))
            out.append(box(xa, 45.0, zc - 2.5, xb, 74.0, zc + 2.5, M.BORE))
    out += [box(-h, y0, zf, h, MAG_TOP_Y, zf + w, M.AWM_MAG), box(-h, y0, zr - w, h, MAG_TOP_Y, zr, M.AWM_MAG)]
    for s in (1, -1):                                                     # 給弾リップ
        xa, xb = sorted((s * 4.5, s * (h - w + 0.3)))
        out.append(box(xa, MAG_TOP_Y - 2.0, zr - 45.0, xb, MAG_TOP_Y, zr - w + 0.3, M.AWM_MAG))
    out.append(box(-h + w, y0, zf + w, h - w, y0 + 1.0, zr - w, M.FOLLOWER))
    return out


def cartridge_338(z_tip, y, x=0.0):
    """.338 Lapua Magnum 実包（回転体）: 全長 93.5mm、薬莢 69.2mm、底 14.93mm。"""
    b = z_tip + 93.5
    case = [(b, 7.47), (b - 1.5, 7.47), (b - 1.9, 6.6), (b - 3.2, 6.6), (b - 3.6, 7.45), (b - 59.0, 7.0),
            (b - 63.0, 4.6), (b - 69.2, 4.6)]
    bullet = [(b - 69.2, 4.3), (b - 76.0, 4.3), (b - 86.0, 3.0), (b - 91.5, 1.2), (z_tip, 0.4)]
    return ([lathe(x, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(x, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


def magazine_rounds():
    """弾倉の中の弾（mag_ammo）: 上の 2 発を互い違いに。薬莢の底を後ろの壁に当てる。"""
    zs = [p[0] for p in O.MAGAZINE["outer"]]
    zr = max(zs) - 1.0 - MAG_WALL - 0.5
    out = []
    for x, y in ((3.6, MAG_TOP_Y - 7.47), (-3.6, MAG_TOP_Y - 7.47 - 11.0)):
        case, bullet = cartridge_338(zr - 93.5, y, x)
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
    add("receiver", "root", (0, b, 0), "receiver", receiver())
    add("selector", "receiver", (-RCV_R, 150.0, SAFETY_Z), "safety", safety())
    add("trigger", "root", (0, 82.0, 4.0), "trigger", trigger())
    add("stock", "root", (0, 100.0, 0.0), "stock", stock())
    add("lower_receiver", "stock", (0, 80.0, 0), None, [])
    add("mag_release", "stock", (0, 76.0, -43.0), "mag_release", mag_release())
    add("butt", "stock", HINGE_PIVOT, "butt", butt())             # 折りたたみ（Y 軸まわりに左へ）

    add("barrel", "root", (0, b, BOLT_FACE_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BOLT_FACE_Z), None, [])
    add("muzzle", "root", (0, b, BRAKE_Z[0]), None, [])
    add("handguard", "root", (0, b, -330.0), None, [])
    add("rail_top", "root", (0, RAIL_Y + 5.0, sum(RAIL_Z) / 2), None, [])
    # デフォルトのアイアンサイト（実銃に照準器は無い。折りたたみ式をレールの前後の端に載せる。
    # サイトのアタッチメントを付けるとコードがこのボーンを描かない）
    irons, sight_y = sights.default_irons(RAIL_Y + 5.0, RAIL_Z[1] - 13.0, RAIL_Z[0] + 11.0, trigger_z=4.0)
    add("iron_sight", "root", (0, RAIL_Y + 5.0, RAIL_Z[1] - 13.0), "iron_sight", irons)
    add("rail_bottom", "root", (0, 100.0, -330.0), None, [])              # 先台の下（二脚）
    add("rail_side", "root", (HALF_FOREND, 125.0, -360.0), None, [])

    add("bolt", "root", (0, b, BOLT_FACE_Z + 40.0), "bolt_shroud", bolt_shroud())
    add("charging_handle", "bolt", (0, b, HANDLE_ROOT_Z), "bolt_body", bolt_body())

    zs = [p[0] for p in O.MAGAZINE["outer"]]
    zc = (min(zs) + max(zs)) / 2
    add("magazin", "root", (0, 80.0, zc), "magazine", magazine())
    add("mag_ammo", "magazin", (0, MAG_TOP_Y - 10.0, zc), None, magazine_rounds())

    tip = BOLT_FACE_Z - 93.5
    case, bullet = cartridge_338(tip, b)
    add("ammo", "root", (0, b, tip + 60.0), None, case)
    add("bullet", "ammo", (0, b, tip + 10.0), None, bullet)

    add_locators(m, muzzle=(0, b * K, BRAKE_Z[0] * K), sight_line_y=sight_y * K,
                 rear_sight_z=(RAIL_Z[1] - 13.0) * K, grip_center=(0, 60.0 * K, 60.0 * K), support_z=-264.0 * K)
    return m, parts
