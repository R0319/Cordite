package net.r0319.cordite.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.AnimationSampler;
import net.r0319.cordite.client.anim.BakedAnimation;
import net.r0319.cordite.client.anim.GunAnimationState;
import net.r0319.cordite.client.model.BakedCube;
import net.r0319.cordite.client.model.BakedGunModel;
import net.r0319.cordite.client.model.GunBone;
import net.r0319.cordite.client.model.GunModelCache;
import net.r0319.cordite.item.gun.GunItem;
import net.r0319.cordite.item.gun.GunProperties;
import org.joml.Vector3f;

import java.util.Map;

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

    /** 非ADS時の一人称カメラ基準ロケーター。 */
    private static final String LOCATOR_IDLE_VIEW = "idle_view";
    /** 地面ドロップ表示の基準ロケーター。 */
    private static final String LOCATOR_GROUND = "ground";
    /** ハンドアンカー（06-animations.md）で腕を追従させるボーン。 */
    private static final String BONE_RIGHT_HAND = "right_hand";
    private static final String BONE_LEFT_HAND = "left_hand";

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

    // --- GUIアイコン（glock_modelshot.png を流用した平面アイコン） ---
    private static final ResourceLocation ICON_TEXTURE =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "textures/gun/glock_icon.png");
    private static final float ICON_ASPECT = 624f / 408f; // 元画像の横:縦比
    private static final float ICON_SCALE = 1.0f; // 🟡仮、実機で調整

    @Override
    public void renderByItem(ItemStack stack, ItemDisplayContext context, PoseStack poseStack,
                              MultiBufferSource bufferSource, int packedLight, int packedOverlay) {
        if (context == ItemDisplayContext.GUI) {
            // インベントリ等のアイコンは3Dモデルではなく平面画像で表示する
            // （3Dモデルをそのまま縮小表示すると小さすぎて視認できないため、07-model-assets.mdの
            // 「アイテムアイコン」枠に沿って専用の平面画像を使う）。
            renderFlatIcon(poseStack, bufferSource, packedLight, packedOverlay);
            return;
        }

        String gunId = BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath();
        BakedGunModel model = GunModelCache.getGeometry(gunId);
        if (model == null) {
            return; // アセット未実装の銃（ak47/m4a1等）は何もしない
        }

        Map<String, AnimationSampler.Pose> poseMap = sampleCurrentPose(gunId, stack);

        poseStack.pushPose();
        applyContextPlacement(poseStack, context, model);

        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityCutoutNoCull(model.texture()));
        renderBone(model.root(), poseStack, consumer, poseMap, packedLight, packedOverlay);

        if (context.firstPerson()) {
            // ハンドアンカー方式の腕は viewmodel（一人称）のみ（06-animations.md）
            renderHandAnchoredArms(poseStack, model, poseMap, bufferSource, packedLight);
        }

        poseStack.popPose();
    }

    /**
     * 現在のボーンポーズを決定する。fire/reload/reload_empty のいずれかが再生中ならそれを、
     * 無ければ idle（無ければrestポーズ）を返す。
     *
     * <p>reload/reload_empty はアニメーションファイル自体の長さ（例 2.9583秒）と、
     * 実際のゲームプレイ上のリロード時間（{@link GunProperties#reloadSeconds()}、🟡仮のバランス値で
     * アニメーションと一致している保証はない）が一致しないため、実際のリロード時間に収まるように
     * 再生速度をスケーリングする（06-animations.mdの「モーション変更なし・時間のみ変わる」方針に合わせる）。
     * fireは反動の"キック"表現なので、次弾でアニメーションが再スタートしても違和感がなく、
     * スケーリングはしない。</p>
     */
    private static Map<String, AnimationSampler.Pose> sampleCurrentPose(String gunId, ItemStack stack) {
        Minecraft mc = Minecraft.getInstance();
        long gameTime = mc.level != null ? mc.level.getGameTime() : 0L;
        float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);

        GunAnimationState.Action action = GunAnimationState.currentAction();
        if (action != null) {
            BakedAnimation actionAnim = switch (action) {
                case FIRE -> GunModelCache.getFireAnimation(gunId);
                case RELOAD -> GunModelCache.getReloadAnimation(gunId);
                case RELOAD_EMPTY -> GunModelCache.getReloadEmptyAnimation(gunId);
            };

            float realDuration = actionAnim == null ? 0f : switch (action) {
                case FIRE -> actionAnim.lengthSeconds();
                case RELOAD, RELOAD_EMPTY -> reloadSecondsOf(stack);
            };

            if (actionAnim != null && realDuration > 0f) {
                GunAnimationState.clearIfFinished(realDuration, gameTime, partialTick);
                if (GunAnimationState.currentAction() == action) {
                    float elapsed = GunAnimationState.elapsedSeconds(gameTime, partialTick);
                    float playbackScale = actionAnim.lengthSeconds() / realDuration;
                    return AnimationSampler.sample(actionAnim, elapsed * playbackScale);
                }
            } else {
                GunAnimationState.clearIfFinished(0f, gameTime, partialTick);
            }
        }

        BakedAnimation idle = GunModelCache.getIdleAnimation(gunId);
        return idle != null ? AnimationSampler.sample(idle, 0f) : Map.of();
    }

    private static float reloadSecondsOf(ItemStack stack) {
        if (stack.getItem() instanceof GunItem gunItem) {
            GunProperties props = gunItem.getProps();
            if (props != null) {
                return props.reloadSeconds();
            }
        }
        return 0f;
    }

    private static void renderFlatIcon(PoseStack poseStack, MultiBufferSource bufferSource, int light, int overlay) {
        poseStack.pushPose();
        poseStack.translate(0.5, 0.5, 0.5);
        poseStack.scale(1f, -1f, 1f);

        float halfW = ICON_SCALE * ICON_ASPECT / 2f;
        float halfH = ICON_SCALE / 2f;
        PoseStack.Pose pose = poseStack.last();
        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityCutoutNoCull(ICON_TEXTURE));
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

    private static void applyContextPlacement(PoseStack poseStack, ItemDisplayContext context, BakedGunModel model) {
        // まず原点をアイテムの基準点（ローカル 0.5, 0.5, 0.5）へ移す。以降の座標はすべて
        // 「基準点からの相対位置」になる（{@link #ANCHOR} の説明を参照）。
        poseStack.translate(ANCHOR, ANCHOR, ANCHOR);

        switch (context) {
            // FIRST_PERSON_LEFT_HAND は左利き設定・オフハンド時に使われる。バニラの手変換は
            // GunClientExtensions で丸ごと止めており、どちらのコンテキストでも PoseStack は
            // カメラ基準のままなので、左右で配置を変える必要はない（左右反転はしない）。
            case FIRST_PERSON_RIGHT_HAND, FIRST_PERSON_LEFT_HAND -> {
                poseStack.translate(FIRST_PERSON_X, FIRST_PERSON_Y, FIRST_PERSON_Z);
                poseStack.mulPose(Axis.YP.rotationDegrees(FIRST_PERSON_YAW_DEG));
                poseStack.mulPose(Axis.XP.rotationDegrees(FIRST_PERSON_PITCH_DEG));
                poseStack.scale(MODEL_SCALE, MODEL_SCALE, MODEL_SCALE);
                alignLocatorToAnchor(poseStack, model, LOCATOR_IDLE_VIEW);
            }
            case GROUND -> {
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
                alignLocatorToAnchor(poseStack, model, LOCATOR_GROUND);
            }
            default -> {
                // 三人称/アイテムフレーム等: 対応するロケーター（thirdperson_hand / fixed）が
                // モデルに用意されたら同様に合わせる。現状はBedrock原点を規約位置に置くだけ。
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
                alignBedrockOriginToDefault(poseStack);
            }
        }
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
     * <p>既知の差異: {@code renderRightHand}/{@code renderLeftHand} は内部で
     * {@code HumanoidModel#setupAnim} を通すため、バニラ一人称の腕と同じ固定のZ軸傾き
     * （{@code AnimationUtils#bobArms} 由来、約±5.7度）が残る。バニラの手と同じ見え方に
     * なるようあえて打ち消していない。</p>
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

        if (rightArm) {
            playerRenderer.renderRightHand(poseStack, bufferSource, light, player);
        } else {
            playerRenderer.renderLeftHand(poseStack, bufferSource, light, player);
        }
        poseStack.popPose();
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
                                    Map<String, AnimationSampler.Pose> poseMap, int light, int overlay) {
        poseStack.pushPose();
        poseStack.translate(bone.localOffset.x(), bone.localOffset.y(), bone.localOffset.z());
        applyAnimationDelta(poseStack, poseMap.get(bone.name));

        PoseStack.Pose pose = poseStack.last();
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

        for (GunBone child : bone.children) {
            renderBone(child, poseStack, consumer, poseMap, light, overlay);
        }
        poseStack.popPose();
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
    }
}
