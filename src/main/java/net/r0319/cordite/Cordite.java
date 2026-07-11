package net.r0319.cordite;

import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.fml.event.lifecycle.FMLCommonSetupEvent;
import net.r0319.cordite.registry.ModCreativeTabs;
import net.r0319.cordite.registry.ModDataComponents;
import net.r0319.cordite.registry.ModItems;
import org.slf4j.Logger;

/**
 * Cordite — NeoForge 1.21.1 の銃PvP Mod。
 * 詳細は docs/specs/README.md および docs/design/00-architecture.md を参照。
 */
@Mod(Cordite.MODID)
public class Cordite {
    public static final String MODID = "cordite";
    private static final Logger LOGGER = LogUtils.getLogger();

    public Cordite(IEventBus modEventBus, ModContainer modContainer) {
        modEventBus.addListener(this::commonSetup);

        // レジストリをモッドイベントバスに登録
        ModDataComponents.COMPONENTS.register(modEventBus);
        ModItems.ITEMS.register(modEventBus);
        ModCreativeTabs.TABS.register(modEventBus);

        modContainer.registerConfig(ModConfig.Type.COMMON, Config.SPEC);
    }

    private void commonSetup(final FMLCommonSetupEvent event) {
        LOGGER.info("Cordite common setup");
    }
}
