package net.r0319.cordite.client.anim;

import org.joml.Vector3f;

/** アニメーション1本・1ボーンの1キーフレーム（時刻[秒]と値）。 */
public record Keyframe(float time, Vector3f value) {}
