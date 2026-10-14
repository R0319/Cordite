# firing — 発射システム 🟡 仮

> **範囲**: 銃の発射・発射モード・入力・弾丸・薬室/ボルト・HUD。仕様は [../specs/02-guns.md](../specs/02-guns.md)、骨組みは [00-architecture.md](00-architecture.md)。

## 操作

| 操作 | 入力（既定） |
|-----|------|
| 発射 | 左クリック（押している間） |
| 発射モード切替 | `V` |
| リロード | `R` |
| （予約）ADS/構え | 右クリック ※将来実装 |

## 独自射撃システム（バニラ使用状態を使わない）

バニラの「アイテム使用（`startUsingItem`/`onUseTick`）」は使わない。理由: 雪玉・食べ物のようなアイテムの浮き沈みモーションが出る／将来のADS・構え・リロードモーション等の独自動作の妨げになるため。

**入力→発射の流れ:**

```
クライアント（ClientInputHandler, ClientTickEvent）
  左クリック押下状態を監視
    → [C→S] SetTriggerPayload(pressed)  ※状態変化時のみ送信
  銃所持中は左クリックのバニラ挙動を抑制:
    - InputEvent.InteractionKeyMappingTriggered(isAttack) を cancel（近接攻撃・破壊開始）
    - PlayerInteractEvent.LeftClickBlock を cancel（長押し破壊の再開始）
        ↓
サーバー（GunServerEvents, PlayerTickEvent.Post）
  triggerHeld と発射モードで毎tick発射判定:
    - SINGLE   : 押下エッジで1発（firedThisPress で二重発射防止）
    - FULL_AUTO: レートが許す限り連射
    - BURST    : 押下エッジで3発ぶん開始し、レートで消化
        ↓
  GunItem.tryFire(): レート/リロード/残弾を検証 → 薬室/ボルト消費 → ProjectileManager.fire()
```

- **サーバー権威**: ダメージ・残弾・レート・リロードはすべてサーバー側で確定。クライアントは入力送信と表示のみ。
- **クールタイムバー非表示**: バニラ `ItemCooldowns` を使わず `GunFireManager` がゲームtick差分でレート制御。
- モード切替／リロードも C→S パケット（`CycleFireModePayload` / `ReloadPayload`）。

## 発射モード（実銃準拠）

`FireMode` = SINGLE / FULL_AUTO / BURST。対応モードは銃ごとに gunpack 定義 `GunDefinition.fireModes`（先頭が既定）。

| 銃 | 対応モード | rpm(実銃準拠) | ボルト |
|----|----------|---------------|-------|
| Glock | 単発 | 400（セミオート速射上限） | クローズド |
| AK-47 | 単発 / フルオート | 600（サイクリックレート） | クローズド |
| M4A1 | 単発 / フルオート / バースト | 800（サイクリックレート） | クローズド |

- `rpm` はフルオート機のサイクリックレート、単発機は速射上限。発射間隔 = `1200 / rpm` tick（**小数のまま扱う**）。
- 間隔を整数tickに丸めない: 800rpm = 1.5tick を 2tick に丸めると実効 600rpm に落ちる。`GunFireManager.State#nextShotTick`（double）に
  間隔を積み上げ、`now >= nextShotTick` で許可する。1.5tick なら 2tick・1tick 空きを交互に繰り返し、平均で定義どおりになる。
  しばらく撃っていなければ現在tickを起点にし直す（過去の許可時刻から積むと連射の「貯金」ができてしまうため）。
- バーストは `FireMode.BURST_COUNT`（=3）発。

## 薬室（チャンバー）とボルト方式

`GunDefinition.boltType`（`BoltType.CLOSED` / `OPEN`）で挙動を分ける。状態は `chambered`（bool）Data Component。

| ボルト方式 | 満タン装弾数 | 挙動 |
|-----------|------------|------|
| クローズド | マガジン容量 + 薬室1発（例 31） | 発射で薬室弾を消費→マガジンに弾があれば次弾を薬室へ自動サイクル。撃ち切ると薬室も空 |
| オープン | マガジン容量ちょうど | 薬室待機なし。マガジンから直接消費 |

**リロード（クローズドのみ差が出る）:**
- 薬室に弾を残してリロード（タクティカル）→ 合計 = マガジン容量 + 1（例 31）
- 撃ち切ってリロード → ボルトリリースで薬室に1発送るため合計 = マガジン容量ちょうど（例 30）

- 現状の3銃はすべてクローズドボルト。オープンボルト機（一部LMG/SMG等）は今後 `BoltType.OPEN` で追加。

## 弾丸（飛翔体）

Entityを使わない軽量トラッカー方式（`combat.GunProjectile` / `ProjectileManager`）。

