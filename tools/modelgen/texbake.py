"""
テクスチャの仕上げ: 陰影の焼き込みと、汚れ・擦れ・埃を 3D の位置で塗る（core.bake の最後に呼ぶ。core.SHADE）。

なぜ要るか（作者の実機確認「テクスチャが気になる」の調査。docs/specs/07-model-assets.md）:
  - ゲームの光は面の向きでしか明暗が付かない。同じ向きの面はどこも同じ明るさで、部品の角・隙間・重なりが読めず、
    暗い色の銃は 1 つの黒い塊に見えた。→ テクセルごとの「開け具合」から、凹んだ所を暗く（遮蔽）、角を明るく
    （擦れて地が出る）塗り、上を向いた面を少し明るくする。
  - 汚れ・擦れの模様を面の区画ごとに別々の乱数で作っていたため、隣り合う区画の継ぎ目で模様が途切れ、
    パッチワークのまだらに見えた。→ 模様を 3D の位置の関数にし、区画をまたいでつながるようにする。

仕組み:
  1. 書き出した geo（poly_mesh・cubes）の三角形を UV の上で塗りつぶし、テクセルごとの位置 [px]・法線・ボーンを得る。
  2. 開け具合 = 全方向のうち、他の面に遮られずに外が見える方向の割合（平らな面 ≈ 0.47、角 > 0.5、凹み < 0.47）。
     方向ごとに、表面の点（テクセル）を投影した深さの地図（シャドウマップ）で遮られるかを判定する（numpy だけ）。
     弾倉・ボルトなど動かす部品は、外したり動かしたりしたときに変な影が残らないよう、自分の形だけで遮る。
  3. 開け具合を、同じ面の近くのテクセルだけで平均してならす（深さの地図の格子のむらを消す）。
"""
import math

import numpy as np

from core import _FACE_CORNERS, _FACE_UV, _rot_raw

N_DIRS = 96             # 方向の数（球面に均等）
SKIP = ("right_hand", "left_hand", "rightItem", "leftItem")
# 動かす部品（自分の形だけで遮る）。名前の先頭で判定
MOVING = ("magazin", "mag_ammo", "ammo", "bullet", "bolt", "charging_handle", "trigger", "selector", "mag_release",
          "port_cover", "slide_stop", "bipod", "feed_cover", "handle", "pump", "lever", "sight_leaf", "safety")

# 仕上げの強さ（全材質共通）
AO_FLOOR = 0.30         # いちばん奥まった所の明るさ（平らな面＝1）
AO_GAMMA = 0.9
SKY = 0.16              # 上を向いた面を明るく・下を向いた面を暗く（±SKY/2）
EDGE_LIGHT = 0.60       # 角を明るくする量（全材質。擦れとは別の「角に光が当たる」分）
WOODS = ("m79_stock", "m79_forend")     # 名前に wood が無い木の材質
FLAT_OPEN = 0.47        # 平らで開けた面の開け具合（この方式の値。裏側の方向は数えない）
EDGE_PROBE = 2.5        # 角の度合いを測る点を面から浮かせる距離 [マス]（角の明るい帯の幅になる）


# ---------------------------------------------------------------- テクセルの位置
def _triangles(geo_bones, tw, th):
    """(位置 3×3 [px], UV 3×2 [テクセル], 法線 3×3, ボーン番号) の並び。ボーンの回転は無い前提（書き出し直後）。"""
    out = []
    for bi, jb in enumerate(geo_bones):
        if jb["name"] in SKIP:
            continue
        pm = jb.get("poly_mesh")
        if pm:
            P = np.asarray(pm["positions"], float)
            Nn = np.asarray(pm["normals"], float) if pm.get("normals") else None
            U = np.asarray(pm["uvs"], float)
            for poly in pm["polys"]:
                uniq = []
                for c in poly:
                    if not uniq or c != uniq[-1]:
                        uniq.append(c)
                if len(uniq) > 1 and uniq[-1] == uniq[0]:
                    uniq.pop()
                for k in range(1, len(uniq) - 1):
                    t = [uniq[0], uniq[k], uniq[k + 1]]
                    p = P[[c[0] for c in t]]
                    uv = U[[c[2] for c in t]]
                    if pm.get("normalized_uvs"):
                        uv = np.c_[uv[:, 0] * tw, (1 - uv[:, 1]) * th]
                    n = Nn[[c[1] for c in t]] if Nn is not None else np.repeat(
                        [np.cross(p[1] - p[0], p[2] - p[0])], 3, 0)
                    out.append((p, uv, n, bi))
        for jc in jb.get("cubes", []):
            uvd = jc.get("uv")
            if not isinstance(uvd, dict):
                continue
            o, s = np.array(jc["origin"], float), np.array(jc["size"], float)
            R = _rot_raw(jc["rotation"]) if "rotation" in jc else None
            pv = np.array(jc.get("pivot", o + s / 2), float)
            ctr = o + s / 2
            ctr_w = R @ (ctr - pv) + pv if R is not None else ctr
            for f, fd in uvd.items():
                pts = []
                for sel in _FACE_CORNERS[f]:
                    q = o + s * np.array(sel)
                    if R is not None:
                        q = R @ (q - pv) + pv
                    pts.append(q)
                pts = np.array(pts)
                u0, v0 = fd["uv"]
                uw, vh = fd["uv_size"]
                uv = np.array([(u0 + a * uw, v0 + b * vh) for a, b in _FACE_UV])
                n = np.cross(pts[1] - pts[0], pts[3] - pts[0])
                if n @ (pts.mean(0) - ctr_w) < 0:
                    n = -n
                for t in ((0, 1, 2), (0, 2, 3)):
                    out.append((pts[list(t)], uv[list(t)], np.repeat([n], 3, 0), bi))
    return out


