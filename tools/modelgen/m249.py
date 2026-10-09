"""
M249（FN 標準型・固定ストック）のパーツと組み立て（単位 mm、メッシュ版）。

寸法の根拠（docs/specs/07-model-assets.md「M249 の参照品」）:
  - 全長 1035mm（40.75in、FN 公表値）・銃身 465mm（18.3in）
  - 側面形は作者提供の写真（STANAG 弾倉・二脚をたたんだ状態／ボックス＋ベルト・二脚を立てた状態の 2 枚）から取った。
    縮尺は全長で合わせた 0.704px/mm（1px≒1.4mm と粗い）。写真は再現品の可能性がある
  - 左右の幅（受け部の幅・ハンドガード・ストック等）は写真が真横だけなので未確認（③）
座標は M4A1 と同じ: X=0 左右対称面（+X が左側面＝弾倉・ベルトの側）、Y=0 グリップ底面、Z=0 トリガー、銃口 -Z。

2 つのモデルを同じ部品から出す: m249（ボックス＋ベルト。仕様の装弾数 100 発に合わせた標準）と m249_stanag（STANAG 弾倉）。
二脚・キャリングハンドル・フィードカバーは回転できるボーンにし、既定はたたんだ状態（写真 1 枚目）。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
from core import MeshPart, Model, box, extrude_x, extrude_x_beveled, inflate_x, lathe
from rig import add_locators
import m249_outline as O

K = 1.0 / ar15_parts.MM_PER_PX
SLOT_MM = ar15_parts.SLOT_MM
RAIL_W = ar15_parts.RAIL_W_MM


class Layout:
    bore_y = 169.3          # ボア軸高さ（グリップ底面基準）
    muzzle_z = -651.0       # フラッシュハイダー先端（全長 1035mm: 床尾 384 から）
    barrel_end_z = -603.0   # 銃身の先端（フラッシュハイダーの付け根）
    breech_z = -138.0       # 銃身の後端（薬室）。銃身 465mm から逆算（受け部前端の少し奥）
    rcv_rear_z = 121.4      # 受け部の後端（ストックの付け根）
    rcv_front_z = -151.0    # 受け部の前端
    rcv_half = 27.0         # 受け部の半幅（③ 未確認）
    rcv_bottom = 110.0      # 受け部の下面
    cover_split = 197.0     # 受け部本体とフィードカバーの境目（写真の横線）
    cover_hinge = (-128.0, 205.0)   # フィードカバーの蝶番（z, y）。前端で回り、後ろが持ち上がる（写真のカバー前端の形から）
    cover_top = 211.0       # フィードカバーの上面（レールの土台）
    cover_front_z = -131.0  # フィードカバーの前端（フィードトレイの前）
    rail_slots = 15         # フィードカバーのレール（写真 約 176mm ÷ 規約 12mm/スロット）
    rail_rear_z = 58.0
    rail_h = 9.2
    sight_y = 222.0         # 照準線の高さ（リアサイトの穴の中心。写真から）
    rear_sight_z = 87.4     # リアサイトの穴の位置
    feed_z = (-131.0, -52.0)   # フィードトレイ（左側のベルト入口）と弾倉口の前後範囲
    feed_y = 183.0          # トレイ上の弾の中心の高さ（ボア軸の約 14mm 上。写真で弾帯が受け部に入る高さ）
    feed_gap = (176.0, 192.0)   # 左側面の弾帯の入口（上下）
    link_pitch = 10.5       # 弾帯の弾の間隔（推定: 薬莢径 9.6mm＋リンクの板。公表値は見つからず）
    hg_rear_z = -151.0      # ハンドガード
    hg_front_z = -362.0
    hg_top = 178.0
    hg_bottom = 97.0
    hg_half = 29.0          # ハンドガードの半幅（③ 未確認）
    shield = (-176.0, -349.0, 180.0, 196.0)   # 銃身上のレール台（前後・下面・上面）
    gas_y = 140.0           # ガスシリンダーの中心高さ
    gas_front_z = -458.0
    fs_z = (-419.0, -442.0)  # フロントサイトの前後
    fs_top = 232.0          # フロントサイトの耳の上端
    bipod_pivot = (-385.0, 99.0)    # 二脚の回転軸（z, y）。ガスシリンダーから下がる取付け金具の下端（写真）
    bipod_len = 235.0       # 回転軸→足先。たたむと足板が受け部の前（Z≈-150）に来て、立てると足が Y≈-135（写真 2 枚）
    bipod_ext = 30.0        # 脚の伸び（伸縮量は未確認）
    bipod_fold_deg = 0.5    # たたんだ脚はハンドガードの下面に沿ってほぼ水平（写真）
    handle_pivot = (-200.0, 206.0)  # キャリングハンドルの回転軸（z, y）。軸は銃身と平行（前後方向）で、左へ倒れる
    handle_fold_deg = 72.0  # たたんだ角度（写真 1 枚目: 握りの高さと傾きが起こした状態の cos72°≒0.3 倍）
    mag_tilt = 45.0         # STANAG 弾倉の傾き（左下へ。③ 写真の見かけの高さ 122mm と 45° が一致）
    mag_pivot = (14.0, 170.0)       # 弾倉上端の中心（X, y）。写真の弾倉下端に合わせた
    mag_center_z = -84.0
    box = (-44.0, -125.0, 0.0, 119.5)   # ボックス（前後・下面・上面。写真のトレースと同じ）
    box_x = (-65.0, 65.0)   # ボックスの左右（③ 幅 約 130mm。受け部の左右へほぼ対称にはみ出す＝作者指摘）
    butt_z = 384.0


L = Layout()
STEEL_BLACK = M.STEEL_DARK


def rotated(parts, axis, deg, pivot):
    """MeshPart の頂点・法線を軸（'x' / 'z'）まわりに回す。pivot は (x, y, z)。"""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)

    def rot(v, p=True):
        x, y, z = (v[0] - pivot[0], v[1] - pivot[1], v[2] - pivot[2]) if p else v
        if axis == "z":
            x, y = x * c - y * s, x * s + y * c
        else:
            y, z = y * c - z * s, y * s + z * c
        return (x + pivot[0], y + pivot[1], z + pivot[2]) if p else (x, y, z)

    out = []
    for m in parts:
        n = None if m.normals is None else [[rot(v, False) for v in f] for f in m.normals]
        out.append(MeshPart([rot(v) for v in m.verts], m.faces, m.mat, n, m.charts, m.chart_uv, m.chart_edge))
    return out


def x_cyl(z, y, r, x0, x1, mat, n=None):
    """X 方向の円柱（ピン・リベット・蝶番の軸）。Z 方向の回転体を作って軸を入れ替える。"""
    m = lathe(0, y, [(x0, r), (x1, r)], n or ar15_mesh.N_SMALL, mat)
    swap = lambda v: (v[2], v[1], v[0])
    n_ = None if m.normals is None else [[swap(v) for v in f] for f in m.normals]
    return MeshPart([(v[2], v[1], v[0] + z) for v in m.verts], m.faces, m.mat, n_, m.charts, m.chart_uv, m.chart_edge)


def y_cyl(x, z, r, y0, y1, mat, n=None):
    """Y 方向の円柱（下向きのつまみ等）。"""
    m = lathe(x, z, [(y0, r), (y1, r)], n or ar15_mesh.N_SMALL, mat)
    swap = lambda v: (v[0], v[2], v[1])
    n_ = None if m.normals is None else [[swap(v) for v in f] for f in m.normals]
    return MeshPart([swap(v) for v in m.verts], m.faces, m.mat, n_, m.charts, m.chart_uv, m.chart_edge)


def ring_z(y, z0, z1, r_in, r_out, mat, cx=0.0, n=None):
    """Z 方向を軸にした輪（フロントサイトのフード等）。"""
    return lathe(cx, y, [(z0, r_in), (z0, r_out), (z1, r_out), (z1, r_in), (z0, r_in)], n or ar15_mesh.N_MID, mat,
                 cap0=False, cap1=False)


def arc_ring(cx, cy, z0, z1, r_in, r_out, a0, a1, mat, n=10):
    """Z 方向を軸にした部分的な輪（角度 a0〜a1 [度]。リンクの「開いた輪」用）。"""
    verts, faces = [], []
    angs = [math.radians(a0 + (a1 - a0) * i / n) for i in range(n + 1)]
    idx = {}
    for i, a in enumerate(angs):
        for j, (r, z) in enumerate(((r_out, z0), (r_out, z1), (r_in, z1), (r_in, z0))):
            idx[i, j] = len(verts)
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for i in range(n):
        for j in range(4):
            faces.append([idx[i, j], idx[i + 1, j], idx[i + 1, (j + 1) % 4], idx[i, (j + 1) % 4]])
    faces.append([idx[0, 0], idx[0, 1], idx[0, 2], idx[0, 3]])
    faces.append([idx[n, 3], idx[n, 2], idx[n, 1], idx[n, 0]])
    return MeshPart(verts, faces, mat).finalize()


def cartridge(x, y, z_tip):
    """5.56×45mm 実包（回転体）: 縁・抽筒溝・テーパーの胴・肩・首、弾頭は先細り。全長 57.4mm、薬莢 44.7mm。"""
    b = z_tip + 57.4                                    # 薬莢の底（+Z 側）
    case = [(b, 4.8), (b - 1.1, 4.8), (b - 1.3, 4.2), (b - 2.2, 4.2), (b - 2.6, 4.75), (b - 36.5, 4.55),
            (b - 39.6, 3.15), (b - 44.7, 3.1)]
    bullet = [(b - 44.7, 2.85), (b - 49.0, 2.8), (b - 53.5, 2.1), (b - 56.5, 0.9), (z_tip, 0.3)]
    return [lathe(x, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False),
            lathe(x, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)]


def outline_parts(o, x0, x1, mat, bevel=0.0, steps=1):
    """トレースした側面形 {'outer', 'holes'} を X 方向に押し出す。穴があれば、穴の中心を通る縦線で
    穴の無い片に切り分けてから押し出す（角丸めは切り口に溝が出るので、穴のある部品では使わない）。"""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import split
    g = Polygon(o["outer"], o["holes"])
    if not o["holes"]:
        f = extrude_x_beveled(o["outer"], x0, x1, bevel, mat, steps) if bevel else extrude_x(o["outer"], x0, x1, mat)
        return [f]
    pieces = [g]
    for h in o["holes"]:
        cz = Polygon(h).centroid.x
        cut = LineString([(cz, -1e4), (cz, 1e4)])
        pieces = [q for pc in pieces for q in split(pc, cut).geoms]
    return [extrude_x(list(q.exterior.coords)[:-1], x0, x1, mat) for q in pieces if q.area > 0.5]


def clip_z(o, z0, z1):
    """側面形を前後 z0〜z1 で切る。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(o["outer"], o["holes"]).intersection(sbox(z0, -1e4, z1, 1e4))
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda q: q.area)
    r = lambda ring: list(ring.coords)[:-1]
    return {"outer": r(g.exterior), "holes": [r(h) for h in g.interiors]}


