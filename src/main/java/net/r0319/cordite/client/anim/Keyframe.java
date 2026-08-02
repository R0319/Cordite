package net.r0319.cordite.client.anim;

import org.joml.Vector3f;

/**
 * アニメーション1本・1ボーンの1キーフレーム（時刻[秒]と値）。
 *
 * <p>Bedrockのキーフレームは値を2つ持てる: {@code pre}＝この時刻に<b>入ってくる</b>ときの値、
 * {@code post}＝この時刻から<b>出ていく</b>ときの値。両者が違うとその時刻で値が飛ぶ（スナップ）。
 * Blockbenchでは {@code {"pre": [...], "post": [...]}} という形で書き出される。
 * 単純な数値配列で書かれたキーフレームでは両方に同じ値が入る。</p>
 *
 * @param time 秒
 * @param pre  この時刻へ向かって補間するときの終点値
 * @param post この時刻から次のキーフレームへ補間するときの始点値
 */
public record Keyframe(float time, Vector3f pre, Vector3f post) {
    /** pre/postが同じ（通常のキーフレーム）用のコンストラクタ。 */
    public Keyframe(float time, Vector3f value) {
        this(time, value, value);
    }
}
