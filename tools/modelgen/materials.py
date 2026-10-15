"""材質パレット。色はテクスチャの下塗り。作者が PNG を塗り直す前提の仮色。"""
from core import Material

# --- パーツ組立版（実寸寄り）: 微小なゆらぎ＋汚れのむら＋傷。
# 面ごとの縁取り（edge）は使わない: 分解できない場所（1 部品の中の面の境目）にも継ぎ目が入って見えるため。
# 金属は傷が目立ち（地金が光る）、樹脂は傷が少なく汚れが乗る、という作り分け。
RECEIVER = Material("receiver", (62, 64, 67), noise=0.05, grime=0.14, scratch=0.004)
POLYMER = Material("polymer", (40, 40, 42), noise=0.06, grime=0.10, scratch=0.0015)
HANDGUARD = Material("handguard", (40, 40, 42), noise=0.06, grime=0.10, scratch=0.0015, dots=6)
STEEL = Material("steel", (74, 74, 70), noise=0.06, grime=0.16, scratch=0.006)
STEEL_DARK = Material("steel_dark", (38, 38, 38), noise=0.05, grime=0.14, scratch=0.004)
BORE = Material("bore", (12, 12, 12))
RAIL = Material("rail", (46, 47, 49), noise=0.05, grime=0.12, scratch=0.003, stripe=4)  # 8tex/px で 0.5px/スロット
RAIL_SIDE = Material("rail_side", (46, 47, 49), noise=0.05, grime=0.12, scratch=0.003, stripe=4, stripe_faces=("east", "west"))
RAIL_DOWN = Material("rail_down", (46, 47, 49), noise=0.05, grime=0.12, scratch=0.003, stripe=4, stripe_faces=("down",))
PANEL = Material("panel", (36, 36, 38), noise=0.06, grime=0.10, scratch=0.001)   # レールカバー（樹脂）
MAG = Material("mag", (74, 76, 68), noise=0.06, grime=0.16, scratch=0.006)            # 旧: オリーブ寄りの灰（不評）
MAG_USGI = Material("mag_usgi", (92, 96, 94), noise=0.05, grime=0.14, scratch=0.008)   # USGI アルミ弾倉（鈍い灰色の陽極酸化。傷で地金が出る）
MAG_AK = Material("mag_ak", (44, 44, 46), noise=0.05, grime=0.14, scratch=0.006)     # AK の鋼製弾倉（黒染め）
MAG_PMAG = Material("mag_pmag", (30, 30, 32), noise=0.05, grime=0.10, scratch=0.002)   # Magpul PMAG（黒い樹脂）
MP5_RECEIVER = Material("mp5_receiver", (48, 50, 54), noise=0.05, grime=0.12, scratch=0.004)   # MP5 の受け部（黒に近い灰色の塗装。写真）
# MP5 の材質（使い込まれた感: 塗装の擦れ・角の擦れ・埃）。他の銃の材質は変えない
MP5_RECEIVER_W = Material("mp5_receiver_w", (48, 50, 54), noise=0.05, grime=0.18, scratch=0.012,
                          wear=0.35, wear_color=(104, 106, 108), edge_wear=0.55, dust=0.12)
MP5_POLY = Material("mp5_poly", (38, 38, 40), noise=0.06, grime=0.14, scratch=0.004,
                    wear=0.25, wear_color=(70, 70, 70), edge_wear=0.35, dust=0.16)
MP5_STEEL = Material("mp5_steel", (36, 36, 37), noise=0.05, grime=0.16, scratch=0.010,
                     wear=0.22, wear_color=(100, 100, 98), edge_wear=0.45, dust=0.10)
MP5_MAG = Material("mp5_mag", (40, 41, 44), noise=0.05, grime=0.18, scratch=0.014,
                   wear=0.26, wear_color=(104, 104, 102), edge_wear=0.45, dust=0.12)
# M24 SWS の材質（使い込まれた感: MP5 と同じ汚し。ストックはざらついた塗装で埃が乗りやすい）
M24_STOCK = Material("m24_stock", (50, 52, 52), noise=0.10, grime=0.16, scratch=0.006,
                     wear=0.22, wear_color=(84, 86, 84), edge_wear=0.4, dust=0.2)
