package net.r0319.cordite.client.model;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.logging.LogUtils;
import net.minecraft.client.renderer.texture.MissingTextureAtlasSprite;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.SimplePreparableReloadListener;
import net.minecraft.util.profiling.ProfilerFiller;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterClientReloadListenersEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.AnimationSampler;
import net.r0319.cordite.client.anim.BakedAnimation;
import net.r0319.cordite.client.anim.BoneTrack;
import org.joml.Vector3f;
import org.slf4j.Logger;

import java.io.BufferedReader;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * 銃のBedrockモデルとアニメーションを、リソースリロード時にロード・ベイクしてキャッシュする。
 *
 * <p><b>登録作業は不要（自動検出）</b>。銃もアニメーションもコード側に一覧を持たない:</p>
 * <ul>
 *   <li><b>銃</b>: {@code assets/cordite/models/gun/&lt;path&gt;.geo.json} が置かれていれば読む。
 *       定義ファイルのパス＝gunId＝アセットのファイル名となるよう、{@code path} を完全一致させること。</li>
 *   <li><b>アニメーション</b>: {@code assets/cordite/animations/gun/&lt;gunId&gt;.animation.json} の
 *       {@code animations} に入っているクリップを<b>全部</b>読み、キー
 *       {@code "animation.&lt;何か&gt;.&lt;名前&gt;"} の最後の区切り以降を<b>クリップ名</b>として引けるようにする
 *       （例 {@code animation.glock.reload_empty} → {@code "reload_empty"}）。</li>
 * </ul>
 *
 * <p>つまり作者がBlockbenchでアニメーションを足す/リネームするだけで反映され、このファイルを
 * 編集する必要はない。ただし<b>「そのクリップをいつ再生するか」はコード側の話</b>なので、
 * 再生ロジックが対応しているのは {@link Clips} に挙げた標準名だけ。標準名以外のクリップは
 * 読み込まれるが再生はされない（無害。将来その名前の再生を実装したら動き出す）。</p>
 *
 * <p>該当アセットが用意されていない銃/クリップ（未実装のak47/m4a1、未作成のinspect等）は null を返す
 * （nullセーフ。呼び出し側の {@link net.r0319.cordite.client.render.GunItemRenderer} は描画・再生を
 * スキップする）。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class GunModelCache {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Gson GSON = new Gson();

    private static final String MODEL_DIR = "models/gun";
    private static final String MODEL_SUFFIX = ".geo.json";
    private static final String ANIMATION_DIR = "animations/gun";
    private static final String ANIMATION_SUFFIX = ".animation.json";
    private static final String TEXTURE_DIR = "textures/gun";

    /**
     * 再生ロジックが対応しているクリップ名。作者はBlockbenchで
     * {@code animation.<gunId>.<ここの名前>} という名前で作れば、コード変更なしで再生される。
     */
    public static final class Clips {
        private Clips() {}

        /** 待機。 */
        public static final String IDLE = "idle";
        /** 取り出し（この銃に持ち替えた瞬間に1回だけ再生）。未作成なら再生されないだけ。 */
        public static final String TAKE_OUT = "take_out";
        /** 発射（反動のキック）。 */
        public static final String FIRE = "fire";
        /**
         * 撃ち切りの1発（スライド／ボルトが後退したまま終わる）。ホールドオープンする銃で
         * 「最後の1発を撃った瞬間にチャンバーが開く」表現に使う。未作成なら{@link #FIRE}で代用される。
         */
        public static final String FIRE_EMPTY = "fire_empty";
        /** リロード。クリップ長は無視され、実際のリロード時間に合わせて再生速度が調整される。 */
        public static final String RELOAD = "reload";
        /** 弾切れからのリロード（スライドリリースを含む）。 */
        public static final String RELOAD_EMPTY = "reload_empty";
        /** 点検（Nキー。銃を眺めるだけでゲームプレイには影響しない）。未作成なら再生されないだけ。 */
        public static final String INSPECT = "inspect";
        /** 弾切れ状態での点検。未作成なら{@link #INSPECT}で代用される。 */
        public static final String INSPECT_EMPTY = "inspect_empty";
        /** 排莢（薬莢の飛行軌道のみ）。発射クリップとは独立に多重再生する（{@link net.r0319.cordite.client.anim.ShellEjectionTracker}）。 */
        public static final String EJECT = "eject";
    }

    /**
     * 描画側が名前で引くロケーターボーン（07-model-assets.md）。作者はBlockbenchでこの名前の
     * ボーンを置くだけでよく、コード側に座標を持たない。
     */
    public static final class Locators {
        private Locators() {}

        /** 腰だめ時の一人称カメラ基準（{@code root} の外に置き、アニメーションの影響を受けない定位置）。 */
        public static final String IDLE_VIEW = "idle_view";
        /** ADS時の一人称カメラ基準（{@code root} の子に置き、銃の動きに追従してサイトがカメラに乗る）。 */
        public static final String IRON_VIEW = "iron_view";
    }

    private static volatile Map<String, BakedGunModel> models = Map.of();
    /** 銃ID → クリップ名 → クリップ。 */
    private static volatile Map<String, Map<String, BakedAnimation>> animations = Map.of();
    /** 銃ID → GUIアイコンのテクスチャと実画像から取得した横:縦比。 */
    private static volatile Map<String, Icon> icons = Map.of();

    /** GUIアイコンの描画に必要な、リソースリロード時に確定する情報。 */
    public record Icon(ResourceLocation texture, float aspect) {}

    private static final Icon MISSING_ICON = new Icon(MissingTextureAtlasSprite.getLocation(), 1f);

    private GunModelCache() {}

    public static BakedGunModel getGeometry(String gunId) {
        return models.get(gunId);
    }

    /**
     * クリップ名でアニメーションを引く。未作成なら null。
     * 名前は {@link Clips} の定数を使うこと（作者側のファイルと対応が付くように）。
     */
    public static BakedAnimation getAnimation(String gunId, String clipName) {
        return animations.getOrDefault(gunId, Map.of()).get(clipName);
    }

    public static BakedAnimation getIdleAnimation(String gunId) {
        return getAnimation(gunId, Clips.IDLE);
    }

    public static BakedAnimation getFireAnimation(String gunId) {
        return getAnimation(gunId, Clips.FIRE);
    }

    public static BakedAnimation getReloadAnimation(String gunId) {
        return getAnimation(gunId, Clips.RELOAD);
    }

    public static BakedAnimation getReloadEmptyAnimation(String gunId) {
        return getAnimation(gunId, Clips.RELOAD_EMPTY);
    }

    /** 排莢アニメーション。未作成の銃は null（薬莢が飛ばないだけで他は通常どおり動く）。 */
    public static BakedAnimation getEjectAnimation(String gunId) {
        return getAnimation(gunId, Clips.EJECT);
    }

    /** 銃ごとのGUIアイコン。画像未作成時はバニラの欠損テクスチャを返す。 */
    public static Icon getIcon(String gunId) {
        return icons.getOrDefault(gunId, MISSING_ICON);
    }

    @SubscribeEvent
    public static void onRegisterReloadListeners(RegisterClientReloadListenersEvent event) {
        event.registerReloadListener(new Listener());
    }

    private static final class Listener extends SimplePreparableReloadListener<Loaded> {
        @Override
        protected Loaded prepare(ResourceManager resourceManager, ProfilerFiller profiler) {
            Map<String, BakedGunModel> newModels = new HashMap<>();
            Map<String, Map<String, BakedAnimation>> newAnimations = new HashMap<>();
            Map<String, Icon> newIcons = new HashMap<>();

            for (String gunId : findGunIds(resourceManager)) {
                newIcons.put(gunId, loadIcon(resourceManager, gunId));
                ResourceLocation geoId = asset(MODEL_DIR, gunId + MODEL_SUFFIX);
                ResourceLocation textureId = asset(TEXTURE_DIR, gunId + ".png");
                try {
                    newModels.put(gunId, BedrockGeometryLoader.load(geoId, textureId, readJson(resourceManager, geoId)));
                } catch (Exception e) {
                    LOGGER.warn("[Cordite] 銃モデル読み込み失敗（{}）: {}", gunId, e.toString());
                    continue;
                }

                Map<String, BakedAnimation> clips = loadAnimations(resourceManager, gunId);
                if (!clips.isEmpty()) {
                    newAnimations.put(gunId, clips);
                }
                warnIfViewLocatorsCollide(gunId, newModels.get(gunId), clips.get(Clips.IDLE));
                LOGGER.info("[Cordite] 銃モデル読み込み完了: {}（アニメーション {}）", gunId, clips.keySet());
            }
            for (String gunId : findIconGunIds(resourceManager)) {
                newIcons.putIfAbsent(gunId, loadIcon(resourceManager, gunId));
            }
            return new Loaded(newModels, newAnimations, newIcons);
        }

        /**
         * {@code textures/gun/<gunId>_modelshot.png} を読み、描画に使う実画像の縦横比をキャッシュする。
         * ファイルが無いか壊れている場合は、未作成を見分けられるようグロック等へ代替せず欠損テクスチャにする。
         */
        private static Icon loadIcon(ResourceManager resourceManager, String gunId) {
            ResourceLocation iconId = asset(TEXTURE_DIR, gunId + "_modelshot.png");
            if (resourceManager.getResource(iconId).isEmpty()) {
                return MISSING_ICON;
            }
            try (InputStream input = resourceManager.open(iconId); NativeImage image = NativeImage.read(input)) {
                if (image.getWidth() <= 0 || image.getHeight() <= 0) {
                    return MISSING_ICON;
                }
                return new Icon(iconId, (float) image.getWidth() / image.getHeight());
            } catch (Exception e) {
                LOGGER.warn("[Cordite] GUIアイコン読み込み失敗（{}）: {}", iconId, e.toString());
                return MISSING_ICON;
            }
        }

        /**
         * {@code models/gun/*.geo.json} を列挙して銃IDを拾う。これにより銃を増やしても
         * コード側の一覧を更新する必要がない。他MOD/リソースパックが同じパスに置いた場合に
         * 意図しない銃を拾わないよう、名前空間はCordite自身のものだけに絞る。
         */
        private static List<String> findGunIds(ResourceManager resourceManager) {
            List<String> ids = new ArrayList<>();
            resourceManager.listResources(MODEL_DIR, loc -> loc.getPath().endsWith(MODEL_SUFFIX))
                    .keySet().forEach(loc -> {
                        if (!Cordite.MODID.equals(loc.getNamespace())) {
                            return;
                        }
                        String fileName = loc.getPath().substring(loc.getPath().lastIndexOf('/') + 1);
                        ids.add(fileName.substring(0, fileName.length() - MODEL_SUFFIX.length()));
                    });
            ids.sort(String::compareTo); // ログ出力を安定させるだけ
            return ids;
        }

        /** モデル未作成でもGUIアイコンだけを先に確認できるよう、modelshotも独立して列挙する。 */
        private static List<String> findIconGunIds(ResourceManager resourceManager) {
            List<String> ids = new ArrayList<>();
            resourceManager.listResources(TEXTURE_DIR, loc -> loc.getPath().endsWith("_modelshot.png"))
                    .keySet().forEach(loc -> {
                        if (!Cordite.MODID.equals(loc.getNamespace())) {
                            return;
                        }
                        String fileName = loc.getPath().substring(loc.getPath().lastIndexOf('/') + 1);
                        ids.add(fileName.substring(0, fileName.length() - "_modelshot.png".length()));
                    });
            ids.sort(String::compareTo);
            return ids;
        }

        /**
         * animation.json 内のクリップを全部読む。クリップ名はBedrockのキー
         * {@code animation.<gunId>.<名前>} の最後の区切り以降。ファイルが無い銃は空マップ
         * （アニメーション無しで描画だけされる）。
         */
        private static Map<String, BakedAnimation> loadAnimations(ResourceManager resourceManager, String gunId) {
            ResourceLocation animId = asset(ANIMATION_DIR, gunId + ANIMATION_SUFFIX);
            if (resourceManager.getResource(animId).isEmpty()) {
                return Map.of(); // アニメーション未作成の銃（警告は出さない）
            }

            JsonObject animJson;
            try {
                animJson = readJson(resourceManager, animId);
            } catch (Exception e) {
                LOGGER.warn("[Cordite] アニメーション読み込み失敗（{}）: {}", gunId, e.toString());
                return Map.of();
            }
            if (!animJson.has("animations") || !animJson.get("animations").isJsonObject()) {
                LOGGER.warn("[Cordite] {}: 'animations' が無い", animId);
                return Map.of();
            }

            Map<String, BakedAnimation> clips = new TreeMap<>(); // ログ出力を安定させるだけ
            for (Map.Entry<String, JsonElement> entry : animJson.getAsJsonObject("animations").entrySet()) {
                String clipName = clipNameOf(entry.getKey());
                try {
                    BakedAnimation baked = BedrockAnimationLoader.load(animId, animJson, entry.getKey());
                    if (clips.put(clipName, baked) != null) {
                        // 例: animation.glock.fire と animation.pistol.fire が同じファイルに同居している
                        LOGGER.warn("[Cordite] {}: クリップ名 '{}' が重複している（後勝ち）", animId, clipName);
                    }
                } catch (Exception e) {
                    LOGGER.warn("[Cordite] アニメーション'{}'読み込み失敗（{}）: {}", entry.getKey(), gunId, e.toString());
                }
            }
            return clips;
        }

        /**
         * 待機ポーズにおいて{@code idle_view}と{@code iron_view}が同じ位置に来ていたら警告する。
         *
         * <p>この2つが重なると<b>ADSしても銃が1mmも動かず、腰だめの時点でサイトがカメラに乗ったまま</b>
         * になる（どちらもカメラ基準点として同じ点を指すため）。モデルとアニメーションの両方を見ないと
         * 分からない不具合で、ゲーム内では「ADSが効いていない」としか見えず原因に辿り着きにくいので、
         * 読み込み時にはっきり出しておく。</p>
         *
         * <p>判定には<b>待機ポーズ適用後</b>の位置を使う。{@code iron_view}は{@code root}の子なので、
         * pivotが同一でも{@code idle}が{@code root}を動かしていれば実際にはズレており、
         * それは正しい構成（腰だめ姿勢を待機アニメーション側で表現する作り方）だから。
         * ボーンの回転は無視しているので、回転だけで離れている構成は見逃すが、誤検知はしない。</p>
         */
        private static void warnIfViewLocatorsCollide(String gunId, BakedGunModel model, BakedAnimation idle) {
            if (model == null) {
                return;
            }
            GunBone hip = model.byName().get(Locators.IDLE_VIEW);
            GunBone sight = model.byName().get(Locators.IRON_VIEW);
            if (hip == null || sight == null) {
                return; // 片方でも無ければ描画側がフォールバックする（別の話）
            }
            Vector3f hipPos = idlePoseOrigin(hip, idle);
            Vector3f sightPos = idlePoseOrigin(sight, idle);
            if (hipPos.distanceSquared(sightPos) < 1.0e-8f) {
                LOGGER.warn("[Cordite] {}: 待機ポーズで '{}' と '{}' が同じ位置にあります。"
                                + "このままではADSしても銃が動かず、腰だめでもサイトがカメラに乗ったままになります。"
                                + "Blockbenchで '{}' を腰だめ位置へ動かすか、待機アニメーションの root に"
                                + "腰だめのオフセットを持たせてください",
                        gunId, Locators.IDLE_VIEW, Locators.IRON_VIEW, Locators.IDLE_VIEW);
            }
        }

        /**
         * 待機ポーズ適用後の、モデル原点から指定ボーンpivotまでのオフセット（平行移動ぶんのみ）。
         * アニメーション差分の符号・スケールの扱いは
         * {@code GunItemRenderer#applyAnimationDelta} と揃えてある。
         */
        private static Vector3f idlePoseOrigin(GunBone bone, BakedAnimation idle) {
            Vector3f sum = new Vector3f();
            for (GunBone current = bone; current != null; current = current.parent) {
                sum.add(current.localOffset);
                if (idle == null) {
                    continue;
                }
                BoneTrack track = idle.bones().get(current.name);
                AnimationSampler.Pose pose = track != null ? AnimationSampler.samplePose(track, 0f) : null;
                if (pose != null) {
                    Vector3f delta = pose.positionDelta();
                    sum.add(-delta.x() / 16f, delta.y() / 16f, delta.z() / 16f);
                }
            }
            return sum;
        }

        /** {@code "animation.glock.reload_empty"} → {@code "reload_empty"}。区切りが無ければキーそのまま。 */
        private static String clipNameOf(String animationKey) {
            int lastDot = animationKey.lastIndexOf('.');
            return lastDot < 0 ? animationKey : animationKey.substring(lastDot + 1);
        }

        @Override
        protected void apply(Loaded loaded, ResourceManager resourceManager, ProfilerFiller profiler) {
            models = Map.copyOf(loaded.models());
            Map<String, Map<String, BakedAnimation>> copied = new HashMap<>();
            loaded.animations().forEach((gunId, clips) -> copied.put(gunId, Map.copyOf(clips)));
            animations = Map.copyOf(copied);
            icons = Map.copyOf(loaded.icons());
        }
    }

    private record Loaded(Map<String, BakedGunModel> models, Map<String, Map<String, BakedAnimation>> animations,
                          Map<String, Icon> icons) {}

    private static ResourceLocation asset(String dir, String fileName) {
        return ResourceLocation.fromNamespaceAndPath(Cordite.MODID, dir + "/" + fileName);
    }

    private static JsonObject readJson(ResourceManager resourceManager, ResourceLocation id) throws Exception {
        try (BufferedReader reader = resourceManager.openAsReader(id)) {
            return GSON.fromJson(reader, JsonObject.class);
        }
    }
}
