"""
照準器の共通部品: 見やすくするための誇張の目安と、穴の抜けた照門・レールに載せる折りたたみ式のアイアンサイト。

実寸の照準器（照星の幅 2mm・照門の穴 3〜4mm）は、ADS で覗くと照星が 1〜2 画素、穴は点にしか見えない。
他のゲームと同じく実物より大きく作る。大きさは「ADS の目からどう見えるか」で決める（視野角 70°・画面の高さ基準）:
  - 照星の幅: 画面の高さの約 1%         → 幅 = 目からの距離 × POST_ANGLE（0.75% ではゲーム内で 4〜5 画素と小さかった）
  - 照門の穴の直径: 約 7%（ゴーストリング）→ 直径 = 距離 × HOLE_ANGLE
  - 切り欠き式の照門の幅: 照星の約 2 倍に見える → 幅 = 距離 × NOTCH_ANGLE
寸法は mm。座標は各銃と同じ（+X が左、銃口が -Z）。
"""
from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import split, unary_union

import materials as M
from core import MeshPart, box, extrude_x

POST_ANGLE = 0.0125
HOLE_ANGLE = 0.0856
NOTCH_ANGLE = 0.025
IRON_BEHIND_TRIGGER = 113.0     # rig.IRON_BEHIND と同じ（ADS の目はトリガーの後ろ 113mm より前に来ない）
APERTURE_RELIEF = 72.0          # rig.IRON_MIN_RELIEF と同じ（穴照門から目まで最低 3px）

BUIS_HEIGHT = 22.0              # 折りたたみ式: レールの天面から照準線まで
BUIS_REAR_LEN = 26.0            # 後ろのクランプの前後の長さ（照準板はその中央）
BUIS_FRONT_LEN = 22.0
# 折りたたみ式の照準板の輪・耳の太さ（作者の指摘「P90 の照準器が太い」。輪を穴の 2 倍の太さにし、耳 3mm・板 4mm に
# していたので、穴を大きくした分だけ枠も太り、後ろ・斜めから見ると受け部より幅広い塊になっていた。実物の MBUS の
# 照準板・耳は 2mm 前後）。穴の大きさ（HOLE_ANGLE。ADS の見え方）は変えない
BUIS_RING = 2.5
BUIS_EAR = 2.0


def eye_z(trigger_z, rear_z):
    """ADS の目の前後位置の見込み（rig の規則のうち、形状を見ない 2 つ）。照準器の大きさを決めるのに使う。"""
    return max(trigger_z + IRON_BEHIND_TRIGGER, rear_z + APERTURE_RELIEF)


def _swap_xz(m):
    s = lambda v: (v[2], v[1], v[0])
    n = None if m.normals is None else [[s(v) for v in f] for f in m.normals]
    return MeshPart([s(v) for v in m.verts], m.faces, m.mat, n, m.charts, m.chart_uv, m.chart_edge)


def plate_z(shape, z0, z1, mat):
    """XY 平面の形（shapely。穴があってよい）を Z 方向 z0〜z1 に押し出した板（照門の板など、後ろから見る部品）。
    穴があれば穴の中心を通る縦線で穴の無い片に切り分けてから押し出す（m249.outline_parts と同じやり方）。"""
    pieces = [shape]
    for h in shape.interiors:
        cx = h.centroid.x
        cut = LineString([(cx, -1e4), (cx, 1e4)])
        pieces = [q for pc in pieces for q in split(pc, cut).geoms]
    # 反時計回りにそろえ、一直線に並ぶ頂点を除く（core の耳切り法は辺の上の頂点で止まる）
    return [_swap_xz(extrude_x(list(orient(q.simplify(0.01), 1.0).exterior.coords)[:-1], z0, z1, mat))
            for q in pieces if q.area > 0.2]


def aperture_plate(sy, z0, z1, hole_d, base_y, mat, half_w=None, ears=True, ring=None, ear_t=3.0):
    """穴照門の板: 照準線 sy を中心に直径 hole_d の穴、外側は輪（既定は穴の 2 倍。ring を渡すとその太さ）、下は base_y まで。
    ears=True なら左右に守りの耳（輪より上まで。厚さ ear_t）。"""
    r_in = hole_d / 2
    r_out = r_in + (max(3.0, r_in) if ring is None else ring)
    q = 3 if r_in < 4.0 else 4                     # 円の分割（小さい穴は 12 角形で十分。面の数を抑える）
    w = r_out if half_w is None else half_w
    g = [Point(0, sy).buffer(r_out, quad_segs=q), sbox(-w, base_y, w, sy)]
    if ears:
        for s in (1, -1):
            xa, xb = sorted((s * (r_out - 1.0), s * (r_out + ear_t)))
            g.append(sbox(xa, base_y, xb, sy + r_out + 1.5))
        g.append(sbox(-(r_out + ear_t), base_y, r_out + ear_t, base_y + 4.0))
    shape = unary_union(g).difference(Point(0, sy).buffer(r_in, quad_segs=q))
    return plate_z(shape.simplify(0.05), z0, z1, mat)