M24_STEEL = Material("m24_steel", (34, 34, 36), noise=0.05, grime=0.16, scratch=0.010,
                     wear=0.25, wear_color=(96, 96, 94), edge_wear=0.5, dust=0.1)
M24_BOLT = Material("m24_bolt", (92, 92, 90), noise=0.05, grime=0.12, scratch=0.016,
                    wear=0.15, wear_color=(140, 140, 136), dust=0.05)          # ボルト（明るい鋼）
# FN P90 の材質（本体は黒に近い灰色の樹脂、受け部はさらに黒い。弾倉は煙色の半透明樹脂。MP5 と同じ汚し）
P90_POLY = Material("p90_poly", (60, 61, 64), noise=0.06, grime=0.14, scratch=0.004,
                    wear=0.22, wear_color=(78, 78, 78), edge_wear=0.35, dust=0.14)
P90_HOUSING = Material("p90_housing", (32, 32, 34), noise=0.05, grime=0.14, scratch=0.008,
                       wear=0.22, wear_color=(84, 84, 84), edge_wear=0.45, dust=0.10)
P90_STEEL = Material("p90_steel", (30, 30, 31), noise=0.05, grime=0.16, scratch=0.010,
                     wear=0.22, wear_color=(96, 96, 94), edge_wear=0.45, dust=0.08)
P90_GUIDE = Material("p90_guide", (96, 94, 88), noise=0.05, grime=0.16, scratch=0.010, dust=0.06)   # 横の灰色の棒
P90_MAG = Material("p90_mag", (60, 56, 50), noise=0.06, grime=0.12, scratch=0.006, dust=0.08)      # 煙色の半透明樹脂
P90_MAG_CAP = Material("p90_mag_cap", (40, 38, 36), noise=0.05, grime=0.12, scratch=0.004)
# Winchester Model 12 トレンチガンの材質（黒染めの鋼は青みのある黒、ストック・先台は赤みのある胡桃材。使い込まれた感の汚し）
M1912_BLUED = Material("m1912_blued", (30, 32, 40), noise=0.05, grime=0.14, scratch=0.010,
                       wear=0.25, wear_color=(96, 98, 104), edge_wear=0.5, dust=0.06)
M1912_STEEL = Material("m1912_steel", (36, 36, 40), noise=0.05, grime=0.14, scratch=0.010,
                       wear=0.2, wear_color=(100, 100, 100), edge_wear=0.4, dust=0.06)
M1912_BOLT = Material("m1912_bolt", (150, 148, 140), noise=0.05, grime=0.12, scratch=0.016,
                      wear=0.15, wear_color=(176, 174, 168), dust=0.04)     # ボルト（排莢口から見える明るい鋼）
M1912_WOOD = Material("m1912_wood", (96, 40, 26), noise=0.08, grime=0.14, scratch=0.004,
                      wear=0.2, wear_color=(128, 70, 44), edge_wear=0.3, dust=0.06)
# Accuracy International AWM の材質（ストックはオリーブ色の樹脂塗装のアルミ・樹脂。作者の指定。使い込まれた感の汚し）
AWM_STOCK = Material("awm_stock", (82, 90, 62), noise=0.08, grime=0.16, scratch=0.006,
                     wear=0.22, wear_color=(112, 118, 92), edge_wear=0.4, dust=0.16)
AWM_STOCK_DARK = Material("awm_stock_dark", (52, 58, 40), noise=0.06, grime=0.14)   # 先台の溝の影
AWM_STEEL = Material("awm_steel", (32, 32, 34), noise=0.05, grime=0.16, scratch=0.010,
                     wear=0.22, wear_color=(96, 96, 94), edge_wear=0.45, dust=0.08)
AWM_BOLT = Material("awm_bolt", (120, 120, 116), noise=0.05, grime=0.12, scratch=0.016,
                    wear=0.15, wear_color=(160, 160, 154), dust=0.04)          # ボルト（明るい鋼）
AWM_MAG = Material("awm_mag", (84, 86, 86), noise=0.05, grime=0.16, scratch=0.014,
                   wear=0.25, wear_color=(130, 130, 128), edge_wear=0.45, dust=0.08)   # 弾倉（灰色の鋼）
