package net.r0319.cordite.client.anim;

import net.minecraft.util.Mth;

/**
 * ローカルプレイヤーのADS（サイトを覗く）状態。右クリック押下で0→1へ、離すと1→0へ遷移する
 * 補間量だけを持つ簡易ホルダ（{@link GunAnimationState} と同じくプロトタイプ範囲の静的ホルダ）。
 *
 * <p>描画側（{@link net.r0319.cordite.client.render.GunItemRenderer}）はこの値で
 * 一人称の基準ロケーターを {@code idle_view}（腰だめ）→{@code iron_view}（サイト）へ補間する。
 * FOVは変えない（docs/specs/02-guns.md「スコープを覗いても画面全体のFOVは変化しない」）。</p>
 *
 * <p><b>未実装</b>: サーバーへの同期。現状ADSは見た目だけで、命中精度やADS中の移動速度には影響しない
 * （それらを入れる際はサーバー権威で持つ必要がある → docs/design/00-architecture.md）。</p>
 */
public final class GunAdsState {
    private GunAdsState() {}

    /**
     * 腰だめ⇔ADSの遷移にかける秒数（🟡仮）。実機で覗き心地を見ながら調整する値。
     * 銃ごとに変えるなら gunpack 定義側へ移す。
     */
    public static final float ADS_TRANSITION_SECONDS = 0.15f;

    /** 右クリックが押されているか（入力側が毎tick更新する）。 */
    private static boolean aiming = false;
    /** 0=腰だめ, 1=完全にサイトを覗いた状態。前tick終了時点の値。 */
    private static float progress = 0f;
    /** 前tickのprogress（フレーム間補間用）。 */
    private static float prevProgress = 0f;

    /** 入力状態を更新し、1tick分だけ補間を進める。クライアントtickから毎tick呼ぶ。 */
    public static void tick(boolean aimingNow) {
        aiming = aimingNow;
        prevProgress = progress;
        float step = 1f / Math.max(1f, ADS_TRANSITION_SECONDS * 20f);
        progress = Mth.clamp(progress + (aiming ? step : -step), 0f, 1f);
    }

    /** 銃を持っていない・GUIを開いた等でADSを打ち切る（次tickから0へ戻る）。 */
    public static void release() {
        aiming = false;
    }

    /** 即座に腰だめへ戻す（持ち替え・リロード開始時など、補間を挟みたくない場合）。 */
    public static void reset() {
        aiming = false;
        progress = 0f;
        prevProgress = 0f;
    }

    public static boolean isAiming() {
        return aiming;
    }

    /** 描画時点の補間量（0〜1）。 */
    public static float progress(float partialTick) {
        return Mth.lerp(Mth.clamp(partialTick, 0f, 1f), prevProgress, progress);
    }
}
