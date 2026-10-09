"""
Bedrock Edition 形式（.geo.json）の銃モデルをスクリプトから生成するための最小ライブラリ。

- 座標系は docs/specs/07-model-assets.md の規約どおり（1単位=1px=1/16ブロック、銃口 -Z、上 +Y、左右対称面 X=0）
- UV は Per-face UV のみ出力する（Box UV はローダーが描画しないため、腕プレースホルダ以外では使わない）
- テクスチャは面ごとに矩形を割り当てて自動で詰め込み（作者が後から塗り直せる配置になる）、
  材質（Material）の色で塗った PNG を同時に出力する
- render() は BedrockGeometryLoader と同じ回転規則で描画するプレビュー（実機を見られない代わりの確認手段）
- メッシュ（MeshPart）はボーンの poly_mesh として出力する。形式は Blockbench の Meshy プラグイン
  （Shadowkitten47/Meshy）の書き出しに合わせる: positions は銃全体の共通座標（キューブの origin と同じ座標系）、
  normalized_uvs=true、UV の V は下端基準（1 - v）、polys は 4 頂点（三角形は先頭頂点を 4 つ目に重ねる）
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

FACES = ("north", "south", "west", "east", "up", "down")


# ---------------------------------------------------------------- 材質（テクスチャの塗り方）
@dataclass(frozen=True)
class Material:
    name: str
    color: tuple[int, int, int]
    noise: float = 0.0          # 1テクセルごとの明度ゆらぎ（0〜1）
    edge: float = 0.0           # 面の外周1テクセルを暗くする量（0〜1）。小さい面には掛からない
    edge_min: int = 4           # 外周を描く最小の面サイズ（テクセル）
    stripe: int = 0             # >0 なら stripe_faces の面に、銃の前後方向の縞（周期テクセル）。レールの刻みをテクスチャで表す
    stripe_dark: float = 0.45
    stripe_faces: tuple = ("up",)
    dots: int = 0               # >0 なら側面・上下面に周期 dots テクセルの暗い点（放熱孔など）


# ---------------------------------------------------------------- 形状
@dataclass
class Cube:
    origin: tuple[float, float, float]
    size: tuple[float, float, float]
    mat: Material
    rotation: tuple[float, float, float] | None = None
    pivot: tuple[float, float, float] | None = None
    faces: tuple[str, ...] = FACES

    def moved(self, dx: float, dy: float, dz: float) -> "Cube":
        o = (self.origin[0] + dx, self.origin[1] + dy, self.origin[2] + dz)
        p = None if self.pivot is None else (self.pivot[0] + dx, self.pivot[1] + dy, self.pivot[2] + dz)
        return Cube(o, self.size, self.mat, self.rotation, p, self.faces)

    def scaled(self, k: float) -> "Cube":
        """mm→px 変換などの一様スケール（回転角はそのまま）。"""
        o = tuple(v * k for v in self.origin)
        s = tuple(v * k for v in self.size)
        p = None if self.pivot is None else tuple(v * k for v in self.pivot)
        return Cube(o, s, self.mat, self.rotation, p, self.faces)


def box(x0, y0, z0, x1, y1, z1, mat, rotation=None, pivot=None) -> Cube:
    """2隅指定の直方体（順序は問わない）。"""
    lo = (min(x0, x1), min(y0, y1), min(z0, z1))
    hi = (max(x0, x1), max(y0, y1), max(z0, z1))
    return Cube(lo, (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]), mat, rotation, pivot)


def cbox(cx, cy, z0, z1, w, h, mat, rotation=None, pivot=None) -> Cube:
    """Z方向に伸びる、断面中心 (cx, cy)・幅 w・高さ h の直方体。"""
    return box(cx - w / 2, cy - h / 2, z0, cx + w / 2, cy + h / 2, z1, mat, rotation, pivot)


def round_rod(cx, cy, z0, z1, d, mat) -> list[Cube]:
    """Z方向の丸棒を、横長・縦長の直方体2本の十字重ねで近似する（キューブのみの制約下での丸断面。回転を使わない）。"""
    return [cbox(cx, cy, z0, z1, d, d * 0.7, mat), cbox(cx, cy, z0, z1, d * 0.7, d, mat)]


@dataclass
class MeshPart:
    """多角形メッシュ。faces は 3〜4 頂点（平面）。UV はチャート単位で矩形を割り当てる:
    同じ chart 番号の面は 1 枚の矩形を共有し、chart_uv（px 単位の展開座標）で貼る。"""
    verts: list
    faces: list                     # [[i, j, k(, l)], ...]
    mat: Material
    normals: list | None = None     # 面ごと・頂点ごとの法線 [[n0, n1, ...], ...]。None なら面法線
    charts: list | None = None      # 面ごとのチャート番号
    chart_uv: list | None = None    # 面ごと・頂点ごとの展開座標 [(s, t), ...]（px）
    chart_edge: dict = field(default_factory=dict)  # チャート番号 → 縁を暗くするか

    def scaled(self, k: float) -> "MeshPart":
        return MeshPart([tuple(c * k for c in v) for v in self.verts], self.faces, self.mat, self.normals,
                        self.charts, None if self.chart_uv is None else
                        [[(s * k, t * k) for s, t in f] for f in self.chart_uv], self.chart_edge)

    def finalize(self):
        """チャート未指定の面へ、平面投影のチャートを割り当てる。"""
        if self.charts is None:
            self.charts = [None] * len(self.faces)
            self.chart_uv = [None] * len(self.faces)
        nxt = max([c for c in self.charts if c is not None], default=-1) + 1
        for fi, f in enumerate(self.faces):
            if self.charts[fi] is not None:
                continue
            p = [np.array(self.verts[i], dtype=float) for i in f]
            n = np.cross(p[1] - p[0], p[2] - p[0])
            n /= np.linalg.norm(n) + 1e-12
            u = p[1] - p[0]
            u /= np.linalg.norm(u) + 1e-12
            v = np.cross(n, u)
            self.charts[fi] = nxt
            self.chart_uv[fi] = [(float((q - p[0]) @ u), float((q - p[0]) @ v)) for q in p]
            self.chart_edge.setdefault(nxt, len(f) == 4)
            nxt += 1
        return self


def lathe(cx, cy, profile, n, mat, cap0=True, cap1=True) -> MeshPart:
    """Z 軸まわりの回転体。profile=[(z, r), ...]（z 昇順）。側面は区間ごとに 1 本の帯へ展開する。"""
    verts, faces, normals, charts, cuv = [], [], [], [], []
    ring = []
    for z, r in profile:
        idx = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            idx.append(len(verts))
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        ring.append(idx)
    edge = {}
    for si in range(len(profile) - 1):
        (z0, r0), (z1, r1) = profile[si], profile[si + 1]
        circ = 2 * math.pi * max(r0, r1)
        for k in range(n):
            k2 = (k + 1) % n
            a0, a1 = 2 * math.pi * (k + 0.5) / n, 2 * math.pi * (k + 1.5) / n
            faces.append([ring[si][k], ring[si][k2], ring[si + 1][k2], ring[si + 1][k]])
            normals.append([(math.cos(a0), math.sin(a0), 0), (math.cos(a1), math.sin(a1), 0),
                            (math.cos(a1), math.sin(a1), 0), (math.cos(a0), math.sin(a0), 0)])
            s0, s1 = circ * k / n, circ * (k + 1) / n
            charts.append(si)
            cuv.append([(s0, 0), (s1, 0), (s1, z1 - z0), (s0, z1 - z0)])
        edge[si] = "rows"  # 帯の継ぎ目（周方向の端）は暗くしない
    m = MeshPart(verts, faces, mat, normals, charts, cuv, edge)
    for ri, cap, nz in ((0, cap0, -1), (len(profile) - 1, cap1, 1)):
        if not cap or profile[ri][1] <= 0:
            continue
        c = len(m.verts)
        m.verts.append((cx, cy, profile[ri][0]))
        for k in range(n):
            m.faces.append([c, ring[ri][k], ring[ri][(k + 1) % n]])
            m.normals.append([(0, 0, nz)] * 3)
            m.charts.append(None)
            m.chart_uv.append(None)
    return m.finalize()


def extrude_x(profile, x0, x1, mat) -> MeshPart:
    """側面形状 profile=[(z, y), ...]（単純多角形）を X 方向 x0〜x1 に押し出す。側面は 1 本の帯へ展開する。"""
    pts = list(profile)
    if _area2(pts) < 0:
        pts.reverse()
    n = len(pts)
    verts = [(x0, y, z) for z, y in pts] + [(x1, y, z) for z, y in pts]
    faces, charts, cuv = [], [], []
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        seg = math.dist(pts[i], pts[j])
        faces.append([i, j, n + j, n + i])
        charts.append(0)
        cuv.append([(s, 0), (s + seg, 0), (s + seg, x1 - x0), (s, x1 - x0)])
        s += seg
    for tri in _triangulate(pts):
        faces.append([tri[0], tri[2], tri[1]])
        charts.append(None)
        cuv.append(None)
        faces.append([n + t for t in tri])
        charts.append(None)
        cuv.append(None)
    return MeshPart(verts, faces, mat, None, charts, cuv, {0: "rows"}).finalize()


def extrude_x_beveled(profile, x0, x1, bevel, mat, steps=2) -> MeshPart:
    """extrude_x の角丸め版。X 方向の両端で輪郭を内側へ縮め（1/4 円を steps 段で近似）、
    グリップ・ストックのような「角の丸い樹脂部品」を作る。"""
    pts = list(profile)
    if _area2(pts) < 0:
        pts.reverse()
    n = len(pts)
    rings = []  # (x, inset)
    for k in range(steps, -1, -1):
        t = math.pi / 2 * k / steps
        rings.append((x0 + bevel * (1 - math.sin(t)), bevel * (1 - math.cos(t))))
    for k in range(0, steps + 1):
        t = math.pi / 2 * k / steps
        rings.append((x1 - bevel * (1 - math.sin(t)), bevel * (1 - math.cos(t))))
    verts, ring_idx = [], []
    for x, d in rings:
        off = _inset(pts, d) if d > 1e-9 else pts
        ring_idx.append(list(range(len(verts), len(verts) + n)))
        verts.extend((x, y, z) for z, y in off)
    perim = [0.0]
    for i in range(n):
        perim.append(perim[-1] + math.dist(pts[i], pts[(i + 1) % n]))
    faces, charts, cuv = [], [], []
    t_acc = [0.0]
    for r in range(len(rings) - 1):
        (xa, da), (xb, db) = rings[r], rings[r + 1]
        t_acc.append(t_acc[-1] + math.hypot(xb - xa, db - da))
    for r in range(len(rings) - 1):
        if abs(rings[r + 1][0] - rings[r][0]) < 1e-9 and abs(rings[r + 1][1] - rings[r][1]) < 1e-9:
            continue
        for i in range(n):
            j = (i + 1) % n
            faces.append([ring_idx[r][i], ring_idx[r][j], ring_idx[r + 1][j], ring_idx[r + 1][i]])
            charts.append(0)
            cuv.append([(perim[i], t_acc[r]), (perim[i + 1], t_acc[r]),
                        (perim[i + 1], t_acc[r + 1]), (perim[i], t_acc[r + 1])])
    first, last = ring_idx[0], ring_idx[-1]
    # 端面の三角形分割は元の輪郭で行い、縮めた輪郭の頂点に当てはめる（縮めた輪郭は点が詰まって分割に失敗しやすい）
    for tri in _triangulate(pts):
        faces.append([first[tri[0]], first[tri[2]], first[tri[1]]])
        charts.append(None)
        cuv.append(None)
        faces.append([last[t] for t in tri])
        charts.append(None)
        cuv.append(None)
    return MeshPart(verts, faces, mat, None, charts, cuv, {0: "rows"}).finalize()


def inflate_x(profile, half_w, mat, steps=5, width_fn=None, radius_fn=None) -> MeshPart:
    """側面形状を左右に「膨らませた」立体（断面が楕円状）。グリップのような丸い樹脂部品用。
    輪郭の各点で丸みの半径 r を変えられる: r = half_w なら縁は X=0 の稜線まで丸まり（前後のストラップ）、
    小さい r なら縁に平らな帯が残る（底面など）。
    width_fn(z, y, f) → 幅の倍率。f はその高さでの前後位置（0=前端, 1=後端）。
    radius_fn(nz, ny) → 丸みの半径。(nz, ny) は輪郭のその点での外向き法線（側面図）。"""
    pts = list(profile)
    if _area2(pts) < 0:
        pts.reverse()
    n = len(pts)
    H = half_w
    ts = [math.pi / 2 * k / steps for k in range(steps + 1)]
    full = [pts if k == 0 else _inset(pts, H * (1 - math.cos(t))) for k, t in enumerate(ts)]

    radii = []
    for i in range(n):
        (z0, y0), (z1, y1), (z2, y2) = pts[i - 1], pts[i], pts[(i + 1) % n]
        nz, ny = (y2 - y0), -(z2 - z0)            # 反時計回りの外向き法線（側面図）
        ln = math.hypot(nz, ny) or 1.0
        r = H if radius_fn is None else min(H, max(0.5, radius_fn(nz / ln, ny / ln)))
        radii.append(r)

    def span(y):
        xs = []
        for i in range(n):
            (za, ya), (zb, yb) = pts[i], pts[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(za + (y - ya) * (zb - za) / (yb - ya))
        return (min(xs), max(xs)) if len(xs) >= 2 else None

    def scale(z, y):
        if width_fn is None:
            return 1.0
        sp = span(y)
        f = 0.5 if sp is None or sp[1] - sp[0] < 1e-6 else min(1.0, max(0.0, (z - sp[0]) / (sp[1] - sp[0])))
        return width_fn(z, y, f)

    verts, ring_idx = [], {}
    for side in (-1, 1):
        for k, t in enumerate(ts):
            idx = []
            for i in range(n):
                r = radii[i]
                bz, by = pts[i]
                fz, fy = full[k][i]
                kk = r / H
                z, y = bz + (fz - bz) * kk, by + (fy - by) * kk   # その点の半径ぶんだけ内側へ
                x = (H - r) + r * math.sin(t)
                idx.append(len(verts))
                verts.append((side * x * scale(bz, by), y, z))
            ring_idx[(side, k)] = idx
    perim = [0.0]
    for i in range(n):
        perim.append(perim[-1] + math.dist(pts[i], pts[(i + 1) % n]))
    faces, charts, cuv = [], [], []
    for side in (-1, 1):
        t_acc = 0.0
        for k in range(steps):
            a, b = ring_idx[(side, k)], ring_idx[(side, k + 1)]
            dt = H * (ts[k + 1] - ts[k])
            for i in range(n):
                j = (i + 1) % n
                faces.append([a[i], a[j], b[j], b[i]] if side == 1 else [a[j], a[i], b[i], b[j]])
                charts.append(0 if side == 1 else 1)
                s0, s1 = (perim[i], perim[i + 1]) if side == 1 else (perim[i + 1], perim[i])
                cuv.append([(s0, t_acc), (s1, t_acc), (s1, t_acc + dt), (s0, t_acc + dt)])
            t_acc += dt
        cap = ring_idx[(side, steps)]
        for tri in _triangulate(pts):
            faces.append([cap[t] for t in (tri if side == 1 else (tri[0], tri[2], tri[1]))])
            charts.append(None)
            cuv.append(None)
    # 縁の帯（左右の稜線をつなぐ。半径 = half_w の点では幅 0）
    a, b = ring_idx[(-1, 0)], ring_idx[(1, 0)]
    for i in range(n):
        j = (i + 1) % n
        faces.append([a[i], a[j], b[j], b[i]])
        charts.append(2)
        w = 2 * (H - max(radii[i], radii[j]) * 0.999)
        cuv.append([(perim[i], 0), (perim[i + 1], 0), (perim[i + 1], max(w, 0.01)), (perim[i], max(w, 0.01))])
    return MeshPart(verts, faces, mat, None, charts, cuv, {0: False, 1: False, 2: False}).finalize()


def _inset(pts, d):
    """反時計回り多角形を内側へ d だけ縮め、元の各頂点に対応する点を返す（頂点数は元と同じ）。
    shapely の buffer で正しく縮めた輪郭に、元の頂点を最近点で投影する。曲率のきつい角（半径 < d）でも
    輪郭が裏返らない。shapely が無ければ単純な辺の平行移動（きつい角で破綻しうる）にフォールバックする。"""
    try:
        from shapely.geometry import Point, Polygon
    except ImportError:
        return _inset_naive(pts, d)
    poly = Polygon(pts).buffer(-d, join_style="round", quad_segs=8)
    if poly.geom_type != "Polygon" or poly.is_empty:
        poly = max(getattr(poly, "geoms", [poly]), key=lambda g: g.area)
    ring = poly.exterior
    out = []
    for q in pts:
        c = ring.interpolate(ring.project(Point(q)))
        out.append((c.x, c.y))
    return out


def _inset_naive(pts, d):
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        n1 = (-e1[1] / l1, e1[0] / l1)
        n2 = (-e2[1] / l2, e2[0] / l2)
        k = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        k = max(k, 0.25)  # 鋭角の頂点で極端に飛び出さないよう制限
        out.append((p1[0] + d * (n1[0] + n2[0]) / k, p1[1] + d * (n1[1] + n2[1]) / k))
    return out


def smooth(points, per_seg=6):
    """Catmull-Rom（centripetal）で点列をなめらかな曲線に補間する（端点を通る開いた曲線）。"""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = (np.array(pts[k], dtype=float) for k in (i - 1, i, i + 1, i + 2))
        def tj(ti, a, b):
            return ti + max(np.linalg.norm(b - a), 1e-6) ** 0.5
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        for k in range(per_seg):
            t = t1 + (t2 - t1) * k / per_seg
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            c = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2
            out.append((float(c[0]), float(c[1])))
    out.append(tuple(points[-1]))
    return out


def _area2(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def _triangulate(p):
    """耳切り法（反時計回りの単純多角形）。"""
    idx = list(range(len(p)))
    out = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            ax, ay = p[a]; bx, by = p[b]; cx, cy = p[c]
            if (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) <= 1e-12:
                continue
            if any(_in_tri(p[o], p[a], p[b], p[c]) for o in idx if o not in (a, b, c)):
                continue
            out.append((a, b, c))
            idx.pop(k)
            break
        else:
            raise ValueError("三角形分割に失敗（自己交差した輪郭）")
    out.append(tuple(idx))
    return out


def _in_tri(q, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(q, a, b), s(q, b, c), s(q, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


@dataclass
class Bone:
    name: str
    parent: str | None
    pivot: tuple[float, float, float]
    cubes: list[Cube] = field(default_factory=list)
    raw: dict | None = None     # 既存モデルから流用するボーン（腕プレースホルダ等）をそのまま出す


@dataclass
class Model:
    bones: list[Bone] = field(default_factory=list)

    def bone(self, name, parent, pivot, cubes=None) -> Bone:
        b = Bone(name, parent, tuple(round(v, 4) for v in pivot), list(cubes or []))
        self.bones.append(b)
        return b

    def raw_bone(self, data: dict) -> None:
        self.bones.append(Bone(data["name"], data.get("parent"), tuple(data["pivot"]), raw=data))

    def get(self, name) -> Bone:
        return next(b for b in self.bones if b.name == name)

    @property
    def cube_count(self) -> int:
        return sum(1 for b in self.bones for c in b.cubes if isinstance(c, Cube))

    @property
    def mesh_face_count(self) -> int:
        return sum(len(c.faces) for b in self.bones for c in b.cubes if isinstance(c, MeshPart))


# ---------------------------------------------------------------- UV 展開＋テクスチャ
def _face_dims(c: Cube, face: str) -> tuple[float, float]:
    sx, sy, sz = c.size
    return {"north": (sx, sy), "south": (sx, sy), "west": (sz, sy), "east": (sz, sy),
            "up": (sx, sz), "down": (sx, sz)}[face]


def bake(model: Model, density: float, seed: int = 1, max_size: int = 1024):
    """面ごとの UV 矩形を割り当て、(geo.json の dict, テクスチャ Image, テクスチャ一辺) を返す。"""
    items = []  # (h, w, bone_idx, cube_idx, face)
    for bi, b in enumerate(model.bones):
        for ci, c in enumerate(b.cubes):
            if isinstance(c, MeshPart):
                for ch in sorted(set(c.charts)):
                    pts = [q for fi, f in enumerate(c.faces) if c.charts[fi] == ch for q in c.chart_uv[fi]]
                    s0, t0 = min(q[0] for q in pts), min(q[1] for q in pts)
                    w = max(1, math.ceil((max(q[0] for q in pts) - s0) * density - 1e-6))
                    h = max(1, math.ceil((max(q[1] for q in pts) - t0) * density - 1e-6))
                    items.append((h, w, bi, ci, ("chart", ch, s0, t0)))
                continue
            for f in c.faces:
                fw, fh = _face_dims(c, f)
                w = max(1, math.ceil(fw * density - 1e-6))
                h = max(1, math.ceil(fh * density - 1e-6))
                items.append((h, w, bi, ci, f))
    items.sort(key=lambda t: (-t[0], -t[1]))

    size = 16
    while True:
        placed = _shelf_pack(items, size)
        if placed is not None:
            break
        size *= 2
        if size > max_size:
            raise ValueError(f"テクスチャが {max_size}px に収まらない（density を下げる）")

    rng = random.Random(seed)
    img = np.zeros((size, size, 4), dtype=np.uint8)
    uvs: dict[tuple[int, int, str], tuple[int, int, int, int]] = {}
    for (h, w, bi, ci, f), (u, v) in placed.items():
        el = model.bones[bi].cubes[ci]
        if isinstance(f, tuple):
            mode = el.chart_edge.get(f[1])
            _paint(img, u, v, w, h, el.mat, rng, "mesh_rows" if mode == "rows" else "mesh" if mode else "mesh_flat")
            uvs[(bi, ci, f[1])] = (u, v, f[2], f[3])
            continue
        _paint(img, u, v, w, h, el.mat, rng, f)
        uvs[(bi, ci, f)] = (u, v, w, h)

    geo_bones = []
    for bi, b in enumerate(model.bones):
        if b.raw is not None:
            geo_bones.append(b.raw)
            continue
        jb: dict = {"name": b.name}
        if b.parent:
            jb["parent"] = b.parent
        jb["pivot"] = [_r(v) for v in b.pivot]
        meshes = [(ci, c) for ci, c in enumerate(b.cubes) if isinstance(c, MeshPart)]
        if meshes:
            jb["poly_mesh"] = _poly_mesh(meshes, bi, uvs, density, size)
        if any(isinstance(c, Cube) for c in b.cubes):
            jb["cubes"] = []
            for ci, c in enumerate(b.cubes):
                if isinstance(c, MeshPart):
                    continue
                jc: dict = {"origin": [_r(v) for v in c.origin], "size": [_r(v) for v in c.size]}
                if c.rotation and any(abs(a) > 1e-9 for a in c.rotation):
                    jc["pivot"] = [_r(v) for v in (c.pivot or _center(c))]
                    jc["rotation"] = [_r(v) for v in c.rotation]
                jc["uv"] = {f: {"uv": [u, v], "uv_size": [w, h]}
                            for f in c.faces for (u, v, w, h) in [uvs[(bi, ci, f)]]}
                jb["cubes"].append(jc)
        geo_bones.append(jb)
    return geo_bones, Image.fromarray(img, "RGBA"), size


def _poly_mesh(meshes, bi, uvs, density, size):
    pm = {"normalized_uvs": True, "positions": [], "normals": [], "uvs": [], "polys": []}
    nmap, umap = {}, {}

    def idx(table, key, val):
        if key not in table:
            table[key] = len(pm[val[0]])
            pm[val[0]].append(val[1])
        return table[key]

    for ci, m in meshes:
        base = len(pm["positions"])
        pm["positions"].extend([[_r(c) for c in v] for v in m.verts])
        for fi, f in enumerate(m.faces):
            if m.normals is not None:
                ns = m.normals[fi]
            else:
                p = [np.array(m.verts[i]) for i in f]
                n = np.cross(p[1] - p[0], p[2] - p[0])
                n = n / (np.linalg.norm(n) + 1e-12)
                ns = [tuple(n)] * len(f)
            u0, v0, s0, t0 = uvs[(bi, ci, m.charts[fi])]
            poly = []
            for k, vi in enumerate(f):
                nn = tuple(round(float(c), 4) + 0.0 for c in ns[k])
                s, t = m.chart_uv[fi][k]
                uv = (round((u0 + (s - s0) * density) / size, 5),
                      round(1 - (v0 + (t - t0) * density) / size, 5))
                poly.append([base + vi, idx(nmap, nn, ("normals", list(nn))), idx(umap, uv, ("uvs", list(uv)))])
            while len(poly) < 4:
                poly.append(poly[0])
            pm["polys"].append(poly)
    return pm


def _shelf_pack(items, size):
    x = y = row_h = 0
    out = {}
    for it in items:
        h, w = it[0], it[1]
        if w > size:
            return None
        if x + w > size:
            x, y, row_h = 0, y + row_h, 0
        if y + h > size:
            return None
        out[it] = (x, y)
        x += w
        row_h = max(row_h, h)
    return out


def _paint(img, u, v, w, h, mat: Material, rng: random.Random, face: str):
    base = np.array(mat.color, dtype=np.float32)
    for yy in range(h):
        for xx in range(w):
            k = 1.0 + (rng.uniform(-1, 1) * mat.noise if mat.noise else 0.0)
            if mat.edge and face != "mesh_flat" and w >= mat.edge_min and h >= mat.edge_min and (
                    (xx in (0, w - 1) and face != "mesh_rows") or yy in (0, h - 1)):
                k *= 1.0 - mat.edge
            if mat.stripe and face in mat.stripe_faces and \
                    ((xx if face in ("east", "west") else yy) % mat.stripe) < mat.stripe // 2:
                k *= 1.0 - mat.stripe_dark
            if mat.dots and face not in ("north", "south", "mesh_flat") and w >= mat.dots and h >= mat.dots \
                    and xx % mat.dots == mat.dots // 2 and yy % mat.dots == mat.dots // 2 \
                    and 0 < xx < w - 1 and 0 < yy < h - 1:
                k *= 0.25
            c = np.clip(base * k, 0, 255)
            img[v + yy, u + xx] = (*c.astype(np.uint8), 255)


def _r(v: float) -> float:
    r = round(float(v), 4)
    return 0.0 if r == 0 else r


def _center(c: Cube):
    return tuple(c.origin[i] + c.size[i] / 2 for i in range(3))


def write_geo(path: Path, geo_bones, tex_size: int, bounds=(4, 4)):
    data = {
        "format_version": "1.21.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": f"geometry.{path.name.removesuffix('.geo.json')}",
                "texture_width": tex_size,
                "texture_height": tex_size,
                "visible_bounds_width": bounds[0],
                "visible_bounds_height": bounds[1],
                "visible_bounds_offset": [0, 1, 0],
            },
            "bones": geo_bones,
        }],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- プレビュー描画（Zバッファ・テクスチャ付き）
def _rot_raw(rot):
    """BedrockGeometryLoader#cubeRotationQuat と同じ回転を、生の Bedrock 座標で表した行列。
    Java側: Rz(z)·Ry(-y)·Rx(-x)（X符号反転座標）→ 生座標では Rz(-z)·Ry(y)·Rx(-x)。"""
    x, y, z = (math.radians(a) for a in rot)
    def rx(a):
        return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    def ry(a):
        return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    def rz(a):
        return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    return rz(-z) @ ry(y) @ rx(-x)


_FACE_CORNERS = {  # (xSel, ySel, zSel) × 4、BedrockGeometryLoader#bakeCube と同じ順
    "north": [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)],
    "south": [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    "west": [(0, 0, 1), (0, 0, 0), (0, 1, 0), (0, 1, 1)],
    "east": [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)],
    "up": [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)],
    "down": [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
}
_FACE_UV = [(0, 0), (1, 0), (1, 1), (0, 1)]


def render(geo_bones, tex: Image.Image, yaw: float, pitch: float, width: int = 900,
           ss: int = 2, background=(0, 0, 0, 0), skip_bones=("right_hand", "left_hand"),
           fixed=None) -> Image.Image:
    """正射影で描画する。yaw=90 で左側面（+X 側から -X を見る）。背景は既定で透明。
    fixed=(倍率, x0, y0, 幅, 高さ) を渡すと自動の拡大縮小をやめ、画面座標 = (x*倍率 + x0, y0 - y*倍率) で描く
    （写真との重ね合わせ用）。"""
    texa = np.asarray(tex.convert("RGBA"), dtype=np.float32)
    th, tw = texa.shape[:2]
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    view = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    view = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ view
    light = np.array([0.35, 0.85, 0.4])
    light /= np.linalg.norm(light)

    # ボーンの回転（アニメーションの姿勢確認用）: 親から順に「回転軸まわりの回転」を重ねる。回転の規則はキューブと同じ
    by_name = {jb["name"]: jb for jb in geo_bones}
    world = {}

    def bone_world(name):
        if name in world:
            return world[name]
        jb = by_name[name]
        m = np.eye(4)
        if jb.get("rotation") and any(abs(a) > 1e-9 for a in jb["rotation"]):
            pv = np.array(jb.get("pivot", [0, 0, 0]), dtype=float)
            m[:3, :3] = _rot_raw(jb["rotation"])
            m[:3, 3] = pv - m[:3, :3] @ pv
        parent = jb.get("parent")
        world[name] = (bone_world(parent) @ m) if parent in by_name else m
        return world[name]

    quads = []
    for jb in geo_bones:
        if jb["name"] in skip_bones:
            continue
        Wm = bone_world(jb["name"])
        place = (lambda q: q) if np.allclose(Wm, np.eye(4)) else (lambda q, Wm=Wm: q @ Wm[:3, :3].T + Wm[:3, 3])
        pm = jb.get("poly_mesh")
        if pm:
            for poly in pm["polys"]:
                uniq = []
                for c in poly:
                    if not uniq or c != uniq[-1]:
                        uniq.append(c)
                if len(uniq) > 1 and uniq[-1] == uniq[0]:
                    uniq.pop()
                pts = np.array([pm["positions"][c[0]] for c in uniq], dtype=float)
                uvl = []
                for c in uniq:
                    u, v = pm["uvs"][c[2]]
                    uvl.append((u, 1 - v) if pm.get("normalized_uvs") else (u / tw, 1 - v / th))
                pts = place(pts)
                for k in range(1, len(uniq) - 1):
                    quads.append((pts[[0, k, k + 1]], [uvl[0], uvl[k], uvl[k + 1]]))
        for jc in jb.get("cubes", []):
            uv = jc.get("uv")
            if not isinstance(uv, dict):
                continue
            o = np.array(jc["origin"], dtype=float)
            s = np.array(jc["size"], dtype=float)
            R = _rot_raw(jc["rotation"]) if "rotation" in jc else None
            pv = np.array(jc.get("pivot", o + s / 2), dtype=float)
            for f, fd in uv.items():
                pts = []
                for sel in _FACE_CORNERS[f]:
                    p = o + s * np.array(sel)
                    if R is not None:
                        p = R @ (p - pv) + pv
                    pts.append(p)
                u0, v0 = fd["uv"]
                uw, vh = fd["uv_size"]
                uvs = [((u0 + a * uw) / tw, (v0 + b * vh) / th) for a, b in _FACE_UV]
                quads.append((place(np.array(pts)), uvs))

    if fixed is not None:
        fs, fx0, fy0, fw, fh = fixed
        W, H, scale = fw * ss, fh * ss, fs * ss
        off = np.array([fx0 * ss, H - fy0 * ss])
    else:
        allp = np.concatenate([q[0] for q in quads]) @ view.T
        lo, hi = allp[:, :2].min(0), allp[:, :2].max(0)
        span = hi - lo
        W = width * ss
        scale = (W * 0.94) / span[0]
        H = int(span[1] * scale / 0.94) + 2 * ss
        off = np.array([W * 0.03, H * 0.03]) - lo * scale * np.array([1, 1])
    color = np.zeros((H, W, 4), dtype=np.float32)
    color[:] = background
    depth = np.full((H, W), -1e9, dtype=np.float32)

    for pts, uvs in quads:
        vp = pts @ view.T
        n = np.cross(pts[1] - pts[0], pts[-1] - pts[0])
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            continue
        n /= nn
        shade = 0.55 + 0.45 * abs(float(n @ light))
        sx_ = vp[:, 0] * scale + off[0]
        sy_ = H - (vp[:, 1] * scale + off[1])
        for tri in (((0, 1, 2), (0, 2, 3)) if len(pts) == 4 else ((0, 1, 2),)):
            _raster(color, depth, texa, sx_[list(tri)], sy_[list(tri)], vp[list(tri), 2],
                    [uvs[i] for i in tri], shade, tw, th)
    img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8), "RGBA")
    return img.resize((W // ss, H // ss), Image.LANCZOS)


def _raster(color, depth, texa, xs, ys, zs, uvs, shade, tw, th):
    H, W = depth.shape
    x0, x1 = max(int(math.floor(xs.min())), 0), min(int(math.ceil(xs.max())), W - 1)
    y0, y1 = max(int(math.floor(ys.min())), 0), min(int(math.ceil(ys.max())), H - 1)
    if x1 < x0 or y1 < y0:
        return
    area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
    if abs(area) < 1e-9:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
    w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
    w2 = 1 - w0 - w1
    m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not m.any():
        return
    z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
    sub = depth[y0:y1 + 1, x0:x1 + 1]
    m &= z > sub
    if not m.any():
        return
    u = w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]
    v = w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]
    tu = np.clip((u * tw).astype(int), 0, tw - 1)
    tv = np.clip((v * th).astype(int), 0, th - 1)
    c = texa[tv, tu]
    sub[m] = z[m]
    out = color[y0:y1 + 1, x0:x1 + 1]
    out[m, :3] = c[m, :3] * shade
    out[m, 3] = 255
