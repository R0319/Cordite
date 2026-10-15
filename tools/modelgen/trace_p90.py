"""
FN P90 の側面形を真横写真（右側面・弾倉を付けた状態、2127×1160px）からトレースし、
p90_outline.py（座標データ）を書き出す。

  python3 trace_p90.py <右側面の写真.jpg>

写真: Wikimedia Commons「FN P90 Standard Submachine Gun Right Side.jpg」（FN Herstal、CC BY-SA 2.0。
https://www.flickr.com/photos/15725582@N08/2768333091/ ）。リポジトリには入れない（トレースした座標だけを入れる）。
この写真は照準器（リングサイト）付きの標準型なので、上面は TR 型（上面レール）の写真から読んだ形に p90.py で差し替える。
縮尺は照準器の横のレールの溝の間隔（ピカティニー規格 10.0mm）で合わせた 3.675px/mm。この縮尺で全長 503mm（FN 公表 505mm）。
写真の x=1395 がトリガー（Z=0）、y=970 がグリップの底（Y=0）。銃口が右（+x）なので左右反転しない。
"""
import sys
from pathlib import Path

from photo_trace import Silhouette

K, X0, Y0 = 3.675, 1395.0, 970.0
BORE_Y = 102.3          # 銃身の軸（写真の消炎器の上下の中点）


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # 名前: (範囲, 除く範囲)。Z は銃口側が負
    "butt_pad": (rect(326.0, 350.0, 0.0, 150.0), ()),                 # 床尾板（ゴム）
    # 樹脂の本体（ストック・グリップ・弾倉の受け）。受け部（黒い枠）の下に隠れる所は Y 100 まで取る（穴の上の壁の厚さ）
    "body": ([(326.0, -5.0), (326.0, 150.0), (181.0, 150.0), (181.0, 117.5), (52.0, 117.5), (52.0, 100.0),
              (-100.0, 100.0), (-100.0, 90.0), (-135.0, 90.0), (-135.0, -5.0)], ()),
    # 受け部（照準器の枠・銃身の覆い）。弾倉の見える所も含む（p90.py で弾倉の溝を切る）
    "housing": (rect(-130.0, 58.0, 88.0, 205.0), ()),
}


def main(photo):
    sil = Silhouette(photo, K, X0, Y0, flip=False, thr=200, blur=0.6)
    out = ['"""FN P90 の側面形（trace_p90.py が写真から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus, min_hole=50.0)!r}")
    out.append(f"MUZZLE_R = {sil.radius_profile(-121.0, -167.0, BORE_Y, step=1.0, band=16.0)!r}")
    Path(__file__).with_name("p90_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote p90_outline.py")


if __name__ == "__main__":
    main(sys.argv[1])
