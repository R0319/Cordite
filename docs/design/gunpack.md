# gunpack — 銃定義のデータ駆動化 🟡 仮

> **範囲**: 銃の不変ステータス（ダメージ・RPM・マガジン容量等）をハードコードから JSON へ移す。
> 「何を作るか(What)」は [../specs/01-gunpack.md](../specs/01-gunpack.md) / [../specs/02-guns.md](../specs/02-guns.md)。
> 対象: NeoForge **1.21.1** / パッケージ `net.r0319.cordite`。

## 目的

**銃を1丁追加するのに Java を1行も書かなくて済む状態にする。**

現状は銃1丁につき以下6箇所の編集が必要で、これが銃追加の実コストになっている:

`ModItems.java` / `ModCreativeTabs.java` / `GunClientExtensions.java` / `lang/en_us.json` / `lang/ja_jp.json` / `models/item/<id>.json`

さらに `GunProperties` の静的プリセット（`GLOCK`/`AK47`/`M4A1`）がコード内にあるため、
バランス調整のたびに再ビルドが必要になっている。

## 採用方式: 単一アイテム + `gun_id` データコンポーネント

**銃ごとにアイテムを登録するのをやめ、`cordite:gun` 1アイテムだけを登録する。**
どの銃かは新規データコンポーネント `cordite:gun_id`（`ResourceLocation`）が持つ。

### なぜこの方式か（検証済みの根拠）

1. **NeoForge のレジストリは凍結されるため、datapack から `Item` を登録することは物理的に不可能。**
   datapack のロードはレジストリ凍結より後に走る。よって「JSONに銃を書いたらアイテムが増える」を
   実現する道は、単一アイテム + コンポーネントしかない。
2. **参考にしている tacz が実際にこの方式**（`/give @s tacz:modern_kinetic_gun{GunId:"..."}`）。
3. **PvPサーバー運用で効く**: 銃ごとにアイテムを登録する方式だと、サーバーとクライアントで
   gunpack の内容が違うとレジストリ不一致で**接続できなくなる**。単一アイテムなら
   アイテムレジストリは常に1件で一致するため、定義の差はデータ同期の問題に閉じる。

### 代償（許容する）

- `cordite:glock` 等のアイテムIDが消える。バニラの `/give` は `cordite:gun[cordite:gun_id="cordite:glock"]` 形式になる。
  利便性のため、Cordite側では同じ権限レベル2で `/cordite give <gunId> [<targets>] [<count>]` を提供する。
  `<gunId>` の補完元はサーバーがロード済みのgunpack定義であり、銃名のハードコードはしない。
- 旧セーブに残った銃は "Unknown item" として消える。**dev ブランチ・銃3丁のみのため互換性維持は不要**。

---

## パッケージ構成

```
net.r0319.cordite.gunpack
├─ GunDefinition.java          銃1丁の不変定義（record + CODEC）。GunProperties を置き換える
├─ GunDefinitions.java         gunId -> GunDefinition の保持（サーバー用/クライアント用の2マップ）
├─ GunDefinitionLoader.java    SimpleJsonResourceReloadListener（data/<ns>/gunpack/guns/*.json）
├─ GunpackEvents.java          ゲームバス: AddReloadListenerEvent / OnDatapackSyncEvent
└─ GunpackClientEvents.java    ゲームバス(Dist.CLIENT): 切断時にクライアント側定義を破棄

net.r0319.cordite.network
└─ SyncGunDefinitionsPayload.java   S→C 全定義同期
```

`item/gun/GunProperties.java` は**削除**する（`GunDefinition` へ一本化）。
`item/gun/` には `GunItem` / `FireMode` / `BoltType` が残る。

### GunProperties を残さず一本化する理由

消費側は「型名」ではなく「取得方法」が変わる。`gun.getProps()`（引数なし）→
`GunItem.definitionOf(stack, level)` はどのみち全消費箇所の書き換えが必要で、
型を2つに分けても編集箇所は減らない。Codec とクラス名が二重になるだけ。
将来 rails / attachments が増えたら `GunDefinition` にフィールドを足す。

---

## JSON スキーマ

