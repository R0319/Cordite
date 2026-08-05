---
name: build-check
description: このプロジェクトのビルド実行と、失敗したときのエラー分類。「ビルドして」「コンパイルエラー出てる」「エラー吐いた」「起動しない」と言われたときに使う。clean禁止・パイプ禁止・JDK21指定など、この環境固有の落とし穴と既知エラーの対処表を持つ。
---

# ビルドとエラー分類

## 実行

```
./gradlew build            # Windowsは gradlew.bat（Bashツールからは ./gradlew でよい）
./gradlew compileJava      # コンパイルだけ見たいとき（速い）
./gradlew runClient        # 実機確認 — 作者が行う。Claudeは基本叩かない
```

## 3つの禁止事項（守らないと確実に事故る）

### 1. `clean` を使わない

実機確認の前に `clean` すると `build/moddev/` の実行用ファイル（`clientRunVmArgs.txt` 等）が消え、
設定キャッシュが「最新」と誤判定して再生成されず **`runClient` が失敗する**。
消してしまったら `./gradlew prepareClientRun` で作り直す。

### 2. パイプで成否を判定しない

```
# ダメ — パイプの終了コードは最後のコマンドのものになり、Gradleの失敗が隠れる
./gradlew build | tail
```

`BUILD SUCCESSFUL` / `BUILD FAILED` の有無で判定する（`${PIPESTATUS[0]}` を見てもよい）。

### 3. 素の `java` でビルドしない

PATH 上の `java` は **JDK 25**。Gradle デーモンは `~/.gradle/gradle.properties` の
`org.gradle.java.home` で **JDK 21** を指定してある。`gradlew` 経由なら正しい JVM が使われる。
JDK 21 の実際の設置場所は `CLAUDE.local.md`（git管理外）を参照。

## ビルド時に自動で走るもの

`processResources` が `syncGunAssets` と `generateSoundsJson` に依存している。つまり
**ビルドするだけで作業フォルダのアセットが同期され、`sounds.json` が補完される**。
ログの `[Cordite]` 行は必ず読む:

- `[Cordite] cordite.assetDir 未設定のためアセット同期をスキップ` → `local.properties` の設定漏れ
- `[Cordite] アセット作業フォルダが見つからない: ...` → パスが違う／フォルダが移動した
- `[Cordite] sounds.json にエントリを追加: [...]` → 新しい `.ogg` が取り込まれた（正常）

## 既知エラー対処表

| エラー | 原因 | 対処 |
|-------|------|------|
| `この文字(0x80)は、エンコーディングwindows-31jにマップできません` | 日本語コメントを含むソースが CP932 として読まれた | `build.gradle` の `options.encoding = 'UTF-8'` が効いているか確認。新規ソースファイルが UTF-8 で保存されているかも見る（Codex が書いたファイルで起きうる） |
| `BUG! exception in phase 'semantic analysis' ... Unsupported class file major version 69` | Gradle 8.8 同梱の Groovy が JDK 25 のクラスファイルを読めない | `org.gradle.java.home` が JDK 21 を指しているか確認（→ 上の禁止事項3） |
| `runClient` が起動しない／`clientRunVmArgs.txt` が無い | `clean` してしまった | `./gradlew prepareClientRun` |
| `cannot find symbol` が大量 | Codex が中途半端に実装を止めた | `git diff` で欠けているクラス/メソッドを特定し、`codex-impl` で追加指示 |
| 起動はするがモデル/音が出ない | ビルドエラーではない。アセット側 | `asset-apply` の検証（`mc-asset-validator`）へ。ゲーム内ログの `[Cordite]` WARN を見る |
| 実行時の例外・クラッシュ | — | `mc-log-analyzer` エージェントに投げる |

## 失敗したときの流れ

1. エラーメッセージの**先頭**（最初の `error:` / 最初の例外）を見る。Gradle は後続エラーが
   派生であることが多いので、末尾だけ見て判断しない。
2. 上の表で分類する。
3. **コード側の問題なら自分で直さず `codex-impl` で Codex に渡す**（このプロジェクトの役割分担）。
   ただしエラーの**原因特定と修正方針の決定は Claude の仕事**なので、そこまでは自分でやる。
4. アセット側の問題なら `asset-apply` へ。作者の作業が必要なら具体的に何をすればいいか伝えて返す。

## 報告

作者に返すときは **`BUILD SUCCESSFUL` かどうかを最初に書く**。通らなかったのに
「直しました」と言わない。通ったら実機で見るべき確認チェックリストを添える。
