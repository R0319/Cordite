package net.r0319.cordite.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraft.world.item.ItemStack;
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

        /**
         * バニラの一人称アイテム変換（手の位置へのオフセット・装備時の上下動・スイング）を丸ごと止める。
         * 銃の配置はモデル側のロケーター（{@code idle_view} 等）を基準に
         * {@link GunItemRenderer} が自前で決めるため、バニラが先に手の位置へずらしてしまうと
         * ロケーターの座標がそのまま反映されない（＝作者がBlockbenchで合わせた見え方にならない）。
         *
         * <p>{@code true} を返すと以降のバニラ変換をスキップして描画へ進むので、
         * {@code PoseStack} はカメラ（視点）基準のままレンダラーへ渡る。</p>
         */
        @Override
        public boolean applyForgeHandTransform(PoseStack poseStack, LocalPlayer player, HumanoidArm arm,
                                                ItemStack itemInHand, float partialTick,
                                                float equipProcess, float swingProcess) {
            return true;
        }
    };

    @SubscribeEvent
    public static void onRegisterClientExtensions(RegisterClientExtensionsEvent event) {
        event.registerItem(EXTENSIONS, ModItems.GUN.get());
    }
}
