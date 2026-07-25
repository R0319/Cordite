package net.r0319.cordite.client.anim;

/** 1ボーン分の position/rotation キーフレーム列（時刻昇順ソート済み）。 */
public record BoneTrack(Keyframe[] position, Keyframe[] rotation) {}
