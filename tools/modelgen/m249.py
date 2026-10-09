"""
M249（FN 標準型・固定ストック）のパーツと組み立て（単位 mm、メッシュ版）。

寸法の根拠（docs/specs/07-model-assets.md「M249 の参照品」）:
  - 全長 1035mm（40.75in、FN 公表値）・銃身 465mm（18.3in）
  - 側面形は作者提供の写真（STANAG 弾倉・二脚をたたんだ状態／ボックス＋ベルト・二脚を立てた状態の 2 枚）から取った。
    縮尺は全長で合わせた 0.704px/mm（1px≒1.4mm と粗い）。写真は再現品の可能性がある
  - 左右の幅（受け部の幅・ハンドガード・ストック等）は写真が真横だけなので未確認（③）
座標は M4A1 と同じ: X=0 左右対称面（+X が左側面＝弾倉・ベルトの側）、Y=0 グリップ底面、Z=0 トリガー、銃口 -Z。

2 つのモデルを同じ部品から出す: m249（ボックス＋ベルト。仕様の装弾数 100 発に合わせた標準）と m249_stanag（STANAG 弾倉）。
二脚・キャリングハンドル・フィードカバーは回転できるボーンにし、既定はたたんだ状態（写真 1 枚目）。
"""
import math

import ar15_mesh
import ar15_parts
import materials as M
from core import MeshPart, Model, box, extrude_x, extrude_x_beveled, inflate_x, lathe
from rig import add_locators

K = 1.0 / ar15_parts.MM_PER_PX
SLOT_MM = ar15_parts.SLOT_MM
RAIL_W = ar15_parts.RAIL_W_MM


class Layout:
    bore_y = 169.3          # ボア軸高さ（グリップ底面基準）
    muzzle_z = -651.0       # フラッシュハイダー先端（全長 1035mm: 床尾 384 から）
    barrel_end_z = -603.0   # 銃身の先端（フラッシュハイダーの付け根）
    breech_z = -138.0       # 銃身の後端（薬室）。銃身 465mm から逆算（受け部前端の少し奥）
    rcv_rear_z = 121.4      # 受け部の後端（ストックの付け根）
    rcv_front_z = -151.0    # 受け部の前端
    rcv_half = 27.0         # 受け部の半幅（③ 未確認）
    rcv_bottom = 110.0      # 受け部の下面
    cover_split = 184.7     # 受け部本体とフィードカバーの境目
    cover_top = 211.0       # フィードカバーの上面（レールの土台）
    cover_front_z = -131.0  # フィードカバーの前端（フィードトレイの前）
    rail_slots = 15         # フィードカバーのレール（写真 約 176mm ÷ 規約 12mm/スロット）
    rail_rear_z = 58.0
    rail_h = 9.2
    sight_y = 222.0         # 照準線の高さ（リアサイトの穴の中心。写真から）
    rear_sight_z = 87.4     # リアサイトの穴の位置
    feed_z = (-131.0, -52.0)   # フィードトレイ（左側のベルト入口）と弾倉口の前後範囲
    hg_rear_z = -151.0      # ハンドガード
    hg_front_z = -362.0
    hg_top = 178.0
    hg_bottom = 97.0
    hg_half = 29.0          # ハンドガードの半幅（③ 未確認）
    shield = (-176.0, -349.0, 180.0, 196.0)   # 銃身上のレール台（前後・下面・上面）
    gas_y = 140.0           # ガスシリンダーの中心高さ
    gas_front_z = -458.0
    fs_z = (-419.0, -442.0)  # フロントサイトの前後
    fs_top = 232.0          # フロントサイトの耳の上端
    bipod_pivot = (-380.0, 122.0)   # 二脚の回転軸（z, y）
    bipod_len = 232.0       # 回転軸→足先（縮めた状態）
    bipod_ext = 30.0        # 脚の伸び（写真の展開状態は 約 260mm）
    bipod_fold_deg = 7.4    # たたんだ脚の下向きの傾き（写真）
    handle_pivot = (-170.0, 206.0)  # キャリングハンドルの回転軸（z, y）
    mag_tilt = 45.0         # STANAG 弾倉の傾き（左下へ。③ 写真の見かけの高さ 122mm と 45° が一致）
    mag_pivot = (14.0, 170.0)       # 弾倉上端の中心（X, y）。写真の弾倉下端に合わせた
    mag_center_z = -84.0
    box = (-46.0, -131.0, 0.0, 118.0)   # ボックス（前後・下面・上面）
    box_x = (-50.0, 80.0)   # ボックスの左右（③ 幅 約 130mm。左斜め前の写真で受け部の左右両方へはみ出し、左の方が大きい）
    butt_z = 384.0


