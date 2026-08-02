# animation-system — Bedrockモデル読込・再生システム 🟡 仮

> **範囲**: Blockbench「Bedrock Edition」形式（`geometry.json`+`animation.json`）の自前パース・ベイク・レンダリング・簡易アニメーション再生。仕様は [../specs/06-animations.md](../specs/06-animations.md) / [../specs/07-model-assets.md](../specs/07-model-assets.md)、骨組みは [00-architecture.md](00-architecture.md)。

## 今回のスコープ（プロトタイプ）と次フェーズ

作者が作成したglockのviewmodel想定モデル・アニメーション（idle/fire/reload/reload_empty）を対象に、「一人称視点で銃が表示され、待機/発射/リロードの各アニメーションが状況に応じて再生される」ところまで実装した。以下は明確にスコープ外（次フェーズ）:

- worldmodel（三人称）・他プレイヤーへのアニメーション同期。
- ADSのゲームプレイ側効果（命中精度・移動速度など。サーバー権威で持つ必要があり未着手）。**見た目のADS（右クリックで`iron_view`をカメラへ寄せる）は実装済み** → [ADS（サイト覗き込み）](#adsサイト覗き込み)
- `thirdperson_hand`/`fixed`ロケーター（モデル側にまだボーンが無い）。
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
- ボーンの`scale`トラックにも対応する（`position`/`rotation`と同じ`readTrack`）。リロード中にマガジン内の弾（`mag_ammo`）を0倍にして消す用途で使われている。`PoseStack#scale`は非一様スケールで法線行列に`1/x`を掛けるため、0成分は微小値に丸める（`GunItemRenderer#safeScale`。潰れたままなので見た目は変わらない）。
- `sound_effects`のパースは実装済み → [サウンド（sound_effects）](#サウンドsound_effects)。`particle_effects`は未実装（マズルフラッシュ等を入れる際に同じ経路で実装する）。

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
- **バニラが腕に掛ける固定のZ軸傾きは打ち消す**（`GunItemRenderer#cancelVanillaArmBob`）。`renderRightHand`/`renderLeftHand`は内部で`setupAnim`を通し、その中の`AnimationUtils#bobModelPart`が`zRot += multiplier * (cos(ageInTicks * 0.09) * 0.05 + 0.05)`を加算する。一人称の手は`ageInTicks = 0`固定で呼ばれるので値は常に**±0.1 rad（約5.73度）**。放置すると肩を軸に傾いたまま描かれ、手先（肩から12px）で**約1.2px＝0.075ブロック**ズレて、作者がBlockbenchで合わせた握り位置と合わなくなる。`ModelPart#render`は「pivotへの平行移動 → `zRot`回転」の順に積むので、その手前で同じpivotまわりの逆回転を積めば回転だけが相殺される。同時に加算される`xRot`は`renderHand`が描画直前に0へ潰すので対処不要。袖は`copyFrom`で腕と同じ姿勢になるため1回で両方に効く。**MCのバージョンを上げる際は`AnimationUtils`の式を確認すること。**
- **Slimスキンでも位置合わせの基準は変わらない**。`setupAnim`が腕パーツのオフセットを毎回`x=∓5, y=2, z=0`へ固定するので、Slim側の`PartPose`（`y=2.5`）は効かない。差はSlimの腕が1px細いことだけで、右腕は最小コーナーが一致する（`our_min_x = -entity_max_x`で、`entity_max_x`はClassic/Slimとも`-4`）。**左腕のみ幅の差ぶん1px（0.0625ブロック）X方向にズレる**。

## アニメーション状態管理（暫定方式）🟡 仮

`client.anim.GunAnimationState`はローカルプレイヤー1人分の「現在再生中のアクション（`Action.FIRE`/`RELOAD`/`RELOAD_EMPTY`のいずれか、または無し）+開始tick」を保持する単純な静的ホルダ。複数プレイヤー分の管理は worldmodel 実装時に拡張する。

**優先順位**: fire/reload/reload_emptyのいずれかが再生中ならそれを最優先で表示し、無ければ（またはアクションの実時間が終わっていれば）待機アニメーションにフォールバックする。この判定・サンプリングは`GunItemRenderer#sampleCurrentPose`が毎フレーム行う（待機自体は`GunAnimationState`が関知しない「デフォルト状態」という位置づけ）。

### 待機ポーズを土台に重ねる（レイヤー合成）⚠️アセット規約

**`idle`は常に土台として敷かれ、その上にアクションのクリップを重ねる**（`AnimationSampler#sampleLayered`）。アクション側は**自分が動かすボーンのトラックだけ**持てばよい。

- そうしないと、クリップにトラックが無いボーンは「差分ゼロ＝restポーズ」になる。`idle`の手のポーズ（`right_hand`/`left_hand`）はrestからの差分で表現されているので、たとえばマガジンしか動かさない`reload`を再生した瞬間に**手だけrestポーズへ飛ぶ**。
- **加算ではなく上書き**。作者のクリップは「その時点の絶対ポーズ」として作られている（`take_out`の終端は`idle`の手の値そのもので、加算すると二重に効いて破綻する）。上書きの粒度は**チャンネル単位**（position/rotation/scale別）で、クリップが打っていないチャンネルは土台の値が残る。
- 作者側の意味: **`idle`が全ボーンの基準ポーズ**。各クリップでは`idle`から動かしたいボーンにだけキーを打てばよく、クリップの終端を`idle`の値に戻しておけば待機へ滑らかに繋がる。

### 弾切れ待機（ホールドオープン）

撃ち切り時にスライド／ボルトが後退保持される銃（[06-animations.md#撃ち切り時のホールドオープン-仮](../specs/06-animations.md#撃ち切り時のホールドオープン-仮)）では、弾切れの間ずっと後退状態を見せる必要がある。

- 銃ごとの属性 `GunProperties.holdOpenOnEmpty`（実銃準拠。Glock/M4A1=true、AK47=false）で分岐する。
- `GunItemRenderer#emptyPoseOverlayFor` が「`holdOpenOnEmpty` かつ `GunItem#getTotalAmmo` が0」のとき、**`reload_empty` の先頭フレーム**を`idle`の上に重ねる（待機系は常に先頭フレーム＝0秒でサンプリングされる）。`reload_empty` が未作成の銃は通常の `idle` のみになる。
- **弾切れ専用の待機クリップ（`idle_empty`）は持たない**。弾切れリロードは「スライドが後退保持された状態」から始まるので、その0秒目のポーズがそのまま弾切れ待機になる。2つ持つと両者の先頭ポーズを手で合わせ込む必要があり、ズレるとリロード開始の瞬間にスライドが飛ぶ——同じフレームを共用すればその不整合が原理的に起きない。作者の作業も1か所で済む。
  - 作者作業: `reload_empty` の0秒目にチャージングハンドル／スライドを後退させたキーを打つ。それが**弾切れ待機とリロード開始の両方**になる。
- 状態は`ItemStack`のデータコンポーネント（既存の同期済み残弾）から毎フレーム読むだけなので、`GunAnimationState`への状態追加やトラッカーの拡張は不要。
#### チャンバーが開くタイミング（撃ち切りの瞬間）

**要件は「0発になった瞬間にチャンバーが開いている」**（遅れて開くと違和感が出る）。遅れの原因は2つあり、どちらも潰してある。

**1. 撃ち切りの判定をパケットで受け取る**

撃ち切ったかどうかは**サーバーが判定**して`GunFiredPayload.emptyAfterShot`で送る。クライアントの残弾コンポーネントはこのパケットより**スロット同期が数tick遅れて届く**ため、それを見て判定すると必ず遅れて開く（このペイロードが作られた理由と同じ問題）。表示側は`GunAnimationState.emptiedByRecentShot`（パケット受信から`AMMO_SYNC_GRACE_TICKS`＝10tickの間だけ有効）を優先し、同期が追いついた後はコンポーネントの値に任せる。

**2. 撃ち切りでも発射モーションは再生し、スライドだけ後退で固定する**

`fire`はスライドが前進して終わるクリップなので、撃ち切りにそのまま流用すると「撃った直後だけスライドが閉じていて、クリップが終わってから開く」ことになる。かといって発射モーションを丸ごと省くと**最後の1発だけ銃が反動で跳ねない**。

そこで**`fire`を再生したうえで、弾切れポーズ（`reload_empty`の先頭フレーム）が待機ポーズと違えている部分だけを上から貼り直す**（`GunItemRenderer#pinEmptyHoldOpen` → `AnimationSampler#applyDifferences`）。glockの場合その差分は`bolt`の後退だけで、`root`は待機と同値なので**反動はそのまま残る**。

- 作者作業は「`reload_empty`の0秒目にスライドを後退させたキーを打つ」だけ（弾切れ待機と共用のもの）。**`fire_empty`を別途作る必要はない**。
- 前提として、各クリップの0秒目は待機ポーズと一致させておくこと（[待機ポーズを土台に重ねる](#待機ポーズを土台に重ねるレイヤー合成)）。ズレていると、その差分まで「弾切れの状態」とみなされて発射中に固定されてしまう。
- 貼り直すのは**発射系のアクション中だけ**。リロード系のクリップはスライドの解放（前進）を自分で表現しているので、貼り直すとスライドが永久に開いたままになる。
- `fire_empty`を作った銃では貼り直しを行わない（スライドの扱いをそのクリップに任せる）。スライドが後退→前進→後退と動く様子まで作り込みたい場合はこちら。

なお発射クリップ全般の終了判定も`animation_length`ではなく**最後のキーフレーム**にしてある（`GunActionPlayback#motionEndSeconds`）。Blockbenchの`animation_length`はタイムラインの長さであって動きの終わりではなく、glockの`fire`は0.5833秒あるのに動きは0.1667秒で終わっている。排莢の寿命判定と同じ考え方。

#### リロード直後のちらつき

リロードアニメーションは**クライアントのローカル予測**で始まる（Rキーを押した時点）ため、サーバーが装填を完了して残弾が同期されるより先に再生が終わる。その隙間で残弾を読むとまだ0なので、**スライドが一瞬開いてから閉じる**。リロード再生の終了から`GunAnimationState.RELOAD_SYNC_GRACE_TICKS`（10tick＝0.5秒）の間は弾切れ表示を抑止して吸収している。

本来はリロード完了をサーバーから通知すべきで、それは後続作業（「リロード検知の専用ペイロード方式への切替」）。それが入ればこの猶予は不要になる。

### マガジン内の弾（`mag_ammo`）は残弾に連動して消す

残弾表示は「マガジン＋薬室」の合計なので、クローズボルト銃で**残り1発**のときは「薬室に1発・マガジンは空」という状態になる。モデルはマガジン内の弾（`mag_ammo`）を常に持っているため、**マガジンが空（`GunItem#getMagazine` が0）の間はscale0で描画から落とす**（`GunItemRenderer#hideEmptyMagazineAmmo`）。オープンボルト銃は薬室を持たない（`isChambered`が常にfalse）ので同じ条件がそのまま通る。

- **リロード中とその直後の同期待ちは触らない**。リロードクリップの`mag_ammo`のscaleキーが「古いマガジンの弾が消える→新しいマガジンで戻る」を表現しているので、割り込むと入れ直した弾が出てこない。猶予（`withinReloadSyncGrace`）も同じで、残弾の同期がまだ0のままなので弾が一瞬消えてから現れるちらつきになる。
- ⚠️ **作者作業**: `reload_empty`の`mag_ammo`のscaleは0秒目が`[1,1,1]`になっている。弾切れリロードは**マガジンが空の状態から始まる**ので、リロードを始めた瞬間だけ空マガジンに弾が現れる（上記のとおりリロード中はコード側が触らないため）。0秒目を`[0,0,0]`に打ち直せば解消する。
- 薬室の弾（`ammo`）は未対応。薬室が空（ホールドオープン中など）でも弾が見えたままになる。`ammo`は排莢の多重描画（`renderEjectedShells`）と共用のボーンなので、消すなら飛行中の薬莢と取り違えないよう別途設計する。

### 空撃ち音との関係（サーバー側）

ホールドオープンする銃は撃発機構が働かないため、`GunItem#tryFire` の空撃ち分岐で**音を鳴らさない**。ホールドオープンしない銃も、`GunFireManager.State#dryFiredThisPress`（押下エッジで`GunServerEvents#driveFiring`がリセット）により1トリガー1回だけ鳴らす（従来はフルオートで押しっぱなしにすると連射レートで鳴り続けていた）。

空撃ち音を`animation.json`の`sound_effects`側に持たせない理由: アニメーション再生はクライアント側で、現状は他プレイヤーへの同期経路が無いため、周囲に聞こえるべき音をそこに置けない。サーバーの`playSound`で配信する現行経路を維持する（`sound_effects`はリロード中のメカ音など、タイミングを作者が詰めたい音のために使う → 下記）。

無音の銃では弾切れに気付けないため、`client.GunHudOverlay`が残弾0のときクロスヘア下に弾切れ／リロード促しを表示する（右下の残弾表示の赤色化と併用）。自分でリロードを始めた直後は`ClientInputHandler#isReloadingPredicted`（既存のローカル予測値）で抑制する。

### 発射検知（fire）

`GunItem#tryFire`が1発撃つことに成功したら、既存の`playSound`と同じ場所で撃った本人へ`network.GunFiredPayload`（**S→C・ペイロード空**）を送り、受け取ったクライアントが`GunAnimationState#playFire`で再生を開始する。ダメージ・方向・命中結果といったゲームプレイ情報は一切積まない純粋な演出トリガーで、かつサーバー→クライアントの片方向なので、サーバー権威は崩れない。[00-architecture.md](00-architecture.md#ネットワーキング発射フローサーバー権威-仮)の「専用のエフェクト同期パケットは持たない」方針は発射音・トレーサーに関する取り決めであり、アニメーション状態同期は同ドキュメントで明示的に「未定・後日検討」とされている領域なので矛盾しない。

ハンドラ（`ModNetwork#onGunFired`）が触るのは`GunAnimationState`だけで、これは`client`パッケージにあるがMinecraftのクライアント専用クラスを一切参照しない素のJavaクラスなので、専用サーバーでロードされても問題ない。ゲーム時刻も`Minecraft.getInstance()`ではなく`IPayloadContext#player()`から取っている。

**旧方式（残弾の同期差分）からの移行理由**: 以前は`ClientGunAnimationTracker`が毎tick合計弾数（`GunItem#getTotalAmmo`）を前tickと比較し、減少していたら発射とみなしていた。専用パケットを増やさずに済む反面、

- スロット同期は発射音の配信より遅れて届くため、**反動アニメーションが銃声からずれて再生されていた**。
- ネットワーク往復以内に複数発撃たれると減少がまとめて届き、**フルオートで1発ぶんしか再生されなかった**。

この遅延は実在が確認できている（「発射直後にRを押すとリロードアニメーションが再生されない」不具合の原因が、まさにこの同期遅れによる残弾値の陳腐化だった → [リロード検知](#リロード検知reload--reload_empty)）。`GunFiredPayload`は発射音と同じtickに送られるので、アニメーションが銃声と揃い、1発ごとに再生される。

**リロード中は発射アニメを割り込ませない**（`GunAnimationState#playFire`が`isReloading`を見て無視する）。リロードを再生し始めた後に、その直前に撃った弾のトリガーが遅れて届くと、fireがreloadを上書きしてしまう。fireは0.5秒級のキックなので、それが終わった時点でidleへ戻り、2.7秒級のリロードモーションが丸ごと消える（サーバー側のリロードだけは進むので「モーション無しでリロードが完了する」ように見える）。サーバーはリロード中の発射を拒否するため、この間に届く発射トリガーは必ず「リロード開始前に撃った弾のぶん」であり、無視して問題ない。あわせて終了判定（`GunActionPlayback#current`）を毎tick回し、`isReloading`が1tick古い状態を返してリロード終了直後の1発を取りこぼさないようにしている。

**既知の制約**: 空撃ち（残弾0の`tryFire`失敗）はペイロードを送っていないため検知できない。空撃ちモーションを入れる際は、`GunFiredPayload`にフラグを1つ足すか専用ペイロードを足せばよい（旧方式と違い、経路自体はもうある）。

### リロード検知（reload / reload_empty）

弾数の変化では「リロード開始」を検知できない（弾数は`GunItem#completeReload`完了時にしか変化しない）ため、fireとは別方式を採る: `client.ClientInputHandler`がRキー押下でリロードパケットを送る**その場で**、サーバー側`GunItem#startReload`と同じ条件（マガジンが満タンでない・既にリロード中でない）をクライアントでも確認し、条件を満たせば`GunAnimationState#play`でreload/reload_emptyを即時開始する（サーバーの許可を待たないローカル予測。既存の発射トリガー送信と同じ「即応性優先」の考え方）。「既にリロード中」の判定は、サーバーの`GunFireManager.State.reloadCompleteTick`をクライアントは参照できないため、`ClientInputHandler`側で`now + props.reloadTicks()`を独自に記録して代用する。

reload/reload_emptyのどちらを再生するかは、リロード開始時点の`GunItem#isChambered`（薬室に弾が残っているか）で判定する（薬室に弾が残っていればタクティカルリロード=`reload`、空ならボルトリリースを伴う`reload_empty`。[firing.md](firing.md#薬室チャンバーとボルト方式)のロジックと対応）。

**満タン判定は撃った直後だけ保留する**: 発射による弾数減少は数tick遅れて届くので、満タンのマガジンから1発撃って即Rを押すと、手元の残弾はまだ満タンのままになる。そのまま「リロード不要」と判定するとアニメーションを出さない一方、サーバーは（実際は1発減っているので）リロードを受理してしまい、**モーション無しでリロードが完了する**。`ClientInputHandler`はトリガーを押していた最後のtickを記録し、そこから`AMMO_SYNC_GRACE_TICKS`（10tick=0.5秒）以内は満タン判定をスキップする。トリガー押しっぱなし中は毎tick更新するのでフルオートでも猶予が途切れない。

**サーバーがリクエストを拒否した場合**（例: 実際にはマガジンが満タンだった等のズレ）でも、クライアントでアニメーションが少し空回りするだけで実害はない（サーバー権威のゲーム状態自体は変化しない）。同じ理由で、撃ち切り直後は薬室の同期待ちにより`reload`/`reload_empty`を取り違えることがある。どちらも正確化にはリロード開始のサーバー→クライアント同期が必要（[00-architecture.md](00-architecture.md)「アニメーション状態のネットワーク同期方式（未定）」）。

### 排莢（薬莢）は独立クリップの多重再生 ⚠️アセット規約

**薬莢の軌道を`fire`クリップに含めてはいけない。** `animation.<gunId>.eject`（薬莢ボーン`ammo`のトラックだけを持つ専用クリップ）に分けて作る。

理由は、薬莢が**同時に複数個存在しうる**のに対し`GunAnimationState`は「今再生中のアクション1つ」しか持てないため。Glockは400RPM＝**0.15秒間隔**で撃てるのに薬莢の軌道は**0.29秒**あるので、`fire`に含めると次弾を撃った瞬間にクリップが頭から再生し直され、**飛行中の薬莢が銃の中へ戻る**（軌道の約半分で消える）。クリップ長を縮める・再生速度をスケーリングする類の対処では原理的に解けない。

- `client.anim.ShellEjectionTracker`が、発射のたびに**独立した開始tickを持つインスタンス**をリングバッファ（最大8個。最速900RPMでも同時5個で収まる）へ積む。開始は`ModNetwork#onGunFired`で`GunAnimationState#playFire`と同じタイミング（発射アニメを抑止したとき＝リロード中に遅れて届いたトリガーでは薬莢も飛ばさないよう、`playFire`が開始可否を返す）。
- 描画は`GunItemRenderer#renderBone`が`ammo`ボーンに来たときだけ分岐し、**生存インスタンスの数だけ同じキューブを重ねて描く**（`renderEjectedShells`）。ボーン本来の描画（＝薬室に装填されている1発）はそのまま残るので、「装填された弾＋飛行中の薬莢」が同時に見える。
- **寿命は`animation_length`ではなく最後のキーフレームの時刻**（`BakedAnimation#lastKeyframeSeconds`）。`AnimationSampler`は最終キー以降の時刻に対して最後の値を返し続けるため、`animation_length`（glockは0.5833秒）を寿命にすると軌道の終点（0.2917秒）で**薬莢が空中に0.29秒静止してから消える**。動きが終わった時点で捨てる。→ **作者が排莢クリップにキーフレームを足せば、そのぶん薬莢が長く飛ぶ**（コード側の調整不要）。
- 破棄は`ClientGunAnimationTracker`が毎tick、銃の持ち替え・退出時は`reset()`。
- 排莢クリップが無い銃（`GunModelCache#getEjectAnimation`がnull）は薬莢が飛ばないだけで他は通常どおり動く（他のアニメーション種別と同じnullセーフ方針）。
- [06-animations.md](../specs/06-animations.md#パフォーマンス方針-仮)の「同時アニメーションレイヤー数を絞る」方針との関係: 増えるのは**1ボーンぶんのサンプリングと描画**だけで、ボーン階層全体を多重評価するレイヤー合成ではない。

**既知の制約**: 薬莢ボーンは`root`の子なので、飛行中も銃本体の動き（`root`）に引きずられる。寿命が0.29秒と短いため実用上は目立たないが、気になる場合は「発射時点の`root`ポーズをスナップショットして固定する」拡張余地がある。ワールド空間で放物線を描かせる（＝クリップの長さから完全に解放する）のはworldmodel実装フェーズの検討事項。

### マズルフラッシュ（ロケーター＋コード生成ビルボード）

**作者が用意するのは「銃口に置いたロケーターボーン」と「png 1枚」だけ**。板もUVもアニメーションのキーフレームも作らない。

- **位置は作者**: モデルに `muzzle_flash` という**cubeを持たないボーン（ロケーター）**を作り、pivotを銃口に置く。`root`の子にしておけば銃の動きに追従する。
- **タイミング・見た目はコード**: `client.anim.MuzzleFlashState` が発射（`GunFiredPayload`受信）から `DURATION_SECONDS`（既定0.1秒＝約2tick）のあいだ表示状態を持ち、`GunItemRenderer#renderMuzzleFlash` がロケーター位置に**常にカメラを向く板を1枚**生成して描く。毎発ランダムなロール角と大きさのゆらぎが入り、経過に応じてアルファがフェードアウトする。
- **発光描画**: 銃本体の`entityCutoutNoCull`（アルファ2値・ワールドの明るさで暗くなる）ではなく **`RenderType.entityTranslucentEmissive` ＋ `LightTexture.FULL_BRIGHT`**。これをしないと**暗所でフラッシュが真っ暗になり**、アルファのグラデーションも出ない（cutoutは0/1の二値）。
- **薬莢と違って多重再生は不要**。フラッシュは1〜2tickなので、連射で撃ち直されても「撃つたびに光る」という正しい挙動になる。
- **一人称のみ**。`MuzzleFlashState`はローカルプレイヤー1人分の状態なので、三人称や他プレイヤーの銃に描くと「自分が撃つと他人の銃も光る」ことになる。他プレイヤーぶんはworldmodel実装時に扱う。
- ロケーターが無い銃では何もしない（テクスチャの参照自体を行わないので、アセット未作成でもミッシングテクスチャにならない）。

**なぜ「板＋`scale`キー」方式をやめたか** ⚠️:
以前は[06-animations.md](../specs/06-animations.md#発射エフェクトのタイミング方式-仮)の「タイミングはアニメーションファイルに埋め込む」方針どおり、`muzzle_flash`ボーンに板を作って`fire`クリップで`scale`を 0→1→0 と打つ設計だった。しかしBedrock geometryのUVは**銃本体テクスチャの宣言解像度**（`description.texture_width/height`）で正規化されるため、別解像度の`muzzle_flash.png`に板のUVを合わせる作業がBlockbench上で煩雑になる（画像全体を貼るために「銃テクスチャの座標系で0,0〜128,128を指定する」ような読み替えが要る）。ロケーター方式なら作者の作業が「pivotを置く」だけになり、板が真横から消える問題（十字に2枚置く等の対処）もビルボード化で消える。**タイミングを作者が持つ方針から外れるのはマズルフラッシュだけ**で、発射音・排莢は従来どおりアニメーションファイル側にある。

**アセット側の要件** ⚠️:
- テクスチャは `textures/effect/muzzle_flash.png`。銃ごとではなく共有（将来gunpackで銃ごとに差し替える余地はある）。
- **アルファ付き（32bit RGBA）であること**。背景が不透明だと板の四角がそのまま見える。パレット形式（8bit・tRNSなし）はアルファチャンネルを持てないので不可。背景は「白く塗る」のではなく**消してアルファ0にする**。フラッシュの芯も白いので、色で抜くと芯に穴が開く点に注意。
- 画像は正方形前提（板が正方形のため）。縦横比を変えたい場合は`GunItemRenderer`側の定数で対応する。
- `muzzle_flash`ボーンには**cubeを作らないこと**。作るとその板が銃本体テクスチャで描かれ、ビルボードと二重に見える。

### 取り出し（`take_out`）

**この銃に持ち替えた瞬間**に1回だけ再生する。判定は`ClientInputHandler`の持ち替え検出（アイテムが変わった／ホットバーのスロットが変わった）で、残弾同期でも立ってしまう`heldChanged`とは別物。

あわせて前の銃の演出状態を捨てる: 飛行中の薬莢（`ShellEjectionTracker`）と鳴りかけのサウンドタイムライン（`GunAnimationSoundPlayer`。リロード中に持ち替えた場合など）をリセットし、撃ち切りフラグも落とす。

**取り出し中でも発射・リロードはできる**。サーバー側に「持ち替え時間」という概念がまだ無いためで、撃てばそちらのアニメーションが上書きする。持ち替え直後を撃てなくするなら、サーバー側にクールダウンを持たせる必要がある（後続作業）。

長さは`animation_length`ではなく**最後のキーフレームの時刻**（`GunActionPlayback#motionEndSeconds`）。動きが終わった後の余白ぶん待たされないようにするためで、ゲームプレイ側の持ち替え時間という概念が無い以上、長さは作者のクリップそのままになる。**終端のポーズを`idle`の値に合わせておくこと**（合っていれば待機へ継ぎ目なく繋がる。上記「待機ポーズを土台に重ねる」）。画面外から銃を振り込むような`root`の平行移動もそのまま出る——腰だめの基準ロケーター`idle_view`は`root`の外にあり、`root`のアニメーションで打ち消されないため（ADSの`iron_view`は逆に`root`の子で、覗いている間はサイトがカメラに固定される。→[ADS](#adsサイト覗き込み)）。

### 点検（`inspect` / `inspect_empty`）

**Nキー**（`ModKeyMappings.INSPECT`、キーコンフィグで変更可）で銃を眺めるモーションを再生する。**クライアント完結**で、サーバーへは何も送らない——ゲーム状態を一切動かさないため（周囲のプレイヤーからは見えない。三人称への反映は他プレイヤーへのアニメーション状態同期に乗る＝後続作業）。

- 弾切れなら`inspect_empty`（スライドが後退したまま眺めるクリップ）。判定は弾切れ待機の表示と同じで、同期が遅れる残弾コンポーネントより`GunFiredPayload`で届いた撃ち切りの事実（`GunAnimationState#emptiedByRecentShot`）を優先する。`inspect_empty`が未作成なら通常の`inspect`で代用する。
- 長さは`take_out`と同じく**最後のキーフレームの時刻**（等速再生）。ゲームプレイ側に「点検にかかる時間」という概念が無いので、リロードのような時間スケーリングはしない。**終端のポーズを`idle`に合わせておくこと**。
- **中断のルール**: 点検はいつ捨ててもよい見せるだけの動作なので、リロードのように他の入力を抑止せず、**点検の方が譲る**。
  - 発射・リロード・持ち替え → それぞれの`GunAnimationState#play`が上書きする（発射は`playFire`の割り込み抑止がリロード中しか効かないため、そのまま上書きされる）。
  - ADS（右クリック）→ `ClientInputHandler`が`GunAnimationState#cancelInspect`で畳む。覗いた状態でNを押した場合も同じ経路で即座に畳まれる（＝ADS中は点検できない）。
  - 逆に**リロード中はNを押しても始まらない**。リロードはサーバー権威で進行中の動作で、モーションだけ上書きすると「モーション無しでリロードが完了する」ことになるため。
- 中断された点検の**サウンドも止める**（`GunAnimationSoundPlayer#stopInspect`。他アクションによる中断は`start`が自動で行う）。「開始したタイムラインは鳴らし切る」の唯一の例外——リロードや発射に移った後で銃を眺める音だけが鳴り続けるのは明らかにおかしいため。

### リロードアニメーションの時間スケーリング

`animation.glock.reload`/`animation.glock.reload_empty`（ともに2.7083秒）というアニメーションファイル自体の長さと、実際のゲームプレイ上のリロード時間（`GunProperties.reloadSeconds`、Glockは1.8秒。🟡仮のバランス値でアニメーション制作時の長さと一致している保証はない）は一致しない。`client.anim.GunActionPlayback#current`は、サンプリング時刻を `elapsed × (アニメーション長 / props.reloadSeconds())` にスケーリングすることで、**アニメーションが実際のリロード完了ちょうどに終わるよう再生速度を伸縮**する。これは[06-animations.md](../specs/06-animations.md)の「客観アニメーション：リロード - モーション変更なし・武器ごとに時間のみ変わる」という設計方針を主観アニメーション側にも適用したもの。fireアニメーションは反動の"キック"表現であり、連射中に毎回頭から再生されても違和感がないためスケーリングしない。

この「どのクリップを・クリップ内の何秒目で再生するか」の判定は描画とサウンド再生の両方で必要なため、`GunActionPlayback`に切り出してある（描画は`GunItemRenderer#sampleCurrentPose`から毎フレーム、サウンドは`ClientGunAnimationTracker`から毎tick呼ぶ）。

## サウンド（sound_effects）

[06-animations.md](../specs/06-animations.md)の「発射音・薬莢排出等のタイミングはアニメーションファイルに埋め込む」方針の実装。

- `BedrockAnimationLoader#readSoundEffects`が`sound_effects`（`{"<秒>": {"effect": "<名前>"}}`、同時刻に複数なら配列）を読み、`BakedAnimation#soundEffects`（時刻昇順の`SoundKeyframe`）として保持する。
- 再生は`client.anim.GunAnimationSoundPlayer`。`ClientGunAnimationTracker`が毎tick進め、前回時刻から今回時刻までに跨いだキーフレームを鳴らす。**描画（毎フレーム）ではなくtick駆動**にしているのは、パーシャルティックの前後動で同じキーフレームが二重再生されるのを避けるため。タイミング精度は1tick（50ms）刻み。
- **サウンドは表示中のアニメーションとは独立に走る**（クリップごとの`Timeline`）。`GunAnimationState`は「今表示しているアクション」を1つしか持たず、表示に紐づけて鳴らすと表示が切り替わった瞬間に残りのサウンドキーフレームが消えてしまう。開始したタイムラインは表示が別のアクションへ移っても最後まで鳴らし切る（[発射検知](#発射検知fire)の割り込み抑止で表示側もリロード中は上書きされなくなったが、二重の保険として独立したままにしてある）。
- 再生開始の検出には`GunAnimationState#playId`（再生のたびに増える通し番号）を使う。同じアクションの撃ち直しでも値が変わるので、開始エッジを取りこぼさない。
- **同系統（発射系／リロード系）のタイムラインは同時に1本まで**。新しく始まった側が古い方を捨てる。連射で発射音が積み重なって鳴り続けるのを防ぐため（リロード側は途中で上書きされないので、この制約で消えることはない）。
- **effect名の解決規則**: Blockbenchのキーフレームの「Effect」名をそのままサウンドイベントIDとして引く。名前空間を省略した場合は`cordite:`を補う。`minecraft:`付きで書けばバニラの音も鳴らせる。解決できない名前はwarnログを1回だけ出して無視する（[06-animations.md](../specs/06-animations.md)の「Cordite側で解決できるID」）。

### 音を足すのにコードを触る必要はない（登録不要）

**`ModSounds`（Javaのレジストリ登録）への追加は不要**。ここで鳴らす音はクライアントローカル再生で、音声ファイルの解決は`sounds.json`を読んだ`SoundManager`が行うため、レジストリ登録が無くてもコード側で`SoundEvent`をその場で作れば鳴る（`GunAnimationSoundPlayer#resolveSound`）。登録が要るのは**サーバーから`playSound`で配信する音だけ**（発射音など。レジストリIDでネットワーク越しに送るため）。

`sounds.json`のエントリも**ビルド時に自動補完される**（`generateSoundsJson`タスク）。`sounds/gun/*.ogg` にあってエントリの無い音だけを書き足し、既存エントリ（手で`subtitle`を足したもの等）は変更しない。字幕を出したい音だけ`sounds.json`と`lang`に手で足す。

したがって作者の作業は「**作業フォルダにoggを置いてBlockbenchでEffect名に指定する**」だけで完結する。

> 実例: `sniper_ready.ogg` を置いて`reload_empty`のキーフレームに指定したのに無音だった——oggは同期されていたが`sounds.json`と`ModSounds`に登録が無く、`SoundEvent`の解決に失敗していた（`latest.log`に「対応する音がありません」のwarn）。この自動化前は音を1つ足すたびに2か所へ手で追記する必要があった。

### 命名規約: 音声ファイル名＝Effect名（＝`sounds.json`のキー）

`assets/cordite/sounds/gun/*.ogg`のファイル名・`sounds.json`のキー・`animation.json`の`effect`値は**すべて同じ文字列に揃える**（サーバー配信する音は`ModSounds`の登録名も同じにする）。

理由は工程を減らすため。Blockbenchはサウンドキーフレームの**「Effect」欄が空だと書き出さない**（タイムラインに音声ファイルを載せただけでは`"sound_effects": {}`になり、ゲーム内では無音）。一方でEffect欄は**音声ファイルを載せるとファイル名から自動補完される**ので、名前を揃えておけば作者の手入力工程そのものが無くなり、入れ忘れが起きなくなる。名前が食い違っていると手入力が必須になり、実際にそれで無音のまま気付けない状態が繰り返し発生した。

したがって**名前を変えるときは全か所を同時に揃える**こと（作者の作業フォルダ側の音声ファイル名も含む）。

保険として、`sound_effects`キーはあるのに読めたキーフレームが0件のときは`BedrockAnimationLoader`が読み込み時にwarnログを出す（`latest.log`を「sound_effects が空です」で検索）。

**役割分担（音をどちらで鳴らすか）**:

| 音 | 経路 | 理由 |
|---|-----|-----|
| 発射音 | サーバー`playSound`（`GunProperties#fireSound`） | 周囲のプレイヤーに聞こえる必要がある |
| 空撃ち音 | サーバー`playSound` | 同上 |
| リロード中のメカ音（マガジン脱着等） | アニメーションの`sound_effects` | タイミングをモーションに合わせて作者が詰めたい |

**リロード音をサーバーの開始/完了2点で鳴らさない理由**: リロード時間（`GunProperties.reloadSeconds`）はアニメーション長と別の🟡仮バランス値で、[リロードアニメーションの時間スケーリング](#リロードアニメーションの時間スケーリング)により再生速度が伸縮する。そのため「開始と同時／完了と同時」に鳴らすとモーションと必ずズレる（glockの実測: 弾倉を外す音が0.44秒早く、挿す音が0.53秒遅い）。`sound_effects`に置けばクリップ内時刻で指定でき、再生速度の伸縮にも自動で追従する。

`sound_effects`側の音は**現状クライアントローカル＝自分にしか聞こえない**（アニメーション状態の同期経路がまだ無いため。[00-architecture.md](00-architecture.md)）。周囲にも届けるには演出用の軽量パケットが要る（後続作業）。

**発射音のキーフレームは無視される（二重再生の防止）**: 発射音はサーバーが配信するので、同じ音が`fire`クリップの`sound_effects`にも入っていると**撃った本人にだけ二重に聞こえる**。とはいえBlockbenchでモーションを詰めるときは発射音を載せてタイミングを見たいのが自然なので、消す運用にはしない。`GunAnimationSoundPlayer`が**その銃の`GunProperties#fireSound`と同じIDのキーフレームだけを鳴らさない**（Blockbench上のプレビューには影響しない）。握り潰したときは`latest.log`にdebugログが1回出る。

したがって`fire`クリップに`pistol_fire`のキーフレームが残っていても問題ない。逆に**発射音のタイミングをモーションに合わせて詰めたくなった場合は、この抑止のせいでキーフレームを動かしても何も変わらない**ので、`GunItem#tryFire`の`playSound`側で調整するか、発射音そのものをアニメーション駆動へ移す設計変更（周囲へ届ける同期パケットとセット）が必要になる。

## ADS（サイト覗き込み）

右クリック押しっぱなしで、モデルの`iron_view`ロケーターがカメラ位置へ寄っていく（＝サイトを覗いた見え方になる）。

- 入力は`ClientInputHandler`。左クリック（発射）と同じく、銃所持中はバニラの右クリック処理（`startUseItem`＝ブロック設置・アイテム使用）を`keyUse`の押下状態を毎tick落として無効化し、物理押下はGLFWから直接読む（`isPhysicallyDown`）。**副作用として銃を持っている間は右クリックでチェスト・ドアを開けなくなる**（別のアイテムに持ち替えれば通常どおり）。
- 状態は`client.anim.GunAdsState`（0=腰だめ〜1=完全にADS）。`ADS_TRANSITION_SECONDS`（🟡仮）で遷移時間を調整できる。持ち替え時は補間を挟まず0へリセットする。
- 描画は`GunItemRenderer#alignViewLocatorToAnchor`。一人称の基準ロケーターを`idle_view`→`iron_view`へ補間して、アイテム基準点（＝カメラ）に合わせる。
- **点ではなく姿勢（位置＋向き）で合わせる**。ロケーターの座標系をカメラの座標系へ一致させる（その逆変換 `R⁻¹·T(-位置)` を積む）ので、**ロケーターを回転させれば画面上の銃の向きが変わる**。位置は線形、向きは球面線形（slerp）で別々に補間する（行列のまま混ぜると途中の姿勢で回転成分が縮んで歪む）。回転は`mulPose(Quaternionf)`で積む——`Matrix4f`を直接掛けると法線行列が更新されずライティングが崩れるため。
  - これが無いと**ロケーターの回転が完全に無視される**。`idle_view`はcubeも子ボーンも持たないトップレベルのロケーターなので、回転キーを打っても他のどこにも効かず何も起きない（`reload`で`idle_view`のrotationを打って「銃を持ち上げる」表現をしようとして発覚）。
  - ⚠️ ADS側（`iron_view`）にも同じく効く。覗いている間は**サイトの向きがカメラに固定される**ので、`root`の回転（発射の反動キック等）はADS中は打ち消される。ADS中に反動を見せたい場合は`iron_view`自身にキーを打つ（`fire`クリップが実際にそうしている）。
- **rest位置ではなくアニメーション適用後の姿勢**を使う（`animatedLocatorFrame`）。`iron_view`は`root`の子で、待機・発射アニメーションが`root`を動かすぶんだけ実際のサイト位置もずれるため、rest位置で合わせるとADSしてもサイトがカメラに乗らない。`idle_view`は`root`の外（トップレベル）でアニメーショントラックも持たないため、腰だめ側の挙動は従来と変わらない。
- **リロード中はADSを無効化する**（`ClientInputHandler`）。リロードは`root`を大きく動かすモーションで、その間サイトをカメラに固定するとモーションが打ち消されて銃が空中で固まって見えるため。
- **ADS中はバニラの一人称の揺れを打ち消す**（`GunItemRenderer#cancelViewSwayForAds`）。`renderByItem`に届くPoseStackには、`applyForgeHandTransform`で止められる範囲の外側で積まれた ①`GameRenderer#bobView`（歩行・走行の揺れ。設定「視点の揺れ」ON時のみ）②`ItemInHandRenderer#renderHandsWithItems`の視点追従遅れ回転（`xBob`/`yBob`）が乗っており、覗いている間はそのままレティクルのブレになる。同じ式の逆変換をADS量ぶんだけ積んで相殺する（腰だめ＝ADS量0では何もしないので、通常時の腕の動きは残る）。被弾時の`bobHurt`はフィードバックとして残す。**バニラの実装値を参照しているので、MCバージョンを上げる際は両者の式を確認すること。**
- **持ち替え判定にItemStackの同一性比較を使わない**（`ClientInputHandler#lastHeldItem`）。発射・リロードで残弾コンポーネントが変わるとサーバーからスロット同期が来てItemStackのインスタンスが差し替わるため、同一性比較だと撃つたびに「持ち替えた」と誤判定してADSが一瞬0に落ちる（構え直しに見える）。アイテム種類＋ホットバースロットで判定する。
- **ADS中はバニラのクロスヘアを消す**（`client.GunHudOverlay.AdsCrosshair`、`RenderGuiLayerEvent.Pre`で`VanillaGuiLayers.CROSSHAIR`をキャンセル）。覗いている間はモデル側のアイアンサイトが照準になるので、画面中央のクロスヘアは重なって見づらいだけのため。覗き始めた瞬間から消え、完全に腰だめへ戻り切ったら復帰する。銃を持っていないときは何もしない。
- FOVは変えない（[02-guns.md#サイト照準仕様](../specs/02-guns.md#サイト照準仕様)「スコープを覗いても画面全体のFOVは変化しない」）。
- **未実装**: サーバーへの同期。現状ADSは見た目だけで、命中精度・移動速度・反動には影響しない。

**アセット側の注意**: **待機ポーズで`idle_view`と`iron_view`が同じ位置に来ているとADSが無効になる**（腰だめの時点でサイトがカメラに乗ったままで、覗いても銃が1mmも動かない）。読み込み時に`GunModelCache#warnIfViewLocatorsCollide`が警告を出す。

引き離し方は2通りあり、**どちらか一方**でよい:

1. **`idle_view`の pivot を腰だめ位置へ置く**（`root`の外なのでアニメーションの影響を受けない定位置になる）。`root`を中立（`[0,0,0]`）としてクリップを作っている場合はこちら。
2. **待機アニメーションの`root`に腰だめのオフセットを持たせる**。`iron_view`は`root`の子なのでそのぶんだけADS側の基準点がズレる。こちらを採る場合は**`take_out`など`root`を打っているクリップの終端も同じ値に合わせる**こと（`[0,0,0]`のままだと待機へ戻る瞬間に銃が飛ぶ）。

`iron_view`自体はサイトの照準線上（フロント/リアサイトを結んだ延長上、目の位置に相当する点）へ置く。座標はいずれも作者作業。

> 実際にあった事故: 当初は 2 の方式（`idle`の`root`が`[0, -2.825, -0.5]`）で成立していたところ、待機アニメーションを作り直して`root`を`[0,0,0]`に戻したため、2つのロケーターが重なってADSが効かなくなった。pivotを触っていなくてもアニメーション側の変更で壊れる。

⚠️ **ロケーター（`idle_view`/`iron_view`/`ground`）にアニメーショントラックを付けてはいけない。** これらは「この点をカメラ（またはドロップ中心）に一致させる」ための基準点で、コードはロケーターの位置に合わせて**モデル全体を平行移動**する。したがってロケーター自身を動かすと**意図と逆向きにモデル全体が動く**。

> 実例: `fire`クリップに `iron_view: {"position": [0, 0, -1.325]}`（サイトが後ろへ下がる反動のつもり）が入っていたため、ADS中に撃つと**銃と腕が丸ごと8cm手前へ引っ張られ、クリップが終わると瞬間復帰する**（＝「撃つと腕が一瞬後退する」）という症状になっていた。静止キーだったのでクリップ全長0.58秒ずっとズレたままだった。

反動の動きは`root`に付ける。ただし**ADS中は`root`の位置反動も打ち消される**（`iron_view`は`root`の子なので、カメラへ固定する過程で`root`の移動量が相殺されるため）。ADS中でも効く反動が必要な場合はコード側の視点キックで作る → [recoil.md](recoil.md#adsとの相互作用-)。

## アセット配置規約

```
assets/cordite/
├─ models/gun/<gunId>.geo.json
├─ animations/gun/<gunId>.animation.json
├─ textures/gun/<gunId>.png
├─ textures/effect/<name>.png ← 銃ごとではない共有エフェクト（muzzle_flash.png / tracer.png）。要アルファ付きRGBA
├─ sounds/gun/<name>.ogg      ← ファイル名はASCIIにする（日本語ファイル名は不可）
└─ sounds.json                ← サウンドイベント名 → oggファイルの対応表
```

- バニラの`models/item/`・`textures/item/`とは別の独自パスに置く（Bedrock JSONはバニラのブロック/アイテムモデルJSONと構造が別物のため）。
- 将来のgunpack構造（`gunpack/models/`・`gunpack/textures/`、[01-gunpack.md](../specs/01-gunpack.md#gunpackフォルダ構造)）への移行時は、`GunModelCache`のパス解決部分だけ差し替えれば済む構成にしてある。

### 作業フォルダからの自動同期（`syncGunAssets`）

作者はBlockbench等の**作業フォルダ**で制作し、`./gradlew runClient`（や`build`）を叩けば上記の配置へ自動でコピーされる。手作業のコピーは不要。

- 作業フォルダのパスはマシン固有なのでリポジトリには置かない。`local.properties`（`.gitignore`済み）の `cordite.assetDir` に書く（`-Pcordite.assetDir=` / 環境変数 `CORDITE_ASSET_DIR` でも可）。未設定ならタスクはスキップするので、cloneしただけの環境でもビルドできる。
- コピー規則は**拡張子と「effectフォルダに入っているか」だけ**で決まる。銃やアニメーションを増やしてもビルドスクリプトの編集は不要:

| 作業フォルダ側 | → | resources |
|---|---|---|
| `**/*.geo.json` | | `models/gun/` |
| `**/*.animation.json` | | `animations/gun/` |
| `**/*.ogg` | | `sounds/gun/` |
| `**/effect/*.png` | | `textures/effect/` |
| その他の `**/*.png` | | `textures/gun/` |

- 作業フォルダ側のフォルダ階層は畳まれ、**ファイル名だけ**が意味を持つ（整理方法は自由）。銃に依らない共有エフェクト（マズルフラッシュ等）だけは `effect` という名前のフォルダに入れること。
- 実装は `build.gradle` の `syncGunAssets` タスク（`processResources`が依存）。

### 銃・アニメーションの自動検出（登録作業は不要）

`GunModelCache`はコード側に銃やアニメーションの一覧を持たない。

- **銃**: `models/gun/<gunId>.geo.json` が置かれていれば読む（`ResourceManager#listResources`で列挙）。`<gunId>`はアイテムの登録名と一致させること。
- **アニメーション**: `animations/gun/<gunId>.animation.json` の `animations` にあるクリップを**全部**読み、キー `animation.<何か>.<名前>` の最後の区切り以降を**クリップ名**として引けるようにする（`animation.glock.reload_empty` → `"reload_empty"`）。
- したがって作者がBlockbenchでアニメーションを足す/リネームするだけで反映され、コード側の登録作業は発生しない。
- ただし**「そのクリップをいつ再生するか」はコード側の話**なので、再生されるのは`GunModelCache.Clips`に挙げた標準名だけ。それ以外の名前のクリップは読み込まれるが再生されない（無害。将来その再生を実装したら動き出す）。

| クリップ名 | 再生タイミング | 未作成のとき |
|-----------|--------------|------------|
| `idle` | 何もしていない間（先頭フレームで静止）。弾切れ中は`reload_empty`の先頭フレームに差し替わる | restポーズ |
| `take_out` | **この銃に持ち替えた瞬間に1回** | 何も再生せず即idle |
| `fire` | 発射 | 何も再生せず即idle |
| `fire_empty` | 撃ち切りの1発（任意） | `fire`を再生し、スライドの後退だけ`reload_empty`の先頭フレームで固定する |
| `reload` / `reload_empty` | リロード（実リロード時間に合わせて伸縮） | 何も再生せず即idle |
| `inspect` | **Nキー**（点検。クライアント完結） | 何も再生せず即idle |
| `inspect_empty` | 弾切れ状態でのNキー（任意） | `inspect`で代用する |
| `eject` | 発射のたびに独立して多重再生（薬莢の軌道） | 薬莢が飛ばない |

### サウンド（sounds.json）の補完

`sounds/gun/*.ogg` に対してエントリの無い音は、`generateSoundsJson`タスクが`sounds.json`へ書き足す（既存エントリは変更しない）。あわせてレジストリ登録も不要なので、**oggを置くだけでアニメーションのサウンドキーフレームが鳴る** → [音を足すのにコードを触る必要はない（登録不要）](#音を足すのにコードを触る必要はない登録不要)

## 主要クラス一覧

| クラス | 役割 |
|-------|------|
| `client.model.BedrockGeometryLoader` | `geometry.json`のパース・ベイク（座標変換込み） |
| `client.model.BedrockAnimationLoader` | `animation.json`のパース・ベイク |
| `client.model.BakedGunModel` / `GunBone` / `BakedCube` | ベイク済みモデルのデータ構造 |
| `client.model.GunModelCache` | リソースリロード時のロード・キャッシュ。銃もアニメーションも**アセットの有無から自動検出**する（コード側に一覧を持たない・nullセーフ） |
| `client.anim.BakedAnimation` / `BoneTrack` / `Keyframe` / `SoundKeyframe` | ベイク済みアニメーションのデータ構造 |
| `client.anim.AnimationSampler` | 指定時刻でのボーン差分（position/rotation/scale）を線形補間でサンプリング（全ボーン／1ボーンのみ／**待機を土台にした重ね合わせ**） |
| `client.anim.ShellEjectionTracker` | 飛行中の薬莢インスタンス（発射クリップとは独立したタイムライン）の保持・破棄 |
| `client.anim.MuzzleFlashState` | マズルフラッシュの表示時間・毎発のランダム（ロール角/大きさ）の保持 |
| `client.anim.GunAnimationState` | ローカルプレイヤー1人分の再生状態（`Action.TAKE_OUT`/`FIRE`/`FIRE_EMPTY`/`RELOAD`/`RELOAD_EMPTY`/`INSPECT`/`INSPECT_EMPTY`、無ければ待機にフォールバック） |
| `client.anim.GunActionPlayback` | 再生中クリップとクリップ内時刻の算出（描画とサウンドで共用。時間スケーリング・終了判定込み） |
| `client.anim.GunAnimationSoundPlayer` | `sound_effects`キーフレームの再生（effect名→SoundEvent解決、クライアントローカル） |
| `client.anim.GunAdsState` | ADS（右クリック覗き込み）の0〜1補間状態 |
| `client.anim.ClientGunAnimationTracker` | アニメーション状態の毎tick進行（終了判定＋サウンドキーフレーム）|
| `registry.ModSounds` | サウンドイベント登録。**サーバーから配信する音（発射音）だけ**必要。アニメーションの`sound_effects`から鳴らす音は登録不要 |
| `client.ClientInputHandler` | （既存）Rキー押下時のreload発火判定に加え、Nキーの点検・右クリックのADS入力・バニラ左右クリック抑制 |
| `client.render.GunItemRenderer` | BEWLR本体。ボーン階層歩行・頂点描画・配置（基準点合わせ、ロケーター、ハンドアンカー腕） |
| `client.render.GunClientExtensions` | `RegisterClientExtensionsEvent`での登録 |

## 後続作業

- `iron_view`をサイトの照準線上へ移動（現状は`idle_view`と同一座標のため、ADSしても見た目が変わらない）（作者作業）
- `thirdperson_hand`/`fixed`ロケーターの作成と反映（モデル側に未作成）
- ADSのゲームプレイ側効果（命中精度・移動速度・反動）とサーバー同期
- worldmodel（三人称）実装・他プレイヤーへのアニメーション状態同期（`sound_effects`の音を周囲へ届けるのもこの経路）
- リロード検知の専用ペイロード方式への切替（サーバー拒否とのズレ・reload/reload_empty取り違えの解消。発射側は`GunFiredPayload`で対応済み）
- `reload_empty`の0秒目にスライド／チャージングハンドルの後退キーを打つ（作者作業。これが弾切れ待機の見た目になる。打つまでは通常idleと同じ見た目になるだけで壊れない）
- `fire_empty`（撃ち切りの1発。スライドが後退→前進→後退と動く様子まで作り込みたい場合のみ。作らなくても`fire`＋スライド固定で成立する）
- 持ち替え直後の発射クールダウン（サーバー側。現状は`take_out`再生中でも撃てる）
- しまうモーション（`put_away`）。持ち替え前の銃で再生するには、切り替えを1クリップぶん遅延させる仕組みが要る
- gunpackからの動的ロードへの移行（`GunModelCache`のパス解決を`assets/cordite/`から`gunpack/`へ差し替え）
- `sound_effects`の音を周囲のプレイヤーにも届ける演出用パケット（現状はクライアントローカル）
- `particle_effects`のパース（マズルフラッシュ等。`sound_effects`と同じ経路で実装できる）
- 銃ごとの発射音アセット（現状ak47/m4a1は`pistol_fire`を流用）
- モデル側のボーン名統一（`magazine`/`chamber`統合等）（作者作業）
- 飛行中の薬莢を`root`の動きから切り離す（発射時のポーズをスナップショット／ワールド空間の放物線化）。現状は銃本体に引きずられる
- マズルフラッシュを銃ごとのテクスチャにできるようにする（現状は共有1枚）
- マズルフラッシュを他プレイヤーの銃にも表示する（worldmodel＋状態同期とセット。現状は一人称のみ）
- マズルフラッシュによる周囲の一時的な照明（現状は板が光るだけで周りは明るくならない）

## 動作確認

`./gradlew runClient` → クリエイティブタブ「Cordite」からglockを取得:
1. 一人称視点で構えるとテクスチャ付きでモデルが表示される（ミッシングテクスチャにならない）。GUI（インベントリ）・地面ドロップ・アイテムフレームでもクラッシュせず何かしら表示される。
2. 何もしていない間はidleの構えポーズになる。
3. 左クリック発射時、既存の曳光弾・HUD残弾減少（[firing.md](firing.md)記載の既存動作）に加えて`barrel`（後退+わずかな回転）・`bolt`（後退→前進のスライドサイクル）・`trigger`（引き込み）が0.5833秒のモーションで動き、終わるとidleに戻る。発射音として`cordite:pistol_fire`（作者制作のogg。サーバー側の`playSound`で鳴る）が鳴る。
   - **薬莢が右上へ排出され、連射しても途中で消えたり銃の中へ戻ったりしない**（最速の連打で複数個が同時に飛ぶ）。単発でも軌道の終点で空中静止せず、飛び切ったところで消える。リロード中は薬莢が飛ばない。
   - `muzzle_flash`ロケーターを置いてあれば、銃口で一瞬光る。**暗い場所（洞窟・夜）でもフラッシュが明るいまま**で、板の四角い縁が見えない（テクスチャのアルファが効いている）。視点を動かしても常にこちらを向き、連射すると毎発向きと大きさが変わる。
   - クロスヘアが跳ね上がってじわっと戻る（→ [recoil.md](recoil.md#動作確認)）。
4. `R`でリロード: 薬室に弾が残っている状態では`reload`、残弾ゼロ（空撃ち後）では`reload_empty`が再生され、実際のリロード完了（`GunProperties.reloadSeconds`、Glockは1.8秒）に合わせて速度が伸縮する。リロード中にfireアニメーションが誤発火しない。マガジン内の弾（`mag_ammo`）がマガジンを抜くタイミングで消え、挿し直すタイミングで戻る（`scale`トラック）。
5. `animation.json`の`sound_effects`にEffect名を入れてあれば、そのタイミングでマガジン脱着音が鳴り、モーションとズレない（Effect名が空だとBlockbenchが書き出さないため無音になる）。
6. 右クリック押しっぱなしでADSになり、`iron_view`の位置がカメラへ寄る（`iron_view`を`idle_view`と別座標に置いてあること）。離すと腰だめへ戻る。リロード中は右クリックしてもADSにならない。銃を持っている間は右クリックでブロックを置いたりチェストを開いたりしない。
   - **撃ちながら構え続けても構えが解けない**（残弾同期で持ち替え誤検出しない）。
   - **構えたまま歩く/走る/視点を振ってもサイトがブレない**。構えていない間は従来どおり腕が揺れる。
   - **構えている間はバニラのクロスヘアが消える**。腰だめに戻すと復帰する。銃以外を持っているときは常に出る。
7. 一人称でバニラのプレイヤー腕が**左右1本ずつ**描画され、モデル側の`right_hand`/`left_hand`の箱の位置と重なる。アニメーション中も箱に追従して動く。三人称・GUI・地面ドロップでは腕が出ない。
8. 銃を捨てるとアイテムが地面に埋まらず、`ground`ボーンの位置を基準に表示される。
9. 撃ち切ると空撃ち音が鳴らず（Glockは`holdOpenOnEmpty=true`）、クロスヘア下に弾切れ表示が出る。`reload_empty`の0秒目に後退キーを打ってあれば、弾切れの間スライド／チャージングハンドルが後退したまま保持され、そのままの姿勢からリロードが始まり、完了で通常のidleに戻る。左クリック押しっぱなしでも空撃ち音が連打されない。
10. ak47/m4a1（モデル未実装）に持ち替えてもクラッシュしない。glockに戻すと表示が復帰する。
11. F3+Tのリソースリロードでクラッシュしない。
