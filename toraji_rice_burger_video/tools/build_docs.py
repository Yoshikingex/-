"""scenes.json と output/timings.json から、台本・プロンプト・チャプター・TTS原稿を生成する。

出力:
  docs/02_script_storyboard.md      … 台本＋絵コンテ（タイムコード付き）
  docs/03_higgsfield_prompts.md     … Higgsfield 用 画像/動画プロンプト（全カット）
  output/narration_for_tts.txt      … 音声合成に貼る原稿（読み仮名補正済み）
  output/youtube_chapters.txt       … 概要欄に貼るチャプター
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "tools" / "scenes.json").read_text(encoding="utf-8"))
tim = json.loads((ROOT / "output" / "timings.json").read_text(encoding="utf-8"))
T = {s["id"]: s for s in tim["scenes"]}
SC = cfg["scenes"]
STYLE = cfg["style_suffix"]

READINGS = cfg["tts_readings"]   # 読み補正の原本は scenes.json（tools/tts_voice.py と共通）


def tc(sec):
    m, s = divmod(int(round(sec)), 60)
    return f"{m}:{s:02d}"


# ---------- 02 台本 ----------
L = ["# 02 台本・絵コンテ（本編）", "",
     "> 自動生成：`tools/build_docs.py`（元データ `tools/scenes.json` ＋ 完成版の実測尺 `output/timings.json`）。直接編集せず scenes.json を直して再生成する。",
     f"> 総尺（完成版・終了画面20秒込み）：**{tc(tim['total_sec'])}**", "",
     f"- 【確定】シーン数 {len(SC)}／章 {len(dict.fromkeys(x['chapter'] for x in SC))}（オープニング〜エンディング）",
     f"- 【確定】主人公＝{cfg.get('host_name', 'ソア')}（焼肉トラジの看板娘）",
     "- 【確定】S14〜S16「時短ルート」＝市販品（トラジライスバーガー・スペシャル）を使う場面として採用", "",
     "| # | TC | 尺 | 章 | 映像（素材） | ナレーション（主人公の声） | テロップ | SE |",
     "|---|---|---|---|---|---|---|---|"]
for s in SC:
    t = T[s["id"]]
    vis = {"host": f"主人公（{s.get('host_shot')}）", "broll": s["img"], "title": s["img"] + "＋タイトル",
           "ingredients": s["img"] + "＋材料カード", "end": s["img"] + "＋終了画面"}[s["kind"]]
    if s.get("unconfirmed"):
        vis += " ⚠要確認"
    L.append(f"| {s['id']} | {tc(t['start'])} | {t['dur']:.1f}s | {s['chapter']} | {vis} | {s['narr']} | {' ／ '.join(s['telop'])} | {s.get('se', '')} |")
L += ["", "## 素材名の見方", "",
      "- `sb22_XX` = 22コマのストーリーボード（`assets/source/02_storyboard_22.jpg`）のXX番。切り出し済み：`assets/panels/sb22_XX.png`",
      "- `sb12_XX` = 12コマのストーリーボード（`assets/source/03_storyboard_12.png`）のXX番。切り出し済み：`assets/panels/sb12_XX.png`",
      "- `H1`〜`H5` = 主人公の出演カット（`docs/03_higgsfield_prompts.md` のプロンプトで生成）", "",
      "## 演出メモ（視聴維持のための設計）", "",
      "1. **最初の7秒で一番おいしい絵（黄身とろ〜りの断面）を見せる**：離脱が最も多い冒頭で「最後まで見る理由」を先に渡す",
      "2. S03 の自己紹介は12秒以内。長いと離脱するので、挨拶→料理名だけで即レシピへ",
      "3. 1カット2〜6秒でテンポよく。長いカット（S12・S17）は途中で寄り/引きの別テイクを挟む",
      "4. 組み立て（S20〜S25）は「焼肉→卵→トマト→ソース→レタス→バンズ」をリズムよく1語ずつ。SE「ポン」で気持ちよく",
      "5. S29 は冒頭 S01 と同じ断面カットの“回収”。同じクリップの別の区間を使う",
      "6. 終了画面（S31）は20秒。おすすめ動画1枠＋登録ボタン"]
(ROOT / "docs" / "02_script_storyboard.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ---------- 03 Higgsfield プロンプト ----------
H = (ROOT / "tools" / "higgsfield_header.md").read_text(encoding="utf-8")
P = [H, "", "## C. 料理カット（B-roll）全カット", "",
     "各カット：①参照画像（`assets/panels/…png`）をアップロード → ②**静止画プロンプト**で16:9高解像度に作り直す → ③できた静止画を**動画プロンプト**で5秒動画化。", "",
     f"**全カット共通の末尾スタイル（静止画プロンプトの最後に必ず付ける）**", "", "```", STYLE, "```", ""]
done = set()
for s in SC:
    if s["kind"] == "host" or s["img"] in done:
        continue
    done.add(s["img"])
    uses = [x["id"] for x in SC if x["img"] == s["img"]]
    P += [f"### {' / '.join(uses)}｜{s['chapter']}｜参照：`assets/panels/{s['img']}.png`" + ("　⚠市販品の確認後に生成" if s.get("unconfirmed") else ""), "",
          "```text",
          "【静止画｜16:9｜参照画像あり】",
          f"Recreate the reference image as a 16:9 high-resolution photo. {s['shot'][0].upper() + s['shot'][1:]}. {STYLE}",
          "",
          "【動画｜image-to-video｜5秒】",
          f"{s['motion'][0].upper() + s['motion'][1:]}. Realistic physics, natural food texture, no morphing, no extra hands, no text.",
          "```", ""]
(ROOT / "docs" / "03_higgsfield_prompts.md").write_text("\n".join(P) + "\n", encoding="utf-8")

# ---------- TTS原稿 ----------
N = ["# ナレーション原稿（音声合成に貼る用・読み仮名補正済み）",
     "# 1行=1シーン。行頭の [S01] はファイル名に使う（S01.mp3 …）。貼るときは [ ] 部分を除く。",
     "# 完成版の音声は tools/tts_voice.py がこの読み補正で自動生成済み（ElevenLabs等に差し替える場合に使う）。", ""]
for s in SC:
    txt = s["narr"]
    for a, b in READINGS:
        txt = txt.replace(a, b)
    N.append(f"[{s['id']}] {txt}")
(ROOT / "output" / "narration_for_tts.txt").write_text("\n".join(N) + "\n", encoding="utf-8")

# ---------- チャプター（YouTube規定：0:00開始・3個以上・各10秒以上） ----------
chap = []
for s in SC:
    if not chap or chap[-1][1] != s["chapter"]:
        chap.append([T[s["id"]]["start"], s["chapter"]])
merged = []
for i, (st, name) in enumerate(chap):
    nxt = chap[i + 1][0] if i + 1 < len(chap) else tim["total_sec"]
    if merged and nxt - st < 10:          # 10秒未満の章は前の章に統合
        merged[-1][1] += "・" + re.sub(r"^[①-⑳]", "", name)
        continue
    merged.append([st, name])
C = [f"{tc(st)} {name}" for st, name in merged]
C[0] = "0:00 " + merged[0][1]
(ROOT / "output" / "youtube_chapters.txt").write_text("\n".join(C) + "\n", encoding="utf-8")
print("docs written;", len(SC), "scenes;", len(done), "b-roll shots;", len(C), "chapters")
