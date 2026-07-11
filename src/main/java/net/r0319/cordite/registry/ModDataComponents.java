package net.r0319.cordite.registry;

import com.mojang.serialization.Codec;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;

/**
 * 銃の可変状態を保持する Data Component 群（docs/design/00-architecture.md 参照）。
 * 銃ID・基礎性能などの不変値はここには入れない（{@code GunProperties} 側で持つ）。
 */
public final class ModDataComponents {
    private ModDataComponents() {}

    public static final DeferredRegister<DataComponentType<?>> COMPONENTS =
            DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, Cordite.MODID);

    /** 現在のマガジン残弾。未設定の場合は満タン扱い（{@code GunProperties.magSize}）。 */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> MAGAZINE_AMMO =
            COMPONENTS.register("magazine_ammo", () -> DataComponentType.<Integer>builder()
                    .persistent(Codec.INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());

    /**
     * 現在の発射モード（{@code FireMode.ordinal()}）。未設定の場合は銃の既定モード扱い。
     * クライアントHUD表示のため networkSynchronized。
     */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> FIRE_MODE =
            COMPONENTS.register("fire_mode", () -> DataComponentType.<Integer>builder()
                    .persistent(Codec.INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());

    /**
     * 薬室（チャンバー）に弾があるか。クローズドボルト銃のみ意味を持つ（オープンボルトは常に空扱い）。
     * 未設定の場合は装填済み扱い（true）。
     */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Boolean>> CHAMBERED =
            COMPONENTS.register("chambered", () -> DataComponentType.<Boolean>builder()
                    .persistent(Codec.BOOL)
                    .networkSynchronized(ByteBufCodecs.BOOL)
                    .build());
}
