"""
生成の入口。  python3 build.py
generated/<variant>/ に m4a1.geo.json・m4a1.png・m4a1.animation.json（腕の待機ポーズ）・m4a1_modelshot.png（インベントリ用アイコン）とプレビュー画像を出す。
parts 版は parts/ に部品ごとの .geo.json も出す（Blockbench で単体確認・別銃への流用用）。
"""
import json
import sys
from pathlib import Path

from core import Model, bake, render, write_geo
from rig import hold_animation, place_iron_view
import ar15_mesh
import m4a1_parts
import m4a1_pixel
import m249
import ak47
import mp5
import m24
import p90
import m1912
import awm
import m79

OUT = Path(__file__).parent / "generated"
VARIANTS = {
    # 名前: (組み立て関数, テクスチャ密度[テクセル/px], 出力ファイル名)
    "m4a1_parts": (m4a1_parts.build, 8, "m4a1"),
    "m4a1_pixel": (m4a1_pixel.build, 2, "m4a1"),
    "m4a1_mesh": (lambda: _with_detail("full"), 8, "m4a1"),
    "m4a1_mesh_lite": (lambda: _with_detail("lite"), 6, "m4a1"),   # 敵 NPC 用などの簡略版（面を減らす）
    "m249_mesh": (lambda: m249.build("belt"), 8, "m249"),          # ボックス＋ベルト（標準）
    "m249_stanag_mesh": (lambda: m249.build("stanag"), 8, "m249_stanag"),   # STANAG 弾倉
    "ak_47_mesh": (lambda: ak47.build("wood"), 8, "ak_47"),                 # 木製（標準）
    "ak_47_rail_mesh": (lambda: ak47.build("rail"), 8, "ak_47_rail"),       # レール付き
    "mp5_mesh": (mp5.build, 8, "mp5"),                                        # MP5A3（伸縮ストック）
    "m24_mesh": (m24.build, 8, "m24"),                                        # M24 SWS（M700 系）
    "p90_mesh": (p90.build, 8, "p90"),                                        # FN P90 TR
    "m1912_mesh": (m1912.build, 8, "m1912"),                                  # Winchester M1912 トレンチガン
    "awm_mesh": (awm.build, 8, "awm"),                                        # Accuracy International AWM
    "m79_mesh": (m79.build, 8, "m79"),                                        # M79 グレネードランチャー
}
def _with_detail(level):
    ar15_mesh.set_detail(level)
    try:
        return m4a1_parts.build(ar15_mesh)
    finally:
        ar15_mesh.set_detail("full")


VIEWS = {"side_left": (-90, 0), "side_right": (90, 0), "three_quarter": (-40, 22), "top": (-90, 89.9),
         "front": (0, 8)}


def build_variant(name, fn, density, stem):
    model, parts = fn()
    geo, tex, size = bake(model, density)
    d = OUT / name
    place_iron_view(geo)
    write_geo(d / f"{stem}.geo.json", geo, size)
    tex.save(d / f"{stem}.png")
    # 腕に銃を握らせる待機ポーズ（作者が待機アニメーションを作るまでの仮置き。無いと腕が真上に立ったまま映る）
    (d / f"{stem}.animation.json").write_text(json.dumps(hold_animation(geo, stem, model.support_z), indent=1) + "\n")
    for view, (yaw, pitch) in VIEWS.items():
        render(geo, tex, yaw, pitch, width=300 if view == "front" else 900,
               background=(150, 160, 170, 255)).save(d / f"preview_{view}.png")
    render(geo, tex, 90, 0, width=512).save(d / f"{stem}_modelshot.png")
    for pname, cubes in parts.items():
        pm = Model()
        pm.bone(pname, None, (0, 0, 0), cubes)
        pg, ptex, psize = bake(pm, density)
        write_geo(d / "parts" / f"{pname}.geo.json", pg, psize)
        ptex.save(d / "parts" / f"{pname}.png")
    stats = {"cubes": model.cube_count, "mesh_faces": model.mesh_face_count, "bones": len(model.bones), "texture": size,
             "texels_per_px": density, "parts": len(parts)}
    (d / "stats.json").write_text(json.dumps(stats, indent=1) + "\n")
    print(name, stats)


if __name__ == "__main__":
    only = sys.argv[1:]
    for n, (f, dens, stem) in VARIANTS.items():
        if not only or n in only:
            build_variant(n, f, dens, stem)
