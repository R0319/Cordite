# animation-system — Bedrockモデル読込・再生システム 🟡 仮

> **範囲**: Blockbench「Bedrock Edition」形式（`geometry.json`+`animation.json`）の自前パース・ベイク・レンダリング・簡易アニメーション再生。仕様は [../specs/06-animations.md](../specs/06-animations.md) / [../specs/07-model-assets.md](../specs/07-model-assets.md)、骨組みは [00-architecture.md](00-architecture.md)。

## 今回のスコープ（プロトタイプ）と次フェーズ

作者が作成したglockのviewmodel想定モデル・発射アニメーションのみを対象に、「一人称視点で銃が表示され、発射時にアニメーションが再生される」最短経路を実装した。以下は明確にスコープ外（次フェーズ）:

- ロケーター（`idle_view`/`iron_view`/`ground`/`thirdperson_hand`/`fixed`）に基づく精密配置。今回はハードコードした仮オフセットで代用（[07-model-assets.md#位置決め用ロケーター表示カメラ基準点](../specs/07-model-assets.md#位置決め用ロケーター表示カメラ基準点)）。
- `right_hand`/`left_hand`ボーンを使ったハンドアンカー方式の腕描画（TACZ方式）。
- worldmodel（三人称）・他プレイヤーへのアニメーション同期。
- ADS、リロード等fire以外のアニメーション。
- gunpackからの動的ロード（現状 `GunModelCache` に銃IDをハードコード、[01-gunpack.md](../specs/01-gunpack.md)実装後に差し替え）。

現状のモデル(`glock.geo.json`)はボーン名（`magazin`/`Slide`/`chamber`/`arm`等）や上記ロケーターが仕様（07-model-assets.md）と一部ズレているが、発射アニメーションが対象とする `barrel`/`bolt`/`trigger` ボーンは仕様通り存在するため、今回のスコープでは問題にならない。ズレの是正は次フェーズで詰める。

## ファイル形式・対応バージョン

- geometry.json `format_version`: **`1.21.0`** を対応版として固定。異なる場合はロード時に警告ログを出し、読み込みは継続する。
- animation.json `format_version`: **`1.8.0`** を対応版として固定。同上。
- UV方式: **per-face UV** に統一（07-model-assets.mdの🔵検討中を確定として記録）。Box UV（配列形式の`uv`）のキューブは非対応で、該当キューブは警告を出してスキップする。
- キーフレーム値は数値配列（`[x,y,z]`）のみサポート。Molang式・`pre`/`post`イージングオブジェクトは非対応（警告を出してそのキーフレームを無視）。

## 座標変換規則（GeckoLib実装準拠）

Bedrock座標系とJava版`PoseStack`の変換規則。GeckoLib現行実装（`RenderUtil`/`GeometryBone`/`GeometryCube`/`ActorBoneAnimationKeyframe`）で実証済みの規則をそのまま踏襲する。

- **位置**（pivot / origin / animationのposition）: **X座標のみ符号反転**、Y・Zはそのまま。1 Bedrock単位 = **1/16 ブロック**。
- **回転**（ボーン・キューブ・アニメーション共通）: **X回転・Y回転のみ符号反転**、Z回転はそのまま。度→ラジアン変換。
- **適用順序**: Bedrockの実効適用順は「X→Y→Z」。`PoseStack#mulPose`は右から効くため、コード上は **Z→Y→X の順で`mulPose`を積む**（`BedrockGeometryLoader`のキューブ静的回転、`GunItemRenderer#applyAnimationDelta`のアニメーション回転で統一）。

キューブ自体の静的な`rotation`（レール曲げ等の造形上の固定回転）は、ロード時に生の座標空間で頂点を直接回転させてからボーンpivot相対・Java座標系へ変換するため、上記のミラー規則とは独立して素直な回転行列で処理してよい（`BedrockGeometryLoader#bakeCube`参照）。

### 実寸スケールについて（既知の不確定要素）🟡

このモデルのcube座標の生値（例: レシーバー幅0.115、全長方向の広がり約4）が「1/16ブロック単位」なのか、Blockbenchの編集画面上で別スケールで作られたものかは実機で見るまで確定できない。上記の変換規則（÷16）はBedrock/GeckoLibの標準規約に沿った処理であり、最終的な見た目の大きさは `GunItemRenderer` の `MODEL_SCALE` 定数1箇所で調整できるようにしてある。実機（`runClient`）で見た目を確認し、大きすぎる/小さすぎる場合はここを調整すること。

## パース・ベイク方式

- `client.model.BedrockGeometryLoader#load`: `geometry.json`を1回だけパースし、`BakedGunModel`（ボーン木構造 `GunBone` + 各ボーンのcube頂点データ `BakedCube`）にベイクする。頂点座標はボーンpivot相対・Java座標系まで変換済みで保持し、毎フレームはボーン変換行列の計算のみで済む（パフォーマンス方針、[06-animations.md#パフォーマンス方針-仮](../specs/06-animations.md#パフォーマンス方針-仮)）。
- `client.model.BedrockAnimationLoader#load`: `animation.json`から指定アニメーションキー（例 `animation.glock17.fire`）のボーン別キーフレーム列を`BakedAnimation`にベイクする。キーフレームは時刻昇順配列で保持し、毎フレームは線形補間のみ（`client.anim.AnimationSampler`）。
- `sound_effects`/`particle_effects`のパースは未実装（今回のfireアニメには含まれておらず、発射音は既存の`GunItem.tryFire`のサーバー側`playSound`で足りているため）。次フェーズで発射エフェクトをアニメーション側のタイミングに寄せる際に実装する。

## ボーン階層とレンダリング

- `client.model.GunModelCache`（`RegisterClientReloadListenersEvent`で登録、`SimplePreparableReloadListener`）がリソースリロード時に銃ID一覧（現状 `glock` のみ）ぶんロード・ベイクし、`gunId → BakedGunModel` / `gunId → BakedAnimation`（fire）としてキャッシュする。**アセット未実装の銃はnullを返す**（呼び出し側は描画をスキップするだけで例外を投げない）。
- アイテムモデル側（`assets/cordite/models/item/glock.json`）の`parent`を`minecraft:builtin/entity`にすることで`BakedModel#isCustomRenderer()`が`true`を返し、全描画コンテキストで`GunItemRenderer#renderByItem`が呼ばれるようになる。
- 登録経路: `client.render.GunClientExtensions`（`RegisterClientExtensionsEvent`、mod bus + Dist.CLIENT）が`IClientItemExtensions#getCustomRenderer()`で`GunItemRenderer`（`BlockEntityWithoutLevelRenderer`のサブクラス、Mod内シングルトン）を返す。
- `GunItemRenderer#renderByItem`は`ItemDisplayContext`ごとに配置を分岐する。`FIRST_PERSON_RIGHT_HAND`/`FIRST_PERSON_LEFT_HAND`のみ精密に扱い（現状は仮の固定オフセット定数）、それ以外（GUI/地面ドロップ/三人称/アイテムフレーム）は原点付近への簡易配置。ロケーター実装後の次フェーズで精密化する。
- ボーン階層の描画はGunBoneを`translate`（localOffset）→ アニメーション差分適用 → cube頂点を`VertexConsumer`へ出力 → 子ボーンを再帰、の順で行う（`GunItemRenderer#renderBone`）。`geometry.json`側で複数のトップレベルボーン（`root`/`bb_main`/`arm`等）が存在する場合は、実体を持たない合成ルートでまとめて木構造にする（`BedrockGeometryLoader`）。

## アニメーション状態管理・発射検知（暫定方式）🟡 仮

- `client.anim.GunAnimationState`: ローカルプレイヤー1人分の「再生中クリップの開始tick」を保持する単純な静的ホルダ。複数プレイヤー分の管理は worldmodel 実装時に拡張する。
- **発射検知**: 専用の同期パケットを新設せず、`client.anim.ClientGunAnimationTracker`（`ClientTickEvent.Post`）が毎tick、メインハンドの銃の合計弾数（`GunItem#getTotalAmmo`、マガジン+薬室、既存の`networkSynchronized`データコンポーネント由来）を前tickと比較し、減少していたら発射とみなして`GunAnimationState#play`を呼ぶ。持ち替え時はアイテム種類の変化を検出して前回値をリセットし、誤検知を防ぐ。
- **既知の制約**:
  - フルオート連射時、ネットワーク往復以内に複数発撃たれると弾数減少がまとめて届き、アニメーションが1回分しか再生されない可能性がある。
  - 空撃ち（残弾0の`tryFire`失敗）は弾数が変化しないため検知できない。
  - いずれもGlock（セミオート）の検証時は実害が薄いが、AK47/M4A1のフルオート検証時には目立つ可能性が高い。
- **次フェーズの代替案**: `GunItem#tryFire`成功時に、既存の`playSound`と同じ場所で、撃った本人（将来的には周囲のトラッキングクライアントにも）へ発射1回ごとの軽量な片方向ペイロード（ダメージ等のゲームプレイ情報は積まない、純粋な演出トリガー）を送る方式へ切り替える。[00-architecture.md](00-architecture.md#ネットワーキング発射フローサーバー権威-仮)の「専用のエフェクト同期パケットは持たない」方針は発射音・トレーサーに関する取り決めであり、アニメーション状態同期は同ドキュメントで明示的に「未定・後日検討」とされているため、この代替案を採用しても既存方針と矛盾しない。

## アセット配置規約

```
assets/cordite/
├─ models/gun/<gunId>.geo.json
├─ animations/gun/<gunId>.animation.json
└─ textures/gun/<gunId>.png
```

- バニラの`models/item/`・`textures/item/`とは別の独自パスに置く（Bedrock JSONはバニラのブロック/アイテムモデルJSONと構造が別物のため）。
- 将来のgunpack構造（`gunpack/models/`・`gunpack/textures/`、[01-gunpack.md](../specs/01-gunpack.md#gunpackフォルダ構造)）への移行時は、`GunModelCache`のパス解決部分だけ差し替えれば済む構成にしてある。

## 主要クラス一覧

| クラス | 役割 |
|-------|------|
| `client.model.BedrockGeometryLoader` | `geometry.json`のパース・ベイク（座標変換込み） |
| `client.model.BedrockAnimationLoader` | `animation.json`のパース・ベイク |
| `client.model.BakedGunModel` / `GunBone` / `BakedCube` | ベイク済みモデルのデータ構造 |
| `client.model.GunModelCache` | リソースリロード時のロード・キャッシュ（銃ID→モデル/アニメ、nullセーフ） |
| `client.anim.BakedAnimation` / `BoneTrack` / `Keyframe` | ベイク済みアニメーションのデータ構造 |
| `client.anim.AnimationSampler` | 指定時刻でのボーン差分を線形補間でサンプリング |
| `client.anim.GunAnimationState` | ローカルプレイヤー1人分の再生状態 |
| `client.anim.ClientGunAnimationTracker` | 弾数tick差分監視による発射検知（暫定方式） |
| `client.render.GunItemRenderer` | BEWLR本体。ボーン階層歩行・頂点描画・配置 |
| `client.render.GunClientExtensions` | `RegisterClientExtensionsEvent`での登録 |

## 後続作業

- ロケーター（`idle_view`/`iron_view`/`ground`/`thirdperson_hand`/`fixed`）読み込みとADS/表示コンテキスト別の精密配置
- `right_hand`/`left_hand`ボーンによるハンドアンカー方式の腕描画
- worldmodel（三人称）実装・他プレイヤーへのアニメーション状態同期
- 発射検知の専用ペイロード方式への切替（フルオート・空撃ち対応）
- リロード等fire以外のアニメーション再生・状態遷移（同時1〜2レイヤーの簡易状態機械）
- gunpackからの動的ロードへの移行（`GunModelCache`のハードコードを置き換え）
- `sound_effects`/`particle_effects`のパースとエフェクトタイミングの反映
- モデル側のボーン名統一（`magazine`/`right_hand`等）・ロケーター追加（作者作業）

## 動作確認

`./gradlew runClient` → クリエイティブタブ「Cordite」からglockを取得:
1. 一人称視点で構えるとテクスチャ付きでモデルが表示される（ミッシングテクスチャにならない）。GUI（インベントリ）・地面ドロップ・アイテムフレームでもクラッシュせず何かしら表示される。
2. 左クリック発射時、既存の曳光弾・HUD残弾減少（[firing.md](firing.md)記載の既存動作）に加えて`barrel`（後退+わずかな回転）・`bolt`（後退→前進のスライドサイクル）・`trigger`（引き込み）が0.3333秒のモーションで動く。
3. ak47/m4a1（モデル未実装）に持ち替えてもクラッシュしない。glockに戻すと表示が復帰する。
4. `R`でリロードしてもfireアニメーションが誤発火しない。
5. F3+Tのリソースリロードでクラッシュしない。
