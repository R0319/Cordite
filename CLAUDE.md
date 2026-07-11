# Cordite — 開発ガイド

Minecraft **NeoForge 1.21.1** の銃PvP Mod。パッケージ: `net.r0319.cordite`。

## 最初に読む

仕様は `docs/specs/` に分割されている。**まず [docs/specs/README.md](docs/specs/README.md) を読み、必要な領域のファイルだけ開く**（全ファイルの丸読みは避ける）。

| 領域 | ファイル |
|-----|---------|
| gunpackシステム | `docs/specs/01-gunpack.md` |
| 銃仕様・数値 | `docs/specs/02-guns.md` |
| アイテム/防具 | `docs/specs/03-items.md` |
| 敵 | `docs/specs/04-enemies.md` |
| 建物生成 | `docs/specs/05-structures.md` |
| アニメーション | `docs/specs/06-animations.md` |
| モデル/テクスチャ | `docs/specs/07-model-assets.md` |
| 的NPC/射撃ターゲット | `docs/specs/08-training-targets.md` |
| NPC分類/PMC | `docs/specs/09-npc.md` |

**技術設計（どう作るか＝How）は別**: `docs/design/00-architecture.md`（骨組み）。機能別の詳細設計は実装直前に `docs/design/<feature>.md` を1枚ずつ書く。

## 前提・ルール

- **ユーザーとのやり取り（説明・コミット文・ドキュメント）は日本語で行う。**
- 仕様の数値はすべて **🟡 仮値**（後でバランス調整する）。実装は仮値で進めてよいが最終値ではない。
- ステータスタグ（✅確定 / 🟡仮 / 🔵検討中 / ⬜未定）を尊重し、✅以外を確定値として扱わない。
- **作者（ユーザー）が手作業で制作し、Claudeは生成・レビューしない領域**:
  - 3Dモデル・テクスチャ（`07-model-assets.md`）
  - アニメーションのモーションデータ（`06-animations.md`）
  - → Claudeが担当するのは「それらを読み込む/再生する側のコード」まで。
- 実装前に既存コードを確認し、サーバー権威（ダメージ判定はサーバー側で検証）を守る。

## サブエージェント（`.claude/agents/`）

- `mc-researcher` — 実装前の既存コード/NeoForge API調査
- `mc-reviewer` — 武器/ダメージ/同期/パケット変更後のレビュー
- `mc-spec-tester` — `docs/specs/` とコードの静的な突き合わせ
- `mc-log-analyzer` — クラッシュログ/スタックトレース解析

## ビルド

- `./gradlew build` / 実行は `./gradlew runClient`（Windowsは `gradlew.bat`）
