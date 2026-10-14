"""
AR-15 系パーツライブラリのメッシュ版（単位 mm）。ar15_parts を土台に、丸・斜面・曲線の部品だけを
メッシュ（poly_mesh）へ置き換える。角張った部品（レシーバー・レール・サイト等）はキューブのまま流用する。

メッシュは Blockbench の Meshy プラグインが書き出す poly_mesh と同じ形で出力される（core.py 冒頭参照）。
"""
import math

from ar15_parts import *  # noqa: F401,F403  角張った部品・Layout・寸法定数はそのまま使う
from ar15_parts import (L, MAG_ANGLE, RAS_FLAT, _ras_rail, fsb_profile, fsb_frame_lower, FSB_TOWER_HALF, FSB_EAR,
                        FSB_RING_R, FSB_RINGS,
                        FSB_SLOT_DEPTH, grip_outline, ear_outlines, guard_bar_outline, trigger_outline,
                        lower_common as _lower_common, lower_rear_outline, ref_zy, LOWER_REAR_UNDER, magwell_outline)
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
    bore = 5.56 / 2
    return [
        # 銃口の端面は輪（中央に穴）。穴の中は暗い筒で、奥をふさぐ
        lathe(0, b, [(l.muzzle_z, bore), (l.muzzle_z, l.barrel_od_front / 2), (l.gas_z, l.barrel_od_front / 2),
                     (l.gas_z, l.barrel_od / 2), (l.bolt_face_z, l.barrel_od / 2)],
              N_MID, M.STEEL, cap0=False),
        lathe(0, b, [(l.muzzle_z, bore), (l.muzzle_z + 25, bore)], N_SMALL, M.BORE, cap0=False, cap1=True),
    ]


def barrel_extension(l=L):
    return [lathe(0, l.bore_y, [(l.bolt_face_z - 40, 13), (l.bolt_face_z, 13)], N_MID, M.STEEL_DARK)]


def gas_block(l=L):
    return [lathe(0, l.bore_y, [(l.gas_z - d1, FSB_RING_R), (l.gas_z - d0, FSB_RING_R)], N_MID, M.STEEL_DARK)
            for d0, d1 in FSB_RINGS]


def _clip_y(poly, y0, y1):
    """側面形状を高さ y0〜y1 で切り取る（shapely）。"""
    from shapely.geometry import Polygon, box as sbox
    g = Polygon(poly).intersection(sbox(-1e4, y0, 1e4, y1))
    return list(g.exterior.coords)[:-1]


def front_sight_base(l=L):
    """A2 フロントサイトベース: 「A」の字の枠（窓は形として抜けている）。切り込みより下は塔、上は左右の耳。"""
    sl = l.bore_y + l.sight_h
    floor = sl - FSB_SLOT_DEPTH
    prof = fsb_profile(l)
    t, (e0, e1) = FSB_TOWER_HALF, FSB_EAR
    tower = _clip_y(prof, -1e4, floor)
    ear = _clip_y(prof, floor - 6, 1e4)
    return [
        extrude_x_beveled(tower, -t, t, 0.8, M.STEEL_DARK, steps=1),
        extrude_x_beveled(ear, e0, e1, 0.8, M.STEEL_DARK, steps=1),     # 耳（左）
        extrude_x_beveled(ear, -e1, -e0, 0.8, M.STEEL_DARK, steps=1),   # 耳（右）
        *fsb_frame_lower(l),
    ]


RAS_HOLES_PER_FACE = 7    # 斜めの面 1 枚あたりの穴の数（作者提供の図面: 1 列 7 個）
RAS_HOLE_RATIO = 0.74     # 穴の直径 / 斜めの面の幅
RAS_HOLE_ASPECT = 1.0     # 穴は実物では丸（作者確認）。側面図で前後に長い楕円に見えるのは 45° の面を真横から
                          # 見た投影で縦に潰れるため。一度これを楕円と誤読して 1.55 にしたが、丸に戻した


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
        rad_s = cell * RAS_HOLE_RATIO / 2                # 幅方向の半径
        rad_z = min(rad_s * RAS_HOLE_ASPECT, cell * 0.46)  # 前後方向の半径（マスからはみ出さない）
        for h in range(n):
            zc = z_first - cell * (h + 0.5)
            ring = []
            for j in range(m + 1):
                a = 2 * math.pi * j / m
                ca, sa = math.cos(a), math.sin(a)
                k_sq = (cell / 2) / max(abs(ca), abs(sa))   # 同じ向きの、マスの縁までの距離
                ring.append(((rad_s * ca, zc + rad_z * sa), (k_sq * ca, zc + k_sq * sa)))
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
        lathe(0, b, [(z0 + 6, 4), (z0, 4), (z0, 10.5), (z0 + 6, 11)], N_MID, M.STEEL_DARK, False, False),  # 先端リング（穴あき）
        lathe(0, b, [(z0 + 6, 6), (z1 - 15, 6)], N_MID, M.BORE, True, True),   # 内側（暗）
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
    zg = LOWER_REAR_UNDER[0][0]
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


