package net.r0319.cordite.client.anim;

import org.joml.Vector3f;

import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * アニメーションを指定時刻でサンプリングする。線形補間のみ（パフォーマンス方針、
 * docs/specs/06-animations.md 参照）。トラックを持たないボーンは結果に含めない
 * （＝レンダラー側は restポーズのまま扱う）。
 */
public final class AnimationSampler {
    private AnimationSampler() {}

    /**
     * ボーンのrestポーズからの差分。position はブロック単位、rotation は度、
     * scale は倍率（トラックが無ければ等倍 {@code (1,1,1)}）。
     */
    public record Pose(Vector3f positionDelta, Vector3f rotationDeltaDeg, Vector3f scaleFactor) {}

    private static final Vector3f NO_SCALE = new Vector3f(1f, 1f, 1f);
    /** 位置・回転の「無変換」。読み取り専用として扱うこと（値を返すときは必ずコピーする）。 */
    private static final Vector3f NO_DELTA = new Vector3f();

    public static Map<String, Pose> sample(BakedAnimation anim, float t) {
        Map<String, Pose> result = new HashMap<>();
        for (Map.Entry<String, BoneTrack> entry : anim.bones().entrySet()) {
            Pose pose = samplePose(entry.getValue(), t);
            if (pose != null) {
                result.put(entry.getKey(), pose);
            }
        }
        return result;
    }

    /**
     * 待機ポーズを土台に、アクションのクリップを<b>上書き（重ね合わせ）</b>してサンプリングする。
     *
     * <p>アクションのクリップは<b>動かすボーンのトラックだけ</b>持っていればよい、という作り方に対応する
     * ためのもの。例えばglockの{@code reload}は{@code magazin}/{@code mag_ammo}しか打っていないが、
     * 待機ポーズを土台に敷かないと<b>リロード中だけ手と銃本体がrestポーズへ飛ぶ</b>
     * （待機の手のポーズはrestからの差分なので、トラックが無い＝差分ゼロになってしまう）。</p>
     *
     * <p><b>加算ではなく上書き</b>にしてある。作者のクリップは「その時点の絶対ポーズ」として作られており
     * （{@code take_out}の終端は待機の手の値そのもの）、加算すると二重に効いて破綻するため。
     * 上書きの粒度は<b>チャンネル単位</b>（position/rotation/scale別）で、クリップが打っていない
     * チャンネルは土台の値がそのまま残る。</p>
     *
     * @param base    土台のクリップ（待機）。null なら重ねる側だけを使う。
     * @param overlay 上に重ねるクリップ。null なら土台だけを返す。
     */
    public static Map<String, Pose> sampleLayered(BakedAnimation base, float baseTime,
                                                   BakedAnimation overlay, float overlayTime) {
        Map<String, Pose> result = base != null ? sample(base, baseTime) : new HashMap<>();
        if (overlay == null) {
            return result;
        }
        for (Map.Entry<String, BoneTrack> entry : overlay.bones().entrySet()) {
            Pose merged = samplePose(entry.getValue(), overlayTime, result.get(entry.getKey()));
            if (merged != null) {
                result.put(entry.getKey(), merged);
            }
        }
        return result;
    }

    /**
     * 1ボーン分のトラックだけをサンプリングする。position/rotation/scale がどれも空なら null
     * （＝restポーズのまま）。特定ボーンを本体とは独立に動かす用途で使う
     * （{@link ShellEjectionTracker} の排莢インスタンス）。
     */
    public static Pose samplePose(BoneTrack track, float t) {
        return samplePose(track, t, null);
    }

