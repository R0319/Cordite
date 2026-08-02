package net.r0319.cordite.gunpack;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.r0319.cordite.Cordite;

/** 接続をまたいで古いサーバーの定義が残らないよう、切断時にクライアント側を空にする。 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class GunpackClientEvents {
    private GunpackClientEvents() {}

    @SubscribeEvent
    public static void onLoggingOut(ClientPlayerNetworkEvent.LoggingOut event) {
        GunDefinitions.clearClient();
    }
}
