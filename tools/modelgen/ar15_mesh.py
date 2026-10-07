"""
AR-15 系パーツライブラリのメッシュ版（単位 mm）。ar15_parts を土台に、丸・斜面・曲線の部品だけを
メッシュ（poly_mesh）へ置き換える。角張った部品（レシーバー・レール・サイト等）はキューブのまま流用する。

メッシュは Blockbench の Meshy プラグインが書き出す poly_mesh と同じ形で出力される（core.py 冒頭参照）。
"""
import math

from ar15_parts import *  # noqa: F401,F403  角張った部品・Layout・寸法定数はそのまま使う
from ar15_parts import L, MAG_ANGLE, grip_outline, guard_outline, trigger_outline, lower_body
from core import box, lathe, extrude_x, extrude_x_beveled
import materials as M

N_BIG = 16    # ハンドガード等の大径
N_MID = 12    # 銃身
N_SMALL = 8   # 弾・小径


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


def handguard(l=L):
    b, f, r = l.bore_y, l.handguard_front_z, l.handguard_rear_z
    return [
        lathe(0, b, [(f, 25), (f + 6, 26), (r - 6, 26), (r, 27)], N_BIG, M.HANDGUARD),
        lathe(0, b, [(r, 27), (r + 4, 31), (r + 12, 31)], N_BIG, M.STEEL_DARK),             # デルタリング
        lathe(0, b, [(f - 6, 20), (f, 23)], N_BIG, M.STEEL_DARK),                         # キャップ
    ]


def flash_hider_a2(l=L):
    b, z1 = l.bore_y, l.muzzle_z
    z0 = z1 - 57
    out = [
        lathe(0, b, [(z1 - 20, 11), (z1, 10)], N_MID, M.STEEL_DARK),          # 根元
        lathe(0, b, [(z0, 10.5), (z0 + 7, 11)], N_MID, M.STEEL_DARK),         # 先端リング
        lathe(0, b, [(z0 + 7, 6), (z1 - 20, 6)], N_MID, M.BORE, False, False),  # 内側（暗）
        box(-6, b - 11, z0 + 7, 6, b - 7, z1 - 20, M.STEEL_DARK),             # 下面の板
    ]
    for ang in (-120, -60, 0, 60, 120):
        out.append(box(-2, b + 7, z0 + 7, 2, b + 11, z1 - 20, M.STEEL_DARK,
                       rotation=(0, 0, ang), pivot=(0, b, (z0 + z1) / 2)))
    return out


def buffer_tube(l=L):
    c = l.bore_y - 4
    return [
        lathe(0, c, [(62, 15), (l.buffer_end_z - 3, 15), (l.buffer_end_z, 13.5)], N_BIG, M.RECEIVER),
        lathe(0, c, [(62, 17.5), (72, 17.5)], N_SMALL, M.STEEL_DARK),       # キャッスルナット（八角）
        box(-16, c - 16, 63, 16, c + 16, 67, M.STEEL_DARK),                 # エンドプレート
    ]


def pistol_grip(l=L):
    return [extrude_x_beveled(grip_outline(l), -14, 14, 5.5, M.POLYMER, steps=3)]


def trigger(l=L):
    return [extrude_x_beveled(trigger_outline(l), -3.2, 3.2, 1.2, M.STEEL_DARK, steps=1)]


def trigger_guard(l=L):
    return [extrude_x_beveled(guard_outline(l), -6, 6, 1.5, M.RECEIVER, steps=1)]


def lower_receiver(l=L):
    return lower_body(l) + trigger_guard(l)


def magazine_stanag(l=L):
    """STANAG 30 発弾倉。上 100mm は直線、下 80mm を半径一定で前方へ曲げる（実物と同じ「バナナ」形）。"""
    b = l.bore_y
    top, split = b - 24, b - 125
    zc, half = -85.0, 32.0
    arc_len, steps = 80.0, 6
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
        box(-11.6, split + 5, -110, 11.6, split + 65, -60, M.MAG),       # 側面のリブ（直線部）
    ]


def stock_m4(l=L):
    """M4 ストック: 前端の筒（チューブを包む）から、下縁がつま先へ向かって斜めに下がる。角は丸める。"""
    b = l.bore_y
    z1 = l.butt_z - 8
    sleeve = [(182, b + 18), (z1, b + 18), (z1, b - 24), (190, b - 24), (182, b - 18)]
    fin = [(200, b - 20), (z1, b - 20), (z1, b - 86), (z1 - 18, b - 86), (208, b - 30)]
    butt = [(z1, b + 20), (l.butt_z, b + 19), (l.butt_z + 1, b - 84), (z1, b - 88)]
    return [
        extrude_x_beveled(sleeve, -17, 17, 5, M.POLYMER, steps=2),   # 上: チューブを包む太い部分
        extrude_x_beveled(fin, -12, 12, 3, M.POLYMER, steps=2),      # 下: 薄いひれ（実物も上より細い）
        box(-5, b - 30, 186, 5, b - 22, 226, M.STEEL_DARK),     # 調整レバー
        extrude_x_beveled(butt, -18, 18, 3, M.RUBBER, steps=2),
    ]


def cartridge_556(z_tip, y, case_mat=M.BRASS, bullet_mat=M.COPPER):
    case = lathe(0, y, [(z_tip + 12.7, 3.1), (z_tip + 20, 3.1), (z_tip + 25, 4.7), (z_tip + 56, 4.8),
                        (z_tip + 56, 4.2), (z_tip + 57.4, 4.8)], N_SMALL, case_mat)
    bullet = lathe(0, y, [(z_tip, 0.4), (z_tip + 5, 2.1), (z_tip + 12.7, 2.85)], N_SMALL, bullet_mat)
    return [case], [bullet]
