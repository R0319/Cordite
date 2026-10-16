"""
Winchester Model 1912（Model 12）トレンチガンの側面形を真横写真（右側面・競売カタログの見開き、2376×1836px の上の段）
からトレースし、m1912_outline.py（座標データ）を書き出す。

  python3 trace_m1912.py <カタログの見開きの画像.jpg>

写真: Rock Island Auction Company の競売カタログ（2022 年 Premier Auction 4094、Lot 331。flipbook の拡大画像
files/large/289.jpg）。第三者の著作物なのでリポジトリには入れない（トレースした座標だけを入れる）。
Wikimedia Commons の自由な写真は幅 600px 程度しか無く（1px≒1.7mm）、米軍の整備マニュアル TM 9-285 の M12 の図は
スポーツ型だけだったため、作者の了承のうえでこの写真を使った。
縮尺は全長（床尾板の後ろ〜銃口）を 20in 銃身の Model 12 の公表値 1003mm に合わせた 2.13px/mm。この縮尺で
引き金〜床尾板の長さが 357mm（実物の計測 13 7/8〜14in＝352〜356mm）と合う。写真は傾いていない（銃身の上の縁が水平）。
トリガーガードとトリガーは内側が光って輪郭が途切れるので、トレースせず m1912.py で写真から読んだ中心線で作る。
写真の x=868 がトリガー（Z=0）、y=290 がグリップの底（Y=0）。銃口が右（+x）なので左右反転しない。
"""
import sys
from pathlib import Path

from photo_trace import Silhouette

K, X0, Y0 = 2.13, 868.0, 290.0
BORE_Y = 102.5          # 銃身の軸（銃身の上の縁 Y 113 から半径 10.5mm）


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # 名前: (範囲, 除く範囲)。Z は銃口側が負。下の段の別の銃（Y -64 より下。床尾の下の角は Y -60）と、銃口の下の兵士の写真（Y 48 より下）を避ける
    "stock": ([(370.0, -64.0), (370.0, 140.0), (23.0, 140.0), (23.0, 64.0), (29.0, 58.0), (29.0, -64.0)], ()),
    "receiver": ([(23.5, 59.5), (23.5, 130.0), (-149.5, 130.0), (-149.5, 52.0), (-52.0, 52.0), (-52.0, 59.5)], ()),
    "collar": (rect(-165.0, -149.5, 52.0, 120.0), ()),            # 受け部の前の輪（分解するときの継ぎ目）
    "forend": (rect(-450.0, -266.0, 48.0, 96.0), ()),             # 先台（ポンプ）
    "heat_shield": (rect(-549.0, -270.0, 95.0, 125.0), ()),       # 放熱カバー（上半分）
    "adapter": ([(-545.0, 48.0), (-545.0, 125.0), (-660.0, 125.0), (-660.0, 48.0)], ()),   # 着剣部（銃口の留め具）
}


def main(photo):
    # 閾値 120: 紙に落ちた影（明るさ 150〜215）を拾わない。165 では下の縁が影の分 2〜3mm 下にずれていた
    sil = Silhouette(photo, K, X0, Y0, flip=False, thr=120, blur=1.0)
    out = ['"""Winchester Model 12 トレンチガンの側面形（trace_m1912.py が写真から書き出した座標。手で編集しない）。'
           '単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus)!r}")
    out.append(f"BARREL_TOP = {sil.radius_profile(-170.0, -265.0, BORE_Y, step=5.0, band=14.0)!r}")
    Path(__file__).with_name("m1912_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote m1912_outline.py")


if __name__ == "__main__":
    main(sys.argv[1])
