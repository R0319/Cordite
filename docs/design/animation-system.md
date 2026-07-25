# animation-system — Bedrockモデル読込・再生システム 🟡 仮

> **範囲**: Blockbench「Bedrock Edition」形式（`geometry.json`+`animation.json`）の自前パース・ベイク・レンダリング・簡易アニメーション再生。仕様は [../specs/06-animations.md](../specs/06-animations.md) / [../specs/07-model-assets.md](../specs/07-model-assets.md)、骨組みは [00-architecture.md](00-architecture.md)。

## 今回のスコープ（プロトタイプ）と次フェーズ

作者が作成したglockのviewmodel想定モデル・アニメーション（idle/fire/reload/reload_empty）を対象に、「一人称視点で銃が表示され、待機/発射/リロードの各アニメーションが状況に応じて再生される」ところまで実装した。以下は明確にスコープ外（次フェーズ）:

- ADS用ロケーター`iron_view`の反映（`idle_view`/`ground`は実装済み。`thirdperson_hand`/`fixed`はモデル側にまだボーンが無い）。
- worldmodel（三人称）・他プレイヤーへのアニメーション同期。
- ADS本体（サイトを覗き込む機能自体）。
- inspectアニメーション（`animation.glock.inspect`はキーフレーム未実装のスタブのみ存在、今回は対象外）。
- gunpackからの動的ロード（現状 `GunModelCache` に銃IDをハードコード、[01-gunpack.md](../specs/01-gunpack.md)実装後に差し替え）。

現状のモデル(`glock.geo.json`)はボーン名（`magazin`/`Slide`/`chamber`等）が仕様（07-model-assets.md）と一部ズレているが、コードから名前で参照するボーン（`barrel`/`bolt`/`trigger`/`root`/`right_hand`/`left_hand`/`idle_view`/`iron_view`）は仕様通り存在するため、今回のスコープでは問題にならない。ズレの是正は次フェーズで詰める。

## ファイル形式・対応バージョン

- geometry.json `format_version`: **`1.21.0`** を対応版として固定。異なる場合はロード時に警告ログを出し、読み込みは継続する。
- animation.json `format_version`: **`1.8.0`** を対応版として固定。同上。
- UV方式: **per-face UV** に統一（07-model-assets.mdの🔵検討中を確定として記録）。Box UV（配列形式の`uv`）のキューブは非対応で、該当キューブは警告を出して**描画から**スキップする（AABBの計算対象からは外さない。ハンドアンカーの位置合わせに使うため）。
- キーフレーム値は数値配列（`[x,y,z]`）のみサポート。Molang式・`pre`/`post`イージングオブジェクトは非対応（警告を出してそのキーフレームを無視）。
- ボーンの`position`/`rotation`は、キーフレームのタイムマップ（`{"0.0": [...], "0.5": [...]}`）だけでなく、**数値配列を直接指定する「静的な単一ポーズ」形式**（例 `"rotation": [21.3, -0.5, 0.6]`）にも対応する。idleアニメーション（動きのない構えポーズ）で使われている形式で、時刻0の単一キーフレームとして読み込む（`BedrockAnimationLoader#readTrack`）。

## 座標変換規則（GeckoLib実装準拠）

Bedrock座標系とJava版`PoseStack`の変換規則。GeckoLib現行実装（`RenderUtil`/`GeometryBone`/`GeometryCube`/`ActorBoneAnimationKeyframe`）で実証済みの規則をそのまま踏襲する。

- **位置**（pivot / origin / animationのposition）: **X座標のみ符号反転**、Y・Zはそのまま。1 Bedrock単位 = **1/16 ブロック**。
- **回転**（ボーン・キューブ・アニメーション共通）: **X回転・Y回転のみ符号反転**、Z回転はそのまま。度→ラジアン変換。
- **適用順序**: Bedrockの実効適用順は「X→Y→Z」。`PoseStack#mulPose`は右から効くため、コード上は **Z→Y→X の順で`mulPose`を積む**（`BedrockGeometryLoader`のキューブ静的回転、`GunItemRenderer#applyAnimationDelta`のアニメーション回転で統一）。