L = Layout()
STEEL_BLACK = M.STEEL_DARK


def rotated(parts, axis, deg, pivot):
    """MeshPart の頂点・法線を軸（'x' / 'z'）まわりに回す。pivot は (x, y, z)。"""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)

    def rot(v, p=True):
        x, y, z = (v[0] - pivot[0], v[1] - pivot[1], v[2] - pivot[2]) if p else v
        if axis == "z":
            x, y = x * c - y * s, x * s + y * c
        else:
            y, z = y * c - z * s, y * s + z * c
        return (x + pivot[0], y + pivot[1], z + pivot[2]) if p else (x, y, z)

    out = []
    for m in parts:
        n = None if m.normals is None else [[rot(v, False) for v in f] for f in m.normals]
        out.append(MeshPart([rot(v) for v in m.verts], m.faces, m.mat, n, m.charts, m.chart_uv, m.chart_edge))
    return out


def _zy(pts):
    return [(z, y) for z, y in pts]


# ---------------------------------------------------------------- 受け部
def receiver(l=L):
    h, b = l.rcv_half, l.bore_y
    side = [(l.rcv_front_z, l.rcv_bottom), (l.rcv_rear_z, l.rcv_bottom), (l.rcv_rear_z, l.cover_split),
            (l.rcv_front_z, l.cover_split)]
    return [
        extrude_x_beveled(side, -h, h, 1.5, M.RECEIVER, steps=1),              # 本体（鋼板のプレス。角張ったまま）
        box(h, 150, l.rcv_front_z + 6, h + 1.2, 160, l.rcv_rear_z - 6, M.RECEIVER),    # 側面の補強の帯（左）
        box(-h - 1.2, 150, l.rcv_front_z + 6, -h, 160, l.rcv_rear_z - 6, M.RECEIVER),  # 〃（右）
        # 左側のフィードトレイ（ベルトの入口）とその下の弾倉口
        box(h, 170.5, l.feed_z[0], h + 8, 209.5, l.feed_z[1], M.RECEIVER),
        # 右側のコッキングハンドル（受け部前寄り、③ 位置は写真の下側の突起から推定）
        box(-h - 18, 158, -152, -h, 166, -140, STEEL_BLACK),
        # 受け部前端の銃身受け（トラニオン）
        lathe(0, b, [(l.rcv_front_z - 6, 20), (l.rcv_front_z + 2, 20)], ar15_mesh.N_MID, STEEL_BLACK),
    ]


def magwell(l=L):
    """弾倉口: 受け部の左下から 45° 左下へ向いた短い筒。"""
    px, py = l.mag_pivot
    zc = l.mag_center_z
    sleeve = [(zc - 36, py + 8), (zc + 36, py + 8), (zc + 36, py - 14), (zc - 36, py - 14)]
    return rotated([extrude_x(sleeve, px - 15, px + 15, M.RECEIVER)], "z", l.mag_tilt, (px, py, zc))


def feed_cover(l=L):
    """フィードカバー（上面にレール、後ろにリアサイト）。後ろの蝶番で上へ開く（ボーン feed_cover）。"""
    h = l.rcv_half
    prof = [(l.cover_front_z, l.cover_split), (l.rcv_rear_z - 3, l.cover_split), (l.rcv_rear_z - 3, l.cover_top - 4),
            (l.rcv_rear_z - 8, l.cover_top), (l.cover_front_z + 4, l.cover_top), (l.cover_front_z, l.cover_top - 4)]
    return [extrude_x_beveled(prof, -h + 1, h - 1, 2.0, M.RECEIVER, steps=1)]


def rail_top(l=L):
    z1 = l.rail_rear_z
    z0 = z1 - l.rail_slots * SLOT_MM
    y0 = l.cover_top
    return [box(-8, y0, z0, 8, y0 + 4, z1, M.RAIL),
            box(-RAIL_W / 2, y0 + 4, z0, RAIL_W / 2, y0 + l.rail_h, z1, M.RAIL)]


