# トラジライスバーガー・スペシャル｜YouTubeレシピ動画（完成版）

焼肉トラジの看板娘 **ソアちゃん** が「トラジライスバーガー・スペシャル」をお家で作るレシピ動画。
**本編・ショート・サムネ・字幕・概要欄まで、すべて自動生成済み**（有料APIは使っていない＝原価0）。

## 完成品（そのままYouTubeに投稿できる）

| ファイル | 中身 | 仕様 |
|---|---|---|
| `output/toraji_rice_burger_main_1080p.mp4` | **本編** 31シーン・9チャプター・終了画面20秒 | 3分3秒／1920×1080／30fps／音量 −14.7 LUFS |
| `output/toraji_rice_burger_shorts_1080x1920.mp4` | **ショート**（本編への誘導） | 28秒／1080×1920／30fps |
| `output/thumbnail_A.jpg`・`B`・`C` | サムネ3案（「テストと比較」用。本命はA） | 1280×720／各約0.3MB |
| `output/subtitles_ja.srt`／`subtitles_ja_shorts.srt` | 日本語字幕（完成版の尺） | SRT |
| `output/youtube_chapters.txt` | 概要欄のチャプター | 9章（YouTubeの規定：各章10秒以上を満たす） |
| `docs/07_youtube_upload.md` | タイトル3案・概要欄（材料・作り方・チャプター・クレジット）・タグ・投稿チェックリスト | コピペ用 |

## どうやって作ったか（すべてこの環境の中で無料実行）

| 要素 | 方法 | ライセンス |
|---|---|---|
| 料理の映像 | ストーリーボード2枚を34コマに切り出し → **Real-ESRGAN で4倍に高画質化** → ゆっくりズーム／パン・クロスフェード | BSD-3-Clause |
| ソアちゃん | 1枚目の写真を切り抜き → 自己紹介・実食・エンディングに登場。料理カット中は右上に**声に合わせて弾む丸ワイプ** | − |
| 声 | **Kokoro-82M の日本語女性ボイス jf_alpha**（明るい・やや高め）。候補を音声認識AIで聞き取り比較して選定（`docs/04_voice.md`） | Apache-2.0 |
| BGM・効果音 | プログラムで合成（明るいウクレレ風ポップ＋焼き音・ポン・キラーン等13種）。声の間はBGMを自動で下げる | オリジナル |
| テロップ | Noto Sans JP／Dela Gothic One（白文字＋黒フチ、POINTは黄色、章ラベルは赤帯） | SIL OFL |

## 確定／未確定

- 【確定】主人公＝ソア／時短ルート（市販品）＝採用
- 【確定】動画の仕様・尺・音量・チャプター（コマンドで実測）
- 【確定】ナレーションの聞き取り一致率：声のみ 平均91.4%／BGM入りの完成品（冒頭60秒）89.6%（音声認識AI Whisper で計測）
- 【推測】「ソア」は音声認識では「ソワ」と取られることがある（珍しい名前のため）。気になる場合はテロップで補っている
- 【推測】1枚目の女性は実在の人物。公開前に、本人・所属先・トラジの許諾を確認すること。投稿時は「改変または合成されたコンテンツ：はい」
- 【未確定】ソアちゃんを「本当に動かす・口パクさせる」には Higgsfield 等の有料AI動画生成が必要。今回は写真を切り抜いて動かす表現にしている（差し替え手順は `docs/03`・`docs/06`）

## ドキュメント

| ファイル | 中身 |
|---|---|
| `docs/01_recipe.md` | レシピ全文（材料・段取り・失敗対策・アレンジ） |
| `docs/02_script_storyboard.md` | 台本・絵コンテ（完成版のタイムコード付き） |
| `docs/03_higgsfield_prompts.md` | （任意・有料）Higgsfield で動く映像に差し替える場合のプロンプト |
| `docs/04_voice.md` | 声の選定結果と、ElevenLabs に差し替える場合の手順 |
| `docs/05_thumbnail.md` | サムネ3案の狙い・A/Bテスト手順 |
| `docs/06_editing.md` | 自動書き出しの作り直し方／手動編集（CapCut）で仕上げる場合の手順 |
| `docs/07_youtube_upload.md` | 投稿用のタイトル・概要欄・タグ・チェックリスト |

## 作り直し方（台本を変えたとき）

台本の原本は `tools/scenes.json`（本編 `scenes`・ショート `shorts`・読み補正 `tts_readings`）。docs/02・03 と output の字幕・チャプターは自動生成なので直接編集しない。

```text
【準備（初回のみ）】
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python -m unidic download          # 日本語辞書（約0.5GB）
bash tools/fetch_fonts.sh          # フォント（PowerShellの場合は fetch_fonts.sh 内の3つのURLから assets\fonts\ にダウンロード）

【Claude Code / Git Bash】
cd /c/dev/-/toraji_rice_burger_video
python tools/crop_panels.py && python tools/cutout_host.py && python tools/upscale_panels.py
python tools/tts_voice.py kokoro && python tools/tts_voice.py kokoro shorts
python tools/make_audio.py
python tools/render_video.py main && python tools/render_video.py shorts
python tools/make_thumbnails.py && python tools/build_docs.py

【PowerShell】
cd C:\dev\-\toraji_rice_burger_video
python tools\crop_panels.py; python tools\cutout_host.py; python tools\upscale_panels.py
python tools\tts_voice.py kokoro; python tools\tts_voice.py kokoro shorts
python tools\make_audio.py
python tools\render_video.py main; python tools\render_video.py shorts
python tools\make_thumbnails.py; python tools\build_docs.py

※ C:\dev\- は clone 先の例（未確定）。実際の場所に読み替える
※ 所要時間の目安（4コアCPU）：高画質化 約4分／本編書き出し 約4分／ショート 約35秒
```

## フォルダ構成

```text
toraji_rice_burger_video/
├─ README.md / requirements.txt
├─ assets/
│  ├─ source/     受け取った元画像5枚
│  ├─ panels/     切り出し34コマ＋ソアちゃんの切り抜き
│  ├─ panels_hd/  高画質化した34コマ（Real-ESRGAN x4）
│  ├─ audio/      BGM・効果音（合成）
│  └─ fonts/      （Git管理外）fetch_fonts.sh で取得
├─ docs/          01〜07
├─ output/        完成動画・サムネ・字幕・チャプター・原稿（animatic_720p.mp4 は旧・仮編集版）
├─ tools/         生成スクリプト一式＋ scenes.json（台本の原本）
└─ work/          （Git管理外）音声・中間ファイル
```
