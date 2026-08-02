package net.r0319.cordite.client.anim;

/**
 * 排莢された薬莢の「飛行中インスタンス」を複数同時に保持する。
 *
 * <p>薬莢は現実に複数個が同時に空中へ存在しうるのに対し、{@link GunAnimationState} は
 * 「今再生中のアクション1つ」しか持てない。薬莢の動きを発射アニメーション（{@code fire}）に
 * 含めていると、次の弾を撃った瞬間にクリップが頭から再生し直され、<b>飛んでいる途中の薬莢が
 * 銃の中へ戻ってしまう</b>（Glockは400RPM＝0.15秒間隔で撃てるのに対し、薬莢の軌道は0.29秒ある）。</p>
 *
 * <p>そこで薬莢の軌道だけを専用クリップ（{@code animation.glock.eject}、{@code ammo}ボーンのみ）に
 * 分け、発射のたびに<b>独立した開始時刻を持つインスタンスをここへ積む</b>。描画側
 * （{@link net.r0319.cordite.client.render.GunItemRenderer}）は生存中のインスタンスの数だけ
 * 薬莢ボーンを重ねて描く。銃本体の発射アニメーションは従来どおり撃つたびに頭から再生してよい。</p>
 *
 * <p>{@link GunAnimationState} と同じくローカルプレイヤー1人分の静的ホルダで、Minecraftの
 * クライアント専用クラスを参照しない素のJavaクラス（{@link net.r0319.cordite.network.ModNetwork}
 * のハンドラから触るため。専用サーバーでロードされても問題ない）。</p>
 */
public final class ShellEjectionTracker {
    private ShellEjectionTracker() {}

    /**
     * 同時に飛べる薬莢の上限。溢れたら最も古いものから捨てる。
     * 軌道0.29秒に対し最速の900RPM（0.067秒間隔）でも同時5個までなので余裕がある。
     */
    public static final int CAPACITY = 8;

    /** 飛行中の薬莢の発射tick。古い順（昇順）に前へ詰めて保持する。 */
    private static final long[] startGameTimes = new long[CAPACITY];
    private static int count = 0;

    /** 1発ぶんの薬莢を飛ばし始める（発射アニメーションの開始と同じタイミングで呼ぶ）。 */
    public static void start(long nowGameTime) {
        if (count == CAPACITY) {
            System.arraycopy(startGameTimes, 1, startGameTimes, 0, CAPACITY - 1);
            count--;
        }
        startGameTimes[count++] = nowGameTime;
    }

    /**
     * 寿命（＝排莢クリップの動きが終わる時刻）を過ぎた薬莢を捨てる。毎tick呼ぶ
     * （{@link ClientGunAnimationTracker}）。配列は古い順なので、先頭から連続して捨てられる。
     */
    public static void prune(float lifeSeconds, long nowGameTime) {
        int expired = expiredCount(lifeSeconds, nowGameTime, 0f);
        if (expired > 0) {
            System.arraycopy(startGameTimes, expired, startGameTimes, 0, count - expired);
            count -= expired;
        }
    }

    /**
     * 飛行中の薬莢のクリップ内時刻[秒]を古い順に {@code out} へ書き、その個数を返す。
     * {@code out} は {@link #CAPACITY} 以上の長さが必要。状態は変更しない（描画から毎フレーム呼ぶ）。
     */
    public static int collect(float lifeSeconds, long nowGameTime, float partialTick, float[] out) {
        int expired = expiredCount(lifeSeconds, nowGameTime, partialTick);
        int alive = 0;
        for (int i = expired; i < count; i++) {
            out[alive++] = elapsedSeconds(startGameTimes[i], nowGameTime, partialTick);
        }
        return alive;
    }

    /** 飛行中の薬莢をすべて消す（銃を持ち替えた・ワールドを抜けた等）。 */
    public static void reset() {
        count = 0;
    }

    /** 先頭から数えて寿命切れになっている個数。配列は古い順なので途中で打ち切ってよい。 */
    private static int expiredCount(float lifeSeconds, long nowGameTime, float partialTick) {
        int expired = 0;
        while (expired < count && elapsedSeconds(startGameTimes[expired], nowGameTime, partialTick) > lifeSeconds) {
            expired++;
        }
        return expired;
    }

    private static float elapsedSeconds(long startGameTime, long nowGameTime, float partialTick) {
        return ((nowGameTime - startGameTime) + partialTick) / 20f;
    }
}
