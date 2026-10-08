"""
AR-15 系パーツライブラリのメッシュ版（単位 mm）。ar15_parts を土台に、丸・斜面・曲線の部品だけを
メッシュ（poly_mesh）へ置き換える。角張った部品（レシーバー・レール・サイト等）はキューブのまま流用する。

メッシュは Blockbench の Meshy プラグインが書き出す poly_mesh と同じ形で出力される（core.py 冒頭参照）。
"""
import math

from ar15_parts import *  # noqa: F401,F403  角張った部品・Layout・寸法定数はそのまま使う
from ar15_parts import (L, MAG_ANGLE, RAS_FLAT, _ras_rail, grip_outline, ear_outlines, guard_bar_outline, trigger_outline,
                        lower_common as _lower_common, lower_rear_outline, ref_zy, REF_LOWER_REAR, magwell_outline)
from core import MeshPart, box, lathe, extrude_x, extrude_x_beveled, inflate_x
import materials as M

# ---- 細かさ（set_detail で切り替える。"lite" は敵 NPC 用などの面を減らした簡略版）
N_BIG = 16    # ハンドガード等の大径
N_MID = 12    # 銃身
N_SMALL = 8   # 弾・小径
GRIP_STEPS = 5      # グリップ断面の丸めの段数
GRIP_SEG = 3        # グリップ輪郭の曲線の細かさ
BEVEL_STEPS = 2     # ストック等の角丸めの段数
MAG_STEPS = 8       # 弾倉の湾曲の分割数
RAS_HOLES = True    # RAS の斜めの面に丸穴を実際に開ける
RAS_HOLE_SEG = 16   # 丸穴 1 つの分割数

_DETAIL = {
    "full": dict(N_BIG=16, N_MID=12, N_SMALL=8, GRIP_STEPS=5, GRIP_SEG=3, BEVEL_STEPS=2, MAG_STEPS=8,
                 RAS_HOLES=True, RAS_HOLE_SEG=16),
    "lite": dict(N_BIG=8, N_MID=6, N_SMALL=6, GRIP_STEPS=2, GRIP_SEG=1, BEVEL_STEPS=1, MAG_STEPS=3,
                 RAS_HOLES=False, RAS_HOLE_SEG=8),
}


def set_detail(level):
    """細かさを切り替える（"full" / "lite"）。部品関数は呼ばれた時点の値を使う。"""
    globals().update(_DETAIL[level])


def barrel(l=L):
    b = l.bore_y
    return [lathe(0, b, [(l.muzzle_z, 7.85), (l.gas_z, 7.85), (l.gas_z, 9.5), (l.bolt_face_z, 9.5)],
                  N_MID, M.STEEL)]


def barrel_extension(l=L):
    return [lathe(0, l.bore_y, [(l.bolt_face_z - 40, 13), (l.bolt_face_z, 13)], N_MID, M.STEEL_DARK)]


def gas_block(l=L):
    return [lathe(0, l.bore_y, [(l.gas_z - 26, 15), (l.gas_z, 15)], N_MID, M.STEEL_DARK)]


def front_sight_base(l=L):
    """A2 フロントサイトベース。塔は前後が斜めの台形、耳は上が丸い板。"""
    b, z = l.bore_y, l.gas_z
    sl = b + l.sight_h
    ear = [(z - 20, sl - 32), (z - 9, sl - 32), (z - 9, sl - 6), (z - 11, sl - 2), (z - 18, sl - 2), (z - 20, sl - 6)]
    return [
        extrude_x([(z - 2, b + 10), (z - 25, b + 10), (z - 21, sl - 22), (z - 9, sl - 22)], -7, 7, M.STEEL_DARK),
        extrude_x(ear, 8, 11, M.STEEL_DARK),
        extrude_x(ear, -11, -8, M.STEEL_DARK),
        box(-11, sl - 32, z - 20, 11, sl - 26, z - 9, M.STEEL_DARK),   # 耳の連結
        box(-4, b - 30, z - 24, 4, b - 14, z - 11, M.STEEL_DARK),      # 着剣ラグ
    ]


