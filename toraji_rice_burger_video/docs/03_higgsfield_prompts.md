# 03 Higgsfield 生成プロンプト集（画像・動画）

> このファイルは `tools/build_docs.py` が自動生成（冒頭部分の原本は `tools/higgsfield_header.md`）。
> 【未確定】Higgsfield の機能名・モデル名・クレジット単価は更新が速いため、**画面上の名称が違う場合は「同じ役割の機能」を選ぶ**。ここに書いた名称は2025年時点の情報にもとづく【推測を含む】。
> 【原価】Higgsfield の生成はクレジット消費（＝有料）。**生成ボタンを押す前に、残りクレジットと1回あたり消費量を確認する**。

## 0. 生成前チェック（必須）

- [ ] **主人公の肖像権・AI生成の許諾**：1枚目の女性は実在の人物と思われる【推測】。本人（または所属事務所）と、トラジ（ロゴ・制服の使用）から「AIで動画を生成してYouTubeに公開する」許諾を**書面で**取る
- [ ] YouTube 投稿時に「**改変または合成されたコンテンツ**」を「はい」にする（実在の人物をリアルに合成した動画は申告が必要）
- [x] 市販品「トラジライスバーガー・スペシャル」：販売ありとして S14〜S16 で使用（確定）

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


## C. 料理カット（B-roll）全カット

各カット：①参照画像（`assets/panels/…png`）をアップロード → ②**静止画プロンプト**で16:9高解像度に作り直す → ③できた静止画を**動画プロンプト**で5秒動画化。

**全カット共通の末尾スタイル（静止画プロンプトの最後に必ず付ける）**

```
cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark
```

