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
    bore_y = 155.4          # ボア軸高さ（グリップ底面基準。A2 グリップはレシーバー下面から約101mm下まである）
    bolt_face_z = -95.0     # ボルトフェイス（銃身の根元）。上部レシーバー前端から約30mm奥（バレルエクステンション分）
    barrel_len = 368.0      # 14.5in
    upper_front_z = -125.0  # 上部レシーバー前端（写真から）
    upper_rear_z = 70.0     # 上部レシーバー後端（写真から。下部の後端より少し前）
    upper_top = 17.0        # ボア軸からの上面高さ
    upper_bottom = -20.0    # 上下レシーバー分割線
    rail_slots = 16         # 写真のレール長 約192mm ÷ 12mm（規約の 0.5px/スロット）
    rail_h = 9.0
    sight_h = 66.0          # ボア軸→照準線（AR 系 2.6in）
    gas_z = -346.0          # フロントサイトベース後端（カービン長ガス）
    handguard_front_z = -338.0
    handguard_rear_z = -152.0   # 銃身ナット（上部レシーバー前端の 15mm 前）の前
    magwell_front_z = -114.0    # マグウェル前面（写真から）
    magwell_rear_z = -42.0      # マグウェル後面＝ガードの前の耳（写真から）
    mag_center_z = -78.0        # 弾倉の前後中心
    lower_bottom = -54.4    # トリガーメカ部の下面（ボア軸基準）。写真のレール上面→この面が 80.4mm になるよう合わせた
    lower_rear_z = 88.0     # 下部レシーバーの後端（バッファチューブの付け根。写真から）
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
        box(-14.8, b - 8, l.bolt_face_z + 5, -14, b + 6, l.bolt_face_z + 70, M.STEEL_DARK),
        # フォワードアシスト（右後方）＋ボタン
        box(-21, b - 1, l.bolt_face_z + 90, -13, b + 13, l.bolt_face_z + 125, M.RECEIVER),
        box(-24, b + 1, l.bolt_face_z + 118, -19, b + 11, l.bolt_face_z + 130, M.STEEL_DARK),
        # ブラスディフレクター
        box(-19, b + 2, l.bolt_face_z + 73, -13, b + 14, l.bolt_face_z + 85, M.RECEIVER),
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
    return [box(-13.6, b - 7, l.bolt_face_z + 7, -6, b + 5, l.bolt_face_z + 68, M.STEEL)]


def rear_sight(l=L, z=None):
    """フリップアップ式リアサイト（アパーチャー中心＝照準線）。z はクランプ前端。"""
    rt, sl = l.rail_top_y, l.bore_y + l.sight_h
    z = l.upper_rear_z - 30 if z is None else z
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
# 下回り（レシーバー後部の下面・トリガーガード・トリガー・グリップ）の側面形状は、作者提供の写真
# （M4 ロアレシーバー＋Engage 系グリップの真横写真）から抽出した輪郭を使う。
#   縮尺: 上部レールの刻み（MIL-STD-1913、10mm 間隔）が写真上 25px → 2.5px/mm
#   基準: 写真上 x=265 がトリガー（Z=0）、y=232 がトリガーメカ部のレシーバー下面（lb）
#   写真は銃口が +x、下が +y。Z = (265 - x) / 2.5、Y = lb - (y - 232) / 2.5
REF_PX_PER_MM = 2.5
REF_TRIGGER_X = 265.0
REF_LOWER_Y = 232.0

