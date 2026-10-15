"""生成したモデルの自動採点（作成後の確認作業の機械でできる部分）。

  python3 score.py <方式> [--photo 写真] [--pose bone:rx:ry:rz;...] [--img-dir 出力先] [--json 結果.json]
  python3 score.py --all                     # generated/ の全メッシュ版（写真なし）

見るもの（作者のこれまでの指摘を機械で拾える形にしたもの。.claude/skills/model-gen/SKILL.md のチェックリスト）:
- 写真との輪郭のずれ（--photo を渡したとき。trace_<銃>.py と同じ縮尺・原点で写真の影絵とモデルの真横の影絵を重ね、
  一致率（IoU）と、上端・下端が 2mm 以上ずれている Z の区間を出す）… #1
- 背景が細く抜けている所（6 方向の影絵を閉じて埋まる、幅 3mm 以下の細長い所。部品を離して浮かせると線に見える）
  … #2・#15。照尺など可動部は --pose で動かした姿勢でも見る（倒した状態では下の部品に隠れて抜けない）
- 開いた辺（どの面ともつながっていない辺。埋め込む前提の端もあるので参考値）… #2
- 長い浅い折れ目（平らな面を細長い三角形の扇で張った所。放射状の筋に見える）… #3
- 面の数（目安 7000 以下）… #14
- ボーン（コードが参照する名前・アニメーションで動かす部品が揃っているか）

数値は「要確認の候補」を出すもので、合否ではない。写真の付属品（スコープ・手・スリング）や、わざと空けた隙間
（ボルトとレシーバーの間など）も拾うので、最後は描画を見て判断する。写真はリポジトリに入れない。
"""
import argparse
import importlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ar15_parts import MM_PER_PX  # noqa: E402

FACE_LIMIT = 7000
SLIT_MAX = 3.0                      # 背景が抜けて線に見える隙間の幅の上限 [mm]（これより広いのは窓・穴として扱う）
SLIT_LEN = 4.0                      # これより短いもの（角の小さな切れ込み）は出さない [mm]
FOLD_LEN, FOLD_DEG, FOLD_REPORT = 25.0, (1.0, 15.0), 1000.0  # 長い浅い折れ目（筋）: 辺の長さ・折れ角・報告する合計 [mm]
# 報告の下限: 描画で筋が見えた物は 1933〜7557mm、見えなかった物（輪郭の角に縁の帯の辺が集まる所）は 522〜919mm だった
EDGE_TOL = 2.0                      # 輪郭のずれとして出す差 [mm]
PX_PER_MM = 2.0                     # 写真との比較の解像度
SLIT_PX_PER_MM = 4.0                # 隙間を探す影絵の解像度（0.5mm の隙間が 2 画素）
ROI_MM = 25.0                       # 写真の影絵はモデルの外形からこの距離までだけ見る（別の銃・文字・台を拾わない）

# 写真のトレースの設定（trace_<銃>.py の Silhouette の引数と同じにする）: (モジュール, 左右反転, 閾値, ぼかし)
PHOTO = {
    "mp5_mesh": ("trace_mp5", False, 200, 0.6),
    "m24_mesh": ("trace_m24", False, 200, 0.6),
    "p90_mesh": ("trace_p90", False, 200, 0.6),
    "m1912_mesh": ("trace_m1912", False, 165, 1.0),
    "awm_mesh": ("trace_awm", True, 205, 0.8),        # 左側面の写真（a4）
    "m79_mesh": ("trace_m79", False, 200, 0.6),
    "m2_mesh": ("trace_m2", False, 128, 0.8),         # trace_m2.py の第 2 引数で書き出した前処理済みの写真
}
CODE_BONES = ("muzzle_flash", "idle_view", "iron_view", "ammo", "right_hand", "left_hand")
PART_BONES = ("receiver", "trigger", "magazin", "mag_ammo", "bolt", "charging_handle", "selector", "mag_release")
SKIP = ("right_hand", "left_hand", "rightItem", "leftItem")


