"""
モデルを前・後ろ・上から同じ縮尺（mm の目盛り付き）で描き、同じ向きの資料（三面図・写真）と並べる。
幅（左右の厚み）は真横の写真からは分からないので、幅を決めた・変えたら必ずこれで確かめる（作者の指摘
「P90 のこの部分の太さってどうなった？」。別の型の三面図の細り方を当てはめ、後ろから見ると全幅の箱のままだった）。

  python3 end_views.py <方式> <出力.png> [--ref <資料の画像> --crop x0 y0 x1 y1 --ref-mm-per-px <mm/px>]

資料の縮尺は、規格で寸法の決まった部品（ピカティニーレールの幅 21.2mm 等）や公表の全幅で求め、2 つ以上で一致を
確かめる。資料は同じ型のものを使う（別の型の資料しか無ければ作者に頼む）。資料の画像はリポジトリに入れない。
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from core import render  # noqa: E402
from ar15_parts import MM_PER_PX  # noqa: E402

S = 3.0                                  # 画面 px / mm
BG = (20, 40, 90, 255)


def load(variant):
    d = Path(__file__).parent / "generated" / variant
    f = next(d.glob("*.geo.json"))
    return json.loads(f.read_text(encoding="utf-8"))["minecraft:geometry"][0]["bones"], \
        Image.open(f.with_name(f.name.replace(".geo.json", ".png")))


def extents(bones):
    xs, ys, zs = [], [], []
    for b in bones:
        pm = b.get("poly_mesh")
        if pm and b["name"] not in ("right_hand", "left_hand"):
            for x, y, z in pm["positions"]:
                xs.append(x * MM_PER_PX); ys.append(y * MM_PER_PX); zs.append(z * MM_PER_PX)
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def ticks(img, x0, y0, xs, ys):
    d = ImageDraw.Draw(img)
    for x in xs:
        d.line([(x0 + x * S, img.height - 14), (x0 + x * S, img.height - 4)], fill=(255, 255, 0))
    for y in ys:
        yy = y0 - y * S
        d.line([(0, yy), (8, yy)], fill=(255, 255, 0)); d.text((10, yy - 6), str(int(y)), fill=(255, 255, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant"); ap.add_argument("out")
    ap.add_argument("--ref"); ap.add_argument("--crop", nargs=4, type=int)
    ap.add_argument("--ref-mm-per-px", type=float)
    a = ap.parse_args()
    bones, tex = load(a.variant)
    (xa, xb), (ya, yb), (za, zb) = extents(bones)
    half = max(abs(xa), abs(xb)) + 10
    w, h = int(2 * half * S), int((yb - ya + 20) * S)
    y0 = (yb + 10) * S
    fs = 24.0 * S
    views = []
    for yaw in (180, 0):                 # 前・後ろ
        im = render(bones, tex, yaw, 0, fixed=(fs, w / 2, y0, w, h), background=BG)
        ticks(im, w / 2, y0, [x for x in range(-30, 31, 5)], range(int(ya // 10 * 10), int(yb) + 1, 10))
        views.append(im)
    tw, th = int((zb - za + 20) * S), w
    top = render(bones, tex, -90, 89.9, fixed=(fs, (-za + 10) * S, th / 2, tw, th), background=BG)
    W = max(2 * w + 10, tw)
    out = Image.new("RGB", (W, h + th + 10), (255, 255, 255))
    out.paste(views[0].convert("RGB"), (0, 0)); out.paste(views[1].convert("RGB"), (w + 10, 0))
    out.paste(top.convert("RGB"), (0, h + 10))
    if a.ref:
        ref = Image.open(a.ref).convert("RGB")
        if a.crop:
            ref = ref.crop(tuple(a.crop))
        if a.ref_mm_per_px:
            k = a.ref_mm_per_px * S
            ref = ref.resize((int(ref.width * k), int(ref.height * k)), Image.LANCZOS)
        both = Image.new("RGB", (out.width + ref.width + 10, max(out.height, ref.height)), (255, 255, 255))
        both.paste(out, (0, 0)); both.paste(ref, (out.width + 10, 0))
        out = both
    out.save(a.out)
    print(a.out, out.size)


if __name__ == "__main__":
    main()