def texel_points(geo_bones, size):
    """テクセルごとの位置 [px]・法線（単位）・ボーン番号と、三角形に中心が入ったかの印。"""
    pos = np.zeros((size, size, 3), np.float32)
    nrm = np.zeros((size, size, 3), np.float32)
    bone = np.full((size, size), -1, np.int32)
    used = np.zeros((size, size), bool)
    for p, uv, n, bi in _triangles(geo_bones, size, size):
        xs, ys = uv[:, 0], uv[:, 1]
        area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
        if abs(area) < 1e-9:
            continue
        x0, x1 = max(int(math.floor(xs.min())), 0), min(int(math.ceil(xs.max())), size - 1)
        y0, y1 = max(int(math.floor(ys.min())), 0), min(int(math.ceil(ys.max())), size - 1)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
        w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not m.any():
            continue
        W = np.stack([w0[m], w1[m], w2[m]], 1)
        yy, xx = np.nonzero(m)
        yy += y0; xx += x0
        pos[yy, xx] = W @ p
        nn = W @ (n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12))
        nrm[yy, xx] = nn / (np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12)
        bone[yy, xx] = bi
        used[yy, xx] = True
    return pos, nrm, bone, used


def _fill(arrs, used, region, iters=4):
    """三角形に中心が入らなかった区画の縁のテクセルを、同じ区画（region が同じ値）の隣のテクセルの値で埋める。"""
    arrs = [a.copy() for a in arrs]
    u = used.copy()
    for _ in range(iters):
        new_vals = None
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            su = np.roll(np.roll(u, dy, 0), dx, 1) & (np.roll(np.roll(region, dy, 0), dx, 1) == region)
            take = (~u) & su & (region >= 0)
            if new_vals is None:
                new_vals = take.copy()
            for a in arrs:
                src = np.roll(np.roll(a, dy, 0), dx, 1)
                a[take] = src[take]
            u = u | take
        if new_vals is None or not new_vals.any():
            break
    return arrs, u


# ---------------------------------------------------------------- 開け具合
def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], 1)