RAS_HOLES_PER_FACE = 7    # 斜めの面 1 枚あたりの丸穴の数（参考写真）
RAS_HOLE_RATIO = 0.74     # 丸穴の直径 / 斜めの面の幅


def ras_body(l=L):
    """KAC M4 RAS の本体: 断面八角の筒（中空。前後の端はデルタリングとキャップに隠れる）。
    斜めの 4 面には丸穴を並べる（RAS_HOLES=True なら形状として穴を開け、穴から銃身が見える）。
    穴のある面は「正方形のマス目の中に丸穴」を並べ、マスの縁と穴の縁を放射状の四角形でつなぐ。"""
    b, f, r = l.bore_y, l.handguard_front_z, l.handguard_rear_z
    w = 2 * RAS_FLAT * math.tan(math.pi / 8)    # 八角の 1 面の幅
    verts, faces, charts, cuv = [], [], [], []

    def to3d(theta, s, z):
        nx, ny = math.cos(theta), math.sin(theta)
        tx, ty = -ny, nx
        return (RAS_FLAT * nx + s * tx, b + RAS_FLAT * ny + s * ty, z)

    def quad(theta, chart, pts2d):
        idx = []
        for s, z in pts2d:
            idx.append(len(verts))
            verts.append(to3d(theta, s, z))
        faces.append(idx)
        charts.append(chart)
        cuv.append([(s, z - r) for s, z in pts2d])

    for k in range(8):
        theta = math.pi / 4 * k
        diagonal = k % 2 == 1
        if not (diagonal and RAS_HOLES):
            quad(theta, k, [(-w / 2, r), (w / 2, r), (w / 2, f), (-w / 2, f)])
            continue
        n = RAS_HOLES_PER_FACE
        cell = w                                   # 正方形のマス
        z_first = (f + r) / 2 + cell * n / 2       # 穴の列を前後中央に寄せる（z は前ほど小さい）
        quad(theta, k, [(-w / 2, r), (w / 2, r), (w / 2, z_first), (-w / 2, z_first)])
        quad(theta, k, [(-w / 2, z_first - cell * n), (w / 2, z_first - cell * n), (w / 2, f), (-w / 2, f)])
        m = RAS_HOLE_SEG
        rad = cell * RAS_HOLE_RATIO / 2
        for h in range(n):
            zc = z_first - cell * (h + 0.5)
            ring = []
            for j in range(m + 1):
                a = 2 * math.pi * j / m
                ca, sa = math.cos(a), math.sin(a)
                k_sq = (cell / 2) / max(abs(ca), abs(sa))   # 同じ向きの、マスの縁までの距離
                ring.append(((rad * ca, zc + rad * sa), (k_sq * ca, zc + k_sq * sa)))
            for j in range(m):
                (c0, e0), (c1, e1) = ring[j], ring[j + 1]
                quad(theta, k, [c0, c1, e1, e0])
    return MeshPart(verts, faces, M.RECEIVER, None, charts, cuv, {k: False for k in range(8)}).finalize()


def handguard(l=L):
    """KAC M4 RAS: 断面八角の本体（斜めの面に丸穴）＋上面レール（角張ったキューブ）＋デルタリング＋キャップ。"""
    b, f, r = l.bore_y, l.handguard_front_z, l.handguard_rear_z
    return [
        ras_body(l),
        *_ras_rail(l, "top", M.RAIL),
        lathe(0, b, [(r, 27), (r + 4, 31), (r + 12, 31)], N_BIG, M.STEEL_DARK),             # デルタリング
        lathe(0, b, [(f - 6, 20), (f, 23)], N_BIG, M.STEEL_DARK),                         # キャップ
    ]


