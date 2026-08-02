package net.r0319.cordite.network;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.GunAnimationState;
import net.r0319.cordite.client.anim.GunRecoilState;
import net.r0319.cordite.client.anim.MuzzleFlashState;
import net.r0319.cordite.client.anim.ReticleKickState;
import net.r0319.cordite.client.anim.ShellEjectionTracker;
import net.r0319.cordite.client.render.TracerState;
import net.r0319.cordite.combat.GunFireManager;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.gunpack.GunDefinitions;
import net.r0319.cordite.gunpack.GunDefinition;

/**
 * パケットの登録とハンドラ。C→Sは入力（トリガー/リロード/モード切替）で、すべてサーバー側で
 * 手持ち銃に対して実行する。S→Cは演出トリガーのみ（{@link GunFiredPayload}）。
 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD)
public final class ModNetwork {
    private ModNetwork() {}

    @SubscribeEvent
    public static void register(RegisterPayloadHandlersEvent event) {
        var registrar = event.registrar("1");
        registrar.playToServer(CycleFireModePayload.TYPE, CycleFireModePayload.CODEC, ModNetwork::onCycleFireMode);
        registrar.playToServer(ReloadPayload.TYPE, ReloadPayload.CODEC, ModNetwork::onReload);
        registrar.playToServer(SetTriggerPayload.TYPE, SetTriggerPayload.CODEC, ModNetwork::onSetTrigger);
        registrar.playToServer(SetAdsPayload.TYPE, SetAdsPayload.CODEC, ModNetwork::onSetAds);
        registrar.playToClient(GunFiredPayload.TYPE, GunFiredPayload.CODEC, ModNetwork::onGunFired);
        registrar.playToClient(TracerPayload.TYPE, TracerPayload.CODEC, ModNetwork::onTracer);
        registrar.playToClient(SyncGunDefinitionsPayload.TYPE, SyncGunDefinitionsPayload.CODEC,
                ModNetwork::onSyncGunDefinitions);
    }

    /**
     * 曳光弾を1本、クライアント側の表示リストへ積む（当たり判定は持たない見た目だけのもの）。
     * 停止距離の算出に必要なブロックのレイキャストは{@link TracerState#spawn}が行う。
     */
    private static void onTracer(TracerPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> TracerState.spawn(
                context.player().level(), payload.origin(), payload.direction(),
                payload.speed(), payload.maxDistance(), context.player()));
    }

    /** サーバーから同期された定義をクライアント側の専用マップへ反映する。 */
    private static void onSyncGunDefinitions(SyncGunDefinitionsPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> GunDefinitions.replaceClient(payload.definitions()));
    }

    /**
     * 発射アニメーションと排莢の再生開始（クライアント側で実行）。
     *
     * <p>ハンドラから触るのは{@link GunAnimationState}と{@link ShellEjectionTracker}だけで、どちらも
     * {@code client}パッケージにあるがMinecraftのクライアント専用クラスを一切参照しない素のJavaクラス
     * なので、専用サーバーでこのクラスがロードされても問題ない。ゲーム時刻も
     * {@code Minecraft.getInstance()}ではなく{@link IPayloadContext#player()}
     * （クライアントではローカルプレイヤー）から取る。</p>
     *
     * <p>薬莢は発射クリップとは別に多重再生する（連射で前の薬莢が銃へ戻らないようにするため。
     * {@link ShellEjectionTracker}）。発射アニメーションを抑止したとき（リロード中に遅れて届いた
     * トリガー）は薬莢も飛ばさず、視点キックもしない。</p>
     *
     * <p>視点キック（{@link GunRecoilState}）もここで始める。視点はMCの構造上クライアントが持つが、
     * 動かした向きは毎tickサーバーへ送られるので、次以降の弾はサーバー側でもズレた方向へ飛ぶ
     * （発射方向はサーバーがプレイヤーの向きから算出する）。</p>
     */
    private static void onGunFired(GunFiredPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> {
            long gameTime = context.player().level().getGameTime();
            if (!GunAnimationState.playFire(gameTime, payload.emptyAfterShot())) {
                return;
            }
            ShellEjectionTracker.start(gameTime);
            MuzzleFlashState.flash(gameTime);
            if (context.player().getMainHandItem().getItem() instanceof GunItem gun) {
                ItemStack stack = context.player().getMainHandItem();
                var gunId = GunItem.gunId(stack);
                GunDefinition props = gunId == null ? null : GunDefinitions.client(gunId);
                if (props != null) {
                    GunRecoilState.kick(props.recoilPitch(), props.recoilYaw());
                    ReticleKickState.kick(gameTime, props.recoilPitch());
                }
            }
        });
    }

    private static void onSetTrigger(SetTriggerPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> {
            if (context.player() instanceof ServerPlayer player) {
                GunFireManager.get(player).triggerHeld = payload.pressed();
            }
        });
    }

    /** ADS状態の保持。腰だめ時の拡散判定（{@link net.r0319.cordite.combat.ProjectileManager}）に使う。 */
    private static void onSetAds(SetAdsPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> {
            if (context.player() instanceof ServerPlayer player) {
                GunFireManager.get(player).aiming = payload.aiming();
            }
        });
    }

    private static void onCycleFireMode(CycleFireModePayload payload, IPayloadContext context) {
        context.enqueueWork(() -> withHeldGun(context, (player, stack, gun) -> gun.cycleFireMode(player, stack)));
    }

    private static void onReload(ReloadPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> withHeldGun(context, (player, stack, gun) -> gun.startReload(player, stack)));
    }

    private interface GunAction {
        void run(ServerPlayer player, ItemStack stack, GunItem gun);
    }

    private static void withHeldGun(IPayloadContext context, GunAction action) {
        if (!(context.player() instanceof ServerPlayer player)) {
            return;
        }
        ItemStack stack = player.getItemInHand(InteractionHand.MAIN_HAND);
        if (stack.getItem() instanceof GunItem gun) {
            action.run(player, stack, gun);
        }
    }
}