**配置**: `data/<namespace>/gunpack/guns/<path>.json` → gunId = `<namespace>:<path>`

`data/<ns>/guns/` ではなく `gunpack/` を挟む理由: 他の銃系MODのデータと衝突して
毎回パースエラーログが出るのを避けるため。[../specs/01-gunpack.md](../specs/01-gunpack.md) の
`gunpack/guns/` 構造とも一致する。

```jsonc
{
  // 表示名。省略時は "item.<namespace>.<path>" の翻訳キーへフォールバック
  "name": "AK-47",                        // リテラル文字列でも {"translate": "..."} でも可

  // --- 必須 ---
  "base_damage": 7.0,
  "rpm": 600,
  "mag_size": 30,

  // --- 任意（既定値） ---
  "muzzle_velocity": 160.0,               // 既定 120.0   blocks/秒
  "effective_range": 60.0,                // 既定 40.0    blocks
  "falloff_start": 40.0,                  // 既定 20.0    blocks
  "reload_seconds": 2.5,                  // 既定 2.0
  "pellet_count": 1,                      // 既定 1
  "recoil_pitch": 1.8,                    // 既定 1.0     度/発（上）
  "recoil_yaw": 0.6,                      // 既定 0.3     度/発（±ランダム）
  "hip_spread_deg": 3.0,                  // 既定 2.0     腰だめ拡散（円錐頂点角）
  "fire_modes": ["single", "full_auto"],  // 既定 ["single"]。先頭が既定モード
  "bolt_type": "closed",                  // 既定 "closed"。"closed" | "open"
  "hold_open_on_empty": false,            // 既定 false
  "fire_sound": "cordite:pistol_fire",    // 既定 "cordite:pistol_fire"
  "fire_sound_range": 48.0                // 任意。省略時は16m可変レンジ
}
```

### バリデーション（不正値でのクラッシュ防止・必須）

| フィールド | 制約 | 理由 |
|-----------|------|------|
| `rpm` | `Codec.intRange(1, 6000)` | `fireIntervalTicks() = 1200/rpm` がゼロ除算する |
| `mag_size` | `Codec.intRange(1, 999)` | |
| `pellet_count` | `Codec.intRange(1, 64)` | |
| `fire_modes` | 空リスト禁止（`validate` で弾く） | `defaultMode()` の `get(0)` が `IndexOutOfBounds` |
| `fire_modes` | canonical constructor で `List.copyOf` | record の不変性を保つ |

**パース失敗は WARN ログを出してその銃だけスキップする。例外を投げてワールドロードを止めない。**

### `BoltType` に Codec を追加

`FireMode` と同じ書式に揃える（`StringRepresentable` 実装 + `StringRepresentable.fromEnum`）。
シリアライズ名は `"closed"` / `"open"`。

---

## 発射音のゼロJava化

`fireSound` は `Holder<SoundEvent>` 型のまま維持し、**JSON の `ResourceLocation` から
`Holder.direct(SoundEvent.createVariableRangeEvent(rl))` を作る。**
`ModSounds` への静的登録は不要。

### 検証済みの根拠（バニラソース実読）

`SoundEvent.STREAM_CODEC = ByteBufCodecs.holder(Registries.SOUND_EVENT, DIRECT_STREAM_CODEC)` であり、
`ByteBufCodecs.holder` の実装は:

```java
case DIRECT:
    VarInt.write(buf, 0);
    codec.encode(buf, holder.value());   // sound_id(ResourceLocation) + Optional<Float> range
```

つまり**レジストリ未登録の SoundEvent もインラインで送信され**、クライアント側は
`Holder.direct(...)` として復元し `getLocation()` で `sounds.json` を引く。
`ClientboundSoundPacket` のフィールドは `Holder<SoundEvent>` なのでそのまま通る。

`sounds.json` は `generateSoundsJson` が `sounds/gun/*.ogg` のファイル名から自動生成する。
→ **作者が `ak_47_fire.ogg` を置き JSON に `"fire_sound": "cordite:ak_47_fire"` と書くだけで固有の発射音が鳴る。**

