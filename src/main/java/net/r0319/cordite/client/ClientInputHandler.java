package net.r0319.cordite.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.GunAnimationState;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.network.CycleFireModePayload;
import net.r0319.cordite.network.ReloadPayload;
import net.r0319.cordite.network.SetTriggerPayload;
import org.lwjgl.glfw.GLFW;

/**
 * クライアントの銃入力。左クリック=射撃（トリガー状態をサーバーへ送信）、V=モード切替、R=リロード。
 *
 * <p><b>左クリックの競合対策</b>: 発射に左クリック（{@code keyAttack}）を使うが、バニラも同じキーで
 * 採掘・近接攻撃・腕振りを行う。バニラは {@code Minecraft.tick()} 内で毎tick {@code keyAttack.isDown()}
 * をポーリングして {@code continueAttack()}（採掘＋腕振り）を呼ぶため、イベントのキャンセルだけでは止まらず、
 * 「撃つと銃が上下する（採掘の腕振り）」「ブロックを壊そうとする」という症状になる。<br>
 * そこで銃所持中は {@link ClientTickEvent.Pre}（バニラの入力処理より前）で {@code keyAttack} の押下状態を
 * 毎tick落とし、溜まったクリックも捨てて、バニラの左クリック処理を完全に無効化する。発射判定には無効化した
 * {@code isDown()} が使えないので、GLFW から物理ボタン状態を直接読む。実際の発射処理はサーバー側。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class ClientInputHandler {
    private ClientInputHandler() {}

    /** 直近でサーバーへ送ったトリガー状態（変化時のみ送信）。 */
    private static boolean lastTriggerSent = false;
    /** 前tickのメインハンドスタック（持ち替え検出用・同一性比較のみ）。 */
    private static ItemStack lastHeldStack = ItemStack.EMPTY;
    /** リロードアニメーションの多重トリガー防止用（サーバーの実際のリロード完了tickとは別管理の予測値）。 */
    private static long localReloadingUntilTick = Long.MIN_VALUE;

    private static boolean holdingGun(Minecraft mc) {
        return mc.player != null && mc.player.getMainHandItem().getItem() instanceof GunItem;
    }

    /**
     * リロード要求を送る際、クライアント側であらかじめreload/reload_emptyアニメーションを
     * 開始しておく（サーバー権威の実際のリロード成立を待たず、体感を優先したローカル予測）。
     * サーバー側の{@code GunItem#startReload}と同じ条件（マガジン満タンでない・既にリロード中でない）を
     * クライアントでも確認し、実際には受理されないリロードで無駄にアニメーションを再生しないようにする。
     * サーバーがリクエストを拒否した場合でも、アニメーションが少し空回りするだけで実害はない。
     */
    private static void triggerReloadAnimationIfEligible(Minecraft mc, ItemStack held) {
        if (!(held.getItem() instanceof GunItem gun) || mc.player == null) {
            return;
        }
        long now = mc.player.level().getGameTime();
        boolean magazineFull = gun.getMagazine(held) >= gun.getAmmoCapacity();
        boolean alreadyReloading = now < localReloadingUntilTick;
        if (magazineFull || alreadyReloading) {
            return;
        }
        GunAnimationState.Action action = gun.isChambered(held)
                ? GunAnimationState.Action.RELOAD
                : GunAnimationState.Action.RELOAD_EMPTY;
        GunAnimationState.play(action, now);
        localReloadingUntilTick = now + gun.getProps().reloadTicks();
    }

    /**
     * 攻撃キー（既定は左クリック）が物理的に押されているかを GLFW から直接読む。
     * {@link #suppressVanillaAttack} で {@code keyAttack.isDown()} を毎tick false に上書きするため、
     * 発射判定にはそれを使えず、OS のボタン状態を直接参照する。
     */
    private static boolean isAttackPhysicallyDown(Minecraft mc) {
        InputConstants.Key key = mc.options.keyAttack.getKey();
        long window = mc.getWindow().getWindow();
        if (key.getType() == InputConstants.Type.MOUSE) {
            return GLFW.glfwGetMouseButton(window, key.getValue()) == GLFW.GLFW_PRESS;
        }
        return InputConstants.isKeyDown(window, key.getValue());
    }

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Pre event) { // バニラの入力処理より前に走らせる
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.getConnection() == null) {
            lastTriggerSent = false; // 未接続: 送信状態をリセット
            lastHeldStack = ItemStack.EMPTY;
            localReloadingUntilTick = Long.MIN_VALUE;
            return;
        }

        // 持ち替え検出: サーバー側も持ち替えで過渡状態をリセットするため、
        // トリガーを押しっぱなしでも次の判定で必ず再送されるようにする（状態不一致の防止）
        ItemStack held = mc.player.getMainHandItem();
        boolean heldChanged = held != lastHeldStack;
        lastHeldStack = held;

        boolean holdingGun = holdingGun(mc);
        boolean guiOpen = mc.screen != null;

        // モード切替・リロード（銃所持かつGUI非表示時のみ）
        while (ModKeyMappings.CYCLE_FIRE_MODE.consumeClick()) {
            if (holdingGun && !guiOpen) {
                PacketDistributor.sendToServer(CycleFireModePayload.INSTANCE);
            }
        }
        while (ModKeyMappings.RELOAD.consumeClick()) {
            if (holdingGun && !guiOpen) {
                triggerReloadAnimationIfEligible(mc, held);
                PacketDistributor.sendToServer(ReloadPayload.INSTANCE);
            }
        }

        // 射撃トリガー（左クリックの物理押下状態を送信）
        boolean triggerDown = holdingGun && !guiOpen
                && mc.mouseHandler.isMouseGrabbed()
                && isAttackPhysicallyDown(mc);

        // 銃所持中はバニラの左クリック処理（採掘・近接攻撃・腕振り）を無効化
        if (holdingGun && !guiOpen) {
            suppressVanillaAttack(mc);
        }

        if (triggerDown != lastTriggerSent || heldChanged) {
            PacketDistributor.sendToServer(new SetTriggerPayload(triggerDown));
            lastTriggerSent = triggerDown;
        }
    }

    /**
     * バニラの左クリック処理を無効化する。キュー済みのクリックを消費して {@code startAttack}（単発の
     * 攻撃・採掘開始）を呼ばせず、押下状態を false に落として {@code continueAttack}（毎tickの採掘＋腕振り）
     * も止める。GLFW のボタンコールバックは押下/離しのエッジでしか発火しないため、一度 false にすれば
     * 押しっぱなしでも再度 true には戻らない（発射は {@link #isAttackPhysicallyDown} で別途検出する）。
     */
    private static void suppressVanillaAttack(Minecraft mc) {
        KeyMapping attack = mc.options.keyAttack;
        while (attack.consumeClick()) {
            // 溜まった単発クリックを捨てる
        }
        attack.setDown(false);
    }
}