def rear_sight(l=L):
    """リアサイト: フィードカバー後部の台に、左右の耳に守られたアパーチャー（穴の中心＝照準線）。"""
    z, sy, y0 = l.rear_sight_z, l.sight_y, l.cover_top
    ear = [(z + 14, y0), (z - 18, y0), (z - 14, sy + 9), (z - 6, sy + 12.4), (z + 6, sy + 12.4), (z + 12, sy + 7)]
    return [
        box(-13, y0, z - 28, 13, y0 + 6, z + 33, M.RECEIVER),                  # 台
        extrude_x_beveled(ear, 6, 11, 1.0, M.RECEIVER, steps=1),               # 耳（左）
        extrude_x_beveled(ear, -11, -6, 1.0, M.RECEIVER, steps=1),             # 耳（右）
        # アパーチャー板（中央に 3mm の穴）
        box(-5, y0 + 6, z - 1, 5, sy - 1.5, z + 1, STEEL_BLACK),
        box(-5, sy + 1.5, z - 1, 5, sy + 6, z + 1, STEEL_BLACK),
        box(1.5, sy - 1.5, z - 1, 5, sy + 1.5, z + 1, STEEL_BLACK),
        box(-5, sy - 1.5, z - 1, -1.5, sy + 1.5, z + 1, STEEL_BLACK),
        lathe(-13, y0 + 12, [(z - 6, 5), (z + 6, 5)], ar15_mesh.N_SMALL, STEEL_BLACK),   # 高さ調整のドラム（右）
    ]


# ---------------------------------------------------------------- 下回り（側面形は写真から）
# グリップの側面形（写真から）。底は Y≒5（Y=0 の約 5mm 上。写真の縮尺誤差の範囲）
GRIP = [(71.0, 108.0), (76.3, 81.7), (84.0, 62.0), (92.3, 42.6), (101.2, 26.0), (102.5, 17.0), (98.5, 8.5),
        (90.0, 5.5), (60.0, 5.5), (43.0, 8.5), (36.0, 16.5), (33.0, 30.0), (32.0, 49.7), (27.0, 62.0),
        (21.3, 81.7), (16.5, 95.0), (14.2, 108.0)]
STOCK = [(121.4, 203.0), (130.0, 203.1), (155.5, 190.3), (189.6, 176.1), (223.6, 169.0), (249.3, 163.4),
         (257.8, 164.8), (266.0, 169.0), (274.9, 177.6), (283.0, 181.8), (352.0, 188.9),
         (352.0, 68.2), (266.0, 70.0), (257.8, 72.4), (252.0, 80.0), (249.3, 100.9), (240.8, 106.5),
         (215.0, 112.2), (172.6, 119.3), (130.0, 120.7), (121.4, 121.0)]


def pistol_grip(l=L):
    """樹脂のグリップ。断面は丸め、上端は受け部の下面（Y=108）に接する。"""
    from core import smooth
    pts = smooth(GRIP, 3)[:-1]

    def radius(nz, ny):
        return 4.0 + 8.0 * (1 - ar15_mesh._smoothstep(0.55, 0.9, abs(ny)))
    return [inflate_x(pts, 14.0, M.POLYMER, steps=ar15_mesh.GRIP_STEPS, radius_fn=radius)]


def trigger_guard(l=L):
    return [
        box(-5, 72.4, 11.0, 5, 108.0, 14.2, M.RECEIVER),     # 後ろの柱
        box(-5, 72.4, -40.5, 5, 108.0, -37.5, M.RECEIVER),   # 前の柱
        box(-5, 72.4, -40.5, 5, 75.6, 14.2, M.RECEIVER),     # 下辺
    ]


def trigger(l=L):
    blade = [(5.0, 109.0), (6.0, 100.0), (4.5, 92.0), (1.0, 86.0), (-3.0, 84.0), (-2.0, 88.0), (0.0, 94.0),
             (1.0, 101.0), (0.0, 109.0)]
    return [extrude_x_beveled(blade, -3, 3, 1.0, STEEL_BLACK, steps=1)]


def stock(l=L):
    """固定ストック（樹脂）: 床尾側が高く、首は細く受け部の後端へ上がる。床尾板と肩当て（上の小さな鉤）付き。"""
    return [
        extrude_x_beveled(STOCK, -19, 19, 5.0, M.POLYMER, steps=ar15_mesh.BEVEL_STEPS),
        extrude_x_beveled([(352.0, 66.0), (372.0, 66.0), (377.0, 76.0), (377.0, 196.0), (372.0, 200.0), (352.0, 200.0)],
                          -21, 21, 3.0, M.RUBBER, steps=1),                                  # 床尾板
        extrude_x_beveled([(354.0, 199.0), (366.0, 199.0), (366.0, 207.4), (356.0, 207.4)], -8, 8, 1.5,
                          STEEL_BLACK, steps=1),                                             # 肩当て
    ]


