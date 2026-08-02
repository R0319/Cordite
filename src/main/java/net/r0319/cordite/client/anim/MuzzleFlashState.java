package net.r0319.cordite.client.anim;

import java.util.random.RandomGenerator;

/**
 * マズルフラッシュの表示状態（ローカルプレイヤー1人分の静的ホルダ）。
 *
 * <p><b>方式</b>: モデル側の {@code muzzle_flash} は<b>実体を持たないロケーター</b>（cube無し・pivotだけ）で、
 * 板もUVもアニメーションのキーフレームも作らない。描画は
 * {@link net.r0319.cordite.client.render.GunItemRenderer} がそのpivot位置に発光ビルボードを
 * 1枚生成して行い、表示タイミングはこのクラスが持つ。</p>
 *
 * <p>以前は「{@code muzzle_flash}ボーンに板を作り、{@code fire}クリップで{@code scale}を0→1→0と打つ」
 * 方式だった（タイミングを作者側に置く思想）。ただしBedrock geometryのUVは銃本体テクスチャの解像度で
 * 正規化されるため、別解像度の{@code muzzle_flash.png}にUVを合わせる作業がBlockbench上で煩雑になる。
 * ロケーター方式なら作者の作業は「pivotを銃口に置く」＋「png1枚」で済む。</p>
 *
 * <p>{@link ShellEjectionTracker} と同じく、Minecraftのクライアント専用クラスを参照しない素のJavaクラス
 * （{@link net.r0319.cordite.network.ModNetwork} のハンドラから触るため）。</p>
 */
public final class MuzzleFlashState {
    private MuzzleFlashState() {}

    /**
     * 表示時間[秒]。1tick=0.05秒なので既定は約2tick。🟡仮（実機で見ながら調整する値）。
     * 短すぎるとフレームレートによっては表示されないフレームが出る。
     */
    public static final float DURATION_SECONDS = 0.1f;

    private static final RandomGenerator RANDOM = new java.util.Random();

    private static long startGameTime = Long.MIN_VALUE / 2;
    private static float rollDegrees;
    private static float sizeJitter = 1f;

    /**
     * 1発ぶんのフラッシュを出す（発射アニメーションの開始と同じタイミングで呼ぶ）。
     * 毎発ランダムに回転・大きさを振って、連射時に同じ絵が張り付いて見えないようにする。
     */
    public static void flash(long nowGameTime) {
        startGameTime = nowGameTime;
        rollDegrees = RANDOM.nextFloat() * 360f;
        sizeJitter = 0.85f + RANDOM.nextFloat() * 0.3f;
    }

    /** 表示中か。 */
    public static boolean isActive(long nowGameTime, float partialTick) {
        float elapsed = elapsedSeconds(nowGameTime, partialTick);
        return elapsed >= 0f && elapsed <= DURATION_SECONDS;
    }

    /** 表示開始からの経過割合（0→1）。フェードアウトに使う。 */
    public static float progress(long nowGameTime, float partialTick) {
        return Math.clamp(elapsedSeconds(nowGameTime, partialTick) / DURATION_SECONDS, 0f, 1f);
    }

    /** この発射ぶんのランダムなロール角[度]（銃口方向まわりの回転）。 */
    public static float rollDegrees() {
        return rollDegrees;
    }

    /** この発射ぶんのランダムな大きさ倍率。 */
    public static float sizeJitter() {
        return sizeJitter;
    }

    /** 銃を持ち替えた・ワールドを抜けた等でフラッシュを消す。 */
    public static void reset() {
        startGameTime = Long.MIN_VALUE / 2;
    }

    private static float elapsedSeconds(long nowGameTime, float partialTick) {
        return ((nowGameTime - startGameTime) + partialTick) / 20f;
    }
}
