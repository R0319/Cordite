package net.r0319.cordite.client.render;

import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.extensions.common.IClientItemExtensions;
import net.neoforged.neoforge.client.extensions.common.RegisterClientExtensionsEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.registry.ModItems;

/**
 * 銃アイテムに {@link GunItemRenderer}（BEWLR）を登録する。対応する
 * {@code models/item/*.json} 側の {@code parent} を {@code minecraft:builtin/entity}
 * にしておく必要がある（{@code BakedModel#isCustomRenderer()} が true を返すようにするため）。
 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class GunClientExtensions {
    private GunClientExtensions() {}

    private static final IClientItemExtensions EXTENSIONS = new IClientItemExtensions() {
        @Override
        public BlockEntityWithoutLevelRenderer getCustomRenderer() {
            return GunItemRenderer.instance();
        }
    };

    @SubscribeEvent
    public static void onRegisterClientExtensions(RegisterClientExtensionsEvent event) {
        event.registerItem(EXTENSIONS, ModItems.GLOCK.get(), ModItems.AK47.get(), ModItems.M4A1.get());
    }
}
