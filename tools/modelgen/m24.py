"""
M24 SWS（Remington 700 ロングアクション・H-S Precision PST-024 ストック）のパーツと組み立て（単位 mm、メッシュ版）。

側面形は Wikimedia Commons の真横写真（右側面。パブリックドメイン）からトレースした輪郭（m24_outline.py ← trace_m24.py）。
縮尺は銃身の見えている長さで合わせ、全長（ストックを縮めた状態 1091mm）が公表値 1092mm と一致することを確かめた。
左右の幅は公表寸法・一般的な寸法からの推定（下の HALF_* と RCV_R。上面図が無いため）。
スコープはアタッチメント扱いなので含めない（受け部の上にスコープの台＝レールだけ付ける）。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝ボルトハンドル・排莢口の側）、Y=0 グリップ底面、
Z=0 トリガー、銃口 -Z。

ボルトの動き（アニメーション用）: ボーン charging_handle（ボルト本体とハンドル）を銃身の軸まわりに 60° 起こし、
ボーン bolt（ボルトの後ろの覆いを含む全体）を後ろへ BOLT_TRAVEL 引く。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import sights
import m24_outline as O
from core import Model, box, extrude_x, extrude_x_beveled, inflate_x, lathe, densify
from m249 import outline_parts, rotated, x_cyl
from mp5 import extrude_z
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
STOCK_MAT = M.M24_STOCK
STEEL_BLACK = M.M24_STEEL
BOLT_MAT = M.M24_BOLT

BORE_Y = 112.8
MUZZLE_Z = -792.6
RCV_FRONT_Z = -201.0     # 受け部の前の輪の前端（銃身との境。写真）
RCV_REAR_Z = -20.0       # 受け部の後端（ボルトの覆いの前。写真）
RCV_R = 16.0             # 受け部の半径（M700 の受け部は丸い筒。外径 1.36in を、写真の上端に合わせて少し小さく）
BOLT_R = 8.85            # ボルトの半径（.697in）
BOLT_FACE_Z = -176.0     # ボルトの前面（薬室の後端）
BOLT_TRAVEL = 105.0      # ボルトを引く量（🟡 ロングアクションの値は未確認。弾を出し入れできる長さ）
PORT_Z = (-160.0, -76.0)  # 右側面の排莢口（写真の暗い窓）
PORT_Y = (106.0, 118.0)  # 下の縁はストックの縁（写真）
HANDLE_ROOT_Z = -30.0    # ボルトハンドルの付け根（写真）
KNOB = (-27.0, 79.0, -15.0)   # ハンドルの玉の中心（X, Y, Z）。Y・Z は写真、X は推定
SAFETY_Z = -8.6          # 安全装置のレバーの頭（右側面、ボルトの覆いの横・ハンドルのすぐ後ろ。写真に目盛りを重ねて読んだ。
                         # 以前は 8.0 で覆いの後ろの空中に浮いていた）。M700 は 2 位置の安全装置
SAFETY_HEAD_Y = 112.0    # レバーの頭（丸いつまみ）の中心の高さ（写真）

# ストックの左右の半幅（H-S PST-024。🟡 推定）
HALF_FOREND = 24.0       # 先台 48mm（ベンチレストに置ける平らで幅広の先台）
HALF_GRIP = 16.0         # グリップ 32mm
HALF_BUTT = 21.0         # 床尾 42mm
HALF_PAD = 23.0          # 床尾板 46mm
STOCK_H = 14.0           # ストックを膨らませる量（丸みの半径の上限）


def _lerp(a, b, t):
    t = min(1.0, max(0.0, t))
    return a + (b - a) * t


# ---------------------------------------------------------------- ストック
def stock():
    """H-S PST-024 ストック（樹脂。表面はざらついた塗装）。側面形はトレース。幅は先台→グリップ→床尾で変える。"""
    def width(z, y, f):
        w = _lerp(HALF_FOREND, 18.0, (z + 60.0) / 90.0)               # 先台（-60 より前）→ 受け部の後ろ
        if z > 30.0:
            w = _lerp(18.0, HALF_BUTT, (z - 100.0) / 60.0)            # 握りの上 → 床尾
        if -10.0 < z < 125.0 and y < 85.0:
            w = min(w, _lerp(HALF_GRIP, 18.0, (y - 60.0) / 25.0))     # グリップ
        return w / STOCK_H

    def radius(nz, ny):
        if ny > 0.6:
            return 4.0           # 上の面（受け部が載る・頬を当てる）は平らな帯を残す
        if ny < -0.5:
            return STOCK_H       # 先台・グリップの下は丸い
        return 7.0
    # 膨らませる量 STOCK_H は側面形の一番薄い所（先台の先 約 40mm）の半分より小さくする（大きいと形が潰れる）。
    # 実際の幅は width_fn の倍率で出す
    # cap_grid: 幅が場所ごとに変わる平らな面を格子で分ける（扇形の細長い三角形だと放射状の筋に見えた）
    return [inflate_x(densify(O.STOCK["outer"]), STOCK_H, STOCK_MAT, steps=4, width_fn=width, radius_fn=radius, cap_grid=14.0)]


def butt():
    """床尾板（ゴム）と、長さ調整の 2 本の棒・調整ノブ（写真: 床尾板を約 45mm 伸ばした状態）。"""
    out = [extrude_x_beveled(O.BUTT_PAD["outer"], -HALF_PAD, HALF_PAD, 6.0, M.RUBBER, steps=2)]
    z0, z1 = 268.0, 314.0
    # 寸法は写真の明るさの段で読んだ（棒の太さ 11mm、下の棒の中心 10.5、ねじの中心 42、ノブは前が太い）
    for y in (75.3, 10.5):                                                # 上下 2 本の棒
        out.append(lathe(0, y, [(z0, 5.5), (z1, 5.5)], ar15_mesh.N_SMALL, STEEL_BLACK))
    out.append(lathe(0, 42.0, [(z0, 5.0), (z1, 5.0)], ar15_mesh.N_SMALL, STEEL_BLACK))   # 調整ねじ
    out.append(lathe(0, 44.0, [(274.0, 24.0), (285.0, 24.0), (291.0, 18.0)], 16, STEEL_BLACK))   # 調整ノブ（刻みはテクスチャ）
    return out


# ---------------------------------------------------------------- 受け部・銃身
def _rcv_section(port=False, n=28):
    """受け部の断面（丸）。port=True で右側面に排莢口の窓。受け部は中まで詰まった形なので、窓は銃身の軸の向こうまで
    深く切り欠き、中のボルト（明るい鋼）が見えるようにする（ボルトの表面の位置で止めると、窓の奥の面が受け部の黒い
    面になってボルトを隠していた）。"""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = RCV_R * math.cos(a), BORE_Y + RCV_R * math.sin(a)
        if port and x < 0 and PORT_Y[0] < y < PORT_Y[1]:
            continue
        pts.append((x, y))
    if port:
        # 窓の上の縁 → ボルトの表面 → 窓の下の縁（断面の点の並びは反時計回り: 右側は上から下へ）
        top = (-math.sqrt(RCV_R ** 2 - (PORT_Y[1] - BORE_Y) ** 2), PORT_Y[1])
        bot = (-math.sqrt(RCV_R ** 2 - (PORT_Y[0] - BORE_Y) ** 2), PORT_Y[0])
        inner = 3.0                                  # 軸の向こう 3mm まで
        i = next(j for j, p in enumerate(pts) if p[0] < 0 and p[1] < PORT_Y[0])
        pts[i:i] = [top, (inner, PORT_Y[1]), (inner, PORT_Y[0]), bot]
    return pts


def receiver():
    """受け部（丸い筒）。右側面に排莢口。前の輪の前に銃身の付け根（太い段）。"""
    pz0, pz1 = PORT_Z
    out = [extrude_z(_rcv_section(), RCV_FRONT_Z, pz0, STEEL_BLACK),
           extrude_z(_rcv_section(port=True), pz0, pz1, STEEL_BLACK),
           extrude_z(_rcv_section(), pz1, RCV_REAR_Z, STEEL_BLACK)]
    # 安全装置（右側面の後ろ、覆いの下の小さなレバー）は selector ボーン
    return out


# 照準器（作者の指示「M24 はアイアンサイト見直し」で、折りたたみ式から実物の M24 の照準器に替えた）:
# 銃口の照星の台（写真のトレース O.FRONT_SIGHT。上面 Y 132.6）にフード付きの照星（輪の中に柱）、スコープの後ろの
# 台座に穴の照門（後ろに目当ての円盤）。どちらも見やすさのために実物より大きい（sights の目安。照星までが遠いので
# 柱は目安の 8 割にして、フードを太らせすぎない）
IRON_REAR_Z = -45.0              # 照門の板（スコープの後ろの台座の上）
IRON_FRONT_Z = -757.0            # 照星の柱（銃口の台の中央）
FRONT_HOOD = (-770.0, -745.0, 11.0, 14.0)   # フードの前後・内半径・外半径
SIGHT_Y = 132.6 + 14.0 + 1.0     # 照準線＝フードの中心（台の上面にフードの外側が 1mm 食い込む）


def irons():
    """M24 の照準器（ボーン iron_sight。スコープを付けるとコードが描かない）。"""
    from m249 import ring_z, x_cyl, y_cyl
    sy = SIGHT_Y
    eye = sights.eye_z(0.0, IRON_REAR_Z)
    hole = min(sights.BUIS_HOLE_MAX, sights.HOLE_ANGLE * (eye - IRON_REAR_Z))
    post_w = 0.8 * sights.POST_ANGLE * (eye - IRON_FRONT_Z)
    # 照門: 台座を挟むクランプ・穴の板・後ろの目当て（円盤）・右の風偏つまみ・上の高低つまみ
    zr = IRON_REAR_Z
    out = [box(-10.0, 132.0, zr - 9.0, 10.0, 137.0, zr + 9.0, STEEL_BLACK)]
    out += sights.aperture_plate(sy, zr - 2.5, zr + 2.5, hole, 136.0, STEEL_BLACK, half_w=7.0, ears=False)
    out.append(ring_z(sy, zr + 2.5, zr + 6.0, hole / 2, hole / 2 + 7.5, STEEL_BLACK))
    out.append(x_cyl(zr, sy - 7.0, 3.0, -14.0, -7.0, STEEL_BLACK, n=10))
    out.append(y_cyl(0.0, zr - 5.5, 3.0, sy + hole / 2 + 2.0, sy + hole / 2 + 7.0, STEEL_BLACK, n=10))
    # 照星: 台に載る輪のフードと、中の柱（先端＝照準線）
    z0, z1, r_in, r_out = FRONT_HOOD
    out.append(ring_z(sy, z0, z1, r_in, r_out, STEEL_BLACK))
    out.append(box(-6.0, 131.5, z0 + 3.0, 6.0, sy - r_in + 0.5, z1 - 3.0, STEEL_BLACK))
    out.append(sights.post(post_w, sy - r_in - 0.5, sy, IRON_FRONT_Z, STEEL_BLACK, depth=3.0))
    return out, sy


def scope_base():
    """スコープの台（受け部の上の一体のレール。写真: 後ろと前の台座が高く、間が低い）。輪はスコープ側（アタッチメント）。"""
    y = BORE_Y + RCV_R - 2.5
    return [box(-9.0, y, -205.0, 9.0, 129.0, -26.0, STEEL_BLACK),
            box(-9.0, 129.0, -75.0, 9.0, 133.5, -26.0, STEEL_BLACK),
            box(-9.0, 129.0, -205.0, 9.0, 133.0, -160.0, STEEL_BLACK)]


def barrel():
    """銃身（ヘビーバレル）: 先台の中は写真の上の縁に合わせた太さ、先台より前はトレースの太さの分布。銃口に照星の台。"""
    prof = sorted(O.BARREL_R)                                  # Z 昇順（銃口側から）
    out = [lathe(0, BORE_Y, [(MUZZLE_Z, 4.0), (MUZZLE_Z, prof[0][1])] + prof + [(-505.0, 12.7), (RCV_FRONT_Z + 1.0, 12.7)],
                 ar15_mesh.N_MID, STEEL_BLACK, cap0=False),
           lathe(0, BORE_Y, [(MUZZLE_Z - 0.2, 3.9), (MUZZLE_Z + 25.0, 3.9)], ar15_mesh.N_SMALL, M.BORE, cap0=False)]
    out += [extrude_x_beveled(O.FRONT_SIGHT["outer"], -6.0, 6.0, 1.0, STEEL_BLACK, steps=1)]
    return out


# ---------------------------------------------------------------- ボルト
def bolt_shroud():
    """ボルトの後ろの覆い（ボルトと一緒に前後するが回らない）。側面形はトレース。"""
    return [inflate_x(O.BOLT_SHROUD["outer"], 8.0, STEEL_BLACK, steps=3)]


def bolt_body():
    """ボルト本体（排莢口から見える明るい鋼の筒）とボルトハンドル。銃身の軸まわりに回る（ボーン charging_handle）。"""
    out = [lathe(0, BORE_Y, [(BOLT_FACE_Z, BOLT_R), (RCV_REAR_Z + 2.0, BOLT_R)], ar15_mesh.N_MID, BOLT_MAT),
           lathe(0, BORE_Y, [(BOLT_FACE_Z - 0.3, 3.0), (BOLT_FACE_Z + 1.0, 3.0)], 8, M.BORE)]   # 撃針の穴
    # ハンドル: 付け根（受け部の後端の切り欠きに収まる）→ 下へ曲がる腕 → 玉
    kx, ky, kz = KNOB
    zr = HANDLE_ROOT_Z
    # 付け根と腕は黒染め（写真）。ボルト本体だけが明るい鋼
    out.append(box(-RCV_R - 2.0, BORE_Y - 3.0, zr - 5.0, -BOLT_R + 1.0, BORE_Y + 6.0, zr + 5.0, STEEL_BLACK))
    arm = [(zr - 4.0, BORE_Y + 4.0), (zr + 4.0, BORE_Y + 4.0), (kz + 4.0, ky + 4.0), (kz - 4.0, ky + 2.0)]
    out.append(extrude_x_beveled(arm, kx + 1.0, -RCV_R - 1.0, 1.2, STEEL_BLACK, steps=1))
    out.append(lathe(kx, ky, [(kz - 9.0, 0.5), (kz - 7.0, 6.0), (kz - 3.0, 8.7), (kz + 3.0, 8.7), (kz + 7.0, 6.0),
                              (kz + 9.0, 0.5)], ar15_mesh.N_MID, STOCK_MAT))      # 玉（樹脂のノブ）
    return out


def safety():
    """安全装置のレバー（ボーン selector。右側面の後ろ。前＝発射、後ろ＝安全の 2 位置）。"""
    # 台（引き金の機構の側面。ストックの上の縁に埋まる）→ レバー → 丸い頭。覆い（半幅 8mm）の右に沿う
    return [box(-11.0, 101.0, SAFETY_Z - 5.5, -8.2, 107.0, SAFETY_Z + 5.0, STEEL_BLACK),
            box(-11.5, 104.0, SAFETY_Z - 2.0, -8.6, SAFETY_HEAD_Y, SAFETY_Z + 2.0, STEEL_BLACK),
            x_cyl(SAFETY_Z, SAFETY_HEAD_Y, 3.5, -12.0, -8.6, STEEL_BLACK, n=10)]


# ---------------------------------------------------------------- 引き金まわり・弾倉
# トリガーガードとトリガーの中心線と半幅 (Z, Y, r)。写真の暗い画素の幅を行ごと・列ごとに読んだ（半値幅）。
# 銀色に光って薄くしか写らないガードの底は、灰色の帯の中心を読んだ。細すぎる所は見える太さとして半幅 1.0 以上にする。
# ガードは後ろの脚が細く、前の脚はストックへ向けて末広がり（前の幅が広い Remington 700 のガード）。
# 底は Y 25.6 でほぼ平ら、前の下の角の内側に弾倉の底板の留め金（ボーン mag_release）がある
GUARD_PATH = [(5.6, 57.5, 3.4), (3.2, 53.0, 4.2), (3.4, 50.0, 2.4), (4.1, 46.0, 1.2), (4.4, 41.0, 1.2), (3.8, 36.0, 1.1),
              (2.6, 33.5, 1.1), (0.8, 31.0, 1.1), (-2.0, 28.8, 1.1), (-5.5, 27.2, 1.1), (-9.5, 26.2, 1.2),
              (-14.0, 25.8, 1.3), (-20.0, 25.6, 1.3), (-26.0, 25.9, 1.3), (-32.0, 26.5, 1.3), (-36.0, 27.5, 1.4),
              (-40.0, 29.0, 1.6), (-44.0, 31.2, 1.8), (-47.0, 34.0, 2.0), (-49.0, 37.5, 2.1), (-50.3, 41.0, 2.2),
              (-51.0, 45.0, 2.4), (-51.1, 48.0, 3.3), (-51.0, 50.5, 4.4), (-50.5, 53.0, 5.6), (-50.5, 57.5, 7.5)]
# トリガーは根元（ストックの中）が太く、すぐ細い刃になって後ろへ膨らみ、先が前へ戻る
TRIGGER_PATH = [(-10.5, 58.0, 2.6), (-8.8, 53.5, 2.0), (-6.5, 50.5, 1.2), (-4.7, 47.5, 1.0), (-3.7, 44.0, 1.0),
                (-3.7, 40.5, 1.0), (-4.4, 37.5, 1.0), (-5.5, 35.5, 0.9)]
FLOORPLATE_LATCH = (-41.0, 31.0)   # 留め金の中心（写真の暗い突起 Z -37.5〜-44、Y 28.5〜33.5）


def _stroke(path, quad_segs=6):
    """中心線 (Z, Y, 半幅) を、太さの変わる帯（側面形）にする。隣り合う 2 点の円の凸包をつなぐ。"""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    circles = [Point(z, y).buffer(r, quad_segs=quad_segs) for z, y, r in path]
    g = unary_union([circles[i].union(circles[i + 1]).convex_hull for i in range(len(circles) - 1)])
    return list(g.simplify(0.12).exterior.coords)[:-1]


def trigger_guard():
    """トリガーガード（底の平らな輪。前の脚が末広がり）。写真では銀色に光って輪郭が途切れるので、
    読んだ中心線と半幅の帯にする。以前は角張った台形で、写真の丸い輪と違っていた（作者の指摘「トリガーがおかしい」）。"""
    return [extrude_x_beveled(_stroke(GUARD_PATH), -5.0, 5.0, 0.5, STEEL_BLACK, steps=1)]


def floorplate_latch():
    """弾倉の底板の留め金（ボーン mag_release。ガードの前の下の角の内側の突起。押すと底板が開く）。"""
    z, y = FLOORPLATE_LATCH
    return [extrude_x_beveled(_stroke([(z + 1.5, y, 2.4), (z - 1.5, y - 0.5, 2.4)]), -3.0, 3.0, 0.5, STEEL_BLACK,
                              steps=1)]


def trigger():
    """トリガー（ストックの下から垂れる、細く湾曲した刃。写真: 根元 Z -10 から後ろへ膨らみ、先は前へ戻る）。
    以前はほぼまっすぐの短い板だった。"""
    return [extrude_x_beveled(_stroke(TRIGGER_PATH), -3.5, 3.5, 0.4, STEEL_BLACK, steps=1)]


def floorplate():
    """内蔵弾倉の底板（ボーン magazin。前の蝶番で開いて弾を抜く）。写真のストックの下の金属の帯。"""
    # 下の面はストックの下の縁と同じ傾き（写真: 後ろ Y 54.4 → 前 60.2。水平の箱では前で 4.5mm はみ出した）。上はストックに埋める
    return [extrude_x_beveled([(-55.0, 54.4), (-150.0, 60.4), (-150.0, 64.0), (-55.0, 58.0)], -13.0, 13.0, 0.8,
                              STEEL_BLACK, steps=1)]


def cartridge_308(z_tip, y, x=0.0):
    """7.62×51mm 実包（回転体）: 全長 71mm、薬莢 51mm。"""
    b = z_tip + 71.0
    case = [(b, 5.95), (b - 1.3, 5.95), (b - 1.6, 5.2), (b - 2.8, 5.2), (b - 3.2, 5.9), (b - 39.0, 5.75),
            (b - 43.5, 4.4), (b - 51.0, 4.35)]
    bullet = [(b - 51.0, 3.9), (b - 57.0, 3.85), (b - 64.0, 2.8), (b - 69.0, 1.2), (z_tip, 0.4)]
    return ([lathe(x, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(x, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


def magazine_rounds():
    """内蔵弾倉の中の弾（mag_ammo）: 上の 2 発を互い違いに。ボルトを引くと排莢口の下の縁から一番上の弾が見える。"""
    out = []
    # 一番上の弾は、頭が Y 108.5（ストックの縁 106 の上）まで来る高さ。閉鎖時はボルトの断面の中に収まって隠れ
    # （弾の右端がボルトの表面より内側になる X に置く）、ボルトを引くと排莢口の下の縁から頭が覗く
    y_top = 108.5 - 5.95
    for x, y in ((-0.8, y_top), (5.0, y_top - 10.0)):
        case, bullet = cartridge_308(BOLT_FACE_Z + 12.0, y, x)
        out += case + bullet
    return out


# ---------------------------------------------------------------- 組み立て
def build():
    b = BORE_Y
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "receiver", receiver() + scope_base())
    add("selector", "receiver", (-10.0, 104.0, SAFETY_Z), "safety", safety())
    add("lower_receiver", "receiver", (0, 58.0, 0), "trigger_guard", trigger_guard())
    add("trigger", "root", (0, 58.0, 0), "trigger", trigger())
    add("mag_release", "lower_receiver", (0, FLOORPLATE_LATCH[1], FLOORPLATE_LATCH[0] - 3.0), "floorplate_latch",
        floorplate_latch())
    add("stock", "root", (0, b, 0), "stock", stock())
    add("butt", "stock", (0, 45.0, 276.0), "butt", butt())          # 床尾（長さ調整で前後させる）

    add("barrel", "root", (0, b, BOLT_FACE_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BOLT_FACE_Z), None, [])
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])
    add("handguard", "root", (0, b, -350.0), None, [])
    add("rail_top", "root", (0, 133.5, -26.0), None, [])               # スコープはここに付く（アタッチメント）
    iron, sight_y = irons()
    add("iron_sight", "root", (0, 133.5, IRON_REAR_Z), "iron_sight", iron)
    add("rail_bottom", "root", (0, 66.0, -450.0), None, [])            # 先台の下の吊り輪の台座（二脚）
    add("rail_side", "root", (HALF_FOREND, 95.0, -350.0), None, [])

    add("bolt", "root", (0, b, BOLT_FACE_Z + 40.0), "bolt_shroud", bolt_shroud())
    add("charging_handle", "bolt", (0, b, HANDLE_ROOT_Z), "bolt_body", bolt_body())   # 銃身の軸まわりに起こす

    add("magazin", "root", (0, 57.0, -150.0), "floorplate", floorplate())            # 前の蝶番で開く
    add("mag_ammo", "magazin", (0, b - 15.0, -120.0), None, magazine_rounds())

    tip = BOLT_FACE_Z - 71.0
    case, bullet = cartridge_308(tip, b)
    add("ammo", "root", (0, b, tip + 50.0), None, case)
    add("bullet", "ammo", (0, b, tip + 8.0), None, bullet)

    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=sight_y * K,
                 rear_sight_z=IRON_REAR_Z * K, grip_center=(0, 48.0 * K, 66.0 * K), support_z=-288.0 * K)
    return m, parts