- サーバーtickごとに `muzzleVelocity/20` blocks 前進し、移動区間を `clip`（ブロック）でレイキャストし、ブロックに遮られた手前までの区間でエンティティ命中を判定する。区間判定なので高速弾でもすり抜けない。
- エンティティ命中は**自前判定**（`GunProjectile#findEntityHit`）: 区間周辺のエンティティを `level.getEntities` で集め、各バウンディングボックスを `ENTITY_HIT_INFLATE`（🟡仮 0.3）膨らませて `AABB.clip` で交点を取り、始点に最も近いものを採る。バニラの `ProjectileUtil.getEntityHitResult`（6引数版）は**交点を持たない結果**（`getLocation()` が足元座標）を返すため使わない——部位判定が常に手足になる。
- 曳光弾は見た目だけで、発射時に `TracerPayload` を1発1パケット配りクライアントが描く（[tracer.md](tracer.md)）。
- 命中でダメージ（距離係数＋部位倍率）を適用し消滅。射程 `effectiveRange` 到達でも消滅。
- 連射で命中が無効化されないよう、命中対象の `invulnerableTime` を毎発リセット。
- `ServerTickEvent.Post` で全弾を前進、`ServerStoppingEvent` でクリア。

### ダメージ計算（docs/specs/02-guns.md）

```
命中ダメージ = 基礎ダメージ × 距離係数 × 部位倍率
```
- 距離係数: 減衰開始まで1.0 → 有効射程で0.5へ線形低下 → 超過0.5。
- 部位倍率（仮）: 頭2.0 / 胴1.0 / 手足0.75（**実際の交点**のY座標と対象の身長比で判定。85%以上=頭 / 35%以下=手足）。
- 防具軽減は後続。

## HUD

`client.GunHudOverlay`（`RegisterGuiLayersEvent`）。銃所持時に画面右下へ表示:
- 残弾: **薬室込みの合計 / 合計容量**（例 `31 / 31`、残弾0は赤）
- 発射モードのラベル（`SINGLE` / `AUTO` / `BURST`）

## 状態（Data Component / networkSynchronized）

| コンポーネント | 型 | 内容 | 既定 |
|--------------|----|------|------|
| `magazine_ammo` | int | マガジン残弾（薬室を含まない） | magSize |
| `chambered` | bool | 薬室に弾があるか（オープンは常に空扱い） | true |
| `fire_mode` | int | 現在の発射モード（`FireMode.ordinal()`） | 銃の既定 |

## 主要クラス一覧

| クラス | 役割 |
|-------|------|
| `item.gun.GunItem` | 銃アイテム。`tryFire`/`completeReload`/`cycleFireMode`/`startReload` |
| `gunpack.GunDefinition` | 不変ステータス（gunpack JSON から読む → [gunpack.md](gunpack.md)） |
| `item.gun.FireMode` / `BoltType` | 発射モード／ボルト方式の列挙 |
| `combat.GunFireManager` | プレイヤー別の過渡状態（トリガー/レート/バースト/リロード） |
| `combat.GunProjectile` / `ProjectileManager` | 弾丸トラッカーと一括tick |
| `network.SetTriggerPayload` / `CycleFireModePayload` / `ReloadPayload` | C→Sパケット |
| `network.ModNetwork` | パケット登録・ハンドラ |
| `event.GunServerEvents` | 発射駆動・リロード完了・弾丸tick・状態クリア |
| `client.ClientInputHandler` | 左クリック監視・トリガー送信・バニラ入力抑制 |
| `client.ModKeyMappings` / `GunHudOverlay` | キーバインド／右下HUD |

## 後続作業

- ADS(構え)本体・発射/リロード/構えの独自アニメーション再生（今回は入力側の土台のみ）
- 弾道ドロップ（重力）・貫通・跳弾、専用トレイル/着弾/マズルフラッシュのアセット化
- ボルトアクション／ポンプ等の手動サイクル・1発ずつ装填（ショットガン）
- リロード中のHUD/演出、耐久劣化・ジャム、アタッチメント、防具軽減
- 銃専用の `DamageType`（現状はバニラの `playerAttack` を流用しており、バニラ防具の軽減・毎発ノックバック・「〜に殺された」死亡メッセージがそのまま乗る）
- 有効射程を超えた弾の扱い（仕様は「射程超過後は距離係数 0.5 固定」だが、現状は有効射程到達で弾が消える＝最大到達距離=有効射程）

## 動作確認

`./gradlew runClient` → クリエイティブタブ「Cordite」から銃を取得:
1. 左クリックで発射・曳光弾の弾道・エンティティへのダメージ（ブロックは壊れない）。
2. `V`でモード切替（SINGLE/AUTO/BURST）、`R`でリロード。
3. アイテムの浮き沈みモーションが出ない。
4. 右下HUDが合計表示（例 `31 / 31` → 撃つと減る）。