def load(variant):
    geo = next((HERE / "generated" / variant).glob("*.geo.json"))
    return json.load(open(geo))["minecraft:geometry"][0]["bones"]


# ---------------------------------------------------------------- メッシュ
def triangles(bones):
    """全ボーンの poly_mesh を三角形にする（既定の姿勢の回転は当てない）。戻り値: 頂点 (N,3,3)[mm]、
    滑らかな陰影の面か（3 頂点の法線が揃っていない＝面の中で陰影が変わる）、ボーン名。"""
    tris, smooth, bone_of = [], [], []
    for b in bones:
        pm = b.get("poly_mesh")
        if not pm or b["name"] in SKIP:
            continue
        P = np.asarray(pm["positions"], float) * MM_PER_PX
        N = np.asarray(pm["normals"], float)
        for poly in pm["polys"]:
            vs = []
            for v in poly:                      # 重なった頂点（三角形を四角形で書いたもの）を除く
                if not vs or v[0] != vs[-1][0]:
                    vs.append(v)
            if len(vs) > 2 and vs[0][0] == vs[-1][0]:
                vs.pop()
            for i in range(1, len(vs) - 1):
                tri = (vs[0], vs[i], vs[i + 1])
                n = N[[v[1] for v in tri]]
                tris.append(P[[v[0] for v in tri]])
                smooth.append(min(n[0] @ n[1], n[1] @ n[2], n[0] @ n[2]) < 0.995)
                bone_of.append(b["name"])
    return np.array(tris), np.array(smooth), np.array(bone_of)


def open_edges(bones):
    """ボーンごとの開いた辺（1 つの面にしか使われていない辺）の数と長さ [mm]。"""
    out = {}
    for b in bones:
        pm = b.get("poly_mesh")
        if not pm or b["name"] in SKIP:
            continue
        P = np.asarray(pm["positions"], float) * MM_PER_PX
        key = {}
        weld = [key.setdefault(tuple(np.round(p, 2)), len(key)) for p in P]
        rep = {}
        for i, w in enumerate(weld):
            rep.setdefault(w, i)
        cnt = defaultdict(int)
        for poly in pm["polys"]:
            f = [weld[v[0]] for v in poly]
            f = [x for i, x in enumerate(f) if x != f[i - 1]]
            for a, c in zip(f, f[1:] + f[:1]):
                cnt[(min(a, c), max(a, c))] += 1
        bad = [e for e, c in cnt.items() if c == 1]
        if bad:
            ln = sum(np.linalg.norm(P[rep[a]] - P[rep[c]]) for a, c in bad)
            out[b["name"]] = (len(bad), round(float(ln), 1))
    return out


def folds(T, smooth, bone_of):
    """平らな陰影の面どうしが、長い辺（FOLD_LEN mm 以上）で浅く折れていて（FOLD_DEG の範囲）、それが 1 点から放射状に
    3 本以上出ている所の長さの合計 [mm]。
    丸めた部品の平らな面を細長い三角形の扇で張ると、面がわずかに曲がっている分だけ放射状の筋に見える
    （AWM のストックで格子分割 cap_grid を入れる前: 5368mm、入れた後: 136mm）。"""
    out = {}
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    for bone in np.unique(bone_of):
        idx = np.nonzero(bone_of == bone)[0]
        key, edges = {}, defaultdict(list)
        for i in idx:
            f = [key.setdefault(tuple(np.round(p, 2)), len(key)) for p in T[i]]
            for k in range(3):
                a_, c_ = f[k], f[(k + 1) % 3]
                edges[(min(a_, c_), max(a_, c_))].append((i, k))
        fold = []
        for e, fs in edges.items():
            if len(fs) != 2 or smooth[fs[0][0]] or smooth[fs[1][0]]:
                continue
            i, k = fs[0]
            if min(abs(nrm[i][0]), abs(nrm[fs[1][0]][0])) < 0.7:     # 横を向いた側面だけ（丸めた縁の帯の段は形どおり）
                continue
            ln = np.linalg.norm(T[i][k] - T[i][(k + 1) % 3])
            if ln < FOLD_LEN:
                continue
            ang = np.degrees(np.arccos(np.clip(abs(nrm[i] @ nrm[fs[1][0]]), 0, 1)))
            if FOLD_DEG[0] < ang < FOLD_DEG[1]:
                fold.append((e, ln))
        deg = defaultdict(int)
        for (a_, c_), _ in fold:
            deg[a_] += 1; deg[c_] += 1
        # 放射状（1 点から 3 本以上）の折れ目だけ数える。丸めた角の帯（平行な長い折れ目）は形どおりなので数えない
        tot = sum(ln for (a_, c_), ln in fold if deg[a_] >= 3 or deg[c_] >= 3)
        if tot >= FOLD_REPORT:
            out[str(bone)] = round(float(tot))
    return out