`Holder<SoundEvent>` 型を維持することで、`GunAnimationSoundPlayer#serverSideFireSoundOf`
（`props.fireSound().value().getLocation()`）などの既存消費側は書き換え不要になる。

> ⚠ ソースコード上は確実だが**実機未検証**。検証手順 §18 で必ず確認すること。

---

## 定義レジストリ: サーバー用/クライアント用の2マップ

```java
public final class GunDefinitions {
    private static volatile Map<ResourceLocation, GunDefinition> SERVER = Map.of();
    private static volatile Map<ResourceLocation, GunDefinition> CLIENT = Map.of();
    // replaceServer / replaceClient / server() / client() / server(id) / client(id) / clearClient()
}
```

`volatile` + 不変マップ（`Map.copyOf`）で、サーバースレッドの書き込みとレンダースレッドの
読み出しを安全にする（`GunModelCache` と同じパターン）。

### 単一マップにしない理由

シングルプレイでは統合サーバーとクライアントが同一JVMなので、単一マップだと
リロードリスナーが書いたものをクライアントがそのまま読んでしまい、
**同期パケットが壊れていてもシングルプレイでは絶対に露見しない**。
専用サーバーで初めて「銃が全部不明になる」形で発覚する。
定義の入手経路が「jarに焼き込み（両側一致が構造的に保証される）」から
「ネットワーク越し」に変わるのがこの移行の本質なので、そこは論理サイドで分ける。

### 呼び分けの規約

- `client/**` 配下 → `GunDefinitions.client(id)` を直接呼ぶ（`Level` 不要）
- サーバー専用コード（`GunItem#tryFire`、`GunServerEvents`、`ModNetwork` の C→S ハンドラ）→ `GunDefinitions.server(id)`
- 両サイドから呼ばれるのは `GunItem` の状態アクセサだけ → **ここだけ `Level` 引数を足す**

---

## サーバー→クライアント同期

`OnDatapackSyncEvent` で全定義を送る。このイベントは `ClientboundLoginPacket` の**後**に
発火するため、`playToClient` ペイロードを送って安全。

```java
@SubscribeEvent
public static void onDatapackSync(OnDatapackSyncEvent event) {
    var payload = new SyncGunDefinitionsPayload(GunDefinitions.server());
    event.getRelevantPlayers().forEach(p -> PacketDistributor.sendToPlayer(p, payload));
}
```

`getRelevantPlayers()` はログイン時＝本人のみ、`/reload` 時＝全員を返す。

`SyncGunDefinitionsPayload` の StreamCodec は `ByteBufCodecs.fromCodecWithRegistries(GunDefinition.CODEC)`
を使い、StreamCodec を別途手書きしない（`ComponentSerialization.CODEC` がレジストリops を要求しうるため
`fromCodec` ではなく `WithRegistries`）。

- ハンドラは `context.enqueueWork(() -> GunDefinitions.replaceClient(...))`。
  **`context.player()` を触らない**（ログイン直後で未設定の可能性を避ける）。
- ロード時・送信時に件数を INFO ログへ出す（`ClientboundCustomPayloadPacket` の約1MB上限の目安確認用）。

---

## クリエイティブタブの動的生成

```java
.icon(() -> new ItemStack(ModItems.GUN.get()))     // ← 定義に依存させない
.displayItems((parameters, output) ->
    GunDefinitions.client().keySet().stream().sorted(Comparator.comparing(ResourceLocation::toString))
        .forEach(id -> output.accept(GunItem.createStack(id))))
```

- **アイコンを定義依存にしてはいけない**: `CreativeModeTab#getIconItem()` は初回結果を永続キャッシュする。
- タブ内の重複判定は `ItemStackLinkedSet.createTypeAndComponentsSet()`＝**種類＋コンポーネント**なので、
  単一アイテムでも `gun_id` が違えば別スタックとして並ぶ。
- `output.accept(Item)` は使えない。**`ItemStack` を渡す形に変える。**

### 既知の制約: `/reload` ではタブが更新されない

