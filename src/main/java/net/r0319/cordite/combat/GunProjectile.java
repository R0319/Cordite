package net.r0319.cordite.combat;

import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.r0319.cordite.gunpack.GunDefinition;

import java.util.Optional;

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
    /**
     * 移動区間の周囲から命中候補のエンティティを集めるときの探索範囲の膨らみ。
     * 判定そのものではなく「候補集め」の範囲なので、{@link #ENTITY_HIT_INFLATE} 以上であればよい。
     */
    private static final double SEARCH_INFLATE = 0.3;
    /**
     * エンティティの当たり判定（バウンディングボックス）を各面に膨らませる量[ブロック]。🟡仮。
     *
     * <p>以前は {@code ProjectileUtil.getEntityHitResult}（6引数版）に任せていたが、あれは内部で各面を
     * 0.3 膨らませたうえ、<b>命中位置を持たない</b> {@code EntityHitResult} を返す
     * （{@code getLocation()} はエンティティの足元座標になる）。そのため部位判定が常に「足元＝手足」と
     * なり、ヘッドショットが一度も成立していなかった。ここでは自前で判定して<b>実際の交点</b>を使う。</p>
     *
     * <p>値は旧実装と同じ 0.3 を据え置いている。プレイヤーの幅 0.6 に対して各面 0.3 は「見た目の倍の幅に
     * 当たる」かなり甘い判定なので、PvP の手触りとして厳しくするなら 0.1 前後まで下げる余地がある
     * （矢の判定はバニラも 0.3 で、銃に流用するには大きい）。</p>
     */
    private static final double ENTITY_HIT_INFLATE = 0.3;
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

        // エンティティ命中（ブロックに遮られた場合は、その手前の区間だけを判定する）
        EntityHitResult hit = findEntityHit(start, end);

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

    /**
     * 区間 {@code start}→{@code end} 上で最初に当たるエンティティと<b>その交点</b>を返す。無ければ null。
     *
     * <p>{@code ProjectileUtil.getEntityHitResult} を使わない理由は {@link #ENTITY_HIT_INFLATE} のコメント参照
     * （交点が取れず部位判定が壊れる）。候補はバニラと同じく {@code level.getEntities} で区間周辺から集め、
     * 各エンティティの膨らませた箱と区間の交点のうち、始点に最も近いものを採る。射手自身と観戦者は除く。</p>
     */
    private EntityHitResult findEntityHit(Vec3 start, Vec3 end) {
        AABB search = new AABB(start, end).inflate(SEARCH_INFLATE);
        Entity closest = null;
        Vec3 closestPoint = null;
        double closestDistSq = Double.MAX_VALUE;
        for (Entity candidate : level.getEntities(owner, search,
                e -> e != owner && e.isAlive() && e.isPickable() && !e.isSpectator())) {
            AABB box = candidate.getBoundingBox().inflate(ENTITY_HIT_INFLATE);
            // 密着して撃った場合は始点がすでに箱の中にある。AABB#clip は外から入る面しか検出しないため
            // そのままだと至近距離だけ当たらない（バニラの矢にも同じ癖がある）。始点を交点とみなす。
            Optional<Vec3> point = box.contains(start) ? Optional.of(start) : box.clip(start, end);
            if (point.isEmpty()) {
                continue;
            }
            double distSq = start.distanceToSqr(point.get());
            if (distSq < closestDistSq) {
                closest = candidate;
                closestPoint = point.get();
                closestDistSq = distSq;
            }
        }
        return closest == null ? null : new EntityHitResult(closest, closestPoint);
    }

    private void applyDamage(Entity target, Vec3 hitPos) {
        float dmg = computeDamage(origin.distanceTo(hitPos), hitPos, target);
        // 連射で命中が無効化されないよう無敵時間をリセット（銃は毎発判定）
        if (target instanceof LivingEntity living) {
            living.invulnerableTime = 0;
        }
        target.hurt(level.damageSources().playerAttack(owner), dmg);
    }

    /**
     * ダメージ計算式（docs/specs/02-guns.md）: 基礎 × 距離係数 × 部位倍率。防具軽減は後続。
     *
     * <p>部位は命中点の高さで判定するため、{@code hitPos} は<b>実際の交点</b>でなければならない
     * （{@link #findEntityHit}）。足元座標を渡すと常に手足扱いになる。</p>
     */
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
