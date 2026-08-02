package net.r0319.cordite.network;

import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.r0319.cordite.Cordite;

/**
 * サーバー→クライアント: 1発撃った、という<b>純粋な演出トリガー</b>。
 * 撃った本人にだけ送り、発射アニメーションの再生開始に使う。
 *
 * <p>{@code emptyAfterShot} は「この1発で撃ち切ったか（ホールドオープンする銃で残弾0になったか）」。
 * 撃ち切り専用の発射アニメーション（{@code fire_empty}、スライドが後退したまま終わる）へ切り替えるために
 * サーバーが判定して載せる。<b>クライアント側で残弾コンポーネントから判定することはできない</b>——
 * スロット同期がこのパケットより遅れて届くため、撃った瞬間はまだ残弾が減る前の値に見える
 * （このパケットが作られた理由と同じ問題）。</p>
 *
 * <p><b>それ以外のゲームプレイ情報は一切積まない</b>（ダメージ・方向・命中結果はサーバーが持ったまま）。
 * サーバー→クライアントの片方向なので、これを受けてもクライアントの申告を信用することにはならず、
 * [00-architecture.md](docs/design/00-architecture.md) のサーバー権威方針と矛盾しない。</p>
 *
 * <p><b>なぜ必要か</b>: 以前は残弾データコンポーネントの同期差分で発射を検知していたが
 * （{@link net.r0319.cordite.client.anim.ClientGunAnimationTracker}）、スロット同期は発射音の
 * 配信より遅れて届くため、<b>反動アニメーションが銃声から遅れて再生されていた</b>。
 * また同期が届く前に複数発撃たれると減少がまとめて届き、フルオートで1発ぶんしか再生されなかった。
 * このペイロードは発射音と同じtickに送られるので、アニメーションが銃声と揃い、1発ごとに再生される。</p>
 *
 * <p><b>発射音はこれに載せない</b>: 銃声は周囲のプレイヤーにも聞こえる必要があるため、従来どおり
 * サーバーの {@code playSound} で配信する（{@code GunItem#tryFire}）。詳細は
 * docs/design/animation-system.md の「役割分担（音をどちらで鳴らすか）」。</p>
 */
public record GunFiredPayload(boolean emptyAfterShot) implements CustomPacketPayload {

    public static final Type<GunFiredPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "gun_fired"));

    public static final StreamCodec<io.netty.buffer.ByteBuf, GunFiredPayload> CODEC = StreamCodec.composite(
            net.minecraft.network.codec.ByteBufCodecs.BOOL, GunFiredPayload::emptyAfterShot,
            GunFiredPayload::new);

    @Override
    public Type<GunFiredPayload> type() {
        return TYPE;
    }
}
