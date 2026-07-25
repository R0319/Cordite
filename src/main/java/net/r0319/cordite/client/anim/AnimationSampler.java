package net.r0319.cordite.client.anim;

import org.joml.Vector3f;

import java.util.HashMap;
import java.util.Map;

/**
 * アニメーションを指定時刻でサンプリングする。線形補間のみ（パフォーマンス方針、
 * docs/specs/06-animations.md 参照）。トラックを持たないボーンは結果に含めない
 * （＝レンダラー側は restポーズのまま扱う）。
 */
public final class AnimationSampler {
    private AnimationSampler() {}

    /** ボーンのrestポーズからの差分。position はブロック単位、rotation は度。 */
    public record Pose(Vector3f positionDelta, Vector3f rotationDeltaDeg) {}

    public static Map<String, Pose> sample(BakedAnimation anim, float t) {
        Map<String, Pose> result = new HashMap<>();
        for (Map.Entry<String, BoneTrack> entry : anim.bones().entrySet()) {
            BoneTrack track = entry.getValue();
            Vector3f pos = sampleTrack(track.position(), t);
            Vector3f rot = sampleTrack(track.rotation(), t);
            if (pos != null || rot != null) {
                result.put(entry.getKey(), new Pose(
                        pos != null ? pos : new Vector3f(),
                        rot != null ? rot : new Vector3f()));
            }
        }
        return result;
    }

    private static Vector3f sampleTrack(Keyframe[] frames, float t) {
        if (frames.length == 0) {
            return null;
        }
        if (frames.length == 1 || t <= frames[0].time()) {
            return new Vector3f(frames[0].value());
        }
        Keyframe last = frames[frames.length - 1];
        if (t >= last.time()) {
            return new Vector3f(last.value());
        }
        for (int i = 0; i < frames.length - 1; i++) {
            Keyframe a = frames[i];
            Keyframe b = frames[i + 1];
            if (t >= a.time() && t <= b.time()) {
                float span = b.time() - a.time();
                float f = span <= 0f ? 0f : (t - a.time()) / span;
                return new Vector3f(a.value()).lerp(b.value(), f);
            }
        }
        return new Vector3f(last.value());
    }
}
