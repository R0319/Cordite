package net.r0319.cordite.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.logging.LogUtils;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.AnimationSampler;
import net.r0319.cordite.client.anim.BakedAnimation;
import net.r0319.cordite.client.anim.GunActionPlayback;
import net.r0319.cordite.client.anim.BoneTrack;
import net.r0319.cordite.client.anim.GunAdsState;
import net.r0319.cordite.client.anim.GunAnimationState;
import net.r0319.cordite.client.anim.MuzzleFlashState;
import net.r0319.cordite.client.anim.ShellEjectionTracker;
import net.r0319.cordite.client.model.BakedCube;
import net.r0319.cordite.client.model.BakedGunModel;
import net.r0319.cordite.client.model.GunBone;
import net.r0319.cordite.client.model.GunModelCache;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.gunpack.GunDefinition;
import org.slf4j.Logger;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashSet;
import java.util.Set;

/**
 * 銃アイテムのカスタムレンダラー（BEWLR）。{@link GunModelCache} からベイク済みモデルを取得し、
 * ボーン階層を再帰的に歩いて {@link PoseStack} へ変換を積みながら頂点を描画する。
 *
 * <p>プロトタイプ範囲: 一人称（{@link ItemDisplayContext#FIRST_PERSON_RIGHT_HAND}/
 * {@link ItemDisplayContext#FIRST_PERSON_LEFT_HAND}）のみ配置を作り込む。それ以外の
 * コンテキスト（GUI/地面ドロップ/三人称/アイテムフレーム）は簡易な仮配置で、
 * クラッシュせず何かしら表示されればよい（ロケーター実装後の次フェーズで精密化する）。</p>
 *
 * <p><b>配置定数について</b>: モデルの生の座標がゲーム内でどの程度の大きさ・位置に見えるかは
 * 実機（{@code runClient}）で目視確認しないと分からないため、下記の {@code FIRST_PERSON_*} /
 * {@code MODEL_SCALE} は仮の値。実機で見た目を確認しながら調整すること。</p>
 */
public final class GunItemRenderer extends BlockEntityWithoutLevelRenderer {
    private static final Logger LOGGER = LogUtils.getLogger();
    /** 定義はあるがモデルが無いgunId。リロード前に同じ警告を繰り返さない。 */
    private static final Set<ResourceLocation> WARNED_MISSING_MODELS = new HashSet<>();
    private static GunItemRenderer instance;

    public static GunItemRenderer instance() {
        if (instance == null) {
            instance = new GunItemRenderer();
        }
        return instance;
    }

    private GunItemRenderer() {
        super(Minecraft.getInstance().getBlockEntityRenderDispatcher(), Minecraft.getInstance().getEntityModels());
    }

    // --- 配置 ---
    // 一人称・地面ドロップの基準位置は、モデル側のロケーターボーン（idle_view / iron_view / ground、
    // 07-model-assets.md）から読み取る。コード側に位置を決め打ちしない（作者がBlockbench上で
    // 配置を決められるようにするため）。下記はその上に乗せる微調整用で、既定は無変換。
    private static final float MODEL_SCALE = 1.0f;
    private static final float FIRST_PERSON_X = 0f;
    private static final float FIRST_PERSON_Y = 0f;
    private static final float FIRST_PERSON_Z = 0f;
    private static final float FIRST_PERSON_YAW_DEG = 0f;
    private static final float FIRST_PERSON_PITCH_DEG = 0f;
    private static final float OTHER_CONTEXT_SCALE = 0.5f;
    /**
     * 三人称の手持ち表示の拡大率。既定はモデルの実寸そのまま（1.0）。viewmodelは一人称で見栄えする
     * よう誇張して作るのが普通なので、三人称では小さくしたくなる可能性がある。🟡仮・実機で調整する値。
     */
    private static final float THIRD_PERSON_SCALE = 1.0f;

    /**
     * {@code renderByItem} に渡される {@link PoseStack} のローカル空間における「アイテムの基準点」。
     *
     * <p>{@code ItemRenderer#render} は独自レンダラーを呼ぶ直前に {@code translate(-0.5, -0.5, -0.5)}
     * を積むため、{@code renderByItem} の中のローカル空間は<b>Javaアイテムモデル空間（ブロックが0〜1）</b>
     * であり、<b>ローカル(0.5, 0.5, 0.5)</b> が display 変換の基準点になる。コンテキスト別の意味は
     * 一人称＝カメラ（視点）位置、地面ドロップ＝ドロップの中心、額縁＝額縁の中心。</p>
     *
     * <p>一方 Bedrock(Blockbench) はブロック中心をX/Zの0とする centered grid（Yのみブロック底面が0）
     * なので、{@code BedrockGeometryLoader} が出す座標との間にX/Zで0.5ブロックのズレがある。
     * その差をここで吸収する（吸収し忘れると銃が全コンテキストで0.5ブロックずれる）。</p>
     */
    private static final float ANCHOR = 0.5f;

    /**
     * 非ADS時の一人称カメラ基準ロケーター。{@code root} の外に置く前提なので、アニメーションで
     * {@code root} を動かしてもこの基準点は動かない（＝銃の動きがそのまま画面に出る）。
     */
    private static final String LOCATOR_IDLE_VIEW = GunModelCache.Locators.IDLE_VIEW;
    /**
     * ADS時の一人称カメラ基準ロケーター（サイトの照準線上に作者が置く）。{@code root} の子なので、
     * 覗いている間はサイトがカメラに固定される。
     *
     * <p><b>{@link #LOCATOR_IDLE_VIEW} と同じ位置に置くとADSが無効になる</b>（腰だめでも
     * サイトがカメラに乗ったままになる）。{@link GunModelCache} が読み込み時に警告する。</p>
     */
    private static final String LOCATOR_IRON_VIEW = GunModelCache.Locators.IRON_VIEW;
    /** 地面ドロップ表示の基準ロケーター。 */
    private static final String LOCATOR_GROUND = "ground";
    /**
     * 三人称の手持ち表示の基準ロケーター（07-model-assets.md）。作者がモデルの「手で握る位置」に
     * pivotを置けば、そこがプレイヤーの手に一致する。未作成の間は既定配置へフォールバックするので、
     * 三人称の見た目は崩れたままになる（本来はworldmodelを別途用意するのが本筋）。
     */
    private static final String LOCATOR_THIRD_PERSON_HAND = "thirdperson_hand";
    /** アイテムフレーム等の固定表示の基準ロケーター。 */
    private static final String LOCATOR_FIXED = "fixed";
    /** ハンドアンカー（06-animations.md）で腕を追従させるボーン。 */
    private static final String BONE_RIGHT_HAND = "right_hand";
    private static final String BONE_LEFT_HAND = "left_hand";
    /**
     * 排莢される薬莢のボーン。このボーンだけは「銃に装填されている1個」に加えて、
     * 飛行中のぶんを{@link ShellEjectionTracker}の生存インスタンスの数だけ重ねて描く。
     */
    private static final String BONE_EJECTED_SHELL = "ammo";
    /**
     * マガジン内に見えている弾のボーン。<b>マガジンが空のときは描かない</b>（{@link #hideEmptyMagazineAmmo}）。
     * 薬室の弾（{@link #BONE_EJECTED_SHELL}）とは別物で、残弾1発のクローズボルト銃は
     * 「薬室に1発・マガジンは空」なのでこちらは消える。
     */
    private static final String BONE_MAGAZINE_AMMO = "mag_ammo";
    /**
     * マズルフラッシュの位置を示す<b>ロケーター</b>ボーン（cubeを持たせない）。作者はBlockbenchで
     * このボーンのpivotを銃口に置くだけでよく、板もUVもアニメーションのキーフレームも作らない。
     * 描画はコード側が{@link #renderMuzzleFlash}で発光ビルボードを1枚生成して行い、表示タイミングは
     * {@link MuzzleFlashState}が持つ。
     */
    private static final String BONE_MUZZLE_FLASH = "muzzle_flash";

