"""
コードが名前で参照するボーン・ロケーター・腕プレースホルダの共通部分（07-model-assets.md のボーン命名規約）。

見た目の調整値（idle_view・腕プレースホルダの位置）は glock の値をそのまま流用した仮置き。
作者が runClient で確認しながら Blockbench で動かす前提で、ここでは「構造的に正しい位置」だけ計算する:
  - muzzle_flash: 銃口の中心
  - iron_view   : 照準線上（リアサイト後方。後方距離は glock の値に合わせた仮値）
  - thirdperson_hand: グリップの中心
"""
from core import Model

# glock.geo.json から流用（作者が配置した値）。腕は両方 Box UV にして描画させない（規約）
ARM_PLACEHOLDERS = [
    {"name": "right_hand", "parent": "root", "pivot": [-6, 12, 6],
     "cubes": [{"origin": [-8, 0, 4], "size": [4, 12, 4], "uv": [0, 0]}]},
    {"name": "rightItem", "parent": "right_hand", "pivot": [-6, 0, 6]},
    {"name": "left_hand", "parent": "root", "pivot": [6, 12, 6.025],
     "cubes": [{"origin": [4, 0, 4], "size": [4, 12, 4], "uv": [0, 0]}]},
    {"name": "leftItem", "parent": "left_hand", "pivot": [6, -0.15, 6.925]},
]
GLOCK_IDLE_VIEW = (0, 7.7, 12.25)
GLOCK_IRON_EYE_BACK = 7.3   # glock: リアサイト（Z≒2.45）→ iron_view（Z=9.75）の距離 [px]


def add_locators(m: Model, muzzle, sight_line_y, rear_sight_z, grip_center):
    m.bone("muzzle_flash", "root", muzzle)
    m.bone("idle_view", "root", GLOCK_IDLE_VIEW)
    m.bone("iron_view", "root", (0, sight_line_y, rear_sight_z + GLOCK_IRON_EYE_BACK))
    m.bone("ground", None, (0, 0, 0))
    m.bone("thirdperson_hand", None, grip_center)
    for b in ARM_PLACEHOLDERS:
        m.raw_bone(b)
