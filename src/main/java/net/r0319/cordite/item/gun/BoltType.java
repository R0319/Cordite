package net.r0319.cordite.item.gun;

import com.mojang.serialization.Codec;
import net.minecraft.util.StringRepresentable;

/**
 * ボルト方式。薬室（チャンバー）内弾薬の扱いが変わる。
 *
 * <ul>
 *   <li>{@link #CLOSED} — クローズドボルト。発射前にボルトが前進し薬室に1発が待機する。
 *       よって満タンは「マガジン容量 + 薬室1発」。薬室に弾を残してリロードすると1発多く装填できる。</li>
 *   <li>{@link #OPEN} — オープンボルト。発射の合間はボルトが後退位置で薬室は空。
 *       薬室待機はなく、満タンはマガジン容量ちょうど。</li>
 * </ul>
 */
public enum BoltType implements StringRepresentable {
    CLOSED("closed"),
    OPEN("open");

    /** 永続化用（enum の並び順に依存しない name ベース）。 */
    public static final Codec<BoltType> CODEC = StringRepresentable.fromEnum(BoltType::values);

    private final String serializedName;

    BoltType(String serializedName) {
        this.serializedName = serializedName;
    }

    @Override
    public String getSerializedName() {
        return serializedName;
    }
}
