"""
AR-15 系のパーツライブラリ（単位 mm）。

各関数は「その部品だけのキューブ一覧」を返す。座標はすべて銃全体の共通座標（mm）:
  X=0 左右対称面（-X が右側面＝エジェクションポート側） / Y=0 グリップ底面 / Z=0 トリガー / 銃口 -Z
組み立て側（guns/*.py）が部品をボーンへ割り当て、mm→px（÷MM_PER_PX）へ変換する。

寸法は公開されている実銃寸法（M4A1: 全長 838mm〔ストック伸長〕・銃身 14.5in=368mm・
A2 フラッシュハイダー 57mm・サイト高 2.6in=66mm・STANAG 弾倉 約 180mm 等）を基にし、
公表値が無い部分（レシーバー各部の厚み等）は外観写真比の概算。
"""
import math

from core import box, cbox, round_rod
import materials as M

MM_PER_PX = 24.0              # 07-model-assets.md「1px ≒ 24mm」
SLOT_MM = 0.5 * MM_PER_PX     # レール1スロット = 0.5px（規約）
RAIL_W_MM = 1.0 * MM_PER_PX   # レール幅 = 1.0px（規約）


class Layout:
    """部品どうしの取り合い寸法。銃ごとにここだけ変えれば同系統の別銃（M16/HK416 等）に流用できる。"""
    bore_y = 155.4          # ボア軸高さ（グリップ底面基準。A2 グリップはレシーバー下面から約101mm下まである）
    bolt_face_z = -106.0    # ボルトフェイス（銃身の根元）。上部レシーバー前面（-125）の約 19mm 奥（バレルエクステンション内）
    barrel_len = 368.0      # 14.5in
    upper_front_z = -125.0  # 上部レシーバー前端（写真から）
    upper_rear_z = 70.0     # 上部レシーバー後端（写真から。下部の後端より少し前）
    upper_top = 17.0        # ボア軸からの上面高さ
    upper_bottom = -20.0    # 上下レシーバー分割線
    rail_slots = 16         # 写真のレール長 約192mm ÷ 12mm（規約の 0.5px/スロット）
    rail_h = 9.0
    sight_h = 66.0          # ボア軸→照準線（AR 系 2.6in）
    gas_port_from_bolt = 198.0  # ガスポート位置（M4 カービン長: ボルトフェイスから 7.8in）
    fsb_len = 46.0          # A2 フロントサイトベースの前後長（後ろの輪の後端〜前の柱の前面。写真から 1.81in。ラグはさらに 8mm 前へ出る）
    gas_port_from_fsb_rear = 6.0   # ガスポート中心 → フロントサイトベース後端（銃身の段 0.295in からキャップのつば分を引く）
    barrel_od = 19.05       # 銃身外径: ハンドガード内〜ガスブロックの軸受け（.750in）
    barrel_od_front = 18.4  # 銃身外径: フロントサイトベースより前（.725in）
    handguard_rear_z = -152.0   # デルタリング前面（上部レシーバー前端の約 27mm 前）
    ras_slots = 10          # RAS 各面のレールのスロット数（規約の 0.5px=12mm/スロット）
    magwell_front_z = -114.0    # マグウェル前面（写真から）
    magwell_rear_z = -42.0      # マグウェル後面＝ガードの前の耳（写真から）
    mag_center_z = -78.0        # 弾倉の前後中心
    lower_bottom = -54.4    # トリガーメカ部の下面（ボア軸基準）。写真のレール上面→この面が 80.4mm になるよう合わせた
    lower_rear_z = 72.0     # 下部レシーバーの後端（バッファチューブの付け根）。全体写真では上部の後端（70）とほぼ揃う
    fh_len = 44.0           # A2 フラッシュハイダーの銃身先端からの長さ
    buffer_end_z = 232.0    # バッファチューブ後端（全長 7.3in=185mm のうち約 25mm がレシーバー内 → 後端から 160mm）
    tube_od = 29.0          # バッファチューブ外径（1.14in）
    stock_collapsed_butt_z = 241.0   # 最も縮めたときの床尾。全体写真でストック前端がキャッスルナットのすぐ後ろ（Z≈86）
    stock_travel = 82.0     # 6 段階の伸縮幅（M4A1 全長 756→838mm の差）
    stock_pos = 2           # 0=最短 … 5=最長。既定は 3 段目（チューブが長く見えすぎないよう中間）
    stock_len = 155.0       # ストック本体の長さ（前端〜床尾。最短位置でレシーバーに当たらない長さ）
    mag_top_below_bore = 14.0   # 弾倉上端（送り出し口）のボア軸からの下がり
    mag_straight = 60.0     # 弾倉の直線部（上端〜マグウェル下あたり）
    mag_arc = 98.0          # 弾倉の湾曲部（半径一定で前へ反る）。全体写真（USGI 型のアルミ弾倉）で下端を合わせ 112→98

    @property
    def muzzle_z(self):     # 銃身先端
        return self.bolt_face_z - self.barrel_len

    @property
    def gas_z(self):        # フロントサイトベース後端（ガスポートはここから gas_port_from_fsb_rear 前）
        return self.bolt_face_z - self.gas_port_from_bolt + self.gas_port_from_fsb_rear

    @property
    def handguard_front_z(self):   # ハンドガードキャップ後端（キャップ 6mm はここから前、フロントサイトベースに接する）
        return self.gas_z + 6

    @property
    def butt_z(self):       # 床尾（ストック位置で変わる）
        return self.stock_collapsed_butt_z + self.stock_travel * self.stock_pos / 5

    @property
    def stock_front_z(self):
        return self.butt_z - self.stock_len

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
    """フリップアップ式リアサイト（起こした状態。アパーチャー中心＝照準線）。z はクランプ前端。
    大きさは全体写真の BUIS に合わせた（台は長さ 約 26mm・高さ 約 14mm、照準板は薄く照準線のすぐ上まで）。"""
    rt, sl = l.rail_top_y, l.bore_y + l.sight_h
    z = l.upper_rear_z - 30 if z is None else z
    return [
        box(-12, rt, z, 12, rt + 6, z + 26, M.STEEL_DARK),            # レールクランプ
        box(-8, rt + 6, z + 4, 8, rt + 13, z + 22, M.STEEL_DARK),     # 台（照準板の付け根）
        # 照準板（中央に 4mm の穴）
        box(-6, rt + 13, z + 11, 6, sl - 2, z + 13, M.STEEL_DARK),
        box(-6, sl + 2, z + 11, 6, sl + 4, z + 13, M.STEEL_DARK),
        box(2, sl - 2, z + 11, 6, sl + 2, z + 13, M.STEEL_DARK),
        box(-6, sl - 2, z + 11, -2, sl + 2, z + 13, M.STEEL_DARK),
        box(8, rt + 7, z + 6, 12, rt + 12, z + 12, M.STEEL_DARK),     # 左右調整ノブ（左）
    ]


