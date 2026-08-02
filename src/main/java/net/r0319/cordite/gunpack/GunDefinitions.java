package net.r0319.cordite.gunpack;

import net.minecraft.resources.ResourceLocation;

import java.util.Map;

/**
 * 論理サイドごとの gunpack 定義保持領域。
 *
 * <p>統合サーバーでも同期経路を必ず通すため、サーバーがロードした定義とクライアントが受信した定義を
 * 別マップにする。各マップは不変コピーへ丸ごと差し替えるため、レンダースレッドからも安全に読める。</p>
 */
public final class GunDefinitions {
    private GunDefinitions() {}

    private static volatile Map<ResourceLocation, GunDefinition> SERVER = Map.of();
    private static volatile Map<ResourceLocation, GunDefinition> CLIENT = Map.of();

    public static void replaceServer(Map<ResourceLocation, GunDefinition> definitions) {
        SERVER = Map.copyOf(definitions);
    }

    public static void replaceClient(Map<ResourceLocation, GunDefinition> definitions) {
        CLIENT = Map.copyOf(definitions);
    }

    public static Map<ResourceLocation, GunDefinition> server() {
        return SERVER;
    }

    public static Map<ResourceLocation, GunDefinition> client() {
        return CLIENT;
    }

    public static GunDefinition server(ResourceLocation id) {
        return SERVER.get(id);
    }

    public static GunDefinition client(ResourceLocation id) {
        return CLIENT.get(id);
    }

    public static void clearClient() {
        CLIENT = Map.of();
    }
}
