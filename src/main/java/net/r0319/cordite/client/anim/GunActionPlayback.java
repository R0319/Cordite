package net.r0319.cordite.client.anim;

import net.minecraft.world.item.ItemStack;
import net.r0319.cordite.client.model.GunModelCache;
import net.r0319.cordite.gunpack.GunDefinition;
import net.r0319.cordite.gunpack.GunDefinitions;
import net.r0319.cordite.item.gun.GunItem;

/**
 * 再生中のアクション（fire/reload/reload_empty）について「どのクリップを・クリップ内の何秒目で」
 * 再生すべきかを求める。描画（{@link net.r0319.cordite.client.render.GunItemRenderer}）と
 * サウンド再生（{@link GunAnimationSoundPlayer}）で同じ再生位置を使うために切り出してある。
 *
 * <p>reload/reload_empty はクリップ自体の長さ（例 2.7083秒）と実際のリロード時間
 * （{@link GunDefinition#reloadSeconds()}、🟡仮のバランス値）が一致しないため、実際のリロード時間に
 * 収まるよう再生速度をスケーリングする。fireは反動の"キック"表現なのでスケーリングしない。</p>
 */
public final class GunActionPlayback {
    private GunActionPlayback() {}

    /** 再生中のクリップとクリップ内時刻（秒）。 */
    public record Sample(GunAnimationState.Action action, BakedAnimation animation, float animTime) {}

    /**
     * アクションに対応するクリップ・そのアクションが続く実時間・再生速度スケール。クリップが無い／
     * 長さが取れない場合は {@code animation}がnullか{@code realDurationSeconds}が0以下になる。
     *
     * <p><b>「いつ終わるか」と「どの速さで再生するか」は別物</b>なので分けてある。リロードは
     * クリップ全体を実リロード時間に収めるので両者が連動するが、発射は等速再生のまま
     * <b>動きが終わった時点で終了させたい</b>（下記 {@link #resolve} を参照）。</p>
     */
    public record Clip(BakedAnimation animation, float realDurationSeconds, float timeScale) {
        public boolean isPlayable() {
            return animation != null && realDurationSeconds > 0f;
        }

        /** クリップ内時刻＝経過実時間 × 再生速度スケール。 */
        public float animTimeAt(float elapsedSeconds) {
            return elapsedSeconds * timeScale;
        }
    }

    /**
     * 指定アクションのクリップと実時間を引く（再生中かどうかとは無関係）。
     *
     * <p><b>発射は{@code animation_length}ではなく最後のキーフレームまでで終わらせる</b>。Blockbenchの
     * {@code animation_length}はタイムラインの長さであって動きの終わりではなく、glockの{@code fire}は
     * 0.5833秒あるのに動きは0.1667秒で終わっている。{@code animation_length}を採用すると、
     * <b>撃ち切った後もスライドが前進したまま0.4秒以上固まってから弾切れ待機へ切り替わる</b>
     * （＝チャンバーが遅れて開く）。排莢の寿命判定と同じ考え方（{@link BakedAnimation#lastKeyframeSeconds}）。</p>
     */
    public static Clip resolve(String gunId, ItemStack stack, GunAnimationState.Action action) {
        BakedAnimation animation = switch (action) {
            case TAKE_OUT -> GunModelCache.getAnimation(gunId, GunModelCache.Clips.TAKE_OUT);
            case FIRE -> GunModelCache.getFireAnimation(gunId);
            // 撃ち切り専用クリップ（スライドが後退したまま終わる）。未作成なら通常のfireで代用する。
            // fireはスライドが前進して終わるクリップだが、描画側が弾切れポーズの差分
            // （＝スライドの後退）を最後に貼り直すので閉じてしまわない
            // （GunItemRenderer#pinEmptyHoldOpen）。これにより「撃ち切った1発だけ反動が消える」
            // ということもなく、作者はfire_emptyを作らなくてよい。
            case FIRE_EMPTY -> fireEmptyOr(gunId, GunModelCache.getFireAnimation(gunId));
            case RELOAD -> GunModelCache.getReloadAnimation(gunId);
            case RELOAD_EMPTY -> GunModelCache.getReloadEmptyAnimation(gunId);
            case INSPECT -> GunModelCache.getAnimation(gunId, GunModelCache.Clips.INSPECT);
            // 弾切れ点検（スライドが後退したまま眺める）。未作成なら通常のinspectで代用する
            case INSPECT_EMPTY -> inspectEmptyOr(gunId, GunModelCache.getAnimation(gunId, GunModelCache.Clips.INSPECT));
        };
        if (animation == null) {
            return new Clip(null, 0f, 1f);
        }
        return switch (action) {
            // 取り出しは等速で、クリップの動きが終わったらidleへ。ゲームプレイ側の持ち替え時間という
            // 概念がまだ無いので、長さは作者が作ったクリップそのままになる。
            // 点検も等速。ゲームプレイ側に「点検にかかる時間」という概念が無いので、
            // 長さは作者が作ったクリップそのままになる（取り出しと同じ扱い）。
            case TAKE_OUT, FIRE, FIRE_EMPTY, INSPECT, INSPECT_EMPTY ->
                    new Clip(animation, motionEndSeconds(animation), 1f);
            case RELOAD, RELOAD_EMPTY -> {
                float reloadSeconds = reloadSecondsOf(stack);
                yield new Clip(animation, reloadSeconds,
                        reloadSeconds > 0f ? animation.lengthSeconds() / reloadSeconds : 1f);
            }
        };
    }