def openness(P, Nm, group, cell, n_dirs=N_DIRS):
    """点ごとの開け具合（面の表側の方向のうち外が見える割合）・上半球の重み付きの開け具合（空の明るさ）・
    角の度合い（面から EDGE_PROBE マス浮かせた点から、全方向のうち外が見える割合。平らな面では面の下の方向が
    自分の面で遮られて約半分、角では面の端の向こうも見えて増え、凹みでは減る）。
    group: 点ごとの遮り方の組（0 = 全体で遮る。それ以外 = 同じ組の点だけで遮る）。"""
    bias = cell * 1.5
    Q = P + Nm * cell * 0.75            # 面から少し浮かせて自分の面で遮らないように
    Q2 = P + Nm * cell * EDGE_PROBE
    vis = np.zeros(len(P), np.float32)
    vis2 = np.zeros(len(P), np.float32)
    sky = np.zeros(len(P), np.float32)
    wsky = 0.0
    groups = np.unique(group)
    for d in fib_dirs(n_dirs):
        a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
        e1 = np.cross(d, a); e1 /= np.linalg.norm(e1)
        e2 = np.cross(d, e1)
        uu, vv, dd = P @ e1, P @ e2, P @ d
        u0, v0 = uu.min(), vv.min()
        iu = ((uu - u0) / cell).astype(int); iv = ((vv - v0) / cell).astype(int)
        W, H = iu.max() + 2, iv.max() + 2
        qu, qv, qd = Q @ e1, Q @ e2, Q @ d
        ju = np.clip(((qu - u0) / cell).astype(int), 0, W - 1); jv = np.clip(((qv - v0) / cell).astype(int), 0, H - 1)
        c = Nm @ d
        # 斜めから見るほど、同じ面の隣の点が手前に来る（1 マスの中の深さの差 ≈ マス × tan）。その分を許す
        b = bias + 2.0 * cell * np.sqrt(np.clip(1 - c * c, 0, 1)) / np.maximum(c, 0.2)
        ok = np.zeros(len(P), bool)
        ok2 = np.zeros(len(P), bool)
        q2u, q2v, q2d = Q2 @ e1, Q2 @ e2, Q2 @ d
        k2u = np.clip(((q2u - u0) / cell).astype(int), 0, W - 1); k2v = np.clip(((q2v - v0) / cell).astype(int), 0, H - 1)
        for g in groups:
            src = np.ones(len(P), bool) if g == 0 else (group == g)
            dm = np.full((H, W), -np.inf)
            np.maximum.at(dm, (iv[src], iu[src]), dd[src])
            dm2 = dm.copy()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):      # 点の抜け（斜めに見た面）を埋める
                dm2 = np.maximum(dm2, np.roll(np.roll(dm, dy, 0), dx, 1))
            sel = group == g
            ok[sel] = qd[sel] >= dm2[jv[sel], ju[sel]] - b[sel]
            ok2[sel] = q2d[sel] >= dm[k2v[sel], k2u[sel]] - bias
        v = (ok & (c > 0.05)).astype(np.float32)      # 面の裏側の方向は自分の面で遮られる
        vis += v
        vis2 += ok2
        if d[1] > 0:
            sky += v * d[1]; wsky += d[1]
    return vis / n_dirs, sky / max(wsky, 1e-9), vis2 / n_dirs


def _smooth(vals, pos, nrm, mask, region, cell, iters=2):
    """同じ区画・近い位置・近い向きのテクセルだけで平均する（深さの地図の格子のむらを消す。角や隙間はぼかさない）。"""
    vals = [v.copy() for v in vals]
    for _ in range(iters):
        acc = [v * mask for v in vals]
        cnt = mask.astype(np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                sp = np.roll(np.roll(pos, dy, 0), dx, 1)
                sn = np.roll(np.roll(nrm, dy, 0), dx, 1)
                ok = (np.roll(np.roll(mask, dy, 0), dx, 1) & mask & (np.roll(np.roll(region, dy, 0), dx, 1) == region)
                      & (np.linalg.norm(sp - pos, axis=2) < cell * 2.5) & ((sn * nrm).sum(2) > 0.85))
                for a, v in zip(acc, vals):
                    a += np.roll(np.roll(v, dy, 0), dx, 1) * ok
                cnt += ok
        vals = [np.where(mask, a / np.maximum(cnt, 1), v) for a, v in zip(acc, vals)]
    return vals


# ---------------------------------------------------------------- 3D のノイズ
def noise3(P, scale, seed):
    """3D の値ノイズ（格子の乱数を三線形補間。-1〜1）。scale [px] が模様の大きさ。区画をまたいでつながる。"""
    q = P / scale
    i0 = np.floor(q).astype(np.int64)
    f = q - i0
    f = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        v = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
        v = (v ^ (v >> 13)) * 1274126177
        return ((v ^ (v >> 16)) & 0xFFFF) / 32767.5 - 1.0

    out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2]))
                out += w * h(i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz)
    return out


