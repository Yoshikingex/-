# トラジライスバーガー・スペシャル｜YouTubeレシピ動画 制作パッケージ

主人公（1枚目の女性）が「トラジライスバーガー・スペシャル」をお家で作るレシピ動画（本編 約4分＋ショート45秒）の、台本・生成プロンプト・音声設計・サムネ・仮編集動画一式。

## できているもの（このフォルダ内）

| ファイル | 中身 | 状態 |
|---|---|---|
| `output/thumbnail_A.jpg` `B` `C` | サムネイル3案（1280×720） | ✅ 完成・そのまま使える |
| `output/thumbnail_compare.jpg` | 3案の比較＋検索結果サイズでの見え方 | ✅ |
| `output/animatic_720p.mp4` | **仮編集動画 3分49秒**（ストーリーボード＋テロップ＋仮ナレ） | ✅ 設計図。本番映像に差し替えて使う |
| `output/subtitles_ja.srt` | 日本語字幕（仮編集の尺） | ✅ 本編完成後に再生成 |
| `output/narration_for_tts.txt` | 音声合成に貼るナレーション原稿（読み仮名補正済み） | ✅ |
| `output/youtube_chapters.txt` | 概要欄のチャプター | ✅ 本編完成後に再生成 |
| `docs/01_recipe.md` | レシピ全文（材料・段取り・失敗対策・アレンジ） | ✅ |
| `docs/02_script_storyboard.md` | 台本・絵コンテ（31シーン、TC・ナレ・テロップ・SE） | ✅ |
| `docs/03_higgsfield_prompts.md` | Higgsfield 画像/動画プロンプト（主人公5カット＋料理27カット） | ✅ |
| `docs/04_voice.md` | 主人公の声の設計（ElevenLabs 設定・説明文） | ✅ |
| `docs/05_thumbnail.md` | サムネの狙い・A/Bテスト手順 | ✅ |
| `docs/06_editing.md` | 編集手順（CapCut）・テロップ規定・音・書き出し・ショート台本 | ✅ |
| `docs/07_youtube_upload.md` | タイトル3案・概要欄・タグ・投稿チェックリスト | ✅ |

## 制作の流れ（1ステップずつ進める）

1. **許諾確認**：主人公の肖像権（AI生成の可否）・トラジのロゴ/商品名の使用許可・市販品の有無 → `docs/03` の「0. 生成前チェック」
2. **仮編集を見る**：`output/animatic_720p.mp4` で流れと尺を確認。直したい所は `tools/scenes.json` を修正
3. **声を作る**：`docs/04_voice.md` → S01〜S31 の音声ファイル
4. **主人公を生成**：`docs/03` の ①キャラ固定 → H1〜H5
5. **料理カットを生成**：`docs/03` の C章（27カット：静止画→5秒動画）
6. **編集**：`docs/06_editing.md`（仮編集に本番素材を差し替え）
7. **サムネ最終化**：H5 ができたら人物を差し替えて再生成（`docs/05`）
8. **投稿**：`docs/07_youtube_upload.md` のチェックリスト

## 確定／未確定

- 【確定】レシピ分量・台本31シーン・テロップ・サムネ3案・仮編集の尺（3:49、終了画面を本番20秒にすると約4:01）
- 【未確定】主人公の名前（台本では `{NAME}`／テロップでは「〇〇」）
- 【未確定】市販品「トラジライスバーガー・スペシャル」の実在・加熱時間（S14〜S16）。ストーリーボード2枚目のパッケージ画像から想定したもの
- 【未確定】「焼肉トラジ」の公式動画として出すか（タイトルの「直伝」表記に影響）
- 【推測】主人公は実在の人物。AI生成して公開するには本人・所属先の許諾が必要
- 【未確定】Higgsfield・ElevenLabs の現行の機能名とクレジット/料金（生成＝有料）

## 作り直し方（台本やサムネを変えたとき）

必要なもの：Python 3.10以上

```text
【Claude Code / Git Bash】
cd /c/dev/-/toraji_rice_burger_video
pip install -r requirements.txt
bash tools/fetch_fonts.sh              # フォント取得（初回のみ）
python tools/crop_panels.py            # ストーリーボードを1コマずつ切り出し
python tools/cutout_host.py            # 主人公の切り抜き
python tools/make_thumbnails.py        # サムネ3案
python tools/build_animatic.py         # 仮編集動画（約3分かかる。仮ナレにネット接続が必要）
python tools/build_docs.py             # 台本・プロンプト・チャプター・TTS原稿

【PowerShell】
cd C:\dev\-\toraji_rice_burger_video
pip install -r requirements.txt
# フォントは tools\fetch_fonts.sh の3つのURLからダウンロードして assets\fonts\ に置く
python tools\crop_panels.py; python tools\cutout_host.py; python tools\make_thumbnails.py
python tools\build_animatic.py; python tools\build_docs.py

※ C:\dev\- はリポジトリの clone 先の例（未確定）。実際の場所に読み替える
※ 台本は tools/scenes.json が原本。docs/02・docs/03 は自動生成なので直接編集しない
```

## フォルダ構成

```text
toraji_rice_burger_video/
├─ README.md
├─ requirements.txt
├─ assets/
│  ├─ source/   受け取った元画像5枚（01_host_girl.jpg ほか）
│  ├─ panels/   ストーリーボードの切り出し34コマ＋主人公の切り抜き
│  └─ fonts/    （Git管理外）fetch_fonts.sh で取得
├─ docs/        01〜07 の制作ドキュメント
├─ output/      サムネ・仮編集動画・字幕・原稿・チャプター
└─ tools/       生成スクリプト＋ scenes.json（台本の原本）
```