# ---------------------------------------------------------------- 銃身まわり
def barrel(l=L):
    b = l.bore_y
    return [
        *round_rod(0, b, l.gas_z, l.bolt_face_z, l.barrel_od, M.STEEL),           # ハンドガード内
        *round_rod(0, b, l.muzzle_z, l.gas_z, l.barrel_od_front, M.STEEL),        # ガスブロック前（少し細い）
        cbox(0, b, l.muzzle_z - 0.3, l.muzzle_z + 20, 5.6, 5.6, M.BORE),   # 銃口の穴（5.56mm）
    ]


def barrel_extension(l=L):
    return round_rod(0, l.bore_y, l.bolt_face_z - 40, l.bolt_face_z, 26, M.STEEL_DARK)


def gas_block(l=L):
    """フロントサイトベースの銃身を抱く前後 2 つの輪（間は空いていて、横から銃身が見える）。"""
    b, z = l.bore_y, l.gas_z
    return [c for d0, d1 in FSB_RINGS for c in round_rod(0, b, z - d1, z - d0, FSB_RING_R * 2, M.STEEL_DARK)]


# ---- A2 フロントサイトベース（M4 用「F」刻印）。横から見ると「A」の字の枠:
#   前後 2 つの輪で銃身を抱き、輪の上を横棒（中にガスチューブ）でつなぐ。前は垂直の柱、後ろは斜めの支柱で、
#   その間（横棒の上）は大きな三角の窓、横棒の下も前後の輪の間が空いている。柱と支柱が上で合わさり、
#   そこに U 字の切り込み（左右の耳）とポストがある。前の輪の下に着剣ラグ（前へ突き出す）、後ろの輪の下にスイベル。
# 寸法は作者提供の側面写真から（縮尺 8.15px/mm）。縮尺は「銃身上面からサイトの上端まで 2.25in」と
# 「着剣ラグの上面が銃身の下面に接する」の 2 条件から決めた（全長は 46mm＝1.81in になり、販売店の 1.8in と合う）。
# 座標は (d, h): d＝後端から前へ [mm]、h＝ボア軸から上 [mm]。鍛造品なので角張ったまま（上端だけ丸い）。
FSB_TOWER_HALF = 7.5          # 横棒・柱・支柱の半幅（X）
FSB_EAR = (5.5, 10.0)         # 耳の内側・外側（X）。耳の間 11mm にポストが立つ
FSB_SLOT_DEPTH = 17.0         # 照準線から切り込みの底までの深さ（底は窓の上端のすぐ上）
FSB_RING_R = 11.0             # 輪の外半径（銃身 .750in を約 1.5mm の肉厚で抱く）
FSB_RINGS = ((0.0, 11.7), (33.7, 46.0))   # 後ろの輪・前の輪の前後範囲 (d0, d1)
FSB_BAR = (14.0, 22.0)        # 横棒の下面・上面の高さ h
FSB_POST_D = 36.7             # ポストの位置 d（窓の右上の出っ張り＝ポストのねじ受け）
# 柱＋上部（窓の上と前）。窓の右上の出っ張りまで含む
FSB_TOP = [(46.0, 14.0), (46.0, 59.4), (45.4, 61.8), (43.9, 64.3), (42.3, 65.8), (40.5, 66.7), (38.2, 67.1),
           (35.8, 66.7), (33.7, 65.8), (31.9, 64.3), (29.7, 61.8), (17.8, 47.1), (33.5, 47.1), (33.5, 41.6),
           (39.9, 41.6), (39.9, 14.0)]
