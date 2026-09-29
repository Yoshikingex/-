"""LP ビフォーアフター縦型リール（1080x1920 / 30fps / 53秒）を組み立てる。

使い方:
  python3 make_music.py                      # output/bgm.wav を生成
  python3 build_video.py <素材mp4フォルダ>    # output/lp_before_after_reel.mp4 を生成

素材は「上=AFTER / 下=BEFORE」の縦動画(720x1280)5本。ファイル名の先頭8文字で識別する。
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
TMP = os.path.join(OUT, "_tmp")
FONTS = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30

# ---- タイムライン（make_music.py と共通。変えるなら両方） ----
HOOK_END = 3.0
REVEAL_END = 7.0
CASE_LEN = 8.0
CASE_SPLIT = 5.0
CASE_STARTS = [REVEAL_END + i * CASE_LEN for i in range(5)]
OUTRO = CASE_STARTS[-1] + CASE_LEN      # 47
OUTRO_LEN = 6.0
TOTAL = OUTRO + OUTRO_LEN               # 53

SRC_IDS = ["dff55191", "717474a4", "f0664387", "b4302077", "24585873"]
# 事例ごとの設定: カテゴリ / 分割表示の開始秒 / ハイライト開始秒 / 見どころ / 下段コピー
CASES = [
    dict(cat="高級車ブランド", split_ss=0.0, hl_ss=15.3,
         feat="メーター連動 × カラー切替", feat_sub="数値が動き、ボディカラーが切り替わる",
         copy="同じ情報でも、ここまで印象が変わる"),
    dict(cat="ケバブ専門店", split_ss=0.0, hl_ss=8.0,
         feat="具材が弾ける × 舞うスパイス", feat_sub="スクロールで“食べたい”が加速する",
         copy="“食べたい”を、スクロールで引き出す"),
    dict(cat="ヘアサロン", split_ss=0.0, hl_ss=19.5,
         feat="雫が舞う × 光の演出", feat_sub="世界観ごと、ブランドを伝える",
         copy="世界観そのものが、ブランドになる"),
    dict(cat="高級旅館", split_ss=0.0, hl_ss=18.5,
         feat="灯り × 花びらの余韻", feat_sub="予約ボタンまで、静かに導く",
         copy="予約前から、体験は始まっている"),
    dict(cat="パーソナルジム", split_ss=0.0, hl_ss=19.5,
         feat="走る文字 × 力強いCTA", feat_sub="最後の一押しまで、テンポで魅せる",
         copy="読ませるより、感じさせる"),
]
SPLIT_SPEED = 3.0   # 分割表示は3倍速（15秒ぶんを5秒で見せる）

# 素材の切り出し範囲（720x1280基準）: 上画面=AFTER / 下画面=BEFORE
AFTER_CROP = "720:620:0:0"
BEFORE_CROP = "720:620:0:660"
HOOK_CUTS = [(0, 6.0), (1, 6.0), (2, 7.0), (3, 6.0), (4, 6.0), (0, 12.0)]           # BEFORE
REVEAL_CUTS = [(0, 1.5), (1, 9.0), (2, 0.3), (3, 4.5), (4, 3.0), (0, 6.0), (1, 14.5), (3, 6.0)]  # AFTER
OUTRO_CELLS = [(0, 15.0), (1, 13.0), (2, 14.0), (3, 15.0), (4, 19.0)]  # 尺不足分は最終フレーム保持

COLOR_FIX = "scale=in_color_matrix=bt2020:out_color_matrix=bt709,setsar=1"
ENC = ["-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(" ".join(cmd))
        print(r.stderr[-3000:])
        sys.exit(1)


def card_chain(inp, label, crop, dur, border, zoom=0.06, punch=False):
    """素材の一部を中央カード化（背景=同じ映像のぼかし）。出力ラベル [<label>o]"""
    z = f"1+{zoom}*t/{dur}"
    if punch:
        z += "+0.08*max(0,1-t/0.25)"
    return (
        f"[{inp}]{COLOR_FIX},crop={crop},split[{label}a][{label}b];"
        f"[{label}a]scale=-2:{H},crop={W}:{H},boxblur=28:3,eq=brightness=-0.28:saturation=1.1[{label}bg];"
        f"[{label}b]scale=w='1072*({z})':h=-2:eval=frame,crop=1072:922:(iw-1072)/2:(ih-922)/2,"
        f"pad=1080:930:4:4:color={border}[{label}fg];"
        f"[{label}bg][{label}fg]overlay=(W-w)/2:(H-h)/2+40,trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[{label}o]"
    )


def seg_cards(name, cuts, crop, border, each=0.5):
    inputs, chains, labels = [], [], []
    for i, (vi, ss) in enumerate(cuts):
        inputs += ["-ss", str(ss), "-t", str(each + 0.3), "-i", SRC[vi]]
        chains.append(card_chain(f"{i}:v", f"v{i}", crop, each, border, zoom=0.05, punch=True))
        labels.append(f"[v{i}o]")
    fc = ";".join(chains) + ";" + "".join(labels) + f"concat=n={len(cuts)}:v=1:a=0[out]"
    path = os.path.join(TMP, f"{name}.mp4")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]", *ENC, path])
    return path


def seg_case(i):
    c = CASES[i]
    src = SRC[i]
    split_src = CASE_SPLIT * SPLIT_SPEED
    hl = CASE_LEN - CASE_SPLIT
    fc = (
        # 分割表示（元の上下画面をそのまま全面に・冒頭にズームパンチ）
        f"[0:v]{COLOR_FIX},setpts=(PTS-STARTPTS)/{SPLIT_SPEED},fps={FPS},"
        f"scale=w='{W}*(1+0.07*max(0,1-t/0.3))':h=-2:eval=frame,"
        f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2,trim=duration={CASE_SPLIT},setpts=PTS-STARTPTS,setsar=1[s];"
        + card_chain("1:v", "h", AFTER_CROP, hl, "0xFFD400", zoom=0.08, punch=True)
        + ";[s][ho]concat=n=2:v=1:a=0[out]"
    )
    path = os.path.join(TMP, f"case{i + 1}.mp4")
    run(["ffmpeg", "-y", "-v", "error",
         "-ss", str(c["split_ss"]), "-t", str(split_src + 0.5), "-i", src,
         "-ss", str(c["hl_ss"]), "-t", str(hl + 0.3), "-i", src,
         "-filter_complex", fc, "-map", "[out]", *ENC, path])
    return path


def seg_outro():
    cw, ch, gap = 520, 440, 14
    x0 = (W - (2 * cw + gap)) // 2
    y0 = 330
    inputs = []
    fc = [f"color=c=0x0B0B0D:s={W}x{H}:r={FPS}:d={OUTRO_LEN}[base0]"]
    # 背景: 1本目AFTERのぼかし
    inputs += ["-ss", "15", "-t", str(OUTRO_LEN + 0.3), "-i", SRC[0]]
    fc.append(f"[0:v]{COLOR_FIX},crop={AFTER_CROP},scale=-2:{H},crop={W}:{H},boxblur=30:3,"
              f"eq=brightness=-0.35,trim=duration={OUTRO_LEN},setpts=PTS-STARTPTS,fps={FPS}[bgv]")
    fc.append("[base0][bgv]overlay[base1]")
    prev = "base1"
    for k, (vi, ss) in enumerate(OUTRO_CELLS):
        inputs += ["-ss", str(ss), "-t", str(OUTRO_LEN + 0.3), "-i", SRC[vi]]
        n = k + 1
        x = x0 + (k % 2) * (cw + gap)
        y = y0 + (k // 2) * (ch + gap)
        fc.append(f"[{n}:v]{COLOR_FIX},crop={AFTER_CROP},scale={cw}:{ch}:force_original_aspect_ratio=increase,"
                  f"crop={cw}:{ch},trim=duration={OUTRO_LEN},setpts=PTS-STARTPTS,fps={FPS}[c{n}]")
        fc.append(f"[{prev}][c{n}]overlay={x}:{y}:enable='gte(t,{0.15 + 0.12 * k:.2f})'[b{n}]")
        prev = f"b{n}"
    # 6マス目（YOUR LP?）の下地
    x = x0 + cw + gap
    y = y0 + 2 * (ch + gap)
    fc.append(f"color=c=0x141416:s={cw}x{ch}:r={FPS}:d={OUTRO_LEN}[c6]")
    fc.append(f"[{prev}][c6]overlay={x}:{y}:enable='gte(t,0.75)',trim=duration={OUTRO_LEN},setsar=1[out]")
    path = os.path.join(TMP, "outro.mp4")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]", *ENC, path])
    return path, (x + cw // 2, y + ch // 2)


# ------------------------------------------------------------------ ASS テロップ
def ts(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


YEL = "&H0000D4FF&"
WHT = "&H00FFFFFF&"
BLK = "&H00000000&"
POP = r"\fscx135\fscy135\t(0,140,\fscx100\fscy100)"


def ev(events, t0, t1, text, style="Base", layer=1):
    events.append(f"Dialogue: {layer},{ts(t0)},{ts(t1)},{style},,0,0,0,,{text}")


def box(x, y, w, h, color="&H000000&", alpha="&H50&", an=7):
    return (rf"{{\an{an}\pos({x},{y})\bord0\shad0\1c{color}\1a{alpha}\p1}}"
            f"m 0 0 l {w} 0 l {w} {h} l 0 {h}{{\\p0}}")


def flash(events, t, dur=0.22, a="&H00&"):
    ev(events, t, t + dur, rf"{{\an7\pos(0,0)\bord0\shad0\1c&HFFFFFF&\1a{a}\fad(0,{int(dur * 1000)})\p1}}"
       f"m 0 0 l {W} 0 l {W} {H} l 0 {H}{{\\p0}}", layer=9)


def tag(events, t0, t1, text, bg, fg):
    ev(events, t0, t1, box(40, 470, 20 + 34 * len(text), 60, bg, "&H00&") , layer=3)
    ev(events, t0, t1, rf"{{\an4\pos(58,500)\fnNoto Sans JP Black\fs36\1c{fg}\bord0\shad0}}{text}", layer=4)


def build_ass(cell6_center):
    e = []
    # ---------- HOOK 0-3 ----------
    tag(e, 0, HOOK_END, "BEFORE｜よくある静止LP", "&H3A3A3A&", WHT)
    ev(e, 0.05, 1.5, rf"{{\an5\pos(540,270)\fs140{POP}}}そのLP、")
    ev(e, 1.5, HOOK_END, rf"{{\an5\pos(540,270)\fs140\1c{YEL}{POP}}}止まってない？")
    ev(e, 0.4, HOOK_END, rf"{{\an5\pos(540,1580)\fnNoto Sans JP Black\fs48\fad(150,0)}}スクロールしても、何も起きない…")
    flash(e, HOOK_END, 0.3)
    # ---------- REVEAL 3-7 ----------
    tag(e, HOOK_END, REVEAL_END, "AFTER｜スクロール連動LP", "&H0000D4FF&", BLK)
    ev(e, 3.05, 4.8, rf"{{\an5\pos(540,190)\fnNoto Sans JP Black\fs64\fad(80,0)}}スクロールするだけで")
    ev(e, 3.3, 4.8, rf"{{\an5\pos(540,330)\fs130\1c{YEL}{POP}}}LPが動き出す。")
    ev(e, 4.8, REVEAL_END, rf"{{\an5\pos(540,200)\fs96{POP}}}静止LP ▶ 動くLP")
    ev(e, 4.8, REVEAL_END, rf"{{\an5\pos(540,330)\fnNoto Sans JP Black\fs52\fad(100,0)}}ビフォーアフター")
    ev(e, 5.0, REVEAL_END, rf"{{\an5\pos(540,1600)\fnAnton\fs170\1c{YEL}{POP}}}5 CASES")
    ev(e, 5.2, REVEAL_END, rf"{{\an5\pos(540,1740)\fnNoto Sans JP Black\fs46\fad(100,0)}}実例で、違いを見てください")
    # ---------- CASES ----------
    for i, (cs, c) in enumerate(zip(CASE_STARTS, CASES)):
        ce = cs + CASE_LEN
        sp = cs + CASE_SPLIT
        n = f"{i + 1:02d}"
        flash(e, cs, 0.22)
        # ヘッダー（上部の暗いエリア）
        ev(e, cs, ce, box(0, 0, W, 250, "&H000000&", "&H60&"), layer=0)
        ev(e, cs, ce, rf"{{\an7\fnAnton\fs92\1c{YEL}\move(-300,40,48,40,0,220)}}CASE {n}")
        ev(e, cs + 0.08, ce, rf"{{\an7\fs68\move(-500,150,48,150,0,240)}}{c['cat']}")
        ev(e, cs, ce, rf"{{\an9\pos(1032,48)\fnAnton\fs60\1a&H40&\3a&H40&}}{n}/05")
        # 分割表示: 中央の区切りラベル
        ev(e, cs, sp, box(0, 932, W, 86, "&H000000&", "&H30&"), layer=2)
        ev(e, cs + 0.1, sp, rf"{{\an4\pos(40,975)\fnNoto Sans JP Black\fs40\1c{YEL}\fad(120,0)}}▲ AFTER：スクロール連動", layer=3)
        ev(e, cs + 0.1, sp, rf"{{\an6\pos(1040,975)\fnNoto Sans JP Black\fs40\1c&HDDDDDD&\fad(120,0)}}BEFORE：静止 ▼", layer=3)
        # 下段コピー
        ev(e, cs + 0.4, sp, box(0, 1790, W, 100, "&H000000&", "&H40&"), layer=2)
        ev(e, cs + 0.4, sp, rf"{{\an5\pos(540,1840)\fnNoto Sans JP Black\fs48\fad(150,0)}}{c['copy']}", layer=3)
        # ハイライト（AFTER拡大）
        flash(e, sp, 0.18, "&H60&")
        tag(e, sp, ce, "AFTER", "&H0000D4FF&", BLK)
        ev(e, sp + 0.05, ce, rf"{{\an5\pos(540,360)\fs76\1c{YEL}{POP}}}{c['feat']}")
        ev(e, sp + 0.25, ce, rf"{{\an5\pos(540,1570)\fnNoto Sans JP Black\fs48\fad(150,0)}}{c['feat_sub']}")
    # ---------- OUTRO ----------
    flash(e, OUTRO, 0.3)
    ev(e, OUTRO + 0.05, TOTAL, rf"{{\an5\pos(540,110)\fnNoto Sans JP Black\fs62\fad(120,0)}}あなたのLPも、")
    ev(e, OUTRO + 0.3, TOTAL, rf"{{\an5\pos(540,235)\fs128\1c{YEL}{POP}}}“動くLP”へ。")
    cx, cy = cell6_center
    ev(e, OUTRO + 0.8, TOTAL, rf"{{\an5\pos({cx},{cy - 60})\fnAnton\fs80{POP}}}NEXT")
    ev(e, OUTRO + 0.95, TOTAL, rf"{{\an5\pos({cx},{cy + 50})\fnAnton\fs96\1c{YEL}{POP}}}YOUR LP?")
    ev(e, OUTRO + 1.4, TOTAL, rf"{{\an5\pos(540,1765)\fs58{POP}}}制作のご相談はプロフィールから")
    ev(e, OUTRO + 1.9, TOTAL, rf"{{\an5\pos(540,1860)\fnNoto Sans JP Black\fs42\1c{YEL}\fad(150,0)}}保存して、あとで見返してください")
    # ---------- 進捗バー（最下部） ----------
    ev(e, 0, TOTAL, rf"{{\an7\pos(0,1910)\bord0\shad0\1c&H0000D4FF&\clip(0,1910,0,1920)"
                    rf"\t(0,{int(TOTAL * 1000)},\clip(0,1910,{W},1920))\p1}}m 0 0 l {W} 0 l {W} 10 l 0 10{{\p0}}", layer=8)

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Dela Gothic One,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,6,4,5,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    path = os.path.join(OUT, "telop.ass")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(e) + "\n")
    return path


def main():
    global SRC
    src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "src")
    SRC = []
    for sid in SRC_IDS:
        m = glob.glob(os.path.join(src_dir, f"*{sid}*.mp4"))
        if not m:
            sys.exit(f"素材が見つかりません: {sid} in {src_dir}")
        SRC.append(m[0])
    os.makedirs(TMP, exist_ok=True)
    bgm = os.path.join(OUT, "bgm.wav")
    if not os.path.exists(bgm):
        sys.exit("先に python3 make_music.py を実行してください")

    parts = [seg_cards("hook", HOOK_CUTS, BEFORE_CROP, "0x8A8A8A"),
             seg_cards("reveal", REVEAL_CUTS, AFTER_CROP, "0xFFD400")]
    for i in range(5):
        parts.append(seg_case(i))
    outro, c6 = seg_outro()
    parts.append(outro)
    print("segments ok")

    ass = build_ass(c6)
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    final = os.path.join(OUT, "lp_before_after_reel.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", bgm,
         "-filter_complex", f"[0:v]subtitles={ass}:fontsdir={FONTS}[v]",
         "-map", "[v]", "-map", "1:a", "-t", str(TOTAL),
         "-c:v", "libx264", "-crf", "19", "-preset", "slow", "-maxrate", "9M", "-bufsize", "18M",
         "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final])
    print("wrote", final)


if __name__ == "__main__":
    main()