`CreativeModeTabs.tryRebuildTabContents` の呼び元は `CreativeModeInventoryScreen` の
コンストラクタと `containerTick` のみで、再構築要否は `registryAccess()` の**参照比較**で決まる。
`/reload` では参照が変わらないため、一度クリエイティブ画面を開いた後は一覧が古いまま。

**対応: 許容する。** 銃を追加するときは新しいモデル/テクスチャも必要で、それらは
`syncGunAssets`（ビルド時タスク）経由なのでどのみち `runClient` の再起動が要る。
`/reload` だけで銃が増える運用は実際には発生しない。
なお **`/give` は `/reload` 直後でも効き、発射・リロードも新定義で正しく動く**（サーバー側は更新済みのため）。

---

## アイテム表示名

`GunItem#getName(ItemStack)` をオーバーライドする。

```
gun_id なし              → Component.translatable("item.cordite.gun")
定義の "name" あり       → その Component
定義に "name" なし       → Component.translatable("item.<ns>.<path>")
```

- 目標が「lang編集ゼロ」なので JSON に `"name": "AK-47"` と書けるのを優先。
- ただし `ComponentSerialization.CODEC` なら `{"translate": "item.cordite.ak_47"}` も書けるので、
  **多言語対応したい銃だけ lang を使う**という両立ができる。片方に決め打たない。
- `getName` を上書きするので、JSONを書き換えれば**既存スタックの表示名も追随する**
  （`DataComponents.ITEM_NAME` を焼き込む方式だと追随しない）。

lang に**1キーだけ**追加: `item.cordite.gun`（"Gun" / "銃"）。

---

## 定義が見つからない場合のフォールバック

**方針: 未知の銃は「不活性なアイテム」にする。クラッシュもしないし、撃てもしない。**

| 呼び出し元 | 定義が null のときの挙動 |
|-----------|------------------------|
| `GunItem#tryFire` | 即 `return false`（発射も音もなし） |
| `startReload` / `completeReload` / `cycleFireMode` | 何もしない |
| `getMagazine` / `getTotalAmmo` / `getAmmoCapacity` | `0` |
| `isChambered` | `false` |
| `getFireMode` | `FireMode.SINGLE` |
| `getName` | `item.cordite.gun` |
| `GunHudOverlay` | 早期 return（HUDもレティクルも出さない） |
| `GunItemRenderer` | 既存の `model == null` 早期returnと同じ経路。加えて**gunIdは解決できたのにモデルが無い場合は warn-once ログ** |
| `GunActionPlayback#reloadSecondsOf` | `0f`（既存のnullチェックがそのまま使える） |
| `ModNetwork#onGunFired` | 反動キックをスキップ（既存の `props != null` チェックがそのまま） |

null になるケース: ①`gun_id` なし（素の `/give cordite:gun`）②JSONを消した/リネームした
③クライアントが同期前 ④定義の入っていない名前空間の gunId。

---

## gunId の命名規約

> **gunId は `ResourceLocation`。定義ファイルのパスがそのまま gunId になる。**
>
> | 種別 | パス |
> |-----|------|
> | 定義 | `data/<ns>/gunpack/guns/<path>.json` → gunId = `<ns>:<path>` |
> | モデル | `assets/<ns>/models/gun/<path>.geo.json` |
> | テクスチャ | `assets/<ns>/textures/gun/<path>.png` |
> | アニメ | `assets/<ns>/animations/gun/<path>.animation.json` |
>
> **`<path>` はアセットのファイル名と完全一致させること。** 命名は snake_case。

`ResourceLocation` を選ぶ理由: datapack のロードは本質的に `ResourceLocation` を返すため、
名前空間を捨てると2つのパックが同名の銃を定義したとき区別できない。
コンポーネントの Codec / StreamCodec もタダで手に入る。

### 既存の不整合を解消する

モデルファイルは `ak_47.geo.json` なのに登録名は `ak47` で、**現在 AK47 は描画されていない**。
→ **定義側を `ak_47` に合わせる**（作者のBlockbenchプロジェクト名を変えさせない方が事故が少ない）。

### 既知の限界（将来課題）