def flash_hider_a2(l=L):
    b, z1 = l.bore_y, l.muzzle_z
    z0 = z1 - l.fh_len
    out = [
        lathe(0, b, [(z1 - 15, 11), (z1, 10)], N_MID, M.STEEL_DARK),          # 根元
        lathe(0, b, [(z0, 10.5), (z0 + 6, 11)], N_MID, M.STEEL_DARK),         # 先端リング
        lathe(0, b, [(z0 + 6, 6), (z1 - 15, 6)], N_MID, M.BORE, False, False),  # 内側（暗）
        box(-6, b - 11, z0 + 6, 6, b - 7, z1 - 15, M.STEEL_DARK),             # 下面の板
    ]
    for ang in (-120, -60, 0, 60, 120):
        out.append(box(-2, b + 7, z0 + 6, 2, b + 11, z1 - 15, M.STEEL_DARK,
                       rotation=(0, 0, ang), pivot=(0, b, (z0 + z1) / 2)))
    return out


def buffer_tube(l=L):
    c = l.bore_y - 4
    z0 = l.lower_rear_z
    return [
        lathe(0, c, [(z0, l.tube_od / 2), (l.buffer_end_z - 3, l.tube_od / 2), (l.buffer_end_z, l.tube_od / 2 - 1.5)], N_BIG, M.RECEIVER),
        lathe(0, c, [(z0, 17.5), (z0 + 10, 17.5)], N_SMALL, M.STEEL_DARK),  # キャッスルナット（八角）
        box(-16, c - 16, z0 + 1, 16, c + 16, z0 + 5, M.STEEL_DARK),         # エンドプレート
    ]


def pistol_grip(l=L):
    """A2 グリップ: 断面は前（指を掛ける側）が細く後ろが太い卵形。上端はレシーバー幅に合わせて絞る。"""
    lb = l.bore_y + l.lower_bottom

    def width(z, y, f):
        fore = 0.68 + 0.32 * _smoothstep(0.0, 0.75, f)            # 前端 68% → 後ろ 100%
        top = 0.86 + 0.14 * _smoothstep(lb + 2, lb - 14, y)       # 上端はレシーバー幅（±12）に収める
        return fore * top

    def radius(nz, ny):
        # 前後のストラップ（法線が前後向き）は全周を丸める。底・上面（法線が上下向き）は角だけ 5mm で丸める
        return 5.0 + 9.5 * (1 - _smoothstep(0.55, 0.9, abs(ny)))

    return [inflate_x(grip_outline(l, per_seg=GRIP_SEG, extend_top=6.0), 14.5, M.POLYMER, steps=GRIP_STEPS,
                      width_fn=width, radius_fn=radius)]


def _smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def trigger(l=L):
    return [extrude_x_beveled(trigger_outline(l), -3.2, 3.2, 1.2, M.STEEL_DARK, steps=1)]


def trigger_guard(l=L):
    rear, front = ear_outlines(l)
    return [
        extrude_x_beveled(rear, -12, 12, 1.5, M.RECEIVER, steps=1),      # 後ろの耳（レシーバーの一部）
        extrude_x_beveled(front, -12, 12, 1.5, M.RECEIVER, steps=1),     # 前の耳
        extrude_x_beveled(guard_bar_outline(l), -6, 6, 1.0, M.RECEIVER, steps=1),  # ガード下辺
    ]


def lower_common(l=L):
    return _lower_common(l, magwell)


def lower_body(l=L):
    b = l.bore_y
    lb = b + l.lower_bottom
    zg = ref_zy(l, [REF_LOWER_REAR[0]])[0][0]
    return lower_common(l) + [
        box(-12, lb, l.magwell_rear_z, 12, b + l.upper_bottom, zg, M.RECEIVER),        # トリガーメカ部
        extrude_x(lower_rear_outline(l), -12.5, 12.5, M.RECEIVER),                     # 後部（下面が後ろへ反り上がる）
    ]


def magwell(l=L):
    """マグウェル: 下端は前ほど高い斜めの切り口。下端に一回り太い縁（フレア）。"""
    pts = magwell_outline(l)
    (zr, _), (_, yr), (zf, yf), _ = pts
    k = (yf - yr) / (zf - zr)
    lip = [(zr + 2, yr - 0.5), (zf - 2, yf + (-2) * k - 0.5), (zf - 2, yf + (-2) * k + 6), (zr + 2, yr + 6)]
    return [extrude_x(pts, -15, 15, M.RECEIVER), extrude_x_beveled(lip, -16.5, 16.5, 1.0, M.RECEIVER, steps=1)]


