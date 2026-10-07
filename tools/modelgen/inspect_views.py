"""
生成モデルの確認用描画（Claude は実機を見られないため、形の確認はこれで行う）。

  python3 inspect_views.py <variant> <ボーン名,…> <出力.png>
      指定ボーンを 6 方向（側面・左前・左後ろ・前・後ろ・左下）から描いた一覧を出す。
      ボーン名に all を渡すと全体。

  python3 inspect_views.py <variant> <ボーン名,…> <出力.png> --photo <写真> --px-per-mm <縮尺>
          --ref <写真上のトリガー x> <写真上のレシーバー下面 y> [--crop x0 y0 x1 y1]
      真横写真（銃口が +x・下が +y に向きを揃えたもの）の上に、モデルの輪郭を赤線で重ねる。
      縮尺は写真に写った寸法の分かる部品（レールの刻み 10mm 間隔など）から求める。

写真は第三者の著作物であることが多いので、重ね合わせ画像はリポジトリに入れない（generated/ にも置かない）。
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from core import render  # noqa: E402

BG = (150, 160, 170, 255)
VIEWS = [("side", 90, 0), ("front-left", 35, 12), ("rear-left", 145, 12),
         ("front", 0, 5), ("rear", 180, 5), ("below-left", 60, -55)]


def load(variant):
    d = Path(__file__).parent / "generated" / variant
    geo = json.loads((d / "m4a1.geo.json").read_text(encoding="utf-8"))
    return geo["minecraft:geometry"][0]["bones"], Image.open(d / "m4a1.png")


def pick(bones, names):
    if names == ["all"]:
        return bones
    return [b for b in bones if b["name"] in names]


def six_views(bones, tex, out, cell=(380, 440)):
    cw, ch = cell
    sheet = Image.new("RGBA", (cw * 3, ch * 2), BG)
    for i, (name, yaw, pitch) in enumerate(VIEWS):
        im = render(bones, tex, yaw, pitch, width=cw - 20, background=BG)
        if im.height > ch - 20:
            im = im.resize((int(im.width * (ch - 20) / im.height), ch - 20), Image.LANCZOS)
        c = Image.new("RGBA", cell, BG)
        c.paste(im, ((cw - im.width) // 2, 20))
        ImageDraw.Draw(c).text((6, 4), name, fill=(0, 0, 0, 255))
        sheet.paste(c, ((i % 3) * cw, (i // 3) * ch))
    sheet.save(out)


def photo_overlay(bones, tex, out, photo_path, px_per_mm, ref_x, ref_y, crop=None):
    import ar15_parts as P
    photo = Image.open(photo_path).convert("RGBA")
    lb_px = (P.L.bore_y + P.L.lower_bottom) / P.MM_PER_PX
    k = px_per_mm * P.MM_PER_PX
    img = render(bones, tex, 90, 0, fixed=(k, ref_x, ref_y + k * lb_px, photo.width, photo.height))
    base = Image.blend(photo, Image.new("RGBA", photo.size, (255, 255, 255, 255)), 0.45)
    edge = img.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    e = ImageChops.difference(edge, edge.filter(ImageFilter.MinFilter(3)))
    line = Image.new("RGBA", img.size, (220, 0, 0, 255))
    line.putalpha(e)
    res = Image.alpha_composite(base, line)
    if crop:
        res = res.crop(tuple(crop))
    res.resize((res.width * 2, res.height * 2), Image.LANCZOS).save(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("variant")
    ap.add_argument("bones")
    ap.add_argument("out")
    ap.add_argument("--photo")
    ap.add_argument("--px-per-mm", type=float)
    ap.add_argument("--ref", type=float, nargs=2)
    ap.add_argument("--crop", type=int, nargs=4)
    a = ap.parse_args()
    bones, tex = load(a.variant)
    sel = pick(bones, a.bones.split(","))
    if a.photo:
        photo_overlay(sel, tex, a.out, a.photo, a.px_per_mm, a.ref[0], a.ref[1], a.crop)
    else:
        six_views(sel, tex, a.out)
