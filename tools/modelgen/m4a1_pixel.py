"""
M4A1（ピクセル版）: 寸法を 0.5px 刻みに丸め、形を簡略化した直接記述版。回転は使わず、
グリップ・弾倉・ストックの傾きは階段状に表す（ドット絵の斜め線と同じ考え方）。
全体の大きさ・ボア軸・レール寸法はパーツ版と同じ（アタッチメント・ロケーターの規約を共有するため）。
"""
from core import Model, box
from rig import add_locators
import materials as M


def build() -> tuple[Model, dict]:
    m = Model()
    m.bone("root", None, (0, 0, 0))
    B = 6.0  # ボア軸

    m.bone("receiver", "root", (0, B, 0), [
        box(-0.5, 5, -6.5, 0.5, 6.5, 1.5, M.PX_RECEIVER),             # 上部レシーバー
        box(-0.75, 5.25, -4, -0.5, 6.25, -1.5, M.PX_DARK),            # エジェクションポートカバー
        box(-0.5, 2, -5, 0.5, 5, -1.5, M.PX_LOWER),                   # マグウェル
        box(-0.5, 3.5, -1.5, 0.5, 5, 2.5, M.PX_LOWER),                # トリガーメカ部
        box(-0.5, 5, 1.5, 0.5, 6.5, 3, M.PX_LOWER),                   # バッファチューブ受け
        box(-0.25, 2, -1.5, 0.25, 2.5, 1.5, M.PX_LOWER),              # トリガーガード（後端はグリップに入る）
        box(-0.25, 2.5, -1.5, 0.25, 3.5, -1, M.PX_LOWER),
        # グリップ（階段で後傾）
        box(-0.5, 2.5, 0.5, 0.5, 3.5, 2.5, M.PX_POLYMER),
        box(-0.5, 1.5, 1, 0.5, 2.5, 3, M.PX_POLYMER),
        box(-0.5, 0.5, 1.5, 0.5, 1.5, 3.5, M.PX_POLYMER),
        box(-0.5, 0, 2, 0.5, 0.5, 3.5, M.PX_POLYMER),
        # バッファチューブ
        box(-0.5, 5.25, 3, 0.5, 6.25, 10, M.PX_LOWER),
        box(-0.75, 4.75, 3, 0.75, 6.75, 3.5, M.PX_DARK),
        # リアサイト
        box(-0.5, 7, 0, 0.5, 7.5, 1, M.PX_DARK),
        box(-0.25, 7.5, 0.25, 0.25, 8.5, 0.75, M.PX_DARK),
    ])
    m.bone("rail_top", "root", (0, 7, 1), [box(-0.5, 6.5, -6, 0.5, 7, 1, M.PX_RAIL)])  # 14 スロット・幅 1.0px
    m.bone("handguard", "root", (0, B, -7), [
        box(-1, 5, -14, 1, 7, -7, M.PX_POLYMER),
        box(-1.25, 4.75, -7, 1.25, 7.25, -6.5, M.PX_DARK),            # デルタリング
        box(-0.75, 5.25, -14.5, 0.75, 6.75, -14, M.PX_DARK),          # キャップ
    ])
    m.bone("barrel", "root", (0, B, -4.5), [box(-0.25, 5.75, -20.5, 0.25, 6.25, -4.5, M.PX_STEEL)])
    m.bone("chamber", "barrel", (0, B, -4.5), [box(-0.5, 5.5, -6.5, 0.5, 6.5, -4.5, M.PX_DARK)])
    m.bone("front_sight_base", "barrel", (0, B, -14.5), [
        box(-0.5, 5.5, -15.5, 0.5, 6.5, -14.5, M.PX_DARK),            # ガスブロック
        box(-0.25, 6.5, -15.5, 0.25, 8, -14.5, M.PX_DARK),            # 塔
        box(-0.25, 5, -15.5, 0.25, 5.5, -15, M.PX_DARK),              # 着剣ラグ
    ])
    m.bone("front_sight_post", "front_sight_base", (0, 8, -15), [
        box(-0.25, 8, -15.25, 0.25, 8.5, -14.75, M.PX_DARK),
    ])
    m.bone("muzzle", "root", (0, B, -20.5), [box(-0.5, 5.5, -22.5, 0.5, 6.5, -20.5, M.PX_DARK)])
    m.bone("bolt", "root", (0, B, -3), [box(-0.25, 5.5, -4, 0.25, 6, -1.5, M.PX_STEEL)])
    m.bone("charging_handle", "root", (0, 6.25, 1.5), [box(-1, 6, 1.5, 1, 6.5, 2, M.PX_DARK)])
    m.bone("trigger", "root", (0, 3.5, -0.25), [
        box(-0.25, 3, -0.5, 0.25, 3.5, 0, M.PX_DARK),
        box(-0.25, 2.5, -0.75, 0.25, 3, -0.25, M.PX_DARK),          # 先端は前へ
    ])
    m.bone("magazin", "root", (0, 2, -3.5), [
        box(-0.5, 0.5, -4.75, 0.5, 2, -2.25, M.PX_MAG),
        box(-0.25, 2, -4.75, 0.25, 5, -2.25, M.PX_MAG),              # マグウェル内（側面が重ならないよう細く）
        box(-0.5, -1, -5, 0.5, 0.5, -2.5, M.PX_MAG),
        box(-0.5, -2.5, -5.5, 0.5, -1, -3, M.PX_MAG),
        box(-0.75, -3, -5.75, 0.75, -2.5, -2.75, M.PX_DARK),          # フロアプレート
    ])
    m.bone("mag_ammo", "magazin", (0, 4.75, -3.5), [
        box(-0.25, 4.5, -4.5, 0.25, 5, -2.5, M.PX_BRASS),
        box(-0.25, 4.5, -5, 0.25, 5, -4.5, M.PX_COPPER),
    ])
    m.bone("ammo", "root", (0, B, -3.5), [box(-0.25, 5.75, -4.5, 0.25, 6.25, -2.5, M.PX_BRASS)])
    m.bone("bullet", "ammo", (0, B, -4.75), [box(-0.25, 5.75, -5, 0.25, 6.25, -4.5, M.PX_COPPER)])
    m.bone("stock", "root", (0, B, 7.5), [
        box(-0.75, 5, 7.5, 0.75, 6.5, 12.5, M.PX_POLYMER),
        box(-0.75, 4, 9, 0.75, 5, 12.5, M.PX_POLYMER),
        box(-0.75, 3, 10.5, 0.75, 4, 12.5, M.PX_POLYMER),
        box(-0.75, 2.5, 11.5, 0.75, 3, 12.5, M.PX_POLYMER),
        box(-1, 2.5, 12.5, 1, 7, 13, M.PX_DARK),                      # バットプレート
    ])
    add_locators(m, muzzle=(0, B, -22.5), sight_line_y=8.25, rear_sight_z=0.5,
                 grip_center=(0, 1.75, 2.25))
    return m, {}