def clip_y(o, y0, y1):
    """側面形を高さ y0〜y1 で切る（穴も含めて）。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(o["outer"], o["holes"]).intersection(sbox(-1e4, y0, 1e4, y1))
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda q: q.area)
    r = lambda ring: list(ring.coords)[:-1]
    return {"outer": r(g.exterior), "holes": [r(h) for h in g.interiors]}


# ---------------------------------------------------------------- 受け部
# 左側面の留め具（写真から。z, y, 半径）。右側面も同じ位置に置く（右側面の写真は無い）
POCKET = (-128.0, -54.0, 150.0, 7.0)   # 給弾部の下の空間（前端 z, 後端 z, 底の高さ, 左右の壁の厚さ）
RIVETS = [(98.0, 172.0, 2.0), (30.0, 172.0, 2.0), (-37.0, 172.0, 2.0), (50.0, 141.0, 2.0), (-27.0, 141.0, 2.0)]
PINS = [(118.0, 178.0, 5.0), (106.0, 170.0, 3.5), (110.0, 145.0, 3.5), (90.0, 152.0, 3.5), (115.0, 122.0, 4.5),
        (30.0, 122.0, 2.5), (-8.0, 121.0, 2.5), (-118.0, 175.0, 3.0)]


def _with_notch(o, z0, z1, y0, y1):
    """側面形に長方形の窓を開ける（穴として）。"""
    return {"outer": o["outer"], "holes": o["holes"] + [[(z0, y0), (z1, y0), (z1, y1), (z0, y1)]]}


def receiver(l=L):
    h, b = l.rcv_half, l.bore_y
    # 給弾部の下の空間（フィードトレイを上げると見える）: 中央部だけ側面形から切り欠き、左右の壁は全形のまま
    from shapely.geometry import Polygon, box as sbox
    pz0, pz1, pfloor, wall = POCKET
    inner = Polygon(O.RECEIVER["outer"]).difference(sbox(pz0, pfloor, pz1, 400))
    inner = inner if inner.geom_type == "Polygon" else max(inner.geoms, key=lambda q: q.area)
    out = [
        *outline_parts(_with_notch(O.RECEIVER, l.feed_z[0] + 3, l.feed_z[1] - 2, *l.feed_gap), h - wall, h,
                       M.RECEIVER),                                             # 左の壁（弾帯の入口を開ける）
        *outline_parts(O.RECEIVER, -h, -h + wall, M.RECEIVER),
        extrude_x(list(inner.exterior.coords)[:-1], -h + wall, h - wall, M.RECEIVER),   # 中央部（給弾部を切り欠く）
        box(-h + wall, pfloor, pz0, h - wall, pfloor + 0.4, pz1, M.BORE),          # 空間の底（暗い）
        ring_z(b, pz0 - 0.5, pz0 + 0.5, 3.6, 12.0, M.STEEL),                    # 前の壁: 薬室の口
        lathe(0, b, [(pz0 - 0.4, 3.6), (pz0 + 0.6, 3.6)], ar15_mesh.N_SMALL, M.BORE),
        box(-9, b - 10, pz1 - 0.6, 9, b + 10, pz1, M.STEEL),                   # 後ろの壁: ボルトの面
        # 側面の段（写真の横の筋）: 中ほどの張り出しと、上下の細い溝
        box(h, 157, -50, h + 1.5, 161, l.rcv_rear_z - 4, M.RECEIVER),
        box(-h - 1.5, 157, -50, -h, 161, l.rcv_rear_z - 4, M.RECEIVER),
        *[box(h, y, -48, h + 0.3, y + 1.0, l.rcv_rear_z - 8, STEEL_BLACK) for y in (127.0, 180.0, 189.0)],
        *[box(-h - 0.3, y, -48, -h, y + 1.0, l.rcv_rear_z - 8, STEEL_BLACK) for y in (127.0, 180.0, 189.0)],
        lathe(0, b, [(l.rcv_front_z - 6, 20), (l.rcv_front_z + 2, 20)], ar15_mesh.N_MID, STEEL_BLACK),   # 銃身受け
    ]
    for s_ in (1, -1):      # 留め具（両側面）
        x0, x1 = (h - 0.5, h + 1.4) if s_ > 0 else (-h - 1.4, -h + 0.5)
        out += [x_cyl(z, y, r, x0, x1, STEEL_BLACK) for z, y, r in RIVETS]
        x0, x1 = (h - 0.5, h + 2.0) if s_ > 0 else (-h - 2.0, -h + 0.5)
        out += [x_cyl(z, y, r, x0, x1, STEEL_BLACK) for z, y, r in PINS]
    out.append(x_cyl(-35.0, 118.0, 4.0, h - 0.5, h + 1.0, M.BORE))           # 側面の丸穴（写真の明るい輪）
    out += left_feed(l) + right_side(l)
    out.append(box(-4, l.cover_split - 0.4, -54, 4, l.cover_split + 0.2, 100, M.BORE))   # 上面のコッキングの溝（カバー裏の溝カバーが閉じる）
    return out


def left_feed(l=L):
    """左側面の給弾口: 弾帯が入る張り出し（上下の枠の間を弾帯が通る）と、その下の弾倉口の受け。"""
    h = l.rcv_half
    z0, z1 = l.feed_z
    g0, g1 = l.feed_gap
    return [
        box(h, 160, z0 + 2, h + 8, g0, z1, M.RECEIVER),                      # 入口の下の枠
        box(h, g1, z0 + 2, h + 8, l.cover_split + 13, z1, M.RECEIVER),       # 入口の上の枠
        box(h, g0, z0 + 2, h + 8, g1, z0 + 5, M.RECEIVER),                   # 入口の前の柱
        box(h, g0, z1 - 2, h + 8, g1, z1, M.RECEIVER),                       # 入口の後ろの柱
        box(h + 8, 153, z0 + 14, h + 10, 157, z1 - 10, STEEL_BLACK),         # 弾倉止めの横棒（写真）
    ]


def right_side(l=L):
    """右側面: コッキングハンドルのガイドレールと取っ手、リンク排出口、薬莢の排莢口（ばね式のダストカバー付き）。
    FM 3-22.68: コッキングハンドルは右側面のガイドレールを動く。薬莢は右側面の下部から、リンクはフィードトレイの右から出る。"""
    h = l.rcv_half
    return [
        box(-h - 3, 160, -150, -h, 168, 20, M.RECEIVER),                       # ガイドレール
        box(-h - 6, 158, -150, -h - 3, 170, -136, STEEL_BLACK),                # 取っ手の付け根
        box(-h - 18, 161, -147, -h - 6, 167, -139, STEEL_BLACK),               # 取っ手の腕（横へ出る）
        y_cyl(-h - 15, -143, 5.0, 128, 166, M.POLYMER),                       # つまみ（下を向く。拡大写真）
        box(-h - 0.3, 186, -122, -h, 196, -66, M.BORE),                        # リンク排出口
        box(-h - 1.5, 116, -124, -h, 140, -62, M.RECEIVER),                    # 排莢口のダストカバー（閉）
        lathe(-h - 1.5, 116, [(-124, 1.8), (-62, 1.8)], ar15_mesh.N_SMALL, STEEL_BLACK),   # ダストカバーの軸
    ]


def magwell(l=L):
    """弾倉口: 受け部の左下から 45° 左下へ向いた短い筒。"""
    px, py = l.mag_pivot
    zc = l.mag_center_z
    sleeve = [(zc - 36, py + 8), (zc + 36, py + 8), (zc + 36, py - 14), (zc - 36, py - 14)]
    return rotated([extrude_x(sleeve, px - 15, px + 15, M.RECEIVER)], "z", l.mag_tilt, (px, py, zc))


def feed_cover(l=L):
    """フィードカバー: 前端の蝶番で回り、後ろが持ち上がる（ボーン feed_cover。開けると支えなしで開いたまま）。
    後ろの左右に押して外すラッチ。裏にはベルトを送るフィードレバーとフィードポール（開けたときに見える）。"""
    h = l.rcv_half
    hz, hy = l.cover_hinge
    top = clip_y(O.FEED_COVER, l.cover_top - 4, 1e4)
    zr = max(p[0] for p in O.FEED_COVER["outer"])
    return [
        *outline_parts(top, -h + 0.5, h - 0.5, M.RECEIVER),                  # 天板
        *outline_parts(O.FEED_COVER, h - 2.0, h, M.RECEIVER),                # 側面の板（左）
        *outline_parts(O.FEED_COVER, -h, -h + 2.0, M.RECEIVER),              # 〃（右）
        box(-h, l.cover_split, zr - 5, h, l.cover_top, zr, M.RECEIVER),       # 後ろの板
        x_cyl(hz, hy, 5.0, -h + 3, h - 3, STEEL_BLACK),                       # 蝶番
        box(h, 199, zr - 16, h + 3, 207, zr - 6, STEEL_BLACK),                # ラッチ（左）
        box(-h - 3, 199, zr - 16, -h, 207, zr - 6, STEEL_BLACK),              # ラッチ（右）
        box(-3, l.cover_top - 9, -112, 3, l.cover_top - 4, 40, STEEL_BLACK),  # フィードレバー（天板の裏）
        box(-12, l.feed_y + 6, hz + 8, 12, l.cover_top - 4, hz + 16, STEEL_BLACK),   # 前の弾ガイド（蝶番の後ろ）
        box(-12, l.feed_y + 6, -66, 12, l.cover_top - 4, -60, STEEL_BLACK),          # 後ろの弾ガイド
        box(4, l.feed_y + 5, -104, 11, l.cover_top - 4, -88, STEEL_BLACK),   # フィードポール（左）
        box(-11, l.feed_y + 5, -104, -4, l.cover_top - 4, -88, STEEL_BLACK),  # 〃（右）
    ]


def feed_tray(l=L):
    """フィードトレイ: 弾帯を左から受け、先頭の弾を弾止めに当てて薬室の上（ボア軸の少し上）に位置決めする。
    リンクの開いた側を下にして平らに置く（FM 3-22.68）。前を軸に持ち上がる（ボーン feed_tray）。"""
    h = l.rcv_half
    y = l.feed_y - 5.0                      # トレイの上面（弾の下）
    z0, z1 = -128.0, -54.0
    return [
        box(-19, y - 3, z0, h + 8, y, z1, M.RECEIVER),
        box(-19, y, -98, h + 8, y + 2, -95, M.RECEIVER),                     # 弾を導く溝の縁（前）
        box(-19, y, -66, h + 8, y + 2, -63, M.RECEIVER),                     # 〃（後ろ）
        box(-11, y, z0, -6, l.feed_y + 4, z1, STEEL_BLACK),                  # 弾止め（先頭の弾の右）
    ]


def rail_top(l=L):
    z1 = l.rail_rear_z
    z0 = z1 - l.rail_slots * SLOT_MM
    y0 = l.cover_top
    return [box(-8, y0, z0, 8, y0 + 4, z1, M.RAIL),
            box(-RAIL_W / 2, y0 + 4, z0, RAIL_W / 2, y0 + l.rail_h, z1, M.RAIL)]


def rear_sight(l=L):
    """リアサイト: 台の上に左右の耳（側面形は写真。耳を通して穴が見える）、間にアパーチャー板（穴の中心＝照準線）。"""
    z, sy, y0 = l.rear_sight_z, l.sight_y, l.cover_top
    base = clip_y(O.REAR_SIGHT, -1e4, y0 + 6)
    ears = clip_y(O.REAR_SIGHT, y0 + 5, 1e4)
    return [
        *outline_parts(base, -13, 13, M.RECEIVER),
        *outline_parts(ears, 6, 11, M.RECEIVER),
        *outline_parts(ears, -11, -6, M.RECEIVER),
        # アパーチャー板（中央に 3mm の穴）
        box(-5, y0 + 6, z - 1, 5, sy - 1.5, z + 1, STEEL_BLACK),
        box(-5, sy + 1.5, z - 1, 5, sy + 6, z + 1, STEEL_BLACK),
        box(1.5, sy - 1.5, z - 1, 5, sy + 1.5, z + 1, STEEL_BLACK),
        box(-5, sy - 1.5, z - 1, -1.5, sy + 1.5, z + 1, STEEL_BLACK),
        # 左右の調整つまみ（拡大写真: 丸穴の板の外側にローレットのつまみ。右側は距離の数字入りのドラム）
        x_cyl(z + 15, sy + 2, 6.0, 11, 18, STEEL_BLACK, n=12),
        x_cyl(z - 12, y0 + 7, 6.0, 11, 18, STEEL_BLACK, n=12),
        x_cyl(z - 6, y0 + 9, 7.0, -18, -11, STEEL_BLACK, n=12),
    ]


# ---------------------------------------------------------------- 下回り
def pistol_grip(l=L):
    """樹脂のグリップ。断面は丸め、上端は受け部の下面（Y=108）に接する。側面に横溝（拡大写真）。"""
    from shapely.geometry import LineString, Polygon
    def radius(nz, ny):
        return 4.0 + 8.0 * (1 - ar15_mesh._smoothstep(0.55, 0.9, abs(ny)))
    out = [inflate_x(O.GRIP["outer"], 14.0, M.POLYMER, steps=ar15_mesh.GRIP_STEPS, radius_fn=radius)]
    g = Polygon(O.GRIP["outer"])
    for y in range(26, 92, 7):
        seg = g.intersection(LineString([(-1e3, y), (1e3, y)]))
        zs = [c[0] for c in seg.coords] if seg.geom_type == "LineString" else []
        if len(zs) < 2:
            continue
        za, zb = min(zs) + 8, max(zs) - 8
        if zb - za < 8:
            continue
        for x0, x1 in ((13.6, 14.3), (-14.3, -13.6)):
            out.append(box(x0, y, za, x1, y + 2.2, zb, M.RUBBER))
    return out


def trigger_guard(l=L):
    return outline_parts(O.TRIGGER_GUARD, -5, 5, M.RECEIVER)


def trigger(l=L):
    return [extrude_x_beveled(O.TRIGGER["outer"], -3, 3, 1.0, STEEL_BLACK, steps=1)]


def stock(l=L):
    """固定ストック（PIP の樹脂ストック。M240 のストックを手本にした形で、中に油圧バッファ）。側面形は写真、
    幅は部品の寸法表記の 2in（51mm）。床尾板は初期型のアルミ板（縦の溝）で、上に肩当ての鉤。下に負い紐の輪。"""
    hw = 25.5
    zb = max(p[0] for p in O.BUTTPLATE["outer"])
    out = [
        extrude_x_beveled(O.STOCK["outer"], -hw, hw, 8.0, M.POLYMER, steps=3),
        *outline_parts(O.BUTTPLATE, -hw - 1.5, hw + 1.5, STEEL_BLACK, bevel=2.0),
    ]
    out += [box(x - 1.0, 74.0, zb - 0.2, x + 1.0, 192.0, zb + 0.4, M.BORE) for x in range(-20, 21, 5)]   # 床尾板の溝
    # 負い紐の輪（ストック下の段の前。写真の小さな鉤）: Y-Z 面の輪
    ring = ring_z(0.0, -1.5, 1.5, 4.0, 7.0, STEEL_BLACK, n=12)
    out.append(MeshPart([(v[2], v[1] + 82.0, v[0] + 247.0) for v in ring.verts], ring.faces, ring.mat,
                        None, ring.charts, ring.chart_uv, ring.chart_edge))
    return out


# ---------------------------------------------------------------- 銃身まわり
def _radius_profile(prof, r_max):
    return [(z, min(r, r_max)) for z, r in prof]


def barrel(l=L):
    """銃身: 写真の太さの分布（先へ細くなり、銃口の手前で太くなる）。ハンドガード内は一定。"""
    b = l.bore_y
    bore = 5.56 / 2
    prof = _radius_profile(O.BARREL_R, 10.1)          # フロントサイト・ガス調整ノブの写り込みを除く
    pts = [(l.barrel_end_z, bore), (l.barrel_end_z, prof[-1][1])] + prof[::-1] + [(l.breech_z, 10.1)]
    pts = [(z, r) for z, r in pts]
    return [
        lathe(0, b, pts, ar15_mesh.N_MID, M.STEEL, cap0=False),
        lathe(0, b, [(l.muzzle_z, bore), (l.muzzle_z + 25, bore)], ar15_mesh.N_SMALL, M.BORE, cap0=False),
    ]


def flash_hider(l=L):
    """スリット入りのフラッシュハイダー（太さは写真。先端は穴あきの輪）。"""
    b, z0, z1 = l.bore_y, l.muzzle_z, l.barrel_end_z
    prof = [(z, r) for z, r in O.FLASH_HIDER_R if r > 8]
    out = [
        lathe(0, b, [(z1, prof[0][1])] + prof[1:8], ar15_mesh.N_MID, STEEL_BLACK),             # 根元
        lathe(0, b, [(z0 + 6, 4)] + [(z0 + 6, prof[-1][1])] + [p for p in prof if p[0] > z0 + 6][::-1][:1],
              ar15_mesh.N_MID, STEEL_BLACK, False, False),
        lathe(0, b, [(z0 + 6, 4), (z0, 4), (z0, 9.5), (z0 + 6, prof[-1][1])], ar15_mesh.N_MID, STEEL_BLACK, False, False),
        lathe(0, b, [(z0 + 6, 6.5), (prof[7][0], 6.5)], ar15_mesh.N_MID, M.BORE),
    ]
    r = max(p[1] for p in prof)
    for k in range(6):   # スリットの間の桟
        a = math.radians(30 + 60 * k)
        cx, cy = (r - 2) * math.cos(a), b + (r - 2) * math.sin(a)
        out.append(extrude_x([(z0 + 6, cy - 2), (prof[7][0], cy - 2), (prof[7][0], cy + 2), (z0 + 6, cy + 2)],
                             cx - 2, cx + 2, STEEL_BLACK))
    return out


def front_sight(l=L):
    """フロントサイト: 銃身を抱く台から塔が立ち、上に輪のフード（中にポスト）。塔の側面に止めねじの穴。
    側面形は写真、輪のフードは拡大写真（前から見ると丸い輪）。"""
    b = l.bore_y
    zs = [p[0] for p in O.FRONT_SIGHT["outer"]]
    z0, z1 = min(zs), max(zs)
    top = max(p[1] for p in O.FRONT_SIGHT["outer"])
    r_out = 10.5
    cy = top - r_out                                    # 輪の中心（照準線のすぐ上）
    zc = (z0 + z1) / 2
    tower = clip_y(O.FRONT_SIGHT, -1e4, cy - r_out + 3)
    return [
        lathe(0, b, [(z0 + 4, 14), (z1 - 4, 14)], ar15_mesh.N_MID, STEEL_BLACK),
        *outline_parts(tower, -6, 6, STEEL_BLACK),
        ring_z(cy, zc - 3, zc + 3, 8.0, r_out, STEEL_BLACK, n=16),
        x_cyl(zc, b + 30, 2.5, 5.8, 6.4, M.BORE), x_cyl(zc, b + 30, 2.5, -6.4, -5.8, M.BORE),   # 止めねじの穴
    ]


def front_sight_post(l=L):
    zc = sum(l.fs_z) / 2
    return [box(-1, l.sight_y - 14, zc - 1, 1, l.sight_y, zc + 1, STEEL_BLACK)]


def gas_system(l=L):
    """銃身下のガスシリンダー・ガスブロック・二脚の取付け（側面形は写真。断面は丸める）と、前端の調整ノブ（六角）。"""
    zs = [p[0] for p in O.GAS["outer"]]
    zf = min(zs)
    pz, py = l.bipod_pivot
    return [box(-11, py - 4, pz - 8, 11, l.gas_y - 8, pz + 8, STEEL_BLACK),          # 二脚の取付け金具（下へ伸びる）
            extrude_x_beveled(O.GAS["outer"], -13, 13, 5.0, STEEL_BLACK, steps=2),
            lathe(0, l.gas_y, [(zf, 12.5), (zf + 14, 12.5)], 6, STEEL_BLACK)]


def handguard(l=L):
    """ハンドガード（黒い樹脂。手を熱・寒さから守り、中に清掃用具を収める。FM 3-22.68）。側面形は二脚を立てた写真。
    断面は下側を大きく丸めた箱形。右から左へ押す止めピンで留まる（海兵隊教材）＝側面の丸い金具。"""
    f, r = l.hg_front_z, l.hg_rear_z

    def radius(nz, ny):
        return 12.0 if ny < -0.5 else 4.0          # 下面の縁は大きく丸め、上面・前後は小さく
    out = [inflate_x(O.HANDGUARD["outer"], l.hg_half, M.POLYMER, steps=4, radius_fn=radius)]
    for y in (118.0, 140.0, 158.0):     # 側面の横溝の間の帯（写真の 3 本の筋）
        for s in (1, -1):
            out.append(box(s * (l.hg_half - 0.5), y, f + 30, s * (l.hg_half + 0.8), y + 4, r - 20, M.POLYMER))
    # 止めピン（左右を貫く。左に穴あきの端、右に頭）
    out += [x_cyl(-314.0, 119.0, 7.0, l.hg_half - 1, l.hg_half + 3, STEEL_BLACK, n=12),
            x_cyl(-314.0, 119.0, 3.0, l.hg_half + 2.9, l.hg_half + 3.2, M.BORE),
            x_cyl(-314.0, 119.0, 5.0, -l.hg_half - 3, -l.hg_half + 1, STEEL_BLACK, n=12)]
    return out


def rail_handguard(l=L):
    """ヒートシールド（銃身の上の放熱板。キャリングハンドルのすぐ前から持ち上げて外す。部品の寸法表記 幅 2in）。
    側面形は写真。下は銃身を覆う幅広の部分（側面に放熱の丸穴の列）、上は細くなってレールを載せる。"""
    zs = [p[0] for p in O.SHIELD["outer"]]
    zf, zr = min(zs), max(zs)
    y1 = max(p[1] for p in O.SHIELD["outer"])
    yb = min(p[1] for p in O.SHIELD["outer"])
    ym = yb + 10.0                                  # 幅広の部分の上端
    lower = clip_y(O.SHIELD, -1e4, ym)
    upper = clip_y(O.SHIELD, ym - 0.5, 1e4)
    holes = [x_cyl(z, yb + 5.0, 3.0, sx, sx + 0.3, M.BORE)
             for z in [zr - 16 - 19 * i for i in range(int((zr - zf - 20) // 19))] for sx in (24.4, -24.7)]
    return holes + [
        extrude_x_beveled(lower["outer"], -24.5, 24.5, 3.0, M.RECEIVER, steps=2),
        extrude_x_beveled(upper["outer"], -15, 15, 2.0, M.RECEIVER, steps=1),
        box(-8, y1, zf + 2, 8, y1 + 3, zr - 2, M.RAIL),
        box(-RAIL_W / 2, y1 + 3, zf + 2, RAIL_W / 2, y1 + 7.6, zr - 2, M.RAIL),
    ]


def carry_handle(l=L):
    """キャリングハンドル（銃身交換用の取っ手。銃身組立品の後部に付き、使わないときは倒す）。
    写真 2 枚の比較から: 銃身の上の台から前へ伸びる棒が回転軸（銃身と平行）で、その前端から腕が上へ立ち、
    握りは腕の上端から後ろへ斜め上に伸びる「C」字形。左へ倒すとたたんだ状態（写真 1 枚目）。
    ここでは起こした形を作り、handle_fold_deg だけ左へ倒して既定の姿勢にする。"""
    _, py = l.handle_pivot
    zb, zf = -160.0, -245.0                    # 台の後端・軸棒の前端
    gz0, gy0, gz1, gy1 = -250.0, 247.0, -166.0, 269.0   # 握りの前端（腕の上端）・後端（写真 2 枚目）
    tilt = math.degrees(math.atan2(gy1 - gy0, gz1 - gz0))
    glen = math.hypot(gz1 - gz0, gy1 - gy0)
    # 握り: 指の凹凸のある回転体（Z 方向に作ってから傾ける）。後端は少し太いつば
    prof = [(gz0, 9.0), (gz0 + 6, 10.5), (gz0 + 16, 9.5), (gz0 + 28, 11.0), (gz0 + 40, 9.5), (gz0 + 52, 11.0),
            (gz0 + 64, 9.8), (gz0 + glen - 10, 10.8), (gz0 + glen - 6, 12.5), (gz0 + glen, 12.5)]
    grip = rotated([lathe(0, gy0, prof, ar15_mesh.N_MID, M.POLYMER)], "x", -tilt, (0, gy0, gz0))
    arm = [extrude_x([(zf - 4, py - 3), (zf + 3, py - 3), (gz0 + 3, gy0), (gz0 - 4, gy0)], -3, 3, STEEL_BLACK)]
    parts = grip + arm + [lathe(0, py, [(zf - 4, 3.2), (zb - 20, 3.2)], ar15_mesh.N_SMALL, STEEL_BLACK)]  # 軸棒
    parts = rotated(parts, "z", -l.handle_fold_deg, (0, py, 0))     # 左（+X）へ倒す
    return parts + [box(-9, l.shield[3] + 2, zb - 22, 9, py + 6, zb, STEEL_BLACK)]   # 台（銃身側。動かない部分）


def bipod_leg(l=L, side=1):
    """二脚の片脚（たたんだ状態: 後ろへ倒れ、ハンドガードの下に沿う）。拡大写真: 脚は溝の入った平たい板で、
    中に細い脚が入る伸縮式。side=+1 左 / -1 右。"""
    pz, py = l.bipod_pivot
    x = side * 9
    end = pz + l.bipod_len - 20
    leg = [
        x_cyl(pz, py, 6.0, x - 3.5, x + 3.5, STEEL_BLACK, n=10),                                  # 付け根の軸
        extrude_x([(pz, py - 6), (end, py - 5), (end, py + 5), (pz, py + 6)], x - 1.8, x + 1.8, STEEL_BLACK),
        extrude_x([(pz + 30, py - 1.5), (end - 20, py - 1.5), (end - 20, py + 1.5), (pz + 30, py + 1.5)],
                  min(x + side * 1.8, x + side * 2.1), max(x + side * 1.8, x + side * 2.1), M.BORE),  # 外側の溝
    ]
    return rotated(leg, "x", l.bipod_fold_deg, (0, py, pz))


def bipod_foot(l=L, side=1):
    """伸縮する中の脚と足板（立てたとき地面に平らに当たる板）。"""
    pz, py = l.bipod_pivot
    x = side * 9
    end = pz + l.bipod_len
    foot = [extrude_x([(end - 40, py - 3.5), (end - 3, py - 3.5), (end - 3, py + 3.5), (end - 40, py + 3.5)],
                      x - 1.2, x + 1.2, STEEL_BLACK),
            extrude_x([(end - 4, py - 15), (end, py - 15), (end, py + 13), (end - 4, py + 13)], x - 8, x + 8, STEEL_BLACK)]
    return rotated(foot, "x", l.bipod_fold_deg, (0, py, pz))


# ---------------------------------------------------------------- 給弾
def stanag_mag(l=L):
    """STANAG 30 発弾倉: 形は M4A1 の弾倉そのまま（側面のリブも含む）。弾倉口から左下へ 45° 傾けて差す点だけが違う。"""
    px, py = l.mag_pivot

    class _ML(ar15_parts.Layout):
        bore_y = py + 14.0
        mag_center_z = l.mag_center_z
    parts = []
    for p in ar15_mesh.magazine_stanag(_ML()):
        if not isinstance(p, MeshPart):     # キューブ（側面のリブ）は同じ寸法のメッシュに置き換えて一緒に傾ける
            (x0, y0, z0), (sx, sy, sz) = p.origin, p.size
            p = extrude_x([(z0, y0), (z0 + sz, y0), (z0 + sz, y0 + sy), (z0, y0 + sy)], x0, x0 + sx, p.mat)
        parts.append(MeshPart([(v[0] + px, v[1], v[2]) for v in p.verts], p.faces, p.mat, p.normals, p.charts,
                              p.chart_uv, p.chart_edge))
    return rotated(parts, "z", l.mag_tilt, (px, py, l.mag_center_z))


def ammo_box(l=L):
    """200 発ボックス（樹脂のふた＋布の袋）。側面形は写真。受け部の下に左右ほぼ対称に掛ける。"""
    x0, x1 = l.box_x
    z0, z1 = min(p[0] for p in O.BOX_BODY["outer"]), max(p[0] for p in O.BOX_BODY["outer"])
    zc = (z0 + z1) / 2
    return [
        extrude_x_beveled(O.BOX_BODY["outer"], x0, x1, 4.0, M.CANVAS, steps=2),
        extrude_x_beveled(O.BOX_LID["outer"], x0 - 1, x1 + 1, 2.0, M.BOX_LID, steps=1),
        box(x1 - 0.5, 20, zc - 2, x1 + 1.5, 80, zc + 2, M.BOX_LID),     # ファスナー（左面。側面写真で見える面）
        box(40, l.box[3] - 0.2, z0 + 12, 60, l.box[3] + 0.3, z1 - 12, M.BORE),   # ふたの上の弾帯の出口
    ]


def belt(l=L):
    """弾帯（M27 リンク）。トレイの上に平らに並び（リンクの開いた側が下、先頭の弾は弾止めに当たる。FM 3-22.68）、
    左側面の入口を出て外で下へ曲がり、ボックスのふたの出口に入る。外へ出ると開いた側は受け部の方を向く。
    リンク（Wikipedia: M27/M13）: 1 枚の板を曲げた部分的な輪。各リンクは 1 つの輪で自分の弾の薬莢（肩の下）を抱き、
    反対側の 2 つの輪で隣の弾を抱く（隣のリンクの輪と互い違い）。小さな舌が薬莢の抽筒溝に掛かる。"""
    pitch, fy = l.link_pitch, l.feed_y
    pts = []                                              # (x, y, 開いた側の向き[度])
    x = 0.0
    while x < l.rcv_half + 8:                             # トレイの上（先頭は X=0、薬室の上）〜入口
        pts.append((x, fy, -90.0))
        x += pitch
    r = 10.0
    cx, cy = x - pitch * 0.4, fy - r                      # 外で下へ曲がる円弧の中心
    for a in (60.0, 20.0):
        t = math.radians(a)
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t), a + 180.0))   # 開いた側は円弧の中心（内側）を向く
    xd = cx + r
    y = cy - pitch * 0.6
    while y > l.box[3] + 3:
        pts.append((xd, y, 180.0))
        y -= pitch
    out = []
    zt = -119.4                                           # 弾頭の先（写真）
    zb = zt + 57.4                                        # 薬莢の底
    for i, (x, y, nd) in enumerate(pts):
        out += cartridge(x, y, zt)
        gap = 70.0                                        # 輪の開き（開いた側の向きを中心に）
        a0, a1 = nd + gap / 2, nd + 360 - gap / 2
        out.append(arc_ring(x, y, zb - 26, zb - 18, 4.85, 5.5, a0, a1, STEEL_BLACK))        # 自分のリンクの輪
        if i > 0:                                                                        # 前の弾のリンクの 2 つの輪
            out.append(arc_ring(x, y, zb - 15, zb - 10, 4.85, 5.5, a0, a1, STEEL_BLACK))
            out.append(arc_ring(x, y, zb - 34, zb - 29, 4.85, 5.5, a0, a1, STEEL_BLACK))
            px, py, _ = pts[i - 1]                                                       # 2 つの弾をつなぐ背の板
            n = math.radians(nd + 180.0)                                                 # 閉じた側
            ox, oy = 5.3 * math.cos(n), 5.3 * math.sin(n)
            for za, zc in ((zb - 34, zb - 29), (zb - 15, zb - 10)):      # 2 つの輪の幅だけの細い帯でつなぐ
                out.append(_plate((px + ox, py + oy), (x + ox, y + oy), za, zc))
        out.append(arc_ring(x, y, zb - 3.2, zb - 1.6, 4.0, 4.6, nd + 120, nd + 240, STEEL_BLACK, n=4))  # 抽筒溝の舌
    return out


def _plate(p0, p1, z0, z1, mat=None):
    """2 点 p0→p1（X, Y）を結ぶ、Z 方向 z0〜z1 の薄い板（両面描画なので 1 枚の四角形）。"""
    (x0, y0), (x1, y1) = p0, p1
    return MeshPart([(x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)], [[0, 1, 2, 3]],
                    mat or STEEL_BLACK).finalize()


# ---------------------------------------------------------------- 組み立て
def build(feed="belt"):
    l = L
    b = l.bore_y
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "receiver", receiver() + magwell())
    add("feed_cover", "receiver", (0, l.cover_hinge[1], l.cover_hinge[0]), "feed_cover", feed_cover())
    add("feed_tray", "receiver", (0, l.cover_split, -128.0), "feed_tray", feed_tray())
    add("rail_top", "feed_cover", (0, l.cover_top + l.rail_h, l.rail_rear_z), "rail_top", rail_top())
    add("rear_sight", "feed_cover", (0, l.cover_top, l.rear_sight_z), "rear_sight", rear_sight())
    add("pistol_grip", "receiver", (0, 108, 40), "pistol_grip", pistol_grip())
    add("lower_receiver", "receiver", (0, 108, 0), "trigger_guard", trigger_guard())
    add("trigger", "root", (0, 108, 0), "trigger", trigger())
    add("stock", "root", (0, b, l.rcv_rear_z), "stock", stock())
    add("handguard", "root", (0, b, l.hg_rear_z), "handguard", handguard() + gas_system())
    add("rail_handguard", "handguard", (0, l.shield[3], l.shield[0]), "rail_handguard", rail_handguard())
    pz, py = l.bipod_pivot
    for name, s in (("bipod_leg_l", 1), ("bipod_leg_r", -1)):
        add(name, "handguard", (s * 9, py, pz), f"{name}", bipod_leg(side=s))
        a = math.radians(l.bipod_fold_deg)          # 足の付け根（たたんだ脚の上で、回転後の位置）
        d = l.bipod_len - 20
        add(name.replace("leg", "foot"), name, (s * 9, py - d * math.sin(a), pz + d * math.cos(a)), None,
            bipod_foot(side=s))
    add("barrel", "root", (0, b, l.breech_z), "barrel", barrel())
    add("chamber", "barrel", (0, b, l.breech_z), None, [])
    add("front_sight_base", "barrel", (0, b, l.fs_z[0]), "front_sight", front_sight())
    add("front_sight_post", "front_sight_base", (0, l.sight_y, sum(l.fs_z) / 2), None, front_sight_post())
    add("carry_handle", "barrel", (0, l.handle_pivot[1], l.handle_pivot[0]), "carry_handle", carry_handle())  # Z 軸まわりに回す
    add("muzzle", "root", (0, b, l.barrel_end_z), "flash_hider", flash_hider())
    add("bolt", "root", (0, b, l.breech_z + 40), None, [])

    if feed == "belt":
        add("magazin", "root", (sum(l.box_x) / 2, l.box[3], sum(l.box[:2]) / 2), "ammo_box", ammo_box())
        add("mag_ammo", "magazin", (0.0, l.feed_y, -90), "belt", belt())
    else:
        add("magazin", "root", (l.mag_pivot[0], l.mag_pivot[1], l.mag_center_z), "magazine_stanag", stanag_mag())
        add("mag_ammo", "magazin", (l.mag_pivot[0], l.mag_pivot[1], l.mag_center_z), None, [])

    tip = l.breech_z - 57.4                     # 薬室内の実包（排莢クリップの起点）
    case, bullet = ar15_parts.cartridge_556(z_tip=tip, y=b)
    add("ammo", "root", (0, b, tip + 35), None, case)
    add("bullet", "ammo", (0, b, tip + 6), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(O.GRIP["outer"]).centroid
    add_locators(m, muzzle=(0, b * K, l.muzzle_z * K), sight_line_y=l.sight_y * K,
                 rear_sight_z=l.rear_sight_z * K, grip_center=(0, c.y * K, c.x * K))
    return m, parts
