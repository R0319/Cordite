package net.r0319.cordite.registry;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.r0319.cordite.Cordite;

public final class ModCreativeTabs {
    private ModCreativeTabs() {}

    public static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, Cordite.MODID);

    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> CORDITE = TABS.register(
            "cordite", () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.cordite"))
                    .icon(() -> ModItems.GLOCK.get().getDefaultInstance())
                    .displayItems((parameters, output) -> {
                        output.accept(ModItems.GLOCK.get());
                        output.accept(ModItems.AK47.get());
                        output.accept(ModItems.M4A1.get());
                    })
                    .build());
}
