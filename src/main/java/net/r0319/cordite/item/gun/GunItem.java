package net.r0319.cordite.item.gun;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.r0319.cordite.combat.GunFireManager;
import net.r0319.cordite.combat.ProjectileManager;
import net.r0319.cordite.registry.ModDataComponents;

/**
 * 銃アイテム。発射はバニラの「アイテム使用」状態を使わず、独自の射撃システムで駆動する
 * （雪玉のようなアイテムの浮き沈みモーションを出さず、将来のADS/構え等の独自動作の土台にするため）。
 *
 * <p>入力: クライアントが左クリックの押下状態を {@link net.r0319.cordite.network.SetTriggerPayload}
 * でサーバーへ送り、{@link net.r0319.cordite.event.GunServerEvents} がサーバーtickで発射モードに応じて
 * {@link #tryFire} を呼ぶ。右クリックは将来のADS用に予約（現状は何もしない）。</p>
 *
 * <p>サーバー権威: ダメージ判定・残弾更新・連射レート検証はサーバー側。連射レートは
 * {@link GunFireManager} のゲームtick差分で制御し、バニラの {@code ItemCooldowns} は使わない
 * （＝ホットバーにクールタイムバーが出ない）。</p>
 */
public class GunItem extends Item {
    private final GunProperties props;

    public GunItem(GunProperties props, Properties properties) {
        super(properties.stacksTo(1));
        this.props = props;
    }

    public GunProperties getProps() {
        return props;
    }

    // --- 状態アクセサ ---

    /** マガジン内の残弾（薬室を含まない）。 */
    public int getMagazine(ItemStack stack) {
        return stack.getOrDefault(ModDataComponents.MAGAZINE_AMMO.get(), props.magSize());
    }

    /** 薬室に弾があるか。オープンボルトは常に false。 */
    public boolean isChambered(ItemStack stack) {
        if (props.boltType() == BoltType.OPEN) {
            return false;
        }
        return stack.getOrDefault(ModDataComponents.CHAMBERED.get(), true);
    }

    /** 合計装弾数（マガジン＋薬室）。 */
    public int getTotalAmmo(ItemStack stack) {
        return getMagazine(stack) + (isChambered(stack) ? 1 : 0);
    }

    /** 表示用の最大弾薬数（弾倉容量。薬室ぶんは含めない）。 */
    public int getAmmoCapacity() {
        return props.magSize();
    }

    public FireMode getFireMode(ItemStack stack) {
        Integer ordinal = stack.get(ModDataComponents.FIRE_MODE.get());
        FireMode[] all = FireMode.values();
        if (ordinal == null || ordinal < 0 || ordinal >= all.length) {
            return props.defaultMode();
        }
        FireMode mode = all[ordinal];
        return props.fireModes().contains(mode) ? mode : props.defaultMode();
    }

    // --- 発射（サーバーtickから呼ばれる。サーバー権威） ---

    /** レート／リロード／残弾を検証して1発撃つ。撃てたら true。 */
    public boolean tryFire(Player player, ItemStack stack, GunFireManager.State state) {
        if (!(player.level() instanceof ServerLevel level)) {
            return false;
        }
        long now = level.getGameTime();

        // リロード中は撃てない
        if (now < state.reloadCompleteTick) {
            return false;
        }
        // 連射レート（実銃準拠）
        if (now - state.lastShotTick < props.fireIntervalTicks()) {
            return false;
        }

        boolean closed = props.boltType() == BoltType.CLOSED;
        int mag = getMagazine(stack);
        boolean chamber = isChambered(stack);
        boolean hasRound = closed ? chamber : mag > 0;

        if (!hasRound) {
            // 空撃ち
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                    SoundEvents.DISPENSER_FAIL, SoundSource.PLAYERS, 0.6f, 1.2f);
            state.lastShotTick = now;
            return false;
        }

        // 1発消費
        if (closed) {
            // 薬室の弾を撃ち、マガジンに弾があればボルトサイクルで次弾を薬室へ送る
            if (mag > 0) {
                stack.set(ModDataComponents.MAGAZINE_AMMO.get(), mag - 1);
                stack.set(ModDataComponents.CHAMBERED.get(), true);
            } else {
                stack.set(ModDataComponents.CHAMBERED.get(), false); // 撃ち切り、薬室も空
            }
        } else {
            stack.set(ModDataComponents.MAGAZINE_AMMO.get(), mag - 1);
        }
        state.lastShotTick = now;

        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.CROSSBOW_SHOOT, SoundSource.PLAYERS, 1.0f, 1.0f);
        ProjectileManager.fire(level, player, props);
        player.swing(InteractionHand.MAIN_HAND);
        return true;
    }

    // --- 外部操作（パケットから呼ばれる。サーバー側で実行） ---

    /** 発射モードを次へ循環する。 */
    public void cycleFireMode(Player player, ItemStack stack) {
        FireMode next = props.nextMode(getFireMode(stack));
        stack.set(ModDataComponents.FIRE_MODE.get(), next.ordinal());
        player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.LEVER_CLICK, SoundSource.PLAYERS, 0.7f, 1.4f);
    }

    /** リロードを開始する（完了は {@link net.r0319.cordite.event.GunServerEvents} が処理）。 */
    public void startReload(Player player, ItemStack stack) {
        if (getMagazine(stack) >= props.magSize()) {
            return; // マガジンが満タンなら不要
        }
        GunFireManager.State state = GunFireManager.get(player);
        long now = player.level().getGameTime();
        if (now < state.reloadCompleteTick) {
            return; // すでにリロード中
        }
        state.reloadCompleteTick = now + props.reloadTicks();
        player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.CROSSBOW_LOADING_START, SoundSource.PLAYERS, 1.0f, 1.0f);
    }

    /**
     * リロード完了時の装填。クローズドボルトは薬室に弾を残していれば「マガジン容量＋薬室」、
     * 撃ち切っていればボルトリリースで薬室に1発送るため合計はマガジン容量ちょうどになる。
     */
    public void completeReload(ItemStack stack) {
        int magSize = props.magSize();
        if (props.boltType() == BoltType.OPEN) {
            stack.set(ModDataComponents.MAGAZINE_AMMO.get(), magSize);
            return;
        }
        boolean chamber = isChambered(stack);
        if (chamber) {
            // タクティカルリロード: 薬室の1発は温存 → 合計 magSize + 1
            stack.set(ModDataComponents.MAGAZINE_AMMO.get(), magSize);
        } else {
            // 撃ち切りリロード: 新マガジンから1発を薬室へ → 合計 magSize
            stack.set(ModDataComponents.MAGAZINE_AMMO.get(), magSize - 1);
            stack.set(ModDataComponents.CHAMBERED.get(), true);
        }
    }
}
