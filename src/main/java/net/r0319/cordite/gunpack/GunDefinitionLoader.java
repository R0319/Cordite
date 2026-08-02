package net.r0319.cordite.gunpack;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.mojang.logging.LogUtils;
import com.mojang.serialization.JsonOps;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.SimpleJsonResourceReloadListener;
import net.minecraft.util.profiling.ProfilerFiller;
import org.slf4j.Logger;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/** data/<namespace>/gunpack/guns/*.json から銃定義を読み込むリロードリスナー。 */
public final class GunDefinitionLoader extends SimpleJsonResourceReloadListener {
    private static final Logger LOGGER = LogUtils.getLogger();
    private final RegistryAccess registryAccess;

    public GunDefinitionLoader(RegistryAccess registryAccess) {
        super(new Gson(), "gunpack/guns");
        this.registryAccess = registryAccess;
    }

    @Override
    protected void apply(Map<ResourceLocation, JsonElement> jsons, ResourceManager resourceManager,
                         ProfilerFiller profiler) {
        var ops = RegistryOps.create(JsonOps.INSTANCE, registryAccess);
        Map<ResourceLocation, GunDefinition> loaded = new HashMap<>();
        Map<String, ResourceLocation> idsByPath = new HashMap<>();
        Set<String> reportedPaths = new HashSet<>();

        for (var entry : jsons.entrySet()) {
            ResourceLocation id = entry.getKey();
            GunDefinition.CODEC.parse(ops, entry.getValue()).resultOrPartial(error ->
                    LOGGER.warn("銃定義 {} の読み込みをスキップしました: {}", id, error))
                    .ifPresent(definition -> {
                        ResourceLocation other = idsByPath.putIfAbsent(id.getPath(), id);
                        if (other != null && !other.equals(id) && reportedPaths.add(id.getPath())) {
                            LOGGER.warn("銃定義 {} と {} は同じアセットパス '{}' を共有します", other, id, id.getPath());
                        }
                        loaded.put(id, definition);
                    });
        }

        GunDefinitions.replaceServer(loaded);
        LOGGER.info("銃定義を {} 件ロードしました", loaded.size());
    }
}
