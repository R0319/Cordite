package net.r0319.cordite.network;

import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.r0319.cordite.Cordite;

/** クライアント→サーバー: 手持ち銃の発射モードを次へ切り替える要求（ペイロードは空）。 */
public record CycleFireModePayload() implements CustomPacketPayload {
    public static final CycleFireModePayload INSTANCE = new CycleFireModePayload();

    public static final Type<CycleFireModePayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "cycle_fire_mode"));

    public static final StreamCodec<io.netty.buffer.ByteBuf, CycleFireModePayload> CODEC =
            StreamCodec.unit(INSTANCE);

    @Override
    public Type<CycleFireModePayload> type() {
        return TYPE;
    }
}
