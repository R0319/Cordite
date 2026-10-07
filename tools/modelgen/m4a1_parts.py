"""
M4A1（パーツ組立版）: ar15_parts の実寸パーツを、コードが参照するボーンへ割り当てて組み立てる。
単位は部品側が mm、ここで px（÷24）へ変換する。
build(P=ar15_mesh) とすると、丸・曲線の部品がメッシュ版に置き換わる（組み立ては共通）。
"""
import numpy as np

import ar15_parts as P
from core import Model, _rot_raw
from rig import add_locators

K = 1.0 / P.MM_PER_PX


def px(v):
    return tuple(c * K for c in v)


def build(P=P) -> tuple[Model, dict]:
    l = P.L
    b = l.bore_y
    m = Model()
    parts: dict[str, list] = {}

    def add(bone, parent, pivot_mm, part_name=None, cubes_mm=()):
        cubes = [c.scaled(K) for c in cubes_mm]
        if part_name:
            parts[part_name] = cubes
        return m.bone(bone, parent, px(pivot_mm), cubes)

    m.bone("root", None, (0, 0, 0))
    add("receiver", "root", (0, b, 0), "upper_receiver", P.upper_receiver())
    add("lower_receiver", "receiver", (0, b + l.lower_bottom, 0), "lower_receiver", P.lower_receiver())
    gp, _ = P.grip_frame()
    add("pistol_grip", "receiver", gp, "pistol_grip", P.pistol_grip())
    add("buffer_tube", "receiver", (0, b - 4, 62), "buffer_tube", P.buffer_tube())
    add("rear_sight", "receiver", (0, l.rail_top_y, 0), "rear_sight", P.rear_sight())

    add("rail_top", "root", (0, l.rail_top_y, l.upper_rear_z - 2), "rail", P.rail())
    add("handguard", "root", (0, b, l.handguard_rear_z), "handguard", P.handguard())

    add("barrel", "root", (0, b, l.bolt_face_z), "barrel", P.barrel())
    add("chamber", "barrel", (0, b, l.bolt_face_z), "barrel_extension", P.barrel_extension())
    add("gas_block", "barrel", (0, b, l.gas_z), "gas_block", P.gas_block())
    add("front_sight_base", "barrel", (0, b, l.gas_z), "front_sight_base", P.front_sight_base())
    add("front_sight_post", "front_sight_base", (0, b + l.sight_h, l.gas_z), "front_sight_post",
        P.front_sight_post())
    add("muzzle", "root", (0, b, l.muzzle_z), "flash_hider_a2", P.flash_hider_a2())

    add("bolt", "root", (0, b, -70), "bolt_carrier", P.bolt_carrier())
    add("charging_handle", "root", (0, b + 12, l.upper_rear_z), "charging_handle", P.charging_handle())
    add("trigger", "root", (0, b + l.lower_bottom, -2), "trigger", P.trigger())

    add("magazin", "root", (0, b - 95, -85), "magazine_stanag", P.magazine_stanag())
    case, bullet = P.cartridge_556(z_tip=-112, y=b - 29)
    add("mag_ammo", "magazin", (0, b - 29, -83), None, case + bullet)

    case, bullet = P.cartridge_556(z_tip=-123, y=b)   # 薬室位置（排莢クリップの起点）
    add("ammo", "root", (0, b, -80), None, case)
    add("bullet", "ammo", (0, b, -117), None, bullet)

    add("stock", "root", (0, b, 180), "stock_m4", P.stock_m4())

    # グリップ中心（回転後）＝三人称で握る位置
    piv, rot = P.grip_frame()
    local = np.array([0, -46, 23])
    center = _rot_raw(rot) @ local + np.array(piv)
    add_locators(
        m,
        muzzle=px((0, b, l.muzzle_z - 57)),
        sight_line_y=(b + l.sight_h) * K,
        rear_sight_z=12 * K,               # アパーチャー板の位置（rear_sight の z+12）
        grip_center=px(tuple(center)),
    )
    return m, parts
