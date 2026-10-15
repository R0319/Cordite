"""
ライオット兵の盾（覗き窓付きのバリスティックシールド）。Cordite-dev の受け渡しの約束（docs/design/soldier.md 11.3）に合わせる:

- 銃と同じ置き場所・読み込み（models/gun/riot_shield.geo.json・textures/gun/riot_shield.png・riot_shield_modelshot.png）。
- 手に持ったときはモデルの thirdperson_hand ロケーター（握りの位置）を手に合わせる。持つのは左手（オフハンド）で、
  腕はバニラの盾を構えるポーズ。一人称・アニメーションは無い。
- 当たり判定はコード側の定数（幅 0.6 × 高さ 1.0 ブロック、体の前 0.35〜0.45、足元から 0.45〜1.45）。見た目もこの大きさ。

縮尺: 盾のアイテムモデルは表示の変換を持たない（builtin/entity）ので、手に持ったとき 1px = 1/16 ブロック。当たり判定と
同じ大きさにするため、銃（1px ≒ 24mm）と違い 1 ブロック = 1000mm（1px = 62.5mm）で作る。
置き方: 手に持った盾が当たり判定の板の上下・左右に重なり、正面を向くように、バニラの「左腕で盾を構える」ポーズの腕と
手持ちの変換（下の VANILLA_*。Minecraft 1.21.1 の PlayerModel・ItemInHandLayer・LivingEntityRenderer の値）を
たどって逆算し、その位置・向きでモデルに焼き込む（ローダーはボーンの初期回転を読まないため）。
**前後だけは当たり判定と合わない**: この腕のポーズでは拳が体の 0.43〜0.56、腕の箱の角が 0.68 ブロック前まで出るので、
板を当たり判定（0.35〜0.45 前）に置くと腕が盾を突き抜ける。見た目の板は腕の前（PLATE_FRONT＝0.70）に置き、
当たり判定を前へずらすようコード側へ伝えた（2026-10-15）。
アイコンは手に持つ向きにする前の盾を前から描く。

寸法（推定。実物の製品の代表的な値）: 板 600×1000mm・厚さ 14mm、角の丸み 70mm、覗き窓 260×90mm（上から 220mm）、
裏に縦の握り（太さ 28mm）と前腕のベルト。
"""
import math

from shapely.geometry import Point, box as sbox
from shapely.ops import unary_union

import ar15_mesh
import materials as M
import sights
from core import extrude_x, extrude_x_beveled
from m249 import y_cyl

K = 16.0 / 1000.0                  # px / mm（1 ブロック = 1000mm。上の説明）
W, H = 600.0, 1000.0               # 板の幅・高さ（当たり判定と同じ）
PLATE_T = 14.0                     # 板の厚さ。盾の座標は板の中心が原点（-Z が前、+Y が上、+X が持つ人の左）
CORNER_R = 70.0
WINDOW = (260.0, 90.0, 220.0)      # 覗き窓の幅・高さ・上の端から窓の中心まで

# 当たり判定（Cordite-dev の combat.Shielded。体の向きを前とする座標 [ブロック]。左が +X）
HIT_CENTER_X = 0.05                # 幅 0.6、中心は左へ 0.05
HIT_CENTER_Y = 0.95                # 足元から 0.45〜1.45
PLATE_FRONT = 0.70                 # 見た目の板の前の面（当たり判定は 0.45。上の説明）

# バニラの値（Minecraft 1.21.1）: 左腕の付け根・盾を構える角度・手持ちの物の基準点・体の空間から足元基準へ
VANILLA_ARM_PIVOT = (5.0, 2.0, 0.0)            # PlayerModel の leftArm（px。+Y 下、-Z 前）
VANILLA_BLOCK_ROT = (-0.9424779, math.pi / 6)  # HumanoidModel#poseLeftArm の BLOCK（xRot, yRot。Cordite-dev の SoldierModel も同じ）
VANILLA_HAND_OFFSET = (-1.0 / 16, 0.125, -0.625)   # ItemInHandLayer#renderArmWithItem（左手）。その前に X -90°・Y 180°
VANILLA_BODY_Y = 1.501                         # LivingEntityRenderer（scale(-1,-1,1) の後の translate）
GRIP_ARM_Y = 12.0                              # 握りを置く腕の上の位置（付け根から px。腕の箱は 12px）

BODY = M.SHIELD_BODY
RIM = M.SHIELD_RIM
GLASS = M.SHIELD_GLASS


def _box(x0, y0, z0, x1, y1, z1, mat):
    """直方体（回せるようにメッシュで作る）。"""
    return extrude_x([(z0, y0), (z1, y0), (z1, y1), (z0, y1)], x0, x1, mat)


def _rounded_rect(x0, y0, x1, y1, r):
    return sbox(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=4)


