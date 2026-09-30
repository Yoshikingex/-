# 03 Higgsfield 生成プロンプト集（画像・動画）

> このファイルは `tools/build_docs.py` が自動生成（冒頭部分の原本は `tools/higgsfield_header.md`）。
> 【未確定】Higgsfield の機能名・モデル名・クレジット単価は更新が速いため、**画面上の名称が違う場合は「同じ役割の機能」を選ぶ**。ここに書いた名称は2025年時点の情報にもとづく【推測を含む】。
> 【原価】Higgsfield の生成はクレジット消費（＝有料）。**生成ボタンを押す前に、残りクレジットと1回あたり消費量を確認する**。

## 0. 生成前チェック（必須）

- [ ] **主人公の肖像権・AI生成の許諾**：1枚目の女性は実在の人物と思われる【推測】。本人（または所属事務所）と、トラジ（ロゴ・制服の使用）から「AIで動画を生成してYouTubeに公開する」許諾を**書面で**取る
- [ ] YouTube 投稿時に「**改変または合成されたコンテンツ**」を「はい」にする（実在の人物をリアルに合成した動画は申告が必要）
- [ ] 市販品「トラジライスバーガー・スペシャル」が実在・販売中か（S14〜S16で使用）。未確認ならそのカットは作らない

## 1. 全体の流れ（どのツールで何を作るか）

| 工程 | 作るもの | 推奨ツール（Higgsfield内） | 本数 |
|---|---|---|---|
| ① キャラ固定 | 主人公の参照画像セット 8〜10枚 | 画像編集モデル（Nano Banana / Seedream 系）に1枚目写真を参照入力 → Soul ID 等のキャラ学習に登録 | 1回 |
| ② 主人公の静止画 | H1〜H5 | ①のキャラで画像生成（16:9） | 5枚 |
| ③ 主人公の動画 | H1・H3・H4 の動く映像 | image-to-video（Kling / Veo / Seedance 系）→ 話す場面は **Lipsync（口パク合わせ）** に ElevenLabs の音声を入れる | 4本 |
| ④ 料理の静止画 | ストーリーボードの各コマを16:9高画質で作り直し | 画像編集モデルに `assets/panels/*.png` を参照入力 | 27枚 |
| ⑤ 料理の動画 | ④を5秒動画に | image-to-video（カメラワーク系は DoP、シズル系は Kling/Seedance） | 27本 |
| ⑥ 高画質化 | 1080p（または4K）に | Upscale | 必要分 |

- 生成回数の目安：**約65回**（主人公10＋料理54。1カット平均2回の撮り直し込み）【推測】
- ストーリーボードのコマは元が小さい（幅約230px）ので、**そのまま動画化せず、必ず④で作り直してから**⑤に進む

## 2. キャラクター固定ブロック（主人公が出る全プロンプトの先頭に貼る）

```text
CHARACTER (must match the reference photo exactly, same face and same outfit):
young Japanese woman in her early 20s, light brown hair in two long loose braids with small red heart-shaped hair accessories near the shoulders, wispy see-through bangs, round thin gold wire-frame glasses, bright friendly smile, natural makeup.
OUTFIT: black beret-style cap with a red band and red "TORAJI" embroidery, red short-sleeve shirt with a black V-neck collar, black bib apron with a small red "TORAJI TOKYO EBISU" logo on the chest, red ribbon tied at the waist, red mini skirt, black knee-high socks, black low heels.
```

**①キャラ参照セットの作り方（1枚目の写真を参照に入れて、以下を1枚ずつ生成）**

```text
Same woman and same outfit as the reference photo. {下のどれか1つ}. Plain light gray studio background, soft even lighting, photorealistic, 4K.
- front view, waist-up, gentle smile
- three-quarter view facing left, waist-up, laughing
- three-quarter view facing right, waist-up, speaking
- close-up portrait, looking at camera, happy
- close-up portrait, eyes closed, delighted expression
- waist-up, holding a plate with both hands
- waist-up, pointing to the right with her index finger
- waist-up, surprised expression with mouth slightly open
注意：顔が変わった画像は採用しない。眼鏡・三つ編み・帽子のロゴが崩れたものも不採用。
```

