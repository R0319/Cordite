package net.r0319.cordite.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.GunAdsState;
import net.r0319.cordite.client.anim.GunAnimationSoundPlayer;
import net.r0319.cordite.client.anim.GunAnimationState;
import net.r0319.cordite.client.anim.ShellEjectionTracker;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.network.CycleFireModePayload;
import net.r0319.cordite.network.ReloadPayload;
import net.r0319.cordite.network.SetAdsPayload;
import net.r0319.cordite.network.SetTriggerPayload;
import org.lwjgl.glfw.GLFW;

/**
 * クライアントの銃入力。左クリック=射撃（トリガー状態をサーバーへ送信）、右クリック=ADS（クライアント表示のみ）、
 * V=モード切替、R=リロード。
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
    /** 直近でサーバーへ送ったADS状態（変化時のみ送信）。 */
    private static boolean lastAdsSent = false;
    /** 前tickのメインハンドスタック（持ち替え検出用・同一性比較のみ）。 */
    private static ItemStack lastHeldStack = ItemStack.EMPTY;
    /**
     * 前tickの「実際に持っている銃」（ADSのリセット判定用）。
     *
     * <p>{@link #lastHeldStack} の同一性比較は使えない: 発射やリロードで残弾のデータコンポーネントが
     * 変わるとサーバーからスロット同期が来て<b>ItemStackのインスタンスが差し替わる</b>ため、
     * 撃つたびに「持ち替えた」と誤判定されてADSが一瞬0に落ちてしまう（構え直しに見える）。
     * gunId＋ホットバースロットで判定すれば、同じ銃を持ち続けている限り誤検出しない。単一アイテム化により
     * Item型では銃を区別できないため、この値で判定する。</p>
     */
    private static ResourceLocation lastHeldGunId = null;
    private static int lastSelectedSlot = -1;
    /** リロードアニメーションの多重トリガー防止用（サーバーの実際のリロード完了tickとは別管理の予測値）。 */
    private static long localReloadingUntilTick = Long.MIN_VALUE;
    /** 直近でトリガーを押していたtick（{@link #AMMO_SYNC_GRACE_TICKS} 参照）。 */
    private static long lastTriggerDownTick = Long.MIN_VALUE;
    /**
     * トリガーを押してから、その発射による残弾減少がサーバーから届くまでの猶予。
     * この間の手元の残弾は「撃つ前の値」のままなので、満タン判定には使えない。
     */
    private static final int AMMO_SYNC_GRACE_TICKS = 10;

    private static boolean holdingGun(Minecraft mc) {
        return mc.player != null && mc.player.getMainHandItem().getItem() instanceof GunItem;
    }

    /**
     * クライアント側の予測でリロード中か（{@link GunHudOverlay} の弾切れ表示を、
     * 自分でリロードを始めた直後にまで出し続けないようにするためのもの）。
     * サーバー権威の {@code GunFireManager.State#reloadCompleteTick} とは別管理の予測値で、
     * サーバーがリクエストを拒否した場合は表示が少し遅れて復帰するだけ。
     */
    public static boolean isReloadingPredicted() {
        Minecraft mc = Minecraft.getInstance();
        return mc.player != null && mc.player.level().getGameTime() < localReloadingUntilTick;
    }

    /**
     * リロード要求を送る際、クライアント側であらかじめreload/reload_emptyアニメーションを
     * 開始しておく（サーバー権威の実際のリロード成立を待たず、体感を優先したローカル予測）。
     * サーバー側の{@code GunItem#startReload}と同じ条件（マガジン満タンでない・既にリロード中でない）を
     * クライアントでも確認し、実際には受理されないリロードで無駄にアニメーションを再生しないようにする。
     * サーバーがリクエストを拒否した場合でも、アニメーションが少し空回りするだけで実害はない。
     *
     * <p><b>満タン判定は撃った直後だけ信用しない</b>: 発射による残弾減少はサーバーの
     * データコンポーネント同期で数tick遅れて届く。満タンのマガジンから1発撃って即Rを押すと、
     * 手元の残弾はまだ満タンのままなので「リロード不要」と誤判定してアニメーションを出さず、
     * サーバー側だけが（実際は1発減っているので）リロードを受理して、
     * <b>モーション無しでリロードが完了する</b>。トリガーを押した直後は満タン判定を保留する。</p>
     */
    private static void triggerReloadAnimationIfEligible(Minecraft mc, ItemStack held) {
        if (!(held.getItem() instanceof GunItem gun) || mc.player == null) {
            return;
        }
        long now = mc.player.level().getGameTime();
        boolean ammoMaybeStale = now - lastTriggerDownTick <= AMMO_SYNC_GRACE_TICKS;
        boolean magazineFull = !ammoMaybeStale && gun.getMagazine(held, mc.level) >= gun.getAmmoCapacity(held, mc.level);
        boolean alreadyReloading = now < localReloadingUntilTick;
        if (magazineFull || alreadyReloading) {
            return;
        }
        // 撃ち切り直後（薬室の同期待ち）はreloadとreload_emptyを取り違えることがある。
        // 判別も残弾同期に依存するため、正確化にはリロード開始のサーバー→クライアント同期が要る
        // （docs/design/00-architecture.md「アニメーション状態のネットワーク同期方式（未定）」）。
        var definition = GunItem.definitionOf(held, mc.level);
        if (definition == null) {
            return;
        }
        GunAnimationState.Action action = gun.isChambered(held, mc.level)
                ? GunAnimationState.Action.RELOAD
                : GunAnimationState.Action.RELOAD_EMPTY;
        GunAnimationState.play(action, now);
        localReloadingUntilTick = now + definition.reloadTicks();
    }

    /**
     * 点検（inspect）モーションを再生する。
     *
     * <p><b>クライアント完結</b>: 銃を眺めるだけでゲーム状態を何も動かさないので、サーバーへは何も送らない
     * （周囲のプレイヤーからは見えない。三人称への反映はworldmodel実装時のアニメーション状態同期に乗る
     * → docs/design/00-architecture.md「アニメーション状態のネットワーク同期方式（未定）」）。</p>
     *
     * <p><b>リロード中は開始しない</b>。リロードはサーバー権威で進行中の動作なので、モーションだけを
     * 上書きすると{@link GunAnimationState#playFire}が発射を弾くのと同じ問題——リロードの残りの
     * モーションが消え、サーバー側だけが装填を終える——が起きる。逆に、点検中に発射・リロード・持ち替えが
     * 起きた場合は<b>そちらが点検を上書きしてよい</b>（点検はいつ捨ててもよいアクション）。</p>
     *
     * <p>弾切れなら{@code inspect_empty}を選ぶ（弾切れ待機のスライド後退姿勢から始まるクリップ）。
     * 残弾の判定は{@link net.r0319.cordite.client.render.GunItemRenderer}の弾切れ表示と同じで、
     * 同期が遅れるコンポーネントより先にパケットで届いた撃ち切りの事実を優先する。</p>
     */
    private static void startInspect(Minecraft mc, ItemStack held) {
        if (!(held.getItem() instanceof GunItem gun) || GunAnimationState.isReloading()) {
            return;
        }
        long now = mc.player.level().getGameTime();
        boolean empty = GunAnimationState.emptiedByRecentShot(now) || gun.getTotalAmmo(held, mc.level) <= 0;
        GunAnimationState.play(
                empty ? GunAnimationState.Action.INSPECT_EMPTY : GunAnimationState.Action.INSPECT, now);
    }

    /**
     * 手持ちアイテムが実際に切り替わったときの演出リセットと、取り出しモーションの再生開始。
     *
     * <p>前の銃の再生状態を持ち越さない: 飛行中の薬莢を消し、鳴りかけのサウンドタイムライン
     * （リロード中に持ち替えた場合など）を捨てる。そのうえで、持ち替え先が銃なら
     * {@code take_out}クリップを再生する（未作成の銃では{@link GunActionPlayback}がクリップ無しと
     * 判定して即idleへ戻るだけで、何も起きない）。</p>
     *
     * <p>取り出し中でも発射・リロードは可能（サーバー側に持ち替え時間の概念がまだ無いため）。
     * 撃てばそちらのアニメーションが上書きする。</p>
     */
    private static void onHeldItemSwitched(Minecraft mc, ItemStack held) {
        ShellEjectionTracker.reset();
        GunAnimationSoundPlayer.reset();
        if (held.getItem() instanceof GunItem) {
            GunAnimationState.play(GunAnimationState.Action.TAKE_OUT, mc.player.level().getGameTime());
        }
    }

    /**
     * 指定キーが物理的に押されているかを GLFW から直接読む。
     * {@link #suppressVanillaAttack}/{@link #suppressVanillaUse} で {@code isDown()} を毎tick false に
     * 上書きするため、発射・ADS判定にはそれを使えず、OS のボタン状態を直接参照する。
     */
    private static boolean isPhysicallyDown(Minecraft mc, KeyMapping mapping) {
        InputConstants.Key key = mapping.getKey();
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
            lastAdsSent = false;
            lastHeldStack = ItemStack.EMPTY;
            lastHeldGunId = null;
            lastSelectedSlot = -1;
            localReloadingUntilTick = Long.MIN_VALUE;
            lastTriggerDownTick = Long.MIN_VALUE;
            GunAdsState.reset();
            return;
        }

        // 持ち替え検出: サーバー側も持ち替えで過渡状態をリセットするため、
        // トリガーを押しっぱなしでも次の判定で必ず再送されるようにする（状態不一致の防止）
        ItemStack held = mc.player.getMainHandItem();
        boolean heldChanged = held != lastHeldStack;
        lastHeldStack = held;

        // 実際の持ち替え（別gunId／別スロット）のときだけADSを畳む。上記heldChangedは
        // 残弾同期でも立ってしまうため使わない。単一アイテム化後はItem型で銃を区別できないため、
        // gunIdとホットバースロットで判定する。
        int selectedSlot = mc.player.getInventory().selected;
        ResourceLocation heldGunId = GunItem.gunId(held);
        if (!java.util.Objects.equals(heldGunId, lastHeldGunId) || selectedSlot != lastSelectedSlot) {
            GunAdsState.reset(); // 持ち替え時は補間を挟まず腰だめへ戻す
            onHeldItemSwitched(mc, held);
        }
        lastHeldGunId = heldGunId;
        lastSelectedSlot = selectedSlot;

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
        // 点検（クライアント完結。押し直すと頭から再生し直す）
        while (ModKeyMappings.INSPECT.consumeClick()) {
            if (holdingGun && !guiOpen) {
                startInspect(mc, held);
            }
        }

        boolean inputActive = holdingGun && !guiOpen && mc.mouseHandler.isMouseGrabbed();

        // 射撃トリガー（左クリックの物理押下状態を送信）
        boolean triggerDown = inputActive && isPhysicallyDown(mc, mc.options.keyAttack);
        if (triggerDown) {
            // フルオートで押しっぱなしの間は毎tick更新し、残弾同期の猶予を伸ばし続ける
            lastTriggerDownTick = mc.player.level().getGameTime();
        }

        // ADS（右クリック押しっぱなし）。リロード中は覗けない: リロードは銃全体を大きく動かす
        // モーションで、その間サイトをカメラに固定すると銃が空中で固まって見えるため。
        boolean aiming = inputActive && !GunAnimationState.isReloading()
                && isPhysicallyDown(mc, mc.options.keyUse);
        // ADSは点検より優先する。リロードのようにADSを抑止するのではなく点検の方を捨てるのは、
        // 点検がゲーム状態を動かさない見せるだけの動作で、「覗きたいのに数秒待たされる」方が
        // 実害が大きいため（覗いた状態でNを押した場合も、この場で畳まれて何も起きない）。
        if (aiming && GunAnimationState.cancelInspect()) {
            GunAnimationSoundPlayer.stopInspect();
        }
        GunAdsState.tick(aiming);

        // 銃所持中はバニラの左クリック処理（採掘・近接攻撃・腕振り）と
        // 右クリック処理（ブロック設置・アイテム使用）を無効化
        if (holdingGun && !guiOpen) {
            suppressVanillaAttack(mc);
            suppressVanillaUse(mc);
        }

        if (triggerDown != lastTriggerSent || heldChanged) {
            PacketDistributor.sendToServer(new SetTriggerPayload(triggerDown));
            lastTriggerSent = triggerDown;
        }
        // ADS状態も状態変化時だけ送る。サーバーは腰だめ時の弾の拡散判定に使う（SetAdsPayload）
        if (aiming != lastAdsSent || heldChanged) {
            PacketDistributor.sendToServer(new SetAdsPayload(aiming));
            lastAdsSent = aiming;
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

    /**
     * バニラの右クリック処理（{@code startUseItem}＝ブロック設置・アイテム使用・ブロック操作）を
     * 無効化する。仕組みは {@link #suppressVanillaAttack} と同じ。
     *
     * <p>副作用として<b>銃を持っている間はチェストやドアを右クリックで開けなくなる</b>
     * （別のアイテムに持ち替えれば通常どおり操作できる）。右クリックをADSに割り当てる以上、
     * 覗くたびに設置・使用が走るよりは持ち替えを要求する方が事故が少ないため、こちらを採る。</p>
     */
    private static void suppressVanillaUse(Minecraft mc) {
        KeyMapping use = mc.options.keyUse;
        while (use.consumeClick()) {
            // 溜まった単発クリックを捨てる
        }
        use.setDown(false);
    }
}
