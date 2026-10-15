"""
HK416 D14.5RS の側面形を作者提供の三面図（紺地に白い線画、1200×857px。上の右側面図）からトレースし、
hk416_outline.py（座標データ）を書き出す。

  python3 trace_hk416.py <三面図.webp> [前処理した影絵の書き出し先（score.py の --photo 用）]

線画なので、白い線を太らせて外から塗り、届かない所（線で囲まれた中）を銃とした影絵にする。トリガーガードの中は線で
囲まれた背景なので、内側の背景を塗り、その凸包（トリガーの線ごと囲む）を穴として抜く（トリガーは AR-15 の部品を使う）。
右下の説明文は消す。
縮尺は上面のピカティニーレールの刻み（規格 10.0mm）を 27 個数えた 1.046px/mm。この縮尺で全長 817mm（ストックを
途中まで伸ばした位置。公表 787〜886mm の間）、弾倉の受けの前後 72mm（AR-15 の寸法と同じ）で、食い違いは無い。
x=392.8 がトリガー（Z=0。弾倉の受けの前の端を AR-15 部品の -114mm に合わせた）、銃口が右なので左右反転しない。
y=145 が銃身の軸（AR-15 部品の bore_y 155.4mm に合わせ、y=307.55 が Y=0）。
図はリポジトリに入れない（第三者の著作物。トレースした座標だけを入れる）。
"""
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from photo_trace import Silhouette

K, X0, Y0 = 1.046, 392.8, 307.55
BORE_Y = 155.4
GUARD_BOX = (382, 198, 436, 225)   # トリガーガードの内側（画素）。この中の背景をすべて塗り、トリガーの線ごと閉じて穴にする


def rect(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


REGIONS = {
    # 名前: (範囲, 除く範囲)。Z は銃口側が負
    "butt": (rect(282.0, 312.0, 50.0, 185.0), ()),                 # 床尾のゴム（刻み）
    # HK のストック（バッファチューブに沿って動く）。前の下の調整レバーまで含め、チューブは含めない
    "stock": ([(115.0, 50.0), (284.0, 50.0), (284.0, 185.0), (136.0, 185.0), (136.0, 143.0), (115.0, 143.0)], ()),
    "grip": (rect(8.0, 115.0, -5.0, 104.0), ()),                   # HK の人間工学グリップ
    # 下部レシーバー（弾倉の受けの下の端は前ほど高い斜めの切り口。その下の弾倉は含めない）
    "lower": ([(-118.0, 85.5), (-41.0, 72.0), (8.0, 72.0), (8.0, 104.0), (95.0, 104.0), (95.0, 136.0),
               (-118.0, 136.0)], ()),
    "handguard": (rect(-372.0, -117.0, 118.0, 193.0), ()),         # レール付きハンドガード（前の端のガスブロックの覆いまで）
    "front_sight": (rect(-350.0, -312.0, 186.0, 232.0), ()),       # 折りたたみ式の照星（起こした状態）
    "rear_sight": (rect(-2.0, 40.0, 186.0, 232.0), ()),            # 回転ドラム式の照門（起こした状態）
}


def clean_image(drawing):
    """線画 → 白地に黒の影絵（図と同じ大きさ）。"""
    img = Image.open(drawing).convert("L")
    w, h = img.size
    lines = img.point(lambda v: 255 if v > 150 else 0).filter(ImageFilter.MaxFilter(3))
    d = ImageDraw.Draw(lines)
    d.rectangle([590, 190, w, h], fill=0)                # 説明文（右下）
    d.rectangle([0, 345, w, h], fill=0)                  # 下の題字・分解図
    d.rectangle([930, 0, w, 345], fill=0)                # 右の正面図・後面図
    fill = lines.copy()
    ImageDraw.floodfill(fill, (0, 0), 128)
    sil = fill.point(lambda v: 0 if v != 128 else 255)   # 外から届かない所＝銃（黒）
    guard = lines.copy()
    x0, y0, x1, y1 = GUARD_BOX
    for y in range(y0, y1 + 1, 2):
        for x in range(x0, x1 + 1, 2):
            if guard.getpixel((x, y)) == 0:
                ImageDraw.floodfill(guard, (x, y), 77)
    import numpy as np
    from shapely.geometry import MultiPoint
    ys, xs = np.nonzero(np.asarray(guard) == 77)
    hull = MultiPoint(list(zip(xs.tolist(), ys.tolist()))).convex_hull      # 内側はほぼ凸なので凸包でトリガーごと囲む
    hole = Image.new("L", img.size, 0)
    ImageDraw.Draw(hole).polygon(list(hull.exterior.coords), fill=255)
    sil.paste(255, mask=hole)                            # トリガーガードの中を抜く
    return sil


def main(drawing, clean_out=None):
    clean = clean_image(drawing)
    if clean_out:
        clean.save(clean_out)
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        clean.save(f.name)
        sil = Silhouette(f.name, K, X0, Y0, flip=False, thr=128, blur=0.5)
    out = ['"""HK416 D14.5RS の側面形（trace_hk416.py が三面図から書き出した座標。手で編集しない）。単位 mm、(Z, Y)。"""', ""]
    for name, (region, minus) in REGIONS.items():
        out.append(f"{name.upper()} = {sil.part(region, minus=minus, min_hole=30.0)!r}")
    out.append(f"MUZZLE_R = {sil.radius_profile(-366.0, -512.0, BORE_Y, step=2.0, band=16.0)!r}")
    Path(__file__).with_name("hk416_outline.py").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote hk416_outline.py")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
