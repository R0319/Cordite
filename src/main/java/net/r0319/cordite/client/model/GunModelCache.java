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
 * 銃のBedrockモデル・発射アニメーションをリソースリロード時にロード・ベイクしてキャッシュする。
 * 該当アセットが用意されていない銃（未実装のak47/m4a1等）は null を返す（nullセーフ。
 * 呼び出し側の {@link net.r0319.cordite.client.render.GunItemRenderer} は描画をスキップする）。
 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class GunModelCache {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Gson GSON = new Gson();

    /** アセットが用意されている銃ID一覧（プロトタイプ時点ではglockのみ）。 */
    private static final List<String> GUN_IDS = List.of("glock");

    /** 銃ID→animation.json内のfireアニメーションキー。 */
    private static final Map<String, String> FIRE_ANIMATION_KEYS = Map.of(
            "glock", "animation.glock17.fire"
    );

    private static volatile Map<String, BakedGunModel> models = Map.of();
    private static volatile Map<String, BakedAnimation> fireAnimations = Map.of();

    private GunModelCache() {}

    public static BakedGunModel getGeometry(String gunId) {
        return models.get(gunId);
    }

    public static BakedAnimation getFireAnimation(String gunId) {
        return fireAnimations.get(gunId);
    }

    @SubscribeEvent
    public static void onRegisterReloadListeners(RegisterClientReloadListenersEvent event) {
        event.registerReloadListener(new Listener());
    }

    private static final class Listener extends SimplePreparableReloadListener<Loaded> {
        @Override
        protected Loaded prepare(ResourceManager resourceManager, ProfilerFiller profiler) {
            Map<String, BakedGunModel> newModels = new HashMap<>();
            Map<String, BakedAnimation> newAnimations = new HashMap<>();

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

                String animKey = FIRE_ANIMATION_KEYS.get(gunId);
                if (animKey != null) {
                    try {
                        JsonObject animJson = readJson(resourceManager, animId);
                        BakedAnimation anim = BedrockAnimationLoader.load(animId, animJson, animKey);
                        newAnimations.put(gunId, anim);
                    } catch (Exception e) {
                        LOGGER.warn("[Cordite] 発射アニメーション読み込み失敗（{}）: {}", gunId, e.toString());
                    }
                }
                LOGGER.info("[Cordite] 銃モデル読み込み完了: {}", gunId);
            }
            return new Loaded(newModels, newAnimations);
        }

        @Override
        protected void apply(Loaded loaded, ResourceManager resourceManager, ProfilerFiller profiler) {
            models = Map.copyOf(loaded.models());
            fireAnimations = Map.copyOf(loaded.fireAnimations());
        }
    }

    private record Loaded(Map<String, BakedGunModel> models, Map<String, BakedAnimation> fireAnimations) {}

    private static JsonObject readJson(ResourceManager resourceManager, ResourceLocation id) throws Exception {
        try (BufferedReader reader = resourceManager.openAsReader(id)) {
            return GSON.fromJson(reader, JsonObject.class);
        }
    }
}
