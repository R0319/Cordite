"""
Winchester Model 1912（Model 12）トレンチガン（第二次大戦の米軍型。20in 銃身・穴の開いた放熱カバー・着剣部）の
パーツと組み立て（単位 mm、メッシュ版）。

側面形は競売カタログの真横写真（右側面）からトレースした輪郭（m1912_outline.py ← trace_m1912.py）。
縮尺は全長 1003mm（20in 銃身の Model 12 の公表値）で合わせ、引き金〜床尾板の長さ 357mm（実物 13 7/8〜14in）を確かめた。
左右の幅は推定（下の HALF_*。上面図が無い）。
座標は他の銃と同じ: X=0 左右対称面（+X が左側面、-X が右側面＝排莢口の側）、Y=0 グリップの底、Z=0 トリガー、銃口 -Z。

ポンプ（先台と左右の作動桿。ボーン pump）を PUMP_TRAVEL 後ろへ引くと、ボルト（ボーン bolt）も同じだけ下がり、
右側面の排莢口が開く。弾倉は銃身の下の筒（固定。外せない）で、ボーン magazin は下面の装填口の位置。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import sights
import m1912_outline as O
from core import MeshPart, box, extrude_x_beveled, extrude_x_rounded, inflate_x, lathe, densify
from m249 import x_cyl
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
WOOD = M.M1912_WOOD
BLUED = M.M1912_BLUED

BORE_Y = 102.5
BARREL_R = 11.0             # 銃身の外径 22mm（写真の上の縁 Y 113.5）
MUZZLE_Z = -646.0
BREECH_Z = -150.0           # 銃身の後端（受け部の前の輪の後ろ）＝薬室の後端
TUBE_Y, TUBE_R = 76.5, 11.5   # 弾倉の筒（写真 Y 65〜88）
TUBE_Z = (-545.0, -150.0)

# 左右の半幅（推定）
HALF_RCV = 16.0             # 受け部 32mm
RCV_BEVEL = 4.5             # 受け部の上の角の丸み（排莢口の上の壁 5.8mm に収まる大きさ）
HALF_GUARD = 5.0
HALF_BUTT = 21.0            # 床尾 42mm
HALF_WRIST = 16.5           # グリップ 33mm

# 右側面の排莢口（写真の明るいボルトの見える窓）とボルト
PORT_Z = (-125.0, -64.0)
PORT_Y = (98.0, 111.0)      # 上の縁は側面の平らな所まで（写真では上の丸みに少し食い込んで見える）
PORT_R = 3.0                # 角の丸み
BOLT_Z = (-150.0, -53.0)    # 閉鎖時のボルト（前面＝薬室の後端）。引いても後ろの端が受け部の後端 Z 23.5 を越えない長さ
PUMP_TRAVEL = 70.0          # ポンプ・ボルトを引く量（12 番の実包 64mm を出し入れできる長さ。🟡 実測値は未確認）

# 先台（ポンプ。木の筒に 18 本の溝）
FOREND_Z = (-447.0, -268.0)
FOREND_Y, FOREND_R = 73.0, 19.5
FOREND_GROOVES = 18

# 放熱カバー（銃身の上半分を覆う穴あきの板）と着剣部
SHIELD_Z = (-549.0, -271.0)
SHIELD_R = 18.0             # 上の縁 Y 120.5
SHIELD_DOWN = 21.0          # 横の縁が水平より下へ回り込む角度（写真の下の縁 Y 96）
SHIELD_HOLE_Y = 108.5       # 横の穴の列（写真）
SHIELD_HOLES = 20           # 1 列の穴の数（写真で数えた）
SHIELD_HOLE_R = 3.4
# 照準: 受け部の上面の溝から銃口の玉（ビード）を狙う。放熱カバーの上の縁（120.5）が銃身（113.5）より高く、銃身の上の
# 実物の玉（3〜4mm）は覗くとカバーに隠れる。ゲーム向けに誇張して、着剣部の前の端に台を立てて大きな玉を載せる
# （上の端＝照準線。カバーの上に玉の上 3 分の 2 が見える）。大きさは ADS の目からの距離で決める（sights の目安）
SIGHT_Y = 125.0
BEAD_Z = -650.0
BEAD_D = sights.POST_ANGLE * 1.2 * (sights.eye_z(0.0, 20.0) - BEAD_Z)   # 丸くて光る玉が目印なので照星の 1.2 倍
SAFETY = (-42.0, 52.0)      # 安全装置（トリガーガードの前のボタン。横に押す）


# ---------------------------------------------------------------- 小道具
def _ring(q):
    return list(q.exterior.coords)[:-1]


def _poly(o):
    from shapely.geometry import Polygon
    return Polygon(o["outer"], o["holes"])


def _rounded_rect(z0, z1, y0, y1, r):
    from shapely.geometry import box as sbox
    return sbox(z0 + r, y0 + r, z1 - r, y1 - r).buffer(r, quad_segs=4)


def arc_z(cy, r_in, r_out, z0, z1, a0, a1, mat, n=24):
    """Z 方向の筒の一部（角度 a0〜a1 度、0 が +X、90 が上）。放熱カバー用。"""
    verts, faces = [], []
    angs = [math.radians(a0 + (a1 - a0) * i / n) for i in range(n + 1)]
    for z in (z0, z1):
        for r in (r_out, r_in):
            for a in angs:
                verts.append((r * math.cos(a), cy + r * math.sin(a), z))
    m = n + 1
    oz0, iz0, oz1, iz1 = 0, m, 2 * m, 3 * m
    for i in range(n):
        faces.append([oz0 + i, oz0 + i + 1, oz1 + i + 1, oz1 + i])          # 外面
        faces.append([iz0 + i + 1, iz0 + i, iz1 + i, iz1 + i + 1])          # 内面
        faces.append([oz0 + i + 1, oz0 + i, iz0 + i, iz0 + i + 1])          # 後ろの端
        faces.append([oz1 + i, oz1 + i + 1, iz1 + i + 1, iz1 + i])          # 前の端
    for e in (0, n):                                                        # 左右の縁
        faces.append([oz0 + e, iz0 + e, iz1 + e, oz1 + e] if e == 0 else [iz0 + e, oz0 + e, oz1 + e, iz1 + e])
    return MeshPart(verts, faces, mat).finalize()


# ---------------------------------------------------------------- ストック
def stock():
    """木のストック（半ピストルグリップ）と床尾板（硬いゴム）。床尾から握りへ細くなる。"""
    def width(z, y, f):
        return min(1.0, max(HALF_WRIST / HALF_BUTT, (HALF_WRIST + (HALF_BUTT - HALF_WRIST) * (z - 60.0) / 200.0)
                            / HALF_BUTT))
    from shapely.geometry import Polygon, box as sbox
    g = _poly(O.STOCK)
    wood = g.difference(sbox(348.0, -100.0, 400.0, 200.0))
    plate = g.intersection(sbox(348.0, -100.0, 400.0, 200.0))
    wood = max([q for q in getattr(wood, "geoms", [wood]) if q.geom_type == "Polygon"], key=lambda q: q.area)
    out = [inflate_x(densify(_ring(wood.simplify(0.3))), HALF_BUTT, WOOD, steps=4, width_fn=width,
                     radius_fn=lambda nz, ny: 6.0 if ny < -0.6 else 8.0, cap_grid=14.0)]   # 格子: 放射状の筋を防ぐ
    for q in [q for q in getattr(plate, "geoms", [plate]) if q.geom_type == "Polygon"]:
        out.append(extrude_x_beveled(_ring(q.simplify(0.3)), -HALF_BUTT + 2.5, HALF_BUTT - 2.5, 3.0, M.RUBBER, steps=2))
    return out


# ---------------------------------------------------------------- 受け部
def receiver_shape():
    from shapely.geometry import Polygon
    return Polygon(O.RECEIVER["outer"]).simplify(0.3)


def receiver():
    """受け部（黒染めの鋼）。上の角を大きく丸めて上面を丸くする。右側面（-X）にだけ排莢口を開けるので、
    左右を X=0 で分けて作る（右半分は排莢口を穴として抜く）。"""
    g = receiver_shape()
    port = _rounded_rect(PORT_Z[0], PORT_Z[1], PORT_Y[0], PORT_Y[1], PORT_R)
    half = lambda z, y: HALF_RCV
    out = [extrude_x_rounded(_ring(g), [], half, RCV_BEVEL, BLUED, steps=3, side=1),
           extrude_x_rounded(_ring(g), [_ring(port)], half, RCV_BEVEL, BLUED, steps=3, side=-1,
                             hole_bevel=0.8)]
    # 排莢口の奥（ボルトを引いたときに見える受け部の中。暗い面）
    out.append(box(-2.0, PORT_Y[0] - 1.0, PORT_Z[0] - 2.0, 0.5, PORT_Y[1] + 1.0, PORT_Z[1] + 2.0, M.BORE))
    return out


# トリガーガードとトリガーの中心線と半幅 (Z, Y, r)。写真では内側が光って輪郭が途切れるので、細かい目盛りを重ねて読んだ
GUARD_PATH = [(5.0, 57.5, 1.8), (5.8, 50.0, 1.6), (5.5, 43.0, 1.6), (4.0, 38.5, 1.6), (1.0, 35.5, 1.5), (-4.0, 33.8, 1.4),
              (-15.0, 33.2, 1.4), (-28.0, 33.4, 1.4), (-36.0, 35.0, 1.5), (-41.0, 38.5, 1.7), (-43.2, 44.0, 1.9),
              (-43.5, 49.5, 2.1), (-43.0, 57.5, 2.6)]
TRIGGER_PATH = [(-4.5, 58.0, 1.8), (-3.0, 52.0, 1.3), (-1.0, 47.5, 1.1), (0.3, 43.0, 1.0), (-0.3, 39.5, 0.9),
                (-1.8, 36.5, 0.8)]


def trigger_guard():
    """トリガーガード（底の平らな輪。前の脚の上に安全装置のボタン）と、受け部の下に沿う板（写真の Y 55〜59.5）。"""
    from m24 import _stroke
    plate = [(12.0, 59.6), (12.0, 57.0), (8.0, 55.0), (-50.0, 55.0), (-53.0, 57.0), (-53.0, 59.6)]
    return [extrude_x_beveled(_stroke(GUARD_PATH), -HALF_GUARD, HALF_GUARD, 0.8, BLUED, steps=1),
            extrude_x_beveled(plate, -HALF_GUARD - 1.5, HALF_GUARD + 1.5, 1.0, BLUED, steps=1)]


def trigger():
    """トリガー（ガードの後ろ寄りの細く湾曲した刃。根元は受け部の中）。"""
    from m24 import _stroke
    return [extrude_x_beveled(_stroke(TRIGGER_PATH), -3.5, 3.5, 0.5, BLUED, steps=1)]


def safety():
    """安全装置（トリガーガードの前の横押しボタン）。"""
    z, y = SAFETY
    return [x_cyl(z, y, 3.2, -HALF_GUARD - 1.5, HALF_GUARD + 1.5, M.M1912_STEEL, n=10)]


def bolt():
    """ボルト（排莢口から見える明るい鋼の板）。ポンプと一緒に PUMP_TRAVEL 下がる。排莢口から 2mm 奥。
    受け部の上面は後ろへ下がっていくので、ボルトの後ろの上を斜めに落とす（引いたときに上面から突き出ない）。"""
    z0, z1 = BOLT_Z
    y0, y1 = PORT_Y[0] - 0.5, PORT_Y[1]
    prof = [(z0, y0), (z1, y0), (z1, 101.0), (z1 - 22.0, y1), (z0, y1)]
    return [extrude_x_beveled(prof, -HALF_RCV + 2.0, HALF_RCV - 4.0, 0.6, M.M1912_BOLT, steps=1)]


# ---------------------------------------------------------------- 銃身まわり
def barrel():
    """銃身・受け部の前の輪・弾倉の筒・放熱カバー・着剣部（分解すると一体で外れる組）。"""
    out = [lathe(0, BORE_Y, [(MUZZLE_Z, 9.3), (MUZZLE_Z, BARREL_R - 0.6), (MUZZLE_Z + 60.0, BARREL_R - 0.5),
                             (BREECH_Z - 20.0, BARREL_R), (BREECH_Z, BARREL_R)], ar15_mesh.N_MID, BLUED, cap0=False),
           lathe(0, BORE_Y, [(MUZZLE_Z - 0.2, 9.2), (MUZZLE_Z + 30.0, 9.2)], ar15_mesh.N_SMALL, M.BORE, cap0=False)]
    from shapely.geometry import Polygon
    col = Polygon(O.COLLAR["outer"]).simplify(0.3)
    out.append(extrude_x_beveled(_ring(col), -HALF_RCV + 0.5, HALF_RCV - 0.5, 4.0, BLUED, steps=2))
    t0, t1 = TUBE_Z
    out.append(lathe(0, TUBE_Y, [(t0, TUBE_R + 0.5), (t0 + 7.0, TUBE_R + 0.5), (t0 + 7.0, TUBE_R), (t1, TUBE_R)],
                     ar15_mesh.N_MID, BLUED))
    out += heat_shield() + adapter()
    return out


def heat_shield():
    """放熱カバー: 銃身の上半分を覆う板（横の縁は水平より SHIELD_DOWN 下まで回る）と、横の穴の列（暗い円）。"""
    z0, z1 = SHIELD_Z
    out = [arc_z(BORE_Y, SHIELD_R - 1.2, SHIELD_R, z0, z1, -SHIELD_DOWN, 180.0 + SHIELD_DOWN, BLUED, n=24)]
    dy = SHIELD_HOLE_Y - BORE_Y
    xs = math.sqrt(SHIELD_R ** 2 - dy ** 2)
    pitch = (z1 - z0 - 24.0) / (SHIELD_HOLES - 1)
    for i in range(SHIELD_HOLES):
        z = z1 - 12.0 - i * pitch
        for s in (1, -1):
            xa, xb = sorted((s * (xs - 1.0), s * (xs + 0.25)))
            out.append(x_cyl(z, SHIELD_HOLE_Y, SHIELD_HOLE_R, xa, xb, M.BORE, n=8))
    return out


# 着剣部（作者の指摘「M1912 のモデルを見直して」。競売カタログの写真を 3 倍に拡大して読んだ。Z, Y）: 銃身を包む筒、
# その下の薄い板（ねじ 3 本。下の縁は大きな弧に抜け、前は鉤になって下がる）、前の下の着剣の突起、後ろで弾倉の筒の
# 先を抱く留め具と、その下の板・負い紐の輪。それまではトレースの輪郭を幅 25mm の塊にしていて、金槌の頭のように見えた
ADAPTER_Z = (-549.0, -649.0)     # 筒（放熱カバーの前から銃口まで）
ADAPTER_SLEEVE_R = 12.0          # 筒の半径（写真の上の縁 Y 114.3）
ADAPTER_PLATE = [(-553.0, 101.0), (-649.0, 101.0), (-649.0, 86.0), (-645.5, 80.0), (-642.6, 72.8), (-639.5, 72.5),
                 (-637.5, 78.0), (-630.0, 86.9), (-611.0, 89.3), (-586.0, 90.1), (-576.0, 86.5), (-572.0, 82.0),
                 (-572.0, 80.0), (-553.0, 80.0)]
ADAPTER_PLATE_HALF = 5.0
ADAPTER_SCREWS = (-564.3, -602.7, -640.2)   # Y 91.6
ADAPTER_LUG = (-643.0, -657.4, 79.0, 5.0)   # 着剣の突起（前後 z, 中心 y, 半径）
ADAPTER_CLAMP_Z = (-553.0, -572.0)          # 弾倉の筒の先を抱く留め具
ADAPTER_TAB = (-551.0, -569.0, 48.6)        # 留め具の下の板（下の端 y）


def adapter():
    """着剣部（銃口と弾倉の筒の先をまとめて留める金具）。上の説明の部品と、照準の玉。"""
    z0, z1 = ADAPTER_Z
    out = [lathe(0, BORE_Y, [(z1, ADAPTER_SLEEVE_R - 1.5), (z1 + 1.5, ADAPTER_SLEEVE_R), (z0, ADAPTER_SLEEVE_R)],
                 ar15_mesh.N_MID, BLUED)]
    h = ADAPTER_PLATE_HALF
    out.append(extrude_x_beveled(ADAPTER_PLATE, -h, h, 1.2, BLUED, steps=1))
    for z in ADAPTER_SCREWS:
        for s_ in (1, -1):
            xa, xb = sorted((s_ * (h - 0.3), s_ * (h + 0.7)))
            out.append(x_cyl(z, 91.6, 2.6, xa, xb, M.M1912_STEEL, n=10))
    lz0, lz1, ly, lr = ADAPTER_LUG
    out.append(lathe(0, ly, [(lz1, lr - 1.0), (lz1 + 1.0, lr), (lz0, lr)], ar15_mesh.N_SMALL, BLUED))
    cz0, cz1 = ADAPTER_CLAMP_Z
    out.append(lathe(0, TUBE_Y, [(cz1, TUBE_R + 2.0), (cz0, TUBE_R + 2.0)], ar15_mesh.N_MID, BLUED))
    tz0, tz1, ty = ADAPTER_TAB
    out.append(extrude_x_beveled([(tz0, ty + 3.0), (tz0, TUBE_Y - 5.0), (tz1, TUBE_Y - 5.0), (tz1, ty + 3.0),
                                  (tz1 + 2.0, ty), (tz0 - 2.0, ty)], -h, h, 1.0, BLUED, steps=1))
    # 負い紐の輪（横に寝た針金の輪。側面からは細長く見える）
    for xa, xb in ((-8.0, -6.0), (6.0, 8.0)):
        out.append(box(xa, 65.0, -591.0, xb, 68.0, -560.0, M.M1912_STEEL))
    out.append(box(-8.0, 65.0, -593.0, 8.0, 68.0, -589.0, M.M1912_STEEL))
    # 照準の玉（誇張。筒の前の端の上に台を立てて載せる）
    r = BEAD_D / 2
    out += [box(-1.5, BORE_Y + ADAPTER_SLEEVE_R - 1.0, BEAD_Z - 1.5, 1.5, SIGHT_Y - r, BEAD_Z + 1.5, BLUED),
            lathe(0, SIGHT_Y - r, [(BEAD_Z - r, 0.01), (BEAD_Z - r * 0.7, r * 0.7), (BEAD_Z, r),
                                   (BEAD_Z + r * 0.7, r * 0.7), (BEAD_Z + r, 0.01)], 10, M.BRASS)]
    return out


# ---------------------------------------------------------------- ポンプ
def pump():
    """先台（木の筒に 18 本の溝。ボーン pump）と左右の作動桿（先台から受け部へ伸びる）。"""
    z0, z1 = FOREND_Z
    r = FOREND_R
    prof = [(z0, r - 5.0), (z0 + 2.5, r - 1.5), (z0 + 7.0, r)]
    pitch = (z1 - z0 - 22.0) / FOREND_GROOVES
    for i in range(FOREND_GROOVES):
        zc = z0 + 12.0 + (i + 0.5) * pitch
        prof += [(zc - 2.4, r), (zc - 1.2, r - 2.6), (zc + 1.2, r - 2.6), (zc + 2.4, r)]   # 写真の深い溝
    prof += [(z1 - 6.0, r), (z1 - 2.0, r - 1.5), (z1, r - 4.0)]
    out = [lathe(0, FOREND_Y, prof, ar15_mesh.N_MID, WOOD)]
    for s in (1, -1):
        xa, xb = sorted((s * 7.5, s * 10.0))
        # 上は 92 まで（写真ではポンプと受け部の間は銃身の下まで暗く、隙間が見えない。90 だと 1.5mm 抜けて見えた。
        # X 7.5〜10 では銃身の下の面は Y 95.8 なので食い込まない）
        out.append(box(xa, 86.0, z1 - 2.0, xb, 92.0, BREECH_Z - 5.0, M.M1912_STEEL))
    return out


# ---------------------------------------------------------------- 実包
def shell_12ga(z_head, y, x=0.0, mat=None):
    """12 番 2 3/4in 実包（第二次大戦の米軍の真鍮の薬莢 M19）: 全長 64mm、縁 22.4mm、胴 20.6mm。後ろ（縁）が z_head。"""
    mat = mat or M.BRASS
    prof = [(z_head - 64.0, 9.6), (z_head - 63.0, 10.3), (z_head - 1.5, 10.3), (z_head - 1.5, 11.2), (z_head, 11.2)]
    return [lathe(x, y, prof, ar15_mesh.N_SMALL, mat)]


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
    add("lower_receiver", "receiver", (0, 57.0, 0), "trigger_guard", trigger_guard())
    add("selector", "lower_receiver", (0, SAFETY[1], SAFETY[0]), "safety", safety())
    add("trigger", "root", (0, 57.0, 5.0), "trigger", trigger())
    add("stock", "root", (0, 60.0, 150.0), "stock", stock())

    add("barrel", "root", (0, b, BREECH_Z), "barrel", barrel())
    add("chamber", "barrel", (0, b, BREECH_Z), None, [])
    add("muzzle", "root", (0, b, MUZZLE_Z), None, [])
    add("handguard", "root", (0, FOREND_Y, sum(FOREND_Z) / 2), None, [])
    add("rail_top", "root", (0, 118.0, -60.0), None, [])               # レールは無い（受け部の上。位置だけ）
    add("rail_bottom", "root", (0, FOREND_Y - FOREND_R, sum(FOREND_Z) / 2), None, [])
    add("rail_side", "root", (SHIELD_R, b, -420.0), None, [])

    add("pump", "root", (0, FOREND_Y, FOREND_Z[1]), "pump", pump())
    add("bolt", "root", (0, b, BOLT_Z[1]), "bolt", bolt())

    # 弾倉は固定の筒。magazin は下面の装填口（受け部の下）の位置、mag_ammo は装填口に入れる 1 発
    add("magazin", "root", (0, TUBE_Y, BREECH_Z + 40.0), None, [])
    add("mag_ammo", "magazin", (0, TUBE_Y, BREECH_Z + 40.0), None, shell_12ga(BREECH_Z + 64.0 + 4.0, TUBE_Y))

    case = shell_12ga(BREECH_Z, b)                            # 薬室の中（縁が銃身の後端）
    add("ammo", "root", (0, b, BREECH_Z - 32.0), None, case)
    add("bullet", "ammo", (0, b, BREECH_Z - 60.0), None, [])     # 散弾は描かない（位置だけ）

    add_locators(m, muzzle=(0, b * K, MUZZLE_Z * K), sight_line_y=SIGHT_Y * K,
                 rear_sight_z=20.0 * K, grip_center=(0, 30.0 * K, 45.0 * K), support_z=-300.0 * K)
    return m, parts
