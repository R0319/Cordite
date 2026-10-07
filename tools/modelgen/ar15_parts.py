"""
AR-15 系のパーツライブラリ（単位 mm）。

各関数は「その部品だけのキューブ一覧」を返す。座標はすべて銃全体の共通座標（mm）:
  X=0 左右対称面（-X が右側面＝エジェクションポート側） / Y=0 グリップ底面 / Z=0 トリガー / 銃口 -Z
組み立て側（guns/*.py）が部品をボーンへ割り当て、mm→px（÷MM_PER_PX）へ変換する。

寸法は公開されている実銃寸法（M4A1: 全長 838mm〔ストック伸長〕・銃身 14.5in=368mm・
A2 フラッシュハイダー 57mm・サイト高 2.6in=66mm・STANAG 弾倉 約 180mm 等）を基にし、
公表値が無い部分（レシーバー各部の厚み等）は外観写真比の概算。
"""
from core import box, cbox, round_rod
import materials as M

MM_PER_PX = 24.0              # 07-model-assets.md「1px ≒ 24mm」
SLOT_MM = 0.5 * MM_PER_PX     # レール1スロット = 0.5px（規約）
RAIL_W_MM = 1.0 * MM_PER_PX   # レール幅 = 1.0px（規約）


class Layout:
    """部品どうしの取り合い寸法。銃ごとにここだけ変えれば同系統の別銃（M16/HK416 等）に流用できる。"""
    bore_y = 140.0          # ボア軸高さ（グリップ底面基準）
    bolt_face_z = -110.0    # ボルトフェイス（銃身の根元）
    barrel_len = 368.0      # 14.5in
    upper_front_z = -155.0
    upper_rear_z = 30.0
    upper_top = 17.0        # ボア軸からの上面高さ
    upper_bottom = -20.0    # 上下レシーバー分割線
    rail_slots = 14
    rail_h = 9.0
    sight_h = 66.0          # ボア軸→照準線（AR 系 2.6in）
    gas_z = -346.0          # フロントサイトベース後端（カービン長ガス）
    handguard_front_z = -340.0
    handguard_rear_z = -172.0
    lower_bottom = -58.0    # トリガーメカ部の下面（ボア軸基準）
    buffer_end_z = 245.0
    butt_z = 304.0

    @property
    def muzzle_z(self):     # 銃身先端
        return self.bolt_face_z - self.barrel_len

    @property
    def rail_top_y(self):
        return self.bore_y + self.upper_top + self.rail_h


L = Layout()


# ---------------------------------------------------------------- 上部
def upper_receiver(l=L):
    b = l.bore_y
    return [
        box(-14, b + l.upper_bottom, l.upper_front_z, 14, b + l.upper_top, l.upper_rear_z, M.RECEIVER),
        # 銃身ナット部（上部レシーバー前端のリング）
        *round_rod(0, b, l.upper_front_z - 15, l.upper_front_z, 32, M.STEEL_DARK),
        # エジェクションポートカバー（右側面）
        box(-14.8, b - 8, -100, -14, b + 6, -35, M.STEEL_DARK),
        # フォワードアシスト（右後方）＋ボタン
        box(-21, b - 1, -12, -13, b + 13, 16, M.RECEIVER),
        box(-24, b + 1, 8, -19, b + 11, 20, M.STEEL_DARK),
        # ブラスディフレクター
        box(-19, b + 2, -36, -13, b + 14, -24, M.RECEIVER),
    ]


def rail(l=L, z_rear=None):
    """ピカティニーレール。長さはスロット数で決まる（規約: 0.5px/スロット・幅 1.0px）。刻みはテクスチャ縞。"""
    z_rear = l.upper_rear_z - 2 if z_rear is None else z_rear
    z_front = z_rear - l.rail_slots * SLOT_MM
    y0 = l.bore_y + l.upper_top
    return [
        box(-8, y0, z_front, 8, y0 + 4, z_rear, M.RAIL),                                 # 首
        box(-RAIL_W_MM / 2, y0 + 4, z_front, RAIL_W_MM / 2, y0 + l.rail_h, z_rear, M.RAIL),  # 天面
    ]


def charging_handle(l=L):
    b = l.bore_y
    z0 = l.upper_rear_z
    return [
        box(-21, b + 8, z0, 21, b + 16, z0 + 9, M.STEEL_DARK),     # T字ハンドル
        box(13, b + 8, z0 + 2, 25, b + 16, z0 + 14, M.STEEL_DARK),  # ラッチ（左）
    ]


