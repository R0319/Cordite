package net.r0319.cordite.network;

import io.netty.buffer.ByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.r0319.cordite.Cordite;

/**
 * クライアント→サーバー: 射撃トリガーの押下状態（押した/離した）を通知する。
 * サーバーはこの状態を保持し、サーバーtickで発射モードに応じて発射する。
 */
public record SetTriggerPayload(boolean pressed) implements CustomPacketPayload {
    public static final Type<SetTriggerPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "set_trigger"));

    public static final StreamCodec<ByteBuf, SetTriggerPayload> CODEC =
            StreamCodec.composite(ByteBufCodecs.BOOL, SetTriggerPayload::pressed, SetTriggerPayload::new);

    @Override
    public Type<SetTriggerPayload> type() {
        return TYPE;
    }
}
