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
  - **見た目・配置の数値調整**（一人称の位置/回転/拡大率、カメラ・ロケーター座標、アイテムアイコンのサイズ等のレンダリング配置定数）
  - → Claudeが担当するのは「それらを読み込む/再生する側のコード」と「調整しやすい定数として切り出すところ」まで。
  - **Claudeはゲーム画面を直接確認できないため、見た目に関わる数値をあてずっぽうで決め打ち・繰り返し調整することはしない。** 実機（`runClient`）で見た目を確認しながらの数値決定・チューニングは作者が行う。Claude側で明らかにおかしい値（画面外に出る等の構造的ミス）に気付いた場合は指摘・修正してよいが、見た目の良し悪しの調整は無理に自分で完結させようとせず、作者に委ねる。
- ローカル環境固有の情報（モデル作業フォルダの絶対パス等、GitHubに上げたくないもの）は `CLAUDE.local.md`（git管理外、`.gitignore`済み）を参照。無ければ作者に確認する。
- **アセットの取り込みは自動化済み**（`syncGunAssets` Gradleタスク＋`GunModelCache`の自動検出）。作者が作業フォルダで保存して `runClient` すれば反映されるので、**モデル/アニメーション/テクスチャの追加・更新でClaudeがコピーや登録を行う必要はない** → [docs/design/animation-system.md](docs/design/animation-system.md#作業フォルダからの自動同期syncgunassets)
- 実装前に既存コードを確認し、サーバー権威（ダメージ判定はサーバー側で検証）を守る。
- ユーザーが実装指示を出している案を一度他に良い改善案がないか思案してから実装に移ること。

## 役割分担: コーディングは Codex に任せる

**このプロジェクトでは実装（コーディング）を Codex CLI に委譲する。**

| 担当 | 範囲 |
|-----|------|
| **Claude** | 仕様書・設計書（`docs/`）の作成、調査、エラー/クラッシュ解析、レビュー、ビルド実行、差分確認 |
| **Codex** | 設計書に沿ったコードの実装（Java・リソースファイル） |
| **作者** | 3Dモデル/テクスチャ/アニメーション制作、見た目の数値調整、実機確認 |

Codex 向けのプロジェクト規約は **[AGENTS.md](AGENTS.md)**（Codex が自動で読む）。日本語で書く・
サーバー権威・アセット非改変・コミット禁止などを明記してある。**内容を変えたら AGENTS.md 側も更新すること。**

### 手順

1. **Claude が設計書を書く** → `docs/design/<feature>.md`。実装判断が必要な点は設計書側で決着させる。
2. **Claude が作業指示書を書く** → リポジトリ直下の `codex-task.md`（`.gitignore` 済みの使い捨て）。
   - 作業範囲を明示的に区切る（「Step 1〜6 のみ」「このファイルには触るな」）
   - 参照すべき既存ファイル・踏襲すべき書式を指定する
   - 「最終メッセージに、変更ファイル一覧と確信の持てなかった箇所を日本語で書け」と指示する
3. **Codex を呼ぶ**（下記）。プロンプトは短く、`codex-task.md` を読ませる形にする＝トークン節約。
4. **Claude が `git diff` で差分確認 → `gradlew build` → エラーがあれば解析し、修正指示を `codex-task.md` に書いて 3 へ戻る。**

### Codex の呼び出し方

**MCP 経由（確立済み・これを使う）**: `.mcp.json` に登録済み
（`claude mcp add --transport stdio --scope project codex -- codex mcp-server`）。
MCP サーバーはセッション開始時に読み込まれるので、登録を変えたら Claude Code の再起動が必要。

Claude からは `mcp__codex__codex` ツールを次のパラメータで呼ぶ:

| パラメータ | 値 |
|-----------|---|
| `prompt` | `codex-task.md を読み、その指示に従って実装してください。` |
| `cwd` | リポジトリのルート |
| `sandbox` | **`danger-full-access`**（下記の理由により必須） |
| `approval-policy` | `never` |

**⚠ Windows 固有の確定事項**: この環境では **Codex のサンドボックスが一切起動できない**
（`CreateProcessAsUserW failed` / `Windows error 5`）。`~/.codex/config.toml` の
`[windows] sandbox` が対話ユーザーのトークンを要求するためで、`elevated` / `unelevated` の両方、
かつ `codex exec` 直叩き・MCP 経由の**どちらでも失敗する**（検証済み）。
`windows.sandbox` に `none` は存在しない。したがって **`danger-full-access` が唯一動く設定**。

サンドボックス無しで動く以上、歯止めは以下で担保する:
- `AGENTS.md` — コミット禁止・アセット非改変・見た目の数値非改変
- `codex-task.md` — 作業範囲を明示的に区切る（「Step 7 のみ」「このファイルには触るな」）
- **Claude が毎回 `git diff` で差分を確認し、`gradlew compileJava` を回す**
- 大きな変更の前に作業ツリーをコミットしておく（未コミットの作業は git の保護外）

### Codex が今何をしているかを見る

MCP の戻り値は **Codex の最終メッセージだけ**で、途中のコマンド・思考は含まれない。
また120秒を超える呼び出しはバックグラウンドタスクへ退避されるため、インライン表示もされない。
実行中の様子は**セッションログ**（`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`、逐次書き込み）を読む:

```powershell
.\codex-watch.ps1            # 直近セッションの最後30件
.\codex-watch.ps1 -Follow    # 実行中をリアルタイム追跡
```

（`codex-watch.ps1` は `.gitignore` 済み。python/jq がこの環境に無いため PowerShell で実装してある）

`codex exec`（CLI直叩き）を使う場合は非対話モードで、`-o <file>` に最終メッセージだけを出し、
それ以外は `*> log.txt` へ捨てるとトークンを節約できる。`-a/--ask-for-approval` は `exec` では使えない。

## スキル（`.claude/skills/`）— よくある作業の手順書

作業の入口が下表のどれかに当たるときは、**まず該当スキルを読んでから動く**（手順の抜けを防ぐため）。

| スキル | いつ使うか |
|-------|-----------|
| `asset-apply` | 「アニメ/テクスチャ/モデル/効果音を更新した、反映して」— 検証→ビルド→確認リスト |
| `ingame-triage` | 実機確認で見つけた不具合の報告 — 症状の切り分けと担当（コード/アセット/作者）の判定 |
| `codex-impl` | コードを実装・修正する必要が出たとき — `codex-task.md` からビルド確認までの委譲手順 |
| `build-check` | 「ビルドして」「エラー出てる」— 禁止事項と既知エラー対処表 |
| `commit-push` | 「コミットして」— 分割・日本語メッセージ・混入チェック・プッシュまで |

ユーザーレベル（`~/.claude/skills/`、リポジトリ外）に第三者製の `minecraft-neoforge` を導入済み。
NeoForge 1.21 の API（DataComponent / CustomPacketPayload / DataAttachment / datagen / AT）を
確認するときの**リファレンス専用**。実装の進め方はこのリポジトリの規約が優先する。

## サブエージェント（`.claude/agents/`）

- `mc-researcher` — 実装前の既存コード/NeoForge API調査
- `mc-reviewer` — 武器/ダメージ/同期/パケット変更後のレビュー
- `mc-spec-tester` — `docs/specs/`（仕様・数値）とコードの静的な突き合わせ
- `mc-doc-sync` — `docs/design/`（技術設計）とコードのズレ、`CLAUDE.md`/`AGENTS.md` の追従漏れ
- `mc-log-analyzer` — クラッシュログ/スタックトレース解析
- `mc-asset-validator` — `.geo.json`/`.animation.json`/`.ogg`/`.png` が「コードが拾える形」かの静的検証

## ビルド

- `./gradlew build` / 実行は `./gradlew runClient`（Windowsは `gradlew.bat`）
- **実機確認の前に `clean` を使わない。** `build/moddev/` の実行用ファイル（`clientRunVmArgs.txt` 等）が
  消え、設定キャッシュが「最新」と誤判定して再生成されず `runClient` が失敗する。
  消してしまったら `./gradlew prepareClientRun` で作り直す。
- ビルドの成否を `./gradlew ... | tail` のようなパイプで判定しない。**パイプの終了コードは最後のコマンドの
  ものになり、Gradleの失敗が隠れる。** `${PIPESTATUS[0]}` を見るか、`BUILD SUCCESSFUL` の有無で判定する。

## Git / GitHub

- **コミットしたら、そのまま GitHub（`origin`）へプッシュする。** バックアップを兼ねているため、
  ローカルにだけコミットして止めない。作業ブランチは `dev`。
- コミット・プッシュは**作者の指示があったときに行う**（勝手にコミットしない）。指示されたら
  コミットとプッシュはセットで最後まで済ませる。
- プッシュ前に、追跡ファイルへローカル固有情報（絶対パス・ユーザー名等）が混ざっていないか確認する。
  そうした情報は `CLAUDE.local.md` / `local.properties`（どちらも `.gitignore` 済み）に置く。
- コミットメッセージは日本語。「何を」だけでなく**「なぜそうしたか」**を本文に書く。
