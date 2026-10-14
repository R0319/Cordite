package net.r0319.cordite.combat;

import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * サーバー側のプレイヤー別・一時的な発射状態（連射レート制御／バースト残数／リロード完了tick）。
 *
 * <p>永続化不要な過渡状態なのでデータコンポーネントではなくメモリ上で持つ。
 * 銃を持っていない間も残るが軽量なので問題にしない（再ログインで消える）。</p>
 */
public final class GunFireManager {
    private GunFireManager() {}

    public static final class State {
        /**
         * 最後に発射（空撃ちを含む）したゲームtick。初期値は「十分昔」を表すが、{@code now - lastShotTick} の
         * 減算オーバーフローを避けるため {@code Long.MIN_VALUE} ではなく {@code Long.MIN_VALUE/2}。
         */
        public long lastShotTick = Long.MIN_VALUE / 2;
        /**
         * 次に発射を許可するゲームtick（<b>小数</b>）。連射間隔 {@code 1200 / rpm} tick は多くの銃で整数に
         * ならない（M4A1 の 800rpm = 1.5tick）。間隔を整数に丸めると 1.5 → 2tick で実効 600rpm に落ちるため、
         * 「次に撃てる時刻」を小数のまま積み上げ、間隔 1.5 なら 2tick・1tick を交互に空けて平均で定義どおりの
         * レートになるようにする（{@link #markShot}）。判定は {@code now >= nextShotTick}。
         */
        public double nextShotTick = -Double.MAX_VALUE;
        /** バーストで残っている発射数。 */
        public int burstRemaining = 0;
        /** リロード完了ゲームtick（未リロード時は Long.MIN_VALUE。比較のみで減算しない）。 */
        public long reloadCompleteTick = Long.MIN_VALUE;
        /**
         * リロード中の銃スタック（同一性比較用）。リロードは「プレイヤー」ではなく
         * 「その銃」に紐づくため、別の銃へ持ち替えたらリロードは中断する
         * （持ち替えで別の銃が即装填される不正を防ぐ）。
         */
        public ItemStack reloadingStack = ItemStack.EMPTY;
        /** 前tickにメインハンドで保持していたスタック（持ち替え検出用・同一性比較のみ）。 */
        public ItemStack lastHeldStack = ItemStack.EMPTY;

        /**
         * 発射（または空撃ち）を記録し、次に撃てる時刻を {@code intervalTicks} ぶん先へ進める。
         *
         * <p>直前の許可時刻がこのtickの範囲内（{@code now - nextShotTick < 1}）なら、そこから間隔を積むことで
         * 小数の端数を次へ持ち越す。しばらく撃っていなかった場合（許可時刻がもっと昔）は現在tickを起点にする。
         * 起点を単純に {@code max(nextShotTick, now)} にすると端数が毎回切り捨てられ、丸めていたのと同じになる。</p>
         */
        public void markShot(long now, double intervalTicks) {
            double base = now - nextShotTick < 1.0 ? nextShotTick : now;
            nextShotTick = base + intervalTicks;
            lastShotTick = now;
        }

        /** 連射レート上は撃ってよい時刻か。 */
        public boolean canShootAt(long now) {
            return now >= nextShotTick;
        }

        /** リロードを中断する。 */
        public void cancelReload() {
            reloadCompleteTick = Long.MIN_VALUE;
            reloadingStack = ItemStack.EMPTY;
        }

        // --- 射撃トリガー（クライアントから同期） ---
        /** トリガー押下中か。 */
        public boolean triggerHeld = false;
        /** 前tickのトリガー状態（押下エッジ検出用）。 */
        public boolean prevTriggerHeld = false;
        /** 現在の押下で単発を撃ったか（SINGLEの二重発射防止）。 */
        public boolean firedThisPress = false;
        /**
         * 現在の押下で空撃ち音を鳴らしたか。実銃はトリガーを引き切った1回しか撃発機構が動かないため、
         * フルオート/バーストで引きっぱなしにしても空撃ち音を連打しない。
         */
        public boolean dryFiredThisPress = false;

        /**
         * ADS（サイトを覗いている）か。クライアントから同期される（{@link net.r0319.cordite.network.SetAdsPayload}）。
         * 腰だめ時に弾をばらつかせる判定に使う（拡散量の算出はサーバー側で行う）。
         */
        public boolean aiming = false;
    }

    private static final Map<UUID, State> STATES = new ConcurrentHashMap<>();

    public static State get(Player player) {
        return STATES.computeIfAbsent(player.getUUID(), id -> new State());
    }

    public static void clear(Player player) {
        STATES.remove(player.getUUID());
    }
}
