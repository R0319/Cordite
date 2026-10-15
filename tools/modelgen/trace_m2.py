"""
M2 重機関銃（M2HB、重銃身・フレキシブル型）の側面形を写真からトレースし、m2_outline.py（座標データ）を書き出す。

  python3 trace_m2.py <図7の画像（縦向きのまま）> [前処理した写真の書き出し先（score.py の --photo 用）]

写真: 米陸軍 TM 9-1225「Ordnance Maintenance: Browning Machine Gun, Cal. .50, M2, All Types」（1943、パブリックドメイン。
archive.org「1943TM9-1225」）の 12 ページ Figure 7「Heavy Barrel, Flexible」の右側面（RIGHT SIDE VIEW）。
ページの画像は縦向きなので 90°回して使う。リポジトリには入れない（トレースした座標だけを入れる）。
縮尺は全長 65 1/8 in（1654mm、同じ図の SPECIFICATIONS）で合わせた 1.2727px/mm。
回した画像の x=200 が親指で押す引き金（両手グリップの間。Z=0）、y=491 がグリップの下端（Y=0）。銃口が右なので左右反転しない。
"""
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from photo_trace import Silhouette

K, X0, Y0 = 1.2727, 200.0, 491.0
BORE_Y = 61.0           # 銃身の軸（銃口近くの上下の縁の中点）


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # 背板と両手グリップ（グリップ・上下の腕・緩衝筒・背板を 1 つの影絵として取る）
    "backplate": (rect(55.0, -40.0, -12.0, 140.0), ()),
    # 受け部（照尺・照星の出っ張りと下の金具は除く）
    "receiver": (rect(-36.0, -632.0, -15.0, 133.0), (rect(-185.0, -360.0, -45.0, 0.0),)),   # 下の金具の所は除く
    "rear_sight": (rect(-38.0, -220.0, 125.0, 215.0), ()),        # 照尺の台（上蓋の留め金を含む）と起きた照尺
    "front_sight": (rect(-590.0, -635.0, 125.0, 175.0), ()),       # 照星（左右の覆い）
    "bracket": (rect(-185.0, -360.0, -45.0, 8.0), ()),             # 受け部の下の三脚への取付け金具（後ろ）
    "handle": (rect(-770.0, -1000.0, -75.0, 30.0), (rect(-770.0, -1000.0, 30.0, 200.0),)),   # 運搬用の取っ手
}


def upper_radius(sil, z, band=50.0):
    """軸から上の縁までの距離（下に別の部品が付いている所の太さ）。"""
    from shapely.geometry import LineString
    seg = sil.geom.intersection(LineString([(z, BORE_Y), (z, BORE_Y + band)]))
    ys = [y for line in getattr(seg, "geoms", [seg]) for _, y in line.coords] if not seg.is_empty else [BORE_Y]
    return round(max(ys) - BORE_Y, 2)


def despike(prof, tol=3.0):
    """前後の両方と tol 以上違う 1 点だけの値（写真のゴミ）を、前後の平均に置き換える。"""
    out = list(prof)
    for i in range(1, len(out) - 1):
        (_, a), (z, r), (_, c) = out[i - 1], out[i], out[i + 1]
        if abs(r - a) > tol and abs(r - c) > tol:
            out[i] = (z, round((a + c) / 2, 2))
    return out


def clean_image(photo):
    """図 7 のページを時計回りに 90°回し、文字・左側面の図を消し、白以外を銃とした白黒の画像にする。
    網点の印刷で銃の中に白い点・光った帯が多く、そのままだと影絵が細切れになるので、小さな切れ目を閉じて
    中の穴を埋める（背景は真っ白 255、銃の光った所は 216〜250）。"""
    from PIL import ImageFilter
    img = Image.open(photo).convert("L").rotate(-90, expand=True)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 592, img.width, img.height], fill=255)          # 左側面の図・説明文
    d.rectangle([1000, 548, 1250, 592], fill=255)                   # 「RIGHT SIDE VIEW」の文字
    d.rectangle([0, 0, img.width, 200], fill=255)                   # ページの上の見出し
    d.rectangle([2300, 0, img.width, img.height], fill=255)         # 右の欄外の見出し
    clean = img.filter(ImageFilter.GaussianBlur(1.0)).point(lambda v: 0 if v < 246 else 255)
    clean = clean.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))     # 切れ目を閉じる
    ImageDraw.floodfill(clean, (0, 0), 128)                                             # 外から届く白＝背景
    return clean.point(lambda v: 255 if v == 128 else 0)                                # 届かない白（中の穴）は銃


def main(photo, clean_out=None):
    clean = clean_image(photo)
    if clean_out:
        clean.save(clean_out)                     # score.py --photo に渡す写真（PHOTO["m2_mesh"]）
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        clean.save(f.name)
        sil = Silhouette(f.name, K, X0, Y0, flip=False, thr=128, blur=0.8)
    out = ['"""M2 の側面形（trace_m2.py が写真から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        hole = 50.0 if name == "handle" else 1e9      # 取っ手は枠（中が抜けている）。他は光の反射を穴と取らない
        out.append(f"{name.upper()} = {sil.part(region, minus=minus, min_hole=hole)!r}")
    out.append(f"SUPPORT_R = {sil.radius_profile(-632.0, -872.0, BORE_Y, step=6.0, band=55.0)!r}")
    # 留め輪の所は下に取っ手の軸が付いているので、上の縁だけで太さを測る
    prof = despike(sil.radius_profile(-872.0, -1610.0, BORE_Y, step=10.0, band=45.0))
    prof = [(z, upper_radius(sil, z) if z >= -1020.0 else r) for z, r in prof]
    out.append(f"BARREL_R = {prof!r}")
    Path(__file__).with_name("m2_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote m2_outline.py")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