# M79 の材質（ストックは暗い赤茶の木、先台は明るい木。銃身は黒染め、受け部の枠は灰色のパーカー処理。使い込まれた感の汚し）
M79_STOCK = Material("m79_stock", (86, 40, 30), noise=0.06, grime=0.14, scratch=0.004,
                     wear=0.2, wear_color=(116, 64, 48), edge_wear=0.3, dust=0.06)
M79_FOREND = Material("m79_forend", (150, 76, 40), noise=0.08, grime=0.14, scratch=0.004,
                      wear=0.2, wear_color=(176, 104, 64), edge_wear=0.3, dust=0.06)
M79_BLUED = Material("m79_blued", (28, 29, 33), noise=0.05, grime=0.14, scratch=0.010,
                     wear=0.22, wear_color=(96, 98, 102), edge_wear=0.45, dust=0.06)
M79_FRAME = Material("m79_frame", (58, 60, 62), noise=0.06, grime=0.16, scratch=0.010,
                     wear=0.22, wear_color=(104, 106, 108), edge_wear=0.45, dust=0.08)
M79_CASE = Material("m79_case", (150, 150, 146), noise=0.05, grime=0.10)        # 40mm の薬莢（アルミ）
M79_GRENADE = Material("m79_grenade", (74, 82, 52), noise=0.05, grime=0.10)     # 擲弾の弾頭（オリーブ色）
# M2 重機関銃の材質（パーカー処理の暗い灰緑の鋼、樹脂のグリップ、オリーブ色の弾薬箱。使い込まれた感の汚し）
M2_STEEL = Material("m2_steel", (56, 58, 54), noise=0.06, grime=0.18, scratch=0.010,
                    wear=0.22, wear_color=(100, 102, 96), edge_wear=0.45, dust=0.10)
M2_GRIP = Material("m2_grip", (34, 32, 30), noise=0.06, grime=0.12, scratch=0.004, edge_wear=0.2)
M2_CAN = Material("m2_can", (76, 82, 54), noise=0.06, grime=0.18, scratch=0.012,
                  wear=0.2, wear_color=(110, 112, 96), edge_wear=0.5, dust=0.14)
# G3A3 の材質（黒いリン酸塩処理の鋼の受け部・小物、オリーブ色の樹脂のハンドガード・グリップ・ストック。使い込まれた感の汚し）
G3_RECEIVER = Material("g3_receiver", (40, 41, 44), noise=0.05, grime=0.16, scratch=0.010,
                       wear=0.28, wear_color=(98, 100, 102), edge_wear=0.5, dust=0.10)
G3_STEEL = Material("g3_steel", (32, 32, 34), noise=0.05, grime=0.16, scratch=0.010,
                    wear=0.22, wear_color=(96, 96, 94), edge_wear=0.45, dust=0.08)
G3_OD = Material("g3_od", (84, 96, 72), noise=0.07, grime=0.16, scratch=0.005,
                 wear=0.2, wear_color=(110, 120, 98), edge_wear=0.35, dust=0.16)
G3_OD_DARK = Material("g3_od_dark", (46, 54, 40), noise=0.05, grime=0.12)       # ハンドガードの凹み・ねじ穴の影
G3_MAG = Material("g3_mag", (42, 43, 46), noise=0.05, grime=0.18, scratch=0.014,
                  wear=0.26, wear_color=(104, 104, 102), edge_wear=0.45, dust=0.12)
# HK416 の材質（黒いアルマイトの受け部・黒い樹脂。AR-15 から流用した部品の灰色の材質をこれに置き換える。使い込まれた感の汚し）
HK_RECEIVER = Material("hk_receiver", (36, 37, 40), noise=0.05, grime=0.14, scratch=0.010,
                       wear=0.25, wear_color=(92, 94, 98), edge_wear=0.5, dust=0.10)
HK_POLY = Material("hk_poly", (30, 30, 32), noise=0.06, grime=0.12, scratch=0.004,
                   wear=0.2, wear_color=(62, 62, 64), edge_wear=0.35, dust=0.14)