    /** 撃ち切り専用クリップ（{@code fire_empty}）。未作成なら {@code fallback}（通常のfire）。 */
    private static BakedAnimation fireEmptyOr(String gunId, BakedAnimation fallback) {
        BakedAnimation dedicated = GunModelCache.getAnimation(gunId, GunModelCache.Clips.FIRE_EMPTY);
        return dedicated != null ? dedicated : fallback;
    }

    /** 弾切れ点検クリップ（{@code inspect_empty}）。未作成なら {@code fallback}（通常のinspect）。 */
    private static BakedAnimation inspectEmptyOr(String gunId, BakedAnimation fallback) {
        BakedAnimation dedicated = GunModelCache.getAnimation(gunId, GunModelCache.Clips.INSPECT_EMPTY);
        return dedicated != null ? dedicated : fallback;
    }

    /**
     * 撃ち切り専用クリップ（{@code fire_empty}）が用意されているか。用意されていれば
     * スライドの扱いはそのクリップに任せる（描画側が弾切れポーズを貼り直さない）。
     */
    public static boolean hasDedicatedFireEmpty(String gunId) {
        return GunModelCache.getAnimation(gunId, GunModelCache.Clips.FIRE_EMPTY) != null;
    }

    /**
     * 動きが終わる時刻[秒]。キーフレームが時刻0にしか無い（静止ポーズだけの）クリップでは0になるので、
     * その場合だけ{@code animation_length}へ戻す（そうしないとアクションが即終了してしまう）。
     */
    private static float motionEndSeconds(BakedAnimation animation) {
        float lastKeyframe = animation.lastKeyframeSeconds();
        return lastKeyframe > 0f ? lastKeyframe : animation.lengthSeconds();
    }

    /**
     * 現在の再生状態を求める。アクション再生中でなければ null（呼び出し側はidleへフォールバックする）。
     * 終了判定（{@link GunAnimationState#clearIfFinished}）もここで行う。
     */
    public static Sample current(String gunId, ItemStack stack, long gameTime, float partialTick) {
        GunAnimationState.Action action = GunAnimationState.currentAction();
        if (action == null) {
            return null;
        }

        Clip clip = resolve(gunId, stack, action);
        if (!clip.isPlayable()) {
            // クリップが無い／長さが取れない: 再生状態だけ即座に畳んでidleへ戻す
            GunAnimationState.clearIfFinished(0f, gameTime, partialTick);
            return null;
        }

        GunAnimationState.clearIfFinished(clip.realDurationSeconds(), gameTime, partialTick);
        if (GunAnimationState.currentAction() != action) {
            return null; // 今の判定で終了した
        }

        float elapsed = GunAnimationState.elapsedSeconds(gameTime, partialTick);
        return new Sample(action, clip.animation(), clip.animTimeAt(elapsed));
    }

    private static float reloadSecondsOf(ItemStack stack) {
        if (stack.getItem() instanceof GunItem) {
            var gunId = GunItem.gunId(stack);
            GunDefinition props = gunId == null ? null : GunDefinitions.client(gunId);
            if (props != null) {
                return props.reloadSeconds();
            }
        }
        return 0f;
    }
}
