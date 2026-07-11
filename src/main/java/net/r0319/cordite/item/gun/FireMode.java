package net.r0319.cordite.item.gun;

import net.minecraft.network.chat.Component;

/**
 * 発射モード。実銃準拠でどの銃がどのモードを持つかは {@link GunProperties#fireModes()} で決まる。
 *
 * <ul>
 *   <li>{@link #SINGLE} — 単発（セミオート）。トリガーごとに1発。押しっぱなしでは連射しない。</li>
 *   <li>{@link #FULL_AUTO} — フルオート。押しっぱなしでサイクリックレートに従い連射。</li>
 *   <li>{@link #BURST} — バースト。1トリガーで {@link #BURST_COUNT} 発を連射。</li>
 * </ul>
 */
public enum FireMode {
    SINGLE("cordite.firemode.single"),
    FULL_AUTO("cordite.firemode.full_auto"),
    BURST("cordite.firemode.burst");

    /** バースト時の発射数。 */
    public static final int BURST_COUNT = 3;

    private final String translationKey;

    FireMode(String translationKey) {
        this.translationKey = translationKey;
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
