package net.r0319.cordite.network;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import net.r0319.cordite.Cordite;

/**
 * サーバー→クライアント: 曳光弾1本ぶんの<b>見た目だけ</b>の情報。撃った本人と周囲のプレイヤーへ送る。
 *
 * <p>弾そのものはサーバー側の軽量トラッカー（{@link net.r0319.cordite.combat.GunProjectile}）が
 * 持ったままで、命中判定もダメージもサーバーが行う。このペイロードはクライアントが
 * 「光る線を飛ばす」ためだけに使い、受け取った値がゲームプレイに影響することはない。
 * サーバー→クライアントの片方向なので、[00-architecture.md](docs/design/00-architecture.md) の
 * サーバー権威方針と矛盾しない。</p>
 *
 * <p><b>なぜパケットにしたか</b>: 以前はサーバーが弾道上に0.5ブロック間隔でパーティクルを
 * {@code sendParticles}していたが、1発あたり数十個のパーティクルパケットが飛ぶうえ、
 * 表示は「tick単位で並んだ点」にしかならず滑らかに動かなかった。発射時に1発1パケットだけ送り、
 * あとはクライアントが弾速から位置を補間するほうが軽く、かつフレーム単位で滑らかに飛ぶ。</p>
 *
 * @param origin      発射位置（射手の目の位置）
 * @param direction   進行方向（正規化済み）
 * @param speed       弾速[ブロック/tick]
 * @param maxDistance この弾が飛びうる最大距離[ブロック]（有効射程）
 */
public record TracerPayload(Vec3 origin, Vec3 direction, float speed, float maxDistance)
        implements CustomPacketPayload {

    public static final Type<TracerPayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "tracer"));

    /** 方向は単位ベクトルなのでfloatで十分（位置だけdoubleで送る）。 */
    private static final StreamCodec<RegistryFriendlyByteBuf, Vec3> VEC3_DOUBLE = StreamCodec.of(
            (buf, vec) -> {
                buf.writeDouble(vec.x);
                buf.writeDouble(vec.y);
                buf.writeDouble(vec.z);
            },
            buf -> new Vec3(buf.readDouble(), buf.readDouble(), buf.readDouble()));

    private static final StreamCodec<RegistryFriendlyByteBuf, Vec3> VEC3_FLOAT = StreamCodec.of(
            (buf, vec) -> {
                buf.writeFloat((float) vec.x);
                buf.writeFloat((float) vec.y);
                buf.writeFloat((float) vec.z);
            },
            buf -> new Vec3(buf.readFloat(), buf.readFloat(), buf.readFloat()));

    public static final StreamCodec<RegistryFriendlyByteBuf, TracerPayload> CODEC = StreamCodec.composite(
            VEC3_DOUBLE, TracerPayload::origin,
            VEC3_FLOAT, TracerPayload::direction,
            ByteBufCodecs.FLOAT, TracerPayload::speed,
            ByteBufCodecs.FLOAT, TracerPayload::maxDistance,
            TracerPayload::new);

    @Override
    public Type<TracerPayload> type() {
        return TYPE;
    }
}
