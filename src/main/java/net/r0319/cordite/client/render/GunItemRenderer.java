package net.r0319.cordite.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
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

    // --- 配置の仮定数（🟡仮、実機で目視調整すること） ---
    // 一人称はまず変換なし（原点・無回転・等倍）から始める。ここに大きな値を入れて
    // 画面外に出てしまうと「何も映らない」ように見えるため、まず0基準で見えるかを確認し、
    // 見えた位置から少しずつ調整していく方針にする。
    private static final float MODEL_SCALE = 1.0f;
    private static final float FIRST_PERSON_X = 0f;
    private static final float FIRST_PERSON_Y = 0f;
    private static final float FIRST_PERSON_Z = 0f;
    private static final float FIRST_PERSON_YAW_DEG = 0f;
    private static final float FIRST_PERSON_PITCH_DEG = 0f;
    private static final float OTHER_CONTEXT_SCALE = 0.5f;
    private static final float GROUND_Y_LIFT = 0.2f;

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

        Map<String, AnimationSampler.Pose> poseMap = Map.of();
        BakedAnimation fireAnimation = GunModelCache.getFireAnimation(gunId);
        if (fireAnimation != null) {
            Minecraft mc = Minecraft.getInstance();
            long gameTime = mc.level != null ? mc.level.getGameTime() : 0L;
            float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);
            if (GunAnimationState.isPlaying(fireAnimation, gameTime, partialTick)) {
                float elapsed = GunAnimationState.elapsedSeconds(gameTime, partialTick);
                poseMap = AnimationSampler.sample(fireAnimation, elapsed);
            }
        }

        poseStack.pushPose();
        applyContextPlacement(poseStack, context);

        VertexConsumer consumer = bufferSource.getBuffer(RenderType.entityCutoutNoCull(model.texture()));
        renderBone(model.root(), poseStack, consumer, poseMap, packedLight, packedOverlay);

        poseStack.popPose();
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

    private static void applyContextPlacement(PoseStack poseStack, ItemDisplayContext context) {
        switch (context) {
            case FIRST_PERSON_RIGHT_HAND -> {
                poseStack.translate(FIRST_PERSON_X, FIRST_PERSON_Y, FIRST_PERSON_Z);
                poseStack.mulPose(Axis.YP.rotationDegrees(FIRST_PERSON_YAW_DEG));
                poseStack.mulPose(Axis.XP.rotationDegrees(FIRST_PERSON_PITCH_DEG));
                poseStack.scale(MODEL_SCALE, MODEL_SCALE, MODEL_SCALE);
            }
            case FIRST_PERSON_LEFT_HAND -> {
                poseStack.translate(-FIRST_PERSON_X, FIRST_PERSON_Y, FIRST_PERSON_Z);
                poseStack.mulPose(Axis.YP.rotationDegrees(180f - FIRST_PERSON_YAW_DEG));
                poseStack.mulPose(Axis.XP.rotationDegrees(FIRST_PERSON_PITCH_DEG));
                poseStack.scale(MODEL_SCALE, MODEL_SCALE, MODEL_SCALE);
            }
            case GROUND -> {
                // 地面ドロップ: モデル自体がpivot付近から下に伸びる形状のため、埋まらないよう底上げする
                // （ground ロケーター未実装のための暫定値。次フェーズで精密化）。
                poseStack.translate(0.0, GROUND_Y_LIFT, 0.0);
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
            }
            default -> {
                // 三人称/アイテムフレーム等: 仮の簡易配置（次フェーズでロケーターにより精密化）
                poseStack.translate(0.0, 0.0, 0.0);
                poseStack.scale(OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE, OTHER_CONTEXT_SCALE);
            }
        }
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