MAG_STYLE = "pmag"   # "usgi"（アルミ・灰色・縦リブ 4 本）/ "pmag"（Magpul PMAG・黒い樹脂・横の段と前後の背骨）


def set_mag_style(style):
    global MAG_STYLE
    MAG_STYLE = style


def magazine_stanag(l=L):
    """STANAG 30 発弾倉（角張った箱形）。上は直線、マグウェルの下から半径一定で前へ反る（実物と同じ「バナナ」形）。
    外観は MAG_STYLE で切り替える（本体の輪郭・寸法は共通。M249 の STANAG 版もこれを回して使う）。"""
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
    def strip(o0, o1, i0=0, i1=None):
        """中心線に沿った帯（前後方向のオフセット o0〜o1、index i0〜i1 の区間）の側面形。湾曲部にも追従する。"""
        i1 = len(center) if i1 is None else i1
        pts = [(cz_ + o1 * math.cos(t), cy_ - o1 * math.sin(t)) for (cz_, cy_), t in zip(center[i0:i1], tangents[i0:i1])]
        pts += [(cz_ + o0 * math.cos(t), cy_ - o0 * math.sin(t)) for (cz_, cy_), t in zip(center[i0:i1], tangents[i0:i1])][::-1]
        return pts

    def band(i, w_along=1.8, extra=2.5):
        """中心線上の点 i で、弾倉を一周する帯（側面形は中心線に直交する細い長方形）。"""
        (cz_, cy_), t = center[i], tangents[i]
        nb_ = (math.cos(t), -math.sin(t))            # 前後方向
        dn_ = (-math.sin(t), -math.cos(t))           # 弾倉の長さ方向（下向き）
        pts = []
        for s_n, s_d in ((half + extra, -w_along), (half + extra, w_along), (-half - extra, w_along), (-half - extra, -w_along)):
            pts.append((cz_ + nb_[0] * s_n + dn_[0] * s_d, cy_ + nb_[1] * s_n + dn_[1] * s_d))
        return pts

    # マグウェルに隠れる直線部（上 60mm）ではなく、見えている湾曲部に凹凸を置く
    if MAG_STYLE == "usgi":
        mat = M.MAG_USGI
        out = [extrude_x(body, -11, 11, mat), extrude_x(plate, -13, 13, M.STEEL_DARK)]
        for o in (-19.0, -6.5, 6.5, 19.0):            # 縦リブ 4 本（側面の補強の段。湾曲部にも沿う）
            out.append(extrude_x(strip(o - 1.6, o + 1.6, 1), -12.2, 12.2, mat))
        return out
    mat = M.MAG_PMAG
    out = [
        extrude_x(body, -11.5, 11.5, mat),
        extrude_x(plate, -13.5, 13.5, mat),            # フロアプレート（樹脂。本体より少し厚く、前後にはみ出す）
        extrude_x(strip(-half - 1.5, -half + 3.5, 1), -12.6, 12.6, mat),   # 前の背骨
        extrude_x(strip(half - 3.5, half + 1.5, 1), -12.6, 12.6, mat),     # 後ろの背骨
    ]
    n = len(center)
    for k in range(5):                                 # 側面の横の段（指掛かりの帯）。湾曲部に等間隔
        i = 2 + int((n - 3) * k / 4)
        out.append(extrude_x(band(i), -12.8, 12.8, mat))
    return out


def stock_m4(l=L):
    """M4 ストック（stock_pos の位置）: 前端の筒（チューブを包む）から、下縁がつま先へ向かって斜めに下がる。"""
    b = l.bore_y
    f = l.stock_front_z
    z1 = l.butt_z - 8
    # 筒の上面 +14: 写真はモデル（+18）より約 7mm 低く、三面図も「レール天面の約 13mm 下」（＝+13）と示す。
    # ただしバッファチューブ上面が +10.5 なので、肉厚 3.5mm を残せる +14 までにとどめる（これ以上下げるならチューブ位置の再検討が要る）
    sleeve = [(f, b + 14), (z1, b + 14), (z1, b - 24), (f + 8, b - 24), (f, b - 18)]
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