## B. 主人公カット（H1〜H5）

### H1｜S03 自己紹介（口パクあり）

```text
【静止画｜16:9】
{キャラクター固定ブロック}
Medium shot, waist-up. She stands behind a wooden counter in a warm, bright Japanese yakiniku restaurant kitchen, waving at the camera with her right hand and smiling. A finished rice burger on a wooden board sits on the counter in front of her. Warm practical lights, soft window light, shallow depth of field, eye-level camera, photorealistic, 4K, no text.

【動画｜image-to-video｜8〜10秒】
She waves, then talks cheerfully to the camera with natural head movement and blinking, slight lean forward, small hand gestures. Static eye-level camera. Keep her face and outfit identical.

【口パク】上の動画 ＋ ElevenLabs で作った S03 の音声 → Lipsync 機能で合わせる
```

### H2｜S05 材料紹介のワイプ用（任意）

```text
【静止画｜16:9】
{キャラクター固定ブロック}
Waist-up, she presents ingredients on the counter with an open palm gesture toward the right side of the frame (tomato, lettuce, eggs, rice, beef in a bowl), cheerful expression, warm restaurant kitchen background, photorealistic, 4K, no text.

【動画｜5秒】
She gestures toward the ingredients and nods with a smile. Static camera.
```

### H3｜S28 実食（2本に分けて作る）

AI動画は「かじる瞬間」が崩れやすい。**口に入る直前でカット → SE「ザクッ」→ 断面カット（S29）→ 噛んでいる顔**の順に編集でつなぐ。

```text
【静止画｜16:9】
{キャラクター固定ブロック}
Medium close-up. She holds a tall rice burger wrapped in wax paper with both hands at chest height, excited expression, looking at the burger. Warm restaurant background with bokeh, photorealistic, 4K, no text.

【動画A｜3秒｜かじる直前まで】
She lifts the burger toward her mouth with both hands, eyes widening with excitement. The clip ends just before the burger touches her lips. Static camera.

【動画B｜4秒｜噛んでいるリアクション】
She is chewing with her mouth closed, one hand covering her mouth politely, eyes closed with a delighted expression, then nods and gives a thumbs-up. Static camera.
```

### H4｜S30 エンディング（口パクあり）

```text
【静止画｜16:9】
{キャラクター固定ブロック}
Waist-up, cheerful fist pump with her right hand raised near her shoulder and left hand on her hip (same pose as the reference photo), big smile, the finished rice burger on the counter beside her, warm restaurant kitchen, photorealistic, 4K, no text.

【動画｜8秒】
She talks to the camera with energy, does a small fist pump at the end and smiles. Static camera.

【口パク】S30 の音声で Lipsync
```

### H5｜サムネイル用の表情カット（クリック率アップ用）

```text
【静止画｜16:9｜切り抜き前提】
{キャラクター固定ブロック}
Close-up from chest up. She holds the rice burger right next to her face with one hand, surprised and delighted expression with her mouth open in an "O" shape, eyebrows raised, looking straight at the camera. Bright high-key lighting, plain light gray background (for easy cutout), photorealistic, 4K, no text.
```

→ 完成したら `tools/make_thumbnails.py` の `host_upper()` が読む画像（`assets/panels/host_cutout.png`）をこの切り抜きに差し替えて再生成すると、サムネの人物が「驚き顔＋商品を持つ」構図になる。

## 生成のコツ（崩れ対策）

- 1プロンプト＝1動作。「切る→混ぜる」のように2動作を入れない
- 手が増える・指が溶けるときは、動きを小さく（`slow`, `gentle`）にして再生成
- 料理が変形するときは、動画の長さを5秒→3〜4秒に短縮
- 同じカットは**3回まで**。3回崩れたら、静止画にズーム（編集ソフトのキーフレーム）で代用する