def post(x_w, y0, sy, zc, mat, depth=None):
    """照星のポスト（四角い柱。先端＝照準線）。"""
    d = x_w if depth is None else depth
    return box(-x_w / 2, y0, zc - d / 2, x_w / 2, sy, zc + d / 2, mat)


def buis_rear(rail_top, sy, zc, hole_d, mat=M.STEEL_DARK):
    """折りたたみ式の後ろのサイト（起こした状態。Magpul MBUS 風）。zc＝照準板の前後位置。
    レールのクランプ・台・照準板（守りの耳付き）・右側の風偏つまみ。"""
    h = BUIS_REAR_LEN / 2
    # クランプ（レールの頭の幅 24mm）。下面はレールへ 1.5mm 埋める（台の高さが前後で違っても浮かない）
    out = [box(-12, rail_top - 1.5, zc - h, 12, rail_top + 6, zc + h, mat),
           box(-6, rail_top + 6, zc - h + 5, 6, rail_top + 10, zc + h - 5, mat)]   # 台（折りたたみの蝶番）
    # 照準板は輪・耳を細く（BUIS_RING・BUIS_EAR）。穴の大きさ（ADS の見え方）は変えない
    out += aperture_plate(sy, zc - 1.5, zc + 1.5, hole_d, rail_top + 9.0, mat, ring=BUIS_RING, ear_t=BUIS_EAR)
    out.append(box(-15, rail_top + 6, zc - 3, -12, rail_top + 10, zc + 3, mat))   # 風偏つまみ（右）
    return out


def buis_front(rail_top, sy, zc, post_w, mat=M.STEEL_DARK):
    """折りたたみ式の前のサイト（起こした状態）。クランプ・塔・左右の守りの耳・ポスト（先端＝照準線）。"""
    h = BUIS_FRONT_LEN / 2
    gap = post_w / 2 + 2.5                         # ポストと耳の間（覗いたとき耳がポストに重ならない）
    top = sy - post_w * 1.5                        # 塔の上面（ここからポストが立つ）
    e = BUIS_EAR
    out = [box(-12, rail_top - 1.5, zc - h, 12, rail_top + 6, zc + h, mat)]   # クランプ（レールへ 1.5mm 埋める）
    parts = [sbox(-(gap + e), rail_top + 5.0, gap + e, top)]
    for s in (1, -1):
        xa, xb = sorted((s * gap, s * (gap + e)))
        parts.append(sbox(xa, top - 1.0, xb, sy + 3.0))
    shape = unary_union(parts)
    out += plate_z(shape, zc - 2.0, zc + 2.0, mat)
    out.append(post(post_w, top - 1.0, sy, zc, mat))
    return out


def _swap_xy(m):
    s = lambda v: (v[1], v[0], v[2])
    n = None if m.normals is None else [[s(v) for v in f] for f in m.normals]
    return MeshPart([s(v) for v in m.verts], m.faces, m.mat, n, m.charts, m.chart_uv, m.chart_edge)


def drum_aperture(cz, r, y0, sy, hole_d, top, mat, n=14):
    """縦軸のドラム（MP5 の回転式照門）に、前後へ抜けた穴（中心＝照準線 sy）。ドラムを穴の下・上・左右の帯に分けて作り、
    帯の四角い穴の角は輪で埋めて丸くする。y0〜top がドラムの高さ。"""
    import math
    from m249 import ring_z, y_cyl
    rh = hole_d / 2
    out = [y_cyl(0.0, cz, r, y0, sy - rh, mat, n=n), y_cyl(0.0, cz, r, sy + rh, top, mat, n=n)]
    for s in (1, -1):                                   # 穴の左右の帯: ドラムの断面（円）の |x| ≥ rh の部分を縦に押し出す
        pts = [(cz + r * math.cos(a), s * r * math.sin(a)) for a in
               (math.asin(rh / r) + (math.pi - 2 * math.asin(rh / r)) * k / 8 for k in range(9))]
        out.append(_swap_xy(extrude_x(list(orient(Polygon(pts), 1.0).exterior.coords)[:-1], sy - rh, sy + rh, mat)))
    r_ring = min(rh * 1.42, r - 0.5)
    c = math.sqrt(r * r - r_ring * r_ring)
    out.append(ring_z(sy, cz - c, cz + c, rh, r_ring, mat))
    return out


BUIS_HOLE_MAX = 10.0            # 折りたたみ式の穴の上限（照門が目から遠い銃で、輪が受け部より太くならないように）


def default_irons(rail_top, rear_zc, front_zc, trigger_z=0.0):
    """実銃に照準器の無い銃のデフォルトのアイアンサイト（折りたたみ式の前後）。ボーン iron_sight に入れる
    （サイトのアタッチメントを付けたらコードがこのボーンを描かない → 07-model-assets.md）。
    戻り値: (部品, 照準線の高さ)。"""
    sy = rail_top + BUIS_HEIGHT
    eye = eye_z(trigger_z, rear_zc)
    hole = min(BUIS_HOLE_MAX, HOLE_ANGLE * (eye - rear_zc))
    return buis_rear(rail_top, sy, rear_zc, hole) + buis_front(rail_top, sy, front_zc, POST_ANGLE * (eye - front_zc)), sy