# ---------------------------------------------------------------- 銃身まわり
def barrel(l=L):
    b = l.bore_y
    bore = 5.56 / 2
    return [
        lathe(0, b, [(l.barrel_end_z, bore), (l.barrel_end_z, 9.0), (-420.0, 9.0), (-420.0, 11.0), (l.breech_z, 11.0)],
              ar15_mesh.N_MID, M.STEEL, cap0=False),
        lathe(0, b, [(l.muzzle_z, bore), (l.muzzle_z + 25, bore)], ar15_mesh.N_SMALL, M.BORE, cap0=False),
    ]


def flash_hider(l=L):
    """スリット入りのフラッシュハイダー（先端は穴あきの輪）。"""
    b, z0, z1 = l.bore_y, l.muzzle_z, l.barrel_end_z
    out = [
        lathe(0, b, [(z1 - 14, 10.5), (z1, 10.0)], ar15_mesh.N_MID, STEEL_BLACK),
        lathe(0, b, [(z0 + 6, 4), (z0, 4), (z0, 10.5), (z0 + 6, 10.5)], ar15_mesh.N_MID, STEEL_BLACK, False, False),
        lathe(0, b, [(z0 + 6, 6.5), (z1 - 14, 6.5)], ar15_mesh.N_MID, M.BORE),
    ]
    for k in range(6):   # スリットの間の桟
        a = math.radians(30 + 60 * k)
        cx, cy = 8.5 * math.cos(a), b + 8.5 * math.sin(a)
        out += rotated([extrude_x([(z0 + 6, cy - 2), (z1 - 14, cy - 2), (z1 - 14, cy + 2), (z0 + 6, cy + 2)],
                                  cx - 2, cx + 2, STEEL_BLACK)], "z", 0, (0, 0, 0))
    return out


def front_sight(l=L):
    """フロントサイト: 銃身を抱く台から塔が立ち、上で左右の耳（フード）がポストを守る。"""
    b, (z1, z0), sy = l.bore_y, l.fs_z, l.sight_y
    tower = [(z1, b + 6), (z0, b + 6), (z0 + 3, b + 40), (z0 + 6, b + 44), (z1 - 6, b + 44), (z1 - 2, b + 40)]
    ear = [(z1 - 4, b + 40), (z0 + 4, b + 40), (z0 + 6, l.fs_top - 3), (z0 + 9, l.fs_top), (z1 - 9, l.fs_top),
           (z1 - 6, l.fs_top - 3)]
    return [
        lathe(0, b, [(z0, 14), (z1, 14)], ar15_mesh.N_MID, STEEL_BLACK),
        extrude_x_beveled(tower, -6, 6, 1.0, STEEL_BLACK, steps=1),
        extrude_x_beveled(ear, 3.5, 6.5, 0.8, STEEL_BLACK, steps=1),
        extrude_x_beveled(ear, -6.5, -3.5, 0.8, STEEL_BLACK, steps=1),
    ]


def front_sight_post(l=L):
    zc = sum(l.fs_z) / 2
    return [box(-1, l.bore_y + 40, zc - 1, 1, l.sight_y, zc + 1, STEEL_BLACK)]


def gas_system(l=L):
    """銃身下のガスシリンダーと、銃身とつなぐガスブロック、前端のレギュレーター。"""
    b, gy = l.bore_y, l.gas_y
    return [
        lathe(0, gy, [(l.gas_front_z, 13), (l.hg_front_z + 10, 13)], ar15_mesh.N_MID, STEEL_BLACK),
        lathe(0, gy, [(l.gas_front_z - 10, 17), (l.gas_front_z, 17)], ar15_mesh.N_MID, STEEL_BLACK),
        box(-10, gy, -418, 10, b, -395, STEEL_BLACK),
        box(-15, gy - 20, -392, 15, gy + 12, -372, STEEL_BLACK),          # 二脚の取付け
    ]


