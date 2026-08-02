package net.r0319.cordite.client.anim;

/**
 * ローカルプレイヤー1人分の「再生中アクション（fire/reload/reload_empty）」を保持する
 * 簡易な静的ホルダ（プロトタイプ範囲）。アクションが無い/終わっている間は idle にフォールバックする
 * （フォールバック自体は {@link net.r0319.cordite.client.render.GunItemRenderer} 側で行う）。
 * 複数プレイヤー分の管理（三人称・他プレイヤー表示）は worldmodel 実装時に拡張する
 * （docs/design/animation-system.md 参照）。
 */
public final class GunAnimationState {
    private GunAnimationState() {}

    /**
     * {@code FIRE_EMPTY} は「その1発でマガジンが空になった」発射。ホールドオープンする銃で
     * スライドが後退したまま終わる専用クリップ（{@code fire_empty}）を再生するための区別で、
     * クリップが未作成なら通常の{@code fire}へフォールバックする。
     */
    public enum Action { TAKE_OUT, FIRE, FIRE_EMPTY, RELOAD, RELOAD_EMPTY, INSPECT, INSPECT_EMPTY }

    /**
     * リロード再生の終了後、残弾の同期を待つ猶予[tick]。
     *
     * <p>リロードアニメーションはクライアントのローカル予測で始まる（Rキーを押した時点）ため、
     * <b>サーバーが装填を完了して残弾コンポーネントが同期されるより先に再生が終わる</b>。
     * その隙間で残弾を読むとまだ0なので、弾切れ待機（スライド後退）が一瞬出てから閉じる、という
     * ちらつきになる。リロードが終わった直後のこの猶予の間は弾切れ表示を抑止する。</p>
     *
     * <p>本来はリロード完了をサーバーから通知すべきで、それは後続作業
     * （docs/design/animation-system.md「リロード検知の専用ペイロード方式への切替」）。</p>
     */
    public static final int RELOAD_SYNC_GRACE_TICKS = 10;

    /**
     * 撃ち切りフラグを残弾コンポーネントより優先する期間[tick]。
     *
     * <p>撃ち切ったかどうかはサーバーが{@link net.r0319.cordite.network.GunFiredPayload}で即座に
     * 送ってくるのに対し、残弾コンポーネントのスロット同期は数tick遅れて届く。同期を待って
     * 弾切れ表示へ移ると<b>0発になった瞬間より遅れてチャンバーが開く</b>ので、パケットで受け取った
     * 事実を先に使い、同期が追いついた後はコンポーネントの値に任せる。</p>
     */
    public static final int AMMO_SYNC_GRACE_TICKS = 10;

    private static Action currentAction = null;
    private static long startGameTime = Long.MIN_VALUE;
    private static long playId = 0L;
    /** 最後にリロード系の再生が終わったゲームtick。 */
    private static long reloadFinishedGameTime = Long.MIN_VALUE / 2;
    /** 最後に「その1発で撃ち切った」発射があったゲームtick。 */
    private static long emptiedByShotGameTime = Long.MIN_VALUE / 2;

    public static void play(Action action, long nowGameTime) {
        if (action == Action.RELOAD || action == Action.RELOAD_EMPTY || action == Action.TAKE_OUT) {
            // 装填し直す／別の銃に持ち替える。どちらも直前の銃の撃ち切り状態は引き継がない
            clearEmptiedByShot();
        }
        currentAction = action;
        startGameTime = nowGameTime;
        playId++;
    }

    /**
     * 再生開始のたびに増える通し番号。「同じアクションが撃ち直された」場合も値が変わるので、
     * 再生開始のエッジを取りこぼさずに検出できる（{@link GunAnimationSoundPlayer} のタイムライン開始に使う）。
     */
    public static long playId() {
        return playId;
    }

    /** 現在のアクション。無ければ null（呼び出し側はidleにフォールバックする）。 */
    public static Action currentAction() {
        return currentAction;
    }

