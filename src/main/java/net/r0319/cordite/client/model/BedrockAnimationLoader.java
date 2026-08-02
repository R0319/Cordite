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
import net.r0319.cordite.client.anim.SoundKeyframe;
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
                Keyframe[] scale = readTrack(boneJson, "scale", id, boneName);
                bones.put(boneName, new BoneTrack(position, rotation, scale));
            }
        }

        return new BakedAnimation(length, bones, readSoundEffects(anim, id, animationKey));
    }

    /**
     * {@code sound_effects} を読む。Blockbenchのエクスポート形式は
     * {@code {"<秒>": {"effect": "<名前>"}}}（同時刻に複数ある場合は配列）。
     *
     * <p><b>注意</b>: Blockbenchはサウンドキーフレームの<b>「Effect」欄が空だと書き出さない</b>。
     * Effect欄は音声ファイルを載せるとファイル名から自動補完されるが、空のまま書き出すと
     * {@code "sound_effects": {}} になり、ここでは何も読めない（＝ゲーム内で鳴らない）。
     * {@link net.r0319.cordite.registry.ModSounds} の登録名は音声ファイル名と揃えてあるので、
     * 自動補完された名前がそのまま通る。</p>
     */
    private static List<SoundKeyframe> readSoundEffects(JsonObject anim, ResourceLocation id, String animationKey) {
        if (!anim.has("sound_effects") || !anim.get("sound_effects").isJsonObject()) {
            return List.of();
        }
        JsonObject soundsJson = anim.getAsJsonObject("sound_effects");
        List<SoundKeyframe> keyframes = new ArrayList<>();
        for (String timeKey : soundsJson.keySet()) {
            float time;
            try {
                time = Float.parseFloat(timeKey);
            } catch (NumberFormatException e) {
                LOGGER.warn("[Cordite] {}: '{}' の sound_effects に数値でない時刻キー'{}'があります", id, animationKey, timeKey);
                continue;
            }
            JsonElement entry = soundsJson.get(timeKey);
            if (entry.isJsonArray()) {
                for (JsonElement each : entry.getAsJsonArray()) {
                    addSoundKeyframe(keyframes, time, each, id, animationKey);
                }
            } else {
                addSoundKeyframe(keyframes, time, entry, id, animationKey);
            }
        }
        if (keyframes.isEmpty()) {
            // Blockbenchで音声ファイルを載せただけ（Effect欄が空）だとこの形になり、音が一切鳴らない。
            // 気付きにくい割に原因が分かりにくいので、読み込み時にはっきり警告しておく。
            LOGGER.warn("[Cordite] {}: '{}' の sound_effects が空です。Blockbenchでサウンドキーフレームを選択し、"
                    + "「Effect」欄にサウンドID（例 smg_magazine_eject＝音声ファイル名と同じ）が入っているか"
                    + "確認してから書き出してください（空欄のキーフレームは書き出されません）", id, animationKey);
        }
        keyframes.sort((a, b) -> Float.compare(a.time(), b.time()));
        return List.copyOf(keyframes);
    }

    private static void addSoundKeyframe(List<SoundKeyframe> out, float time, JsonElement entry,
                                          ResourceLocation id, String animationKey) {
        String effect = null;
        if (entry.isJsonObject()) {
            effect = GsonHelper.getAsString(entry.getAsJsonObject(), "effect", null);
        } else if (entry.isJsonPrimitive()) {
            effect = entry.getAsString(); // {"0.5": "name"} 形式も受け付ける
        }
        if (effect == null || effect.isBlank()) {
            LOGGER.warn("[Cordite] {}: '{}' の {}秒のサウンドキーフレームにeffect名がありません（Blockbenchで入力してください）",
                    id, animationKey, time);
            return;
        }
        out.add(new SoundKeyframe(time, effect));
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
            float time;
            try {
                time = Float.parseFloat(timeKey);
            } catch (NumberFormatException e) {
                continue;
            }
            Keyframe keyframe = readKeyframe(track.get(timeKey), time, id, boneName, key, timeKey);
            if (keyframe != null) {
                keyframes.add(keyframe);
            }
        }
        keyframes.sort((a, b) -> Float.compare(a.time(), b.time()));
        return keyframes.toArray(new Keyframe[0]);
    }

    /**
     * 1キーフレームを読む。値の書かれ方は2通り:
     * <ul>
     *   <li>数値配列 {@code [x,y,z]} — 通常のキーフレーム</li>
     *   <li>オブジェクト {@code {"pre": [...], "post": [...], "lerp_mode": "..."}} — Blockbenchで
     *       キーフレームに個別の入り値/出値を設定した場合や、補間モードを変えた場合の形式。
     *       {@code pre}/{@code post} は片方だけのこともあるので、欠けている側はもう片方で埋める。</li>
     * </ul>
     *
     * <p>{@code lerp_mode}（{@code catmullrom} 等）は読み飛ばして<b>常に線形補間</b>で扱う
     * （docs/specs/06-animations.md のパフォーマンス方針）。キーフレームの値自体は正しく通るので、
     * モーションが途中で止まることはなく、曲線の滑らかさだけが直線寄りになる。</p>
     */
    private static Keyframe readKeyframe(JsonElement valueElement, float time, ResourceLocation id,
                                          String boneName, String key, String timeKey) {
        if (valueElement.isJsonArray()) {
            return new Keyframe(time, readVector(valueElement.getAsJsonArray()));
        }
        if (valueElement.isJsonObject()) {
            JsonObject obj = valueElement.getAsJsonObject();
            Vector3f pre = obj.has("pre") && obj.get("pre").isJsonArray()
                    ? readVector(obj.getAsJsonArray("pre")) : null;
            Vector3f post = obj.has("post") && obj.get("post").isJsonArray()
                    ? readVector(obj.getAsJsonArray("post")) : null;
            if (pre == null && post == null) {
                LOGGER.warn("[Cordite] {}: ボーン'{}'の{}キーフレーム({})にpre/postの数値配列がないため無視しました（Molang式は未対応）",
                        id, boneName, key, timeKey);
                return null;
            }
            return new Keyframe(time, pre != null ? pre : post, post != null ? post : pre);
        }
        LOGGER.warn("[Cordite] {}: ボーン'{}'の{}キーフレーム({})は未対応の形式のため無視しました（Molang式は未対応）",
                id, boneName, key, timeKey);
        return null;
    }

    private static Vector3f readVector(JsonArray arr) {
        return new Vector3f(arr.get(0).getAsFloat(), arr.get(1).getAsFloat(), arr.get(2).getAsFloat());
    }
}
