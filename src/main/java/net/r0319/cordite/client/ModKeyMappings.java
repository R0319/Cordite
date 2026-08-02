package net.r0319.cordite.client;

import net.minecraft.client.KeyMapping;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterKeyMappingsEvent;
import net.r0319.cordite.Cordite;
import org.lwjgl.glfw.GLFW;

/** 銃操作のキーバインド。 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class ModKeyMappings {
    private ModKeyMappings() {}

    public static final String CATEGORY = "key.category.cordite";

    /** 発射モード切替（既定: V）。 */
    public static final KeyMapping CYCLE_FIRE_MODE =
            new KeyMapping("key.cordite.cycle_fire_mode", GLFW.GLFW_KEY_V, CATEGORY);

    /** リロード（既定: R）。 */
    public static final KeyMapping RELOAD =
            new KeyMapping("key.cordite.reload", GLFW.GLFW_KEY_R, CATEGORY);

    /** 点検（既定: N）。銃を眺めるだけでゲームプレイには影響しない。 */
    public static final KeyMapping INSPECT =
            new KeyMapping("key.cordite.inspect", GLFW.GLFW_KEY_N, CATEGORY);

    @SubscribeEvent
    public static void register(RegisterKeyMappingsEvent event) {
        event.register(CYCLE_FIRE_MODE);
        event.register(RELOAD);
        event.register(INSPECT);
    }
}