# A2 グリップ（M4A1 標準）の輪郭（z, レシーバー下面 lb からの y）。上面と前面上端・後ろ上端の張り出しの上縁は
# 写真から取ったレシーバー側の取付面に合わせ、本体は A2 の特徴で描く（A2 の真横写真による検証はまだ）:
# 小さな張り出し、ゆるく膨らむ背面、軸にほぼ直角な底、前面中ほどの指掛けの膨らみ1つ。通過点を曲線で結ぶ。
A2_GRIP_CURVE = [
    (51.2, 0.0),                                  # 上面の後端（ここからレシーバー下面が反り上がる）
    (55.0, 5.5), (59.2, 10.0),                    # 後ろ上端の小さな張り出し: 上縁はレシーバー後部の下面（写真）に沿う
    (61.5, 9.5), (62.5, 5.5), (61.5, 0.5),        # 張り出しの先端（丸める）
    (61.2, -4.0), (63.0, -10.0),                  # 張り出しの下（小さなくびれ）
    (69.0, -22.0), (77.0, -38.0), (84.0, -52.0),  # 背面: 軸 25°（AR 標準のグリップ角）、わずかに外へ膨らむ
    (90.5, -66.0), (96.0, -80.0),
    (99.8, -87.0), (99.5, -91.0), (96.0, -93.5),  # 背面→底の丸い角
    (78.0, -97.0), (57.5, -101.0),                # 底（前がやや低い）
    (54.0, -99.0), (52.5, -94.0),                 # 底→前面の丸い角
    (48.2, -84.0), (43.2, -72.0), (37.5, -60.0),  # 前面下部（薬指・小指。わずかに凹む）
    (30.5, -54.0), (26.8, -49.0), (28.0, -44.0),  # 指掛けの膨らみ（中指と薬指の間）
    (27.3, -38.0),                                # 中指の凹み
    (23.5, -32.0), (21.6, -24.0), (21.0, -12.0),  # 前面上部（トリガーガードの後ろの耳に沿ってほぼ垂直）
    (20.8, 0.0),                                  # 上面の前端
]

REF_GRIP = [  # 参考: 写真の Engage 系グリップの輪郭（写真の画素座標）。grip_outline_engage で使う
    (213, 232), (137, 232),                                     # 上面（レシーバー下面に接する）
    (117, 207), (95, 193), (73, 185), (55, 190), (52, 196),     # 後ろ上端の張り出し（上縁はレシーバー後部の下面に沿う）
    (73, 197), (89, 210), (99, 220), (104, 230), (107, 240),    # 張り出しの下（手の水かきが当たる凹み）
    (109, 250), (108, 260), (105, 270), (100, 280), (95, 290),
    (87, 300), (81, 310), (74, 320), (67, 330), (60, 340),      # 背面（滑り止めの刻みは輪郭から除いて平均化）
    (54, 352), (49, 362), (43, 372), (39, 380), (33, 392),
    (28, 404), (23, 416), (18, 428), (15, 440), (17, 446),
    (30, 453), (50, 463), (70, 472), (90, 480), (110, 488), (120, 491),   # 底（前下がり）
    (129, 488), (136, 476), (136, 460), (138, 452), (142, 444),          # 底→前面の角
    (148, 436), (159, 428), (160, 416), (160, 404), (163, 396),          # 前面下部（小指）
    (167, 388), (173, 380), (183, 372), (185, 368),                      # 指掛けの膨らみ（薬指の上）
    (184, 360), (184, 352), (186, 344), (188, 340), (192, 330),          # 前面上部（中指・薬指）
    (198, 320), (206, 315), (213, 300),                                  # 前面の上端（レシーバー後ろの耳に接する）
]
REF_LOWER_REAR = [  # レシーバー後部の下面（グリップ上面の後端から、張り出しの上縁に沿ってバッファチューブ受けまで）
    (137, 232), (117, 207), (95, 193), (73, 185), (45, 182),
]
REF_OPENING_REAR = [  # トリガーガード内側の開口の後ろ側（上→下）
    (253, 238), (247, 242), (243, 246), (240, 250), (238, 254), (237, 258), (236, 262), (235, 266),
    (235, 270), (236, 274), (237, 278), (239, 282), (241, 286), (244, 290), (248, 294), (253, 298), (255, 302),
]
REF_OPENING_FRONT = [  # 開口の前側（上→下）
    (341, 238), (347, 242), (351, 246), (354, 250), (356, 254), (357, 258), (358, 262), (359, 266),
    (359, 270), (358, 274), (357, 278), (355, 282), (353, 286), (350, 290), (347, 294), (345, 298), (342, 302),
]
REF_GUARD_BOTTOM_Y = 311     # ガード下辺の下面
REF_EAR_REAR_X = 213         # 後ろの耳の後端（＝グリップ前面）
REF_EAR_BOTTOM_Y = 315       # 後ろの耳の下端
REF_TRIGGER_REAR = [(266, 235), (264, 241), (262, 247), (261, 253), (260, 259), (260, 265), (261, 271),
                    (262, 277), (264, 283), (267, 289), (272, 295), (274, 298)]   # トリガー後面（上→下）
