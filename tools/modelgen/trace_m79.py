"""
M79 グレネードランチャーの側面形を真横写真（右側面・照尺を起こした状態、2541×966px）からトレースし、
m79_outline.py（座標データ）を書き出す。

  python3 trace_m79.py <右側面の写真.jpg>

写真: Wikimedia Commons「M79 Grenade Launcher (7414625716).jpg」（米空軍、パブリックドメイン）。
リポジトリには入れない（トレースした座標だけを入れる）。
縮尺は全長 731mm（公表値）で合わせた 3.30px/mm。この縮尺で銃身の長さ（受け部の前の継ぎ目〜銃口）が 357mm
（公表 14in）、銃身の太さが 45mm（口径 40mm）と合う。
写真の x=1150 がトリガー（Z=0）、y=878 がトリガーガードの底（Y=0）。銃口が右（+x）なので左右反転しない。
"""
import sys
from pathlib import Path

from photo_trace import Silhouette

K, X0, Y0 = 3.30, 1150.0, 878.0
BORE_Y = 80.8           # 銃身の軸（銃口の上下の縁 Y 103.3 / 58.2 の中点）


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # ストック（床尾板・グリップ・受け部を包む木の部分。上の留め金のレバーと下の負い紐の環は除く）
    "stock": ([(360.0, 10.0), (360.0, 160.0), (46.0, 160.0), (46.0, 101.0), (-26.0, 101.0), (-26.0, 39.0),
               (18.0, 39.0), (18.0, 10.0)],
              (rect(225.0, 262.0, 0.0, 22.5), rect(31.0, 46.0, 88.0, 101.0))),
    "safety": (rect(31.0, 46.0, 88.0, 101.0), ()),                     # 床尾の上の安全装置の突起
    "latch": (rect(-26.0, 30.0, 100.5, 118.0), ()),                     # 銃身の留め金のレバー（受け部の上の後ろ）
    "trigger_guard": (rect(-40.0, 18.0, -3.0, 39.5), (rect(-9.0, 4.0, 4.0, 39.5),)),
    "trigger": (rect(-9.0, 4.0, 4.0, 39.5), ()),
    # 受け部（枠）: 後ろの縦の部分と、銃身の下へ伸びる部分（蝶番まで）
    "frame": ([(-24.0, 36.0), (-24.0, 104.0), (-42.0, 104.0), (-42.0, 62.0), (-161.0, 62.0), (-161.0, 36.0)], ()),
    "top_rib": (rect(-42.0, -105.0, 103.0, 118.0), ()),                  # 銃身の後ろの上の台（銃身と一緒に折れる）
    "forend": (rect(-155.0, -300.0, 37.0, 66.0), ()),                # 先台（後ろは枠の板の端に少し差し込む）
    "front_sight": (rect(-358.0, -385.0, 101.0, 126.0), ()),
    "leaf": (rect(-213.0, -258.0, 101.0, 255.0), ()),                    # 照尺（起こした状態）と台・つまみ
}


def main(photo):
    sil = Silhouette(photo, K, X0, Y0, flip=False, thr=200, blur=0.6)
    out = ['"""M79 の側面形（trace_m79.py が写真から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus, min_hole=20.0)!r}")
    out.append(f"BARREL_R = {sil.radius_profile(-110.0, -398.0, BORE_Y, step=8.0, band=30.0)!r}")
    Path(__file__).with_name("m79_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote m79_outline.py")


if __name__ == "__main__":
    main(sys.argv[1])