def world_tris(bones, pose=None):
    """全ボーンの面（poly_mesh・キューブ）を、ボーンの回転（既定の姿勢＋pose）を当てて三角形にする [mm]。
    pose = {ボーン名: (rx, ry, rz)}。回転の規則は core.render と同じ。"""
    from core import _FACE_CORNERS, _rot_raw
    by = {b["name"]: b for b in bones}
    world = {}

    def bw(n):
        if n in world:
            return world[n]
        b = by[n]
        rot = (pose or {}).get(n, b.get("rotation"))
        m = np.eye(4)
        if rot and any(abs(x) > 1e-9 for x in rot):
            pv = np.array(b.get("pivot", [0, 0, 0]), float)
            m[:3, :3] = _rot_raw(rot)
            m[:3, 3] = pv - m[:3, :3] @ pv
        par = b.get("parent")
        world[n] = (bw(par) @ m) if par in by else m
        return world[n]
    out = []
    for b in bones:
        if b["name"] in SKIP:
            continue
        mine = []
        pm = b.get("poly_mesh")
        if pm:
            P = np.asarray(pm["positions"], float)
            for poly in pm["polys"]:
                f = [v[0] for v in poly]
                mine += [P[[f[0], f[i], f[i + 1]]] for i in range(1, len(f) - 1)]
        for c in b.get("cubes", []):
            o, sz = np.array(c["origin"], float), np.array(c["size"], float)
            R = _rot_raw(c["rotation"]) if "rotation" in c else None
            pv = np.array(c.get("pivot", o + sz / 2), float)
            for corners in _FACE_CORNERS.values():
                q = np.array([o + sz * np.array(k) for k in corners])
                if R is not None:
                    q = (q - pv) @ R.T + pv
                mine += [q[[0, 1, 2]], q[[0, 2, 3]]]
        W = bw(b["name"])
        if not np.allclose(W, np.eye(4)):
            mine = [t @ W[:3, :3].T + W[:3, 3] for t in mine]
        out += mine
    return np.array(out) * MM_PER_PX


VIEWS = {"右": (90, 0), "左": (-90, 0), "上": (90, 90), "下": (90, -90), "後ろ": (0, 0), "前": (180, 0)}
AXIS = "XYZ"


def view_matrix(yaw, pitch):
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    v = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    return v * np.array([-1.0, 1.0, 1.0])   # core.render と同じく X を反転してから回す


def mask(T, V, frame=None, P=PX_PER_MM, margin=6.0):
    """三角形を V で投影して塗った影絵（True = モデル）。frame=(x0, y0, W, H) [mm・画素] を渡さなければ外形 + margin。"""
    Q = T @ V.T
    if frame is None:
        lo, hi = Q[:, :, :2].reshape(-1, 2).min(0) - margin, Q[:, :, :2].reshape(-1, 2).max(0) + margin
        frame = (lo[0], hi[1], int((hi[0] - lo[0]) * P) + 1, int((hi[1] - lo[1]) * P) + 1)
    x0, y0, W, H = frame
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for t in Q:
        dr.polygon([((x - x0) * P, (y0 - y) * P) for x, y, _ in t], fill=255)
    return np.asarray(img) > 127, frame