def handguard(l=L):
    """ハンドガード（樹脂、ガスシリンダーと銃身の下半分を覆う）。前端は丸い。"""
    f, r, t, bt = l.hg_front_z, l.hg_rear_z, l.hg_top, l.hg_bottom
    side = [(r, bt), (f + 26, bt), (f + 8, bt + 8), (f, bt + 24), (f, t - 14), (f + 6, t - 4), (f + 18, t), (r, t)]
    out = [extrude_x_beveled(side, -l.hg_half, l.hg_half, 4.0, M.POLYMER, steps=ar15_mesh.BEVEL_STEPS)]
    for y in (118.0, 140.0, 158.0):     # 側面の横溝の間の帯（写真の 3 本の筋）
        for s in (1, -1):
            out.append(box(s * l.hg_half, y, f + 30, s * (l.hg_half + 1.2), y + 4, r - 20, M.POLYMER))
    return out


def rail_handguard(l=L):
    """銃身の上のレール台（ヒートシールドを兼ねる）とレール。"""
    zr, zf, y0, y1 = l.shield
    return [
        box(-14, y0, zf, 14, y1, zr, M.RECEIVER),
        box(-8, y1, zf + 2, 8, y1 + 3, zr - 2, M.RAIL),
        box(-RAIL_W / 2, y1 + 3, zf + 2, RAIL_W / 2, y1 + 7.6, zr - 2, M.RAIL),
    ]


def carry_handle(l=L):
    """キャリングハンドル（たたんだ状態: 握りが銃身の上で前を向く）。"""
    pz, py = l.handle_pivot
    return [
        box(-9, l.hg_top, pz - 6, 9, py + 4, pz + 6, STEEL_BLACK),        # 銃身の台
        box(-6, py, pz - 18, 6, py + 12, pz + 2, STEEL_BLACK),            # 腕
        lathe(0, py + 16, [(pz - 88, 9), (pz - 86, 11), (pz - 20, 11), (pz - 18, 9)], ar15_mesh.N_MID, M.POLYMER),
    ]


def bipod_leg(l=L, side=1):
    """二脚の片脚（たたんだ状態: 後ろへ倒れ、ハンドガードの下に沿う）。side=+1 左 / -1 右。"""
    pz, py = l.bipod_pivot
    x = side * 9
    leg = [lathe(x, py, [(pz, 6), (pz + l.bipod_len - 20, 6)], ar15_mesh.N_SMALL, STEEL_BLACK)]
    return rotated(leg, "x", l.bipod_fold_deg, (0, py, pz))


def bipod_foot(l=L, side=1):
    pz, py = l.bipod_pivot
    x = side * 9
    end = pz + l.bipod_len
    foot = [lathe(x, py, [(end - 30, 4.5), (end - 4, 4.5)], ar15_mesh.N_SMALL, STEEL_BLACK),
            extrude_x([(end - 4, py - 3), (end, py - 3), (end, py + 9), (end - 4, py + 9)], x - 6, x + 6, STEEL_BLACK)]
    return rotated(foot, "x", l.bipod_fold_deg, (0, py, pz))


# ---------------------------------------------------------------- 給弾
def stanag_mag(l=L):
    """STANAG 30 発弾倉（M4A1 と同じ形）を、弾倉口から左下へ 45° 傾けて差す。"""
    px, py = l.mag_pivot

    class _ML(ar15_parts.Layout):
        bore_y = py + 14.0
        mag_center_z = l.mag_center_z
    parts = [p for p in ar15_mesh.magazine_stanag(_ML()) if isinstance(p, MeshPart)]
    parts = [MeshPart([(v[0] + px, v[1], v[2]) for v in p.verts], p.faces, p.mat, p.normals, p.charts,
                      p.chart_uv, p.chart_edge) for p in parts]
    return rotated(parts, "z", l.mag_tilt, (px, py, l.mag_center_z))


def ammo_box(l=L):
    """200 発ボックス（樹脂のふた＋布の袋。作者提供の単体写真）。受け部の左下に掛ける。"""
    z0, z1, y0, y1 = l.box
    x0, x1 = l.box_x
    lid = 22.0
    body = [(z1, y0), (z0, y0), (z0, y1 - lid), (z1, y1 - lid)]
    top = [(z1, y1 - lid), (z0, y1 - lid), (z0 + 3, y1), (z1 - 3, y1)]
    return [
        extrude_x_beveled(body, x0, x1, 4.0, M.CANVAS, steps=2),
        extrude_x_beveled(top, x0 - 1, x1 + 1, 2.0, M.BOX_LID, steps=1),
        box(x1 - 0.5, y1 - 40, (z0 + z1) / 2 - 2, x1 + 1.5, y0 + 8, (z0 + z1) / 2 + 2, M.BOX_LID),   # ファスナー（左面。側面写真で見える面）
    ]


