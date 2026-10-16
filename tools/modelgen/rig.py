"""
コードが名前で参照するボーン・ロケーター・腕プレースホルダの共通部分（07-model-assets.md のボーン命名規約）と、
一人称で腕に銃を握らせる待機ポーズ（idle アニメーション）の計算。

一人称の配置は TaCZ の既定銃（AK47・M4A1。同じ idle_view / iron_view 方式）の実測から、トリガーを基準に決める。
どの肩撃ち銃もトリガー→床尾は 285〜390mm（腕の長さに合わせて作られる）なので、トリガー基準なら形が違っても同じ式で済む。
TaCZ（1px≒20.5mm）の実測: 腰だめのカメラ＝トリガーの 9px 後ろ・照準線の 0.8〜1.1px 上・2.5〜3.3px 横、
ADS の目＝トリガーの 5.5px 後ろ（AK・M4 で同じ）。下の値はそれを mm にしてこちらの縮尺（1px=24mm）に直したもの。
見た目の最終調整は作者が runClient で行う（ここは出発点）。
"""
import math

import numpy as np

from core import Model, _rot_raw

# glock.geo.json と同じ箱（作者が配置した値）。幅は 3px（SLIM。コードは常に SLIM の腕で描く → 07-model-assets.md）。
# 腕は両方 Box UV にして描画させない（規約）
ARM_PLACEHOLDERS = [
    {"name": "right_hand", "parent": "root", "pivot": [-6, 12, 6],
     "cubes": [{"origin": [-7.5, 0, 4], "size": [3, 12, 4], "uv": [0, 0]}]},
    {"name": "rightItem", "parent": "right_hand", "pivot": [-6, 0, 6]},
    {"name": "left_hand", "parent": "root", "pivot": [6, 12, 6.025],
     "cubes": [{"origin": [4.5, 0, 4], "size": [3, 12, 4], "uv": [0, 0]}]},
    {"name": "leftItem", "parent": "left_hand", "pivot": [6, -0.15, 6.925]},
]
ARM_LEN = 12.0                  # 腕の箱の長さ [px]（pivot＝肩側の端、Y=0 の端＝手）

HIP_SIDE = 3.0                  # 腰だめのカメラを銃の左へ [px]（+X が左。銃が画面の右に出る）
HIP_UP = 1.6                    # 腰だめのカメラの照準線からの高さ [px]（TaCZ の 0.85 では銃の上端がクロスヘアに届いて窮屈）
HIP_BEHIND = 7.7                # 腰だめのカメラのトリガーからの後ろ [px]（185mm）
IRON_BEHIND = 4.7               # ADS の目のトリガーからの後ろ [px]（113mm）
IRON_MIN_RELIEF = 3.0           # ADS の目はリアサイトより最低これだけ後ろ [px]（リアサイトが後ろ寄りの銃）
IRON_CLEAR = 3.5                # ADS の目は、照準線の近く（IRON_CLEAR_BELOW 以内）まで高さのある部品より最低これだけ後ろ [px]
IRON_CLEAR_BELOW = 0.6          # （AK の機関部カバー後端のように目の直前にあると、覗いた画面の下半分を覆う。実銃の頬付けで約 85mm）
IRON_MIN_ADVANCE = 1.0          # ADS の目は腰だめのカメラより最低これだけ前（覗いたとき銃が手前へ寄ってくるように）

