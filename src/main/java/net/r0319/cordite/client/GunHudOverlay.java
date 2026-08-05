package net.r0319.cordite.client;

import com.mojang.blaze3d.systems.RenderSystem;
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
import net.neoforged.neoforge.client.event.RenderGuiLayerEvent;
import net.neoforged.neoforge.client.gui.VanillaGuiLayers;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.GunAdsState;
import net.r0319.cordite.client.anim.ReticleKickState;
import net.r0319.cordite.item.gun.FireMode;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.gunpack.GunDefinition;

/**
 * 銃所持時に画面右下へ「残弾 / マガジン容量」と発射モードを表示する HUD。
 *
 * <p>ADS中はバニラのクロスヘアを消す（{@link AdsCrosshair}）。
 *
 * <p>加えて、弾を撃ち切った状態ではクロスヘア下に弾切れ／リロード促しを表示する。
 * ホールドオープンする銃（{@link GunDefinition#holdOpenOnEmpty()}）は
 * 実銃同様に空撃ち音が鳴らないため、右下の残弾表示だけでは弾切れに気付きにくいのを補う。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class GunHudOverlay {
    private GunHudOverlay() {}

    private static final ResourceLocation ID =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "gun_hud");

    private static final int MARGIN = 6;
    private static final int WHITE = 0xFFFFFFFF;
    private static final int ACCENT = 0xFFFFCC33;
    private static final int LOW_AMMO = 0xFFFF5555;

    /** 弾切れ表示のクロスヘア中心からの下方向オフセット（px）。🟡仮・実機で調整する値。 */
    private static final int EMPTY_PROMPT_OFFSET_Y = 14;

    // --- レティクル（作者制作の画像） ---

    /** レティクル画像（作者制作）。作業フォルダの {@code texture/reticle/} から自動同期される。 */
    private static final ResourceLocation RETICLE_TEXTURE =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "textures/reticle/reticle.png");
    /** 画像の元サイズ（px四方）。画像を作り直して解像度が変わったらここも直す。 */
    private static final int RETICLE_TEXTURE_SIZE = 32;
    /**
     * 画面に描く最小の一辺（px）。拡散が小さい銃でも潰れないようにするための下限で、
     * <b>この値を大きくすれば実質「常に一定サイズ」になる</b>（拡散連動をやめたい場合）。
     * 🟡仮・実機で調整する値（バニラのクロスヘアは15px）。
     */
    private static final int RETICLE_MIN_SIZE = 16;

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

        GunDefinition definition = GunItem.definitionOf(stack, mc.level);
        if (definition == null) {
            return;
        }

        Font font = mc.font;
        int screenW = graphics.guiWidth();
        int screenH = graphics.guiHeight();

        drawReticle(graphics, deltaTracker, definition, screenW, screenH);

        int total = gun.getTotalAmmo(stack, mc.level);
        int capacity = gun.getAmmoCapacity(stack, mc.level);
        FireMode mode = gun.getFireMode(stack, mc.level);

        // 薬室ぶんを含めた合計で表示（例 31 / 31）
        Component ammoText = Component.literal(total + " / " + capacity);
        Component modeText = mode.label();

        int ammoColor = total == 0 ? LOW_AMMO : WHITE;

        int ammoY = screenH - 30;
        int modeY = screenH - 18;

        drawRight(graphics, font, ammoText, screenW - MARGIN, ammoY, ammoColor);
        drawRight(graphics, font, modeText, screenW - MARGIN, modeY, ACCENT);

        // 弾切れ: リロード操作中は促し続けない（自分で開始したリロードの最中は消す）
        if (total <= 0 && !ClientInputHandler.isReloadingPredicted()) {
            Component prompt = Component.translatable(
                    "hud.cordite.empty", ModKeyMappings.RELOAD.getTranslatedKeyMessage());
            drawCentered(graphics, font, prompt, screenW / 2, screenH / 2 + EMPTY_PROMPT_OFFSET_Y, LOW_AMMO);
        }
    }

    private static void drawCentered(GuiGraphics graphics, Font font, Component text, int centerX, int y, int color) {
        graphics.drawString(font, text, centerX - font.width(text) / 2, y, color, true);
    }

    /**
     * 銃専用のレティクル（作者制作の画像）を画面中央に描く。バニラのクロスヘアは銃所持中は
     * {@link AdsCrosshair} が消しているので、これが唯一の照準表示になる。
     *
     * <p>三人称では自機の照準表示を出さないため、描画しない。</p>
     *
     * <p><b>大きさは実際の拡散量そのもの</b>。画像の一辺を、腰だめの拡散角
     * （{@link GunDefinition#hipSpreadDeg()}）が画面上で占める大きさ（直径＝半角の2倍）に換算するので、
     * 「画像の内側に弾が来る」という読み方が成立する。連射・移動によるブルームを実装したら、
     * ここが自動的に開閉するようになる。拡散が小さい銃で潰れないよう {@link #RETICLE_MIN_SIZE} を下限とする
     * （この下限を大きくすれば実質「常に一定サイズ」にできる）。</p>
     *
     * <p>これに<b>発射した瞬間だけ乗る一時的なキック</b>（{@link ReticleKickState}）を足す。
     * こちらは実際の拡散ではなく手応えのための演出で、撃った瞬間に開いてすぐ戻る。</p>
     *
     * <p>一辺を偶数へ丸めてから中心を出すので、<b>上下左右が必ず対称</b>になる
     * （奇数だと中心が半pxずれて片側にはみ出す）。</p>
     *
     * <p>ADS中は描かない。サイトを覗いている間はモデル側のアイアンサイトが照準になるため、
     * 画面中央のレティクルは重なって見づらくなるだけ。</p>
     */
    private static void drawReticle(GuiGraphics graphics, DeltaTracker deltaTracker, GunDefinition definition,
                                     int screenW, int screenH) {
        if (!Minecraft.getInstance().options.getCameraType().isFirstPerson()) {
            return;
        }
        float partialTick = deltaTracker.getGameTimeDeltaPartialTick(false);
        if (GunAdsState.progress(partialTick) > 0f) {
            return;
        }
        float radius = spreadToPixels(definition.hipSpreadDeg(), screenH)
                + reticleKickPixels(partialTick);
        int size = Math.max(RETICLE_MIN_SIZE, Math.round(radius * 2f));
        size += size & 1; // 偶数化: 画面中心から半分ずつ振り分けるので、奇数だと対称に置けない
        int x = screenW / 2 - size / 2;
        int y = screenH / 2 - size / 2;

        // アルファ付きPNGなのでブレンドを明示的に有効化する（blitはシェーダーとテクスチャしか設定しない）
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        graphics.blit(RETICLE_TEXTURE, x, y, size, size,
                0f, 0f, RETICLE_TEXTURE_SIZE, RETICLE_TEXTURE_SIZE, RETICLE_TEXTURE_SIZE, RETICLE_TEXTURE_SIZE);
        RenderSystem.disableBlend();
    }

    /**
     * 発射直後にレティクルを開かせる一時的な追加量[px]（{@link ReticleKickState}）。
     * ワールドに居ないときは0（ゲーム時刻が取れないため）。
     */
    private static float reticleKickPixels(float partialTick) {
        Minecraft mc = Minecraft.getInstance();
        return mc.level == null ? 0f : ReticleKickState.extraPixels(mc.level.getGameTime(), partialTick);
    }

    /**
     * 拡散角[度]が画面上で何pxに見えるかを求める。
     *
     * <p>画面の高さの半分が視野角の半分に対応するので、焦点距離[px] = (画面高/2) / tan(FOV/2)。
     * そこに tan(拡散角) を掛ければ中心からのズレがpxで出る。GUIスケールが変わっても
     * 「画面に占める割合」は変わらないため、スケール依存の調整は不要。</p>
     */
    private static int spreadToPixels(float spreadDeg, int screenH) {
        if (spreadDeg <= 0f) {
            return 0;
        }
        double fovDeg = Minecraft.getInstance().options.fov().get();
        double focalPixels = (screenH / 2.0) / Math.tan(Math.toRadians(fovDeg) / 2.0);
        return (int) Math.round(focalPixels * Math.tan(Math.toRadians(spreadDeg)));
    }

    /**
     * 銃を持っている間はバニラのクロスヘアを描かせない。腰だめでは代わりに専用レティクル
     * （{@link #drawReticle}）を出し、ADS中はモデル側のアイアンサイトが照準になるので何も出さない。
     *
     * <p>ゲームバスのイベントなので {@link GunHudOverlay} 本体（modバス）とは別に購読する。</p>
     */
    @EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
    public static final class AdsCrosshair {
        private AdsCrosshair() {}

        @SubscribeEvent
        public static void onRenderGuiLayer(RenderGuiLayerEvent.Pre event) {
            if (!VanillaGuiLayers.CROSSHAIR.equals(event.getName())) {
                return;
            }
            Minecraft mc = Minecraft.getInstance();
            if (mc.player == null || !mc.options.getCameraType().isFirstPerson()
                    || !(mc.player.getMainHandItem().getItem() instanceof GunItem)) {
                return;
            }
            event.setCanceled(true);
        }
    }

    private static void drawRight(GuiGraphics graphics, Font font, Component text, int right, int y, int color) {
        int x = right - font.width(text);
        graphics.drawString(font, text, x, y, color, true);
    }
}