def bolt_carrier(l=L):
    """エジェクションポート奥に見えるボルトキャリア（射撃アニメで前後させる部品）。"""
    b = l.bore_y
    return [box(-13.6, b - 7, -98, -6, b + 5, -37, M.STEEL)]


def rear_sight(l=L, z=0.0):
    """フリップアップ式リアサイト（アパーチャー中心＝照準線）。z はクランプ前端。"""
    rt, sl = l.rail_top_y, l.bore_y + l.sight_h
    return [
        box(-13, rt, z, 13, rt + 8, z + 26, M.STEEL_DARK),            # レールクランプ
        box(-10, rt + 8, z + 6, 10, sl - 16, z + 18, M.STEEL_DARK),   # 支柱
        box(7, sl - 16, z + 8, 10, sl + 10, z + 16, M.STEEL_DARK),    # 保護耳（左）
        box(-10, sl - 16, z + 8, -7, sl + 10, z + 16, M.STEEL_DARK),  # 保護耳（右）
        # アパーチャー板（中央に 4mm の穴）
        box(-7, sl - 16, z + 11, 7, sl - 2, z + 13, M.STEEL_DARK),
        box(-7, sl + 2, z + 11, 7, sl + 5, z + 13, M.STEEL_DARK),
        box(2, sl - 2, z + 11, 7, sl + 2, z + 13, M.STEEL_DARK),
        box(-7, sl - 2, z + 11, -2, sl + 2, z + 13, M.STEEL_DARK),
        box(10, rt + 10, z + 8, 16, rt + 18, z + 16, M.STEEL_DARK),   # 調整ノブ
    ]


# ---------------------------------------------------------------- 銃身まわり
def barrel(l=L):
    b = l.bore_y
    return [
        *round_rod(0, b, l.gas_z, l.bolt_face_z, 19, M.STEEL),        # ハンドガード内（太い）
        *round_rod(0, b, l.muzzle_z, l.gas_z, 15.7, M.STEEL),         # ガスブロック前（細い）
    ]


def barrel_extension(l=L):
    return round_rod(0, l.bore_y, l.bolt_face_z - 40, l.bolt_face_z, 26, M.STEEL_DARK)


def gas_block(l=L):
    """フロントサイトベースの銃身クランプ部（＝ガスブロック）。"""
    return round_rod(0, l.bore_y, l.gas_z - 26, l.gas_z, 30, M.STEEL_DARK)


def front_sight_base(l=L):
    b, z = l.bore_y, l.gas_z
    sl = b + l.sight_h
    return [
        box(-8, b + 12, z - 25, 8, b + 28, z - 2, M.STEEL_DARK),     # 塔（下段）
        box(-6, b + 28, z - 21, 6, sl - 22, z - 8, M.STEEL_DARK),    # 塔（上段）
        box(8, sl - 30, z - 20, 11, sl - 2, z - 9, M.STEEL_DARK),    # 保護耳（左）
        box(-11, sl - 30, z - 20, -8, sl - 2, z - 9, M.STEEL_DARK),  # 保護耳（右）
        box(-11, sl - 32, z - 20, 11, sl - 26, z - 9, M.STEEL_DARK), # 耳の連結
        box(-4, b - 30, z - 24, 4, b - 14, z - 11, M.STEEL_DARK),    # 着剣ラグ
    ]


def front_sight_post(l=L):
    b, z = l.bore_y, l.gas_z
    sl = b + l.sight_h
    return [
        box(-3, sl - 26, z - 17, 3, sl - 20, z - 12, M.STEEL_DARK),   # 台座
        box(-1.6, sl - 20, z - 16, 1.6, sl, z - 13, M.STEEL_DARK),    # ポスト（先端＝照準線）
    ]


def handguard(l=L):
    b = l.bore_y
    return [
        *round_rod(0, b, l.handguard_front_z, l.handguard_rear_z, 52, M.HANDGUARD),
        *round_rod(0, b, l.handguard_rear_z, l.handguard_rear_z + 12, 60, M.STEEL_DARK),     # デルタリング
        *round_rod(0, b, l.handguard_front_z - 6, l.handguard_front_z, 46, M.STEEL_DARK),   # ハンドガードキャップ
    ]