`syncGunAssets` はアセットをファイル名だけに畳んで `assets/cordite/` へコピーし、
`GunModelCache#findGunIds` は `cordite` 名前空間のみを走査する。よって**アセット側は名前空間を持たない**。
今回は `GunModelCache.getGeometry(gunId.getPath())` で橋渡しする。
`othermod:ak_47` と `cordite:ak_47` が両方あると同じモデルを共有してしまうため、
ロード時に **path が衝突する定義がある旨を WARN で出す**。名前空間対応の `GunModelCache` は将来課題。

---

## 実装ステップ

各ステップ単体でコンパイルが通る順序。Step 7 のみアトミック。

| Step | 内容 |
|-----|------|
| **1** | `BoltType` に `StringRepresentable` + `CODEC` を追加 |
| **2** | `gunpack/GunDefinition.java` 新規（誰もまだ使わない） |
| **3** | `GunDefinitions` / `GunDefinitionLoader` / `GunpackEvents`(AddReloadListenerEvent) 新規 → ロードログが出る |
| **4** | `SyncGunDefinitionsPayload` / `ModNetwork` に1行 / `OnDatapackSyncEvent` / `GunpackClientEvents` → 同期ログが出る |
| **5** | `ModDataComponents` に `GUN_ID` を追加（クラスJavadocの「銃IDはここに入れない」を書き換える） |
| **6** | `data/cordite/gunpack/guns/{glock,ak_47,m4a1}.json` を現行プリセットと同値で新規作成 |
| **7** | **切替（アトミック）**: 下表の全ファイルを1コミットで |
| **8** | 仕上げ: 銃ごとのGUIアイコン（実装済み）、ツールチップ |

### Step 7 の変更ファイル

| ファイル | 内容 |
|---------|------|
| `registry/ModItems.java` | 3登録 → `GUN = ITEMS.register("gun", ...)` の1つに |
| `item/gun/GunItem.java` | `props`フィールドと`getProps()`を削除。`static gunId(ItemStack)` / `static definitionOf(ItemStack, Level)` / `static createStack(ResourceLocation)` を追加。状態アクセサに`Level`引数を追加（`getAmmoCapacity()`含む）。`getName(ItemStack)`を追加。`shouldCauseReequipAnimation`を`!Objects.equals(gunId(old), gunId(new))`に |
| `item/gun/GunProperties.java` | **削除** |
| `combat/ProjectileManager.java` / `combat/GunProjectile.java` | 型を`GunDefinition`へ。**値渡しスナップショットのまま維持**（下記） |
| `event/GunServerEvents.java` | 引数追加のみ。**持ち替え検知ロジックは変更不要**（`held == state.lastHeldStack` のインスタンス同一性判定は影響を受けない） |
| `network/ModNetwork.java` | `onGunFired` で `getMainHandItem()` の stack から定義を引く |
| `registry/ModCreativeTabs.java` | icon を定義非依存に、`displayItems` を `GunDefinitions.client()` 走査に |
| `client/render/GunClientExtensions.java` | `event.registerItem(EXTENSIONS, ModItems.GUN.get())` |
| `client/render/GunItemRenderer.java` | gunId取得を`gun_id`コンポーネントに。`emptyPoseOverlayFor`を定義経由に。モデル欠落時のwarn-once追加 |
| `client/anim/ClientGunAnimationTracker.java` | gunId取得を同様に。null なら `reset()` |
| `client/anim/GunActionPlayback.java` / `GunAnimationSoundPlayer.java` | 定義取得を`GunDefinitions.client(...)`経由に |
| `client/GunHudOverlay.java` | `drawReticle` に定義（または`ItemStack`）を渡す |
| `client/ClientInputHandler.java` | `lastHeldItem`(`Item`) → `lastHeldGunId`(`ResourceLocation`)。判定を`!Objects.equals(...)`に。コメントも更新 |
| `assets/.../models/item/` | `{glock,ak47,m4a1}.json` 削除、`gun.json` 新規 |
| `assets/.../lang/{en_us,ja_jp}.json` | 銃3キー削除、`item.cordite.gun` 追加 |
| `client/model/GunModelCache.java` | Javadocの命名規約（「gunIdはアイテムの登録名と一致させること」）を上記の新規約に更新 |

