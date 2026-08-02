package net.r0319.cordite.client.render;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.List;

/**
 * 飛行中の曳光弾（見た目だけ）の保持。{@link net.r0319.cordite.network.TracerPayload} の受信で1本積まれ、
 * {@link TracerRenderer} が毎フレーム位置を補間して描く。
 *
 * <p><b>当たり判定は持たない</b>。ダメージ・命中はサーバー側の
 * {@link net.r0319.cordite.combat.GunProjectile} が担当し、こちらは「どこで止まって見えるか」だけを
 * 決める。壁の向こうまで光が突き抜けて見えないよう、生成時に<b>1回だけ</b>ブロックへレイキャストして
 * 停止距離を求めておく（毎tickのレイキャストは行わない）。エンティティは貫通して見えるが、
 * 弾速が速いため1〜2フレームの差でしかない。</p>
 *
 * <p>Minecraftのクライアント専用クラスを参照しない（{@link net.r0319.cordite.network.ModNetwork} の
 * ハンドラから触るため。{@link Level}/{@link Vec3} は共通クラス）。</p>
 */
public final class TracerState {
    private TracerState() {}

    /**
     * 同時に表示できる曳光弾の上限。溢れたら最も古いものから捨てる。
     * LMGの900RPM級でも1本の寿命は1秒未満なので、この数で頭打ちになることは通常ない。
     */
    private static final int CAPACITY = 256;

    /**
     * @param origin        発射位置
     * @param direction     進行方向（正規化済み）
     * @param speed         弾速[ブロック/tick]
     * @param stopDistance  ここまで進んだら消える距離[ブロック]（射程かブロック衝突点の近いほう）
     * @param startGameTime 発射tick
     */
    public record Tracer(Vec3 origin, Vec3 direction, float speed, double stopDistance, long startGameTime) {
        /** 発射からの経過tick（partialTick込み）に対する先端位置までの距離[ブロック]。 */
        public double traveled(long nowGameTime, float partialTick) {
            return speed * ((nowGameTime - startGameTime) + partialTick);
        }

        public boolean isFinished(long nowGameTime, float partialTick) {
            return traveled(nowGameTime, partialTick) >= stopDistance;
        }
    }

    private static final List<Tracer> ACTIVE = new ArrayList<>();

    /**
     * 曳光弾を1本追加する。停止距離はここでブロックへのレイキャストで確定させる。
     *
     * @param viewer レイキャストの基準にするエンティティ（ブロック形状の判定コンテキストに使われる。null可）
     */
    public static void spawn(Level level, Vec3 origin, Vec3 direction, float speed, float maxDistance,
                             Entity viewer) {
        Vec3 dir = direction.normalize();
        Vec3 end = origin.add(dir.scale(maxDistance));
        HitResult hit = level.clip(new ClipContext(
                origin, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, viewer));
        double stopDistance = hit.getType() == HitResult.Type.MISS
                ? maxDistance
                : origin.distanceTo(hit.getLocation());

        if (ACTIVE.size() >= CAPACITY) {
            ACTIVE.removeFirst();
        }
        ACTIVE.add(new Tracer(origin, dir, speed, stopDistance, level.getGameTime()));
    }

    /** 表示中の曳光弾（描画用。呼び出し側は変更しないこと）。 */
    public static List<Tracer> active() {
        return ACTIVE;
    }

    /** 飛び終わった曳光弾を捨てる（毎tick呼ぶ）。 */
    public static void prune(long nowGameTime) {
        ACTIVE.removeIf(t -> t.isFinished(nowGameTime, 0f));
    }

    /** すべて消す（ワールドを抜けた等）。 */
    public static void reset() {
        ACTIVE.clear();
    }
}