# 待機ポーズ: 手先の位置（右＝グリップ、左＝ハンドガードの下）と、腕を伸ばしていく先（肘の目安。カメラからの相対 [px]）。
# 腕の箱は 12px しかないので、届かなければ長さ方向に伸ばす（TaCZ も待機ポーズで腕を 1.5 倍に伸ばしている）
RIGHT_TIP = (-0.6, -0.3, -1.2)  # グリップ中心からの手先の位置（glock の待機ポーズの手先とグリップの関係）
RIGHT_ELBOW = (-6.0, -10.0, 1.0)
LEFT_ELBOW = (7.0, -10.0, -5.0)
LEFT_SIDE = 0.4                 # 左手の中心を銃の中心線から左へ
LEFT_GRIP = 0.8                 # 左手の箱（厚さ 4px）の上面をハンドガードの下面からこれだけ食い込ませる（指が回り込む分）
# 拳銃: 作者が作った glock の一人称（両手で構える）をそのまま使う。カメラはトリガーからの前後と照準線からの高さ、
# 腕の待機ポーズは銃身の軸の高さとトリガーの前後の差だけ平行移動する（手と銃の関係を glock と同じにする）
GLOCK_TRIGGER_Z = 0.03525       # glock.geo.json の trigger の pivot
GLOCK_BORE_Y = 4.3125           # glock.geo.json の ammo の pivot（銃身の軸）
PISTOL_HIP = (0.0, 3.0, 12.215)     # idle_view: 照準線の 3px 上・トリガーの 12.2px 後ろ（glock の (0, 7.7, 12.25)）
PISTOL_IRON_Z = 9.715               # iron_view: トリガーの 9.7px 後ろ（glock の (0, 4.7, 9.75)）
PISTOL_IRON_BEHIND = PISTOL_IRON_Z * 24.0   # 同じ値の mm（照準器の誇張の大きさを決めるのに使う）
GLOCK_IDLE = {"right_hand": {"rotation": [-90, -6.25, 0], "position": [4.05159, -10.825, 5.8133]},
              "left_hand": {"rotation": [-90, 25, 0], "position": [-0.825, -11.175, 5]}}
SUPPORT_SKIP = ("magazin", "mag_ammo", "ammo", "bullet", "bipod_leg_l", "bipod_foot_l", "bipod_leg_r", "bipod_foot_r")


def add_locators(m: Model, muzzle, sight_line_y, rear_sight_z, grip_center, support_z, eye_relief=None, hands=None):
    """support_z: 左手を添える前後位置 [px]（ハンドガード・ポンプ・先台の下）。
    eye_relief: 照門から ADS の目までの距離 [px]（銃ごとに離したいとき。腰だめのカメラもその後ろへ下がる）。
    hands: (右手の先, 左手の先) [px] を直接指定する（M2 のように両手で後ろのグリップを握る銃）。"""
    tz = m.get("trigger").pivot[2]
    iron_z = max(tz + IRON_BEHIND, rear_sight_z + (IRON_MIN_RELIEF if eye_relief is None else eye_relief))
    hip = (HIP_SIDE, sight_line_y + HIP_UP, max(tz + HIP_BEHIND, iron_z + IRON_MIN_ADVANCE))
    m.bone("muzzle_flash", "root", muzzle)
    # カメラ基準は idle_view を親、iron_view をその子（どちらも root の外。07-model-assets.md）
    m.bone("idle_view", None, hip)
    m.bone("iron_view", "idle_view", (0, sight_line_y, iron_z))
    m.bone("ground", None, (0, 0, 0))
    m.bone("thirdperson_hand", None, grip_center)
    for b in ARM_PLACEHOLDERS:
        m.raw_bone(b)
    m.support_z = support_z
    m.hands = hands


def add_pistol_locators(m: Model, muzzle, sight_line_y, bore_y, grip_center):
    """拳銃のカメラ・腕の基準（glock と同じ構え。上の PISTOL_*）。bore_y: 銃身の軸の高さ [px]。"""
    tz = m.get("trigger").pivot[2]
    m.bone("muzzle_flash", "root", muzzle)
    m.bone("idle_view", None, (PISTOL_HIP[0], sight_line_y + PISTOL_HIP[1], tz + PISTOL_HIP[2]))
    m.bone("iron_view", "idle_view", (0, sight_line_y, tz + PISTOL_IRON_Z))
    m.bone("ground", None, (0, 0, 0))
    m.bone("thirdperson_hand", None, grip_center)
    for b in ARM_PLACEHOLDERS:
        m.raw_bone(b)
    m.support_z = None
    m.hands = None
    m.pistol = (0.0, bore_y - GLOCK_BORE_Y, tz - GLOCK_TRIGGER_Z)


def _bottom_at(bones, z, half_x=1.0):
    """前後位置 z の断面で、銃の中心線付近（|x| < half_x）の一番低い所の高さ [px]。"""
    import score
    T = score.world_tris([b for b in bones if b["name"] not in SUPPORT_SKIP
                                 and not b["name"].startswith(("belt_", "link_eject"))]) / score.MM_PER_PX
    low = math.inf
    for t in T:
        dz = t[:, 2] - z
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if dz[i] * dz[j] < 0 or dz[i] == 0:
                p = t[i] if dz[i] == 0 else t[i] + (t[j] - t[i]) * (dz[i] / (dz[i] - dz[j]))
                if abs(p[0]) < half_x:
                    low = min(low, p[1])
    return low