def flash_hider_a2(l=L):
    """A2 バードケージ。下面は閉じ（バードケージ下の板）、他はスリット＝棒で表す。"""
    b, z1 = l.bore_y, l.muzzle_z
    z0 = z1 - 57
    out = [
        *round_rod(0, b, z1 - 20, z1, 22, M.STEEL_DARK),      # 根元
        *round_rod(0, b, z0, z0 + 7, 22, M.STEEL_DARK),       # 先端リング
        cbox(0, b, z0 + 7, z1 - 20, 12, 12, M.BORE),          # 内側（暗）
        box(-6, b - 11, z0 + 7, 6, b - 7, z1 - 20, M.STEEL_DARK),   # 下面の板
    ]
    for ang in (-120, -60, 0, 60, 120):                    # スリット間の棒（銃軸まわりに回転配置）
        out.append(box(-2, b + 7, z0 + 7, 2, b + 11, z1 - 20, M.STEEL_DARK,
                       rotation=(0, 0, ang), pivot=(0, b, (z0 + z1) / 2)))
    return out


# ---------------------------------------------------------------- 下部
def lower_receiver(l=L):
    return lower_body(l) + trigger_guard(l)


def lower_body(l=L):
    b = l.bore_y
    lb = b + l.lower_bottom
    return [
        box(-15, b - 95, -122, 15, b + l.upper_bottom, -45, M.RECEIVER),     # マグウェル
        box(-16.5, b - 95, -124, 16.5, b - 85, -43, M.RECEIVER),             # マグウェル下端のフレア
        box(-12, lb, -45, 12, b + l.upper_bottom, 62, M.RECEIVER),           # トリガーメカ部
        box(-13, b + l.upper_bottom, l.upper_rear_z, 13, b + 14, 62, M.RECEIVER),  # バッファチューブ受け
        box(-15.8, b - 18, -115, 15.8, b - 12, -109, M.STEEL_DARK),          # 前ピン
        box(-15, b - 18, 42, 15, b - 12, 48, M.STEEL_DARK),                  # 後ピン
        box(-16, b - 45, -42, -12, b - 37, -34, M.STEEL_DARK),               # マガジンキャッチ（右）
        box(12, b - 30, -48, 15, b - 14, -38, M.STEEL_DARK),                 # ボルトキャッチ（左）
        box(12, b - 38, 18, 14.5, b - 32, 38, M.STEEL_DARK),                 # セレクター（左）
    ]


# ---- 下回りの側面形状（z, y）。メッシュ版はこの輪郭をそのまま押し出し、キューブ版は箱で近似する
def guard_outline(l=L):
    """トリガーガード: 前端はマグウェル後面のピン、後端は上へ曲がってグリップ前面に入る。"""
    lb = l.bore_y + l.lower_bottom
    return [(-45, lb - 18), (-38, lb - 18), (-38, lb - 22), (14, lb - 22), (19, lb - 19), (21, lb - 12),
            (27, lb - 12), (25, lb - 22), (20, lb - 27), (-45, lb - 27)]


def trigger_outline(l=L):
    """トリガー: 上端はレシーバー内、下へ行くほど前へ反り、先端が前を向く（指を掛ける前面が凹む）。"""
    lb = l.bore_y + l.lower_bottom
    back = [(4, lb + 4), (4, lb - 2), (3.3, lb - 8), (1.3, lb - 13), (-1.5, lb - 17.5)]
    tip = [(-3.5, lb - 18.2)]
    front = [(-5.3, lb - 16.2), (-3.5, lb - 13.2), (-2.2, lb - 8), (-2, lb - 2), (-2, lb + 4)]
    return back + tip + front


def grip_outline(l=L):
    """A2 グリップ: 上面はレシーバー下面と平行（水平）、前面に指掛けの膨らみ1つ、後ろ上端に張り出し。"""
    lb = l.bore_y + l.lower_bottom
    return [(16, lb), (64, lb), (66, lb - 5), (65, lb - 14), (70, lb - 33), (76, lb - 53), (82, lb - 73),
            (83, lb - 79), (80, lb - 82), (52, lb - 82), (46, lb - 80), (41, lb - 68), (37.5, lb - 57),
            (33, lb - 49), (29, lb - 43), (29, lb - 38), (31.5, lb - 33), (28, lb - 24), (22, lb - 12)]


def trigger_guard(l=L):
    lb = l.bore_y + l.lower_bottom
    return [
        box(-6, lb - 27, -45, 6, lb - 18, -38, M.RECEIVER),     # 前端
        box(-6, lb - 27, -38, 6, lb - 22, 20, M.RECEIVER),      # 下辺
        box(-6, lb - 27, 19, 6, lb - 12, 26, M.RECEIVER),       # 後端（グリップへ）
    ]