def _hold():
    """手持ちの変換: 盾の座標 [mm] → モデルの座標 [px] の (回転, 平行移動) と、握りの位置（盾の座標 [mm]）。"""
    import numpy as np

    def rx(a):
        c, s_ = math.cos(a), math.sin(a)
        return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])

    def ry(a):
        c, s_ = math.cos(a), math.sin(a)
        return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
    body = np.diag([1.0, -1.0, -1.0])                         # 体の空間 → 足元基準（南向き: 左 +X・上 +Y・前 +Z）
    body0 = np.array([0.0, VANILLA_BODY_Y, 0.0])
    arm = ry(VANILLA_BLOCK_ROT[1]) @ rx(VANILLA_BLOCK_ROT[0])
    pivot = np.array(VANILLA_ARM_PIVOT) / 16.0
    item = arm @ rx(math.radians(-90)) @ ry(math.radians(180))
    anchor = body @ (pivot + item @ np.array(VANILLA_HAND_OFFSET)) + body0       # 手持ちの物の基準点（足元基準）
    to_world = body @ item @ np.diag([-1.0, 1.0, 1.0]) / 16.0                    # モデル [px] → 足元基準（ローダーが X を反転）
    shield = np.diag([1.0, 1.0, -1.0]) / 1000.0                                   # 盾の座標 [mm] → 足元基準
    center = np.array([HIT_CENTER_X, HIT_CENTER_Y, PLATE_FRONT + PLATE_T / 2000.0])
    inv = np.linalg.inv(to_world)
    rot = inv @ shield                                                           # 盾 [mm] → モデル [px]
    off = inv @ (center - anchor)
    fist = body @ (pivot + arm @ np.array([1.0, GRIP_ARM_Y, 0.0]) / 16.0) + body0
    grip = np.linalg.inv(shield) @ (fist - center)
    return rot, off, tuple(float(v) for v in grip)


def _plate():
    """板（覗き窓の穴が前後に抜けている）・前の面の縁の帯・窓の枠・窓のガラス（暗い色の板。穴の中に少し引っ込める）。"""
    y0, y1 = -H / 2, H / 2
    ww, wh, wc = WINDOW
    wy = y1 - wc
    win = _rounded_rect(-ww / 2, wy - wh / 2, ww / 2, wy + wh / 2, 14.0)
    plate = _rounded_rect(-W / 2, y0, W / 2, y1, CORNER_R).difference(win)
    zf, zb = -PLATE_T / 2, PLATE_T / 2
    out = sights.plate_z(plate.simplify(0.05), zf, zb, BODY)
    rim = _rounded_rect(-W / 2, y0, W / 2, y1, CORNER_R).difference(_rounded_rect(-W / 2 + 22, y0 + 22, W / 2 - 22, y1 - 22,
                                                                                  CORNER_R - 22))
    out += sights.plate_z(rim.simplify(0.05), zf - 4.0, zf + 0.5, RIM)          # 前の面の縁（4mm 出す）
    frame = win.buffer(16.0, quad_segs=4).difference(win)
    out += sights.plate_z(frame.simplify(0.05), zf - 6.0, zf + 0.5, RIM)        # 窓の枠
    out += sights.plate_z(win.buffer(0.6).simplify(0.05), zf + 4.0, zb - 2.0, GLASS)   # ガラス（前の面から 4mm 引っ込める）
    return out


def _handle(grip):
    """裏の縦の握り（台座 2 つで板に留める）と、前腕を通すベルト。握りは拳の位置（_hold が求めた grip）に置く。"""
    gx, gy, gz = grip
    zb = PLATE_T / 2
    out = [y_cyl(gx, gz, 14.0, gy - 70.0, gy + 70.0, M.POLYMER, n=ar15_mesh.N_SMALL)]
    for y in (gy - 85.0, gy + 85.0):                                    # 台座（板の裏から握りまで）
        out.append(extrude_x_beveled([(zb - 1.0, y - 15.0), (gz + 6.0, y - 15.0), (gz + 6.0, y + 15.0), (zb - 1.0, y + 15.0)],
                                     gx - 16.0, gx + 16.0, 3.0, RIM, steps=1))
    yb = gy - 230.0                                                     # 前腕のベルト（握りの下）
    for x in (gx - 95.0, gx + 95.0):
        out.append(_box(x - 12, yb - 20, zb - 1.0, x + 12, yb + 20, zb + 14.0, RIM))
    out.append(_box(gx - 95, yb - 15, zb + 10.0, gx + 95, yb + 15, zb + 16.0, M.CANVAS))
    return out


def parts(grip):
    return _plate() + _handle(grip)


def _transform(items, rot, off):
    """メッシュの頂点・法線に、回転 rot（3×3）と平行移動 off をかける。"""
    import numpy as np
    from core import MeshPart
    out = []
    for m in items:
        v = np.asarray(m.verts, float) @ rot.T + off
        n = None
        if m.normals is not None:
            r = rot / np.linalg.norm(rot[:, 0])
            n = [[tuple(float(c) for c in r @ np.asarray(nv)) for nv in f] for f in m.normals]
        uv = None if m.chart_uv is None else [None if f is None else [(a * K, b * K) for a, b in f] for f in m.chart_uv]
        out.append(MeshPart([tuple(float(c) for c in p) for p in v], m.faces, m.mat, n, m.charts, uv, m.chart_edge))
    return out


def build(upright=False):
    """手に持つ向き（_hold）の盾。upright=True で盾の座標のまま（アイコン用）。"""
    from core import Model
    rot, off, grip = _hold()
    m = Model()
    items = parts(grip)
    if upright:
        items = [c.scaled(K) for c in items]
    else:
        items = _transform(items, rot, off)
    m.bone("root", None, (0, 0, 0))
    m.bone("shield", "root", (0, 0, 0), items)
    m.bone("thirdperson_hand", None, (0, 0, 0))                       # 手持ちの基準点（RiotShieldRenderer が手に合わせる）
    if not upright:
        m.icon_model = lambda: build(upright=True)[0]
        m.icon_view = (160, 12)                                       # 前から少し斜めに
    return m, {"riot_shield": items}
