package net.r0319.cordite.gunpack;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.Holder;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.util.ExtraCodecs;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.BoltType;
import net.r0319.cordite.item.gun.FireMode;

import java.util.List;
import java.util.Optional;

/**
 * gunpack JSON から読む、銃1丁ぶんの不変定義。
 *
 * <p>発射後の弾丸は、この不変オブジェクトへの参照をスナップショットとして保持できる。リロードで
 * 定義マップが差し替わっても、すでに発射済みの弾丸の弾道・ダメージは変化しない。</p>
 */
public record GunDefinition(
        Optional<Component> name,
        float baseDamage,
        double muzzleVelocity,
        double effectiveRange,
        double falloffStart,
        int rpm,
        float reloadSeconds,
        int magSize,
        int pelletCount,
        float recoilPitch,
        float recoilYaw,
        float hipSpreadDeg,
        List<FireMode> fireModes,
        BoltType boltType,
        boolean holdOpenOnEmpty,
        Holder<SoundEvent> fireSound,
        Optional<Float> fireSoundRange
) {
    private static final ResourceLocation DEFAULT_FIRE_SOUND =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "pistol_fire");
    /** 発射音のIDと任意の固定レンジを、JSON上では同じ階層の2フィールドとして扱う。 */
    private static final MapCodec<FireSound> FIRE_SOUND_CODEC = RecordCodecBuilder.mapCodec(instance -> instance.group(
            ResourceLocation.CODEC.optionalFieldOf("fire_sound", DEFAULT_FIRE_SOUND).forGetter(FireSound::id),
            Codec.FLOAT.optionalFieldOf("fire_sound_range").forGetter(FireSound::range)
    ).apply(instance, FireSound::new));

    /**
     * 正の値しか意味を持たない物理量用。0 や負を通すと弾が進まない（弾速0）・回復になる（負ダメージ）・
     * リロードが即完了する（0秒）といった壊れ方をするので、パース時点で弾いて WARN ログに出す。
     * 上限は「明らかな桁違い」だけを止める程度の緩い値。
     */
    private static final Codec<Double> POSITIVE_DOUBLE = Codec.doubleRange(Double.MIN_VALUE, 1.0e6);
    private static final Codec<Float> POSITIVE_FLOAT = Codec.floatRange(Float.MIN_VALUE, 1.0e6f);
    /** 0 を許す量（反動・拡散は 0 で「無し」を表せる）。負は意味を持たないので弾く。 */
    private static final Codec<Float> NON_NEGATIVE_FLOAT = Codec.floatRange(0f, 1.0e6f);

    /** JSON の全フィールドを検証しつつ読み書きする Codec。 */
    public static final Codec<GunDefinition> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            ComponentSerialization.CODEC.optionalFieldOf("name").forGetter(GunDefinition::name),
            POSITIVE_FLOAT.fieldOf("base_damage").forGetter(GunDefinition::baseDamage),
            POSITIVE_DOUBLE.optionalFieldOf("muzzle_velocity", 120.0).forGetter(GunDefinition::muzzleVelocity),
            POSITIVE_DOUBLE.optionalFieldOf("effective_range", 40.0).forGetter(GunDefinition::effectiveRange),
            POSITIVE_DOUBLE.optionalFieldOf("falloff_start", 20.0).forGetter(GunDefinition::falloffStart),
            Codec.intRange(1, 6000).fieldOf("rpm").forGetter(GunDefinition::rpm),
            POSITIVE_FLOAT.optionalFieldOf("reload_seconds", 2.0f).forGetter(GunDefinition::reloadSeconds),
            Codec.intRange(1, 999).fieldOf("mag_size").forGetter(GunDefinition::magSize),
            Codec.intRange(1, 64).optionalFieldOf("pellet_count", 1).forGetter(GunDefinition::pelletCount),
            NON_NEGATIVE_FLOAT.optionalFieldOf("recoil_pitch", 1.0f).forGetter(GunDefinition::recoilPitch),
            NON_NEGATIVE_FLOAT.optionalFieldOf("recoil_yaw", 0.3f).forGetter(GunDefinition::recoilYaw),
            NON_NEGATIVE_FLOAT.optionalFieldOf("hip_spread_deg", 2.0f).forGetter(GunDefinition::hipSpreadDeg),
            ExtraCodecs.nonEmptyList(FireMode.CODEC.listOf()).optionalFieldOf("fire_modes", List.of(FireMode.SINGLE))
                    .forGetter(GunDefinition::fireModes),
            BoltType.CODEC.optionalFieldOf("bolt_type", BoltType.CLOSED).forGetter(GunDefinition::boltType),
            Codec.BOOL.optionalFieldOf("hold_open_on_empty", false).forGetter(GunDefinition::holdOpenOnEmpty),
            FIRE_SOUND_CODEC.forGetter(definition ->
                    new FireSound(definition.fireSound().value().getLocation(), definition.fireSoundRange()))
    ).apply(instance, GunDefinition::create));

    /** record が外部から可変リストを受け取らないよう、防御的にコピーする。 */
    public GunDefinition {
        fireModes = List.copyOf(fireModes);
    }

    private static GunDefinition create(Optional<Component> name, float baseDamage, double muzzleVelocity,
                                        double effectiveRange, double falloffStart, int rpm, float reloadSeconds,
                                        int magSize, int pelletCount, float recoilPitch, float recoilYaw,
                                        float hipSpreadDeg, List<FireMode> fireModes, BoltType boltType,
                                        boolean holdOpenOnEmpty, FireSound fireSound) {
        SoundEvent sound = fireSound.range()
                .<SoundEvent>map(range -> SoundEvent.createFixedRangeEvent(fireSound.id(), range))
                .orElseGet(() -> SoundEvent.createVariableRangeEvent(fireSound.id()));
        return new GunDefinition(name, baseDamage, muzzleVelocity, effectiveRange, falloffStart, rpm, reloadSeconds,
                magSize, pelletCount, recoilPitch, recoilYaw, hipSpreadDeg, fireModes, boltType, holdOpenOnEmpty,
                Holder.direct(sound), fireSound.range());
    }

    /**
     * 発射間隔（tick、小数）。20tick/秒なので {@code 1200 / rpm}。
     * 整数に丸めない: 800rpm = 1.5tick のような銃は、丸めると 2tick（600rpm）に落ちてしまう。
     * 小数のまま {@link net.r0319.cordite.combat.GunFireManager.State#markShot} で積み上げて使う。
     */
    public double fireIntervalTicks() {
        return 1200.0 / rpm;
    }

    /** リロード時間（tick）。 */
    public int reloadTicks() {
        return Math.max(1, Math.round(reloadSeconds * 20f));
    }

    /** 既定の発射モード。 */
    public FireMode defaultMode() {
        return fireModes.get(0);
    }

    /** {@code current} の次のモード。未対応値は既定モードへ戻す。 */
    public FireMode nextMode(FireMode current) {
        int index = fireModes.indexOf(current);
        return index < 0 ? defaultMode() : fireModes.get((index + 1) % fireModes.size());
    }

    /** Codec の組み立て時だけ使う、JSON上の発射音表現。 */
    private record FireSound(ResourceLocation id, Optional<Float> range) {}
}
