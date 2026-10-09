# modelgen — 銃モデル生成ツール（🔵 試作）

Bedrock 形式（`.geo.json`）の銃モデルと下塗りテクスチャをスクリプトから生成する。
方針・比較の観点は [docs/specs/07-model-assets.md](../../docs/specs/07-model-assets.md#モデル生成方式の試作比較-検討中)。

```
python3 build.py              # 全方式を生成
python3 build.py m4a1_parts   # 1方式だけ
```

必要なもの: Python 3.10+、numpy、Pillow、shapely（メッシュの角丸めで使用）。

| ファイル | 役割 |
|---------|------|
| `core.py` | キューブ/ボーン、面ごとのUV自動割り当て＋テクスチャ塗り、プレビュー描画（ローダーと同じ回転規則） |
| `materials.py` | 材質（下塗り色）。作者が PNG を塗り直す前提の仮色 |
| `ar15_parts.py` | AR-15 系パーツライブラリ（単位 mm、実寸ベース）。`Layout` を変えれば同系統の別銃に流用できる |
| `ar15_mesh.py` | 上のメッシュ版。丸・曲線の部品だけ `poly_mesh`（Meshy プラグイン互換）へ置き換え |
| `inspect_views.py` | 確認用描画: 6 方向の一覧、真横写真への輪郭の重ね合わせ（写真と重ねた画像はリポジトリに入れない） |
| `rig.py` | コードが参照するロケーター・腕プレースホルダ（見た目の値は glock から流用した仮置き） |
| `m4a1_parts.py` | A: パーツ組立版 M4A1 |
| `m4a1_pixel.py` | B: ピクセル版 M4A1 |
| （`build.py` 内） | C: パーツ組立＋メッシュ版 M4A1（`m4a1_parts.build(ar15_mesh)`）。メッシュ対応ローダーが必要。`m4a1_mesh_lite` はその簡略版（`ar15_mesh.set_detail("lite")`、敵 NPC 用など） |
| `generated/` | 出力。`<方式>/m4a1.geo.json`・`m4a1.png`・`m4a1_modelshot.png`・`preview_*.png`、A は `parts/` に部品単体も |

## ゲームで試す

`generated/<方式>/` の `m4a1.geo.json`・`m4a1.png`・`m4a1_modelshot.png` を作業フォルダへコピーして `runClient`
（`syncGunAssets` が取り込む。gunpack の `m4a1.json` は既存）。同じ銃IDなので、2方式は入れ替えて1つずつ確認する。
Blockbench で開く場合は `m4a1.geo.json` を「Bedrock Entity」として開き、`m4a1.png` をテクスチャに割り当てる。

## 形の作り分け

全部を丸くしない。樹脂の握る部品は丸く、金属の削り出し部品（レシーバー・弾倉・レール）は角張ったまま、
という作り分けで実物らしさを出す → [07-model-assets.md「形の作り分け（メリハリ）」](../../docs/specs/07-model-assets.md#形の作り分けメリハリ-仮)

## 部品を作る・直す前に

参照する実物の**メーカー・型番・取付方法・寸法を先に調べ**、[07-model-assets.md「部品ごとの参照品」](../../docs/specs/07-model-assets.md#部品ごとの参照品メーカー型番取付-仮)
の表に書いてから形を決める。寸法は `ar15_parts.Layout`（取り合い）か部品関数の定数に入れ、根拠をコメントに残す。
分からなかった値は「未確認」として表に残し、推測で埋めない。
