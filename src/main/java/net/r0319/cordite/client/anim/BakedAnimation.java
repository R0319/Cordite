package net.r0319.cordite.client.anim;

import java.util.Map;

/** ロード済みの1アニメーションクリップ（ボーン名→トラック）。 */
public record BakedAnimation(float lengthSeconds, Map<String, BoneTrack> bones) {}
