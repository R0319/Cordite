package net.r0319.cordite.client.anim;

import java.util.List;
import java.util.Map;

/**
 * ロード済みの1アニメーションクリップ（ボーン名→トラック、および時刻付きのサウンドキーフレーム）。
 *
 * @param soundEffects 時刻昇順。{@code sound_effects} が空/未記載なら空リスト。
 */
public record BakedAnimation(float lengthSeconds, Map<String, BoneTrack> bones, List<SoundKeyframe> soundEffects) {

    /**
     * 最後のキーフレームの時刻[秒]。キーフレームが1つも無ければ0。
     *
     * <p>{@link #lengthSeconds}（{@code animation_length}）とは別物で、こちらは<b>実際に動きが
     * 終わる時刻</b>。動きが終わった後の時刻をサンプリングすると{@link AnimationSampler}は最後の値を
     * 返し続けるため、「動き終わったら消す」寿命判定にはこちらを使う（{@link ShellEjectionTracker}）。</p>
     */
    public float lastKeyframeSeconds() {
        float last = 0f;
        for (BoneTrack track : bones.values()) {
            last = Math.max(last, lastTime(track.position()));
            last = Math.max(last, lastTime(track.rotation()));
            last = Math.max(last, lastTime(track.scale()));
        }
        return last;
    }

    private static float lastTime(Keyframe[] frames) {
        return frames.length == 0 ? 0f : frames[frames.length - 1].time();
    }
}
