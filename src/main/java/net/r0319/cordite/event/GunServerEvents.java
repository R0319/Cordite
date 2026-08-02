package net.r0319.cordite.event;

import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.player.AttackEntityEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.level.BlockEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.combat.GunFireManager;
import net.r0319.cordite.combat.ProjectileManager;
import net.r0319.cordite.item.gun.FireMode;
import net.r0319.cordite.item.gun.GunItem;

/**
 * 銃関連のサーバーtick処理。射撃トリガーによる発射駆動とリロード完了を担当する。
 */
@EventBusSubscriber(modid = Cordite.MODID)
public final class GunServerEvents {
    private GunServerEvents() {}

    @SubscribeEvent
    public static void onPlayerTick(PlayerTickEvent.Post event) {
        Player player = event.getEntity();
        if (player.level().isClientSide) {
            return;
        }

        GunFireManager.State state = GunFireManager.get(player);
        ItemStack held = player.getMainHandItem();

        handleHeldChange(state, held);
        completeReloadIfDue(player, state, held);
        driveFiring(player, state, held);

        state.lastHeldStack = held;
    }

    /**
     * メインハンドのスタックが変わった（持ち替え）ときの過渡状態リセット。
     * リロードは銃ごとなので中断し、バースト残数も引き継がせない。
     */
    private static void handleHeldChange(GunFireManager.State state, ItemStack held) {
        if (held == state.lastHeldStack) {
            return; // 同一スタック（同じスロットを持ち続けている）
        }
        state.cancelReload();
        state.burstRemaining = 0;
        // 持ち替え直後にトリガー押しっぱなしで単発が暴発しないよう、押下済み扱いにする
        state.firedThisPress = true;
    }

    /**
     * リロード完了（時間経過後の実際の装填）。
     * リロードを開始した銃を今も持っている場合のみ装填する（持ち替えによる不正装填を防ぐ）。
     */
    private static void completeReloadIfDue(Player player, GunFireManager.State state, ItemStack held) {
        if (state.reloadCompleteTick == Long.MIN_VALUE) {
            return;
        }
        if (player.level().getGameTime() < state.reloadCompleteTick) {
            return;
        }
        ItemStack reloading = state.reloadingStack;
        state.cancelReload();

        if (held == reloading && held.getItem() instanceof GunItem gun) {
            gun.completeReload(held, player.level());
            // 装填音はアニメーションの sound_effects 側で鳴らす（GunItem#startReload のコメント参照）
        }
    }

    /** トリガー押下状態と発射モードに応じてサーバー側で発射する。 */
    private static void driveFiring(Player player, GunFireManager.State state, ItemStack held) {
        if (!(held.getItem() instanceof GunItem gun)) {
            // 銃を持っていない: トリガー状態をリセット
            state.triggerHeld = false;
            state.prevTriggerHeld = false;
            state.burstRemaining = 0;
            state.dryFiredThisPress = false;
            return;
        }

        boolean pressEdge = state.triggerHeld && !state.prevTriggerHeld;
        FireMode mode = gun.getFireMode(held, player.level());

        if (pressEdge) {
            state.firedThisPress = false;
            state.dryFiredThisPress = false; // 引き直しで空撃ち音を1回だけ鳴らし直す
            if (mode == FireMode.BURST) {
                state.burstRemaining = FireMode.BURST_COUNT;
            }
        }

        if (state.triggerHeld) {
            switch (mode) {
                case SINGLE -> {
                    if (!state.firedThisPress) {
                        gun.tryFire(player, held, state); // 押下ごとに1発（空撃ちも1回）
                        state.firedThisPress = true;
                    }
                }
                case FULL_AUTO -> gun.tryFire(player, held, state);
                case BURST -> {
                    if (state.burstRemaining > 0 && gun.tryFire(player, held, state)) {
                        state.burstRemaining--;
                    }
                }
            }
        }

        state.prevTriggerHeld = state.triggerHeld;
    }

    @SubscribeEvent
    public static void onServerTick(ServerTickEvent.Post event) {
        ProjectileManager.tick();
    }

    @SubscribeEvent
    public static void onServerStopping(ServerStoppingEvent event) {
        ProjectileManager.clear();
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        GunFireManager.clear(event.getEntity());
    }

    /**
     * 銃所持中はブロック破壊を禁止（サーバー権威）。クライアント側の左クリック抑制
     * （{@link net.r0319.cordite.client.ClientInputHandler}）に加え、サーバーでも確実に止める。
     */
    @SubscribeEvent
    public static void onBlockBreak(BlockEvent.BreakEvent event) {
        if (event.getPlayer().getMainHandItem().getItem() instanceof GunItem) {
            event.setCanceled(true);
        }
    }

    /**
     * 銃所持中は近接攻撃（殴打）を禁止（サーバー権威）。クライアント側の左クリック抑制だけでは
     * 改造クライアントの直接パケット送信を防げないため、サーバーでも止める。
     */
    @SubscribeEvent
    public static void onAttackEntity(AttackEntityEvent event) {
        if (event.getEntity().getMainHandItem().getItem() instanceof GunItem) {
            event.setCanceled(true);
        }
    }
}
