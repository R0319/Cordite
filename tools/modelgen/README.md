# modelgen — 銃モデル生成ツール（🔵 試作）

Bedrock 形式（`.geo.json`）の銃モデルと下塗りテクスチャをスクリプトから生成する。
方針・比較の観点は [docs/specs/07-model-assets.md](../../docs/specs/07-model-assets.md#モデル生成方式の試作比較-検討中)。

```
python3 build.py              # 全方式を生成
python3 build.py m4a1_parts   # 1方式だけ
```

必要なもの: Python 3.10+、numpy、Pillow。

| ファイル | 役割 |
|---------|------|
| `core.py` | キューブ/ボーン、面ごとのUV自動割り当て＋テクスチャ塗り、プレビュー描画（ローダーと同じ回転規則） |
| `materials.py` | 材質（下塗り色）。作者が PNG を塗り直す前提の仮色 |
| `ar15_parts.py` | AR-15 系パーツライブラリ（単位 mm、実寸ベース）。`Layout` を変えれば同系統の別銃に流用できる |
| `ar15_mesh.py` | 上のメッシュ版。丸・曲線の部品だけ `poly_mesh`（Meshy プラグイン互換）へ置き換え |
| `rig.py` | コードが参照するロケーター・腕プレースホルダ（見た目の値は glock から流用した仮置き） |
| `m4a1_parts.py` | A: パーツ組立版 M4A1 |
| `m4a1_pixel.py` | B: ピクセル版 M4A1 |
| （`build.py` 内） | C: パーツ組立＋メッシュ版 M4A1（`m4a1_parts.build(ar15_mesh)`）。メッシュ対応ローダーが必要 |
| `generated/` | 出力。`<方式>/m4a1.geo.json`・`m4a1.png`・`m4a1_modelshot.png`・`preview_*.png`、A は `parts/` に部品単体も |

## ゲームで試す

`generated/<方式>/` の `m4a1.geo.json`・`m4a1.png`・`m4a1_modelshot.png` を作業フォルダへコピーして `runClient`
（`syncGunAssets` が取り込む。gunpack の `m4a1.json` は既存）。同じ銃IDなので、2方式は入れ替えて1つずつ確認する。
Blockbench で開く場合は `m4a1.geo.json` を「Bedrock Entity」として開き、`m4a1.png` をテクスチャに割り当てる。