    /**
     * {@code from} から {@code to} へ<b>値が変わったチャンネルだけ</b>を {@code target} へ上書きする。
     *
     * <p>用途は「状態として保持したい差分」を、再生中のモーションの上に貼り直すこと。撃ち切りの1発では
     * 発射モーション（銃全体の反動）を再生しつつ、弾切れポーズ（＝待機＋スライド後退）が待機と違えている
     * 部分＝スライドの後退だけを維持したい。差分だけを見るので、両者で同じ値のチャンネル
     * （例: 弾切れポーズの{@code root}は待機と同じ）は<b>モーション側の値が生き残る</b>。</p>
     *
     * <p>片方にしか無いボーンは、無い側を無変換（位置・回転0／等倍）とみなして比較する。</p>
     */
    public static void applyDifferences(Map<String, Pose> target, Map<String, Pose> from, Map<String, Pose> to) {
        for (Map.Entry<String, Pose> entry : to.entrySet()) {
            String boneName = entry.getKey();
            Pose after = entry.getValue();
            Pose before = from.get(boneName);
            Pose current = target.get(boneName);
            target.put(boneName, new Pose(
                    pickChanged(after.positionDelta(), channelOf(before, Pose::positionDelta),
                            channelOf(current, Pose::positionDelta), NO_DELTA),
                    pickChanged(after.rotationDeltaDeg(), channelOf(before, Pose::rotationDeltaDeg),
                            channelOf(current, Pose::rotationDeltaDeg), NO_DELTA),
                    pickChanged(after.scaleFactor(), channelOf(before, Pose::scaleFactor),
                            channelOf(current, Pose::scaleFactor), NO_SCALE)));
        }
    }

    /**
     * {@code after} が {@code before} から変わっていればその値を、変わっていなければ
     * {@code current}（再生中のモーションの値）を返す。値が無い側は {@code neutral}（無変換）とみなす。
     */
    private static Vector3f pickChanged(Vector3f after, Vector3f before, Vector3f current, Vector3f neutral) {
        boolean changed = !after.equals(before != null ? before : neutral);
        return new Vector3f(changed ? after : (current != null ? current : neutral));
    }

    private static Vector3f channelOf(Pose pose, Function<Pose, Vector3f> channel) {
        return pose == null ? null : channel.apply(pose);
    }

    /**
     * {@link #samplePose(BoneTrack, float)} と同じだが、トラックの無いチャンネルを
     * {@code under}（下に敷かれているポーズ）の値で埋める（{@link #sampleLayered} 用）。
     * {@code under} が null なら無変換（位置・回転0／等倍）で埋める。
     */
    private static Pose samplePose(BoneTrack track, float t, Pose under) {
        Vector3f pos = sampleTrack(track.position(), t);
        Vector3f rot = sampleTrack(track.rotation(), t);
        Vector3f scale = sampleTrack(track.scale(), t);
        if (pos == null && rot == null && scale == null) {
            return under; // このボーンについてクリップは何も言っていない: 土台のまま
        }
        return new Pose(
                pos != null ? pos : copyOr(under != null ? under.positionDelta() : null, new Vector3f()),
                rot != null ? rot : copyOr(under != null ? under.rotationDeltaDeg() : null, new Vector3f()),
                scale != null ? scale : copyOr(under != null ? under.scaleFactor() : null, NO_SCALE));
    }

    private static Vector3f copyOr(Vector3f value, Vector3f fallback) {
        return new Vector3f(value != null ? value : fallback);
    }

    /**
     * 区間 [a, b] の補間は「aから<b>出ていく</b>値（{@code post}）」→「bへ<b>入ってくる</b>値（{@code pre}）」で行う。
     * pre/postが違うキーフレームでは、その時刻で値が飛ぶ（Bedrockのスナップ表現）。
     */
    private static Vector3f sampleTrack(Keyframe[] frames, float t) {
        if (frames.length == 0) {
            return null;
        }
        if (frames.length == 1 || t <= frames[0].time()) {
            return new Vector3f(frames[0].pre());
        }
        Keyframe last = frames[frames.length - 1];
        if (t >= last.time()) {
            return new Vector3f(last.post());
        }
        for (int i = 0; i < frames.length - 1; i++) {
            Keyframe a = frames[i];
            Keyframe b = frames[i + 1];
            if (t >= a.time() && t <= b.time()) {
                float span = b.time() - a.time();
                float f = span <= 0f ? 0f : (t - a.time()) / span;
                return new Vector3f(a.post()).lerp(b.pre(), f);
            }
        }
        return new Vector3f(last.post());
    }
}
