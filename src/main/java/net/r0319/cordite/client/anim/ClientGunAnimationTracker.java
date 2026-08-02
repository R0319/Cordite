package net.r0319.cordite.client.anim;

import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.model.GunModelCache;
import net.r0319.cordite.item.gun.GunItem;

/**
 * メインハンドの銃について、アニメーション再生状態を毎tick進める（終了判定・サウンドキーフレームの進行・
 * 飛び終わった薬莢の破棄）。
 *
 * <p>再生の<b>開始</b>はここでは行わない。発射は{@link net.r0319.cordite.network.GunFiredPayload}
 * （サーバーが1発撃つたびに本人へ送る演出トリガー）、リロードは
 * {@link net.r0319.cordite.client.ClientInputHandler}のローカル予測が起点になる。</p>
 *
 * <p>以前は残弾データコンポーネントの同期差分で発射を検知していたが、スロット同期が発射音より
 * 遅れて届くため反動アニメーションが銃声からずれ、フルオートでは減少がまとめて届いて1発ぶんしか
 * 再生されなかった。{@code GunFiredPayload}への移行でどちらも解消している。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class ClientGunAnimationTracker {
    private ClientGunAnimationTracker() {}

    /** サウンドタイムラインを起こした最後の再生通し番号（{@link GunAnimationState#playId}）。 */
    private static long lastSoundPlayId = -1L;

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) {
            reset();
            return;
        }

        ItemStack held = mc.player.getMainHandItem();
        if (!(held.getItem() instanceof GunItem)) {
            reset();
            return;
        }

        long gameTime = mc.level.getGameTime();
        ResourceLocation gunId = GunItem.gunId(held);
        if (gunId == null) {
            reset();
            return;
        }
        String gunPath = gunId.getPath();

        // 表示側のアクション終了判定（戻り値は描画側でしか使わない）。毎tick回しておくことで
        // GunAnimationState#isReloading が古い状態を返さず、発射アニメの割り込み判定が正しく効く。
        GunActionPlayback.current(gunPath, held, gameTime, 0f);

        advanceAnimationSounds(gunPath, held, gameTime);
        pruneEjectedShells(gunPath, gameTime);
    }

    /**
     * 飛び終わった薬莢を捨てる（{@link ShellEjectionTracker}）。寿命は排莢クリップの
     * <b>最後のキーフレーム時刻</b>で、{@code animation_length}ではない。動きが終わった後の時刻を
     * サンプリングすると最後の値が返り続けるため、クリップ長を寿命にすると軌道の終点で薬莢が
     * 空中に停止して見えるので、動きが終わった時点で消す。
     *
     * <p>作者が排莢クリップにキーフレームを足せば、そのぶん薬莢が長く飛ぶ（コード側の調整は不要）。
     * 排莢クリップが無い銃は寿命0＝薬莢が飛ばないだけで、他の挙動は変わらない。</p>
     */
    private static void pruneEjectedShells(String gunId, long gameTime) {
        BakedAnimation eject = GunModelCache.getEjectAnimation(gunId);
        ShellEjectionTracker.prune(eject == null ? 0f : eject.lastKeyframeSeconds(), gameTime);
    }

    /**
     * アニメーションの {@code sound_effects} を進める。描画側（毎フレーム）ではなくtickで駆動するのは、
     * 同じ音が1tick内に何度も鳴ったり、パーシャルティックの戻りで二重再生されるのを避けるため。
     * タイミング精度は1tick（50ms）刻みになる。
     *
     * <p>再生開始（{@link GunAnimationState#playId}の変化）を見てサウンドタイムラインを起こし、
     * あとは{@link GunAnimationSoundPlayer}が表示中のアクションとは独立に進める。これにより、
     * リロード中に表示が別のアクションへ移っても、リロードの音は最後まで鳴り切る。</p>
     */
    private static void advanceAnimationSounds(String gunId, ItemStack held, long gameTime) {
        long playId = GunAnimationState.playId();
        GunAnimationState.Action action = GunAnimationState.currentAction();
        if (playId != lastSoundPlayId) {
            lastSoundPlayId = playId;
            if (action != null) {
                GunAnimationSoundPlayer.start(action, GunActionPlayback.resolve(gunId, held, action), held, gameTime);
            }
        }
        GunAnimationSoundPlayer.tick(gameTime);
    }

    private static void reset() {
        lastSoundPlayId = GunAnimationState.playId();
        GunAnimationSoundPlayer.reset();
        ShellEjectionTracker.reset();
        MuzzleFlashState.reset();
        ReticleKickState.reset();
    }
}
