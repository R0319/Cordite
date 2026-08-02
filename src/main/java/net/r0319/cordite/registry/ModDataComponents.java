package net.r0319.cordite.registry;

import com.mojang.serialization.Codec;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.FireMode;

/**
 * 銃の可変状態を保持する Data Component 群（docs/design/00-architecture.md 参照）。
 * 銃IDは {@link #GUN_ID} に保持し、基礎性能などの不変値は gunpack の定義側で持つ。
 */
public final class ModDataComponents {
    private ModDataComponents() {}

    public static final DeferredRegister<DataComponentType<?>> COMPONENTS =
            DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, Cordite.MODID);

    /** このスタックが参照する gunpack 定義のID。 */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<ResourceLocation>> GUN_ID =
            COMPONENTS.register("gun_id", () -> DataComponentType.<ResourceLocation>builder()
                    .persistent(ResourceLocation.CODEC)
                    .networkSynchronized(ResourceLocation.STREAM_CODEC)
                    .build());

    /** 現在のマガジン残弾。未設定の場合は gunpack 定義上の満タン扱い。 */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> MAGAZINE_AMMO =
            COMPONENTS.register("magazine_ammo", () -> DataComponentType.<Integer>builder()
                    .persistent(Codec.INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());

    /**
     * 現在の発射モード。未設定の場合は銃の既定モード扱い。
     * クライアントHUD表示のため networkSynchronized。
     *
     * <p>永続化は enum の並び順に依存しない name ベース（{@link FireMode#CODEC}）。
     * ordinal で保存すると将来 {@code FireMode} に値を追加・並べ替えた際、
     * 既存セーブの銃が別モードに化けるため。</p>
     */
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<FireMode>> FIRE_MODE =
            COMPONENTS.register("fire_mode", () -> DataComponentType.<FireMode>builder()
                    .persistent(FireMode.CODEC)
                    .networkSynchronized(FireMode.STREAM_CODEC)
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