def _shift_max(m, r, axis):
    out = m.copy()
    for d in range(1, r + 1):
        a = np.roll(m, d, axis); b = np.roll(m, -d, axis)
        if axis == 0:
            a[:d] = False; b[-d:] = False
        else:
            a[:, :d] = False; b[:, -d:] = False
        out |= a | b
    return out


def dilate(m, r):
    """正方形（一辺 2r+1 画素）で膨らませる。"""
    return _shift_max(_shift_max(m, r, 0), r, 1)


def erode(m, r):
    return ~dilate(~m, r)


def open2(m):
    """2×2 の正方形で開く（幅 1 画素の線・点を消し、2 画素以上は残す）。"""
    e = m[:-1, :-1] & m[1:, :-1] & m[:-1, 1:] & m[1:, 1:]
    d = np.zeros_like(m)
    d[:-1, :-1] |= e; d[1:, :-1] |= e; d[:-1, 1:] |= e; d[1:, 1:] |= e
    return d


def _label(m):
    """True の画素の 8 近傍のまとまり（scipy が無いので素直に塗りつぶす）。"""
    lab = np.zeros(m.shape, int)
    H, W = m.shape
    n = 0
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]:
            continue
        n += 1
        st = [(y0, x0)]
        lab[y0, x0] = n
        while st:
            y, x = st.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        st.append((yy, xx))
    return lab, n


def slits(bones, pose=None, img_dir=None):
    """6 方向の影絵で、部品の間に背景が細く抜けている所（幅 SLIT_MAX mm 以下の溝・すき間）を探す。
    影絵を SLIT_MAX の大きさで閉じて（膨らませて縮める）埋まった所のうち、細長いものを出す。"""
    T = world_tris(bones, pose)
    P = SLIT_PX_PER_MM
    rad = int(SLIT_MAX * P / 2 + 0.5)
    out = []
    for name, (yaw, pitch) in VIEWS.items():
        V = view_matrix(yaw, pitch)
        m, (x0, y0, W, H) = mask(T, V, P=P, margin=SLIT_MAX * 2)
        sl = erode(dilate(m, rad), rad) & ~m
        sl = open2(sl)              # 幅 1 画素の線（三角形の継ぎ目の塗り残し）を落とす
        lab, n = _label(sl)
        ax = [(int(np.abs(V[i]).argmax()), float(np.sign(V[i][np.abs(V[i]).argmax()]))) for i in (0, 1)]
        hits = []
        for i in range(1, n + 1):
            ys, xs = np.nonzero(lab == i)
            area = len(ys) / P ** 2
            ln = max(np.ptp(xs), np.ptp(ys)) / P
            wd = area / max(ln, 1e-6)
            if ln < SLIT_LEN or ln / wd < 3:
                continue
            sx = x0 + np.array([xs.min(), xs.max()]) / P
            sy = y0 - np.array([ys.max(), ys.min()]) / P
            rng = {}
            for (a, sg), r in zip(ax, (sx, sy)):
                v = sorted(sg * r)
                rng[AXIS[a]] = [round(v[0], 1), round(v[1], 1)]
            hits.append({"view": name, "length_mm": round(ln, 1), "width_mm": round(wd, 2), "range_mm": rng})
            out.append(hits[-1])
        if img_dir and hits:
            rgb = np.full(m.shape + (3,), 255, np.uint8)
            rgb[m] = (120, 120, 120)
            rgb[sl] = (255, 0, 255)
            Image.fromarray(rgb).save(Path(img_dir) / f"slit_{name}.png")
    return sorted(out, key=lambda r: -r["length_mm"])


