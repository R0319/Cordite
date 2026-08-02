package net.r0319.cordite.client.anim;

/**
 * 1ボーン分の position/rotation/scale キーフレーム列（時刻昇順ソート済み）。
 * scale はリロード中にマガジン内の弾（{@code mag_ammo}）を消す等に使われる。
 */
public record BoneTrack(Keyframe[] position, Keyframe[] rotation, Keyframe[] scale) {}
