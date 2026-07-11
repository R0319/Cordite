package net.r0319.cordite.combat;

import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.r0319.cordite.item.gun.GunProperties;
import org.joml.Vector3f;

/**
 * 軽量な弾丸トラッカー（Entityを使わない）。サーバーtickごとに弾速ぶんだけ前進し、
 * 移動区間をレイキャストして命中判定する（docs/design/00-architecture.md の「軽量トラッカー」方式）。
 *
 * <p>全弾に曳光弾トレイルを付けて弾道を可視化する。命中/射程到達で {@link #isDead()} になる。</p>
 */
public class GunProjectile {
    /** 曳光弾の色（オレンジ）。 */
    private static final Vector3f TRACER_COLOR = new Vector3f(1.0f, 0.55f, 0.15f);
    private static final DustParticleOptions TRACER = new DustParticleOptions(TRACER_COLOR, 0.6f);
    /** トレイル粒子の間隔（blocks）。 */
    private static final double TRACER_STEP = 0.5;
    /** 当たり判定の膨らみ。 */
    private static final double HIT_INFLATE = 0.25;
    /** 安全のための最大生存tick。 */
    private static final int MAX_TICKS = 100;

    private final ServerLevel level;
    private final Player owner;
    private final GunProperties props;
    private final Vec3 origin;
    private final Vec3 velocity; // blocks/tick
    private Vec3 pos;
    private double traveled;
    private int age;
    private boolean dead;

    public GunProjectile(ServerLevel level, Player owner, GunProperties props, Vec3 origin, Vec3 direction) {
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
            Vec3 hp = hit.getLocation();
            drawTracer(start, hp);
            applyDamage(hit.getEntity(), hp);
            dead = true;
            return;
        }
        if (block.getType() != HitResult.Type.MISS) {
            drawTracer(start, end);
            dead = true;
            return;
        }

        drawTracer(start, next);
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

    private void drawTracer(Vec3 from, Vec3 to) {
        double dist = from.distanceTo(to);
        if (dist < 1.0e-4) {
            return;
        }
        Vec3 dir = to.subtract(from).scale(1.0 / dist);
        for (double d = 0; d < dist; d += TRACER_STEP) {
            Vec3 p = from.add(dir.scale(d));
            level.sendParticles(TRACER, p.x, p.y, p.z, 1, 0, 0, 0, 0);
        }
    }
}