### 弾丸は値渡しスナップショットのまま維持する

`ProjectileManager.fire` と `GunProjectile` はその場に `ItemStack` を持たないが、
**これは正しい設計なので変えない**。理由:

- 弾丸は**発射時のステータスで飛び切るべき**（発射後に持ち替えても弾道・ダメージが変わらない）。
- gunId を持たせて毎tick引き直すと、**飛行中に `/reload` で定義が消えたら NPE**。
  record は immutable でリロード時はマップごと差し替えるため、参照を握っていれば古い定義が生き続けて安全。

---

## 検証手順

### Step 3-4 完了時（挙動が変わらないうちに確認）

1. `runClient` → ワールド読み込み時に「銃定義を N 件ロード」ログ
2. `/reload` → 再ロード + 同期ログ
3. **`runServer` + `runClient` で localhost 接続** → クライアントに「定義 N 件を受信」ログ
4. わざと `"rpm": 0` に壊す → WARN が出てその銃だけスキップ、クラッシュしない

### Step 7 完了時

| # | 確認 | 期待 |
|---|-----|------|
| 1 | クリエイティブタブ | glock / ak_47 / m4a1 が並ぶ。名前が JSON の `"name"` どおり |
| 2-6 | 描画・発射・HUD・リロード・モード切替 | 従来どおり |
| 7 | **glock と ak_47 を隣のスロットに置いて持ち替え** | take_out アニメが毎回再生される（**単一アイテム化で最も壊れやすい箇所**） |
| 8 | 同じ銃を撃ちながら持ち続ける | リエクイップ演出が出ない |
| 9 | **ak_47 を持つ** | **モデルが描画される**（これまで `ak47`/`ak_47` 不整合で不可視だった） |
| 10 | m4a1 を持つ | モデル無しで不可視 + warn-once ログ。クラッシュしない |
| 11 | `/give @s cordite:gun` | 「銃」という不活性アイテム。撃てない・クラッシュしない |
| 12 | `/give @s cordite:gun[cordite:gun_id="cordite:glock"]` | 通常のグロック |
| 13 | `/give @s cordite:gun[cordite:gun_id="cordite:nonexistent"]` | 不活性。クラッシュしない |
| 14 | `rpm` を変えて `/reload` → 撃つ | 連射速度が変わる（サーバー側定義更新の確認） |
| 15 | `"name"` を変えて `/reload` | 手持ちの表示名が変わる（クライアント同期の確認） |
| 16 | **`runServer` + `runClient` で 1〜13 を再確認** | SPと同じ挙動（2マップ設計の効果検証） |
| 17 | `ak_47_fire.ogg` を置き `"fire_sound": "cordite:ak_47_fire"` | **ak_47 だけ別の音（Java編集ゼロ）** — 発射音ゼロJava化の実機検証 |

---

## 銃を1丁追加する手順（移行後）

1. **アセットを作業フォルダに置く**（階層は自由。ファイル名だけが意味を持つ）
   - `mp5.geo.json`（必須・無いと不可視）/ `mp5.png`（必須）
   - `mp5.animation.json`（任意。`idle`/`fire`/`reload`/`reload_empty`/`eject`/`take_out`/`inspect`）
   - `mp5_fire.ogg`（任意。無ければ既定の `cordite:pistol_fire`）
2. **定義JSONを1枚書く**: `src/main/resources/data/cordite/gunpack/guns/mp5.json`
3. **`./gradlew runClient`**
4. クリエイティブタブに MP5 が出る（または `/cordite give cordite:mp5`）

**Java の編集: 0行。lang の編集: 0行（`"name"` をリテラルで書いた場合）。**

## 関連

- [00-architecture.md](00-architecture.md) — 骨組み（「gunpack定義のサーバー→クライアント同期方式」はここで決定）
- [../specs/01-gunpack.md](../specs/01-gunpack.md) — gunpack仕様（レール・アタッチメントは未実装）
- [../specs/02-guns.md](../specs/02-guns.md) — 銃の数値（🟡仮値）
- [animation-system.md](animation-system.md) — アセット自動同期・アニメ再生