REF_TRIGGER_FRONT = [(286, 235), (279, 241), (274, 247), (271, 253), (269, 259), (268, 265), (268, 271),
                     (268, 277), (270, 283), (272, 289), (276, 295), (276, 298)]  # トリガー前面（指を掛ける面）


def ref_zy(l, pts):
    lb = l.bore_y + l.lower_bottom
    return [((REF_TRIGGER_X - x) / REF_PX_PER_MM, lb - (y - REF_LOWER_Y) / REF_PX_PER_MM) for x, y in pts]


def lower_receiver(l=L):
    return lower_body(l) + trigger_guard(l)


def lower_rear_outline(l=L):
    """レシーバー後部（トリガーメカ部の後ろ〜バッファチューブ受け）の側面形状。下面は後ろへ反り上がる。"""
    b = l.bore_y
    under = ref_zy(l, REF_LOWER_REAR)
    zr = under[-1][0]
    return under + [(zr, b + 14), (l.upper_rear_z, b + 14), (l.upper_rear_z, b + l.upper_bottom),
                    (under[0][0], b + l.upper_bottom)]


def lower_body(l=L):
    """キューブ版。メッシュ版は ar15_mesh.lower_body でレシーバー後部だけ輪郭の押し出しに置き換える。"""
    b = l.bore_y
    lb = b + l.lower_bottom
    zg = ref_zy(l, [REF_LOWER_REAR[0]])[0][0]    # グリップ上面の後端
    return lower_common(l) + [
        box(-12, lb, l.magwell_rear_z, 12, b + l.upper_bottom, zg, M.RECEIVER),             # トリガーメカ部
        box(-12.5, lb + 10, zg, 12.5, b + 14, l.lower_rear_z - 8, M.RECEIVER),           # 後部（下面の反り上がりを段で近似）
        box(-12.5, lb + 18, l.lower_rear_z - 8, 12.5, b + 14, l.lower_rear_z, M.RECEIVER),
        box(-12.5, b + l.upper_bottom, l.upper_rear_z, 12.5, b + 14, zg, M.RECEIVER),
    ]


def lower_common(l=L, magwell_fn=None):
    """マグウェルとピン・レバー類。magwell_fn でマグウェルの作り方（キューブ/メッシュ）を差し替える。"""
    b = l.bore_y
    return [
        *(magwell_fn or magwell)(l),
        box(-15.8, b - 18, l.magwell_front_z + 6, 15.8, b - 12, l.magwell_front_z + 12, M.STEEL_DARK),  # 前ピン
        box(-13.3, b - 18, 42, 13.3, b - 12, 48, M.STEEL_DARK),              # 後ピン
        box(-16, b - 45, -42, -12, b - 37, -34, M.STEEL_DARK),               # マガジンキャッチ（右）
        box(12, b - 30, -48, 15, b - 14, -38, M.STEEL_DARK),                 # ボルトキャッチ（左）
        box(12, b - 38, 18, 14.5, b - 32, 38, M.STEEL_DARK),                 # セレクター（左）
    ]


