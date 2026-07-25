package net.r0319.cordite.client.anim;

/**
 * ローカルプレイヤー1人分の「再生中アニメーション」を保持する簡易な静的ホルダ（プロトタイプ範囲）。
 * 複数プレイヤー分の管理（三人称・他プレイヤー表示）は worldmodel 実装時に拡張する
 * （docs/design/animation-system.md 参照）。
 */
public final class GunAnimationState {
    private GunAnimationState() {}

    private static long startGameTime = Long.MIN_VALUE;
    private static boolean playing = false;

    public static void play(long nowGameTime) {
        startGameTime = nowGameTime;
        playing = true;
    }

    public static boolean isPlaying(BakedAnimation anim, long nowGameTime, float partialTick) {
        if (!playing || anim == null) {
            return false;
        }
        if (elapsedSeconds(nowGameTime, partialTick) > anim.lengthSeconds()) {
            playing = false;
            return false;
        }
        return true;
    }

    public static float elapsedSeconds(long nowGameTime, float partialTick) {
        return ((nowGameTime - startGameTime) + partialTick) / 20f;
    }
}