def trigger(l=L):
    lb = l.bore_y + l.lower_bottom
    return [
        box(-3, lb - 6, -2, 3, lb + 4, 4, M.STEEL_DARK),
        box(-3, lb - 12, -3.5, 3, lb - 6, 2.5, M.STEEL_DARK),
        box(-3, lb - 18, -5.5, 3, lb - 12, 0, M.STEEL_DARK),    # 先端は前へ
    ]


GRIP_ANGLE = 22.0


def grip_frame(l=L):
    """A2 グリップの回転基準（上端前縁）と角度。"""
    return (0.0, l.bore_y + l.lower_bottom, 14.0), (GRIP_ANGLE, 0.0, 0.0)


def pistol_grip(l=L):
    (px, py, pz), rot = grip_frame(l)
    top = py
    return [
        box(-14, top - 92, pz, 14, top, pz + 46, M.POLYMER, rotation=rot, pivot=(px, py, pz)),
        box(-13, top - 52, pz - 7, 13, top - 38, pz, M.POLYMER, rotation=rot, pivot=(px, py, pz)),    # 指掛け
        box(-12, top - 8, 50, 12, top, 66, M.POLYMER),     # 上端の張り出し（傾けない＝レシーバー下面に沿う）
    ]


def buffer_tube(l=L):
    c = l.bore_y - 4
    return [
        *round_rod(0, c, 62, l.buffer_end_z, 30, M.RECEIVER),
        *round_rod(0, c, 62, 72, 35, M.STEEL_DARK),                       # キャッスルナット
        box(-16, c - 16, 63, 16, c + 16, 67, M.STEEL_DARK),               # エンドプレート
    ]


def stock_m4(l=L):
    """M4 6 ポジションストック（最伸長位置）。下側の斜面は回転板＋段で埋める。"""
    b = l.bore_y
    z0, z1 = 180.0, l.butt_z - 6
    slope = 39.6  # 下縁 (z0, b-22) → (z0+70, b-80)
    return [
        box(-17, b - 22, z0, 17, b + 16, z1, M.POLYMER),                       # チューブ外套
        box(-16, b - 80, 250, 16, b - 22, z1, M.POLYMER),                      # 後部
        box(-15.7, b - 51, 215, 15.7, b - 22, 250, M.POLYMER),                     # 斜面の内側を段で埋める
        box(-15.7, b - 34, 195, 15.7, b - 22, 215, M.POLYMER),
        box(-15.4, b - 22, z0, 15.4, b + 12, z0 + 91, M.POLYMER,
            rotation=(-slope, 0, 0), pivot=(0, b - 22, z0)),                   # 下側の斜面（板の下縁＝斜面）
        box(-5, b - 30, z0 + 5, 5, b - 22, z0 + 50, M.STEEL_DARK),             # 調整レバー
        box(-19, b - 85, z1, 19, b + 20, l.butt_z, M.RUBBER),                  # バットプレート
    ]


MAG_ANGLE = 14.0


def magazine_stanag(l=L):
    """STANAG 30 発弾倉。上半分は直線、下半分を前方へ曲げる（実物の湾曲を 2 分割で近似）。"""
    b = l.bore_y
    top, split = b - 24, b - 125
    piv = (0, split, -53)
    rot = (-MAG_ANGLE, 0, 0)
    return [
        box(-11, split, -117, 11, top, -53, M.MAG),
        box(-11, split - 80, -117, 11, split, -53, M.MAG, rotation=rot, pivot=piv),
        box(-13, split - 86, -121, 13, split - 78, -49, M.STEEL_DARK, rotation=rot, pivot=piv),  # フロアプレート
        box(-11.6, split + 5, -110, 11.6, split + 65, -60, M.MAG),      # 側面のリブ（直線部）
    ]


def cartridge_556(z_tip, y, case_mat=M.BRASS, bullet_mat=M.COPPER):
    """5.56x45 実包（弾頭が -Z）。全長 57.4mm、薬莢径 9.6mm。"""
    return (
        [box(-4.8, y - 4.8, z_tip + 12.7, 4.8, y + 4.8, z_tip + 57.4, case_mat)],
        [box(-2.85, y - 2.85, z_tip, 2.85, y + 2.85, z_tip + 12.7, bullet_mat)],
    )
