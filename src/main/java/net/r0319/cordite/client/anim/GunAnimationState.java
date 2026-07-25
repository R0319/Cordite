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

    public enum Action { FIRE, RELOAD, RELOAD_EMPTY }

    private static Action currentAction = null;
    private static long startGameTime = Long.MIN_VALUE;

    public static void play(Action action, long nowGameTime) {
        currentAction = action;
        startGameTime = nowGameTime;
    }

    /** 現在のアクション。無ければ null（呼び出し側はidleにフォールバックする）。 */
    public static Action currentAction() {
        return currentAction;
    }

    public static float elapsedSeconds(long nowGameTime, float partialTick) {
        return ((nowGameTime - startGameTime) + partialTick) / 20f;
    }

    /** アクションが終わった（指定した実時間を超えた）ら null に戻す。 */
    public static void clearIfFinished(float realDurationSeconds, long nowGameTime, float partialTick) {
        if (currentAction != null && elapsedSeconds(nowGameTime, partialTick) > realDurationSeconds) {
            currentAction = null;
        }
    }
}
