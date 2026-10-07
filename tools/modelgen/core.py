"""
Bedrock Edition 形式（.geo.json）の銃モデルをスクリプトから生成するための最小ライブラリ。

- 座標系は docs/specs/07-model-assets.md の規約どおり（1単位=1px=1/16ブロック、銃口 -Z、上 +Y、左右対称面 X=0）
- UV は Per-face UV のみ出力する（Box UV はローダーが描画しないため、腕プレースホルダ以外では使わない）
- テクスチャは面ごとに矩形を割り当てて自動で詰め込み（作者が後から塗り直せる配置になる）、
  材質（Material）の色で塗った PNG を同時に出力する
- render() は BedrockGeometryLoader と同じ回転規則で描画するプレビュー（実機を見られない代わりの確認手段）
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
        return sum(len(b.cubes) for b in self.bones)


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
        mat = model.bones[bi].cubes[ci].mat
        _paint(img, u, v, w, h, mat, rng)
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
        if b.cubes:
            jb["cubes"] = []
            for ci, c in enumerate(b.cubes):
                jc: dict = {"origin": [_r(v) for v in c.origin], "size": [_r(v) for v in c.size]}
                if c.rotation and any(abs(a) > 1e-9 for a in c.rotation):
                    jc["pivot"] = [_r(v) for v in (c.pivot or _center(c))]
                    jc["rotation"] = [_r(v) for v in c.rotation]
                jc["uv"] = {f: {"uv": [u, v], "uv_size": [w, h]}
                            for f in c.faces for (u, v, w, h) in [uvs[(bi, ci, f)]]}
                jb["cubes"].append(jc)
        geo_bones.append(jb)
    return geo_bones, Image.fromarray(img, "RGBA"), size


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


def _paint(img, u, v, w, h, mat: Material, rng: random.Random):
    base = np.array(mat.color, dtype=np.float32)
    for yy in range(h):
        for xx in range(w):
            k = 1.0 + (rng.uniform(-1, 1) * mat.noise if mat.noise else 0.0)
            if mat.edge and w >= mat.edge_min and h >= mat.edge_min and (
                    xx in (0, w - 1) or yy in (0, h - 1)):
                k *= 1.0 - mat.edge
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
           ss: int = 2, background=(0, 0, 0, 0), skip_bones=("right_hand", "left_hand")) -> Image.Image:
    """正射影で描画する。yaw=90 で左側面（+X 側から -X を見る）。背景は既定で透明。"""
    texa = np.asarray(tex.convert("RGBA"), dtype=np.float32)
    th, tw = texa.shape[:2]
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    view = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    view = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ view
    light = np.array([0.35, 0.85, 0.4])
    light /= np.linalg.norm(light)

    quads = []
    for jb in geo_bones:
        if jb["name"] in skip_bones:
            continue
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
                quads.append((np.array(pts), uvs))

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
        n = np.cross(pts[1] - pts[0], pts[3] - pts[0])
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            continue
        n /= nn
        shade = 0.55 + 0.45 * max(0.0, float(n @ light))
        sx_ = vp[:, 0] * scale + off[0]
        sy_ = H - (vp[:, 1] * scale + off[1])
        for tri in ((0, 1, 2), (0, 2, 3)):
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
