package net.r0319.cordite.client.model;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.mojang.logging.LogUtils;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.SimplePreparableReloadListener;
import net.minecraft.util.profiling.ProfilerFiller;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterClientReloadListenersEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.BakedAnimation;
import org.slf4j.Logger;

import java.io.BufferedReader;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 銃のBedrockモデル・各種アニメーション（idle/fire/reload/reload_empty）をリソースリロード時に
 * ロード・ベイクしてキャッシュする。該当アセットが用意されていない銃/アニメーション種別
 * （未実装のak47/m4a1、未作成のinspect等）は null を返す（nullセーフ。呼び出し側の
 * {@link net.r0319.cordite.client.render.GunItemRenderer} は描画・再生をスキップする）。
 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class GunModelCache {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Gson GSON = new Gson();

    /** アセットが用意されている銃ID一覧（プロトタイプ時点ではglockのみ）。 */
    private static final List<String> GUN_IDS = List.of("glock");

    /** 銃ID→animation.json内の各アニメーションキー。用意されていない銃/種別は単純に登録しない。 */
    private static final Map<String, String> IDLE_ANIMATION_KEYS = Map.of("glock", "animation.glock.idle");
    private static final Map<String, String> FIRE_ANIMATION_KEYS = Map.of("glock", "animation.glock.fire");
    private static final Map<String, String> RELOAD_ANIMATION_KEYS = Map.of("glock", "animation.glock.reload");
    private static final Map<String, String> RELOAD_EMPTY_ANIMATION_KEYS = Map.of("glock", "animation.glock.reload_empty");

    private static volatile Map<String, BakedGunModel> models = Map.of();
    private static volatile Map<String, BakedAnimation> idleAnimations = Map.of();
    private static volatile Map<String, BakedAnimation> fireAnimations = Map.of();
    private static volatile Map<String, BakedAnimation> reloadAnimations = Map.of();
    private static volatile Map<String, BakedAnimation> reloadEmptyAnimations = Map.of();

    private GunModelCache() {}

    public static BakedGunModel getGeometry(String gunId) {
        return models.get(gunId);
    }

    public static BakedAnimation getIdleAnimation(String gunId) {
        return idleAnimations.get(gunId);
    }

    public static BakedAnimation getFireAnimation(String gunId) {
        return fireAnimations.get(gunId);
    }

    public static BakedAnimation getReloadAnimation(String gunId) {
        return reloadAnimations.get(gunId);
    }

    public static BakedAnimation getReloadEmptyAnimation(String gunId) {
        return reloadEmptyAnimations.get(gunId);
    }

    @SubscribeEvent
    public static void onRegisterReloadListeners(RegisterClientReloadListenersEvent event) {
        event.registerReloadListener(new Listener());
    }

    private static final class Listener extends SimplePreparableReloadListener<Loaded> {
        @Override
        protected Loaded prepare(ResourceManager resourceManager, ProfilerFiller profiler) {
            Map<String, BakedGunModel> newModels = new HashMap<>();
            Map<String, BakedAnimation> newIdle = new HashMap<>();
            Map<String, BakedAnimation> newFire = new HashMap<>();
            Map<String, BakedAnimation> newReload = new HashMap<>();
            Map<String, BakedAnimation> newReloadEmpty = new HashMap<>();

            for (String gunId : GUN_IDS) {
                ResourceLocation geoId = ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "models/gun/" + gunId + ".geo.json");
                ResourceLocation animId = ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "animations/gun/" + gunId + ".animation.json");
                ResourceLocation textureId = ResourceLocation.fromNamespaceAndPath(Cordite.MODID, "textures/gun/" + gunId + ".png");
                try {
                    JsonObject geoJson = readJson(resourceManager, geoId);
                    BakedGunModel model = BedrockGeometryLoader.load(geoId, textureId, geoJson);
                    newModels.put(gunId, model);
                } catch (Exception e) {
                    LOGGER.warn("[Cordite] 銃モデル読み込み失敗（{}）: {}", gunId, e.toString());
                    continue;
                }

                JsonObject animJson;
                try {
                    animJson = readJson(resourceManager, animId);
                } catch (Exception e) {
                    LOGGER.warn("[Cordite] アニメーション読み込み失敗（{}）: {}", gunId, e.toString());
                    LOGGER.info("[Cordite] 銃モデル読み込み完了: {}", gunId);
                    continue;
                }

                loadAnimationInto(newIdle, gunId, animId, animJson, IDLE_ANIMATION_KEYS);
                loadAnimationInto(newFire, gunId, animId, animJson, FIRE_ANIMATION_KEYS);
                loadAnimationInto(newReload, gunId, animId, animJson, RELOAD_ANIMATION_KEYS);
                loadAnimationInto(newReloadEmpty, gunId, animId, animJson, RELOAD_EMPTY_ANIMATION_KEYS);
                LOGGER.info("[Cordite] 銃モデル読み込み完了: {}", gunId);
            }
            return new Loaded(newModels, newIdle, newFire, newReload, newReloadEmpty);
        }

        private static void loadAnimationInto(Map<String, BakedAnimation> out, String gunId, ResourceLocation animId,
                                               JsonObject animJson, Map<String, String> keyTable) {
            String animKey = keyTable.get(gunId);
            if (animKey == null) {
                return; // この銃/種別のアニメーションはまだ用意されていない
            }
            try {
                out.put(gunId, BedrockAnimationLoader.load(animId, animJson, animKey));
            } catch (Exception e) {
                LOGGER.warn("[Cordite] アニメーション'{}'読み込み失敗（{}）: {}", animKey, gunId, e.toString());
            }
        }

        @Override
        protected void apply(Loaded loaded, ResourceManager resourceManager, ProfilerFiller profiler) {
            models = Map.copyOf(loaded.models());
            idleAnimations = Map.copyOf(loaded.idleAnimations());
            fireAnimations = Map.copyOf(loaded.fireAnimations());
            reloadAnimations = Map.copyOf(loaded.reloadAnimations());
            reloadEmptyAnimations = Map.copyOf(loaded.reloadEmptyAnimations());
        }
    }

    private record Loaded(Map<String, BakedGunModel> models, Map<String, BakedAnimation> idleAnimations,
                           Map<String, BakedAnimation> fireAnimations, Map<String, BakedAnimation> reloadAnimations,
                           Map<String, BakedAnimation> reloadEmptyAnimations) {}

    private static JsonObject readJson(ResourceManager resourceManager, ResourceLocation id) throws Exception {
        try (BufferedReader reader = resourceManager.openAsReader(id)) {
            return GSON.fromJson(reader, JsonObject.class);
        }
    }
}
