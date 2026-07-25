package net.r0319.cordite.client.anim;

import net.minecraft.client.Minecraft;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.item.gun.GunItem;

/**
 * 発射検知（暫定方式、docs/design/animation-system.md 参照）: メインハンドの銃の合計弾数
 * （マガジン+薬室、{@link GunItem#getTotalAmmo}）を毎tick監視し、前tickから減少していたら
 * 発射とみなして fire アニメーションを開始する。
 *
 * <p>専用の同期パケットを新設せず、既存の {@code magazine_ammo}/{@code chambered}
 * データコンポーネント（既にnetworkSynchronized、{@link net.r0319.cordite.registry.ModDataComponents}）
 * の変化を流用する暫定実装。フルオート連射時の取りこぼし・空撃ちの検知不可という
 * 既知の制約がある（次フェーズで専用ペイロード方式への切替を検討）。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class ClientGunAnimationTracker {
    private ClientGunAnimationTracker() {}

    /** 前tickのメインハンドスタック（持ち替え検出用・同一性比較のみ）。 */
    private static ItemStack lastHeldStack = ItemStack.EMPTY;
    private static int lastTotalAmmo = -1;

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) {
            reset();
            return;
        }

        ItemStack held = mc.player.getMainHandItem();
        if (!(held.getItem() instanceof GunItem gun)) {
            reset();
            return;
        }

        boolean changedGun = held.getItem() != lastHeldStack.getItem();
        int total = gun.getTotalAmmo(held);

        if (!changedGun && lastTotalAmmo >= 0 && total < lastTotalAmmo) {
            GunAnimationState.play(GunAnimationState.Action.FIRE, mc.level.getGameTime());
        }

        lastHeldStack = held;
        lastTotalAmmo = total;
    }

    private static void reset() {
        lastHeldStack = ItemStack.EMPTY;
        lastTotalAmmo = -1;
    }
}
