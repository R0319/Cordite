"""
M249 の側面形を作者提供の写真からトレースし、m249_outline.py（座標データ）を書き出す。

  python3 trace_m249.py <写真.jpg>

写真: 上下に 2 丁並んだ真横写真（上: STANAG 弾倉・二脚たたみ、下: ボックス＋ベルト・二脚展開。銃口は左向き）。
写真はリポジトリに入れない（第三者の著作物）。座標データだけを入れる。
縮尺は FN の全長 1035mm で合わせた 0.704px/mm。左右反転後、x=307.5 がトリガー（Z=0）、
上の銃は y=290、下の銃は y=574.5 がグリップ底面（Y=0）。

部品の境目は写真に線として写っていないので、下の REGIONS（mm の多角形）で切り分ける。
"""
import sys
from pathlib import Path

from photo_trace import Silhouette

K, X0 = 0.704, 307.5
Y0_TOP, Y0_BOTTOM = 290.0, 574.5


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


TRIGGER = rect(-11.0, 8.0, 83.0, 107.5)
REGIONS = {
    # 名前: (写真 'top' / 'bottom', 範囲, 除く範囲)
    "stock": ("top", rect(121.4, 352.0, 55.0, 215.0), ()),
    "buttplate": ("top", rect(352.0, 400.0, 55.0, 215.0), ()),
    "receiver": ("top", [(-151.0, 108.0), (121.4, 108.0), (121.4, 184.7), (-131.0, 184.7), (-131.0, 214.0),
                         (-151.0, 214.0)], ()),
    "feed_cover": ("top", rect(-131.0, 121.4, 184.7, 211.0), ()),
    "rear_sight": ("top", rect(56.0, 125.0, 211.0, 242.0), ()),
    "grip": ("top", rect(14.5, 115.0, -10.0, 108.0), ()),
    "trigger_guard": ("top", rect(-42.0, 14.5, 68.0, 108.0), (TRIGGER,)),
    "trigger": ("top", TRIGGER, ()),
    "handguard": ("bottom", rect(-366.0, -151.0, 90.0, 179.0), ()),
    "shield": ("top", rect(-352.0, -177.0, 179.0, 196.5), ()),
    "carry_handle": ("top", [(-262.0, 206.0), (-178.0, 206.0), (-178.0, 178.0), (-160.0, 178.0), (-160.0, 242.0),
                             (-262.0, 242.0)], ()),
    "gas": ("top", rect(-475.0, -362.0, 110.0, 160.0), ()),
    "front_sight": ("top", rect(-447.0, -412.0, 179.0, 242.0), ()),
    "box_body": ("bottom", rect(-142.0, -35.0, -10.0, 92.0), ()),
    "box_lid": ("bottom", rect(-142.0, -35.0, 92.0, 119.5), ()),     # 上はベルトが出るので 119.5 で切る
}


def main(photo):
    sil = {"top": Silhouette(photo, K, X0, Y0_TOP), "bottom": Silhouette(photo, K, X0, Y0_BOTTOM)}
    out = ['"""M249 の側面形（trace_m249.py が写真から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (src, region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil[src].part(region, minus=minus)!r}")
    # 丸い部品は半径の分布（Z, 半径）で持つ
    out.append(f"BARREL_R = {sil['top'].radius_profile(-447.0, -603.0, 169.3, step=4.0, band=14.0)!r}")
    out.append(f"FLASH_HIDER_R = {sil['top'].radius_profile(-603.0, -652.0, 169.3, step=1.5, band=16.0)!r}")
    Path(__file__).with_name("m249_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