def belt(l=L, n=8):
    """ボックスから左側のフィードトレイへ上がる弾帯（弾は前向きに縦に並ぶ）。"""
    out = []
    x = l.rcv_half + 6
    for i in range(n):
        y = l.box[3] + 6 + i * 9.0
        case, bullet = ar15_parts.cartridge_556(z_tip=-119.4, y=y)
        out += [c.moved(x, 0, 0) for c in case + bullet]
        out.append(box(x - 5.5, y - 4.5, -100, x + 5.5, y + 4.5, -92, STEEL_BLACK))   # リンク
    return out


# ---------------------------------------------------------------- 組み立て
def build(feed="belt"):
    l = L
    b = l.bore_y
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name, items):
        items = [c.scaled(K) for c in items]
        if part_name:
            parts[part_name] = items
        return m.bone(bone, parent, tuple(v * K for v in pivot_mm), items)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "receiver", receiver() + magwell())
    add("feed_cover", "receiver", (0, l.cover_top, l.rcv_rear_z - 6), "feed_cover", feed_cover())
    add("rail_top", "feed_cover", (0, l.cover_top + l.rail_h, l.rail_rear_z), "rail_top", rail_top())
    add("rear_sight", "feed_cover", (0, l.cover_top, l.rear_sight_z), "rear_sight", rear_sight())
    add("pistol_grip", "receiver", (0, 108, 40), "pistol_grip", pistol_grip())
    add("lower_receiver", "receiver", (0, 108, 0), "trigger_guard", trigger_guard())
    add("trigger", "root", (0, 108, 0), "trigger", trigger())
    add("stock", "root", (0, b, l.rcv_rear_z), "stock", stock())
    add("handguard", "root", (0, b, l.hg_rear_z), "handguard", handguard() + gas_system())
    add("rail_handguard", "handguard", (0, l.shield[3], l.shield[0]), "rail_handguard", rail_handguard())
    pz, py = l.bipod_pivot
    for name, s in (("bipod_leg_l", 1), ("bipod_leg_r", -1)):
        add(name, "handguard", (s * 9, py, pz), f"{name}", bipod_leg(side=s))
        a = math.radians(l.bipod_fold_deg)          # 足の付け根（たたんだ脚の上で、回転後の位置）
        d = l.bipod_len - 20
        add(name.replace("leg", "foot"), name, (s * 9, py - d * math.sin(a), pz + d * math.cos(a)), None,
            bipod_foot(side=s))
    add("barrel", "root", (0, b, l.breech_z), "barrel", barrel())
    add("chamber", "barrel", (0, b, l.breech_z), None, [])
    add("front_sight_base", "barrel", (0, b, l.fs_z[0]), "front_sight", front_sight())
    add("front_sight_post", "front_sight_base", (0, l.sight_y, sum(l.fs_z) / 2), None, front_sight_post())
    add("carry_handle", "barrel", (0, l.handle_pivot[1], l.handle_pivot[0]), "carry_handle", carry_handle())
    add("muzzle", "root", (0, b, l.barrel_end_z), "flash_hider", flash_hider())
    add("bolt", "root", (0, b, l.breech_z + 40), None, [])

    if feed == "belt":
        add("magazin", "root", (sum(l.box_x) / 2, l.box[3], sum(l.box[:2]) / 2), "ammo_box", ammo_box())
        add("mag_ammo", "magazin", (l.rcv_half + 6, l.box[3], -100), "belt", belt())
    else:
        add("magazin", "root", (l.mag_pivot[0], l.mag_pivot[1], l.mag_center_z), "magazine_stanag", stanag_mag())
        add("mag_ammo", "magazin", (l.mag_pivot[0], l.mag_pivot[1], l.mag_center_z), None, [])

    tip = l.breech_z - 57.4                     # 薬室内の実包（排莢クリップの起点）
    case, bullet = ar15_parts.cartridge_556(z_tip=tip, y=b)
    add("ammo", "root", (0, b, tip + 35), None, case)
    add("bullet", "ammo", (0, b, tip + 6), None, bullet)

    from shapely.geometry import Polygon
    c = Polygon(GRIP).centroid
    add_locators(m, muzzle=(0, b * K, l.muzzle_z * K), sight_line_y=l.sight_y * K,
                 rear_sight_z=l.rear_sight_z * K, grip_center=(0, c.y * K, c.x * K))
    return m, parts
