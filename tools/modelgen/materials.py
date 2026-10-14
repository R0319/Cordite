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