REF_MAGWELL_BOTTOM_REAR_Y = 307   # マグウェル下端（後ろ）。下端は前ほど高い斜めの切り口
REF_MAGWELL_BOTTOM_FRONT_Y = 275  # マグウェル下端（前）


def magwell_outline(l=L):
    lb = l.bore_y + l.lower_bottom
    yr = lb - (REF_MAGWELL_BOTTOM_REAR_Y - REF_LOWER_Y) / REF_PX_PER_MM
    yf = lb - (REF_MAGWELL_BOTTOM_FRONT_Y - REF_LOWER_Y) / REF_PX_PER_MM
    top = l.bore_y + l.upper_bottom
    return [(l.magwell_rear_z, top), (l.magwell_rear_z, yr), (l.magwell_front_z, yf), (l.magwell_front_z, top)]


def magwell(l=L):
    """キューブ版: 斜めの下端を 3 段で近似。"""
    (zr, top), (_, yr), (zf, yf), _ = magwell_outline(l)
    out = []
    for i in range(3):
        z0 = zr + (zf - zr) * i / 3
        z1 = zr + (zf - zr) * (i + 1) / 3
        y = yr + (yf - yr) * (i + 0.5) / 3
        out.append(box(-15, y, z0, 15, top, z1, M.RECEIVER))
    return out


# ---- 下回りの側面形状（z, y）。メッシュ版はこの輪郭をそのまま押し出し、キューブ版は箱で近似する
def ear_outlines(l=L):
    """トリガーガードの前後の耳（レシーバーの一部）。内側の縁がガード開口の輪郭。"""
    lb = l.bore_y + l.lower_bottom
    rear_in = ref_zy(l, REF_OPENING_REAR)
    front_in = ref_zy(l, REF_OPENING_FRONT)
    ear_z = (REF_TRIGGER_X - REF_EAR_REAR_X) / REF_PX_PER_MM
    ear_y = lb - (REF_EAR_BOTTOM_Y - REF_LOWER_Y) / REF_PX_PER_MM
    gy = lb - (REF_GUARD_BOTTOM_Y - REF_LOWER_Y) / REF_PX_PER_MM
    rear = [(rear_in[0][0], lb)] + rear_in + [(rear_in[-1][0] + 2, gy), (ear_z, ear_y), (ear_z, lb)]
    front = [(l.magwell_rear_z - 3, lb), (l.magwell_rear_z - 3, gy), (front_in[-1][0] - 2, gy)] + front_in[::-1] \
        + [(front_in[0][0], lb)]
    return rear, front


def guard_bar_outline(l=L):
    """ガードの下辺（薄い板）。両端は耳に埋まる。"""
    lb = l.bore_y + l.lower_bottom
    gy = lb - (REF_GUARD_BOTTOM_Y - REF_LOWER_Y) / REF_PX_PER_MM
    rear_z = ref_zy(l, REF_OPENING_REAR)[-1][0] + 2
    front_z = ref_zy(l, REF_OPENING_FRONT)[-1][0] - 2
    return [(rear_z, gy), (rear_z, gy + 3.2), (front_z, gy + 3.2), (front_z, gy)]


def trigger_outline(l=L):
    """トリガー: 前面（指を掛ける面）が凹み、先端が前を向く。写真の刃を 0.5mm ずつ太らせる（細すぎて見えないため）。"""
    lb = l.bore_y + l.lower_bottom
    rear = [(z + 0.5, y) for z, y in ref_zy(l, REF_TRIGGER_REAR)]
    front = [(z - 0.5, y) for z, y in ref_zy(l, REF_TRIGGER_FRONT)]
    return [(rear[0][0], lb + 4)] + rear + [(sum(p[0] for p in (rear[-1], front[-1])) / 2, rear[-1][1] - 1)] \
        + front[::-1] + [(front[0][0], lb + 4)]


