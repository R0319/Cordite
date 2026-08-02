package net.r0319.cordite.gunpack;

import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.AddReloadListenerEvent;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.network.SyncGunDefinitionsPayload;
import org.slf4j.Logger;

/** gunpack のロードとサーバーからクライアントへの定義同期を登録する。 */
@EventBusSubscriber(modid = Cordite.MODID)
public final class GunpackEvents {
    private static final Logger LOGGER = LogUtils.getLogger();

    private GunpackEvents() {}

    @SubscribeEvent
    public static void onAddReloadListener(AddReloadListenerEvent event) {
        event.addListener(new GunDefinitionLoader(event.getRegistryAccess()));
    }

    @SubscribeEvent
    public static void onDatapackSync(OnDatapackSyncEvent event) {
        var payload = new SyncGunDefinitionsPayload(GunDefinitions.server());
        LOGGER.info("銃定義 {} 件をクライアントへ同期します", payload.definitions().size());
        event.getRelevantPlayers().forEach(player -> PacketDistributor.sendToPlayer(player, payload));
    }
}
