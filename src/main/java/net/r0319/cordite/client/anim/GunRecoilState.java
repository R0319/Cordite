package net.r0319.cordite.client.anim;

import net.minecraft.util.Mth;

import java.util.Random;

/**
 * 視点キック（反動のうち「実際にクロスヘアが跳ね上がる」層）の状態。
 *
 * <p>Minecraftの視点はクライアントが持ち、毎tickサーバーへ送られる。したがってここで視点を動かせば、
 * <b>次以降の弾はサーバー側でもズレた方向へ飛ぶ</b>（発射方向はサーバーがプレイヤーの向きから算出する）。
 * サーバー権威を崩さずに反動を効かせられるのはこのため。ただし視点そのものはMCの構造上
 * クライアント権威なので、<b>これ単体はチート耐性を持たない</b>。命中のばらつきを担保するには
 * サーバー側の拡散（未実装）が要る → {@code docs/design/recoil.md}。</p>
 *
 * <p>挙動は2段階:</p>
 * <ol>
 *   <li><b>立ち上がり</b>: 撃った瞬間に全部動かすとカクつくので、キック量を「未適用ぶん」として貯め、
 *       毎tick一定割合ずつ視点へ移す（{@link #RISE_RATE}）。</li>
 *   <li><b>回復</b>: 適用したキックのうち{@link #RECOVERY_RATIO}の割合を「戻せるぶん」として覚えておき、
 *       毎tick一定割合ずつ戻す（{@link #RECOVER_RATE}）。戻らない残りが実質的な照準のズレになる。</li>
 * </ol>
 *
 * <p>{@link GunAnimationState} と同じくローカルプレイヤー1人分の静的ホルダで、Minecraftの
 * クライアント専用クラスを参照しない（{@link net.r0319.cordite.network.ModNetwork} のハンドラから
 * 触るため）。視点への反映は{@link net.r0319.cordite.client.GunRecoilHandler}が行う。</p>
 */
public final class GunRecoilState {
    private GunRecoilState() {}

    // --- チューニング定数（🟡仮）。手触りの値なので実機で撃ちながら調整する ---
    /** 1tickで未適用キックのうち視点へ移す割合。大きいほど鋭く跳ねる。 */
    public static final float RISE_RATE = 0.5f;
    /** 跳ね上がったぶんのうち、時間経過で戻ってくる割合。1.0だと完全に元へ戻る＝反動が実質無い。 */
    public static final float RECOVERY_RATIO = 0.8f;
    /** 1tickで戻せるぶんのうち実際に戻す割合。小さいほどゆっくり戻る。 */
    public static final float RECOVER_RATE = 0.12f;
    /** ADS中の反動倍率。構えている方が制御できる、という表現。 */
    public static final float ADS_RECOIL_MULTIPLIER = 0.6f;

    /** これ未満は0とみなして打ち切る（いつまでも微小な回復が続くのを防ぐ）。 */
    private static final float EPSILON = 1.0e-4f;

    private static final Random RANDOM = new Random();

    /** まだ視点へ移していないキック量。pitchは上向きを正とする。 */
    private static float pendingPitch;
    private static float pendingYaw;
    /** 視点へ移し終えたキックのうち、これから戻すぶん。 */
    private static float recoverablePitch;
    private static float recoverableYaw;

    /** このtickに視点へ加える量（度）。pitchはMinecraftの符号（負が上向き）。 */
    public record ViewDelta(float pitch, float yaw) {
        public boolean isZero() {
            return pitch == 0f && yaw == 0f;
        }
    }

    private static final ViewDelta ZERO = new ViewDelta(0f, 0f);

    /**
     * 1発ぶんのキックを加える（発射トリガー受信時）。左右のブレは ±{@code yawDeg} でランダム。
     * ADS中は{@link #ADS_RECOIL_MULTIPLIER}まで減衰させる。
     */
    public static void kick(float pitchDeg, float yawDeg) {
        float scale = Mth.lerp(GunAdsState.progress(1f), 1f, ADS_RECOIL_MULTIPLIER);
        pendingPitch += pitchDeg * scale;
        pendingYaw += (RANDOM.nextFloat() * 2f - 1f) * yawDeg * scale;
    }

    /** 1tick進め、視点へ加えるべき量を返す。毎クライアントtickに1回だけ呼ぶこと。 */
    public static ViewDelta advance() {
        if (isSettled()) {
            return ZERO;
        }

        float risePitch = pendingPitch * RISE_RATE;
        pendingPitch -= risePitch;
        recoverablePitch += risePitch * RECOVERY_RATIO;
        float backPitch = recoverablePitch * RECOVER_RATE;
        recoverablePitch -= backPitch;

        float riseYaw = pendingYaw * RISE_RATE;
        pendingYaw -= riseYaw;
        recoverableYaw += riseYaw * RECOVERY_RATIO;
        float backYaw = recoverableYaw * RECOVER_RATE;
        recoverableYaw -= backYaw;

        snapTinyToZero();

        // pitchは「負が上向き」なので、跳ね上げは符号反転して渡す。回復はその逆向き。
        return new ViewDelta(backPitch - risePitch, riseYaw - backYaw);
    }

    /** 反動を打ち切る（切断・持ち替え時など）。 */
    public static void reset() {
        pendingPitch = 0f;
        pendingYaw = 0f;
        recoverablePitch = 0f;
        recoverableYaw = 0f;
    }

    private static boolean isSettled() {
        return Math.abs(pendingPitch) < EPSILON && Math.abs(pendingYaw) < EPSILON
                && Math.abs(recoverablePitch) < EPSILON && Math.abs(recoverableYaw) < EPSILON;
    }

    private static void snapTinyToZero() {
        if (Math.abs(pendingPitch) < EPSILON) pendingPitch = 0f;
        if (Math.abs(pendingYaw) < EPSILON) pendingYaw = 0f;
        if (Math.abs(recoverablePitch) < EPSILON) recoverablePitch = 0f;
        if (Math.abs(recoverableYaw) < EPSILON) recoverableYaw = 0f;
    }
}
