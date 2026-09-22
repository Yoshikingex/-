# Atelier Lumière — 文具店のスクロール連動サンプルサイト

Three.js（r169）と GSAP ScrollTrigger（3.12.5）で作った、架空の文具店のサンプルページです。
スクロールすると、ガラスのペン立てから鉛筆と色鉛筆が飛び出し、革のノートが開いて文房具が飛び出します。最後は机の上に俯瞰で並びます。

## 構成

```
stationery-shop/
├─ index.html          ページ本体（6章構成）
├─ css/style.css       スタイル
├─ js/main.js          3Dシーン・モデル生成・スクロール連動
├─ assets/             シーンから書き出した画像と動画
│   ├─ hero.jpg, gallery-01〜04.jpg, flatlay.jpg
│   └─ film.webm       12秒のショートフィルム
└─ tools/render.mjs    画像・動画を書き出すスクリプト（Playwright）
```

## 見る方法

ES Modules と CDN を使うので、ファイルを直接ダブルクリックしても動きません。ローカルサーバーを立ててください。

```
cd stationery-shop
npx http-server -p 8123
# → http://localhost:8123 を開く
```

## 仕組み

- **モデル**：画像ファイルを使わず、コードで生成しています（六角軸の鉛筆＋金の刻印、木の削り面、黒鉛の芯、真鍮の口金、消しゴム、24色の色鉛筆、万年筆、アクリル定規、マスキングテープ、ゼムクリップ、革のノート、ガラスのペン立て、木の机）。
- **質感**：PBR マテリアル（クリアコート、透過ガラス、金属）、RoomEnvironment の映り込み、ソフトシャドウ、ACES トーンマッピング、ブルーム、周辺減光・フィルムグレイン。
- **スクロール**：`.chapter`（175vh）の中に sticky パネルを置いています。次の章が画面下から入ってくる区間を ScrollTrigger で 0〜1 に変換し、合計値 `p = 0〜5` で全オブジェクトのキーフレームを補間しています。文字の出現も ScrollTrigger で制御しています。

## 画像・動画を書き出し直す

```
npx http-server -p 8123 &
node tools/render.mjs stills assets 1600 1000   # 静止画
node tools/render.mjs film assets 960 540   # 動画（WebM, 12秒・20fps）
```

`?capture` を付けて開くと UI が隠れ、`window.__renderAt(p, t)` で任意の場面を1フレームずつ描画できます。

※ 店名・住所・価格はすべて架空です。
