package net.r0319.cordite.item.gun;

import com.mojang.serialization.Codec;
import io.netty.buffer.ByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.util.StringRepresentable;

/**
 * 発射モード。実銃準拠でどの銃がどのモードを持つかは {@link GunProperties#fireModes()} で決まる。
 *
 * <ul>
 *   <li>{@link #SINGLE} — 単発（セミオート）。トリガーごとに1発。押しっぱなしでは連射しない。</li>
 *   <li>{@link #FULL_AUTO} — フルオート。押しっぱなしでサイクリックレートに従い連射。</li>
 *   <li>{@link #BURST} — バースト。1トリガーで {@link #BURST_COUNT} 発を連射。</li>
 * </ul>
 */
public enum FireMode implements StringRepresentable {
    SINGLE("single", "cordite.firemode.single"),
    FULL_AUTO("full_auto", "cordite.firemode.full_auto"),
    BURST("burst", "cordite.firemode.burst");

    /** バースト時の発射数。 */
    public static final int BURST_COUNT = 3;

    /** 永続化用（enum の並び順に依存しない name ベース）。 */
    public static final Codec<FireMode> CODEC = StringRepresentable.fromEnum(FireMode::values);
    /** ネットワーク同期用（両端のバージョンは一致する前提なので ordinal で可）。 */
    public static final StreamCodec<ByteBuf, FireMode> STREAM_CODEC =
            ByteBufCodecs.idMapper(i -> FireMode.values()[i], FireMode::ordinal);

    private final String serializedName;
    private final String translationKey;

    FireMode(String serializedName, String translationKey) {
        this.serializedName = serializedName;
        this.translationKey = translationKey;
    }

    @Override
    public String getSerializedName() {
        return serializedName;
    }

    /** 押しっぱなしで連続発射できるか。 */
    public boolean isAutomatic() {
        return this == FULL_AUTO;
    }

    /** HUD表示用ラベル。 */
    public Component label() {
        return Component.translatable(translationKey);
    }
}
