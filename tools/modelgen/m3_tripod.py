"""
M3 三脚（M2 重機関銃の地上用の据え付け台）のパーツと組み立て（単位 mm、メッシュ版）。

構造は米陸軍 FM 23-65（2002、パブリックドメイン）図 1-2・1-6（三脚）・1-8（旋回・俯仰装置）・1-9（ピントル）・5-1〜5-3
（据えた状態の射撃姿勢）の線画で確かめた: 3 本の筒の脚（短い前脚と、後ろへ開く 2 本の後脚）が三脚の頭でつながり、
後脚どうしを旋回の横棒がつなぐ。銃は前の取付け穴をピントル（三脚の頭に差す二股の金具）で、後ろの金具を
旋回・俯仰装置（横棒の上を左右に滑る台＋縦のねじ）で支える。足の先は地面に踏み込む板。
寸法は推定（真横の写真が無い）: 低い据え方で銃身の軸が地面から約 12in（FM 23-65 1-5 項）、脚の長さ・開きは線画の比率。
重さ 44lb（ピントル・旋回俯仰装置を含む。同 1-5 項）。

**銃（m2.py）と同じ座標で作る**（同じ原点に重ねて置くと、ピントルが銃の前の取付け穴に、旋回・俯仰装置が後ろの金具に合う）。
地面は Y = GROUND_Y。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
import m2
from core import box, lathe
from m249 import x_cyl

K = 1.0 / ar15_parts.MM_PER_PX
STEEL = M.M2_STEEL
GROUND_Y = m2.BORE_Y - 305.0          # 低い据え方: 銃身の軸が地面から 12in
PIN_Z, PIN_Y = m2.TRUNNION_PIN        # 銃の前の取付け穴（ピントルの軸）
HEAD = (0.0, -78.0, PIN_Z)            # 三脚の頭（ピントルの差し込み口の上の端）
FRONT_FOOT = (0.0, GROUND_Y, PIN_Z - 260.0)
TRAIL_FOOT = (430.0, GROUND_Y, PIN_Z + 1080.0)    # 後脚の足（左。右は X を反転）
LEG_R = 15.0
TE_Z = -272.0                         # 旋回・俯仰装置（銃の後ろの金具の中央）
BRACKET_Y = -36.0                     # 銃の後ろの金具の下の端（m2_outline.BRACKET）


def tube(p0, p1, r, mat, n=10):
    """p0→p1 の丸い筒（Z 方向の回転体を作って向きを合わせる）。"""
    from core import MeshPart
    p0, p1 = [float(v) for v in p0], [float(v) for v in p1]
    d = [b - a for a, b in zip(p0, p1)]
    ln = math.sqrt(sum(v * v for v in d))
    m = lathe(0, 0, [(0.0, r), (ln, r)], n, mat)
    # Z 軸 → d の向きへ回す（Z 軸と d の外積まわり）
    ux, uy, uz = (v / ln for v in d)
    ax, ay = -uy, ux                                  # (0,0,1) × u
    s = math.sqrt(ax * ax + ay * ay)
    c = uz
    if s < 1e-9:
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1 if c > 0 else -1]]
    else:
        ax, ay = ax / s, ay / s
        t = 1 - c
        R = [[t * ax * ax + c, t * ax * ay, s * ay],
             [t * ax * ay, t * ay * ay + c, -s * ax],
             [-s * ay, s * ax, c]]
    f = lambda v: tuple(p0[i] + sum(R[i][j] * v[j] for j in range(3)) for i in range(3))
    g = lambda v: tuple(sum(R[i][j] * v[j] for j in range(3)) for i in range(3))
    nm = None if m.normals is None else [[g(v) for v in fn] for fn in m.normals]
    return MeshPart([f(v) for v in m.verts], m.faces, m.mat, nm, m.charts, m.chart_uv, m.chart_edge)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def head():
    """三脚の頭（脚の付け根の金具）とピントルの差し込み口。"""
    x, y, z = HEAD
    return [box(-38.0, y - 50.0, z - 45.0, 38.0, y - 10.0, z + 45.0, STEEL),
            box(-20.0, y - 12.0, z - 20.0, 20.0, y + 2.0, z + 20.0, STEEL)]


def legs():
    """前脚 1 本・後脚 2 本（伸縮の筒。先の太い所が外筒）と足の板。"""
    x, y, z = HEAD
    root_f = (0.0, y - 40.0, z - 30.0)
    out = [tube(root_f, FRONT_FOOT, LEG_R, STEEL), tube(lerp(root_f, FRONT_FOOT, 0.45), FRONT_FOOT, LEG_R + 3.0, STEEL)]
    feet = [FRONT_FOOT]
    for s in (1, -1):
        foot = (s * TRAIL_FOOT[0], TRAIL_FOOT[1], TRAIL_FOOT[2])
        root = (s * 30.0, y - 35.0, z + 35.0)
        out += [tube(root, foot, LEG_R, STEEL), tube(lerp(root, foot, 0.5), foot, LEG_R + 3.0, STEEL)]
        feet.append(foot)
    for fx, fy, fz in feet:                           # 足の板（地面に踏み込む）
        out.append(box(fx - 28.0, fy, fz - 40.0, fx + 28.0, fy + 8.0, fz + 40.0, STEEL))
    return out


def traversing_bar():
    """旋回の横棒（後脚どうしをつなぐ。上に目盛り）。"""
    x, y, z = HEAD
    t = (TE_Z - z) / (TRAIL_FOOT[2] - z)
    p = lambda s: (s * (30.0 + (TRAIL_FOOT[0] - 30.0) * t), (y - 35.0) + (GROUND_Y - (y - 35.0)) * t, TE_Z)
    a, b = p(1), p(-1)
    return [box(b[0] - 5.0, a[1] - 6.0, TE_Z - 12.0, a[0] + 5.0, a[1] + 6.0, TE_Z + 12.0, STEEL),
            box(-60.0, a[1] + 6.0, TE_Z - 10.0, 60.0, a[1] + 8.0, TE_Z + 10.0, M.STEEL_DARK)]   # 目盛りの板


def te_mechanism():
    """旋回・俯仰装置: 横棒の上を滑る台・縦の俯仰ねじ（上下に手回しの輪）・銃の後ろの金具をはさむ二股。"""
    x, y, z = HEAD
    t = (TE_Z - z) / (TRAIL_FOOT[2] - z)
    bar_y = (y - 35.0) + (GROUND_Y - (y - 35.0)) * t
    out = [box(-22.0, bar_y - 10.0, TE_Z - 18.0, 22.0, bar_y + 14.0, TE_Z + 18.0, STEEL),          # 滑る台
           box(-9.0, bar_y + 14.0, TE_Z - 9.0, 9.0, BRACKET_Y - 12.0, TE_Z + 9.0, M.STEEL_DARK),   # 俯仰ねじ
           box(-26.0, BRACKET_Y - 14.0, TE_Z - 14.0, 26.0, BRACKET_Y - 6.0, TE_Z + 14.0, STEEL)]  # 二股の台
    for s in (1, -1):                                  # 二股（銃の金具をはさむ）・手回しの輪
        xa, xb = sorted((s * 23.0, s * 27.0))
        out.append(box(xa, BRACKET_Y - 8.0, TE_Z - 14.0, xb, BRACKET_Y + 20.0, TE_Z + 14.0, STEEL))
    mid = (bar_y + 14.0 + BRACKET_Y - 12.0) / 2
    out.append(y_wheel(TE_Z, mid, 36.0, 8.0, M.STEEL_DARK))                                  # 俯仰の手回しの輪
    return out


def y_wheel(z, y, r, h, mat):
    """水平の輪（縦軸の円盤）。"""
    from m2 import y_lathe
    return y_lathe(0.0, z, [(y - h / 2, 0.01), (y - h / 2, r), (y + h / 2, r), (y + h / 2, 0.01)], 16, mat)


def pintle():
    """ピントル: 三脚の頭に差す棒と、銃の前の取付け穴をはさむ二股・軸のボルト。"""
    x, y, z = HEAD
    out = [box(-14.0, y - 30.0, z - 14.0, 14.0, -8.0, z + 14.0, STEEL),                      # 差し込みの棒
           box(-m2.RCV_HALF - 8.0, -14.0, z - 22.0, m2.RCV_HALF + 8.0, -6.0, z + 22.0, STEEL)]   # 二股の下
    for s in (1, -1):
        xa, xb = sorted((s * (m2.RCV_HALF + 1.0), s * (m2.RCV_HALF + 8.0)))
        out.append(box(xa, -14.0, z - 22.0, xb, PIN_Y + 14.0, z + 22.0, STEEL))
        xa, xb = sorted((s * (m2.RCV_HALF + 7.0), s * (m2.RCV_HALF + 13.0)))
        out.append(x_cyl(PIN_Z, PIN_Y, 10.0, xa, xb, M.STEEL_DARK, n=10))                   # 軸のボルトの頭
    return out


def build():
    from core import Model
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("tripod", "root", HEAD, "tripod", head() + legs() + traversing_bar())
    add("pintle", "tripod", (0, PIN_Y, PIN_Z), "pintle", pintle())
    add("te_mechanism", "tripod", (0, BRACKET_Y, TE_Z), "te_mechanism", te_mechanism())
    add("ground", None, (0, GROUND_Y, 0), None, [])
    return m, parts