# 斜めの支柱（後端の下部は垂直。窓側の辺は外側の辺と平行）
FSB_STRUT = [(0.0, 14.0), (0.0, 24.9), (29.6, 61.8), (36.0, 61.8), (24.0, 47.1), (4.0, 22.0), (4.0, 14.0)]


def _fsb_zy(l, pts):
    return [(l.gas_z - d, l.bore_y + h) for d, h in pts]


def fsb_profile(l=L):
    """柱＋支柱＋上部の側面形状 (z, y)（窓の下の横棒は含まない。下が開いているので穴のない 1 枚の輪郭になる）。"""
    from shapely.geometry import Polygon
    g = Polygon(_fsb_zy(l, FSB_TOP)).union(Polygon(_fsb_zy(l, FSB_STRUT)))
    return list(g.exterior.coords)[:-1]


def fsb_post_z(l=L):
    return l.gas_z - FSB_POST_D


def _fsb_box(l, d0, d1, h0, h1, x0, x1):
    b, z = l.bore_y, l.gas_z
    return box(x0, b + h0, z - d1, x1, b + h1, z - d0, M.STEEL_DARK)


def front_sight_base(l=L):
    """キューブ版（斜めの支柱は段で近似）。"""
    t, (e0, e1) = FSB_TOWER_HALF, FSB_EAR
    floor = l.sight_h - FSB_SLOT_DEPTH
    return [
        *fsb_frame_lower(l),
        _fsb_box(l, 39.9, 46.0, FSB_BAR[1], floor, -t, t),          # 前の柱
        _fsb_box(l, 33.5, 39.9, 41.6, floor, -t, t),                # ポストのねじ受け
        _fsb_box(l, 17.8, 39.9, 47.1, floor, -t, t),               # 窓の上
        *[_fsb_box(l, max(0.0, (h - 24.9) / 1.247), 4.0 + (h + 5.0 - 22.0) / 1.255, h, h + 5.0, -t, t)
          for h in (22.0, 27.0, 32.0, 37.0, 42.0)],                 # 斜めの支柱（5mm ごとの段）
        *[_fsb_box(l, d0, 46.0, floor - 4, top, x0, x1)             # 耳（左右。上の丸みは 2 段で近似）
          for x0, x1 in ((e0, e1), (-e1, -e0)) for d0, top in ((20.0, 57.0), (28.0, l.sight_h + 1))],
    ]


