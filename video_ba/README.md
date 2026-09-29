# LP ビフォーアフター縦型リール

- 完成動画: `output/lp_before_after_reel.mp4`（1080x1920 / 30fps / 53秒 / H.264+AAC）
- BGM単体: `output/bgm.wav`（Pythonで合成したオリジナル曲。外部素材なし＝著作権フリー。CapCutでの再編集用）
- テロップ: `output/telop.ass`（字幕ソフトで編集可能）

## 構成（120BPM・カットはビートに同期）
| 秒 | パート | 内容 |
|---|---|---|
| 0–3 | フック | BEFORE（静止LP）を0.5秒ずつ見せる＋「そのLP、止まってない？」 |
| 3–7 | リビール | 白フラッシュ＋ドロップ、AFTERを0.5秒ずつ8カット＋「5 CASES」 |
| 7–47 | 事例×5（各8秒） | 5秒=上下分割（3倍速）＋3秒=AFTER拡大と見どころテロップ |
| 47–53 | アウトロ | 5事例のグリッド＋「NEXT YOUR LP?」＋相談導線＋保存促し |

## 再生成
```
pip install numpy scipy imageio-ffmpeg   # ffmpeg は libass 入りのものが必要
python3 make_music.py
python3 build_video.py <素材mp4フォルダ>
```
事例ごとのカテゴリ名・テロップ・ハイライト秒数は `build_video.py` 冒頭の `CASES` で変更できる。

## 素材ライセンス
- フォント: Anton / Dela Gothic One / Noto Sans JP（いずれも SIL Open Font License 1.1、Google Fonts 由来。npm `@expo-google-fonts/*` から取得）
- 音楽・効果音: `make_music.py` による自作合成（第三者素材なし）
