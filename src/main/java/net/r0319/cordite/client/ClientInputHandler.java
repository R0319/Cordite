package net.r0319.cordite.client;

import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.InputEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.network.CycleFireModePayload;
import net.r0319.cordite.network.ReloadPayload;
import net.r0319.cordite.network.SetTriggerPayload;

/**
 * クライアントの銃入力。左クリック=射撃（トリガー状態をサーバーへ送信）、V=モード切替、R=リロード。
 * 銃所持中は左クリックのバニラ挙動（ブロック破壊・近接攻撃）を抑制する。実際の発射処理はサーバー側。
 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class ClientInputHandler {
    private ClientInputHandler() {}

    /** 直近でサーバーへ送ったトリガー状態（変化時のみ送信）。 */
    private static boolean lastTriggerSent = false;

    private static boolean holdingGun(Minecraft mc) {
        return mc.player != null && mc.player.getMainHandItem().getItem() instanceof GunItem;
    }

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.getConnection() == null) {
            lastTriggerSent = false; // 未接続: 送信状態をリセット
            return;
        }

        boolean holdingGun = holdingGun(mc);
        boolean guiOpen = mc.screen != null;

        // モード切替・リロード（銃所持かつGUI非表示時のみ）
        while (ModKeyMappings.CYCLE_FIRE_MODE.consumeClick()) {
            if (holdingGun && !guiOpen) {
                PacketDistributor.sendToServer(CycleFireModePayload.INSTANCE);
            }
        }
        while (ModKeyMappings.RELOAD.consumeClick()) {
            if (holdingGun && !guiOpen) {
                PacketDistributor.sendToServer(ReloadPayload.INSTANCE);
            }
        }

        // 射撃トリガー（左クリック押下状態の変化を送信）
        boolean wantFire = holdingGun && !guiOpen
                && mc.mouseHandler.isMouseGrabbed()
                && mc.options.keyAttack.isDown();
        if (wantFire != lastTriggerSent) {
            PacketDistributor.sendToServer(new SetTriggerPayload(wantFire));
            lastTriggerSent = wantFire;
        }
    }

    /** 銃所持中は左クリック（攻撃）のバニラ処理を抑制（近接攻撃・ブロック破壊開始を止める）。 */
    @SubscribeEvent
    public static void onAttackInput(InputEvent.InteractionKeyMappingTriggered event) {
        Minecraft mc = Minecraft.getInstance();
        if (event.isAttack() && holdingGun(mc)) {
            event.setCanceled(true);
        }
    }

    /** 銃所持中は左クリック長押しでのブロック破壊（再開始）を抑制。 */
    @SubscribeEvent
    public static void onLeftClickBlock(PlayerInteractEvent.LeftClickBlock event) {
        if (event.getEntity().getMainHandItem().getItem() instanceof GunItem) {
            event.setCanceled(true);
        }
    }
}
