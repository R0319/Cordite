package net.r0319.cordite.registry;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.CreativeModeTab;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.gunpack.GunDefinitions;
import net.r0319.cordite.item.gun.GunItem;

import java.util.Comparator;

public final class ModCreativeTabs {
    private ModCreativeTabs() {}

    public static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, Cordite.MODID);

    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> CORDITE = TABS.register(
            "cordite", () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.cordite"))
                    .icon(() -> ModItems.GUN.get().getDefaultInstance())
                    .displayItems((parameters, output) -> GunDefinitions.client().keySet().stream()
                            .sorted(Comparator.comparing(ResourceLocation::toString))
                            .forEach(id -> output.accept(GunItem.createStack(id))))
                    .build());
}
