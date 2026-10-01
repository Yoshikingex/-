# 整体接骨院 サンプルサイト（スクロール連動）

1ページ完結。スクロール量に合わせて20秒の動画（4章）が進みます。

## ファイル
- `index.html` … ページ本体（CSS/JSを内包）
- `assets/hero_16x9.mp4` / `assets/hero_9x16.mp4` … スクロール用動画（横長=PC、縦長=スマホを自動切替。6コマごとにキーフレーム）
- `assets/*.webp` … 画像（ストーリーボードの切り出し・キーフレーム）

## 使っているライブラリ（CDN）
GSAP 3.12.5 + ScrollTrigger / Three.js r128 / Lenis 1.1.13 / Google Fonts（Klee One・Zen Kaku Gothic New）

## ローカルで確認
動画を fetch で読み込むため、ファイルを直接開かずサーバー経由で開く。
```
cd site && python3 -m http.server 8000   # → http://localhost:8000
```

## 章とスクロール位置
| 章 | 動画 | スクロール進行 |
|---|---|---|
| 01 悩み | 0–5秒 | 0–25% |
| 02 来院 | 5–10秒 | 25–50% |
| 03 施術 | 10–15秒 | 50–75% |
| 04 回復＋ロゴ | 15–20秒 | 75–100% |

※電話番号・受付時間・予約フォームはサンプルです（送信されません）。

## 公開先（本番）
- URL: https://yoshikingex.github.io/-/
- 仕組み: GitHub Pages（`gh-pages` ブランチの中身をそのまま配信）
- 更新手順: `site/` の `index.html` と `assets/` を `gh-pages` ブランチの直下にコピーして push すると、1〜2分で反映
