package net.r0319.cordite.network;

import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.r0319.cordite.Cordite;

/** クライアント→サーバー: 手持ち銃のリロード要求（ペイロードは空）。 */
public record ReloadPayload() implements CustomPacketPayload {
    public static final ReloadPayload INSTANCE = new ReloadPayload();

    public static final Type<ReloadPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "reload"));

    public static final StreamCodec<io.netty.buffer.ByteBuf, ReloadPayload> CODEC =
            StreamCodec.unit(INSTANCE);

    @Override
    public Type<ReloadPayload> type() {
        return TYPE;
    }
}
