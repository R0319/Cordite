"""
AK-47 の側面形を作者提供の図面（線画）からトレースし、ak47_outline.py（座標データ）を書き出す。

  python3 trace_ak47.py <図面.jpg>

図面: 濃い青の背景に白い線の AK-47 の図（529×378px）。上段の側面図（銃口が右）を使う。
図面はリポジトリに入れない（第三者の著作物）。座標データだけを入れる。

手順（blueprint_trace.py）: 側面図の範囲を 4 倍に拡大 → 白い線を取り出す → 外から塗って背景を決める →
線に囲まれていても抜けている場所（トリガーガードの中）を抜く → 残りが銃の影絵。
縮尺は全長 880mm（Type 3 の公表値）で合わせた 1.784px/mm（拡大後。元の図面で 2.24mm/px）。
拡大後の x=595 がトリガー（Z=0）、y=387 がグリップ底面（Y=0）。

部品の境目は図面の線の位置を mm 目盛りに描き直して読んだ（REGIONS）。
"""
import sys
import tempfile
from pathlib import Path

from blueprint_trace import blueprint_silhouette
from photo_trace import Silhouette

BOX = (18, 18, 437, 141)        # 側面図の範囲（元の図面の座標）
UPSCALE = 4
ERASE = [(26, 96, 34, 141)]     # 床尾の下の縦の寸法線
SEEDS = [(630, 230), (585, 235)]  # トリガーガードの中（トリガーの前と後ろ）
K, X0, Y0 = 1570 / 880.0, 595.0, 387.0


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # 名前: (範囲, 除く範囲)。Z は銃口側が負
    "stock": (rect(80.0, 320.0, 20.0, 160.0), ()),
    "receiver": (rect(-150.0, 80.0, 99.0, 141.0), ()),
    "dust_cover": (rect(-125.0, 80.0, 140.0, 175.0), ()),
    "trigger_guard": (rect(-52.0, 15.0, 60.0, 100.0), ()),
    "grip": ([(17.0, 100.0), (80.0, 100.0), (80.0, -10.0), (10.0, -10.0), (10.0, 60.0), (17.0, 60.0)], ()),
    "magazine": (rect(-195.0, -50.0, -80.0, 100.0), ()),
    "rear_sight": (rect(-208.0, -125.0, 141.0, 195.0), ()),
    "front_trunnion": (rect(-208.0, -150.0, 98.0, 141.0), ()),
    "upper_handguard": (rect(-312.0, -208.0, 145.0, 180.0), ()),
    "lower_handguard": (rect(-320.0, -208.0, 100.0, 145.0), ()),
    "gas": (rect(-412.0, -320.0, 140.0, 175.0), ()),
    "gas_lug": (rect(-412.0, -392.0, 105.0, 141.0), ()),
    "front_sight": (rect(-500.0, -460.0, 141.0, 195.0), ()),
    "front_sight_base": (rect(-512.0, -460.0, 108.0, 141.0), ()),
}
BORE_Y = 133.0


def main(drawing):
    sil_img, _ = blueprint_silhouette(drawing, BOX, UPSCALE, erase=ERASE, seeds=SEEDS)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "sil.png"
        sil_img.save(p)
        sil = Silhouette(str(p), K, X0, Y0, flip=False, thr=128, blur=0.8)
    out = ['"""AK-47 の側面形（trace_ak47.py が図面から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus)!r}")
    # 丸い部品は半径の分布（Z, 半径）で持つ
    out.append(f"BARREL_R = {sil.radius_profile(-412.0, -460.0, BORE_Y, step=4.0, band=11.0)!r}")
    out.append(f"MUZZLE_R = {sil.radius_profile(-512.0, -575.0, BORE_Y, step=2.0, band=15.0)!r}")
    Path(__file__).with_name("ak47_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote ak47_outline.py")


if __name__ == "__main__":
    main(sys.argv[1])
