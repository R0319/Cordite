package net.r0319.cordite.client.model;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.logging.LogUtils;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.GsonHelper;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Blockbench "Bedrock Edition" {@code geometry.json} のパーサー兼ベイカー。
 *
 * <p>座標変換規則（GeckoLib実装で実証済みの規則をそのまま踏襲。docs/design/animation-system.md 参照）:</p>
 * <ul>
 *   <li>位置(pivot/origin): X座標のみ符号反転。1 Bedrock単位 = 1/16 ブロック。</li>
 *   <li>回転: X回転・Y回転のみ符号反転、Z回転はそのまま。度→ラジアン変換。</li>
 *   <li>回転の適用順序: X→Y→Z（PoseStackへは mulPose を Z→Y→X の順で積む）。</li>
 *   <li>回転は必ず「先に位置をJava座標系へ変換してから」適用する（生のBedrock座標のまま
 *       回転してからミラーする方式は符号規則がズレるため使わない。{@link #toVertex} 参照）。</li>
 * </ul>
 *
 * <p>ロード時に1回だけ全キューブの頂点をボーンpivot相対のJava座標系へベイクし、
 * 毎フレームはボーン変換行列の計算のみで済むようにする（パフォーマンス方針、
 * docs/specs/06-animations.md 参照）。</p>
 */
public final class BedrockGeometryLoader {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String SUPPORTED_FORMAT_VERSION = "1.21.0";

    private BedrockGeometryLoader() {}

    public static BakedGunModel load(ResourceLocation id, ResourceLocation texture, JsonObject root) {
        String formatVersion = GsonHelper.getAsString(root, "format_version", "");
        if (!SUPPORTED_FORMAT_VERSION.equals(formatVersion)) {
            LOGGER.warn("[Cordite] {}: 未対応の format_version '{}'（対応: {}）。読み込みを続行しますが表示が崩れる可能性があります。",
                    id, formatVersion, SUPPORTED_FORMAT_VERSION);
        }

        JsonArray geometries = GsonHelper.getAsJsonArray(root, "minecraft:geometry");
        if (geometries.isEmpty()) {
            throw new IllegalStateException(id + ": minecraft:geometry が空です");
        }
        JsonObject geometry = geometries.get(0).getAsJsonObject();

        JsonObject description = GsonHelper.getAsJsonObject(geometry, "description", new JsonObject());
        float textureWidth = GsonHelper.getAsFloat(description, "texture_width", 16f);
        float textureHeight = GsonHelper.getAsFloat(description, "texture_height", 16f);

        JsonArray bonesJson = GsonHelper.getAsJsonArray(geometry, "bones", new JsonArray());

        Map<String, JsonObject> byName = new LinkedHashMap<>();
        for (JsonElement e : bonesJson) {
            JsonObject b = e.getAsJsonObject();
            byName.put(GsonHelper.getAsString(b, "name"), b);
        }

        Map<String, List<String>> childrenOf = new HashMap<>();
        List<String> topLevel = new ArrayList<>();
        for (JsonObject b : byName.values()) {
            String name = GsonHelper.getAsString(b, "name");
            String parent = GsonHelper.getAsString(b, "parent", null);
            if (parent != null && byName.containsKey(parent)) {
                childrenOf.computeIfAbsent(parent, k -> new ArrayList<>()).add(name);
            } else {
                topLevel.add(name);
            }
        }

        Map<String, GunBone> baked = new HashMap<>();
        List<GunBone> roots = new ArrayList<>();
        Vector3f modelOrigin = new Vector3f(0, 0, 0);
        for (String name : topLevel) {
            roots.add(bakeBone(name, modelOrigin, byName, childrenOf, textureWidth, textureHeight, baked));
        }

        // 「root」ボーンが存在する場合は、それだけを実際の描画ツリーとして採用する
        // （07-model-assets.mdの規約: root=モデル全体の基準）。bb_main（Blockbenchの既定グループ）や
        // arm（手・腕の位置合わせ用にBlockbench上へ置いた参考オブジェクトと思われる、cordite的な
        // right_hand/left_handボーンではない独自命名）等、root配下に無いトップレベルボーンは
        // 造形上の参考物であり実際のモデル描画には含めない。
        GunBone actualRoot = baked.get("root");
        if (actualRoot == null) {
            LOGGER.warn("[Cordite] {}: 'root'ボーンが見つからないため、全トップレベルボーンをまとめて描画します", id);
            actualRoot = new GunBone("__model_root__", new Vector3f(0, 0, 0), List.of(), roots);
        } else if (roots.size() > 1) {
            LOGGER.info("[Cordite] {}: 'root'以外のトップレベルボーン{}個は描画対象から除外しました（参考オブジェクトとみなす）",
                    id, roots.size() - 1);
        }
        return new BakedGunModel(actualRoot, baked, texture);
    }

    private static GunBone bakeBone(String name, Vector3f parentPivotRaw, Map<String, JsonObject> byName,
                                     Map<String, List<String>> childrenOf, float tw, float th,
                                     Map<String, GunBone> outBaked) {
        JsonObject boneJson = byName.get(name);
        Vector3f pivotRaw = readVec3(boneJson, "pivot", 0, 0, 0);

        List<BakedCube> cubes = new ArrayList<>();
        if (boneJson.has("cubes")) {
            for (JsonElement ce : boneJson.getAsJsonArray("cubes")) {
                BakedCube baked = bakeCube(ce.getAsJsonObject(), pivotRaw, tw, th);
                if (baked != null) {
                    cubes.add(baked);
                }
            }
        }

        List<GunBone> children = new ArrayList<>();
        for (String childName : childrenOf.getOrDefault(name, List.of())) {
            children.add(bakeBone(childName, pivotRaw, byName, childrenOf, tw, th, outBaked));
        }

        Vector3f localOffset = mirrorAndScale(
                pivotRaw.x() - parentPivotRaw.x(),
                pivotRaw.y() - parentPivotRaw.y(),
                pivotRaw.z() - parentPivotRaw.z());

        GunBone bone = new GunBone(name, localOffset, cubes, children);
        outBaked.put(name, bone);
        return bone;
    }

    private static BakedCube bakeCube(JsonObject cubeJson, Vector3f bonePivotRaw, float tw, float th) {
        JsonElement uvElement = cubeJson.get("uv");
        if (uvElement == null || !uvElement.isJsonObject()) {
            // Box UV(配列形式)は現状未対応。docs/design/animation-system.md でper-face UVに統一する方針。
            LOGGER.warn("[Cordite] Box UV形式のキューブをスキップしました（per-face UVのみ対応）");
            return null;
        }
        JsonObject uv = uvElement.getAsJsonObject();

        Vector3f origin = readVec3(cubeJson, "origin", 0, 0, 0);
        Vector3f size = readVec3(cubeJson, "size", 0, 0, 0);
        Vector3f max = new Vector3f(origin).add(size);

        Vector3f cubePivot = cubeJson.has("pivot")
                ? readVec3(cubeJson, "pivot", 0, 0, 0)
                : new Vector3f(origin).add(size.x() / 2f, size.y() / 2f, size.z() / 2f);
        Vector3f cubeRotation = readVec3(cubeJson, "rotation", 0, 0, 0);
        boolean hasRotation = cubeRotation.lengthSquared() > 1.0e-8f;
        // 回転はボーン/アニメーションと同じ規則（X・Y符号反転、Z反転なし）で、
        // 先にJava座標系へ変換した点に対して適用する（クラス冒頭のコメント参照）。
        Quaternionf rotQ = hasRotation
                ? new Quaternionf()
                        .rotateZ((float) Math.toRadians(cubeRotation.z()))
                        .rotateY((float) Math.toRadians(-cubeRotation.y()))
                        .rotateX((float) Math.toRadians(-cubeRotation.x()))
                : null;
        Vector3f cubePivotJava = mirrorAndScale(
                cubePivot.x() - bonePivotRaw.x(), cubePivot.y() - bonePivotRaw.y(), cubePivot.z() - bonePivotRaw.z());

        List<BakedCube.Quad> quads = new ArrayList<>();
        addFace(quads, uv, "north", tw, th, bonePivotRaw, cubePivotJava, rotQ,
                corner(origin, max, 1, 0, 0), corner(origin, max, 0, 0, 0),
                corner(origin, max, 0, 1, 0), corner(origin, max, 1, 1, 0),
                0, 0, -1);
        addFace(quads, uv, "south", tw, th, bonePivotRaw, cubePivotJava, rotQ,
                corner(origin, max, 0, 0, 1), corner(origin, max, 1, 0, 1),
                corner(origin, max, 1, 1, 1), corner(origin, max, 0, 1, 1),
                0, 0, 1);
        addFace(quads, uv, "west", tw, th, bonePivotRaw, cubePivotJava, rotQ,
                corner(origin, max, 0, 0, 1), corner(origin, max, 0, 0, 0),
                corner(origin, max, 0, 1, 0), corner(origin, max, 0, 1, 1),
                -1, 0, 0);
        addFace(quads, uv, "east", tw, th, bonePivotRaw, cubePivotJava, rotQ,
                corner(origin, max, 1, 0, 0), corner(origin, max, 1, 0, 1),
                corner(origin, max, 1, 1, 1), corner(origin, max, 1, 1, 0),
                1, 0, 0);
        addFace(quads, uv, "up", tw, th, bonePivotRaw, cubePivotJava, rotQ,
                corner(origin, max, 0, 1, 1), corner(origin, max, 1, 1, 1),
                corner(origin, max, 1, 1, 0), corner(origin, max, 0, 1, 0),
                0, 1, 0);
        addFace(quads, uv, "down", tw, th, bonePivotRaw, cubePivotJava, rotQ,
                corner(origin, max, 0, 0, 0), corner(origin, max, 1, 0, 0),
                corner(origin, max, 1, 0, 1), corner(origin, max, 0, 0, 1),
                0, -1, 0);

        if (quads.isEmpty()) {
            return null;
        }
        return new BakedCube(quads);
    }

    private static void addFace(List<BakedCube.Quad> quads, JsonObject uvRoot, String faceKey, float tw, float th,
                                 Vector3f bonePivotRaw, Vector3f cubePivotJava, Quaternionf rotQ,
                                 Vector3f c0, Vector3f c1, Vector3f c2, Vector3f c3,
                                 float nx, float ny, float nz) {
        if (!uvRoot.has(faceKey)) {
            return;
        }
        JsonObject face = uvRoot.getAsJsonObject(faceKey);
        float[] uvPos = readVec2(face, "uv", 0, 0);
        float[] uvSize = readVec2(face, "uv_size", 0, 0);
        float u0 = uvPos[0] / tw;
        float v0 = uvPos[1] / th;
        float u1 = (uvPos[0] + uvSize[0]) / tw;
        float v1 = (uvPos[1] + uvSize[1]) / th;

        // 法線もまずミラー（位置と同じX符号反転）してから、必要なら回転を適用する。
        Vector3f normal = new Vector3f(-nx, ny, nz);
        if (rotQ != null) {
            rotQ.transform(normal);
        }

        BakedCube.Vertex vtx0 = toVertex(c0, cubePivotJava, rotQ, bonePivotRaw, u0, v0);
        BakedCube.Vertex vtx1 = toVertex(c1, cubePivotJava, rotQ, bonePivotRaw, u1, v0);
        BakedCube.Vertex vtx2 = toVertex(c2, cubePivotJava, rotQ, bonePivotRaw, u1, v1);
        BakedCube.Vertex vtx3 = toVertex(c3, cubePivotJava, rotQ, bonePivotRaw, u0, v1);
        quads.add(new BakedCube.Quad(normal, vtx0, vtx1, vtx2, vtx3));
    }

    /**
     * 頂点を先にJava座標系（ボーンpivot相対、X符号反転＋1/16スケール）へ変換してから、
     * キューブの静的回転（あれば）を cubePivotJava を中心に適用する。回転をJava座標系側で
     * 行うことで、ボーン/アニメーションの回転（X・Y符号反転、Z反転なし）と同じ規則を
     * 一貫して使える（先に生のBedrock座標で回転してからミラーする方式は符号規則が
     * ズレるため採用しない）。
     */
    private static BakedCube.Vertex toVertex(Vector3f cornerRaw, Vector3f cubePivotJava, Quaternionf rotQ,
                                              Vector3f bonePivotRaw, float u, float v) {
        Vector3f local = mirrorAndScale(
                cornerRaw.x() - bonePivotRaw.x(), cornerRaw.y() - bonePivotRaw.y(), cornerRaw.z() - bonePivotRaw.z());
        if (rotQ != null) {
            local.sub(cubePivotJava);
            rotQ.transform(local);
            local.add(cubePivotJava);
        }
        return new BakedCube.Vertex(local.x(), local.y(), local.z(), u, v);
    }

    private static Vector3f corner(Vector3f min, Vector3f max, int xSel, int ySel, int zSel) {
        return new Vector3f(
                xSel == 0 ? min.x() : max.x(),
                ySel == 0 ? min.y() : max.y(),
                zSel == 0 ? min.z() : max.z());
    }

    private static Vector3f mirrorAndScale(float x, float y, float z) {
        return new Vector3f(-x / 16f, y / 16f, z / 16f);
    }

    private static Vector3f readVec3(JsonObject obj, String key, float dx, float dy, float dz) {
        if (obj == null || !obj.has(key)) {
            return new Vector3f(dx, dy, dz);
        }
        JsonArray arr = obj.getAsJsonArray(key);
        return new Vector3f(arr.get(0).getAsFloat(), arr.get(1).getAsFloat(), arr.get(2).getAsFloat());
    }

    private static float[] readVec2(JsonObject obj, String key, float dx, float dy) {
        if (obj == null || !obj.has(key)) {
            return new float[] {dx, dy};
        }
        JsonArray arr = obj.getAsJsonArray(key);
        return new float[] {arr.get(0).getAsFloat(), arr.get(1).getAsFloat()};
    }
}