def fsb_frame_lower(l=L):
    """横棒・輪の上の脚・着剣ラグ・スイベル（キューブ。メッシュ版と共通）。"""
    t = FSB_TOWER_HALF
    (r0, r1), (f0, f1) = FSB_RINGS
    return [
        _fsb_box(l, 0.0, 46.0, FSB_BAR[0], FSB_BAR[1], -t, t),           # 横棒（中にガスチューブ）
        _fsb_box(l, r0, r1, 0.0, FSB_BAR[0], -FSB_RING_R, FSB_RING_R),    # 後ろの脚（輪の上半分〜横棒）
        _fsb_box(l, f0, f1, 0.0, FSB_BAR[0], -FSB_RING_R, FSB_RING_R),    # 前の脚
        _fsb_box(l, 36.2, 53.9, -17.9, -9.9, -4, 4),                      # 着剣ラグ（前の輪の下から前へ突き出す）
        _fsb_box(l, 36.2, 44.2, -22.2, -17.9, -4, 4),                     # ラグの下の段
        _fsb_box(l, 2.2, 9.0, -23.0, -9.0, -3, 3),                        # スイベルの台（後ろの輪の下、ピンは h=-16.7）
        # スイベルの吊り輪（ピンは左右方向。輪は銃身と同じ縦の面にあり、横から見ると四角い輪が見える）
        _fsb_box(l, -1.0, 10.8, -18.7, -16.7, -1.5, 1.5),
        _fsb_box(l, -1.0, 10.8, -30.8, -28.8, -1.5, 1.5),
        _fsb_box(l, -1.0, 1.0, -30.8, -16.7, -1.5, 1.5),
        _fsb_box(l, 8.8, 10.8, -30.8, -16.7, -1.5, 1.5),
    ]


def front_sight_post(l=L):
    b = l.bore_y
    sl = b + l.sight_h
    pz = fsb_post_z(l)
    floor = sl - FSB_SLOT_DEPTH
    return [
        box(-3, floor, pz - 2.5, 3, floor + 4, pz + 2.5, M.STEEL_DARK),   # 台座（回して高さを調整する部分）
        box(-0.9, floor + 4, pz - 0.9, 0.9, sl, pz + 0.9, M.STEEL_DARK),  # ポスト（1.8mm 角、先端＝照準線）
    ]


# ---- KAC M4 RAS（レール付きハンドガード）。純正ハンドガードと同じくデルタリングとキャップの間に収まる。
# 本体は断面八角（向かい合う平面間 42mm）、上下左右に MIL-STD-1913 レール。レールは削り出しなので角張ったまま。
# 上面レールの天面は上部レシーバーのレールと同じ高さ（アタッチメントの取付高さを揃える）。
RAS_FLAT = 21.0     # ボア軸→本体の平面
RAS_NECK = (16.0, 2.0)   # レールの首（幅, 高さ）
RAS_HEAD = (24.0, 3.0)   # レールの頭（幅＝規約の 1.0px, 高さ）


def ras_rail_span(l=L):
    """RAS レールの前後端（中央寄せ、スロット数で長さが決まる）。戻り値は (前端 z, 後端 z)。"""
    mid = (l.handguard_front_z + l.handguard_rear_z) / 2
    half = l.ras_slots * SLOT_MM / 2
    return mid - half, mid + half


