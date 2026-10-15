"""
MP5A3 の側面形を作者提供の真横写真（右側面・ストックを伸ばした状態、1208×906px）からトレースし、
mp5_outline.py（座標データ）を書き出す。

  python3 trace_mp5.py <右側面の写真.jpg>

縮尺は照準半径（照門ドラムの中心〜照星リングの中心 603px）を HK 公表の 340mm（13.39in）に合わせた 1.774px/mm。
この縮尺で全長 671mm（作者提供の図面のトレースでは 662mm、照準半径と高さ 230mm の 2 つで合わせた縮尺）。
写真の x=612 がトリガー（Z=0）、y=606 がグリップ底面（Y=0）。銃口が右（+x）なので左右反転しない。

部品の境目は写真に mm 目盛りを重ねて読んだ（REGIONS）。写真・図面はリポジトリに入れない（第三者の著作物）。
"""
import sys
from pathlib import Path

from photo_trace import Silhouette

K, X0, Y0 = 603 / 340.0, 612.0, 606.0
BORE_Y = 153.5          # 銃身の軸（写真の銃口の上下の中点）


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # 名前: (範囲, 除く範囲)。Z は銃口側が負
    "stock_butt": (rect(296.0, 350.0, 40.0, 185.0), ()),          # 床尾板（後ろの面にすべり止めの刻み）
    "stock_rods": (rect(158.0, 297.0, 134.0, 162.0), ()),         # 左右 2 本の棒（側面では 1 本に重なる）
    "stock_latch": (rect(106.0, 158.0, 105.0, 175.0), ()),        # 受け部の後端キャップ＋ストックの受け・止め金
    "receiver": (rect(-110.0, 106.0, 137.0, 191.5), ()),          # 受け部（板金の筒）
    "rear_sight": (rect(28.0, 82.0, 191.0, 225.0), ()),           # 照門（回転ドラム）
    "cocking_tube": (rect(-262.0, -108.0, 176.0, 191.5), ()),     # コッキングチューブ（ハンドガードの上）
    "cocking_handle": (rect(-206.0, -176.0, 191.0, 202.0), ()),   # コッキングハンドルの頭（チューブの上に出る）
    "handguard": (rect(-262.0, -108.0, 110.0, 177.0), ()),        # ハンドガード（後ろが太く前が細い）
    "front_sight": (rect(-300.0, -258.0, 136.0, 230.0), ()),      # 照星（台・塔・リングのフード）
    "lower_housing": (rect(-106.0, 125.0, 86.0, 138.0), ()),      # トリガーハウジング（弾倉口まで）
    "grip": (rect(26.0, 125.0, -8.0, 87.0), ()),                  # グリップ
    "trigger_guard": (rect(-42.0, 26.0, 48.0, 87.0), (rect(-9.0, 9.0, 60.0, 88.0),)),
    "trigger": (rect(-9.0, 9.0, 60.0, 87.0), ()),
    "mag_release": (rect(-60.0, -43.0, 60.0, 87.0), ()),          # 弾倉止めのレバー（トリガーガードの前、弾倉の後ろ）
    "magazine": (rect(-170.0, -62.0, -70.0, 92.0), ()),           # 弾倉（弾倉口の下に見える部分）
}


def main(photo):
    sil = Silhouette(photo, K, X0, Y0, flip=False, thr=200, blur=0.6)
    out = ['"""MP5A3 の側面形（trace_mp5.py が写真から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus)!r}")
    out.append(f"MUZZLE_R = {sil.radius_profile(-297.0, -331.0, BORE_Y, step=1.5, band=14.0)!r}")
    Path(__file__).with_name("mp5_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote mp5_outline.py")


if __name__ == "__main__":
    main(sys.argv[1])