# ---------------------------------------------------------------- 写真
def silhouettes(variant, bones, photo, pose=None):
    """写真の影絵とモデルの真横の影絵を同じ mm の枠（モデルの外形 + 20mm）に描く。戻り値: (写真, モデル, (Z の最大, Y の最大))
    影絵は左右どちらから見ても鏡像で同じなので、左側面の写真（反転してトレースしたもの）も右側面の投影と比べる。"""
    from photo_trace import Silhouette
    mod, flip, thr, blur = PHOTO[variant]
    m = importlib.import_module(mod)
    sil = Silhouette(photo, m.K, m.X0, m.Y0, flip=flip, thr=thr, blur=blur)
    model_m, (x0, y0, W, H) = mask(world_tris(bones, pose), view_matrix(90, 0), margin=20.0)
    P = PX_PER_MM
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    tf = lambda ring: [((-z - x0) * P, (y0 - y) * P) for z, y in ring.coords]   # 右側面: 画面の x = -Z
    for g in getattr(sil.geom, "geoms", [sil.geom]):
        if g.geom_type != "Polygon":
            continue
        dr.polygon(tf(g.exterior), fill=255)
        for h in g.interiors:
            dr.polygon(tf(h), fill=0)
    roi = dilate(model_m, int(ROI_MM * P))
    return (np.asarray(img) > 127) & roi, model_m, (-x0, y0)


def outline_diff(photo_m, model_m, origin):
    z0, y0 = origin
    P = PX_PER_MM
    inter, union = (photo_m & model_m).sum(), (photo_m | model_m).sum()
    rows = np.arange(photo_m.shape[0])[:, None]
    big = photo_m.shape[0]

    def edges(m):
        has = m.any(0)
        top = np.where(has, np.where(m, rows, big).min(0), -1)
        bot = np.where(has, np.where(m, rows, -1).max(0), -1)
        return has, top, bot
    hp, tp, bp = edges(photo_m)
    hm, tm, bm = edges(model_m)
    runs = []
    for name, dp, dm, sign in (("上端", tp, tm, -1), ("下端", bp, bm, -1)):
        d = np.where(hp & hm, (dm - dp) * sign / P, 0.0)   # 正 = モデルの方が上
        bad = np.abs(d) >= EDGE_TOL
        i = 0
        while i < len(bad):
            if not bad[i]:
                i += 1; continue
            j = i
            while j + 1 < len(bad) and (bad[j + 1] or (j + 2 < len(bad) and bad[j + 2])):
                j += 1
            if (j - i + 1) / P >= 3.0:
                seg = d[i:j + 1]
                k = np.abs(seg).argmax()
                runs.append({"edge": name, "z_mm": [round(z0 - j / P, 1), round(z0 - i / P, 1)],
                             "max_mm": round(float(seg[k]), 1)})
            i = j + 1
    only = []
    for name, a, b in (("写真だけにある", hp & ~hm, None), ("モデルだけにある", hm & ~hp, None)):
        idx = np.nonzero(a)[0]
        if len(idx):
            cuts = np.split(idx, np.nonzero(np.diff(idx) > 2)[0] + 1)
            for c in cuts:
                if len(c) / P >= 3.0:
                    only.append({"what": name, "z_mm": [round(z0 - c[-1] / P, 1), round(z0 - c[0] / P, 1)]})
    return {"iou": round(float(inter / max(union, 1)), 3), "edge_runs": runs, "columns": only}


def diff_image(photo_m, model_m, path):
    """灰 = 両方、緑 = 写真だけ、赤 = モデルだけ。"""
    img = np.full(photo_m.shape + (3,), 255, np.uint8)
    img[photo_m & model_m] = (150, 150, 150)
    img[photo_m & ~model_m] = (40, 170, 60)
    img[model_m & ~photo_m] = (220, 50, 50)
    Image.fromarray(img).save(path)


