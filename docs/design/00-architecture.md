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

```
Client 入力（射撃キー）
  → [C→S] FireRequestPayload（照準方向 or トリガーのみ）
      ↓ サーバー検証:
        - 前回発射tick と 連射レートでクールダウン判定（改造連射を無効化）
        - マガジン残弾 / 薬室 / 耐久 チェック
        - 弾道シミュレート（下記）→ 命中判定 → ダメージ適用
      ↓
  ← [S→C] ShotEffectPayload（周囲クライアントへ: マズルフラッシュ/発射音/トレーサー）
  ← [S→C] 状態同期（残弾など。ItemStack同期で足りる場合は不要）
```

- **アンチチート**: サーバーが「最終発射tick」「残弾」を保持。規定間隔より速い要求は破棄。ダメージ量もサーバーが算出（クライアント値を信用しない）。

## ヒット方式：弾道シミュレート 🟡

- 仕様に**弾速（blocks/秒）**があるため（[../specs/02-guns.md](../specs/02-guns.md#武器別ステータス仮)）、純ヒットスキャンではなく**飛翔体（travel timeあり）**を採用。
- 実装は「弾丸Entity」か「サーバー側の軽量弾丸トラッカー（Entityを使わずtickで前進＆レイキャスト）」を検討。大量発射時のパフォーマンス（[../specs/02-guns.md] のLMG等）を考慮して後者寄りで詳細設計する。
- ショットガンは1発で複数ペレット分の弾道。

## クライアント表示

- 銃・アタッチメントのレンダリング（gunpackモデル + レール座標でアタッチメント配置）
- HUD: 残弾・耐久・レティクル（PiP/疑似ズーム → [../specs/02-guns.md](../specs/02-guns.md#サイト照準仕様)）
- アニメ再生はコードが担当（モーションデータは作者制作）

## 未決定（実装時に個別設計）

- 弾道: 弾丸Entity か 軽量トラッカーか
- gunpack 定義のサーバー→クライアント同期方式（参加時／リロード時）
- 近接システムの判定方式（[../specs/04-enemies.md](../specs/04-enemies.md#近接システム)）
- 的NPC・敵AIの実装（[../specs/08-training-targets.md](../specs/08-training-targets.md) / [../specs/04-enemies.md](../specs/04-enemies.md)）
- アニメーション再生システム（[../specs/06-animations.md](../specs/06-animations.md) 確定後）

## 関連

- 仕様全体 → [../specs/README.md](../specs/README.md)
- 機能別設計（今後追加）→ `docs/design/<feature>.md`
