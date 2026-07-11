# 01. gunpackシステム 🟡 仮

> **範囲**: コミュニティが銃を追加するためのJSON配布システム。銃側のレール定義、アタッチメント描画位置、アタッチメント側の定義、フォルダ構造。
> 用語・凡例は [README.md](README.md) を参照。

taczのgunpackを参考に、コミュニティが独自の銃を追加できる仕組み。

## 設計方針

- gunpackはJSONベースで定義
- 銃ごとにレール情報・対応アタッチメントを定義する
- gunpack制作者の負担を減らすため、変更できる部位は絞る

## 変更できる部位 / できない部位

| 変更できる | 変更できない |
|-----------|------------|
| サイト（レール上で位置調整可） | バレル長（銃ごとに固定） |
| マズルデバイス | ハンドガード |
| マガジン | レシーバー |
| ストック | |
| ウェポンライト | |

## レール定義（銃側）

```json
"rails": {
  "top": {
    "length": 10,
    "movable": true,
    "fov_effect": true
  },
  "bottom": {
    "length": 4,
    "movable": false,
    "fov_effect": false
  }
}
```

- `length`：レールの長さ（スロット数）
- `movable`：アタッチメントの前後移動可否
- `fov_effect`：レール上の位置によって視野が変化するか

## アタッチメント描画位置

gunpackのJSONで銃モデルごとにレールの座標をgunpack制作者が指定する。

```json
"attachments": {
  "top_rail": {
    "x": 0.0,
    "y": 0.5,
    "z": 0.2
  },
  "bottom_rail": {
    "x": 0.0,
    "y": -0.3,
    "z": 0.1
  }
}
```

## アタッチメント定義（アタッチメント側）

```json
"sight": {
  "size": 2,
  "reticle": "reticles/dot.png",
  "reticle_size": 0.8,
  "fov_near": 60,
  "fov_far": 80
}
```

- `size`：占有スロット数
- `reticle`：レティクル画像のパス（gunpack内で指定）
- `reticle_size`：レティクルの大きさ
- `fov_near`：後ろ寄り（目に近い）配置時のFOV
- `fov_far`：前寄り（銃口寄り）配置時のFOV

## gunpackフォルダ構造

```
gunpack/
  guns/
    ak47.json
  reticles/
    dot.png
    holo.png
    scope_mil.png
  models/
  textures/
```

## 関連

- 重火器は `"rails": null`（レールなし）→ [03-items.md](03-items.md#重火器のgunpack定義)
- サイトの見え方・FOVの詳細 → [02-guns.md](02-guns.md#サイト照準仕様)