# ---------------------------------------------------------------- まとめ
def score(variant, photo=None, img_dir=None, pose=None):
    bones = load(variant)
    names = {b["name"] for b in bones}
    has_geo = {b["name"] for b in bones if b.get("poly_mesh") or b.get("cubes")}
    faces = sum(len(b["poly_mesh"]["polys"]) for b in bones if b.get("poly_mesh") and b["name"] not in SKIP)
    cubes = sum(len(b.get("cubes", [])) for b in bones if b["name"] not in SKIP)
    T, smooth, bone_of = triangles(bones)
    res = {
        "variant": variant,
        "faces": faces, "cubes": cubes, "faces_ok": faces <= FACE_LIMIT,
        "bones_missing": [n for n in CODE_BONES + PART_BONES if n not in names],
        "bones_empty": [n for n in PART_BONES if n in names and n not in has_geo],
        "pose": pose or {},
        "slits": slits(bones, pose, img_dir),
        "folds": folds(T, smooth, bone_of),
        "open_edges": open_edges(bones),
    }
    if photo:
        pm, mm, org = silhouettes(variant, bones, photo, pose)
        res["photo"] = outline_diff(pm, mm, org)
        if img_dir:
            diff_image(pm, mm, Path(img_dir) / f"photo_{variant}.png")
    return res


def report(r):
    L = [f"== {r['variant']}",
         f"面: {r['faces']}（キューブ {r['cubes']}）{'' if r['faces_ok'] else f'  ⚠ 目安 {FACE_LIMIT} を超えている'}"]
    if r["bones_missing"]:
        L.append(f"ボーンが無い: {', '.join(r['bones_missing'])}")
    if r["bones_empty"]:
        L.append(f"中身の無いボーン: {', '.join(r['bones_empty'])}")
    if r["pose"]:
        L.append("姿勢: " + ", ".join(f"{b} {v}" for b, v in r["pose"].items()))
    if "photo" in r:
        p = r["photo"]
        L.append(f"写真との一致率（IoU）: {p['iou']}")
        for e in p["edge_runs"]:
            L.append(f"  {e['edge']} Z {e['z_mm'][0]}〜{e['z_mm'][1]}: モデルが最大 {e['max_mm']:+}mm"
                     f"（{'上' if e['max_mm'] > 0 else '下'}にずれ）")
        for c in p["columns"]:
            L.append(f"  {c['what']}: Z {c['z_mm'][0]}〜{c['z_mm'][1]}")
    L.append(f"背景が細く抜けている所（幅 {SLIT_MAX}mm 以下・長さ {SLIT_LEN}mm 以上、6 方向の影絵）: {len(r['slits'])} か所")
    for g in r["slits"][:15]:
        rg = "、".join(f"{k} {v[0]}〜{v[1]}" for k, v in g["range_mm"].items())
        L.append(f"  {g['view']}から: 長さ {g['length_mm']}mm・幅 {g['width_mm']}mm（{rg}）")
    if r["folds"]:
        L.append(f"長い浅い折れ目（筋に見える。{FOLD_REPORT:.0f}mm 以上のボーン）: "
                 + ", ".join(f"{b} {n}mm" for b, n in sorted(r["folds"].items(), key=lambda x: -x[1])))
    if r["open_edges"]:
        oe = sorted(r["open_edges"].items(), key=lambda x: -x[1][1])
        L.append("開いた辺（参考）: " + ", ".join(f"{b} {n}本/{ln}mm" for b, (n, ln) in oe[:8]))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", nargs="?")
    ap.add_argument("--all", action="store_true", help="generated/ の全メッシュ版（写真なし）")
    ap.add_argument("--photo", help="trace_<銃>.py でトレースに使った写真")
    ap.add_argument("--pose", default="", help="ボーンの回転 'bone:rx:ry:rz;...'（例: 照尺を起こす rear_sight:-90:0:0）")
    ap.add_argument("--img-dir", help="差分画像（写真との重ね・隙間の位置）を書き出すフォルダ")
    ap.add_argument("--json")
    a = ap.parse_args()
    pose = {}
    for item in filter(None, a.pose.split(";")):
        n, *r = item.split(":")
        pose[n] = [float(x) for x in r]
    if a.img_dir:
        Path(a.img_dir).mkdir(parents=True, exist_ok=True)
    vs = sorted(p.name for p in (HERE / "generated").iterdir() if p.name.endswith("_mesh")) if a.all else [a.variant]
    out = []
    for v in vs:
        r = score(v, None if a.all else a.photo, a.img_dir, pose or None)
        out.append(r)
        print(report(r))
    if a.json:
        json.dump(out if a.all else out[0], open(a.json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