def _ras_rail(l, side, mat):
    """side: 'top' / 'bottom' / 'left'(+X) / 'right'(-X)"""
    b = l.bore_y
    z0, z1 = ras_rail_span(l)
    (nw, nh), (hw, hh) = RAS_NECK, RAS_HEAD
    r0, r1, r2 = RAS_FLAT, RAS_FLAT + nh, RAS_FLAT + nh + hh
    if side in ("top", "bottom"):
        s = 1 if side == "top" else -1
        return [box(-nw / 2, b + s * r0, z0, nw / 2, b + s * r1, z1, mat),
                box(-hw / 2, b + s * r1, z0, hw / 2, b + s * r2, z1, mat)]
    s = 1 if side == "left" else -1
    return [box(s * r0, b - nw / 2, z0, s * r1, b + nw / 2, z1, mat),
            box(s * r1, b - hw / 2, z0, s * r2, b + hw / 2, z1, mat)]


def handguard(l=L):
    """RAS 本体（キューブ版は角柱）＋上面レール＋デルタリング＋キャップ。下面・側面レールは別ボーン。"""
    b = l.bore_y
    f, r = l.handguard_front_z, l.handguard_rear_z
    return [
        cbox(0, b, f, r, RAS_FLAT * 2, RAS_FLAT * 2, M.RECEIVER),
        *_ras_rail(l, "top", M.RAIL),
        *round_rod(0, b, r, r + 12, 60, M.STEEL_DARK),     # デルタリング
        *round_rod(0, b, f - 6, f, 46, M.STEEL_DARK),     # ハンドガードキャップ
    ]


def ras_rail_bottom(l=L):
    return _ras_rail(l, "bottom", M.RAIL_DOWN)


def ras_rail_sides(l=L):
    return _ras_rail(l, "left", M.RAIL_SIDE) + _ras_rail(l, "right", M.RAIL_SIDE)


