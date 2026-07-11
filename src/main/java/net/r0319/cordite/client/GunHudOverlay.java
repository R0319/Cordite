package net.r0319.cordite.client;

import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.LayeredDraw;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterGuiLayersEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.FireMode;
import net.r0319.cordite.item.gun.GunItem;

/** 銃所持時に画面右下へ「残弾 / マガジン容量」と発射モードを表示する HUD。 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class GunHudOverlay {
    private GunHudOverlay() {}

    private static final ResourceLocation ID =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "gun_hud");

    private static final int MARGIN = 6;
    private static final int WHITE = 0xFFFFFFFF;
    private static final int ACCENT = 0xFFFFCC33;
    private static final int LOW_AMMO = 0xFFFF5555;

    @SubscribeEvent
    public static void register(RegisterGuiLayersEvent event) {
        event.registerAboveAll(ID, GunHudOverlay::render);
    }

    private static void render(GuiGraphics graphics, DeltaTracker deltaTracker) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.options.hideGui) {
            return;
        }

        ItemStack stack = mc.player.getMainHandItem();
        if (!(stack.getItem() instanceof GunItem gun)) {
            return;
        }

        Font font = mc.font;
        int screenW = graphics.guiWidth();
        int screenH = graphics.guiHeight();

        int total = gun.getTotalAmmo(stack);
        int capacity = gun.getAmmoCapacity();
        FireMode mode = gun.getFireMode(stack);

        // 薬室ぶんを含めた合計で表示（例 31 / 31）
        Component ammoText = Component.literal(total + " / " + capacity);
        Component modeText = mode.label();

        int ammoColor = total == 0 ? LOW_AMMO : WHITE;

        int ammoY = screenH - 30;
        int modeY = screenH - 18;

        drawRight(graphics, font, ammoText, screenW - MARGIN, ammoY, ammoColor);
        drawRight(graphics, font, modeText, screenW - MARGIN, modeY, ACCENT);
    }

    private static void drawRight(GuiGraphics graphics, Font font, Component text, int right, int y, int color) {
        int x = right - font.width(text);
        graphics.drawString(font, text, x, y, color, true);
    }
}