HK_STEEL = Material("hk_steel", (28, 28, 30), noise=0.05, grime=0.16, scratch=0.010,
                    wear=0.22, wear_color=(96, 96, 94), edge_wear=0.45, dust=0.08)
MARK_WHITE = Material("mark_white", (226, 226, 220), noise=0.03, grime=0.10)   # 刻印の白い塗り（セレクターの S など）
MARK_RED = Material("mark_red", (196, 38, 34), noise=0.03, grime=0.10)       # 刻印の赤い塗り（セレクターの E・F など）
FOLLOWER = Material("follower", (88, 100, 78), noise=0.05, grime=0.10, scratch=0.002)  # 弾倉の送り板（樹脂。中が見えたとき本体と見分けられる色）
RUBBER = Material("rubber", (24, 24, 24), noise=0.10, grime=0.08)
CANVAS = Material("canvas", (150, 126, 82), noise=0.10, grime=0.18)   # 布（タン）
BOX_LID = Material("box_lid", (30, 30, 32), noise=0.05, grime=0.12, scratch=0.002)
BOX_PLASTIC = Material("box_plastic", (46, 50, 44), noise=0.05, grime=0.14, scratch=0.002)   # 200 発ボックス（硬質樹脂・暗い緑黒）
WOOD = Material("wood", (108, 66, 36), noise=0.08, grime=0.16, scratch=0.002)   # AK の木製部品（赤みのある積層材。木目は作者が塗る）
BRASS = Material("brass", (184, 142, 62), noise=0.05, grime=0.08)
COPPER = Material("copper", (176, 102, 62), noise=0.05, grime=0.06)

# --- ピクセル版: 平塗り＋縁取り（ドット絵寄り）。グレーの段差をはっきり付けて部品を見分けやすくする
PX_RECEIVER = Material("px_receiver", (70, 72, 76), edge=0.35, edge_min=3)
PX_LOWER = Material("px_lower", (58, 60, 64), edge=0.35, edge_min=3)
PX_POLYMER = Material("px_polymer", (40, 40, 42), edge=0.35, edge_min=3)
PX_STEEL = Material("px_steel", (88, 88, 84), edge=0.35, edge_min=3)
PX_DARK = Material("px_dark", (28, 28, 30), edge=0.30, edge_min=3)
PX_RAIL = Material("px_rail", (54, 56, 60), stripe=2, stripe_dark=0.35)  # 2tex/px で 1テクセル交互
PX_RAIL_SIDE = Material("px_rail_side", (54, 56, 60), stripe=2, stripe_dark=0.35, stripe_faces=("east", "west"))
PX_RAIL_DOWN = Material("px_rail_down", (54, 56, 60), stripe=2, stripe_dark=0.35, stripe_faces=("down",))
PX_MAG = Material("px_mag", (82, 84, 76), edge=0.35, edge_min=3)
PX_BRASS = Material("px_brass", (200, 158, 70))
PX_COPPER = Material("px_copper", (190, 112, 70))


# --- ゲーム内の見え方への補正（作者の実機確認: 「テクスチャが暗い・まだら」）。
# 黒い仕上げの下塗り色（28〜48）はゲームの光でほぼ真っ黒になり、形が読めなかった。また、黒い下地に明るい「塗装の擦れの斑」
# （wear）・埃（dust）・汚れのむら（grime）を散らすと、色の差が大きくて斑点に見えた。暗い材質を持ち上げ、斑・むらは弱め、
# 角の擦れ（edge_wear。部品の輪郭が読める）だけ残す。銃口・穴の奥（BORE）と刻印の色は変えない。
def _game_ready(m):
    from dataclasses import replace
    if m.name in ("bore",) or m.name.startswith("mark_"):
        return m
    c = m.color
    if max(c) < 75:                                   # 黒・暗い灰の仕上げ
        c = tuple(int(round(v * 0.7 + 26)) for v in c)
    return replace(m, color=c, noise=m.noise * 0.8, grime=m.grime * 0.55, scratch=m.scratch * 0.7,
                   wear=m.wear * 0.3, dust=m.dust * 0.35)


for _n, _m in list(globals().items()):
    if isinstance(_m, Material):
        globals()[_n] = _game_ready(_m)
