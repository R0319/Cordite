"""
AK-47（Type 3・削り出し受け部・木製の固定ストック）のパーツと組み立て（単位 mm、メッシュ版）。

寸法の根拠（docs/specs/07-model-assets.md「AK-47 の参照品」）:
  - 全長 880mm（固定ストック）・銃身 415mm・照準半径 378mm（Wikipedia の Type 3 の値）
  - 側面の比率は作者提供の図面（線画。全長で縮尺 2.27mm/px）。様式化された図なので、受け部の高さ・ストックの
    落ち・ハンドガードの前後位置など「比率」だけを読み、絶対寸法は公表値と実物の構造から決めた
  - 左右の幅は図面の正面・上面図と実物の構造から（③ 未確認が多い）
座標は M4A1 と同じ: X=0 左右対称面（+X が左側面）、Y=0 グリップ底面、Z=0 トリガー、銃口 -Z。

2 つのモデルを同じ部品から出す:
  ak_47      … 木製の上下ハンドガード・木製グリップ・木製ストック（図面どおりの標準型）
  ak_47_rail … 下ハンドガードをアルミの四面レール、上ハンドガード（ガスチューブカバー）を上面レール付き、
               ダストカバーを上面レール付きに替えたもの。レール寸法はプロジェクト規約（0.5px=12mm/スロット・幅 24mm）
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
from core import MeshPart, Model, box, extrude_x, extrude_x_beveled, inflate_x, lathe
from m249 import arc_ring, clip_y, ring_z, rotated, x_cyl, y_cyl
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
SLOT_MM = ar15_parts.SLOT_MM
RAIL_W = ar15_parts.RAIL_W_MM
STEEL_BLACK = M.STEEL_DARK


class Layout:
    bore_y = 128.0          # ボア軸（グリップ底面基準）。図面: 受け部の上端から約 20mm 下
    muzzle_z = -563.0       # 銃口（全長 880 = 床尾 +317 から）
    barrel_len = 415.0      # 銃身全長（薬室を含む）
    rcv_front_z = -150.0    # 受け部の前端（図面。フロントトラニオンの前面）
    rcv_rear_z = 90.0       # 受け部の後端（リアトラニオン。ストックの付け根）
    rcv_bottom = 91.0       # 受け部の下面（図面: 受け部の高さ約 57mm）
    rcv_top = 148.0         # ダストカバーの上面
    rcv_half = 17.0         # 受け部の半幅（③ 削り出し受け部 約 34mm）
    cover_front_z = -135.0  # ダストカバーの前端（リアサイトブロックに差し込む）
    cover_rear_z = 80.0     # ダストカバーの後端（リアトラニオンの上）
    magwell = (-105.0, -40.0)   # 弾倉口の前後（7.62×39 の弾倉は前後 65mm）
    tg_front_z = -32.0      # トリガーガード前端（弾倉止めレバーの前）
    tg_rear_z = 28.0        # トリガーガード後端
    tg_bottom = 70.0
    grip_top = (44.0, 86.0) # グリップ上面の前後（受け部の下面に付く）
    grip_bottom = (60.0, 100.0)   # グリップ底面の前後（後ろへ寝る）
    butt_z = 317.0          # 床尾
    stock_heel_y = 132.0    # 床尾の上端（図面: ダストカバーより約 16mm 下）
    stock_toe_y = 30.0      # 床尾の下端
    hg_lower = (-152.0, -322.0)   # 下ハンドガード（木）の前後（受け部前面から。図面: 受け部前面〜キャップ 約 148mm）
    hg_upper = (-192.0, -330.0)   # 上ハンドガード（ガスチューブカバー）の前後
    gas_block = (-340.0, -368.0)  # ガスブロック
    gas_tube_y = 150.0      # ガスチューブの中心高さ
    rsb = (-150.0, -192.0)  # リアサイトブロック（受け部前面〜ガスチューブ後端）
    rear_sight_z = -160.0   # 照門の位置
    sight_y = 166.0         # 照準線の高さ
    fsb = (-520.0, -548.0)  # フロントサイトベース（照準半径 378: 照門 -160 → 照星 -538）
    front_sight_z = -538.0
    barrel_r_rear = 9.0     # 銃身半径: 受け部〜ガスブロック
    barrel_r_front = 7.5    # ガスブロック〜銃口
    rod_y = 112.0           # クリーニングロッド（銃身の下）


L = Layout()


# ---------------------------------------------------------------- 材質の割り当て
WOOD = M.WOOD


def _bar_profile(z0, z1, y0, y1):
    return [(z0, y0), (z1, y0), (z1, y1), (z0, y1)]


# ---------------------------------------------------------------- 受け部
def receiver(l=L):
    """削り出し受け部（Type 3）: 箱形。側面の上部に弾倉口の上の軽量化の削り込み（Type 3 の特徴）。
    左右の壁の間は弾倉口・トリガー部分を除いて詰まっている（中は見えない）。"""
    h, zf, zr, yb, yt = l.rcv_half, l.rcv_front_z, l.rcv_rear_z, l.rcv_bottom, l.rcv_top
    body = [(zf, yb), (zr, yb), (zr, yb + 30), (zr - 6, yb + 36), (zr - 6, yt - 18), (zf, yt - 18)]
    out = [extrude_x_beveled(body, -h, h, 1.5, M.RECEIVER, steps=1)]
    # Type 3 の軽量化の削り込み（弾倉口の上、左右）: 浅い凹み（暗い面で表す）
    for s in (1, -1):
        x0, x1 = sorted((s * (h - 0.6), s * (h + 0.2)))
        out.append(box(x0, yb + 14, l.magwell[0] - 10, x1, yb + 30, l.magwell[1] + 2, M.STEEL_DARK))
    # 弾倉口の縁（受け部の下面の開口）
    out.append(box(-h + 2, yb - 0.3, l.magwell[0], h - 2, yb + 0.3, l.magwell[1], M.BORE))
    # セレクターレバー（右側面。上がセーフ。斜めの長い板）
    lever = [(-62.0, 118.0), (-52.0, 124.0), (40.0, 108.0), (40.0, 103.0), (-58.0, 114.0)]
    out.append(extrude_x(lever, -h - 2.5, -h - 0.5, STEEL_BLACK))
    out.append(x_cyl(-30.0, 118.0, 4.5, -h - 3.0, -h, STEEL_BLACK, n=10))           # レバーの軸
    # 左側面のリベット・ピン（削り出しでも機関部のピンは見える）
    for z, y in ((-20.0, 100.0), (14.0, 100.0), (-70.0, 138.0), (60.0, 120.0)):
        for s in (1, -1):
            x0, x1 = sorted((s * (h - 0.3), s * (h + 0.8)))
            out.append(x_cyl(z, y, 2.5, x0, x1, STEEL_BLACK, n=8))
    # リアトラニオンのタング（ストックを受ける）
    out.append(box(-h + 3, yb + 10, zr - 2, h - 3, yt - 24, zr + 12, M.RECEIVER))
    return out


def dust_cover(l=L, rail=False):
    """ダストカバー: 板金の蓋。上面は丸く（断面が半円に近い）、後端にリコイルスプリングガイドのボタン。
    rail=True なら上面に MIL-STD-1913 レール（光学機器用のレール付きカバー）。"""
    h, zf, zr, yt = l.rcv_half, l.cover_front_z, l.cover_rear_z, l.rcv_top
    prof = [(zf, yt - 18), (zr, yt - 18), (zr, yt), (zf, yt)]
    out = [extrude_x_beveled(prof, -h, h, 7.0, M.RECEIVER, steps=3)]
    out.append(box(-6, yt - 14, zr - 1, 6, yt - 4, zr + 4, STEEL_BLACK))             # ガイドロッドのボタン
    # 横の補強リブ（板金のビード）3 本
    for z in (-100.0, -40.0, 20.0):
        out.append(box(-h + 1, yt - 0.3, z - 2, h - 1, yt + 0.6, z + 2, M.RECEIVER))
    if rail:
        slots = 16
        z1 = zr - 8
        z0 = z1 - slots * SLOT_MM
        out += [box(-8, yt, z0, 8, yt + 4, z1, M.RAIL), box(-RAIL_W / 2, yt + 4, z0, RAIL_W / 2, yt + 9, z1, M.RAIL)]
    return out


def trigger_guard(l=L):
    """トリガーガード（板金）と弾倉止めレバー（ガードの前）。"""
    h = 6.0
    zf, zr, yb, yt = l.tg_front_z, l.tg_rear_z, l.tg_bottom, l.rcv_bottom
    guard = {"outer": [(zf, yt), (zf, yb + 6), (zf + 4, yb), (zr - 6, yb), (zr, yb + 8), (zr, yt)],
             "holes": [[(zf + 3, yt - 0.5), (zr - 3, yt - 0.5), (zr - 3, yb + 7), (zr - 7, yb + 3), (zf + 5, yb + 3), (zf + 3, yb + 7)]]}
    from m249 import outline_parts
    out = outline_parts(guard, -h, h, STEEL_BLACK)
    out.append(extrude_x([(zf - 14, yt), (zf, yt), (zf, yt - 14), (zf - 10, yt - 18)], -5, 5, STEEL_BLACK))   # 弾倉止めレバー
    return out


def trigger(l=L):
    return [extrude_x([(-3, l.rcv_bottom), (3, l.rcv_bottom), (2, 76.0), (-6, 78.0)], -3, 3, STEEL_BLACK)]


def pistol_grip(l=L):
    """木製グリップ: 上面は受け部の下面に付き、下へ向かって後ろへ寝る。断面は楕円。"""
    (t0, t1), (b0, b1) = l.grip_top, l.grip_bottom
    yt = l.rcv_bottom
    prof = [(t0, yt), (t1, yt), (t1 + 2, yt - 20), (b1, 4.0), (b1 - 4, 0.0), (b0 + 4, 0.0), (b0, 4.0), (t0 - 1, yt - 25)]

    def radius(nz, ny):
        return 5.0 if ny < -0.7 else 14.0
    return [inflate_x(prof, 15.0, WOOD, steps=4, radius_fn=radius)]


def stock(l=L):
    """木製の固定ストック: 受け部後端のタングから床尾へ。上面はほぼ水平、下面は床尾へ向かって下がる。
    床尾には鋼の床尾板（図面: 無地）。断面は前が細く（受け部の幅）、床尾で広い。"""
    zr, zb = l.rcv_rear_z, l.butt_z
    yt0, yb0 = l.rcv_top - 8, l.rcv_bottom + 2      # 付け根の上下（受け部の中に差し込まれる）
    heel, toe = l.stock_heel_y, l.stock_toe_y
    # 図面の側面形: 上面は受け部上端のすぐ下から床尾の踵へなだらかに下がり（落ち 約 10mm）、
    # 下面は付け根から爪先へ大きく下がる（約 60mm）。途中は少し凹んだ曲線。
    prof = [(zr, yb0), (zr + 30, yb0 - 14), (zr + 90, yb0 - 32), (zr + 160, toe + 18), (zb - 4, toe), (zb, toe + 2),
            (zb, heel - 2), (zb - 4, heel), (zr + 120, heel + 2), (zr + 40, yt0 - 4), (zr, yt0)]

    def width(z, y, f):
        return 0.9 + 0.35 * (z - zr) / (zb - zr)       # 付け根 29mm → 床尾 40mm

    def radius(nz, ny):
        return 9.0
    out = [inflate_x(prof, 16.0, WOOD, steps=4, width_fn=width, radius_fn=radius)]
    plate = [(zb - 1, toe + 1), (zb + 3, toe + 1), (zb + 3, heel - 1), (zb - 1, heel - 1)]
    out.append(extrude_x_beveled(plate, -21, 21, 1.0, STEEL_BLACK, steps=1))   # 板厚 4mm なので丸めは 1mm まで
    out.append(x_cyl(zb + 1, heel - 14, 2.2, -21.5, -20.5, STEEL_BLACK, n=8))       # 床尾板のねじ（左）
    out.append(x_cyl(zb + 1, toe + 14, 2.2, -21.5, -20.5, STEEL_BLACK, n=8))
    out.append(ring_z(0.0, -1.5, 1.5, 3.5, 6.0, STEEL_BLACK, n=10))                  # 負い紐の輪（下面。位置は後で動かす）
    out[-1] = MeshPart([(v[2], v[1] + toe + 30.0, v[0] + zb - 60.0) for v in out[-1].verts], out[-1].faces,
                       out[-1].mat, None, out[-1].charts, out[-1].chart_uv, out[-1].chart_edge)
    return out


# ---------------------------------------------------------------- 銃身まわり
def barrel(l=L):
    b = l.bore_y
    bore = 7.62 / 2
    gz = l.gas_block[0]
    pts = [(l.muzzle_z, bore), (l.muzzle_z, l.barrel_r_front), (gz, l.barrel_r_front), (gz, l.barrel_r_rear),
           (l.rcv_front_z - 2, l.barrel_r_rear)]
    return [lathe(0, b, pts, ar15_mesh.N_MID, M.STEEL, cap0=False),
            lathe(0, b, [(l.muzzle_z, bore), (l.muzzle_z + 25, bore)], ar15_mesh.N_SMALL, M.BORE, cap0=False)]


def muzzle_nut(l=L):
    """銃口のナット（AK-47 はスラントブレーキではなく、ねじ山を守る短いナット）。"""
    b, z = l.bore_y, l.muzzle_z
    return [lathe(0, b, [(z, 4.0), (z, 9.0), (z + 14, 9.0), (z + 14, l.barrel_r_front)], ar15_mesh.N_MID, STEEL_BLACK,
                  cap0=False, cap1=False)]


def rear_sight_block(l=L):
    """リアサイトブロック: 受け部の前で銃身を抱き、上にタンジェント式の照門（距離目盛の板）を載せる。
    ガスチューブの後端もここに差し込む。"""
    b = l.bore_y
    z0, z1 = l.rsb           # z0 が後ろ（受け部側）
    out = [lathe(0, b, [(z1, 12.5), (z0, 12.5)], ar15_mesh.N_MID, STEEL_BLACK)]
    out.append(extrude_x([(z1, b), (z0, b), (z0, l.gas_tube_y + 4), (z1 + 10, l.gas_tube_y + 4), (z1, l.gas_tube_y - 6)],
                         -11, 11, STEEL_BLACK))                                     # 台（前面は斜め。ガスチューブの受け）
    # 照門の板: 後ろの軸から前へ斜めに上がる（タンジェントサイト）。板の後端に V 字の照門
    leaf = [(z0 + 2, l.gas_tube_y + 4), (z1 + 4, l.gas_tube_y + 4), (z1 + 4, l.sight_y - 2), (z0 + 2, l.sight_y + 2)]
    out.append(extrude_x(leaf, -8, 8, STEEL_BLACK))
    out.append(box(-8.5, l.sight_y - 4, l.rear_sight_z - 3, 8.5, l.sight_y + 4, l.rear_sight_z + 3, STEEL_BLACK))  # 照門（遊底）
    out.append(box(-1.5, l.sight_y + 0.5, l.rear_sight_z - 3.2, 1.5, l.sight_y + 4.3, l.rear_sight_z + 3.2, M.BORE))  # V 字の切り欠き
    out.append(box(-6, l.gas_tube_y + 4, z1 + 8, 6, l.gas_tube_y + 10, z1 + 26, STEEL_BLACK))   # 距離目盛の調整つまみ
    return out


def gas_block(l=L):
    """ガスブロック: 銃身を抱き、上へガスチューブ、下に着剣ラグ・クリーニングロッドの通し穴。"""
    b = l.bore_y
    z0, z1 = l.gas_block     # z0 が後ろ
    out = [lathe(0, b, [(z1, 12.0), (z0, 12.0)], ar15_mesh.N_MID, STEEL_BLACK),
           box(-9, b, z1 + 2, 9, l.gas_tube_y + 6, z0 - 2, STEEL_BLACK),             # ガスポートの筒
           lathe(0, l.gas_tube_y, [(z1, 7.5), (z0 + 4, 7.5)], ar15_mesh.N_SMALL, STEEL_BLACK),
           box(-4, l.rod_y - 8, z1 + 4, 4, b - 8, z0 - 4, STEEL_BLACK)]              # 下のラグ（ロッドの通し穴の台）
    return out


def gas_tube(l=L):
    b = l.gas_tube_y
    return [lathe(0, b, [(l.gas_block[0], 7.0), (l.rsb[1] + 2, 7.0)], ar15_mesh.N_SMALL, M.STEEL)]


def cleaning_rod(l=L):
    return [lathe(0, l.rod_y, [(l.fsb[1] + 10, 2.5), (l.hg_lower[1] - 4, 2.5)], 6, M.STEEL)]


def front_sight(l=L):
    """フロントサイト: 銃身を抱く台から塔が立ち、上に半円のフード（上が開いた輪）とポスト。台の下に着剣ラグ。"""
    b = l.bore_y
    z0, z1 = l.fsb           # z0 が後ろ
    zc = l.front_sight_z
    hood_cy = l.sight_y + 2.0
    out = [lathe(0, b, [(z1, 11.0), (z0, 11.0)], ar15_mesh.N_MID, STEEL_BLACK),
           extrude_x_beveled([(z0 - 2, b), (z1 + 2, b), (zc - 7, hood_cy - 10), (zc + 7, hood_cy - 10)], -6, 6, 1.0,
                             STEEL_BLACK, steps=1),                                      # 塔
           arc_ring(0.0, hood_cy, zc - 4, zc + 4, 8.5, 10.5, 120.0, 420.0, STEEL_BLACK, n=14),   # フード（上が開く）
           box(-4, hood_cy - 12, zc - 5, 4, hood_cy - 8, zc + 5, STEEL_BLACK),           # ポストの台
           box(-1.0, hood_cy - 8, zc - 1.0, 1.0, l.sight_y, zc + 1.0, STEEL_BLACK),      # ポスト（先端＝照準線）
           box(-5, l.rod_y - 6, z1 + 2, 5, b - 7, z0 - 2, STEEL_BLACK),                  # 着剣ラグ・ロッドの受け
           lathe(0, b, [(z1 - 1, 9.5), (z1 - 1, 11.0)], ar15_mesh.N_MID, STEEL_BLACK, cap0=False, cap1=False)]
    return out


# ---------------------------------------------------------------- ハンドガード
def lower_handguard_wood(l=L):
    """下ハンドガード（木）: 銃身の下を抱く。断面は下が丸い箱形。前後の端は鋼の留め金。"""
    b = l.bore_y
    zr, zf = l.hg_lower      # zr が後ろ（受け部側）
    top, bottom = b - 2, b - 34

    def radius(nz, ny):
        return 11.0 if ny < -0.5 else 3.0
    prof = [(zf + 6, bottom), (zr - 6, bottom), (zr, bottom + 4), (zr, top), (zf, top), (zf + 2, bottom + 4)]
    # inflate_x は半幅ぶん内側へ縮めた輪郭を使うので、半幅は輪郭の最小厚み（高さ 32）の半分より小さくする
    out = [inflate_x(prof, 15.0, WOOD, steps=4, radius_fn=radius)]
    # 前後の鋼の留め金（前: ハンドガードキャップ、後ろ: 受け部前面の受け）
    out.append(extrude_x_beveled([(zf - 8, bottom - 2), (zf + 1, bottom - 2), (zf + 1, b + 1), (zf - 8, b + 1)], -17, 17, 2.0,
                                 STEEL_BLACK, steps=1))
    out.append(extrude_x_beveled([(zr - 1, bottom - 1), (zr + 8, bottom - 1), (zr + 8, b + 1), (zr - 1, b + 1)], -17, 17, 2.0,
                                 STEEL_BLACK, steps=1))
    return out


def upper_handguard_wood(l=L):
    """上ハンドガード（木製のガスチューブカバー）: ガスチューブを覆う丸い木。両端は鋼の金具。"""
    g = l.gas_tube_y
    zr, zf = l.hg_upper
    out = [lathe(0, g, [(zf, 7.5), (zf + 4, 12.0), (zr - 4, 12.0), (zr, 7.5)], ar15_mesh.N_MID, WOOD)]
    out.append(lathe(0, g, [(zf - 6, 8.0), (zf, 8.0)], ar15_mesh.N_SMALL, STEEL_BLACK))
    out.append(lathe(0, g, [(zr, 8.0), (zr + 6, 8.0)], ar15_mesh.N_SMALL, STEEL_BLACK))
    return out


def _rail(z0, z1, y_base, s_dir, mat, along="y"):
    """レールの首＋頭。along='y' なら上下向き（s_dir=+1 上 / -1 下）、'x' なら左右向き。"""
    nh, hh = 2.0, 4.0
    if along == "y":
        return [box(-8, y_base, z0, 8, y_base + s_dir * nh, z1, mat) if s_dir > 0 else
                box(-8, y_base - nh, z0, 8, y_base, z1, mat),
                box(-RAIL_W / 2, y_base + s_dir * nh, z0, RAIL_W / 2, y_base + s_dir * (nh + hh), z1, mat)]
    return None


def lower_handguard_rail(l=L):
    """レール付きの下ハンドガード（アルミ・四面レール）。本体は箱形で、下面と左右にレール。
    上面は無く、上ハンドガード側のレールが上面レールになる。"""
    b = l.bore_y
    zr, zf = l.hg_lower
    top, bottom = b - 3, b - 30
    hw = 20.0
    body = [(zf, bottom), (zr, bottom), (zr, top), (zf, top)]
    out = [extrude_x_beveled(body, -hw, hw, 2.0, M.RECEIVER, steps=1)]
    slots = int((zr - zf) // SLOT_MM) - 1
    z1 = (zr + zf) / 2 + slots * SLOT_MM / 2
    z0 = z1 - slots * SLOT_MM
    # 下面レール
    out += [box(-8, bottom - 2, z0, 8, bottom, z1, M.RAIL_DOWN),
            box(-RAIL_W / 2, bottom - 6, z0, RAIL_W / 2, bottom - 2, z1, M.RAIL_DOWN)]
    # 側面レール（左右）
    yc = (top + bottom) / 2
    for s in (1, -1):
        x0, x1 = sorted((s * hw, s * (hw + 2)))
        out.append(box(x0, yc - 8, z0, x1, yc + 8, z1, M.RAIL_SIDE))
        x0, x1 = sorted((s * (hw + 2), s * (hw + 6)))
        out.append(box(x0, yc - RAIL_W / 2, z0, x1, yc + RAIL_W / 2, z1, M.RAIL_SIDE))
    # 放熱の丸穴（上寄りの側面に 1 列）
    for k in range(6):
        z = z0 + (z1 - z0) * (k + 0.5) / 6
        for s in (1, -1):
            x0, x1 = sorted((s * (hw - 0.3), s * (hw + 0.3)))
            out.append(x_cyl(z, top - 6, 3.0, x0, x1, M.BORE, n=10))
    return out, (z0, z1), (bottom - 6, hw + 6)


def upper_handguard_rail(l=L):
    """レール付きの上ハンドガード（ガスチューブカバー）: アルミの半円カバーに上面レール。"""
    g = l.gas_tube_y
    zr, zf = l.hg_upper
    out = [lathe(0, g, [(zf, 8.0), (zf + 3, 12.5), (zr - 3, 12.5), (zr, 8.0)], ar15_mesh.N_MID, M.RECEIVER)]
    slots = int((zr - zf - 10) // SLOT_MM)
    z1 = (zr + zf) / 2 + slots * SLOT_MM / 2
    z0 = z1 - slots * SLOT_MM
    y = g + 11.0
    out += [box(-8, y, z0, 8, y + 3, z1, M.RAIL), box(-RAIL_W / 2, y + 3, z0, RAIL_W / 2, y + 7, z1, M.RAIL)]
    return out, (z0, z1), y + 7


# ---------------------------------------------------------------- 機関部の可動部
def bolt_carrier(l=L):
    """ボルトキャリア（ダストカバーの中。右側面のコッキングハンドルだけが外に出る）。"""
    b = l.bore_y
    return [box(-12, b - 6, -120, 12, b + 14, -40, M.STEEL)]


def charging_handle(l=L):
    """コッキングハンドル（右側面。ボルトキャリアと一体で前後に動く）。"""
    b, h = l.bore_y, l.rcv_half
    return [box(-h - 12, b + 8, -70, -h + 2, b + 16, -56, STEEL_BLACK),
            extrude_x([(-72, b + 4), (-54, b + 4), (-50, b + 14), (-76, b + 14)], -h - 20, -h - 12, STEEL_BLACK)]


# ---------------------------------------------------------------- 弾倉
MAG_DEPTH = 64.0        # 前後（7.62×39 の全長 56mm ＋壁）
MAG_HALF_W = 13.5       # 半幅（複列 27mm。③）
MAG_STRAIGHT = 42.0     # 直線部（弾倉口の中を含む）
MAG_ARC_DEG = 52.0      # 湾曲の角度（7.62×39 のテーパーが大きく、バナナ形が強い）
MAG_ARC_LEN = 118.0     # 湾曲部の長さ。弾倉の下端がグリップ底面の約 55mm 下（図面の比率）になる長さ
MAG_STEPS = 10


def magazine_ak(l=L):
    """AK 30 発弾倉（鋼・リブ付き）: 上は直線、下は半径一定で前へ強く反る。側面に縦リブ 2 本と横の補強。"""
    top = l.rcv_bottom + 18.0                        # 弾倉上端（受け部の中、給弾口）
    split = top - MAG_STRAIGHT
    zc, half = sum(l.magwell) / 2, MAG_DEPTH / 2
    radius = MAG_ARC_LEN / math.radians(MAG_ARC_DEG)
    center = [(zc, top), (zc, split)]
    tangents = [0.0, 0.0]
    for i in range(1, MAG_STEPS + 1):
        t = math.radians(MAG_ARC_DEG) * i / MAG_STEPS
        center.append((zc - radius * (1 - math.cos(t)), split - radius * math.sin(t)))
        tangents.append(t)
    back = [(cz + half * math.cos(t), cy - half * math.sin(t)) for (cz, cy), t in zip(center, tangents)]
    front = [(cz - half * math.cos(t), cy + half * math.sin(t)) for (cz, cy), t in zip(center, tangents)]
    body = back + front[::-1]
    (cz, cy), t = center[-1], tangents[-1]
    dn = (-math.sin(t), -math.cos(t))
    nb = (math.cos(t), -math.sin(t))

    def p(s_n, s_d):
        return (cz + nb[0] * s_n + dn[0] * s_d, cy + nb[1] * s_n + dn[1] * s_d)

    def strip(o0, o1, i0=0):
        pts = [(cz_ + o1 * math.cos(tt), cy_ - o1 * math.sin(tt)) for (cz_, cy_), tt in zip(center[i0:], tangents[i0:])]
        pts += [(cz_ + o0 * math.cos(tt), cy_ - o0 * math.sin(tt)) for (cz_, cy_), tt in zip(center[i0:], tangents[i0:])][::-1]
        return pts
    plate = [p(half + 3, -2), p(half + 3, 5), p(-half - 3, 5), p(-half - 3, -2)]
    out = [extrude_x(body, -MAG_HALF_W, MAG_HALF_W, M.MAG_AK),
           extrude_x(plate, -MAG_HALF_W - 1.5, MAG_HALF_W + 1.5, STEEL_BLACK)]
    for o in (-12.0, 12.0):                                           # 縦リブ 2 本（鋼の補強ビード）
        out.append(extrude_x(strip(o - 2.0, o + 2.0, 2), -MAG_HALF_W - 1.2, MAG_HALF_W + 1.2, M.MAG_AK))
    out.append(extrude_x(strip(-half - 1.5, -half + 2.5, 2), -MAG_HALF_W - 0.8, MAG_HALF_W + 0.8, M.MAG_AK))   # 前の背
    out.append(extrude_x(strip(half - 2.5, half + 1.5, 2), -MAG_HALF_W - 0.8, MAG_HALF_W + 0.8, M.MAG_AK))     # 後ろの背
    return out, (zc, top)


def cartridge_762(z_tip, y):
    """7.62×39mm 実包（回転体）: 全長 56mm、薬莢 38.7mm、テーパーの強い胴。"""
    b = z_tip + 56.0
    case = [(b, 5.6), (b - 1.5, 5.6), (b - 1.8, 4.9), (b - 3.0, 4.9), (b - 3.4, 5.55), (b - 30.5, 5.2),
            (b - 33.5, 4.4), (b - 38.7, 4.3)]
    bullet = [(b - 38.7, 3.9), (b - 44.0, 3.85), (b - 50.0, 2.9), (b - 54.5, 1.2), (z_tip, 0.4)]
    return ([lathe(0, y, case, ar15_mesh.N_SMALL, M.BRASS, cap0=True, cap1=False)],
            [lathe(0, y, bullet, ar15_mesh.N_SMALL, M.COPPER, cap0=False, cap1=True)])


# ---------------------------------------------------------------- 組み立て
def build(variant="wood"):
    l = L
    b = l.bore_y
    rail = variant == "rail"
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "receiver", receiver() + dust_cover(rail=rail))
    add("lower_receiver", "receiver", (0, l.rcv_bottom, 0), "trigger_guard", trigger_guard())
    add("pistol_grip", "receiver", (0, l.rcv_bottom, 65), "pistol_grip", pistol_grip())
    add("trigger", "root", (0, l.rcv_bottom, 0), "trigger", trigger())
    add("stock", "root", (0, b, l.rcv_rear_z), "stock", stock())

    add("barrel", "root", (0, b, l.rcv_front_z), "barrel", barrel())
    add("chamber", "barrel", (0, b, l.rcv_front_z), None, [])
    add("rear_sight", "barrel", (0, b, l.rsb[0]), "rear_sight_block", rear_sight_block())
    add("gas_block", "barrel", (0, b, l.gas_block[0]), "gas_block", gas_block() + gas_tube() + cleaning_rod())
    add("front_sight_base", "barrel", (0, b, l.fsb[0]), "front_sight", front_sight())
    add("front_sight_post", "front_sight_base", (0, l.sight_y, l.front_sight_z), None, [])
    add("muzzle", "root", (0, b, l.muzzle_z), "muzzle_nut", muzzle_nut())

    if rail:
        lower, (rz0, rz1), (rail_bottom_y, rail_side_x) = lower_handguard_rail()
        upper, (uz0, uz1), upper_top = upper_handguard_rail()
        add("handguard", "root", (0, b, l.hg_lower[0]), "handguard_rail", lower + upper)
        add("rail_top", "root", (0, l.rcv_top + 9, l.cover_rear_z - 8), None, [])   # ダストカバーのレールは receiver 側に含む
        add("rail_bottom", "root", (0, rail_bottom_y, rz1), None, [])
        add("rail_side", "root", (rail_side_x, b - 16.5, rz1), None, [])
    else:
        add("handguard", "root", (0, b, l.hg_lower[0]), "handguard_wood", lower_handguard_wood() + upper_handguard_wood())
        add("rail_top", "root", (0, l.rcv_top, l.cover_rear_z), None, [])
        add("rail_bottom", "root", (0, b - 32, l.hg_lower[0]), None, [])
        add("rail_side", "root", (l.rcv_half, b, l.hg_lower[0]), None, [])

    add("bolt", "root", (0, b, -80), "bolt_carrier", bolt_carrier())
    add("charging_handle", "bolt", (-l.rcv_half, b + 10, -63), "charging_handle", charging_handle())

    mag, (mz, mtop) = magazine_ak()
    add("magazin", "root", (0, l.rcv_bottom, mz), "magazine_ak", mag)
    case, bullet = cartridge_762(z_tip=mz - 28, y=mtop - 6)
    add("mag_ammo", "magazin", (0, mtop - 6, mz + 2), None, case + bullet)

    tip = l.rcv_front_z - 20 - 56.0                 # 薬室内の実包（排莢クリップの起点）
    case, bullet = cartridge_762(z_tip=tip, y=b)
    add("ammo", "root", (0, b, tip + 35), None, case)
    add("bullet", "ammo", (0, b, tip + 6), None, bullet)

    grip_center = (0, l.rcv_bottom / 2, (sum(l.grip_top) + sum(l.grip_bottom)) / 4)
    add_locators(m, muzzle=(0, b * K, l.muzzle_z * K), sight_line_y=l.sight_y * K,
                 rear_sight_z=l.rear_sight_z * K, grip_center=tuple(v * K for v in grip_center))
    return m, parts
