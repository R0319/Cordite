package net.r0319.cordite.network;

import com.mojang.serialization.Codec;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.gunpack.GunDefinition;

import java.util.Map;

/** サーバー→クライアント: 現在有効な gunpack 定義の全件同期。 */
public record SyncGunDefinitionsPayload(Map<ResourceLocation, GunDefinition> definitions)
        implements CustomPacketPayload {
    public static final Type<SyncGunDefinitionsPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "sync_gun_definitions"));

    private static final Codec<Map<ResourceLocation, GunDefinition>> DEFINITIONS_CODEC =
            Codec.unboundedMap(ResourceLocation.CODEC, GunDefinition.CODEC);
    private static final StreamCodec<RegistryFriendlyByteBuf, Map<ResourceLocation, GunDefinition>>
            DEFINITIONS_STREAM_CODEC = ByteBufCodecs.fromCodecWithRegistries(DEFINITIONS_CODEC);

    public static final StreamCodec<RegistryFriendlyByteBuf, SyncGunDefinitionsPayload> CODEC =
            StreamCodec.composite(DEFINITIONS_STREAM_CODEC, SyncGunDefinitionsPayload::definitions,
                    SyncGunDefinitionsPayload::new);

    public SyncGunDefinitionsPayload {
        definitions = Map.copyOf(definitions);
    }

    @Override
    public Type<SyncGunDefinitionsPayload> type() {
        return TYPE;
    }
}
