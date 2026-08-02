package net.r0319.cordite.combat;

import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.r0319.cordite.gunpack.GunDefinition;

/**
 * 軽量な弾丸トラッカー（Entityを使わない）。サーバーtickごとに弾速ぶんだけ前進し、
 * 移動区間をレイキャストして命中判定する（docs/design/00-architecture.md の「軽量トラッカー」方式）。
 * 命中/射程到達で {@link #isDead()} になる。
 *
 * <p><b>見た目は持たない</b>。曳光弾の表示は発射時に1発1パケットだけ配って
 * クライアントが描く（{@link net.r0319.cordite.network.TracerPayload} /
 * {@link net.r0319.cordite.client.render.TracerRenderer}）。以前はここから弾道上へ
 * パーティクルを撒いていたが、1発あたり数十パケット飛ぶうえ表示もtick単位の点列にしかならなかった。</p>
 */
public class GunProjectile {
    /** 当たり判定の膨らみ。 */
    private static final double HIT_INFLATE = 0.25;
    /** 安全のための最大生存tick。 */
    private static final int MAX_TICKS = 100;
    /** 着弾時に飛び散るブロック破片の数と勢い。🟡仮（見た目の調整値）。 */
    private static final int IMPACT_DEBRIS_COUNT = 8;
    private static final double IMPACT_DEBRIS_SPEED = 0.08;
    /** エンティティ命中時の粒子数。🟡仮。 */
    private static final int IMPACT_HIT_COUNT = 6;

    private final ServerLevel level;
    private final Player owner;
    private final GunDefinition props;
    private final Vec3 origin;
    private final Vec3 velocity; // blocks/tick
    private Vec3 pos;
    private double traveled;
    private int age;
    private boolean dead;

    public GunProjectile(ServerLevel level, Player owner, GunDefinition props, Vec3 origin, Vec3 direction) {
        this.level = level;
        this.owner = owner;
        this.props = props;
        this.origin = origin;
        this.pos = origin;
        this.velocity = direction.normalize().scale(props.muzzleVelocity() / 20.0);
    }

    public boolean isDead() {
        return dead;
    }

    /** 1tick前進させて命中判定・トレイル描画を行う。 */
    public void tick() {
        if (dead) {
            return;
        }
        Vec3 start = pos;
        Vec3 next = start.add(velocity);

        // ブロック遮蔽
        BlockHitResult block = level.clip(new ClipContext(
                start, next, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, owner));
        Vec3 end = block.getType() != HitResult.Type.MISS ? block.getLocation() : next;

        // エンティティ命中
        AABB search = new AABB(start, end).inflate(HIT_INFLATE);
        EntityHitResult hit = ProjectileUtil.getEntityHitResult(
                level, owner, start, end, search,
                e -> e != owner && e.isAlive() && e.isPickable() && !e.isSpectator());

        if (hit != null) {
            applyDamage(hit.getEntity(), hit.getLocation());
            spawnEntityImpact(hit.getLocation());
            dead = true;
            return;
        }
        if (block.getType() != HitResult.Type.MISS) {
            spawnBlockImpact(block);
            dead = true;
            return;
        }

        pos = next;
        traveled += velocity.length();
        age++;
        if (traveled >= props.effectiveRange() || age >= MAX_TICKS) {
            dead = true;
        }
    }

    private void applyDamage(Entity target, Vec3 hitPos) {
        float dmg = computeDamage(origin.distanceTo(hitPos), hitPos, target);
        // 連射で命中が無効化されないよう無敵時間をリセット（銃は毎発判定）
        if (target instanceof LivingEntity living) {
            living.invulnerableTime = 0;
        }
        target.hurt(level.damageSources().playerAttack(owner), dmg);
    }

    /** ダメージ計算式（docs/specs/02-guns.md）: 基礎 × 距離係数 × 部位倍率。防具軽減は後続。 */
    private float computeDamage(double dist, Vec3 hitPos, Entity target) {
        double falloffStart = props.falloffStart();
        double range = props.effectiveRange();
        double distFactor;
        if (dist <= falloffStart) {
            distFactor = 1.0;
        } else if (dist >= range) {
            distFactor = 0.5;
        } else {
            distFactor = 1.0 - 0.5 * (dist - falloffStart) / (range - falloffStart);
        }

        // 部位倍率（仮）: 頭 2.0 / 胴 1.0 / 手足 0.75
        double partFactor = 1.0;
        double relY = hitPos.y - target.getY();
        double height = target.getBbHeight();
        if (relY >= height * 0.85) {
            partFactor = 2.0;
        } else if (relY <= height * 0.35) {
            partFactor = 0.75;
        }

        return (float) (props.baseDamage() * distFactor * partFactor);
    }

    /**
     * ブロックへの着弾エフェクト（当たった場所の破片＋煙）。
     *
     * <p>弾道のトレイルと違い<b>着弾の1点で1回だけ</b>撒くので、サーバーからの{@code sendParticles}で
     * 十分軽い（弾道全体に撒いていた頃の「1発で数十パケット」にはならない）。周囲のプレイヤーにも
     * 見えるため、着弾点はここで出すのが素直（曳光弾のように専用パケットを作る必要がない）。</p>
     */
    private void spawnBlockImpact(BlockHitResult hit) {
        Vec3 point = hit.getLocation();
        BlockState state = level.getBlockState(hit.getBlockPos());
        if (!state.isAir()) {
            // 当たった面から少し手前に出さないと、破片がブロックの内側に埋まって見えない
            Vec3 offset = point.add(Vec3.atLowerCornerOf(hit.getDirection().getNormal()).scale(0.1));
            level.sendParticles(new BlockParticleOption(ParticleTypes.BLOCK, state),
                    offset.x, offset.y, offset.z, IMPACT_DEBRIS_COUNT, 0.0, 0.0, 0.0, IMPACT_DEBRIS_SPEED);
            level.sendParticles(ParticleTypes.SMOKE, offset.x, offset.y, offset.z, 1, 0.0, 0.0, 0.0, 0.0);
        }
    }

    /** エンティティへの着弾エフェクト（バニラのダメージ表示に加える小さな血飛沫代わり）。 */
    private void spawnEntityImpact(Vec3 point) {
        level.sendParticles(ParticleTypes.CRIT, point.x, point.y, point.z, IMPACT_HIT_COUNT, 0.1, 0.1, 0.1, 0.0);
    }
}
