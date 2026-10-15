"""
線画の図面（濃い背景に明るい線）から、銃の影絵（シルエット）を作る。

写真のトレース（photo_trace.Silhouette）は「暗い部分＝銃」を前提にしているので、線画はそのままでは使えない。
ここで次の手順で影絵の画像に変換し、それを Silhouette に渡す:

  1. 指定範囲を切り出して拡大（双三次補間。線の輪郭を画素以下でなめらかにするため）
  2. 明るい線を取り出す（赤の成分がしきい値より大きい画素。背景の濃い青・薄いグリッド線は赤が小さい）
  3. 寸法線など銃以外の線を消す（erase: 元画像の座標の矩形）
  4. 画像の外周から「線で囲まれていない領域」を塗る＝背景。残り（線と、線に囲まれた内側）が銃
  5. 線に囲まれていても実際は抜けている場所（トリガーガードの中など）は、seeds の点から背景として塗り直す

  sil_img, info = blueprint_silhouette(path, box, upscale=4, erase=[...], seeds=[...])
  sil_img: 銃が黒・背景が白の画像（拡大後の座標）

図面は第三者の著作物であることが多いので、リポジトリには入れない（トレースした座標だけを入れる）。
"""
import numpy as np
from PIL import Image, ImageDraw


def line_mask(path, box, upscale=4, red_thr=95, erase=()):
    x0, y0, x1, y1 = box
    src = Image.open(path).convert("RGB")
    c = src.crop(box).resize(((x1 - x0) * upscale, (y1 - y0) * upscale), Image.BICUBIC)
    m = np.asarray(c)[:, :, 0].astype(float) > red_thr
    for ex0, ey0, ex1, ey1 in erase:
        m[max(0, (ey0 - y0) * upscale):max(0, (ey1 - y0) * upscale),
          max(0, (ex0 - x0) * upscale):max(0, (ex1 - x0) * upscale)] = False
    return m


def blueprint_silhouette(path, box, upscale=4, red_thr=95, erase=(), seeds=(), close=0):
    """seeds は拡大後の座標（線に囲まれているが実際は抜けている場所の 1 点）。
    close > 0 なら、線を close 画素だけ太らせてから外を塗り、銃の影絵を同じだけ細らせて戻す。解像度の低い図面で
    輪郭線が途切れていると、外からの塗りが部品の内側へ入り込む（中が抜けた影絵になる）のを防ぐ。"""
    from PIL import ImageFilter
    m = line_mask(path, box, upscale, red_thr, erase)
    img = Image.fromarray(np.where(m, 0, 255).astype(np.uint8), "L")
    if close:
        img = img.filter(ImageFilter.MinFilter(2 * close + 1))      # 線（黒）を太らせる
    w, h = img.size
    pad = Image.new("L", (w + 2, h + 2), 255)
    pad.paste(img, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128, thresh=10)
    for sx, sy in seeds:
        if pad.getpixel((sx + 1, sy + 1)) == 255:
            ImageDraw.floodfill(pad, (sx + 1, sy + 1), 128, thresh=10)
    a = np.asarray(pad)[1:-1, 1:-1]
    gun = a != 128
    out = Image.fromarray(np.where(gun, 0, 255).astype(np.uint8), "L")
    if close:
        out = out.filter(ImageFilter.MaxFilter(2 * close + 1))      # 太らせたぶん影絵（黒）を細らせて戻す
    return out, m