キューブ自体の静的な`rotation`（レール曲げ等の造形上の固定回転）は、ロード時に生の座標空間で頂点を直接回転させてからボーンpivot相対・Java座標系へ変換するため、上記のミラー規則とは独立して素直な回転行列で処理してよい（`BedrockGeometryLoader#bakeCube`参照）。

### 原点の違い（centered grid）— 描画側で吸収する ⚠️

上記の変換規則が出すのは**「モデル原点を0とした相対座標」**であって、Javaアイテムモデル空間の座標ではない。両者は**原点の位置が違う**:

| | X | Y | Z |
|---|---|---|---|
| Bedrock（Blockbench, centered grid） | ブロック中心が0（-8〜+8） | ブロック底面が0（0〜16） | ブロック中心が0（-8〜+8） |
| Javaアイテムモデル | ブロックの角が0（0〜16） | ブロックの角が0（0〜16） | ブロックの角が0（0〜16） |

つまり `Java_x = 8 - Bedrock_x` / `Java_y = Bedrock_y` / `Java_z = 8 + Bedrock_z`（px）で、**X・Zに8px（0.5ブロック）のオフセットがある**（Yには無い）。この差を吸収しないと全描画コンテキストで銃が0.5ブロックずれる。

吸収する場所は**描画側1箇所**（`GunItemRenderer` の `ANCHOR` 定数）に寄せる。理由は、`renderByItem`に渡ってくる`PoseStack`の状態がバニラ都合で決まるため:

```java
// ItemRenderer#render（1.21.1）
handleCameraTransforms(poseStack, model, context, leftHand);
poseStack.translate(-0.5F, -0.5F, -0.5F);   // ← 独自レンダラーにも効く（分岐より前）
if (!model.isCustomRenderer() && ...) { ... } else {
    IClientItemExtensions.of(stack).getCustomRenderer().renderByItem(...);
}
```

`translate(-0.5, -0.5, -0.5)`が**`renderByItem`を呼ぶ前**に積まれているので、`renderByItem`内のローカル空間は「Javaアイテムモデル空間（ブロックが0〜1）」であり、**ローカル`(0.5, 0.5, 0.5)`がアイテムの基準点**になる。コンテキスト別の意味は、一人称＝カメラ（視点）位置、`GROUND`＝ドロップの中心、`FIXED`＝額縁の中心。

したがって`GunItemRenderer#applyContextPlacement`は、まず`translate(0.5, 0.5, 0.5)`で原点を基準点へ移し、以降をすべて基準点からの相対配置として扱う。ロケーター指定が無い場合の既定配置は、Bedrock原点をJavaの対応位置＝ブロック底面の中心（基準点から真下0.5ブロック）に置く（`alignBedrockOriginToDefault`）。

> なお`glock.json`の`parent`は`minecraft:builtin/entity`で、その実体`ModelBakery.BLOCK_ENTITY_MARKER`は`{"gui_light": "side"}`のみ＝**`display`変換を一切持たない**。バニラのアイテムが通常持つコンテキスト別の縮小・回転が効かないので、`GROUND`等の縮小もこちら側（`OTHER_CONTEXT_SCALE`）で行う必要がある。

### 実寸スケールについて（既知の不確定要素）🟡

このモデルのcube座標の生値（例: レシーバー幅0.115、全長方向の広がり約4）が「1/16ブロック単位」なのか、Blockbenchの編集画面上で別スケールで作られたものかは実機で見るまで確定できない。上記の変換規則（÷16）はBedrock/GeckoLibの標準規約に沿った処理であり、最終的な見た目の大きさは `GunItemRenderer` の `MODEL_SCALE` 定数1箇所で調整できるようにしてある。実機（`runClient`）で見た目を確認し、大きすぎる/小さすぎる場合はここを調整すること。

