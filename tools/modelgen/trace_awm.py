"""
Accuracy International AWM の側面形を、英軍 L115A3（AWM .338 の英軍型。折りたたみストック）の真横写真（左側面、
3820×1158px）からトレースし、awm_outline.py（座標データ）を書き出す。

  python3 trace_awm.py <左側面の写真.jpg>

写真: Wikimedia Commons「L115A3 sniper rifle.jpg」（Andrew Linnett／英国防省、Open Government Licence v1.0）。
リポジトリには入れない（トレースした座標だけを入れる）。写真は消音器・二脚・後ろの一脚・スコープ付きなので、それらは
範囲から外す（スコープ・消音器・二脚はアタッチメント扱い）。色はタン色だが、作者の指定でモデルはオリーブ色にする。
縮尺は受け部の上のレールの溝の間隔（ピカティニー規格 10.0mm、26px）で合わせた 2.60px/mm。この縮尺でスコープの長さが
413mm（Schmidt & Bender 5-25×56 PM II の公表 400mm）と合う。
銃口が左（左側面）の写真なので左右反転して読む。反転した写真の x=1024 がトリガー（Z=0）、y=732 がグリップの底（Y=0）。
"""
import sys
from pathlib import Path

from photo_trace import Silhouette

K, X0, Y0 = 2.60, 1024.0, 732.0
BORE_Y = 145.5          # 銃身の軸（銃身の上下の縁の中点）


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


# ストック（シャーシ）の上の縁。これより上は受け部・銃身（黒）とほお当て
STOCK_TOP = [(302.0, 131.0), (112.0, 131.0), (100.0, 141.0), (-232.0, 141.0), (-232.0, 145.5), (-420.0, 145.5)]

REGIONS = {
    "butt_pad": (rect(301.0, 370.0, 5.0, 146.0), ()),               # 床尾板（ゴム）と間座
    "cheek": (rect(165.0, 300.0, 131.0, 155.0), ()),                 # ほお当て（高さ調整式）
    "stock": ([(302.0, -10.0)] + STOCK_TOP + [(-420.0, -10.0)],
              (rect(92.0, 118.0, 97.0, 141.0),                         # 折りたたみの蝶番（黒）
               rect(-145.5, -47.0, -10.0, 79.5),                       # 弾倉
               rect(-47.0, -39.0, 45.0, 72.0),                         # 弾倉止め
               [(-420.0, -10.0), (-420.0, 99.0), (-255.0, 99.0), (-232.0, 95.5), (-232.0, -10.0)],   # 二脚（先台の下の縁に沿う）
               rect(238.0, 292.0, -10.0, 44.5),                        # 後ろの一脚
               rect(-9.0, 9.0, 58.0, 82.5))),                          # トリガー
    "magazine": (rect(-146.0, -46.0, 30.0, 79.6), ()),
    "hinge": (rect(92.0, 118.0, 97.0, 141.0), ()),
    "shroud": (rect(-2.0, 45.0, 131.0, 160.0), ()),                 # ボルトの後ろの覆い（受け部の後ろの黒い箱）
}


def main(photo):
    sil = Silhouette(photo, K, X0, Y0, flip=True, thr=205, blur=0.8)
    out = ['"""AWM（L115A3）の側面形（trace_awm.py が写真から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus, min_hole=80.0)!r}")
    out.append(f"BARREL_R = {sil.radius_profile(-235.0, -800.0, BORE_Y, step=10.0, band=18.0)!r}")
    Path(__file__).with_name("awm_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote awm_outline.py")


if __name__ == "__main__":
    main(sys.argv[1])