    /**
     * 発射アニメーションの再生を要求する（{@link net.r0319.cordite.network.GunFiredPayload} の受信時）。
     *
     * <p><b>リロード中は無視する</b>。リロードは2.7秒級の長いモーションなのに対し、発射アニメは
     * 0.5秒級の短いキックなので、上書きするとキックが終わった時点でidleへ戻り
     * <b>残りのリロードモーションが丸ごと消える</b>（サーバー側のリロードだけは進むので
     * 「モーション無しでリロードが完了する」ように見える）。サーバーはリロード中の発射を拒否するため、
     * ここに届く発射トリガーは「リロード開始前に撃った弾のぶんが遅れて届いたもの」でしかない。</p>
     *
     * @param emptyAfterShot この1発で撃ち切った（ホールドオープンする銃で残弾0になった）か。
     *                      サーバーが判定して{@link net.r0319.cordite.network.GunFiredPayload}で送る
     *                      （クライアントの残弾コンポーネントは同期が遅れるため自前判定できない）。
     * @return 再生を開始したか。無視した場合はfalse（呼び出し側は排莢も飛ばさない）。
     */
    public static boolean playFire(long nowGameTime, boolean emptyAfterShot) {
        if (isReloading()) {
            return false;
        }
        play(emptyAfterShot ? Action.FIRE_EMPTY : Action.FIRE, nowGameTime);
        if (emptyAfterShot) {
            emptiedByShotGameTime = nowGameTime;
        } else {
            clearEmptiedByShot();
        }
        return true;
    }

    /**
     * 直近の発射で撃ち切った状態か（残弾コンポーネントの同期を待たずに弾切れ表示へ移るために使う）。
     * 猶予（{@link #AMMO_SYNC_GRACE_TICKS}）を過ぎたら、あとはコンポーネントの値が真になる。
     */
    public static boolean emptiedByRecentShot(long nowGameTime) {
        return nowGameTime - emptiedByShotGameTime < AMMO_SYNC_GRACE_TICKS;
    }

    private static void clearEmptiedByShot() {
        emptiedByShotGameTime = Long.MIN_VALUE / 2;
    }

    /**
     * リロード系（reload/reload_empty）を再生中か。発射アニメの割り込み判定（{@link #playFire}）と、
     * ADSの抑止（リロード中は覗けない）に使う。
     */
    public static boolean isReloading() {
        return currentAction == Action.RELOAD || currentAction == Action.RELOAD_EMPTY;
    }

    /** 点検系（inspect/inspect_empty）を再生中か。 */
    public static boolean isInspecting() {
        return currentAction == Action.INSPECT || currentAction == Action.INSPECT_EMPTY;
    }

    /**
     * 点検を中断してidleへ戻す（ADSを始めたときなど）。
     *
     * <p>点検はゲーム状態を何も動かさない「見せるだけ」のアクションなので、
     * リロードと違っていつ捨ててもよい。発射・リロード・持ち替えによる中断は
     * それぞれの{@link #play}が上書きするので、明示的に呼ぶ必要があるのは
     * 「別のアクションを始めるわけではないが点検はやめたい」場面だけ。</p>
     *
     * @return 実際に中断したか（呼び出し側は再生中だったサウンドも止める）。
     */
    public static boolean cancelInspect() {
        if (!isInspecting()) {
            return false;
        }
        currentAction = null;
        return true;
    }

    public static float elapsedSeconds(long nowGameTime, float partialTick) {
        return ((nowGameTime - startGameTime) + partialTick) / 20f;
    }

    /** アクションが終わった（指定した実時間を超えた）ら null に戻す。 */
    public static void clearIfFinished(float realDurationSeconds, long nowGameTime, float partialTick) {
        if (currentAction != null && elapsedSeconds(nowGameTime, partialTick) > realDurationSeconds) {
            if (isReloading()) {
                reloadFinishedGameTime = nowGameTime;
            }
            currentAction = null;
        }
    }

    /**
     * リロード再生が終わった直後で、残弾の同期待ちの猶予（{@link #RELOAD_SYNC_GRACE_TICKS}）の中か。
     * この間は残弾0でも弾切れ表示（スライド後退）をしない。
     */
    public static boolean withinReloadSyncGrace(long nowGameTime) {
        return nowGameTime - reloadFinishedGameTime < RELOAD_SYNC_GRACE_TICKS;
    }
}
