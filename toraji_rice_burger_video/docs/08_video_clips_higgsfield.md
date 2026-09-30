# 08 動画クリップ版（写真を使わない完成版）｜Higgsfield API・200クレジット以内

## 結論

- 全31シーンを **30本の動画クリップ**（S01とS29は同じクリップを共有）で作り、つないで1本にする
- 生成は `tools/hf_generate.py`、つなぎ込みは `tools/render_video.py --clips work/clips`（テロップ・ナレーション・BGM・効果音は今の完成版と同じ）
- **予算200クレジットは、スクリプトが強制的に守る**：送る前に毎回見積もりを取り、「使用済み＋次の1本」が200を超えるなら送らずに止まる
- 【確定】失敗（failed）や規約で弾かれた（nsfw）生成は課金されない（Higgsfield公式ドキュメント「Billing and retention」）
- 【未確定】1本あたりのクレジット：モデルのページに記載がなく、あなたのアカウントで見積もりを取るまで分からない。候補7モデルを見積もり、予算の85%（170）以内に収まる中で品質が最も高いものを自動で選ぶ（15%は撮り直し用）

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