def flash_hider_a2(l=L):
    """A2 バードケージ。下面は閉じ（バードケージ下の板）、他はスリット＝棒で表す。"""
    b, z1 = l.bore_y, l.muzzle_z
    z0 = z1 - l.fh_len
    out = [
        *round_rod(0, b, z1 - 15, z1, 22, M.STEEL_DARK),      # 根元
        *round_rod(0, b, z0, z0 + 6, 22, M.STEEL_DARK),       # 先端リング
        cbox(0, b, z0 - 0.3, z0 + 6, 8, 8, M.BORE),           # 先端の穴
        cbox(0, b, z0 + 6, z1 - 15, 12, 12, M.BORE),          # 内側（暗）
        box(-6, b - 11, z0 + 6, 6, b - 7, z1 - 15, M.STEEL_DARK),   # 下面の板
    ]
    for ang in (-120, -60, 0, 60, 120):                    # スリット間の棒（銃軸まわりに回転配置）
        out.append(box(-2, b + 7, z0 + 6, 2, b + 11, z1 - 15, M.STEEL_DARK,
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

# A2 グリップ（M4A1 標準）の輪郭（z, レシーバー下面 lb からの y）。作者提供の全体写真（上の LOWER_REAR_UNDER と同じ縮尺）の
# 輪郭に合わせた。写真は 1px≒1mm と粗いので、通過点を曲線で結んでなだらかにする。
# 特徴: 上端の後ろに張り出しは無く、レシーバー下面からなだらかにつながる。背面は前面より寝ていて（背面 約 33°・前面 約 28°）
# 下ほど前後に太い。前面中ほどに指掛けの膨らみ 1 つ。底は前がやや低い。
A2_GRIP_CURVE = [
    (49.5, 0.0),                                  # 上面の後端（ここからレシーバー下面が反り上がる）
    (50.2, -6.0), (52.5, -13.0),                  # 背面の上端（レシーバー下面からなだらかに続く）
    (59.8, -25.0), (66.2, -33.0), (71.6, -42.0),  # 背面
    (78.0, -50.5), (83.3, -59.0), (89.7, -68.0),
    (95.1, -76.0), (99.5, -84.0),
    (100.5, -88.0), (98.0, -92.0),                # 背面→底の丸い角
    (80.0, -95.5), (58.0, -99.0),                 # 底（前がやや低い）
    (51.5, -97.5), (48.5, -92.0),                 # 底→前面の丸い角
    (46.5, -85.0), (43.0, -76.0), (39.5, -71.0),  # 前面下部（薬指・小指）
    (35.5, -63.0), (30.5, -58.5),
    (24.0, -54.0), (23.0, -50.5),                 # 指掛けの膨らみ（中指と薬指の間）
    (25.0, -46.0),                                # 中指の凹み
    (21.5, -38.0), (20.8, -30.0),                 # 前面上部（トリガーガードの後ろの耳に沿ってほぼ垂直）
    (21.0, -18.0), (20.8, 0.0),                   # 上面の前端
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
# レシーバー後部の下面（z, レシーバー下面 lb からの y）。グリップ上面の後端から、なだらかに反り上がってバッファチューブ受けまで。
# 作者提供の全体写真（M4A1＋RAS、縮尺は上部レシーバーの長さ 195mm で合わせた 0.936px/mm）から。
# 以前は別の写真から取った輪郭で後端が Z=88 まで伸び、グリップ上端の後ろに張り出しを作って面を合わせていた（機関部が 16mm 長かった）
LOWER_REAR_UNDER = [(49.5, 0.0), (51.5, 5.0), (54.0, 9.5), (59.0, 13.5), (66.0, 16.5), (72.0, 18.0)]
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
    lb = b + l.lower_bottom
    under = [(z, lb + y) for z, y in LOWER_REAR_UNDER]
    zr = l.lower_rear_z
    return under + [(zr, b + 14), (l.upper_rear_z, b + 14), (l.upper_rear_z, b + l.upper_bottom),
                    (under[0][0], b + l.upper_bottom)]


def lower_body(l=L):
    """キューブ版。メッシュ版は ar15_mesh.lower_body でレシーバー後部だけ輪郭の押し出しに置き換える。"""
    b = l.bore_y
    lb = b + l.lower_bottom
    zg = LOWER_REAR_UNDER[0][0]    # グリップ上面の後端
    return lower_common(l) + [
        box(-12, lb, l.magwell_rear_z, 12, b + l.upper_bottom, zg, M.RECEIVER),             # トリガーメカ部
        box(-12.5, lb + 8, zg, 12.5, b + 14, 60.0, M.RECEIVER),                          # 後部（下面の反り上がりを段で近似）
        box(-12.5, lb + 15, 60.0, 12.5, b + 14, l.lower_rear_z, M.RECEIVER),
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


def grip_outline(l=L, per_seg=3, extend_top=0.0):
    """A2 グリップの側面形状。extend_top>0 で上面（と張り出しの上縁）をレシーバー内へ持ち上げる
    （メッシュ版は縁を丸めるので、丸みをレシーバーの中に埋めて上面の密着を保つため）。"""
    from core import smooth
    lb = l.bore_y + l.lower_bottom
    curve = A2_GRIP_CURVE
    if extend_top:
        curve = [(z, y + extend_top) if i in (0, 1, 2, len(curve) - 1) else (z, y) for i, (z, y) in enumerate(curve)]
    return [(z, lb + y) for z, y in smooth(curve, per_seg)[:-1]]


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


GRIP_ANGLE = 30.0   # キューブ版の傾き（背面 33°・前面 28° の中間）


def grip_frame(l=L):
    """キューブ版グリップの回転基準（上端前縁）と角度。"""
    return (0.0, l.bore_y + l.lower_bottom, 21.0), (GRIP_ANGLE, 0.0, 0.0)


def pistol_grip(l=L):
    (px, py, pz), rot = grip_frame(l)
    top = py
    return [
        box(-14, top - 112, pz, 14, top, pz + 30, M.POLYMER, rotation=rot, pivot=(px, py, pz)),
        box(-14, top - 112, pz + 30, 14, top - 30, pz + 40, M.POLYMER, rotation=rot, pivot=(px, py, pz)),  # 下ほど太い
        box(-13, top - 60, pz - 4, 13, top - 50, pz, M.POLYMER, rotation=rot, pivot=(px, py, pz)),    # 指掛け
    ]


def buffer_tube(l=L):
    c = l.bore_y - 4
    z0 = l.lower_rear_z
    return [
        *round_rod(0, c, z0, l.buffer_end_z, l.tube_od, M.RECEIVER),
        *round_rod(0, c, z0, z0 + 10, 35, M.STEEL_DARK),                  # キャッスルナット
        box(-16, c - 16, z0 + 1, 16, c + 16, z0 + 5, M.STEEL_DARK),       # エンドプレート
    ]


def stock_m4(l=L):
    """M4 6 ポジションストック（stock_pos の位置）。下側の斜面は回転板＋段で埋める。"""
    b = l.bore_y
    f, z1 = l.stock_front_z, l.butt_z - 6
    zr = z1 - 48                        # 後部（つま先側の縦の部分）の前端
    dz = zr - f
    slope = math.degrees(math.atan2(58, dz))
    line = lambda z: b - 22 - (z - f) * 58 / dz   # 下縁の斜面
    zs1, zs2 = f + dz * 0.25, f + dz * 0.6
    return [
        box(-17, b - 22, f, 17, b + 16, z1, M.POLYMER),                        # チューブ外套
        box(-16, b - 80, zr, 16, b - 22, z1, M.POLYMER),                       # 後部
        box(-15.7, line(zs2), zs2, 15.7, b - 22, zr, M.POLYMER),               # 斜面の内側を段で埋める
        box(-15.7, line(zs1), zs1, 15.7, b - 22, zs2, M.POLYMER),
        box(-15.4, b - 22, f, 15.4, b + 12, f + math.hypot(dz, 58), M.POLYMER,
            rotation=(-slope, 0, 0), pivot=(0, b - 22, f)),                   # 下側の斜面（板の下縁＝斜面）
        box(-5, b - 30, f + 5, 5, b - 22, f + 50, M.STEEL_DARK),               # 調整レバー
        box(-19, b - 85, z1, 19, b + 20, l.butt_z, M.RUBBER),                  # バットプレート
    ]


MAG_ANGLE = 17.5   # 湾曲部全体での反りの角度（反りの半径は約 320mm のまま、湾曲部を短くした分だけ小さい）


def magazine_stanag(l=L):
    """STANAG 30 発弾倉（角張った箱形）。上は直線、マグウェルの下から前へ反る。湾曲は 2 本の箱で近似。"""
    b = l.bore_y
    top = b - l.mag_top_below_bore
    split = top - l.mag_straight
    zf, zr = l.mag_center_z - 32, l.mag_center_z + 32
    half = l.mag_arc / 2
    a1 = math.radians(MAG_ANGLE / 2)
    piv1 = (0, split, zr)
    piv2 = (0, split - half * math.cos(a1), zr - half * math.sin(a1))   # 1 本目の下端後ろ角（回転後）
    rot1, rot2 = (-MAG_ANGLE / 2, 0, 0), (-MAG_ANGLE, 0, 0)
    p2y, p2z = piv2[1], piv2[2]
    return [
        box(-11, split, zf, 11, top, zr, M.MAG),
        box(-11, split - half, zf, 11, split, zr, M.MAG, rotation=rot1, pivot=piv1),
        box(-11, p2y - half, p2z - 64, 11, p2y + 1, p2z, M.MAG, rotation=rot2, pivot=piv2),
        box(-13, p2y - half - 6, p2z - 68, 13, p2y - half + 2, p2z + 4, M.STEEL_DARK, rotation=rot2, pivot=piv2),  # 底板
        box(-11.6, split + 5, zf + 7, 11.6, top - 25, zr - 7, M.MAG),  # 側面のリブ（直線部）
    ]


def cartridge_556(z_tip, y, case_mat=M.BRASS, bullet_mat=M.COPPER):
    """5.56x45 実包（弾頭が -Z）。全長 57.4mm、薬莢径 9.6mm。"""
    return (
        [box(-4.8, y - 4.8, z_tip + 12.7, 4.8, y + 4.8, z_tip + 57.4, case_mat)],
        [box(-2.85, y - 2.85, z_tip, 2.85, y + 2.85, z_tip + 12.7, bullet_mat)],
    )
