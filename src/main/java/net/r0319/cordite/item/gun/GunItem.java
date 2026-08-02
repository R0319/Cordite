package net.r0319.cordite.item.gun;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.PacketDistributor;
import net.r0319.cordite.combat.GunFireManager;
import net.r0319.cordite.combat.ProjectileManager;
import net.r0319.cordite.gunpack.GunDefinition;
import net.r0319.cordite.gunpack.GunDefinitions;
import net.r0319.cordite.network.GunFiredPayload;
import net.r0319.cordite.registry.ModDataComponents;

import java.util.Objects;

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
    public GunItem(Properties properties) {
        super(properties.stacksTo(1));
    }

    /** スタックに設定された gunpack 定義ID。素の銃など未設定時は null。 */
    public static ResourceLocation gunId(ItemStack stack) {
        return stack == null ? null : stack.get(ModDataComponents.GUN_ID.get());
    }

    /** 論理サイドに対応する gunpack 定義。ワールド未確定時は安全側で null を返す。 */
    public static GunDefinition definitionOf(ItemStack stack, Level level) {
        ResourceLocation id = gunId(stack);
        if (id == null || level == null) {
            return null;
        }
        return level.isClientSide ? GunDefinitions.client(id) : GunDefinitions.server(id);
    }

    /** クリエイティブタブなどで使う、指定された gunpack 定義を参照する銃スタックを作る。 */
    public static ItemStack createStack(ResourceLocation gunId) {
        ItemStack stack = new ItemStack(net.r0319.cordite.registry.ModItems.GUN.get());
        stack.set(ModDataComponents.GUN_ID.get(), gunId);
        return stack;
    }

    @Override
    public Component getName(ItemStack stack) {
        ResourceLocation id = gunId(stack);
        GunDefinition definition = id == null ? null : GunDefinitions.client(id);
        if (definition == null) {
            return Component.translatable("item.cordite.gun");
        }
        return definition.name().orElseGet(() -> Component.translatable("item." + id.getNamespace() + "." + id.getPath()));
    }

    /**
     * 銃ではブロックを破壊・攻撃できない（サーバー権威）。クライアントの左クリック抑制
     * （{@link net.r0319.cordite.client.ClientInputHandler}）と併せて、破壊予測・採掘進行を
     * サーバー/クライアント双方で禁止する。実際の破壊除去は {@code BlockEvent.BreakEvent} でも止める
     * （{@link net.r0319.cordite.event.GunServerEvents}）。
     */
    @Override
    public boolean canAttackBlock(BlockState state, Level level, BlockPos pos, Player player) {
        return false;
    }

    /**
     * 「構え直し」アニメーション（一人称でアイテムが一度下がって戻る、雪玉/クロスボウ発射時と同じ動き）は
     * 同じ銃を持ち続けている限り再生しない。バニラの既定実装は {@code !oldStack.equals(newStack)} で、
     * {@code ItemStack.equals} はデータコンポーネントの中身まで比較するため、発射のたびに変化する
     * {@link net.r0319.cordite.registry.ModDataComponents#MAGAZINE_AMMO}/{@code CHAMBERED} が
     * 「別アイテムに変わった」と誤判定され、毎発リエクイップ演出が入ってしまう
     * （耐久値変化で武器/道具が毎回リエクイップしないようにするのと同じ対策）。
     */
    @Override
    public boolean shouldCauseReequipAnimation(ItemStack oldStack, ItemStack newStack, boolean slotChanged) {
        if (slotChanged) {
            return true; // ホットバー切り替え等は通常通り演出する
        }
        return !Objects.equals(gunId(oldStack), gunId(newStack));
    }

    // --- 状態アクセサ ---

    /** マガジン内の残弾（薬室を含まない）。 */
    public int getMagazine(ItemStack stack, Level level) {
        GunDefinition definition = definitionOf(stack, level);
        return definition == null ? 0 : stack.getOrDefault(ModDataComponents.MAGAZINE_AMMO.get(), definition.magSize());
    }

    /** 薬室に弾があるか。オープンボルトは常に false。 */
    public boolean isChambered(ItemStack stack, Level level) {
        GunDefinition definition = definitionOf(stack, level);
        if (definition == null || definition.boltType() == BoltType.OPEN) {
            return false;
        }
        return stack.getOrDefault(ModDataComponents.CHAMBERED.get(), true);
    }

    /** 合計装弾数（マガジン＋薬室）。 */
    public int getTotalAmmo(ItemStack stack, Level level) {
        return getMagazine(stack, level) + (isChambered(stack, level) ? 1 : 0);
    }

    /** 表示用の最大弾薬数（弾倉容量。薬室ぶんは含めない）。 */
    public int getAmmoCapacity(ItemStack stack, Level level) {
        GunDefinition definition = definitionOf(stack, level);
        return definition == null ? 0 : definition.magSize();
    }

    public FireMode getFireMode(ItemStack stack, Level level) {
        GunDefinition definition = definitionOf(stack, level);
        if (definition == null) {
            return FireMode.SINGLE;
        }
        FireMode mode = stack.get(ModDataComponents.FIRE_MODE.get());
        if (mode == null || !definition.fireModes().contains(mode)) {
            return definition.defaultMode(); // 未設定、またはこの銃が対応しないモード
        }
        return mode;
    }

    // --- 発射（サーバーtickから呼ばれる。サーバー権威） ---

    /** レート／リロード／残弾を検証して1発撃つ。撃てたら true。 */
    public boolean tryFire(Player player, ItemStack stack, GunFireManager.State state) {
        if (!(player.level() instanceof ServerLevel level)) {
            return false;
        }
        GunDefinition props = definitionOf(stack, level);
        if (props == null) {
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
        int mag = getMagazine(stack, level);
        boolean chamber = isChambered(stack, level);
        boolean hasRound = closed ? chamber : mag > 0;

        if (!hasRound) {
            // 空撃ち。ホールドオープンする銃（Glock/M4A1等）は撃ち切った時点でスライド／ボルトが
            // 後退位置で保持され撃発機構が働かないため、実銃同様まったく音がしない。
            // 音が出る銃でも撃発は1トリガーにつき1回なので、押しっぱなしでは連打しない。
            if (props.holdOpenOnEmpty()) {
                state.dryFiredThisPress = true; // 無音でも「この押下は処理済み」として扱う
            } else if (!state.dryFiredThisPress) {
                level.playSound(null, player.getX(), player.getY(), player.getZ(),
                        SoundEvents.DISPENSER_FAIL, SoundSource.PLAYERS, 0.6f, 1.2f);
                state.dryFiredThisPress = true;
            }
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

        // 発射音は周囲にも聞こえる必要があるためサーバーから配信する（第1引数nullで本人も含む全員へ）。
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                props.fireSound(), SoundSource.PLAYERS, 1.0f, 1.0f);
        ProjectileManager.fire(level, player, props, state.aiming);
        // バニラの腕振り（player.swing）は使わない: 毎発「殴るモーション」で銃が上下して見えるため。
        // 反動などの発射モーションは作者制作アニメで再生する。その開始トリガーを本人へ送る
        // （発射音と同じtickなので、反動アニメが銃声と揃う。GunFiredPayload のコメント参照）。
        // 撃ち切り判定はサーバー側でしか正しく取れない（クライアントの残弾同期はこのパケットより遅れる）
        if (player instanceof ServerPlayer serverPlayer) {
            boolean emptyAfterShot = props.holdOpenOnEmpty() && getTotalAmmo(stack, level) <= 0;
            PacketDistributor.sendToPlayer(serverPlayer, new GunFiredPayload(emptyAfterShot));
        }
        return true;
    }

    // --- 外部操作（パケットから呼ばれる。サーバー側で実行） ---

    /** 発射モードを次へ循環する。 */
    public void cycleFireMode(Player player, ItemStack stack) {
        GunDefinition props = definitionOf(stack, player.level());
        if (props == null) {
            return;
        }
        FireMode next = props.nextMode(getFireMode(stack, player.level()));
        stack.set(ModDataComponents.FIRE_MODE.get(), next);
        player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.LEVER_CLICK, SoundSource.PLAYERS, 0.7f, 1.4f);
    }

    /** リロードを開始する（完了は {@link net.r0319.cordite.event.GunServerEvents} が処理）。 */
    public void startReload(Player player, ItemStack stack) {
        GunDefinition props = definitionOf(stack, player.level());
        if (props == null || getMagazine(stack, player.level()) >= props.magSize()) {
            return; // マガジンが満タンなら不要
        }
        GunFireManager.State state = GunFireManager.get(player);
        long now = player.level().getGameTime();
        if (now < state.reloadCompleteTick) {
            return; // すでにリロード中
        }
        state.reloadCompleteTick = now + props.reloadTicks();
        state.reloadingStack = stack; // この銃に紐づける（別の銃へ持ち替えたら中断される）
        // リロード中のメカ音（マガジン脱着）はここでは鳴らさない。開始/完了の2点固定ではモーションと
        // タイミングが合わない（リロード時間はアニメーション長と別の🟡仮バランス値で、再生速度が伸縮するため）。
        // アニメーションの sound_effects 側で作者がタイミングを置く（GunAnimationSoundPlayer）。
    }

    /**
     * リロード完了時の装填。クローズドボルトは薬室に弾を残していれば「マガジン容量＋薬室」、
     * 撃ち切っていればボルトリリースで薬室に1発送るため合計はマガジン容量ちょうどになる。
     */
    public void completeReload(ItemStack stack, Level level) {
        GunDefinition props = definitionOf(stack, level);
        if (props == null) {
            return;
        }
        int magSize = props.magSize();
        if (props.boltType() == BoltType.OPEN) {
            stack.set(ModDataComponents.MAGAZINE_AMMO.get(), magSize);
            return;
        }
        boolean chamber = isChambered(stack, level);
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