    /**
     * マズルフラッシュのテクスチャ。銃ごとではなく共有（将来gunpackで銃ごとに差し替える余地はある）。
     * <b>アルファ付き（RGBA）である必要がある</b>: 背景が不透明だと板の四角がそのまま見える。
     */
    private static final ResourceLocation MUZZLE_FLASH_TEXTURE =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "textures/effect/muzzle_flash.png");

    /** マズルフラッシュの板の一辺の半分[ブロック]。🟡仮（実機で見ながら調整する値。0.25から2/3へ縮小）。 */
    private static final float MUZZLE_FLASH_HALF_SIZE = 0.167f;

    /**
     * 飛行中の薬莢のクリップ内時刻の受け取り用。{@code renderByItem}はレンダースレッドからのみ
     * 呼ばれるので使い回してよい（毎フレームの確保を避ける）。
     */
    private static final float[] SHELL_TIMES = new float[ShellEjectionTracker.CAPACITY];

    /**
     * {@code PlayerRenderer#renderRightHand}/{@code renderLeftHand} が描くバニラの腕の箱の最小コーナーを、
     * こちらの座標系（+X右 / +Y上 / +Z手前）へ写した位置。単位はブロック。
     *
     * <p>エンティティモデル空間は +Y下・+X左・-Z前で、{@code scale(-1, -1, 1)} でこちらの座標系へ写る。
     * {@code HumanoidModel} の定義:</p>
     * <ul>
     *   <li>right_arm: {@code PartPose.offset(-5, 2, 0)} + {@code addBox(-3, -2, -2, 4, 12, 4)}
     *       → モデル空間 x[-8,-4] y[0,12] z[-2,2] → 写像後 x[4,8] y[-12,0] z[-2,2]</li>
     *   <li>left_arm: {@code PartPose.offset(5, 2, 0)} + {@code addBox(-1, -2, -2, 4, 12, 4)}
     *       → モデル空間 x[4,8] y[0,12] z[-2,2] → 写像後 x[-8,-4] y[-12,0] z[-2,2]</li>
     * </ul>
     */
    private static final Vector3f VANILLA_RIGHT_ARM_MIN = new Vector3f(4f / 16f, -12f / 16f, -2f / 16f);
    private static final Vector3f VANILLA_LEFT_ARM_MIN = new Vector3f(-8f / 16f, -12f / 16f, -2f / 16f);

    /**
     * バニラが腕に必ず掛ける「揺れ」のZ回転[rad]（右腕。左腕は符号が逆）。{@link #cancelVanillaArmBob} で打ち消す。
     *
     * <p>{@code PlayerRenderer#renderHand} は内部で {@code setupAnim} を通し、その最後で
     * {@code AnimationUtils.bobModelPart} が {@code zRot += multiplier * (cos(ageInTicks * 0.09) * 0.05 + 0.05)}
     * を加算する。一人称の手は {@code ageInTicks = 0} 固定で呼ばれるので、値は常に
     * {@code ±(1 * 0.05 + 0.05) = ±0.1 rad}（約5.73度）になる。同時に加算される {@code xRot} の方は
     * {@code renderHand} が描画直前に0へ潰すので残らない。</p>
     *
     * <p><b>バニラのバージョンを上げる際は{@code AnimationUtils}の式を確認すること。</b></p>
     */
    private static final float VANILLA_ARM_BOB_Z_ROT = 0.1f;
    /** バニラの腕パーツの回転中心（{@code HumanoidModel#setupAnim} が毎回 {@code x=∓5, y=2, z=0} へ固定する）。 */
    private static final float VANILLA_ARM_PIVOT_X = 5f / 16f;
    private static final float VANILLA_ARM_PIVOT_Y = 2f / 16f;

    /** スロットに対する占有率。1.0で長辺がスロットいっぱい。🟡仮、実機で調整 */
    private static final float ICON_SCALE = 1.0f;

    @Override
    public void renderByItem(ItemStack stack, ItemDisplayContext context, PoseStack poseStack,
                              MultiBufferSource bufferSource, int packedLight, int packedOverlay) {
        if (context == ItemDisplayContext.GUI) {
            // インベントリ等のアイコンは3Dモデルではなく平面画像で表示する
            // （3Dモデルをそのまま縮小表示すると小さすぎて視認できないため、07-model-assets.mdの
            // 「アイテムアイコン」枠に沿って専用の平面画像を使う）。
            renderFlatIcon(stack, poseStack, bufferSource, packedLight, packedOverlay);
            return;
        }

        ResourceLocation gunId = GunItem.gunId(stack);
        if (gunId == null) {
            return;
        }
        String gunPath = gunId.getPath();
        BakedGunModel model = GunModelCache.getGeometry(gunPath);
        if (model == null) {
            if (WARNED_MISSING_MODELS.add(gunId)) {
                LOGGER.warn("[Cordite] gunpack定義 '{}' に対応するモデル '{}' がありません", gunId, gunPath);
            }
            return;
        }

        Map<String, AnimationSampler.Pose> poseMap = sampleCurrentPose(gunPath, stack, context);

        poseStack.pushPose();
        applyContextPlacement(poseStack, context, model, poseMap);

        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityCutoutNoCull(model.texture()));
        renderBone(model.root(), poseStack, consumer, poseMap, sampleEjectedShells(gunPath),
                packedLight, packedOverlay);

        if (context.firstPerson()) {
            // ハンドアンカー方式の腕は viewmodel（一人称）のみ（06-animations.md）
            renderHandAnchoredArms(poseStack, model, poseMap, bufferSource, packedLight);
            // マズルフラッシュも一人称のみ。{@link MuzzleFlashState} はローカルプレイヤー1人分の状態なので、
            // 三人称/他プレイヤーの銃にも描くと「自分が撃つと他人の銃も光る」ことになる。
            // 他プレイヤーぶんの表示は worldmodel 実装時に扱う（docs/design/animation-system.md）。
            renderMuzzleFlash(poseStack, model, poseMap, bufferSource);
        }

        poseStack.popPose();
    }

    /**
     * 現在のボーンポーズを決定する。<b>常に待機クリップ（{@code idle}）を土台に敷き</b>、その上に
     * 再生中のアクション（take_out/fire/reload/reload_empty）か、弾切れ待機の上書き
     * （{@link #emptyPoseOverlayFor}）を重ねる（{@link AnimationSampler#sampleLayered}）。
     * どのクリップを何秒目で再生するかの判定は {@link GunActionPlayback}（サウンド再生と共通）。
     * 三人称等は待機ポーズと弾切れ上書きだけを使い、worldmodel専用クリップは未実装である。
     *
     * <p>土台を敷くのは、アクションのクリップが<b>動かすボーンのトラックしか持たない</b>ため。
     * 例えば {@code reload} はマガジンしか動かさないので、待機の手のポーズを下に敷かないと
     * リロード中だけ手がrestポーズへ飛ぶ。</p>
     *
     * <p>待機クリップは<b>常に先頭フレーム（0秒）</b>でサンプリングする（待機の時間再生＝呼吸などの
     * ループ再生は未実装）。弾切れ待機が {@code reload_empty} の先頭フレームで成立するのはこのため。</p>
     */
    private static Map<String, AnimationSampler.Pose> sampleCurrentPose(String gunId, ItemStack stack,
                                                                          ItemDisplayContext context) {
        Minecraft mc = Minecraft.getInstance();
        long gameTime = mc.level != null ? mc.level.getGameTime() : 0L;
        float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);

        GunActionPlayback.Sample sample = GunActionPlayback.current(gunId, stack, gameTime, partialTick);
        // current() の終了処理がリロード完了時刻を記録する。後段の猶予判定はこの状態遷移に依存するため、
        // emptyPoseOverlayFor() より必ず先に評価しないと終了フレームだけ弾切れ姿勢が混ざる。
        BakedAnimation idle = GunModelCache.getIdleAnimation(gunId);
        BakedAnimation emptyPose = emptyPoseOverlayFor(gunId, stack);
        if (!context.firstPerson()) {
            sample = null;
        }

        Map<String, AnimationSampler.Pose> poseMap;
        if (sample == null) {
            poseMap = AnimationSampler.sampleLayered(idle, 0f, emptyPose, 0f);
        } else {
            poseMap = AnimationSampler.sampleLayered(idle, 0f, sample.animation(), sample.animTime());
            pinEmptyHoldOpen(poseMap, gunId, idle, emptyPose, sample.action());
        }
        hideEmptyMagazineAmmo(poseMap, stack, gameTime);
        return poseMap;
    }

    /**
     * 撃ち切りの1発で、<b>発射モーションを再生しつつスライド／ボルトの後退を維持する</b>。
     *
     * <p>撃ち切った瞬間からチャンバーを開けておきたいが、{@code fire}はスライドが前進して終わる
     * クリップなので、そのまま再生するとスライドが閉じてしまう。かといって発射モーションを
     * 丸ごと省くと<b>最後の1発だけ銃が反動で跳ねない</b>（以前はこちらだった）。</p>
     *
     * <p>そこで、弾切れポーズ（{@code reload_empty}の先頭フレーム）が<b>待機ポーズと違えている部分だけ</b>を
     * 発射モーションの上へ貼り直す（{@link AnimationSampler#applyDifferences}）。glockの場合その差分は
     * {@code bolt}の後退だけで、{@code root}は待機と同値なので<b>反動はそのまま残る</b>。
     * 作者は「{@code reload_empty}の0秒目にスライドを後退させたキーを打つ」という既存の作業だけでよく、
     * {@code fire_empty}を別途作らなくても撃ち切りが成立する。</p>
     *
     * <p>適用するのは発射系のアクション中だけ。リロード系のクリップはスライドの解放（前進）を
     * 自分で表現しているので、貼り直すと<b>スライドが永久に開いたまま</b>になる。
     * 撃ち切り専用クリップ（{@code fire_empty}）が用意されている銃も、スライドの扱いを
     * そのクリップに任せるので対象外。</p>
     */
    private static void pinEmptyHoldOpen(Map<String, AnimationSampler.Pose> poseMap, String gunId,
                                          BakedAnimation idle, BakedAnimation emptyPose,
                                          GunAnimationState.Action action) {
        boolean firing = action == GunAnimationState.Action.FIRE || action == GunAnimationState.Action.FIRE_EMPTY;
        if (emptyPose == null || !firing || GunActionPlayback.hasDedicatedFireEmpty(gunId)) {
            return;
        }
        AnimationSampler.applyDifferences(poseMap,
                AnimationSampler.sampleLayered(idle, 0f, null, 0f),
                AnimationSampler.sampleLayered(idle, 0f, emptyPose, 0f));
    }

    /**
     * マガジンが空の間、マガジン内の弾（{@link #BONE_MAGAZINE_AMMO}）を描かない。
     *
     * <p>残弾表示は「マガジン＋薬室」の合計なので、クローズボルト銃で<b>残り1発</b>のときは
     * 「薬室に1発・マガジンは空」の状態になる。モデルはマガジン内の弾を常に持っているため、
     * ここで消さないと空のマガジンに弾が見えたままになる。オープンボルト銃は薬室を持たない
     * （{@code GunItem#isChambered} が常にfalse）ので、同じ条件がそのまま通る。</p>
     *
     * <p><b>リロード中と、その直後の同期待ちの間は触らない</b>。リロードクリップの
     * {@code mag_ammo} のscaleキーが「古いマガジンの弾が消える→新しいマガジンで戻る」を
     * 表現しているので、そこへ割り込むと入れ直した弾が出てこない。再生直後の猶予
     * （{@link GunAnimationState#withinReloadSyncGrace}）も同じで、残弾の同期がまだ0のままなので
     * 弾が一瞬消えてから現れるちらつきになる。</p>
     *
     * <p>消し方はscale0（{@link #safeScale} で潰れる）。ボーン階層はそのまま残るので、
     * マガジン本体の動きには影響しない。</p>
     */
    private static void hideEmptyMagazineAmmo(Map<String, AnimationSampler.Pose> poseMap, ItemStack stack,
                                               long gameTime) {
        Minecraft mc = Minecraft.getInstance();
        if (!(stack.getItem() instanceof GunItem gunItem) || gunItem.getMagazine(stack, mc.level) > 0) {
            return;
        }
        if (GunAnimationState.isReloading() || GunAnimationState.withinReloadSyncGrace(gameTime)) {
            return;
        }
        AnimationSampler.Pose current = poseMap.get(BONE_MAGAZINE_AMMO);
        poseMap.put(BONE_MAGAZINE_AMMO, new AnimationSampler.Pose(
                current != null ? current.positionDelta() : new Vector3f(),
                current != null ? current.rotationDeltaDeg() : new Vector3f(),
                new Vector3f()));
    }

    /**
     * 飛行中の薬莢のポーズを古い順に返す（飛んでいなければ空リスト）。
     *
     * <p>薬莢は発射クリップ本体とは<b>独立したタイムライン</b>で動く（{@link ShellEjectionTracker}）。
     * 連射すると発射クリップは撃つたびに頭から再生し直されるが、それに薬莢が乗っていると
     * 飛行中の薬莢が銃の中へ戻ってしまうため、軌道だけを専用クリップ（{@code eject}）へ分けてある。
     * 装填されている側の薬莢（＝ボーン本来の描画）は発射クリップの差分で動くのでここでは扱わない。</p>
     */
    private static List<AnimationSampler.Pose> sampleEjectedShells(String gunId) {
        BakedAnimation eject = GunModelCache.getEjectAnimation(gunId);
        if (eject == null) {
            return List.of(); // 排莢クリップ未作成の銃: 薬莢は飛ばない
        }
        BoneTrack track = eject.bones().get(BONE_EJECTED_SHELL);
        if (track == null) {
            return List.of();
        }

        Minecraft mc = Minecraft.getInstance();
        long gameTime = mc.level != null ? mc.level.getGameTime() : 0L;
        float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);
        int count = ShellEjectionTracker.collect(
                eject.lastKeyframeSeconds(), gameTime, partialTick, SHELL_TIMES);
        if (count == 0) {
            return List.of();
        }

        List<AnimationSampler.Pose> poses = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            AnimationSampler.Pose pose = AnimationSampler.samplePose(track, SHELL_TIMES[i]);
            if (pose != null) {
                poses.add(pose);
            }
        }
        return poses;
    }

    /**
     * 弾切れ待機のときに待機ポーズへ重ねるクリップを返す（通常の待機中は null＝待機ポーズのみ）。
     * 撃ち切り時にスライド／ボルトが後退保持される銃（{@link GunDefinition#holdOpenOnEmpty()}）で
     * 残弾が尽きている間だけ、後退状態を表示し続けるために使う。
     * 重ねるのは常に先頭フレーム（0秒）（{@link #sampleCurrentPose}）。
     *
     * <p>弾切れ待機には<b>{@code reload_empty} の先頭フレーム</b>を使う。弾切れリロードは
     * 「スライドが後退保持された状態」から始まるので、その0秒目のポーズがそのまま弾切れ待機になる。
     * 専用の待機クリップ（{@code idle_empty}）は作らない——2つ持つと両者の先頭ポーズを手で
     * 合わせ込む必要があり、ズレるとリロード開始の瞬間にスライドが飛ぶ。同じフレームを共用すれば
     * その不整合が原理的に起きない。作者側の作業は「{@code reload_empty} の0秒目に
     * チャージングハンドル／スライドを後退させたキーを打つ」だけ。</p>
     *
     * <p><b>リロード直後は残弾0でも弾切れ表示にしない</b>（{@link GunAnimationState#withinReloadSyncGrace}）。
     * リロードアニメーションはローカル予測で始まるためサーバーの装填完了より先に終わり、その隙間で
     * 残弾を読むとまだ0なので、スライドが一瞬開いてから閉じるちらつきになる。</p>
     */
    private static BakedAnimation emptyPoseOverlayFor(String gunId, ItemStack stack) {
        Minecraft mc = Minecraft.getInstance();
        long gameTime = mc.level != null ? mc.level.getGameTime() : 0L;
        if (GunAnimationState.withinReloadSyncGrace(gameTime)) {
            return null;
        }
        if (stack.getItem() instanceof GunItem gunItem) {
            GunDefinition props = GunItem.definitionOf(stack, mc.level);
            // 撃ち切りは「パケットで届いた事実」を優先し、同期が追いついたらコンポーネントの値に任せる
            // （コンポーネントだけを見ると、0発になった瞬間より数tick遅れてチャンバーが開く）
            boolean empty = GunAnimationState.emptiedByRecentShot(gameTime) || gunItem.getTotalAmmo(stack, mc.level) <= 0;
            if (props != null && props.holdOpenOnEmpty() && empty) {
                return GunModelCache.getReloadEmptyAnimation(gunId); // 先頭フレーム＝スライド後退保持の姿勢
            }
        }
        return null;
    }

    /**
     * インベントリ等のアイコンを平面画像で描く。
     *
     * <p>GUIコンテキストの{@link PoseStack}は、バニラが{@code scaling(1,-1,1)}を掛けた後の状態で渡ってくる
     * （＝<b>このローカル空間では+Yが画面の上</b>）。ここでさらにY反転を掛けると画像が上下逆さまになる。</p>
     *
     * <p>板の大きさは<b>長辺</b>を{@link #ICON_SCALE}に合わせる。画像ごとの縦横比は
     * {@link GunModelCache} がリソースリロード時に読み取り、短辺だけを縮める。</p>
     */
    private static void renderFlatIcon(ItemStack stack, PoseStack poseStack, MultiBufferSource bufferSource,
                                       int light, int overlay) {
        ResourceLocation gunId = GunItem.gunId(stack);
        GunModelCache.Icon icon = GunModelCache.getIcon(gunId == null ? "" : gunId.getPath());
        poseStack.pushPose();
        poseStack.translate(ANCHOR, ANCHOR, ANCHOR);

        float halfW = ICON_SCALE / 2f * Math.min(1f, icon.aspect());
        float halfH = ICON_SCALE / 2f * Math.min(1f, 1f / icon.aspect());
        PoseStack.Pose pose = poseStack.last();
        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityCutoutNoCull(icon.texture()));
        Vector3f normal = new Vector3f(0f, 0f, 1f);

        addIconVertex(consumer, pose, normal, light, overlay, -halfW, -halfH, 0, 0, 1);
        addIconVertex(consumer, pose, normal, light, overlay, halfW, -halfH, 0, 1, 1);
        addIconVertex(consumer, pose, normal, light, overlay, halfW, halfH, 0, 1, 0);
        addIconVertex(consumer, pose, normal, light, overlay, -halfW, halfH, 0, 0, 0);

        poseStack.popPose();
    }

    private static void addIconVertex(VertexConsumer consumer, PoseStack.Pose pose, Vector3f normal,
                                       int light, int overlay, float x, float y, float z, float u, float v) {
        consumer.addVertex(pose, x, y, z)
                .setColor(255, 255, 255, 255)
                .setUv(u, v)
                .setOverlay(overlay)
                .setLight(light)
                .setNormal(pose, normal.x(), normal.y(), normal.z());
    }

    private static void applyContextPlacement(PoseStack poseStack, ItemDisplayContext context, BakedGunModel model,
                                               Map<String, AnimationSampler.Pose> poseMap) {
        // まず原点をアイテムの基準点（ローカル 0.5, 0.5, 0.5）へ移す。以降の座標はすべて
        // 「基準点からの相対位置」になる（{@link #ANCHOR} の説明を参照）。
        poseStack.translate(ANCHOR, ANCHOR, ANCHOR);

        switch (context) {
            // FIRST_PERSON_LEFT_HAND は左利き設定・オフハンド時に使われる。バニラの手変換は
            // GunClientExtensions で丸ごと止めており、どちらのコンテキストでも PoseStack は
            // カメラ基準のままなので、左右で配置を変える必要はない（左右反転はしない）。
            case FIRST_PERSON_RIGHT_HAND, FIRST_PERSON_LEFT_HAND -> {
                cancelViewSwayForAds(poseStack);
                poseStack.translate(FIRST_PERSON_X, FIRST_PERSON_Y, FIRST_PERSON_Z);
                poseStack.mulPose(Axis.YP.rotationDegrees(FIRST_PERSON_YAW_DEG));
                poseStack.mulPose(Axis.XP.rotationDegrees(FIRST_PERSON_PITCH_DEG));
                poseStack.scale(MODEL_SCALE, MODEL_SCALE, MODEL_SCALE);
                alignViewLocatorToAnchor(poseStack, model, poseMap);
            }
            case GROUND -> {
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
                alignLocatorToAnchor(poseStack, model, LOCATOR_GROUND);
            }
            // 三人称の手持ち。基準点はプレイヤーの手の位置なので、モデル側で「手で握る位置」に置いた
            // thirdperson_hand ロケーターをそこへ合わせる。左手側も同じロケーターでよい
            // （バニラが左右それぞれの手の位置までPoseStackを進めてから呼ぶため）。
            case THIRD_PERSON_RIGHT_HAND, THIRD_PERSON_LEFT_HAND -> {
                poseStack.scale(THIRD_PERSON_SCALE, THIRD_PERSON_SCALE, THIRD_PERSON_SCALE);
                alignLocatorToAnchor(poseStack, model, LOCATOR_THIRD_PERSON_HAND);
            }
            case FIXED -> {
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
                alignLocatorToAnchor(poseStack, model, LOCATOR_FIXED);
            }
            default -> {
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
                alignBedrockOriginToDefault(poseStack);
            }
        }
    }

    /**
     * ADS中だけ、一人称の手に乗っている「揺れ」を打ち消す。腰だめ（ADS量0）では何もしないので、
     * 通常時の腕の動き＝臨場感はそのまま残る。
     *
     * <p>{@code renderByItem} に届く時点で、{@link PoseStack} には手の位置合わせ変換の手前に
     * 次の2つが積まれている（どちらもバニラがカメラ基準の行列へ直接掛けるもので、
     * {@code applyForgeHandTransform} で止められる範囲の外）:</p>
     * <ol>
     *   <li>{@code GameRenderer#bobView} — 歩行・走行に合わせた上下左右の揺れ（設定「視点の揺れ」がONのときのみ）</li>
     *   <li>{@code ItemInHandRenderer#renderHandsWithItems} — 視点回転に手が遅れて追従する回転（{@code xBob}/{@code yBob}）</li>
     * </ol>
     *
     * <p>サイトを覗いている間はこれらがそのままレティクルのブレになるため、同じ変換の逆を
     * ADS量ぶんだけ積んで相殺する。積む順は「後に積まれた側から逆順に」（下記コード順）。
     * ダメージ時の{@code bobHurt}は被弾のフィードバックなので打ち消さない。</p>
     *
     * <p>バニラの実装値をそのまま参照しているので、Minecraftのバージョンを上げる際は
     * {@code bobView}/{@code renderHandsWithItems}の式が変わっていないか確認すること。</p>
     */
    private static void cancelViewSwayForAds(PoseStack poseStack) {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer player = mc.player;
        if (player == null) {
            return;
        }
        float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);
        float ads = GunAdsState.progress(partialTick);
        if (ads <= 0f) {
            return; // 腰だめ: バニラの揺れをそのまま活かす
        }

        // 2. 手の追従遅れ（rotX → rotY の順に積まれているので、逆順に rotY → rotX で戻す）
        float lagX = (player.getViewXRot(partialTick) - Mth.lerp(partialTick, player.xBobO, player.xBob)) * 0.1f;
        float lagY = (player.getViewYRot(partialTick) - Mth.lerp(partialTick, player.yBobO, player.yBob)) * 0.1f;
        poseStack.mulPose(Axis.YP.rotationDegrees(-lagY * ads));
        poseStack.mulPose(Axis.XP.rotationDegrees(-lagX * ads));

        // 1. 歩行の揺れ（translate → rotZ → rotX の順に積まれているので、逆順に戻す）
        if (mc.options.bobView().get()) {
            float walkDelta = player.walkDist - player.walkDistO;
            float phase = -(player.walkDist + walkDelta * partialTick);
            float amount = Mth.lerp(partialTick, player.oBob, player.bob);
            float sin = Mth.sin(phase * (float) Math.PI);
            float cos = Mth.cos(phase * (float) Math.PI);
            poseStack.mulPose(Axis.XP.rotationDegrees(
                    -Math.abs(Mth.cos(phase * (float) Math.PI - 0.2f) * amount) * 5.0f * ads));
            poseStack.mulPose(Axis.ZP.rotationDegrees(-sin * amount * 3.0f * ads));
            poseStack.translate(-sin * amount * 0.5f * ads, Math.abs(cos * amount) * ads, 0f);
        }
    }

    /**
     * 一人称のカメラ基準ロケーターをアイテムの基準点（＝カメラ）へ合わせる。
     * 腰だめでは {@code idle_view}、ADS中は {@code iron_view} で、その間を
     * {@link GunAdsState#progress} で補間する（＝右クリックでサイトがカメラへ寄っていく）。
     *
     * <p><b>点ではなく姿勢（位置＋向き）で合わせる</b>。ロケーターの原点だけを見て平行移動していた頃は、
     * <b>ロケーターの回転が完全に無視されていた</b>——{@code idle_view}はcubeも子ボーンも持たないので、
     * 作者が回転キーを打っても他のどこにも効かず、何も起きなかった。カメラの向きを動かして
     * 「リロードで銃を持ち上げる」ような表現をするには、向きも合わせる必要がある。
     * ロケーターの座標系をカメラの座標系に一致させる（＝その逆変換を積む）ことで両方を扱う。</p>
     *
     * <p>補間は位置を線形、向きを球面線形（slerp）で別々に行う。行列のまま混ぜると、
     * 途中の姿勢が歪む（回転成分が縮む）ため。</p>
     *
     * <p><b>rest位置ではなくアニメーション適用後の姿勢</b>を使う。{@code iron_view} は {@code root} の
     * 子で、待機・発射アニメーションが {@code root} を動かすぶんだけ実際のサイト位置もずれるため、
     * rest位置で合わせるとADSしてもサイトがカメラに乗らない。リロード中はADS自体を無効化してあるので
     * （{@link net.r0319.cordite.client.ClientInputHandler}）、大きく動くモーションを打ち消して
     * 銃が固まって見えることはない。</p>
     *
     * <p>ロケーターが両方とも無ければ既定配置へフォールバックする。</p>
     */
    private static void alignViewLocatorToAnchor(PoseStack poseStack, BakedGunModel model,
                                                  Map<String, AnimationSampler.Pose> poseMap) {
        float partialTick = Minecraft.getInstance().getTimer().getGameTimeDeltaPartialTick(false);
        float ads = GunAdsState.progress(partialTick);

        LocatorFrame hip = animatedLocatorFrame(model, LOCATOR_IDLE_VIEW, poseMap);
        LocatorFrame sight = ads > 0f ? animatedLocatorFrame(model, LOCATOR_IRON_VIEW, poseMap) : null;

        LocatorFrame target;
        if (hip != null && sight != null) {
            // hipは都度生成なので破壊的な補間で問題ない
            target = new LocatorFrame(
                    hip.position().lerp(sight.position(), ads),
                    hip.rotation().slerp(sight.rotation(), ads));
        } else if (hip != null) {
            target = hip;
        } else if (sight != null) {
            target = sight;
        } else {
            alignBedrockOriginToDefault(poseStack);
            return;
        }

        // ロケーターの姿勢 M = T(位置)·R(向き) の逆 M⁻¹ = R⁻¹·T(-位置) を積む。
        // 単位クォータニオンの逆＝共役。回転は mulPose(Quaternionf) で積む（法線行列も同時に回るため、
        // Matrix4f を直接掛けるのと違ってライティングが崩れない）。
        poseStack.mulPose(target.rotation().conjugate());
        poseStack.translate(-target.position().x(), -target.position().y(), -target.position().z());
    }

    /** アニメーション適用後のロケーターの姿勢。位置と向きは別々に補間するので分けて持つ。 */
    private record LocatorFrame(Vector3f position, Quaternionf rotation) {}

    /**
     * アニメーション適用後の、モデル原点から見た指定ボーンの姿勢（pivot位置とボーンの向き）を求める。
     * ボーンが無ければ null。
     */
    private static LocatorFrame animatedLocatorFrame(BakedGunModel model, String boneName,
                                                      Map<String, AnimationSampler.Pose> poseMap) {
        GunBone bone = model.byName().get(boneName);
        if (bone == null) {
            return null;
        }
        PoseStack chain = new PoseStack();
        applyBoneChain(chain, bone, poseMap);
        Matrix4f matrix = chain.last().pose();
        return new LocatorFrame(
                matrix.getTranslation(new Vector3f()),
                matrix.getNormalizedRotation(new Quaternionf()));
    }

    /**
     * 指定ロケーターボーンがアイテムの基準点に来るようモデル全体を平行移動する。
     * 一人称なら「そのロケーターがカメラ（視点）の位置に一致する」、地面ドロップなら
     * 「そのロケーターがドロップの中心に一致する」という意味になる（07-model-assets.md）。
     *
     * <p>ロケーターがモデルに無ければ既定配置（{@link #alignBedrockOriginToDefault}）へフォールバックする。
     * ロケーター自体がアニメーションで動く場合の追従は未対応（rest位置のみを見る）。</p>
     */
    private static void alignLocatorToAnchor(PoseStack poseStack, BakedGunModel model, String locatorName) {
        GunBone locator = model.byName().get(locatorName);
        if (locator == null) {
            alignBedrockOriginToDefault(poseStack);
            return;
        }
        Vector3f offset = locator.modelOffset;
        poseStack.translate(-offset.x(), -offset.y(), -offset.z());
    }

    /**
     * ロケーター指定が無いときの既定配置。Bedrockモデルの原点(0,0,0)を、Javaアイテムモデルの
     * 対応位置＝ブロック底面の中心（基準点から見て真下0.5ブロック）に置く。
     */
    private static void alignBedrockOriginToDefault(PoseStack poseStack) {
        poseStack.translate(0f, -ANCHOR, 0f);
    }

    /**
     * ハンドアンカー方式（06-animations.md）でバニラのプレイヤー腕を描画する。
     *
     * <p>モデル側の {@code right_hand}/{@code left_hand} ボーンに置かれた<b>腕プレースホルダの箱</b>
     * （バニラ準拠の4×12×4px。07-model-assets.md）に、バニラの腕モデルがぴったり重なるよう配置する。
     * つまり配置数値はコード側に持たず、作者がBlockbench上で箱を動かせばそのまま追従する。
     * プレースホルダの箱自体はBox UVのため描画対象から外れており（{@code BedrockGeometryLoader}）、
     * 二重に見えることはない。</p>
     *
     * <p>{@code renderRightHand}/{@code renderLeftHand} は内部で {@code HumanoidModel#setupAnim} を
     * 通すため、バニラ一人称の腕と同じ固定のZ軸傾き（{@code AnimationUtils#bobArms} 由来、約±5.73度）が
     * 掛かる。これが残っていると<b>作者がBlockbenchで合わせた握り位置と実際の腕がズレる</b>ので、
     * {@link #cancelVanillaArmBob} で打ち消してから描く。</p>
     *
     * <p>Slimスキンでも位置合わせの基準は変わらない: {@code setupAnim} が腕パーツの
     * オフセットを毎回 {@code x=∓5, y=2, z=0} へ固定するため、Slim側の{@code PartPose}（{@code y=2.5}）は
     * 効かない。差はSlimの腕が1px細いことだけで、右腕は最小コーナーが一致し、
     * 左腕のみ幅の差ぶん（1px）X方向にズレる。</p>
     */
    private static void renderHandAnchoredArms(PoseStack poseStack, BakedGunModel model,
                                                Map<String, AnimationSampler.Pose> poseMap,
                                                MultiBufferSource bufferSource, int light) {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer player = mc.player;
        if (player == null || player.isInvisible()) {
            return;
        }
        if (!(mc.getEntityRenderDispatcher().getRenderer(player) instanceof PlayerRenderer playerRenderer)) {
            return;
        }
        renderAnchoredArm(poseStack, model, poseMap, bufferSource, light, playerRenderer, player,
                BONE_RIGHT_HAND, VANILLA_RIGHT_ARM_MIN, true);
        renderAnchoredArm(poseStack, model, poseMap, bufferSource, light, playerRenderer, player,
                BONE_LEFT_HAND, VANILLA_LEFT_ARM_MIN, false);
    }

    private static void renderAnchoredArm(PoseStack poseStack, BakedGunModel model,
                                           Map<String, AnimationSampler.Pose> poseMap,
                                           MultiBufferSource bufferSource, int light,
                                           PlayerRenderer playerRenderer, LocalPlayer player,
                                           String boneName, Vector3f vanillaArmMin, boolean rightArm) {
        GunBone bone = model.byName().get(boneName);
        if (bone == null || bone.boundsMin == null) {
            return; // ボーンが無い、または位置合わせの基準になる箱が無い
        }

        poseStack.pushPose();
        applyBoneChain(poseStack, bone, poseMap);
        // バニラの腕の箱の最小コーナーを、プレースホルダの箱の最小コーナーへ合わせる
        poseStack.translate(
                bone.boundsMin.x() - vanillaArmMin.x(),
                bone.boundsMin.y() - vanillaArmMin.y(),
                bone.boundsMin.z() - vanillaArmMin.z());
        // エンティティモデル空間（+Y下・+X左）へ写す。行列式は正のままなので面の裏表は反転しない。
        poseStack.scale(-1f, -1f, 1f);
        cancelVanillaArmBob(poseStack, rightArm);

        if (rightArm) {
            playerRenderer.renderRightHand(poseStack, bufferSource, light, player);
        } else {
            playerRenderer.renderLeftHand(poseStack, bufferSource, light, player);
        }
        poseStack.popPose();
    }

    /**
     * バニラが腕に必ず掛ける固定のZ軸傾き（{@link #VANILLA_ARM_BOB_Z_ROT}）を打ち消す。
     * 呼ぶ時点の{@link PoseStack}は<b>エンティティモデル空間</b>（{@code scale(-1,-1,1)} 適用後）であること。
     *
     * <p>{@code ModelPart#render}は内部で「pivotへの平行移動 → {@code zRot}回転」の順に積むので、
     * その手前で<b>同じpivotまわりの逆回転</b>を積めば、回転だけが相殺されて平行移動（＝パーツの正規の位置）
     * だけが残る。結果、バニラの腕が<b>モデル側の腕プレースホルダの箱にぴったり重なる</b>。</p>
     *
     * <p>打ち消さないと肩を軸に約5.73度傾いたまま描かれ、手先（肩から12px）で約1.2px＝0.075ブロック
     * ズレる。ハンドアンカー方式は「作者がBlockbenchで置いた箱の位置に腕が来る」ことが前提なので、
     * この傾きが残っているとアニメーションで詰めた握り位置と実際の腕が合わない。
     * 袖（{@code rightSleeve}）は{@code copyFrom}で腕と同じ姿勢になるため、これ1回で両方に効く。</p>
     */
    private static void cancelVanillaArmBob(PoseStack poseStack, boolean rightArm) {
        float pivotX = rightArm ? -VANILLA_ARM_PIVOT_X : VANILLA_ARM_PIVOT_X;
        float zRot = rightArm ? VANILLA_ARM_BOB_Z_ROT : -VANILLA_ARM_BOB_Z_ROT;
        poseStack.translate(pivotX, VANILLA_ARM_PIVOT_Y, 0f);
        poseStack.mulPose(Axis.ZP.rotation(-zRot));
        poseStack.translate(-pivotX, -VANILLA_ARM_PIVOT_Y, 0f);
    }

    /** モデル原点から指定ボーンまでの変換（各ボーンのオフセット＋アニメーション差分）を根元から順に積む。 */
    private static void applyBoneChain(PoseStack poseStack, GunBone bone,
                                        Map<String, AnimationSampler.Pose> poseMap) {
        if (bone.parent != null) {
            applyBoneChain(poseStack, bone.parent, poseMap);
        }
        poseStack.translate(bone.localOffset.x(), bone.localOffset.y(), bone.localOffset.z());
        applyAnimationDelta(poseStack, poseMap.get(bone.name));
    }

    private static void renderBone(GunBone bone, PoseStack poseStack, VertexConsumer consumer,
                                    Map<String, AnimationSampler.Pose> poseMap,
                                    List<AnimationSampler.Pose> shellPoses, int light, int overlay) {
        if (!shellPoses.isEmpty() && bone.name.equals(BONE_EJECTED_SHELL)) {
            renderEjectedShells(bone, poseStack, consumer, shellPoses, light, overlay);
        }

        poseStack.pushPose();
        poseStack.translate(bone.localOffset.x(), bone.localOffset.y(), bone.localOffset.z());
        applyAnimationDelta(poseStack, poseMap.get(bone.name));

        drawCubes(bone, poseStack.last(), consumer, light, overlay);

        for (GunBone child : bone.children) {
            renderBone(child, poseStack, consumer, poseMap, shellPoses, light, overlay);
        }
        poseStack.popPose();
    }

    /**
     * マズルフラッシュを{@code muzzle_flash}ロケーターの位置に1枚のビルボード（常にカメラを向く板）
     * として描く。銃本体は{@code entityCutoutNoCull}（アルファ2値・ワールドの明るさで暗くなる）だが、
     * フラッシュは発光体なので<b>フルブライト＋半透明</b>で描く。これをしないと暗所でフラッシュが
     * 真っ暗になり、アルファのグラデーションも出ない。
     *
     * <p>板は毎発ランダムに回転・拡縮し（{@link MuzzleFlashState}）、表示時間の経過に応じて
     * アルファをフェードアウトさせる。ロケーターが無い銃では何もしない（テクスチャの参照自体を
     * 行わないので、アセット未作成でもミッシングテクスチャにならない）。</p>
     */
    private static void renderMuzzleFlash(PoseStack poseStack, BakedGunModel model,
                                           Map<String, AnimationSampler.Pose> poseMap,
                                           MultiBufferSource bufferSource) {
        GunBone bone = model.byName().get(BONE_MUZZLE_FLASH);
        if (bone == null) {
            return; // ロケーター未作成の銃
        }
        Minecraft mc = Minecraft.getInstance();
        long gameTime = mc.level != null ? mc.level.getGameTime() : 0L;
        float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);
        if (!MuzzleFlashState.isActive(gameTime, partialTick)) {
            return;
        }

        poseStack.pushPose();
        applyBoneChain(poseStack, bone, poseMap);
        PoseStack.Pose pose = poseStack.last();

        // ビルボードの向き: このボーンのローカル空間から見たカメラ方向。描画空間の原点＝カメラ位置なので、
        // 変換行列の逆行列で原点を引き戻せば求まる（一人称/三人称や銃の姿勢に依らず正しく向く）。
        Vector3f toCamera = new Matrix4f(pose.pose()).invert().transformPosition(new Vector3f());
        if (toCamera.lengthSquared() < 1.0e-8f) {
            poseStack.popPose();
            return; // カメラがボーンと同じ位置（通常起きない）
        }
        toCamera.normalize();

        // カメラ方向に垂直な2軸を作り、銃口方向まわりに毎発ランダムなロールをかける
        Vector3f reference = Math.abs(toCamera.y()) > 0.99f ? new Vector3f(0f, 0f, 1f) : new Vector3f(0f, 1f, 0f);
        Vector3f right = reference.cross(toCamera, new Vector3f()).normalize();
        Vector3f up = new Vector3f(toCamera).cross(right, new Vector3f()).normalize();
        Quaternionf roll = new Quaternionf().rotateAxis(
                (float) Math.toRadians(MuzzleFlashState.rollDegrees()), toCamera);
        roll.transform(right);
        roll.transform(up);

        float half = MUZZLE_FLASH_HALF_SIZE * MuzzleFlashState.sizeJitter();
        right.mul(half);
        up.mul(half);
        int alpha = (int) (255 * (1f - MuzzleFlashState.progress(gameTime, partialTick)));

        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityTranslucentEmissive(MUZZLE_FLASH_TEXTURE));
        addFlashVertex(consumer, pose, toCamera, alpha, right, up, -1f, -1f, 0f, 1f);
        addFlashVertex(consumer, pose, toCamera, alpha, right, up, 1f, -1f, 1f, 1f);
        addFlashVertex(consumer, pose, toCamera, alpha, right, up, 1f, 1f, 1f, 0f);
        addFlashVertex(consumer, pose, toCamera, alpha, right, up, -1f, 1f, 0f, 0f);

        poseStack.popPose();
    }

    private static void addFlashVertex(VertexConsumer consumer, PoseStack.Pose pose, Vector3f normal, int alpha,
                                        Vector3f right, Vector3f up, float rightSign, float upSign, float u, float v) {
        consumer.addVertex(pose,
                        right.x() * rightSign + up.x() * upSign,
                        right.y() * rightSign + up.y() * upSign,
                        right.z() * rightSign + up.z() * upSign)
                .setColor(255, 255, 255, alpha)
                .setUv(u, v)
                .setOverlay(OverlayTexture.NO_OVERLAY)
                .setLight(LightTexture.FULL_BRIGHT)
                .setNormal(pose, normal.x(), normal.y(), normal.z());
    }

    /**
     * 飛行中の薬莢を、同じボーンのキューブを使って生存インスタンスの数だけ重ねて描く。
     * 呼ばれる時点の{@link PoseStack}は親ボーンの空間なので、通常の描画と同じ手順
     * （ボーンオフセット→アニメーション差分）を各インスタンスのポーズで積めばよい。
     *
     * <p>薬莢ボーンの子ボーンは複製されない（現状の{@code ammo}は子を持たない）。
     * 子を持つ構成にするなら、ここも再帰させる必要がある。</p>
     */
    private static void renderEjectedShells(GunBone bone, PoseStack poseStack, VertexConsumer consumer,
                                             List<AnimationSampler.Pose> shellPoses, int light, int overlay) {
        for (AnimationSampler.Pose shell : shellPoses) {
            poseStack.pushPose();
            poseStack.translate(bone.localOffset.x(), bone.localOffset.y(), bone.localOffset.z());
            applyAnimationDelta(poseStack, shell);
            drawCubes(bone, poseStack.last(), consumer, light, overlay);
            poseStack.popPose();
        }
    }

    private static void drawCubes(GunBone bone, PoseStack.Pose pose, VertexConsumer consumer, int light, int overlay) {
        for (BakedCube cube : bone.cubes) {
            for (BakedCube.Quad quad : cube.quads()) {
                for (BakedCube.Vertex v : quad.vertices()) {
                    consumer.addVertex(pose, v.x(), v.y(), v.z())
                            .setColor(255, 255, 255, 255)
                            .setUv(v.u(), v.v())
                            .setOverlay(overlay)
                            .setLight(light)
                            .setNormal(pose, quad.normal().x(), quad.normal().y(), quad.normal().z());
                }
            }
        }
    }

    /** アニメーションのボーン差分を適用する。値は生のBedrock単位（geometryと同じ座標系）で保持されている。 */
    private static void applyAnimationDelta(PoseStack poseStack, AnimationSampler.Pose delta) {
        if (delta == null) {
            return;
        }
        Vector3f pos = delta.positionDelta();
        poseStack.translate(-pos.x() / 16f, pos.y() / 16f, pos.z() / 16f);

        Vector3f rot = delta.rotationDeltaDeg();
        poseStack.mulPose(Axis.ZP.rotationDegrees(rot.z()));
        poseStack.mulPose(Axis.YP.rotationDegrees(-rot.y()));
        poseStack.mulPose(Axis.XP.rotationDegrees(-rot.x()));

        Vector3f scale = delta.scaleFactor();
        if (scale.x() != 1f || scale.y() != 1f || scale.z() != 1f) {
            // ボーンpivotを原点にした状態でかけるので、Bedrock同様pivot中心の拡縮になる。
            poseStack.scale(safeScale(scale.x()), safeScale(scale.y()), safeScale(scale.z()));
        }
    }

    /**
     * スケール0を微小値に丸める。{@code mag_ammo} の弾を消すような 0 倍指定はそのまま渡すと
     * {@code PoseStack#scale} の法線行列計算（非一様時に {@code 1/x}）が発散するため。
     * 丸めた後も潰れたままなので見た目は不可視で変わらない。
     */
    private static float safeScale(float value) {
        return value == 0f ? 1e-4f : value;
    }
}
