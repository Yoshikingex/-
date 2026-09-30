# 05 サムネイル

## 結論

- **本命は A 案**（主人公＋巨大バーガー＋「焼肉屋が本気で作った／ライスバーガー」）
- A/B/C の3枚を YouTube Studio の「**テストと比較**」に登録し、総再生時間で勝った案を残す【確定：YouTubeは最大3枚のサムネを比較テストできる】
- 完成ファイル：
  - `toraji_rice_burger_video/output/thumbnail_A.jpg`（本命）
  - `toraji_rice_burger_video/output/thumbnail_B.jpg`
  - `toraji_rice_burger_video/output/thumbnail_C.jpg`
  - `toraji_rice_burger_video/output/thumbnail_compare.jpg`（3案＋検索結果サイズでの見え方）
- 仕様：1280×720・JPG・各約0.3MB（YouTube上限2MB以内）

## 3案の狙い

| 案 | 構図 | 文字 | 検証したいこと |
|---|---|---|---|
| A | 主人公(左)＋バーガー(右) | 焼肉屋が本気で作った／ライスバーガー／黄身とろ〜り | 「人＋料理＋権威（焼肉屋）」の王道 |
| B | バーガー(左)＋主人公(右) | ごはんで挟む！／焼肉バーガー／フライパン1つで | 「作り方の簡単さ」訴求は効くか |
| C | 料理のみ・大きく | 黄身とろ〜り／焼肉屋の本気ライスバーガー／お家でトラジ | 顔なし（シズル全振り）は効くか |

## 作りのルール（今後のシリーズでも共通）

1. 文字は**3要素まで**。一番大きい文字は7文字前後
2. 黄色グラデ＋黒フチ＋赤フチの三重フチ（どんな背景でも読める）
3. 料理は画面の半分以上。黄身・ソースのしずくが見える位置で切る
4. 人物は白フチで背景から浮かせる。視線はカメラ
5. 右下は再生時間表示で隠れるので、重要な文字を置かない

## さらにクリック率を上げる次の一手

- 現在の人物は「ガッツポーズの全身写真」を切り抜いたもの。**H5（バーガーを顔の横に持って驚く表情）** を Higgsfield で生成し（`docs/03_higgsfield_prompts.md`）、`assets/panels/host_cutout.png` を差し替えて再生成すると、「表情＋商品」で目が止まりやすくなる【推測：料理系チャンネルで一般的な傾向】

## 作り直し方

- 文字や配置を変える：`toraji_rice_burger_video/tools/make_thumbnails.py` の `thumb_a()`〜`thumb_c()` を編集 → 下のコマンド
- コマンド（Claude Code／Git Bash）：`cd /c/dev/-/toraji_rice_burger_video && python tools/make_thumbnails.py`
- コマンド（PowerShell）：`cd C:\dev\-\toraji_rice_burger_video; python tools\make_thumbnails.py`
- ※ `C:\dev\-` はリポジトリの clone 先の例【未確定】。実際の場所に読み替える
