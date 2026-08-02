package net.r0319.cordite.network;

import io.netty.buffer.ByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.r0319.cordite.Cordite;

/**
 * クライアント→サーバー: ADS（サイトを覗いているか）の状態を通知する。
 * {@link SetTriggerPayload} と同じく<b>状態が変わったときだけ</b>送る。
 *
 * <p>ADSはこれまでクライアント側の見た目だけの状態だったが、<b>腰だめ時の弾の拡散</b>
 * （docs/design/recoil.md の「③拡散」）はサーバー権威で行う必要があるため、サーバーにも状態を持たせる。
 * 送るのはbool 1つだけで、拡散量も発射方向もサーバーが算出する（クライアントに申告させない）。</p>
 *
 * <p>不正に「常にADS中」と申告すれば拡散を避けられるが、その場合ADSの<b>デメリット</b>
 * （移動速度低下・視野の制限など、今後実装するもの）も同時に負うことになるため、送信内容としては
 * 対称。より厳密にするならサーバー側で「ADS開始からの経過時間」を要求する余地がある（後続作業）。</p>
 */
public record SetAdsPayload(boolean aiming) implements CustomPacketPayload {
    public static final Type<SetAdsPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "set_ads"));

    public static final StreamCodec<ByteBuf, SetAdsPayload> CODEC =
            StreamCodec.composite(ByteBufCodecs.BOOL, SetAdsPayload::aiming, SetAdsPayload::new);

    @Override
    public Type<SetAdsPayload> type() {
        return TYPE;
    }
}
