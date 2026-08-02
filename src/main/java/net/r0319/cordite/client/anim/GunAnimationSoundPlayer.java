package net.r0319.cordite.client.anim;

import com.mojang.logging.LogUtils;
import net.minecraft.client.Minecraft;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.item.ItemStack;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.gunpack.GunDefinition;
import net.r0319.cordite.gunpack.GunDefinitions;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

/**
 * アニメーションの {@code sound_effects} キーフレームを再生する（docs/specs/06-animations.md
 * 「発射音・薬莢排出等のタイミングはアニメーションファイルに埋め込む」方針）。
 *
 * <p><b>表示中のアニメーションとは独立に走る</b>のがポイント。{@link GunAnimationState} は
 * 「今表示しているアクション」を1つしか持たないため、リロード開始直後に1発出た等で
 * fireがreloadを上書きすると、reloadの残りのサウンドキーフレームが鳴らないまま消えてしまう。
 * ここではクリップごとに独立したタイムライン（{@link Timeline}）を持ち、開始したものは
 * 表示が別のアクションへ移っても最後まで鳴らし切る。</p>
 *
 * <p><b>同種の重複は許さない</b>: 同じ系統（発射系／リロード系）のタイムラインは常に1本だけで、
 * 新しく始まった側が古い方を捨てる。連射で発射音が積み重なって鳴り続けるのを防ぐため。</p>
 *
 * <p><b>点検（inspect）だけは中断で鳴り止む</b>: 別のアクションが始まった時点で（{@link #start}）、
 * またはADSで畳まれた時点で（{@link #stopInspect}）タイムラインごと捨てる。上記「最後まで鳴らし切る」の
 * 唯一の例外で、リロードや発射に移った後で銃を眺める音だけが鳴り続けるのを避けるため。</p>
 *
 * <p><b>effect名の解決規則</b>: Blockbenchのキーフレームの「Effect」名をそのまま
 * サウンドイベントIDとして引く。名前空間を省略した場合は {@code cordite:} を補うので、
 * {@code smg_magazine_eject} と書けば {@link net.r0319.cordite.registry.ModSounds} の登録名に一致する
 * （登録名は音声ファイル名と揃えてあり、BlockbenchがEffect欄をファイル名から自動補完するため
 * 通常は手入力不要。ModSoundsのコメント参照）。
 * {@code minecraft:block.note_block.hat} のように名前空間付きで書けばバニラの音も鳴らせる。</p>
 *
 * <p><b>既知の制約</b>: アニメーション再生はクライアント側にしか存在せず、状態の同期経路がまだ無いため
 * （docs/design/00-architecture.md「アニメーション状態のネットワーク同期方式（未定）」）、ここで鳴らす音は
 * <b>自分にしか聞こえない</b>。周囲に聞こえる必要がある音（発射音）はサーバー側の {@code playSound}
 * で配信する（{@link GunDefinition#fireSound()}）。</p>
 *
 * <p><b>発射音のキーフレームは無視する</b>: 上記のとおり発射音はサーバーが配信するので、同じ音が
 * アニメーションの {@code sound_effects} にも入っていると<b>撃った本人にだけ二重に聞こえる</b>。
 * Blockbenchは音声ファイルを載せた時点でプレビュー再生できてしまうため、作者がモーションを詰める際に
 * 発射音を置いたまま書き出すのは自然な流れで、そのたびに手で消させるのは事故のもと。
 * そこで<b>持っている銃の {@code fireSound} と同じIDのキーフレームだけはここで鳴らさない</b>
 * （Blockbench上でのプレビューはそのまま効く）。</p>
 */
public final class GunAnimationSoundPlayer {
    private static final Logger LOGGER = LogUtils.getLogger();

    private GunAnimationSoundPlayer() {}

    /** タイムラインの系統。同じ系統は同時に1本まで。 */
    private enum Group { FIRE, RELOAD, EQUIP, INSPECT }