# ---------------------------------------------------------------- 仕上げ
def finish(geo_bones, tex, mat_map, mats, seed=1, debug=None):
    """core.bake が塗った下地（色・細かいゆらぎ・傷・縞・点）に、遮蔽・角・空の明るさと、3D の汚れ・擦れ・埃を重ねる。"""
    from PIL import Image
    a = np.asarray(tex.convert("RGBA")).astype(np.float32)
    size = a.shape[0]
    pos, nrm, bone, used = texel_points(geo_bones, size)
    (pos, nrm, bone), filled = _fill([pos, nrm, bone], used, mat_map * 0 + _regions(mat_map, a))
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-12
    texel = 1.0 / _density(geo_bones, size)
    cell = texel

    # 動かす部品は自分の形だけで遮る
    names = [jb["name"] for jb in geo_bones]
    gid = np.zeros(len(names), np.int32)
    for i, n in enumerate(names):
        if n.startswith(MOVING):
            gid[i] = i + 1
    m = filled & (bone >= 0)
    P, Nm = pos[m].astype(np.float64), nrm[m].astype(np.float64)
    op_, sk_, cv_ = openness(P, Nm, gid[bone[m]], cell)
    op = np.full((size, size), FLAT_OPEN, np.float32); op[m] = op_
    sk = np.full((size, size), 0.5, np.float32); sk[m] = sk_
    flat2 = float(np.median(cv_[op_ > FLAT_OPEN * 0.95])) if (op_ > FLAT_OPEN * 0.95).any() else 0.55
    cv = np.full((size, size), flat2, np.float32); cv[m] = cv_
    region = _regions(mat_map, a)
    op, sk, cv = _smooth([op, sk, cv], pos, nrm, m, region, cell)
    if debug is not None:
        debug.update(open=op, sky=sk, convex=cv, flat2=flat2, used=m)

    rgb = a[..., :3].copy()
    out_rgb = rgb.copy()
    Pm = pos[m].astype(np.float64)
    o, s = op[m], sk[m]
    c = rgb[m]
    mid = mat_map[m]
    occ = np.clip(o / FLAT_OPEN, 0, 1) ** AO_GAMMA            # 1 = 開けた面、0 = 奥
    crev = 1.0 - occ
    edge = np.clip((cv[m] - flat2 - 0.05) / 0.10, 0, 1)        # 角（緩く丸い面は入れない）
    n_big = noise3(Pm, 3.0, seed) * 0.75 + noise3(Pm, 1.2, seed + 1) * 0.25    # 汚れのむら（70mm・30mm。緩やかに）
    n_fine = noise3(Pm, 0.22, seed + 2)                                          # 角の擦れの途切れ（5mm）
    for k, mat in enumerate(mats):
        sel = mid == k
        if not sel.any() or mat.name.startswith("px_") or mat.name == "bore" or mat.name.startswith("mark_"):
            continue
        cc = c[sel]
        if "wood" in mat.name or mat.name in WOODS:
            # 木目: 銃の前後（Z）に長く伸びた縞。太い年輪のむらと、細く暗い筋
            Pw = Pm[sel] * np.array([1.0, 1.0, 0.06])
            g1 = noise3(Pw, 0.22, seed + 7)
            g2 = noise3(Pw, 0.07, seed + 8)
            k = 1.0 - 0.16 * (0.5 + 0.5 * g1) - 0.22 * np.clip(g2 * 2.5 - 1.1, 0, 1)
            cc = cc * k[:, None]
        g = mat.grime
        if g:
            # 隙間に溜まる汚れ＋ごく緩やかなむら（しきい値で切り替える斑はまだらに見えたのでやめた）
            amt = g * (0.25 + 0.2 * n_big[sel] + 1.2 * crev[sel])
            cc = cc * (1 - np.clip(amt, 0, 0.5))[:, None]
        if mat.edge_wear:
            e = edge[sel] ** 1.5 * np.clip(n_fine[sel] * 0.8 + 0.7, 0, 1) * min(1.0, mat.edge_wear * 1.6)
            cc = cc * (1 - e[:, None]) + np.array(mat.wear_color, np.float32) * 1.15 * e[:, None]
        if mat.dust:
            d = mat.dust * (0.3 + 0.2 * n_big[sel] + 1.5 * crev[sel]) * (0.6 + 0.8 * s[sel])     # 隙間と上を向いた面に
            cc = cc * (1 - d[:, None]) + np.array(mat.dust_color, np.float32) * d[:, None]
        # 光: 奥ほど暗く、上を向いた面ほど明るく、角は少し明るく
        light = (AO_FLOOR + (1 - AO_FLOOR) * occ[sel]) * (1 - SKY / 2 + SKY * s[sel]) / (1 - SKY / 2 + SKY * 0.5)
        cc = cc * light[:, None]
        cc = cc + (np.minimum(255, cc * 1.5 + 20) - cc) * (edge[sel] * EDGE_LIGHT)[:, None]
        c[sel] = cc
    out_rgb[m] = c
    out = a.copy()
    out[..., :3] = np.clip(out_rgb, 0, 255)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _regions(mat_map, a):
    """区画の番号の代わり: 材質の番号（同じ材質の隣どうしは同じ扱い。区画をまたいで平均しても同じ材質なら色は合う）。"""
    return np.where(a[..., 3] > 0, mat_map, -1)


def _density(geo_bones, size):
    """テクセル/px（UV の長さ ÷ 位置の長さ の中央値）。"""
    rs = []
    for p, uv, n, bi in _triangles(geo_bones, size, size)[:400]:
        dp = np.linalg.norm(p[1] - p[0]); du = np.linalg.norm(uv[1] - uv[0])
        if dp > 1e-3 and du > 1e-3:
            rs.append(du / dp)
    return float(np.median(rs)) if rs else 8.0
