"""
写真のトレース: 真横写真の銃のシルエットを、画素以下の精度の輪郭（等値線）で取り出し、部品ごとの範囲で切り出して mm の側面形にする。

  sil = photo_trace.Silhouette(photo, k=0.704, x0=307.5, y0=290.0, flip=True)
  outline = sil.part([(z0, y0), (z1, y0), ...])        # 範囲（mm の多角形）で切り出した輪郭

座標: 写真を左右反転して銃口を +x にそろえたうえで、Z = (x0 - x) / k、Y = (y0 - y) / k（k は px/mm、x0/y0 は Z=0/Y=0 の画素位置）。
写真の暗い部分＝銃とみなす（背景が白い商品写真を想定）。輪郭の内側の明るい穴（トリガーガードの中・サイトの穴等）も穴として残る。
写真は第三者の著作物であることが多いので、リポジトリには入れない（トレースした座標だけを入れる）。
"""
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from shapely.geometry import LineString, Polygon, MultiPolygon, box as sbox
from shapely.ops import polygonize, unary_union


class Silhouette:
    def __init__(self, photo, k, x0, y0, flip=True, thr=200, blur=0.6):
        img = Image.open(photo).convert("L")
        if flip:
            img = ImageOps.mirror(img)
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        self.a = np.asarray(img, dtype=float)
        self.k, self.x0, self.y0, self.thr = k, x0, y0, thr
        self.geom = self._trace()

    def _trace(self):
        import contourpy
        h, w = self.a.shape
        pad = np.full((h + 2, w + 2), 255.0)
        pad[1:-1, 1:-1] = self.a
        gen = contourpy.contour_generator(z=pad, line_type=contourpy.LineType.Separate)
        lines = [LineString([(x - 1, y - 1) for x, y in seg]) for seg in gen.lines(self.thr) if len(seg) > 3]
        faces = list(polygonize(unary_union(lines)))
        dark = []
        for f in faces:
            p = f.representative_point()
            if self.a[min(h - 1, int(p.y)), min(w - 1, int(p.x))] < self.thr:
                dark.append(f)
        g = unary_union(dark)
        # 画素座標 → mm（Z, Y）
        from shapely import affinity
        g = affinity.affine_transform(g, [-1 / self.k, 0, 0, -1 / self.k, self.x0 / self.k, self.y0 / self.k])
        return g

    def part(self, region, tol=0.5, minus=(), min_hole=60.0):
        """region（mm の多角形）で切り出した輪郭。minus の多角形は除く。最大の 1 片を返す。
        面積 min_hole [mm²] 未満の穴は捨てる（ピンの光りなど、穴ではない明るい点を拾うため）。"""
        g = self.geom.intersection(Polygon(region))
        for m in minus:
            g = g.difference(Polygon(m))
        if isinstance(g, MultiPolygon) or g.geom_type == "GeometryCollection":
            polys = [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
            g = max(polys, key=lambda p: p.area)
        g = g.simplify(tol, preserve_topology=True)
        r = lambda ring: [(round(x, 1), round(y, 1)) for x, y in list(ring.coords)[:-1]]
        return {"outer": r(g.exterior), "holes": [r(h) for h in g.interiors if Polygon(h).area >= min_hole]}

    def radius_profile(self, z_from, z_to, axis_y, step=2.0, band=30.0):
        """銃身などの丸い部品: 各 Z で軸の上下の輪郭までの距離（の平均）を半径とする。"""
        out = []
        z = z_from
        while (z_to - z) * (z_to - z_from) > 0 or z == z_from:
            seg = self.geom.intersection(LineString([(z, axis_y - band), (z, axis_y + band)]))
            if not seg.is_empty:
                ys = [y for line in getattr(seg, "geoms", [seg]) for _, y in line.coords]
                out.append((round(z, 1), round((max(ys) - min(ys)) / 2, 2)))
            z += step if z_to > z_from else -step
        return out