    /** 再生中のサウンドタイムライン1本ぶん。 */
    private static final class Timeline {
        final Group group;
        final BakedAnimation animation;
        /**
         * 再生速度スケール（クリップ内時刻 ÷ 実時間）。リロードは実リロード時間に合わせて伸縮するので1でない。
         * 表示側のアクションが先に終わっても、サウンドはクリップの最後まで同じ速度で鳴らし切る。
         */
        final float timeScale;
        final long startGameTime;
        /**
         * サーバーが配信する発射音のID。同じIDのキーフレームは鳴らさない（クラスコメントの
         * 「発射音のキーフレームは無視する」）。銃が特定できない場合は null。
         */
        final ResourceLocation serverSideFireSound;
        /** 直前に処理したクリップ内時刻。これより後〜今回の時刻までのキーフレームを鳴らす。 */
        float lastAnimTime = -1f;

        Timeline(Group group, BakedAnimation animation, float timeScale, long startGameTime,
                 ResourceLocation serverSideFireSound) {
            this.group = group;
            this.animation = animation;
            this.timeScale = timeScale;
            this.startGameTime = startGameTime;
            this.serverSideFireSound = serverSideFireSound;
        }
    }

    private static final List<Timeline> TIMELINES = new ArrayList<>();
    /** 解決に失敗したeffect名（毎tickログを出さないための記録）。 */
    private static final Set<String> WARNED_EFFECTS = new HashSet<>();
    /** 発射音として握り潰したeffect名（毎tickログを出さないための記録）。 */
    private static final Set<String> SUPPRESSED_EFFECTS = new HashSet<>();

    /**
     * アクションの再生開始に合わせてサウンドタイムラインを開始する。
     * サウンドキーフレームを持たないクリップでは新しいタイムラインを起こさない
     * （点検の打ち切りだけはクリップの中身に関わらず行う。下記参照）。
     *
     * @param stack 再生元の銃スタック。サーバー配信の発射音と重複するキーフレームを弾くために使う。
     */
    public static void start(GunAnimationState.Action action, GunActionPlayback.Clip clip, ItemStack stack,
                             long startGameTime) {
        Group group = groupOf(action);
        if (group != Group.INSPECT) {
            // 点検は他のアクションが始まった時点で中断される（GunAnimationState#play の上書き）。
            // 「開始したものは鳴らし切る」の例外で、中断された点検の音は残さない
            // ——リロードや発射に移った後で銃を眺める音だけが鳴り続けるのは明らかにおかしいため。
            stopInspect();
        }
        if (!clip.isPlayable() || clip.animation().soundEffects().isEmpty()) {
            return;
        }
        TIMELINES.removeIf(t -> t.group == group); // 同系統の古いタイムラインは捨てる（重複再生の防止）
        TIMELINES.add(new Timeline(group, clip.animation(), clip.timeScale(), startGameTime,
                serverSideFireSoundOf(stack)));
    }

    /** その銃の発射音（サーバーが {@code playSound} で配信するもの）のID。取れなければ null。 */
    private static ResourceLocation serverSideFireSoundOf(ItemStack stack) {
        if (!(stack.getItem() instanceof GunItem gunItem)) {
            return null;
        }
        ResourceLocation gunId = GunItem.gunId(stack);
        GunDefinition props = gunId == null ? null : GunDefinitions.client(gunId);
        if (props == null || props.fireSound() == null) {
            return null;
        }
        return props.fireSound().value().getLocation();
    }

    /** 全タイムラインを1tick進め、跨いだサウンドキーフレームを鳴らす。終わったものは片付ける。 */
    public static void tick(long gameTime) {
        for (Iterator<Timeline> it = TIMELINES.iterator(); it.hasNext(); ) {
            Timeline timeline = it.next();
            float elapsed = (gameTime - timeline.startGameTime) / 20f;
            float animTime = elapsed * timeline.timeScale;

            for (SoundKeyframe keyframe : timeline.animation.soundEffects()) {
                if (keyframe.time() > timeline.lastAnimTime && keyframe.time() <= animTime) {
                    play(keyframe.effect(), timeline.serverSideFireSound);
                }
            }
            timeline.lastAnimTime = animTime;

            if (animTime >= timeline.animation.lengthSeconds()) {
                it.remove();
            }
        }
    }

