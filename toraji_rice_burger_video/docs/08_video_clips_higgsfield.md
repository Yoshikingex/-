# 08 動画クリップ版（写真を使わない完成版）｜Higgsfield・200クレジット以内

## 結果（2026-09-30 実行済み）

- **Claude Code の Higgsfield 連携で、全30本の動画クリップを生成済み**（APIキーの登録・新しいセッションは不要になった）
- モデル：**Hailuo 2.3**（ソアちゃん3本と「一番おいしい絵」3本）＋ **Hailuo 2.3 Fast**（残り24本）／各6秒・768p・最初のコマ指定
- 【確定】使用クレジット：**140**（上限200）。残高 2,112 → 1,976（一括生成後）→ 作り直し1本分 4
  - 事前見積もり（無料）で比較：Hailuo 2.3 Fast 6秒=4／Seedance 2.0 Mini 4秒=4／Kling 3.0 3秒=4.5／Veo 3.1 Lite 4秒=6／Hailuo 2.3 6秒=6
- 作り直し：`sb22_02`（パッケージ）は初回版で「トラジ」が「トフジ」に崩れたため、パッケージ全体が映る入力で再生成（+4）
- 部分使用：`sb22_21`（包む）は後半で映像が崩れるため 0〜2.6秒のみ使用（`tools/scenes.json` の `clip_trim`）
- クリップ本体と生成記録：`assets/clips_hailuo/`（30本＋`generation_log.json`：ジョブID・プロンプト・クレジット）
- 完成動画：`output/toraji_rice_burger_main_1080p_clips.mp4`／`output/toraji_rice_burger_shorts_1080x1920_clips.mp4`

---

以下は、APIキー方式（`tools/hf_generate.py`）で作り直す場合の手順（今回は連携ツールで実行したため未使用）。

## あなたがやること（1回だけ）

1. Higgsfield Console（https://console.higgsfield.ai）で **APIキー** を発行する（キーIDとシークレットの2つが出る）
2. Claude Code の画面上部のクラウド環境メニュー →「編集」→ 環境変数に次の2行を登録する
   ```text
   HF_API_KEY_ID=（キーID）
   HF_API_KEY_SECRET=（シークレット）
   ```
3. **新しいセッション**を始めて、次の1行を送る（登録したキーは新しいセッションから有効になる）
   ```text
   toraji_rice_burger_video/_handoff/ の最新の引き継ぎJSON（handoff_v2.json）を読んで、動画クリップ版を200クレジット以内で最後まで作って
   ```

- キーやパスワードはチャットに貼らないこと（環境変数にだけ入れる）

## 新しいセッションで自動で行う手順（Claudeが実行）

```text
【準備】work/ はGit管理外なので作り直す
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r toraji_rice_burger_video/requirements.txt
python -m unidic download
bash toraji_rice_burger_video/tools/fetch_fonts.sh
cd toraji_rice_burger_video
python tools/tts_voice.py kokoro && python tools/tts_voice.py kokoro shorts   # ナレーション

【見積もり（無料）→ 生成（有料・上限200）】
python tools/hf_generate.py prepare
python tools/hf_generate.py estimate --budget 200
python tools/hf_generate.py run --budget 200
python tools/hf_generate.py status

【つなぎ込み】
python tools/render_video.py main --clips work/clips     # → output/toraji_rice_burger_main_1080p_clips.mp4
python tools/render_video.py shorts --clips work/clips   # → output/toraji_rice_burger_shorts_1080x1920_clips.mp4
```

## クリップの中身

| 種類 | 本数 | 入力（最初のフレーム） | 動き |
|---|---|---|---|
| 料理 | 27 | 高画質化したコマを16:9に切り出したもの（`work/clip_inputs/`） | `tools/scenes.json` の `motion`（例：卵を割り入れる、ソースをかける） |
| ソアちゃん | 3（S03・S28・S30） | 切り抜きを暖色のボケ背景に合成したもの | 手を振って話す／笑顔でうなずく／ガッツポーズ |

- 最初のフレームとして画像を渡すのは、絵コンテやソアちゃんの見た目をそろえるため。**完成動画には写真の静止画は出ない**（全シーンが動画。料理カット中の顔ワイプも出さない）
- 1本の長さはモデルの最短付近（3〜6秒）にしてクレジットを節約。場面より短いクリップはスロー再生（最低0.5倍）でつなぐ
- 生成に2回失敗したクリップだけは、その場面を写真のズーム表示で代用し、ログに素材名を出す

## 注意

- 【確定】ソアちゃんをAIで動かす許諾：ユーザー確認済み（本人・所属先・トラジ）
- 生成したクリップは公式の保存期間が「少なくとも7日」なので、`work/clips/` にダウンロードして保存する（スクリプトが自動で行う）
