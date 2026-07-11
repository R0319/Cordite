package net.r0319.cordite.combat;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.r0319.cordite.item.gun.GunProperties;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * アクティブな弾丸トラッカーの管理。サーバーtickごとに全弾を前進させ、命中/射程で除去する。
 */
public final class ProjectileManager {
    private ProjectileManager() {}

    /** ショットガンのペレット拡散量。 */
    private static final double PELLET_SPREAD = 0.08;

    private static final List<GunProjectile> ACTIVE = new ArrayList<>();

    /** 銃1回の発射（ペレット数ぶんの弾丸を生成）。サーバー側で呼ぶ。 */
    public static void fire(ServerLevel level, Player player, GunProperties props) {
        Vec3 origin = player.getEyePosition();
        Vec3 view = player.getViewVector(1.0f);

        for (int i = 0; i < props.pelletCount(); i++) {
            Vec3 dir = props.pelletCount() == 1 ? view : applySpread(level, view);
            ACTIVE.add(new GunProjectile(level, player, props, origin, dir));
        }
    }

    /** 毎サーバーtickで呼ぶ。 */
    public static void tick() {
        if (ACTIVE.isEmpty()) {
            return;
        }
        Iterator<GunProjectile> it = ACTIVE.iterator();
        while (it.hasNext()) {
            GunProjectile p = it.next();
            p.tick();
            if (p.isDead()) {
                it.remove();
            }
        }
    }

    public static void clear() {
        ACTIVE.clear();
    }

    private static Vec3 applySpread(ServerLevel level, Vec3 view) {
        var r = level.random;
        return view.add(
                (r.nextDouble() - 0.5) * PELLET_SPREAD,
                (r.nextDouble() - 0.5) * PELLET_SPREAD,
                (r.nextDouble() - 0.5) * PELLET_SPREAD).normalize();
    }
}
