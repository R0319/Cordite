package net.r0319.cordite.network;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.combat.GunFireManager;
import net.r0319.cordite.item.gun.GunItem;

/** C→S パケットの登録とハンドラ。すべてサーバー側で手持ち銃に対して実行する。 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD)
public final class ModNetwork {
    private ModNetwork() {}

    @SubscribeEvent
    public static void register(RegisterPayloadHandlersEvent event) {
        var registrar = event.registrar("1");
        registrar.playToServer(CycleFireModePayload.TYPE, CycleFireModePayload.CODEC, ModNetwork::onCycleFireMode);
        registrar.playToServer(ReloadPayload.TYPE, ReloadPayload.CODEC, ModNetwork::onReload);
        registrar.playToServer(SetTriggerPayload.TYPE, SetTriggerPayload.CODEC, ModNetwork::onSetTrigger);
    }

    private static void onSetTrigger(SetTriggerPayload payload, IPayloadContext context) {
        context.enqueueWork(() -> {
            if (context.player() instanceof ServerPlayer player) {
                GunFireManager.get(player).triggerHeld = payload.pressed();
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
