package net.r0319.cordite.client.anim;

/**
 * {@code animation.json} の {@code sound_effects} キーフレーム1個。
 *
 * @param time   アニメーション先頭からの秒数
 * @param effect Blockbench上でキーフレームに入力された「Effect」名。Cordite側でサウンドイベントIDとして
 *               解決する（名前空間省略時は {@code cordite:}）。→ {@link GunAnimationSoundPlayer}
 */
public record SoundKeyframe(float time, String effect) {}
