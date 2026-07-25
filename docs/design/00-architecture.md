# 00. アーキテクチャ（骨組み）🟡 仮

> **範囲**: 「どう作るか(How)」の土台だけ。**機能別の詳細設計は実装する直前に `docs/design/<feature>.md` を1枚ずつ書く**（全部を先に設計しない）。
> 「何を作るか(What)」は [../specs/README.md](../specs/README.md)。
> 対象: NeoForge **1.21.1** / パッケージ `net.r0319.cordite`。

## 設計原則

- **サーバー権威**: ダメージ・命中・弾数・耐久・クールダウンはすべてサーバーが真実を持つ。クライアントは入力送信と表示のみ。
- **データ駆動**: 銃・アタッチメントは gunpack の JSON から読む（[../specs/01-gunpack.md](../specs/01-gunpack.md)）。ハードコードしない。
- **アセットは作者制作**: モデル/テクスチャ/アニメーションはコード外（[../specs/07-model-assets.md](../specs/07-model-assets.md) / [../specs/06-animations.md](../specs/06-animations.md)）。コードは「読み込む/再生する側」だけ。

## パッケージ構成（仮）

```
net.r0319.cordite
├─ registry     DeferredRegister 一式（Items, Entities, DataComponents, Sounds, CreativeTabs）
├─ item.gun     GunItem ほか銃アイテム
├─ item.armor   防具アイテム
├─ entity       弾丸・敵・的NPC などのエンティティ
├─ combat       ダメージ計算・レイキャスト/弾道・近接システム
├─ gunpack      JSON定義のロード（GunDefinition / AttachmentDefinition / RailDefinition）とリロードリスナー
├─ network      Payload（発射リクエスト・エフェクト同期・状態同期）
├─ client       レンダリング・HUD・アニメ再生・キー入力（DistExecutor / @Mod dist=CLIENT）
└─ config       Config（既存）
```

## レジストリ（NeoForge 1.21.1）

- `DeferredRegister` / `DeferredRegister.Items` / `DeferredRegister.DataComponents` を使用
- 登録するもの: アイテム（銃・防具・弾薬・機関部・設置物）、エンティティ（弾丸・敵・的NPC）、データコンポーネント、サウンド、クリエイティブタブ

## 銃の状態保持：データコンポーネント（1.21で NBT から移行）🟡

銃の可変状態は **Data Component** で持つ（`ItemStack` に付与）。案:

| コンポーネント | 内容 |
|--------------|------|
| `magazine_ammo` | 現在のマガジン残弾（int） |
| `chambered` | 薬室に弾があるか（bool） |
| `attachments` | 装着中アタッチメントID + レール位置（map） |
| `durability_state` | 耐久値（int。しきい値は [../specs/02-guns.md](../specs/02-guns.md#耐久劣化しきい値仮)） |

- 銃ID・基礎性能など**不変値は gunpack 定義側**（コンポーネントには入れない）。

## ネットワーキング：発射フロー（サーバー権威）🟡

NeoForge 1.21 の Payload（`CustomPacketPayload` + `StreamCodec` + `Type`、`RegisterPayloadHandlersEvent` で登録）を使う。

**採用方式（実装済み）**: 発射1回ごとのリクエストではなく、**トリガー押下状態のみを送り、発射はサーバーtickで駆動する**。

```
Client 入力（左クリックの押下/離しエッジ）
  → [C→S] SetTriggerPayload（bool のみ。状態変化時だけ送信）
      ↓ サーバーの PlayerTickEvent で毎tick駆動:
        - 発射モード（単発/フルオート/バースト）に応じて発射判定
        - 前回発射tick と 連射レートでクールダウン判定（改造連射を無効化）
        - マガジン残弾 / 薬室 チェック
        - 弾道シミュレート（下記）→ 命中判定 → ダメージ適用
      ↓
  発射音・トレーサーはサーバーから playSound / sendParticles で周囲へ配信
  （専用のエフェクト同期パケットは持たない）
  残弾・発射モードは ItemStack のデータコンポーネント同期で伝わる
```

- 詳細は [firing.md](firing.md) を参照（本ファイルは骨組みのみ）。
- **アンチチート**: サーバーが「最終発射tick」「残弾」を保持。規定間隔より速い要求は破棄。ダメージ量もサーバーが算出（クライアント値を信用しない）。トリガー状態パケットは bool のみで、発射数・ダメージ・方向をクライアントに申告させない。

## ヒット方式：弾道シミュレート 🟡

- 仕様に**弾速（blocks/秒）**があるため（[../specs/02-guns.md](../specs/02-guns.md#武器別ステータス仮)）、純ヒットスキャンではなく**飛翔体（travel timeあり）**を採用。
- **決定済み**: 「サーバー側の軽量弾丸トラッカー」（Entityを使わずtickで前進＆レイキャスト）を採用・実装済み（`combat/GunProjectile` / `combat/ProjectileManager`、[firing.md](firing.md) 参照）。大量発射時のパフォーマンス（[../specs/02-guns.md](../specs/02-guns.md) のLMG等）のため弾丸Entityは使わない。
- ショットガンは1発で複数ペレット分の弾道。

## クライアント表示

- 銃・アタッチメントのレンダリング（gunpackモデル + レール座標でアタッチメント配置）
- HUD: 残弾・耐久・レティクル（PiP/疑似ズーム → [../specs/02-guns.md](../specs/02-guns.md#サイト照準仕様)）
- アニメ再生はコードが担当（モーションデータは作者制作）

## 未決定（実装時に個別設計）

- gunpack 定義のサーバー→クライアント同期方式（参加時／リロード時）
- 近接システムの判定方式（[../specs/04-enemies.md](../specs/04-enemies.md#近接システム)）
- 的NPC・敵AIの実装（[../specs/08-training-targets.md](../specs/08-training-targets.md) / [../specs/04-enemies.md](../specs/04-enemies.md)）
- アニメーション再生システム: 方向性は決定済み（外部ライブラリ不使用・Bedrock Edition形式(`geometry.json`+`animation.json`)を自前パース＋軽量補間、viewmodel/worldmodel分離、[../specs/06-animations.md](../specs/06-animations.md#アニメーション作成方式-仮)）。パース方式・補間アルゴリズム・状態遷移の詳細設計は実装直前に `docs/design/animation-system.md` を書く
- **アニメーション状態のネットワーク同期方式（未定・後日検討）**: リロード中/ADS中等の状態を周囲プレイヤーにどう伝えるか。上記アニメーション再生システムの設計時にあわせて決定する

## 関連

- 仕様全体 → [../specs/README.md](../specs/README.md)
- 機能別設計（今後追加）→ `docs/design/<feature>.md`