def _arm(pivot, tip, elbow):
    """手先 tip から肘の目安 elbow へ向かう腕のポーズ（回転・位置・長さ方向の拡大）。
    回転は core._rot_raw（= ローダーのアニメーション回転と同じ規則）で、静止時の向き (0,-1,0) を手先の向きへ回す。
    Z 回転は 0（glock の待機ポーズと同じ。腕のひねりを入れない）。"""
    tip, elbow, pivot = (np.array(v, float) for v in (tip, elbow, pivot))
    d = tip - elbow
    s = max(1.0, np.linalg.norm(d) / ARM_LEN)
    d /= np.linalg.norm(d)
    rx = -math.degrees(math.acos(max(-1.0, min(1.0, -d[1]))))
    ry = math.degrees(math.atan2(-d[0], -d[2]))
    R = _rot_raw((rx, ry, 0))
    assert np.allclose(R @ np.array([0, -1.0, 0]), d, atol=1e-6)
    shoulder = tip - ARM_LEN * s * d
    r = lambda v: [round(float(x), 4) for x in v]
    return {"rotation": r((rx, ry, 0)), "position": r(shoulder - pivot), "scale": r((1, s, 1))}


def place_iron_view(geo_bones):
    """焼き上げた形状を見て、ADS の目（iron_view）を目の直前の部品から IRON_CLEAR だけ離す（後ろへ下げるだけ）。"""
    import score
    by = {b["name"]: b for b in geo_bones}
    iv, hip = by["iron_view"]["pivot"], by["idle_view"]["pivot"]
    P = (score.world_tris(geo_bones) / score.MM_PER_PX).reshape(-1, 3)
    near = P[(np.abs(P[:, 0]) < 1.0) & (P[:, 1] > iv[1] - IRON_CLEAR_BELOW) & (P[:, 2] < iv[2])]
    if len(near):
        iv[2] = round(max(iv[2], float(near[:, 2].max()) + IRON_CLEAR), 4)
    # 機関部が床尾近くまで照準線の高さで続く銃（M249・MP5）は IRON_CLEAR を取りきれない。腰だめより前に留める
    iv[2] = min(iv[2], round(hip[2] - IRON_MIN_ADVANCE, 4))


def hold_animation(geo_bones, stem, support_z, hands=None, pistol=None):
    """腕に銃を握らせる待機ポーズ（idle）。作者が待機アニメーションを作るまでの仮置きで、腕のボーン以外は動かさない。
    hands を渡すと手先をその位置にし、肘は銃の中心に対して左右対称（手先の外 2.5px・カメラの 10px 下）に置く。
    pistol（add_pistol_locators が決める平行移動）を渡すと glock の待機ポーズをその分ずらして使う。"""
    if pistol is not None:
        bones = {n: {"rotation": list(v["rotation"]),
                     "position": [round(p + d, 4) for p, d in zip(v["position"], pistol)]} for n, v in GLOCK_IDLE.items()}
        return {"format_version": "1.8.0", "animations": {f"animation.{stem}.idle": {"loop": True, "bones": bones}}}
    by = {b["name"]: b for b in geo_bones}
    eye = np.array(by["idle_view"]["pivot"], float)
    if hands:
        right_tip, left_tip = (np.array(h, float) for h in hands)
        right_elbow = np.array((right_tip[0] - 2.5, eye[1] - 10.0, eye[2] + 1.0))
        left_elbow = np.array((left_tip[0] + 2.5, eye[1] - 10.0, eye[2] + 1.0))
    else:
        grip = np.array(by["thirdperson_hand"]["pivot"], float)
        right_tip = grip + RIGHT_TIP
        left_tip = np.array((LEFT_SIDE, _bottom_at(geo_bones, support_z) - 2.0 + LEFT_GRIP, support_z))
        right_elbow, left_elbow = eye + RIGHT_ELBOW, eye + LEFT_ELBOW
    return {"format_version": "1.8.0", "animations": {f"animation.{stem}.idle": {"loop": True, "bones": {
        "right_hand": _arm(by["right_hand"]["pivot"], right_tip, right_elbow),
        "left_hand": _arm(by["left_hand"]["pivot"], left_tip, left_elbow),
    }}}}