def grip_outline(l=L, per_seg=3):
    """A2 グリップの側面形状。"""
    from core import smooth
    lb = l.bore_y + l.lower_bottom
    return [(z, lb + y) for z, y in smooth(A2_GRIP_CURVE, per_seg)[:-1]]


def grip_outline_engage(l=L):
    """参考写真の Engage 系グリップ（作者が選べるよう残す）。"""
    return ref_zy(l, REF_GRIP)


def polygon_centroid(pts):
    a = cx = cy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def trigger_guard(l=L):
    lb = l.bore_y + l.lower_bottom
    (r0, r1), (f0, f1) = [(min(p[0] for p in o), max(p[0] for p in o)) for o in ear_outlines(l)]
    gy = guard_bar_outline(l)[0][1]
    return [
        box(-12, gy, r0 + 3, 12, lb, r1, M.RECEIVER),           # 後ろの耳
        box(-12, gy, f0, 12, lb, f1 - 3, M.RECEIVER),           # 前の耳
        box(-6, gy, f1 - 5, 6, gy + 3.2, r0 + 5, M.RECEIVER),   # 下辺
    ]


def trigger(l=L):
    lb = l.bore_y + l.lower_bottom
    return [
        box(-3, lb - 6, -7, 3, lb + 4, 1, M.STEEL_DARK),
        box(-3, lb - 18, -1.5, 3, lb - 6, 2.5, M.STEEL_DARK),
        box(-3, lb - 26, -4.5, 3, lb - 18, 0.5, M.STEEL_DARK),  # 先端は前へ
    ]


GRIP_ANGLE = 25.0


def grip_frame(l=L):
    """キューブ版グリップの回転基準（上端前縁）と角度。"""
    return (0.0, l.bore_y + l.lower_bottom, 21.0), (GRIP_ANGLE, 0.0, 0.0)


def pistol_grip(l=L):
    (px, py, pz), rot = grip_frame(l)
    top = py
    return [
        box(-14, top - 108, pz, 14, top, pz + 42, M.POLYMER, rotation=rot, pivot=(px, py, pz)),
        box(-13, top - 56, pz - 5, 13, top - 46, pz, M.POLYMER, rotation=rot, pivot=(px, py, pz)),    # 指掛け
        box(-12, top, 51, 12, top + 6, 62, M.POLYMER),          # 後ろ上端の小さな張り出し
    ]


def buffer_tube(l=L):
    c = l.bore_y - 4
    z0 = l.lower_rear_z
    return [
        *round_rod(0, c, z0, l.buffer_end_z, 30, M.RECEIVER),
        *round_rod(0, c, z0, z0 + 10, 35, M.STEEL_DARK),                  # キャッスルナット
        box(-16, c - 16, z0 + 1, 16, c + 16, z0 + 5, M.STEEL_DARK),       # エンドプレート
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
    zf, zr = l.mag_center_z - 32, l.mag_center_z + 32
    piv = (0, split, zr)
    rot = (-MAG_ANGLE, 0, 0)
    return [
        box(-11, split, zf, 11, top, zr, M.MAG),
        box(-11, split - 80, zf, 11, split, zr, M.MAG, rotation=rot, pivot=piv),
        box(-13, split - 86, -121, 13, split - 78, -49, M.STEEL_DARK, rotation=rot, pivot=piv),  # フロアプレート
        box(-11.6, split + 5, zf + 7, 11.6, split + 65, zr - 7, M.MAG),  # 側面のリブ（直線部）
    ]


def cartridge_556(z_tip, y, case_mat=M.BRASS, bullet_mat=M.COPPER):
    """5.56x45 実包（弾頭が -Z）。全長 57.4mm、薬莢径 9.6mm。"""
    return (
        [box(-4.8, y - 4.8, z_tip + 12.7, 4.8, y + 4.8, z_tip + 57.4, case_mat)],
        [box(-2.85, y - 2.85, z_tip, 2.85, y + 2.85, z_tip + 12.7, bullet_mat)],
    )
