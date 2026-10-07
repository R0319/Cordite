"""
生成の入口。  python3 build.py
generated/<variant>/ に m4a1.geo.json・m4a1.png・m4a1_modelshot.png（インベントリ用アイコン）とプレビュー画像を出す。
parts 版は parts/ に部品ごとの .geo.json も出す（Blockbench で単体確認・別銃への流用用）。
"""
import json
import sys
from pathlib import Path

from core import Model, bake, render, write_geo
import m4a1_parts
import m4a1_pixel

OUT = Path(__file__).parent / "generated"
VARIANTS = {
    # 名前: (組み立て関数, テクスチャ密度[テクセル/px])
    "m4a1_parts": (m4a1_parts.build, 8),
    "m4a1_pixel": (m4a1_pixel.build, 2),
}
VIEWS = {"side_left": (90, 0), "side_right": (-90, 0), "three_quarter": (40, 22), "top": (90, 89.9),
         "front": (0, 8)}


def build_variant(name, fn, density):
    model, parts = fn()
    geo, tex, size = bake(model, density)
    d = OUT / name
    write_geo(d / "m4a1.geo.json", geo, size)
    tex.save(d / "m4a1.png")
    for view, (yaw, pitch) in VIEWS.items():
        render(geo, tex, yaw, pitch, width=300 if view == "front" else 900,
               background=(150, 160, 170, 255)).save(d / f"preview_{view}.png")
    render(geo, tex, 90, 0, width=512).save(d / "m4a1_modelshot.png")
    for pname, cubes in parts.items():
        pm = Model()
        pm.bone(pname, None, (0, 0, 0), cubes)
        pg, ptex, psize = bake(pm, density)
        write_geo(d / "parts" / f"{pname}.geo.json", pg, psize)
        ptex.save(d / "parts" / f"{pname}.png")
    stats = {"cubes": model.cube_count, "bones": len(model.bones), "texture": size,
             "texels_per_px": density, "parts": len(parts)}
    (d / "stats.json").write_text(json.dumps(stats, indent=1) + "\n")
    print(name, stats)


if __name__ == "__main__":
    only = sys.argv[1:]
    for n, (f, dens) in VARIANTS.items():
        if not only or n in only:
            build_variant(n, f, dens)
