package net.r0319.cordite.client.anim;

/**
 * 発射した瞬間にレティクルを一瞬だけ開かせる演出の状態（ローカルプレイヤー1人分の静的ホルダ）。
 *
 * <p>撃った瞬間に最大まで開き、{@link #DURATION_SECONDS} かけて元へ戻る。描画するのは
 * {@link net.r0319.cordite.client.GunHudOverlay}。</p>
 *
 * <p><b>これは演出であって実際の拡散ではない</b>。レティクルの隙間は本来
 * {@link net.r0319.cordite.gunpack.GunDefinition#hipSpreadDeg()} を画面上のpxへ換算した
 * 「線の内側に弾が来る」表示で、ここで足す量はその上に乗せる見た目だけのキックになる。
 * 連射・移動によるブルーム（実際に拡散が広がる仕様）を入れるときは、
 * <b>拡散量そのものを動かしてこのクラスを畳む</b>のが本筋
 * （そうすれば表示と当たりの意味が再び一致する）。</p>
 *
 * <p>{@link MuzzleFlashState} と同じく、Minecraftのクライアント専用クラスを参照しない素のJavaクラス
 * （{@link net.r0319.cordite.network.ModNetwork} のハンドラから触るため）。</p>
 */
public final class ReticleKickState {
    private ReticleKickState() {}

    /** 開いてから元に戻るまでの時間[秒]。🟡仮（実機で見ながら調整する値）。 */
    public static final float DURATION_SECONDS = 0.12f;

    /**
     * 反動値1あたりの最大の開き[px]。実際の開きはこれに銃の
     * {@link net.r0319.cordite.gunpack.GunDefinition#recoilPitch()} を掛けた値になる
     * （反動の大きい銃ほど大きく開く）。🟡仮（実機で見ながら調整する値）。
     */
    public static final float PIXELS_PER_RECOIL = 3f;

    private static long startGameTime = Long.MIN_VALUE / 2;
    private static float maxPixels;

    /**
     * 1発ぶんのキックを始める（マズルフラッシュ・視点反動と同じタイミングで呼ぶ）。
     *
     * <p>連射では<b>撃つたびに開き切った状態へ戻す</b>（積み上げない）。積み上げ方式にすると
     * 連射中にどこまでも開いてしまい、上限や減衰の調整が要る。撃ち続けている間は開いたまま、
     * 撃ち止めると閉じる、という挙動はこの方式でも成立する。</p>
     *
     * @param recoilPitch 銃の縦反動値（{@link net.r0319.cordite.gunpack.GunDefinition#recoilPitch()}）。
     */
    public static void kick(long nowGameTime, float recoilPitch) {
        startGameTime = nowGameTime;
        maxPixels = PIXELS_PER_RECOIL * recoilPitch;
    }

    /**
     * 今フレームの追加の開き[px]。キックしていない／戻り切っていれば0。
     *
     * <p>撃った瞬間が最大で、二次関数で戻す（等速で戻すより「弾かれて収まる」感じになる）。</p>
     */
    public static float extraPixels(long nowGameTime, float partialTick) {
        float elapsed = ((nowGameTime - startGameTime) + partialTick) / 20f;
        if (elapsed < 0f || elapsed >= DURATION_SECONDS) {
            return 0f;
        }
        float remaining = 1f - elapsed / DURATION_SECONDS;
        return maxPixels * remaining * remaining;
    }

    /** 銃を持ち替えた・ワールドを抜けた等で開きを消す。 */
    public static void reset() {
        startGameTime = Long.MIN_VALUE / 2;
    }
}