    /** 持ち替え・切断など、再生中のタイムラインを全部捨てる場面で呼ぶ。 */
    public static void reset() {
        TIMELINES.clear();
    }

    /**
     * 点検のサウンドタイムラインを捨てる（{@link GunAnimationState#cancelInspect} で中断したとき）。
     * 他のアクションによる中断は {@link #start} が自動で行うので、明示的に呼ぶ必要はない。
     */
    public static void stopInspect() {
        TIMELINES.removeIf(t -> t.group == Group.INSPECT);
    }

    private static Group groupOf(GunAnimationState.Action action) {
        return switch (action) {
            case TAKE_OUT -> Group.EQUIP;
            case FIRE, FIRE_EMPTY -> Group.FIRE;
            case RELOAD, RELOAD_EMPTY -> Group.RELOAD;
            case INSPECT, INSPECT_EMPTY -> Group.INSPECT;
        };
    }

    private static void play(String effect, ResourceLocation serverSideFireSound) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) {
            return;
        }
        ResourceLocation soundId = effect.indexOf(':') >= 0
                ? ResourceLocation.tryParse(effect)
                : ResourceLocation.fromNamespaceAndPath(Cordite.MODID, effect);
        if (soundId != null && soundId.equals(serverSideFireSound)) {
            // 発射音はサーバーが配信済み。ここで鳴らすと本人にだけ二重に聞こえる（クラスコメント参照）
            if (SUPPRESSED_EFFECTS.add(effect)) {
                LOGGER.debug("[Cordite] アニメーションのsound_effects '{}' はサーバー配信の発射音と重複するため"
                        + "クライアント側では鳴らしません", effect);
            }
            return;
        }
        SoundEvent sound = resolveSound(mc, soundId, effect);
        if (sound == null) {
            return;
        }
        // ローカルプレイヤー位置で鳴らす（クライアント側のみ。上記「既知の制約」を参照）
        mc.player.playSound(sound, 1.0f, 1.0f);
    }

    /**
     * effect名からサウンドイベントを解決する。鳴らせなければ null（警告は初回のみ）。
     *
     * <p><b>{@link net.r0319.cordite.registry.ModSounds} への登録は必須ではない</b>。ここで鳴らす音は
     * クライアントローカル再生で、音声ファイルの解決は{@code sounds.json}を読んだ
     * {@code SoundManager}が行うため、レジストリ登録が無くても{@code SoundEvent}をその場で
     * 作れば鳴る。登録が要るのは<b>サーバーから{@code playSound}で配信する音だけ</b>（発射音など。
     * レジストリIDでネットワーク越しに送るため）。</p>
     *
     * <p>この扱いにしているのは、アニメーションに音を足すたびにJavaのレジストリへ書き足す作業を
     * 無くすため。作者が作業フォルダにoggを置けば{@code syncGunAssets}がコピーし、
     * {@code generateSoundsJson}が{@code sounds.json}へエントリを補完するので、
     * <b>コード側の作業なしで鳴る</b>ようになる。</p>
     */
    private static SoundEvent resolveSound(Minecraft mc, ResourceLocation soundId, String effect) {
        if (soundId == null) {
            if (WARNED_EFFECTS.add(effect)) {
                LOGGER.warn("[Cordite] アニメーションのsound_effects '{}' はサウンドIDとして解釈できません", effect);
            }
            return null;
        }
        SoundEvent registered = BuiltInRegistries.SOUND_EVENT.get(soundId);
        if (registered != null) {
            return registered;
        }
        if (mc.getSoundManager().getSoundEvent(soundId) == null) {
            if (WARNED_EFFECTS.add(effect)) {
                LOGGER.warn("[Cordite] アニメーションのsound_effects '{}' に対応する音がありません"
                        + "（{} が sounds.json に無い。oggを作業フォルダに置いて再ビルドすると自動で追加されます）",
                        effect, soundId);
            }
            return null;
        }
        return SoundEvent.createVariableRangeEvent(soundId);
    }
}
