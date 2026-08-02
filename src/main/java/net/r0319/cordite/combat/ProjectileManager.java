package net.r0319.cordite.combat;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.network.PacketDistributor;
import net.r0319.cordite.gunpack.GunDefinition;
import net.r0319.cordite.network.TracerPayload;

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

    /**
     * 銃1回の発射（ペレット数ぶんの弾丸を生成）。サーバー側で呼ぶ。
     *
     * <p>あわせて曳光弾（見た目だけ）を撃った本人と周囲のプレイヤーへ配る。弾道の計算・命中判定は
     * ここで作る{@link GunProjectile}がサーバー側で行い、クライアントへ渡すのは
     * 「どこから・どちらへ・どのくらいの速さで光が飛ぶか」だけ（{@link TracerPayload}）。</p>
     */
    public static void fire(ServerLevel level, Player player, GunDefinition props, boolean aiming) {
        Vec3 origin = player.getEyePosition();
        // 腰だめは狙点そのものがばらつく。ADS中はばらつかない（docs/design/recoil.md「③拡散」）。
        // 拡散量も乱数もサーバー側で決めるので、クライアントは発射方向を申告できない。
        Vec3 view = aiming
                ? player.getViewVector(1.0f)
                : applyConeSpread(level, player.getViewVector(1.0f), props.hipSpreadDeg());

        for (int i = 0; i < props.pelletCount(); i++) {
            Vec3 dir = props.pelletCount() == 1 ? view : applySpread(level, view);
            ACTIVE.add(new GunProjectile(level, player, props, origin, dir));
            PacketDistributor.sendToPlayersTrackingEntityAndSelf(player, new TracerPayload(
                    origin, dir, (float) (props.muzzleVelocity() / 20.0), (float) props.effectiveRange()));
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

    /**
     * 指定方向を頂点角{@code maxAngleDeg}の円錐内へランダムにずらす（腰だめの拡散）。
     *
     * <p>角度に {@code sqrt(random)} を掛けているのは、円錐の断面を<b>面積で一様</b>にするため。
     * そのまま一様乱数を角度に使うと中心付近に着弾が偏り、拡散しているように見えない。</p>
     */
    private static Vec3 applyConeSpread(ServerLevel level, Vec3 direction, float maxAngleDeg) {
        if (maxAngleDeg <= 0f) {
            return direction;
        }
        var r = level.random;
        double angle = Math.toRadians(maxAngleDeg) * Math.sqrt(r.nextDouble());
        double roll = r.nextDouble() * Math.PI * 2.0;

        // 進行方向に直交する2軸（真上/真下を向いているときは別の基準軸を使う）
        Vec3 reference = Math.abs(direction.y) > 0.99 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
        Vec3 right = direction.cross(reference).normalize();
        Vec3 up = right.cross(direction).normalize();

        double tan = Math.tan(angle);
        return direction
                .add(right.scale(Math.cos(roll) * tan))
                .add(up.scale(Math.sin(roll) * tan))
                .normalize();
    }

    private static Vec3 applySpread(ServerLevel level, Vec3 view) {
        var r = level.random;
        return view.add(
                (r.nextDouble() - 0.5) * PELLET_SPREAD,
                (r.nextDouble() - 0.5) * PELLET_SPREAD,
                (r.nextDouble() - 0.5) * PELLET_SPREAD).normalize();
    }
}