def lower_receiver(l=L):
    return lower_body(l) + trigger_guard(l)


def magazine_stanag(l=L):
    """STANAG 30 発弾倉（角張った箱形）。上は直線、マグウェルの下から半径一定で前へ反る（実物と同じ「バナナ」形）。"""
    b = l.bore_y
    top = b - l.mag_top_below_bore
    split = top - l.mag_straight
    zc, half = l.mag_center_z, 32.0
    arc_len, steps = l.mag_arc, MAG_STEPS
    radius = arc_len / math.radians(MAG_ANGLE)
    center = [(zc, top), (zc, split)]
    tangents = [0.0, 0.0]
    for i in range(1, steps + 1):
        t = math.radians(MAG_ANGLE) * i / steps
        center.append((zc - radius * (1 - math.cos(t)), split - radius * math.sin(t)))
        tangents.append(t)
    back = [(cz + half * math.cos(t), cy - half * math.sin(t)) for (cz, cy), t in zip(center, tangents)]
    front = [(cz - half * math.cos(t), cy + half * math.sin(t)) for (cz, cy), t in zip(center, tangents)]
    body = back + front[::-1]
    # フロアプレート（最下端の法線方向へ 8mm、前後に 4mm ずつはみ出す）
    (cz, cy), t = center[-1], tangents[-1]
    dn = (-math.sin(t), -math.cos(t))
    nb = (math.cos(t), -math.sin(t))
    def p(s_n, s_d):
        return (cz + nb[0] * s_n + dn[0] * s_d, cy + nb[1] * s_n + dn[1] * s_d)
    plate = [p(half + 4, -2), p(half + 4, 6), p(-half - 4, 6), p(-half - 4, -2)]
    return [
        extrude_x(body, -11, 11, M.MAG),
        extrude_x(plate, -13, 13, M.STEEL_DARK),
        box(-11.6, split + 5, zc - 25, 11.6, top - 25, zc + 25, M.MAG),  # 側面のリブ（直線部）
    ]


def stock_m4(l=L):
    """M4 ストック（stock_pos の位置）: 前端の筒（チューブを包む）から、下縁がつま先へ向かって斜めに下がる。"""
    b = l.bore_y
    f = l.stock_front_z
    z1 = l.butt_z - 8
    sleeve = [(f, b + 18), (z1, b + 18), (z1, b - 24), (f + 8, b - 24), (f, b - 18)]
    fin = [(f + 18, b - 20), (z1, b - 20), (z1, b - 86), (z1 - 18, b - 86), (f + 26, b - 30)]
    butt = [(z1, b + 20), (l.butt_z, b + 19), (l.butt_z + 1, b - 84), (z1, b - 88)]
    return [
        extrude_x_beveled(sleeve, -17, 17, 5, M.POLYMER, steps=BEVEL_STEPS),   # 上: チューブを包む太い部分
        extrude_x_beveled(fin, -12, 12, 3, M.POLYMER, steps=BEVEL_STEPS),      # 下: 薄いひれ（実物も上より細い）
        box(-5, b - 30, f + 4, 5, b - 22, f + 44, M.STEEL_DARK),     # 調整レバー
        extrude_x_beveled(butt, -18, 18, 3, M.RUBBER, steps=BEVEL_STEPS),
    ]


def cartridge_556(z_tip, y, case_mat=M.BRASS, bullet_mat=M.COPPER):
    case = lathe(0, y, [(z_tip + 12.7, 3.1), (z_tip + 20, 3.1), (z_tip + 25, 4.7), (z_tip + 56, 4.8),
                        (z_tip + 56, 4.2), (z_tip + 57.4, 4.8)], N_SMALL, case_mat)
    bullet = lathe(0, y, [(z_tip, 0.4), (z_tip + 5, 2.1), (z_tip + 12.7, 2.85)], N_SMALL, bullet_mat)
    return [case], [bullet]
