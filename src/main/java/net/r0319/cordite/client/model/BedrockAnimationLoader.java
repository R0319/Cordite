package net.r0319.cordite.client.model;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.logging.LogUtils;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.GsonHelper;
import net.r0319.cordite.client.anim.BakedAnimation;
import net.r0319.cordite.client.anim.BoneTrack;
import net.r0319.cordite.client.anim.Keyframe;
import org.joml.Vector3f;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Blockbench "Bedrock Edition" {@code animation.json} のパーサー。
 * キーフレーム値は数値配列のみサポートする（Molang式・pre/postイージングは非対応、
 * docs/specs/06-animations.md の方針どおり。該当する場合は警告を出してそのキーフレームを無視する）。
 */
public final class BedrockAnimationLoader {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String SUPPORTED_FORMAT_VERSION = "1.8.0";

    private BedrockAnimationLoader() {}

    public static BakedAnimation load(ResourceLocation id, JsonObject root, String animationKey) {
        String formatVersion = GsonHelper.getAsString(root, "format_version", "");
        if (!SUPPORTED_FORMAT_VERSION.equals(formatVersion)) {
            LOGGER.warn("[Cordite] {}: 未対応の format_version '{}'（対応: {}）", id, formatVersion, SUPPORTED_FORMAT_VERSION);
        }

        JsonObject animations = GsonHelper.getAsJsonObject(root, "animations");
        if (!animations.has(animationKey)) {
            throw new IllegalStateException(id + ": アニメーション '" + animationKey + "' が見つかりません");
        }
        JsonObject anim = animations.getAsJsonObject(animationKey);
        float length = GsonHelper.getAsFloat(anim, "animation_length", 0f);

        Map<String, BoneTrack> bones = new HashMap<>();
        if (anim.has("bones")) {
            JsonObject bonesJson = anim.getAsJsonObject("bones");
            for (String boneName : bonesJson.keySet()) {
                JsonObject boneJson = bonesJson.getAsJsonObject(boneName);
                Keyframe[] position = readTrack(boneJson, "position", id, boneName);
                Keyframe[] rotation = readTrack(boneJson, "rotation", id, boneName);
                bones.put(boneName, new BoneTrack(position, rotation));
            }
        }

        return new BakedAnimation(length, bones);
    }

    private static Keyframe[] readTrack(JsonObject boneJson, String key, ResourceLocation id, String boneName) {
        if (!boneJson.has(key)) {
            return new Keyframe[0];
        }
        JsonElement element = boneJson.get(key);
        if (element.isJsonArray()) {
            // キーフレームではなく数値配列が直接書かれている場合は「アニメーション全体で一定のポーズ」
            // （idleの静止ポーズ等）を意味する。時刻0の単一キーフレームとして扱えば、
            // AnimationSamplerはどの時刻でもこの値を返す（frames.length==1の分岐）。
            JsonArray staticArr = element.getAsJsonArray();
            Vector3f staticValue = new Vector3f(
                    staticArr.get(0).getAsFloat(), staticArr.get(1).getAsFloat(), staticArr.get(2).getAsFloat());
            return new Keyframe[] {new Keyframe(0f, staticValue)};
        }
        JsonObject track = element.getAsJsonObject();
        List<Keyframe> keyframes = new ArrayList<>();
        for (String timeKey : track.keySet()) {
            JsonElement valueElement = track.get(timeKey);
            if (!valueElement.isJsonArray()) {
                LOGGER.warn("[Cordite] {}: ボーン'{}'の{}キーフレーム({})は数値配列以外のため無視しました（Molang式/イージングは未対応）",
                        id, boneName, key, timeKey);
                continue;
            }
            JsonArray arr = valueElement.getAsJsonArray();
            float time;
            try {
                time = Float.parseFloat(timeKey);
            } catch (NumberFormatException e) {
                continue;
            }
            Vector3f value = new Vector3f(arr.get(0).getAsFloat(), arr.get(1).getAsFloat(), arr.get(2).getAsFloat());
            keyframes.add(new Keyframe(time, value));
        }
        keyframes.sort((a, b) -> Float.compare(a.time(), b.time()));
        return keyframes.toArray(new Keyframe[0]);
    }
}
