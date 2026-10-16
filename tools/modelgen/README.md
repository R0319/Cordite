# modelgen — 銃モデル生成ツール（🔵 試作）

Bedrock 形式（`.geo.json`）の銃モデルと下塗りテクスチャをスクリプトから生成する。
方針・比較の観点は [docs/specs/07-model-assets.md](../../docs/specs/07-model-assets.md#モデル生成方式の試作比較-検討中)。

```
python3 build.py              # 全方式を生成
python3 build.py m4a1_parts   # 1方式だけ
```

必要なもの: Python 3.10+、numpy、Pillow、shapely（メッシュの角丸めで使用）。写真のトレースには contourpy も使う。

| ファイル | 役割 |
|---------|------|
| `core.py` | キューブ/ボーン、面ごとのUV自動割り当て＋テクスチャ塗り、プレビュー描画（ローダーと同じ回転規則。ボーンの rotation も反映するので、開閉・展開の姿勢を確かめられる） |
| `materials.py` | 材質（下塗り色）。作者が PNG を塗り直す前提の仮色 |
| `texbake.py` | テクスチャの仕上げ（`core.bake` の最後）: 形から決まる陰影（隙間の遮蔽・角の明るさ・上向きの明るさ）の焼き込みと、3D の位置で作る汚れ・擦れ・埃・木目 |
| `ar15_parts.py` | AR-15 系パーツライブラリ（単位 mm、実寸ベース）。`Layout` を変えれば同系統の別銃に流用できる |
| `ar15_mesh.py` | 上のメッシュ版。丸・曲線の部品だけ `poly_mesh`（Meshy プラグイン互換）へ置き換え |
| `score.py` | 作成後の自動採点（未説明の食い違いが 0 件になるまで直すか理由を書く）: 写真の影絵との一致率と輪郭のずれ（`--photo`）、6 方向の影絵で部品の間に背景が細く抜けている所、放射状の浅い折れ目（筋）、面の数、ボーン。`--pose` で可動部を動かした姿勢でも見る。`python3 score.py m79_mesh --photo <写真> --pose rear_sight:-90:0:0 --img-dir <出力先>` / `python3 score.py --all` |
| `score_expected.json` | 自動採点の写真との食い違い・隙間のうち、理由の分かっている物（銃ごと。説明済み・要修正・要確認）と、写真から除く枠（背景の人物等）。ここに無い物は「未説明」で終了コード 1 |
| `end_views.py` | 前・後ろ・上から同じ縮尺（mm の目盛り付き）で描き、同じ向きの資料と並べる。幅の確認用 |
| `inspect_views.py` | 確認用描画: 6 方向の一覧、真横写真への輪郭の重ね合わせ（写真と重ねた画像はリポジトリに入れない） |
| `m2.py` / `trace_m2.py` / `m3_tripod.py` | M2 重機関銃（教範の写真をトレース）と M3 三脚（銃と同じ座標） |
| `g3a3.py` / `trace_g3.py` | G3A3（作者提供の真横写真をトレース。MP5 と同じ作りの受け部・照準器） |
| `hk416.py` / `trace_hk416.py` | HK416 D14.5RS（作者提供の三面図の線画を影絵にしてトレース。AR-15 と同じ規格の部品は `ar15_mesh` を `HKLayout` で流用） |
| `fiveseven.py` | FN Five-seveN MK2（作者提供の三面図に mm 目盛りを重ねて点を読み取った。一人称の構えは glock と同じ: `rig.add_pistol_locators`） |
| `riot_shield.py` | ライオット兵の盾（覗き窓付きの防弾板）。手に持つ向きはバニラの盾の構えの変換を逆算して焼き込む。1px = 62.5mm（当たり判定と同じ大きさ） |
| `sights.py` | 照準器の共通部品（誇張の目安・穴の抜けた照門・デフォルトのアイアンサイト `iron_sight`） |
| `rig.py` | コードが参照するロケーター・腕プレースホルダと、一人称の配置（トリガー基準の式）・腕の待機ポーズ（`<銃ID>.animation.json`） |
| `m4a1_parts.py` | A: パーツ組立版 M4A1 |
| `m4a1_pixel.py` | B: ピクセル版 M4A1 |
| `photo_trace.py` | 写真のトレース: 真横写真のシルエットを等値線（画素以下の精度）で取り出し、mm の多角形の範囲で部品ごとに切り出す。銃身などは太さの分布（Z, 半径）で取る |
| `trace_m249.py` | M249 の写真から部品ごとの側面形をトレースして `m249_outline.py` に書き出す（写真はリポジトリに入れない。`python3 trace_m249.py <写真>`） |
| `m249.py` | M249（メッシュ版）。`m249`（ボックス＋ベルト）と `m249_stanag`（STANAG 弾倉）の 2 つを出す。二脚・キャリングハンドル・フィードカバーは回転できるボーン |
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
