package net.r0319.cordite.event;

import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
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

        completeReloadIfDue(player, state);
        driveFiring(player, state);
    }

    /** リロード完了（時間経過後の実際の装填）。 */
    private static void completeReloadIfDue(Player player, GunFireManager.State state) {
        if (state.reloadCompleteTick == Long.MIN_VALUE) {
            return;
        }
        if (player.level().getGameTime() >= state.reloadCompleteTick) {
            state.reloadCompleteTick = Long.MIN_VALUE;

            ItemStack held = player.getMainHandItem();
            if (held.getItem() instanceof GunItem gun) {
                gun.completeReload(held);
                player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                        SoundEvents.CROSSBOW_LOADING_END, SoundSource.PLAYERS, 1.0f, 1.0f);
            }
        }
    }

    /** トリガー押下状態と発射モードに応じてサーバー側で発射する。 */
    private static void driveFiring(Player player, GunFireManager.State state) {
        ItemStack held = player.getMainHandItem();
        if (!(held.getItem() instanceof GunItem gun)) {
            // 銃を持っていない: トリガー状態をリセット
            state.triggerHeld = false;
            state.prevTriggerHeld = false;
            state.burstRemaining = 0;
            return;
        }

        boolean pressEdge = state.triggerHeld && !state.prevTriggerHeld;
        FireMode mode = gun.getFireMode(held);

        if (pressEdge) {
            state.firedThisPress = false;
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
}