### S01 / S29｜オープニング｜参照：`assets/panels/sb12_11.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Rice burger torn in half showing thick layers of glossy sweet-savory beef and a fried egg, runny yolk slowly oozing and dripping. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Slow push-in, yolk drips down in slow motion, steam rises. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S02｜オープニング｜参照：`assets/panels/sb12_10.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Tall rice burger with crispy grilled rice buns, egg, tomato, lettuce and dripping sauce on a wooden board. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Slow 15-degree orbit around the burger, sauce drips, steam. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S04｜オープニング｜参照：`assets/panels/sb22_01.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Finished rice burger hero shot, crispy rice buns, sweet-savory beef, fried egg, tomato, lettuce, pink aurora sauce. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Static camera, steam rising, gentle rack focus from front lettuce to egg yolk. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S05｜材料｜参照：`assets/panels/sb22_03.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Top-down flat lay of ingredients: two rice patties, tomato, green leaf lettuce, egg, sweet-savory beef in a bowl, pink sauce. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Top-down, very slow clockwise rotation and slight push-in. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S06｜①特製ソース｜参照：`assets/panels/sb22_04.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Mayonnaise and ketchup side by side in a white ceramic bowl. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Static, a spoon enters frame from the right. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S07｜①特製ソース｜参照：`assets/panels/sb22_05.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Hands whisking mayonnaise and ketchup with a spoon in a white bowl, turning pink. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Circular whisking motion, sauce swirls smoothly, locked-off camera. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S08｜①特製ソース｜参照：`assets/panels/sb22_06.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Smooth glossy pink aurora sauce in a white bowl with a soft peak. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
A spoon lifts a glossy ribbon of sauce and lets it fall, slow motion. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S09｜②野菜｜参照：`assets/panels/sb22_07.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Chef knife slicing a ripe red tomato into thick rounds on a wooden board. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Knife slices down in slow motion, juice glistens. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S10｜②野菜｜参照：`assets/panels/sb22_08.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Hands tearing crisp green leaf lettuce over a steel colander, water droplets. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Water droplets splash in slow motion as leaves are torn. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S11｜③ライスバンズ｜参照：`assets/panels/sb12_01.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Freshly cooked glossy Japanese white rice, individual grains visible, steam rising. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Slow push-in, steam curls upward. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S12｜③ライスバンズ｜参照：`assets/panels/sb12_02.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Round rice patty searing in a black frying pan with sesame oil, golden crust with grill marks. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Sizzling oil bubbles at the edges, crust darkens, slight push-in. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S13｜③ライスバンズ｜参照：`assets/panels/sb22_13.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Extreme macro of a golden crispy rice bun surface with toasted grains. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
A pastry brush glazes soy sauce across the crust, sizzle and steam, slow lateral slide. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S14｜時短ルート｜参照：`assets/panels/sb22_02.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Retail package of a frozen rice burger on a wooden table. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Slow push-in on the package. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S15｜時短ルート｜参照：`assets/panels/sb22_11.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Rice burger package inside a microwave oven, warm interior light. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Turntable rotates slowly, warm glow. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S16｜時短ルート｜参照：`assets/panels/sb22_12.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Digital kitchen timer showing 5:00 next to a paper-wrapped package. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Timer digits count down, time-lapse feel. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S17｜④甘辛焼肉｜参照：`assets/panels/sb12_03.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Chopped beef and sliced onion stir-fried in a pan, glossy caramelized yakiniku sauce, spatula. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Spatula tosses the beef, heavy steam, sauce bubbles and turns glossy. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S18｜⑤目玉焼き｜参照：`assets/panels/sb22_09.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Hands cracking an egg into an oiled round steel ring mold in a black pan. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Yolk drops into the ring in slow motion. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S19｜⑤目玉焼き｜参照：`assets/panels/sb22_10.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Perfectly round sunny-side-up egg in a steel ring mold, bright orange yolk, black pepper. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Whites gently bubble, black pepper falls from above. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S20｜⑥組み立て｜参照：`assets/panels/sb22_14.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Glossy sweet-savory beef heaped on a crispy rice bun, a hand holding the top bun. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Beef settles onto the bun, steam rises. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S21｜⑥組み立て｜参照：`assets/panels/sb22_15.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Spatula placing a round fried egg on top of the beef. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Egg slides off the spatula and settles, yolk wobbles. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S22｜⑥組み立て｜参照：`assets/panels/sb22_16.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Fingers placing a thick tomato slice on the fried egg. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Tomato placed gently, droplets glisten. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S23｜⑥組み立て｜参照：`assets/panels/sb22_17.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. A spoon drizzling pink aurora sauce onto the tomato slice. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Thick sauce pours in slow motion and spreads. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S24｜⑥組み立て｜参照：`assets/panels/sb22_18.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Hands placing crisp green leaf lettuce on top of the stack. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Lettuce placed, leaves bounce slightly. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S25｜⑥組み立て｜参照：`assets/panels/sb22_19.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Hand pressing the crispy top rice bun onto the finished burger. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Top bun pressed down, sauce squeezes out and drips. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S26｜⑥組み立て｜参照：`assets/panels/sb22_20.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Low-angle close-up of the burger layers: crispy rice bun, sauce, lettuce, tomato, egg, beef. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Slow dolly left to right across the layers, sauce drips. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S27｜⑥組み立て｜参照：`assets/panels/sb22_21.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Rice burger wrapped in printed wax paper on a wooden board. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Hands fold the wax paper around the burger. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

### S31｜エンディング｜参照：`assets/panels/sb22_22.png`

```text
【静止画｜16:9｜参照画像あり】
Recreate the reference image as a 16:9 high-resolution photo. Finished rice burger next to its product package on a dark wooden table, bokeh. cinematic Japanese food commercial, macro lens, shallow depth of field, warm tungsten key light with soft rim light, dark rustic wooden table, subtle steam, photorealistic, 4K, no text, no numbers, no watermark

【動画｜image-to-video｜5秒】
Slow pull-back, steam. Realistic physics, natural food texture, no morphing, no extra hands, no text.
```

