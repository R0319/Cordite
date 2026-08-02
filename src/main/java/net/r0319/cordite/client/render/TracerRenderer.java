package net.r0319.cordite.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.RenderLevelStageEvent;
import net.r0319.cordite.Cordite;
import org.joml.Vector3f;

import java.util.List;

/**
 * 曳光弾の描画。{@link TracerState} が持つ飛行中の弾を、進行方向へ伸ばした<b>発光する板</b>として
 * 毎フレーム描く（弾丸の3Dモデルは使わない。長さを弾速に合わせて伸ばしたいので、板をコード側で
 * 生成するほうが素直なため）。
 *
 * <p>板は常にカメラを向く（進行方向を軸にした帯）。銃本体と違ってワールドの明るさで暗くならないよう、
 * マズルフラッシュと同じ<b>フルブライト＋半透明の発光</b>で描く。</p>
 *
 * <p>テクスチャ {@code textures/effect/tracer.png} は任意。用意されていなければバニラの白テクスチャに
 * {@link #TRACER_COLOR} を掛けた単色の帯で描くので、アセット未作成でもミッシングテクスチャにならない。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class TracerRenderer {
    private TracerRenderer() {}

    /** 曳光弾の見た目の長さ[ブロック]。🟡仮（実機で見ながら調整する値）。 */
    private static final float TRACER_LENGTH = 2.0f;
    /** 曳光弾の太さ[ブロック]。🟡仮。 */
    private static final float TRACER_WIDTH = 0.06f;
    /**
     * 先端に描く発光点の一辺[ブロック]。🟡仮。
     *
     * <p>帯（進行方向に伸ばした板）だけでは<b>自分が撃った弾が見えない</b>。自分の弾は視線の正面へ
     * 飛んでいくため、画面上では進行方向の長さがほぼゼロに潰れてしまう（真後ろから見る帯）。
     * 常にカメラを向く点を先端に描くことで、飛んでいく弾が正面からでも見えるようにする。</p>
     */
    private static final float TRACER_HEAD_SIZE = 0.12f;
    /** 曳光弾の色（オレンジ）。テクスチャがある場合はそれに乗算される。 */
    private static final float[] TRACER_COLOR = {1.0f, 0.55f, 0.15f};
    /**
     * カメラからこの距離[ブロック]より内側には曳光弾を描かない。🟡仮（実機で見ながら調整する値）。
     *
     * <p>自分で撃った弾は<b>目の位置から出る</b>ため、これが無いと発射の瞬間に画面いっぱいの帯が映り、
     * 「頭から弾が出ている」ように見える。帯は手前側を切り詰めて描くので、この距離ちょうどから
     * 生えてくるように見え、途中から唐突に現れることはない。</p>
     */
    private static final double MIN_CAMERA_DISTANCE = 5.0;

    private static final ResourceLocation TRACER_TEXTURE =
            ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "textures/effect/tracer.png");
    /** テクスチャ未作成時のフォールバック（バニラの白1枚）。 */
    private static final ResourceLocation WHITE_TEXTURE =
            ResourceLocation.withDefaultNamespace("textures/misc/white.png");

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) {
            TracerState.reset();
            return;
        }
        TracerState.prune(mc.level.getGameTime());
    }

    @SubscribeEvent
    public static void onRenderLevelStage(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) {
            return;
        }
        List<TracerState.Tracer> tracers = TracerState.active();
        if (tracers.isEmpty()) {
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) {
            return;
        }

        long gameTime = mc.level.getGameTime();
        float partialTick = mc.getTimer().getGameTimeDeltaPartialTick(false);
        Vec3 camera = event.getCamera().getPosition();
        RenderType renderType = RenderType.entityTranslucentEmissive(resolveTexture(mc));

        PoseStack poseStack = event.getPoseStack();
        poseStack.pushPose();
        // ワールド座標をカメラ相対へ（レベル描画のPoseStackはカメラ位置が原点）
        poseStack.translate(-camera.x, -camera.y, -camera.z);

        MultiBufferSource.BufferSource buffers = mc.renderBuffers().bufferSource();
        VertexConsumer consumer = buffers.getBuffer(renderType);
        for (TracerState.Tracer tracer : tracers) {
            drawTracer(consumer, poseStack.last(), tracer, camera, gameTime, partialTick);
        }
        buffers.endBatch(renderType);

        poseStack.popPose();
    }

    private static void drawTracer(VertexConsumer consumer, PoseStack.Pose pose, TracerState.Tracer tracer,
                                    Vec3 camera, long gameTime, float partialTick) {
        double head = Math.min(tracer.traveled(gameTime, partialTick), tracer.stopDistance());
        if (head <= 0) {
            return;
        }
        double tail = Math.max(0, head - TRACER_LENGTH);
        Vec3 headPos = tracer.origin().add(tracer.direction().scale(head));
        Vec3 tailPos = tracer.origin().add(tracer.direction().scale(tail));

        double minDistSq = MIN_CAMERA_DISTANCE * MIN_CAMERA_DISTANCE;
        if (headPos.distanceToSqr(camera) < minDistSq) {
            return; // 帯全体がカメラの手前側にある
        }
        // 尾だけがカメラの近くにある場合は、手前側を切り詰める（丸ごと消すと、先端が最小距離に達した
        // 瞬間に2ブロックぶんの帯がまとめて現れてしまう）。UVも切った位置に合わせてずらす。
        float tailV = 1f;
        if (tailPos.distanceToSqr(camera) < minDistSq) {
            double t = exitFraction(tailPos, headPos, camera, MIN_CAMERA_DISTANCE);
            tailPos = tailPos.add(headPos.subtract(tailPos).scale(t));
            tailV = (float) (1.0 - t);
        }

        Vec3 toCamera = camera.subtract(headPos.add(tailPos).scale(0.5));
        if (toCamera.lengthSqr() < 1.0e-8) {
            return;
        }
        Vec3 forward = toCamera.normalize();

        // 帯の横方向 = 進行方向 × カメラへの方向（＝進行方向を軸にカメラを向く）。
        // 自分が撃った弾は視線の正面へ飛ぶので、この2つが平行になり外積がほぼ0になる
        // （＝帯が画面上で潰れる）。その場合は任意の直交軸で代用し、先端の発光点で見せる。
        Vec3 side = tracer.direction().cross(forward);
        if (side.lengthSqr() < 1.0e-6) {
            side = anyPerpendicular(forward);
        }
        side = side.normalize();

        Vector3f normal = new Vector3f((float) forward.x, (float) forward.y, (float) forward.z);
        Vec3 halfWidth = side.scale(TRACER_WIDTH / 2.0);
        addVertex(consumer, pose, normal, tailPos.subtract(halfWidth), 0f, tailV);
        addVertex(consumer, pose, normal, headPos.subtract(halfWidth), 0f, 0f);
        addVertex(consumer, pose, normal, headPos.add(halfWidth), 1f, 0f);
        addVertex(consumer, pose, normal, tailPos.add(halfWidth), 1f, tailV);

        drawHead(consumer, pose, normal, headPos, forward, side);
    }

    /**
     * 線分 {@code from→to} が、{@code center}を中心とする半径{@code radius}の球から出る位置を
     * 線分上の割合[0,1]で返す。{@code from}が球の内側・{@code to}が外側にある前提。
     */
    private static double exitFraction(Vec3 from, Vec3 to, Vec3 center, double radius) {
        Vec3 d = to.subtract(from);
        Vec3 f = from.subtract(center);
        double a = d.lengthSqr();
        if (a < 1.0e-12) {
            return 0.0;
        }
        double b = 2.0 * f.dot(d);
        double c = f.lengthSqr() - radius * radius;
        double discriminant = b * b - 4.0 * a * c;
        if (discriminant <= 0.0) {
            return 0.0;
        }
        return Math.clamp((-b + Math.sqrt(discriminant)) / (2.0 * a), 0.0, 1.0);
    }

    /** 先端の発光点（常にカメラを向く正方形）。真正面／真後ろから見ても弾が見えるようにするためのもの。 */
    private static void drawHead(VertexConsumer consumer, PoseStack.Pose pose, Vector3f normal, Vec3 headPos,
                                  Vec3 forward, Vec3 side) {
        Vec3 right = side.scale(TRACER_HEAD_SIZE / 2.0);
        Vec3 up = forward.cross(side).normalize().scale(TRACER_HEAD_SIZE / 2.0);
        addVertex(consumer, pose, normal, headPos.subtract(right).subtract(up), 0f, 1f);
        addVertex(consumer, pose, normal, headPos.add(right).subtract(up), 1f, 1f);
        addVertex(consumer, pose, normal, headPos.add(right).add(up), 1f, 0f);
        addVertex(consumer, pose, normal, headPos.subtract(right).add(up), 0f, 0f);
    }

    /** 指定ベクトルに直交する任意の単位ベクトル。 */
    private static Vec3 anyPerpendicular(Vec3 v) {
        Vec3 reference = Math.abs(v.y) > 0.99 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
        return v.cross(reference).normalize();
    }

    private static void addVertex(VertexConsumer consumer, PoseStack.Pose pose, Vector3f normal, Vec3 position,
                                   float u, float v) {
        consumer.addVertex(pose, (float) position.x, (float) position.y, (float) position.z)
                .setColor(TRACER_COLOR[0], TRACER_COLOR[1], TRACER_COLOR[2], 1.0f)
                .setUv(u, v)
                .setOverlay(OverlayTexture.NO_OVERLAY)
                .setLight(LightTexture.FULL_BRIGHT)
                .setNormal(pose, normal.x(), normal.y(), normal.z());
    }

    /** 専用テクスチャがあればそれを、無ければ白テクスチャを使う。 */
    private static ResourceLocation resolveTexture(Minecraft mc) {
        return mc.getResourceManager().getResource(TRACER_TEXTURE).isPresent() ? TRACER_TEXTURE : WHITE_TEXTURE;
    }
}
