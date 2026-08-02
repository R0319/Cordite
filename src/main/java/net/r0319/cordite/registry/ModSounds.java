package net.r0319.cordite.registry;

import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;

/**
 * 銃まわりのサウンドイベント。実体の音声ファイルは {@code assets/cordite/sounds/gun/*.ogg}、
 * 対応表は {@code assets/cordite/sounds.json}（作者制作アセット）。
 *
 * <p><b>登録名 = 音声ファイル名 = アニメーションの {@code sound_effects} に書く名前</b>、の3つを
 * 一致させてある。Blockbenchはサウンドキーフレームに音声ファイルを載せるとファイル名から
 * 「Effect」欄を自動補完するので、名前を揃えておけば<b>作者がEffect名を手入力する必要がなくなる</b>。
 * 手入力の工程が残っていると入れ忘れたまま書き出され、{@code "sound_effects": {}} になって
 * 無音のまま気付けない（実際に起きた。docs/design/animation-system.md「アセット側の注意」）。
 *
 * <p><b>ここに登録が要るのは「サーバーから {@code playSound} で配信する音」だけ</b>（発射音など。
 * レジストリIDでネットワーク越しに送るため）。アニメーションの {@code sound_effects} から鳴らす音は
 * クライアントローカル再生なので登録不要で、{@code sounds.json} にエントリがあれば鳴る
 * （{@link net.r0319.cordite.client.anim.GunAnimationSoundPlayer#resolveSound}）。
 * その {@code sounds.json} も ogg を作業フォルダに置けばビルド時に自動補完されるため、
 * <b>リロード音などを足すのにこのファイルを編集する必要はない</b>。</p>
 *
 * <p>そのため<b>ここの登録名は勝手に変えないこと</b>。変えるなら
 * {@code assets/cordite/sounds/gun/*.ogg} のファイル名・作者の作業フォルダ側の音声ファイル名・
 * {@code sounds.json} のキーも同時に揃える。読み替えは
 * {@link net.r0319.cordite.client.anim.GunAnimationSoundPlayer} が {@code cordite:} 名前空間を補って行う。</p>
 */
public final class ModSounds {
    private ModSounds() {}

    public static final DeferredRegister<SoundEvent> SOUNDS =
            DeferredRegister.create(Registries.SOUND_EVENT, Cordite.MODID);

    /** 発射音（拳銃）。サーバー側の {@code playSound} で周囲へ配信する。 */
    public static final DeferredHolder<SoundEvent, SoundEvent> PISTOL_FIRE = register("pistol_fire");
    /** リロード: マガジンを抜く音。アニメーションの {@code sound_effects} から鳴らす。 */
    public static final DeferredHolder<SoundEvent, SoundEvent> MAGAZINE_EJECT = register("smg_magazine_eject");
    /** リロード: マガジンを挿す音。アニメーションの {@code sound_effects} から鳴らす。 */
    public static final DeferredHolder<SoundEvent, SoundEvent> MAGAZINE_INSERT = register("smg_magazine_insert");

    private static DeferredHolder<SoundEvent, SoundEvent> register(String name) {
        return SOUNDS.register(name, () -> SoundEvent.createVariableRangeEvent(
                ResourceLocation.fromNamespaceAndPath(Cordite.MODID, name)));
    }
}
