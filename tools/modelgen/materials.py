"""材質パレット。色はテクスチャの下塗り。作者が PNG を塗り直す前提の仮色。"""
from core import Material

# --- パーツ組立版（実寸寄り）: 微小なゆらぎ＋面の縁を暗く
RECEIVER = Material("receiver", (62, 64, 67), noise=0.05, edge=0.30, edge_min=6)
POLYMER = Material("polymer", (40, 40, 42), noise=0.07, edge=0.25, edge_min=6)
HANDGUARD = Material("handguard", (40, 40, 42), noise=0.07, edge=0.25, edge_min=6, dots=6)
STEEL = Material("steel", (74, 74, 70), noise=0.06, edge=0.30, edge_min=6)
STEEL_DARK = Material("steel_dark", (38, 38, 38), noise=0.05, edge=0.25, edge_min=6)
BORE = Material("bore", (12, 12, 12))
RAIL = Material("rail", (46, 47, 49), noise=0.05, edge=0.30, edge_min=6, stripe=4)  # 8tex/px で 0.5px/スロット
RAIL_SIDE = Material("rail_side", (46, 47, 49), noise=0.05, edge=0.30, edge_min=6, stripe=4, stripe_faces=("east", "west"))
RAIL_DOWN = Material("rail_down", (46, 47, 49), noise=0.05, edge=0.30, edge_min=6, stripe=4, stripe_faces=("down",))
MAG = Material("mag", (74, 76, 68), noise=0.06, edge=0.30, edge_min=6)
RUBBER = Material("rubber", (24, 24, 24), noise=0.10)
BRASS = Material("brass", (184, 142, 62), noise=0.05)
COPPER = Material("copper", (176, 102, 62), noise=0.05)

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