## パース・ベイク方式

- `client.model.BedrockGeometryLoader#load`: `geometry.json`を1回だけパースし、`BakedGunModel`（ボーン木構造 `GunBone` + 各ボーンのcube頂点データ `BakedCube`）にベイクする。頂点座標はボーンpivot相対・Java座標系まで変換済みで保持し、毎フレームはボーン変換行列の計算のみで済む（パフォーマンス方針、[06-animations.md#パフォーマンス方針-仮](../specs/06-animations.md#パフォーマンス方針-仮)）。
- `client.model.BedrockAnimationLoader#load`: `animation.json`から指定アニメーションキー（例 `animation.glock.fire`）のボーン別キーフレーム列を`BakedAnimation`にベイクする。キーフレームは時刻昇順配列で保持し、毎フレームは線形補間のみ（`client.anim.AnimationSampler`）。1本の`animation.json`ファイルに複数のアニメーション（idle/fire/reload/reload_empty/inspect）が入っており、`GunModelCache`が同じ`animJson`から必要なキーをそれぞれ抽出する（ファイル読み込み自体は銃1丁につき1回）。
- `sound_effects`/`particle_effects`のパースは未実装（今回のfireアニメには含まれておらず、発射音は既存の`GunItem.tryFire`のサーバー側`playSound`で足りているため）。次フェーズで発射エフェクトをアニメーション側のタイミングに寄せる際に実装する。

## ボーン階層とレンダリング

- `client.model.GunModelCache`（`RegisterClientReloadListenersEvent`で登録、`SimplePreparableReloadListener`）がリソースリロード時に銃ID一覧（現状 `glock` のみ）ぶんロード・ベイクし、`gunId → BakedGunModel` と、種別（idle/fire/reload/reload_empty）ごとの `gunId → BakedAnimation` としてキャッシュする。アニメーションキー名は銃ID・種別ごとに個別のテーブル（`IDLE_ANIMATION_KEYS`等）で管理する（例 `glock` の fire は `animation.glock.fire`）。**アセット未実装の銃・アニメーション種別はnullを返す**（呼び出し側は描画・再生をスキップするだけで例外を投げない）。
- アイテムモデル側（`assets/cordite/models/item/glock.json`）の`parent`を`minecraft:builtin/entity`にすることで`BakedModel#isCustomRenderer()`が`true`を返し、全描画コンテキストで`GunItemRenderer#renderByItem`が呼ばれるようになる。
- 登録経路: `client.render.GunClientExtensions`（`RegisterClientExtensionsEvent`、mod bus + Dist.CLIENT）が`IClientItemExtensions#getCustomRenderer()`で`GunItemRenderer`（`BlockEntityWithoutLevelRenderer`のサブクラス、Mod内シングルトン）を返す。
- `GunItemRenderer#renderByItem`は`ItemDisplayContext`ごとに配置を分岐する。位置の基準は**モデル側のロケーターボーン**から読み取る（`GunItemRenderer#alignLocatorToAnchor`）: 一人称は`idle_view`が視点（カメラ）位置に、`GROUND`は`ground`がドロップ中心に一致するようモデル全体を平行移動する。コード側に座標を決め打ちしない（作者がBlockbench上で配置を決められるようにするため。CLAUDE.mdのビジュアル作業分担）。対応ロケーターがモデルに無い場合は既定配置にフォールバックする。ロケーター自体がアニメーションで動く場合の追従は未対応（rest位置のみ見る）。
- `FIRST_PERSON_LEFT_HAND`（左利き設定・オフハンド）は`FIRST_PERSON_RIGHT_HAND`と同じ配置にする。バニラの手変換を止めているため`PoseStack`はどちらもカメラ基準のままで、左右を反転させる理由が無い（反転させると銃が後ろ向きになる）。
- 一人称では`IClientItemExtensions#applyForgeHandTransform`で`true`を返し、**バニラの一人称アイテム変換（手の位置へのオフセット・装備時の上下動・スイング）を丸ごと止める**。これをしないとバニラが先に手の位置へずらしてしまい、`idle_view`ロケーターの座標がそのまま反映されない。結果、`PoseStack`はカメラ基準のままレンダラーに渡る。
- ボーン階層の描画はGunBoneを`translate`（localOffset）→ アニメーション差分適用 → cube頂点を`VertexConsumer`へ出力 → 子ボーンを再帰、の順で行う（`GunItemRenderer#renderBone`）。`geometry.json`側で複数のトップレベルボーン（`root`/`bb_main`/`arm`等）が存在する場合は、実体を持たない合成ルートでまとめて木構造にする（`BedrockGeometryLoader`）。

## 一人称の腕（ハンドアンカー方式）

[06-animations.md#一人称の手腕表示ハンドアンカー方式-仮](../specs/06-animations.md#一人称の手腕表示ハンドアンカー方式-仮) の方式。**一人称コンテキストのみ**描画する（`ItemDisplayContext#firstPerson`）。

- モデル側の`right_hand`/`left_hand`ボーンに置かれた**腕プレースホルダの箱**（バニラ準拠の4×12×4px。[07-model-assets.md](../specs/07-model-assets.md)）に、バニラのプレイヤー腕（`PlayerRenderer#renderRightHand`/`renderLeftHand`）が**ぴったり重なるように**配置する。
- **配置数値はコードに持たない**。作者がBlockbench上でプレースホルダの箱を動かせば、バニラの腕がそのまま追従する（CLAUDE.mdのビジュアル作業分担に沿った設計）。位置合わせは「プレースホルダのAABBの最小コーナー」と「バニラの腕の箱の最小コーナー」を一致させることで行う（`GunItemRenderer#renderAnchoredArm`）。
- バニラ側の箱の位置は`HumanoidModel`の定義から確定できる定数として持つ（`VANILLA_RIGHT_ARM_MIN`/`VANILLA_LEFT_ARM_MIN`）。エンティティモデル空間は+Y下・+X左なので、`scale(-1, -1, 1)`でこちらの座標系へ写してから`ModelPart`を描かせる（行列式は正のままなので面の裏表は反転しない）。
- ボーンはアニメーション（idle/fire/reload/reload_empty）の`right_hand`/`left_hand`トラックで動く。`right_hand`/`left_hand`は`root`の外（トップレベル）に置かれているため、`renderBone`の再帰では届かない。`GunBone#parent`をたどって根元から変換を積み直す専用経路（`GunItemRenderer#applyBoneChain`）で対応する。
- プレースホルダの箱自体はBox UVのため描画対象から外れており（下記）、バニラの腕と二重に見えることはない。
- **AABBはUV方式に関わらず全キューブから計算する**（`BedrockGeometryLoader#expandBounds` → `GunBone#boundsMin`/`boundsMax`）。描画できないBox UVのキューブでも、位置合わせの基準としては使うため。
- 既知の差異: `renderRightHand`/`renderLeftHand`は内部で`HumanoidModel#setupAnim`を通すため、バニラ一人称の腕と同じ固定のZ軸傾き（`AnimationUtils#bobArms`由来、約±5.7度）が残る。バニラの手と同じ見え方になるようあえて打ち消していない。ズレが気になる場合はBlockbench側で箱を傾けて相殺する。

## アニメーション状態管理（暫定方式）🟡 仮

`client.anim.GunAnimationState`はローカルプレイヤー1人分の「現在再生中のアクション（`Action.FIRE`/`RELOAD`/`RELOAD_EMPTY`のいずれか、または無し）+開始tick」を保持する単純な静的ホルダ。複数プレイヤー分の管理は worldmodel 実装時に拡張する。

**優先順位**: fire/reload/reload_emptyのいずれかが再生中ならそれを最優先で表示し、無ければ（またはアクションの実時間が終わっていれば）`idle`にフォールバックする。この判定・サンプリングは`GunItemRenderer#sampleCurrentPose`が毎フレーム行う（idle自体は`GunAnimationState`が関知しない「デフォルト状態」という位置づけ）。

### 発射検知（fire）

専用の同期パケットを新設せず、`client.anim.ClientGunAnimationTracker`（`ClientTickEvent.Post`）が毎tick、メインハンドの銃の合計弾数（`GunItem#getTotalAmmo`、マガジン+薬室、既存の`networkSynchronized`データコンポーネント由来）を前tickと比較し、減少していたら発射とみなして`GunAnimationState#play(FIRE, ...)`を呼ぶ。持ち替え時はアイテム種類の変化を検出して前回値をリセットし、誤検知を防ぐ。

**既知の制約**:
- フルオート連射時、ネットワーク往復以内に複数発撃たれると弾数減少がまとめて届き、アニメーションが1回分しか再生されない可能性がある。
- 空撃ち（残弾0の`tryFire`失敗）は弾数が変化しないため検知できない。
- いずれもGlock（セミオート）の検証時は実害が薄いが、AK47/M4A1のフルオート検証時には目立つ可能性が高い。

**次フェーズの代替案**: `GunItem#tryFire`成功時に、既存の`playSound`と同じ場所で、撃った本人（将来的には周囲のトラッキングクライアントにも）へ発射1回ごとの軽量な片方向ペイロード（ダメージ等のゲームプレイ情報は積まない、純粋な演出トリガー）を送る方式へ切り替える。[00-architecture.md](00-architecture.md#ネットワーキング発射フローサーバー権威-仮)の「専用のエフェクト同期パケットは持たない」方針は発射音・トレーサーに関する取り決めであり、アニメーション状態同期は同ドキュメントで明示的に「未定・後日検討」とされているため、この代替案を採用しても既存方針と矛盾しない。

### リロード検知（reload / reload_empty）

弾数のtick差分では「リロード開始」を検知できない（弾数は`GunItem#completeReload`完了時にしか変化しない）ため、fireとは別方式を採る: `client.ClientInputHandler`がRキー押下でリロードパケットを送る**その場で**、サーバー側`GunItem#startReload`と同じ条件（マガジンが満タンでない・既にリロード中でない）をクライアントでも確認し、条件を満たせば`GunAnimationState#play`でreload/reload_emptyを即時開始する（サーバーの許可を待たないローカル予測。既存の発射トリガー送信と同じ「即応性優先」の考え方）。「既にリロード中」の判定は、サーバーの`GunFireManager.State.reloadCompleteTick`をクライアントは参照できないため、`ClientInputHandler`側で`now + props.reloadTicks()`を独自に記録して代用する。

reload/reload_emptyのどちらを再生するかは、リロード開始時点の`GunItem#isChambered`（薬室に弾が残っているか）で判定する（薬室に弾が残っていればタクティカルリロード=`reload`、空ならボルトリリースを伴う`reload_empty`。[firing.md](firing.md#薬室チャンバーとボルト方式)のロジックと対応）。

**サーバーがリクエストを拒否した場合**（例: 実際にはマガジンが満タンだった等のズレ）でも、クライアントでアニメーションが少し空回りするだけで実害はない（サーバー権威のゲーム状態自体は変化しない）。

### リロードアニメーションの時間スケーリング

`animation.glock.reload`（2.9583秒）/`animation.glock.reload_empty`（3.5833秒）というアニメーションファイル自体の長さと、実際のゲームプレイ上のリロード時間（`GunProperties.reloadSeconds`、Glockは1.8秒。🟡仮のバランス値でアニメーション制作時の長さと一致している保証はない）は一致しない。`GunItemRenderer#sampleCurrentPose`は、サンプリング時刻を `elapsed × (アニメーション長 / props.reloadSeconds())` にスケーリングすることで、**アニメーションが実際のリロード完了ちょうどに終わるよう再生速度を伸縮**する。これは[06-animations.md](../specs/06-animations.md)の「客観アニメーション：リロード - モーション変更なし・武器ごとに時間のみ変わる」という設計方針を主観アニメーション側にも適用したもの。fireアニメーションは反動の"キック"表現であり、連射中に毎回頭から再生されても違和感がないためスケーリングしない。

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
| `client.anim.GunAnimationState` | ローカルプレイヤー1人分の再生状態（`Action.FIRE`/`RELOAD`/`RELOAD_EMPTY`、無ければidleにフォールバック） |
| `client.anim.ClientGunAnimationTracker` | 弾数tick差分監視による発射検知（暫定方式） |
| `client.ClientInputHandler` | （既存）Rキー押下時にreload/reload_emptyの発火判定・開始も兼ねる |
| `client.render.GunItemRenderer` | BEWLR本体。ボーン階層歩行・頂点描画・配置（基準点合わせ、ロケーター、ハンドアンカー腕） |
| `client.render.GunClientExtensions` | `RegisterClientExtensionsEvent`での登録 |

## 後続作業

- `iron_view`を使ったADS時の配置切替（`idle_view`/`ground`は実装済み。`thirdperson_hand`/`fixed`はモデル側に未作成。なお現状の`iron_view`は`idle_view`と同一座標のため、実装しても見た目が変わらない）（座標は作者作業）
- ロケーターがアニメーションで動く場合の追従（現状はrest位置のみ参照。反動でカメラを揺らす等をやるなら必要）
- worldmodel（三人称）実装・他プレイヤーへのアニメーション状態同期
- 発射検知・リロード検知の専用ペイロード方式への切替（フルオート・空撃ち対応、サーバー拒否とのズレ解消）
- inspectアニメーションの中身作成・再生対応
- gunpackからの動的ロードへの移行（`GunModelCache`のハードコードを置き換え）
- `sound_effects`/`particle_effects`のパースとエフェクトタイミングの反映
- モデル側のボーン名統一（`magazine`/`chamber`統合等）（作者作業）
- `mag_ammo`/`ammo`のBox UVをper-face UVに変換（現状は読み飛ばされ非表示）（作者作業）

## 動作確認

`./gradlew runClient` → クリエイティブタブ「Cordite」からglockを取得:
1. 一人称視点で構えるとテクスチャ付きでモデルが表示される（ミッシングテクスチャにならない）。GUI（インベントリ）・地面ドロップ・アイテムフレームでもクラッシュせず何かしら表示される。
2. 何もしていない間はidleの構えポーズになる。
3. 左クリック発射時、既存の曳光弾・HUD残弾減少（[firing.md](firing.md)記載の既存動作）に加えて`barrel`（後退+わずかな回転）・`bolt`（後退→前進のスライドサイクル）・`trigger`（引き込み）が0.3333秒のモーションで動き、終わるとidleに戻る。
4. `R`でリロード: 薬室に弾が残っている状態では`reload`、残弾ゼロ（空撃ち後）では`reload_empty`が再生され、実際のリロード完了（`GunProperties.reloadSeconds`、Glockは1.8秒）に合わせて速度が伸縮する。リロード中にfireアニメーションが誤発火しない。
5. 一人称でバニラのプレイヤー腕が**左右1本ずつ**描画され、モデル側の`right_hand`/`left_hand`の箱の位置と重なる。アニメーション中も箱に追従して動く。三人称・GUI・地面ドロップでは腕が出ない。
6. 銃を捨てるとアイテムが地面に埋まらず、`ground`ボーンの位置を基準に表示される。
7. ak47/m4a1（モデル未実装）に持ち替えてもクラッシュしない。glockに戻すと表示が復帰する。
8. F3+Tのリソースリロードでクラッシュしない。
