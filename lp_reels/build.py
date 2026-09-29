"""LP ビフォーアフター縦型リールを 1素材=1本 で生成する。

  python3 build.py <素材mp4フォルダ> [car kebab salon ryokan gym]

処理: 画面の台形補正 → 色補正(黒を締めて色かぶり除去) → テーマ別レイアウト/テロップ(ASS) →
      Mixkitの曲をドロップ位置に合わせて配置 + 効果音 → 1080x1920/30fps/H.264
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from themes import THEMES, HOOK, END_LEN, COMMON_END

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
CACHE = os.path.join(HERE, "_cache")        # 曲・効果音のダウンロード先（git管理外）
FONTS = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30

# レイアウト
CW, CH, CX = 1000, 660, 40      # 分割表示のカード
A_Y, B_Y = 330, 1060            # AFTER / BEFORE カード上端
HW, HH = 1040, 686              # ヒーロー（AFTER単独）カード
HX, HY = 20, 540
RADIUS = 26
CAP_Y1, CAP_Y2 = 1786, 1846     # 見どころキャプション（英字 / 日本語）


def use_rec_layout():
    """画面録画(16:9)用レイアウト。キャプションはInstagramのUIに隠れない高さへ上げる"""
    global CW, CH, CX, A_Y, B_Y, HW, HH, HX, HY, CAP_Y1, CAP_Y2
    CW, CH, CX = 1040, 585, 20
    A_Y, B_Y = 330, 990
    HW, HH, HX, HY = 1040, 585, 20, 600
    CAP_Y1, CAP_Y2 = 1650, 1712

EDGES = json.load(open(os.path.join(HERE, "edges.json")))
LEVELS = json.load(open(os.path.join(HERE, "levels.json")))
DROPS = json.load(open(os.path.join(HERE, "drops.json")))


def sh(cmd, capture=False):
    r = subprocess.run(cmd, capture_output=True, text=not capture)
    if r.returncode != 0:
        print(" ".join(map(str, cmd))[:3000])
        print((r.stderr if not capture else r.stderr.decode())[-3000:])
        sys.exit(1)
    return r.stdout


def fetch(url, path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sh(["curl", "-sSL", "-m", "120", "-o", path, url])
    return path


def music_path(n):
    return fetch(f"https://assets.mixkit.co/music/{n}/{n}.mp3", os.path.join(CACHE, f"music_{n}.mp3"))


def sfx_path(n):
    return fetch(f"https://assets.mixkit.co/active_storage/sfx/{n}/{n}-preview.mp3", os.path.join(CACHE, f"sfx_{n}.mp3"))


def duration(path):
    out = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True).stderr
    h, m, s = out.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def peak_time(path):
    raw = sh(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture=True)
    a = np.abs(np.frombuffer(raw, np.int16).astype(float))
    env = np.convolve(a, np.ones(400) / 400, "same")
    return float(np.argmax(env) / 8000)


def beats_of(track, start):
    import librosa
    y, sr = librosa.load(music_path(track), sr=22050, offset=start, duration=40)
    _, b = librosa.beat.beat_track(y=y, sr=sr, units="time")
    return np.array(b)


# ------------------------------------------------------------------ 画像アセット
def rgba(c, a):
    return (c[0], c[1], c[2], int(a * 255))


def rounded_mask(w, h, r, scale=4):
    m = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * scale - 1, h * scale - 1], r * scale, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def make_assets(key, t, d):
    os.makedirs(d, exist_ok=True)
    base, acc, light = t["base"], t["accent"], t["light"]
    # 1) 全体のトーン（ベース色の縦グラデーション + ビネット）
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    yy = np.linspace(-1, 1, H)[:, None]
    vign = np.clip(np.sqrt((x * 0.9) ** 2 + (yy * 0.75) ** 2), 0, 1.4)
    if light:
        alpha = 0.80 + 0.10 * vign ** 2
    else:
        alpha = 0.50 + 0.28 * (np.abs(y - 0.5) * 2) ** 1.5 + 0.30 * vign ** 2
    alpha = np.clip(alpha, 0, 0.96)
    img = np.zeros((H, W, 4), np.uint8)
    img[..., :3] = base
    img[..., 3] = (alpha * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(f"{d}/tint.png")

    def shadow_layer(rects, strength):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        for (x0, y0, w, h) in rects:
            dr.rounded_rectangle([x0, y0 + 18, x0 + w, y0 + h + 18], RADIUS, fill=(0, 0, 0, int(255 * strength)))
        return lay.filter(ImageFilter.GaussianBlur(28))

    def frame_layer(items):
        lay = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        for (x0, y0, w, h, col, a, wd) in items:
            dr.rounded_rectangle([x0 * 2, y0 * 2, (x0 + w) * 2 - 1, (y0 + h) * 2 - 1], RADIUS * 2,
                                 outline=rgba(col, a), width=wd * 2)
        return lay.resize((W, H), Image.LANCZOS)

    s = 0.22 if light else 0.65
    shadow_layer([(CX, A_Y, CW, CH), (CX, B_Y, CW, CH)], s).save(f"{d}/shadow_split.png")
    shadow_layer([(HX, HY, HW, HH)], s).save(f"{d}/shadow_hero.png")
    neutral = (120, 110, 100) if light else (255, 255, 255)
    frame_layer([(CX, A_Y, CW, CH, acc, 0.95, 2), (CX, B_Y, CW, CH, neutral, 0.28, 2)]).save(f"{d}/frame_split.png")
    frame_layer([(HX, HY, HW, HH, acc, 0.95, 2)]).save(f"{d}/frame_hero.png")
    rounded_mask(CW, CH, RADIUS).save(f"{d}/mask.png")
    rounded_mask(HW, HH, RADIUS).save(f"{d}/mask_hero.png")
    # 2) AFTER登場前のガラス調プレースホルダー
    ph = Image.new("RGBA", (CW, CH), rgba(base, 0.55 if not light else 0.6))
    g = np.linspace(0, 1, CH)[:, None] * np.ones((1, CW))
    sheen = Image.fromarray(((1 - g) * 38).astype(np.uint8), "L")
    white = Image.new("RGBA", (CW, CH), (255, 255, 255, 0))
    white.putalpha(sheen)
    ph = Image.alpha_composite(ph, white)
    ph.putalpha(Image.fromarray(np.minimum(np.array(ph.split()[3]), np.array(rounded_mask(CW, CH, RADIUS)))))
    ph.save(f"{d}/placeholder.png")


# ------------------------------------------------------------------ 映像
def quad(e, a, b):
    return (f"perspective=0:{e[a]['y0']:.1f}:720:{e[a]['y720']:.1f}:0:{e[b]['y0']:.1f}:720:{e[b]['y720']:.1f}"
            ":interpolation=cubic")


def grade(L, which):
    lo, hi = L[which]["lo"], L[which]["hi"]
    cl = ":".join(f"{c}imin={lo[i] / 255:.3f}:{c}imax={hi[i] / 255:.3f}" for i, c in enumerate("rgb"))
    if which == "after":
        return (f"colorlevels={cl},curves=all='0/0 0.32/0.12 0.52/0.33 0.72/0.63 0.9/0.9 1/1',"
                "eq=saturation=1.28,unsharp=5:5:0.9:3:3:0.0")
    return (f"colorlevels={cl}:romax=0.985:gomax=0.985:bomax=0.985,curves=all='0/0 0.25/0.2 0.5/0.52 1/1',"
            "eq=saturation=1.15,unsharp=5:5:0.7:3:3:0.0")


def build_video(key, t, srcs, times, ass, d, out):
    S, DEND, TOTAL = times["S"], times["DEND"], times["TOTAL"]
    img = lambda p: ["-loop", "1", "-t", f"{TOTAL:.3f}", "-framerate", str(FPS), "-i", f"{d}/{p}"]
    images = img("tint.png") + img("shadow_split.png") + img("frame_split.png") + \
        img("mask.png") + img("shadow_hero.png") + img("frame_hero.png") + img("mask_hero.png") + img("placeholder.png")
    if "rec" in t:
        # 画面録画: AFTER/BEFORE 別ファイル。補正不要、AFTERは HOOK 秒遅らせて冒頭から見せる
        off = t["rec"]["offset"]
        pa = TOTAL - off - duration(srcs["after"]) + 0.5
        pb = TOTAL - duration(srcs["before"]) + 0.5
        inputs = ["-i", srcs["after"], "-i", srcs["before"]] + images
        n0 = 2
        src_fc = [
            f"[0:v]setsar=1,fps={FPS},tpad=start_mode=clone:start_duration={off:.2f}:"
            f"stop_mode=clone:stop_duration={max(pa, 0.1):.2f},split=3[a0][a1][a2]",
            f"[1:v]setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration={max(pb, 0.1):.2f},"
            f"scale={CW}:{CH}:flags=lanczos,format=rgba[b0]",
        ]
    else:
        e = EDGES[str(t["idx"])]
        L = LEVELS[str(t["idx"])]
        crop = "crop=iw*0.98:ih*0.94:iw*0.01:ih*0.025"
        inputs = ["-i", srcs["src"]] + images
        n0 = 1
        pad = TOTAL - duration(srcs["src"]) + 0.5
        src_fc = [
            f"[0:v]scale=in_color_matrix=bt2020:out_color_matrix=bt709,setsar=1,fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration={max(pad, 0.1):.2f},split=2[sa][sb]",
            f"[sa]{quad(e, 't1', 'b1')},{crop},{grade(L, 'after')},split=3[a0][a1][a2]",
            f"[sb]{quad(e, 't2', 'b2')},{crop},{grade(L, 'before')},scale={CW}:{CH}:flags=lanczos,format=rgba[b0]",
        ]
    i = lambda k: f"[{n0 + k}:v]"   # 画像入力: 0 tint 1 shadow_split 2 frame_split 3 mask 4 shadow_hero 5 frame_hero 6 mask_hero 7 placeholder
    fc = src_fc + [
        # 背景: AFTER映像を大きくぼかしたアンビエント光 + テーマ色
        f"[a2]scale=-2:192,crop=108:192,gblur=sigma=5,scale={W}:{H}:flags=bicubic,"
        f"eq=brightness={t['amb_bright']}:saturation={t['amb_sat']},format=rgba[amb]",
        f"[amb]{i(0)}overlay=format=auto,noise=alls=5:allf=t,format=rgba[bg]",
        f"[a0]scale={CW}:{CH}:flags=lanczos,format=rgba[a0s]",
        f"{i(3)}format=gray,split[m1][m2]",
        f"[a0s][m1]alphamerge,fade=t=in:st={HOOK:.2f}:d=0.22:alpha=1[acard]",
        "[b0][m2]alphamerge[bcard]",
        f"[a1]scale={HW}:{HH}:flags=lanczos,format=rgba[a1s]",
        f"{i(6)}format=gray[mh]", "[a1s][mh]alphamerge[hcard]",
        f"[bg]{i(1)}overlay=enable='lt(t,{S:.3f})'[v1]",
        f"[v1]{i(7)}overlay={CX}:{A_Y}:enable='lt(t,{HOOK + 0.2:.3f})'[v2]",
        f"[v2][acard]overlay={CX}:{A_Y}:enable='lt(t,{S:.3f})'[v3]",
        f"[v3][bcard]overlay={CX}:{B_Y}:enable='lt(t,{S:.3f})'[v4]",
        f"[v4]{i(2)}overlay=enable='lt(t,{S:.3f})'[v5]",
        f"[v5]{i(4)}overlay=enable='between(t,{S:.3f},{DEND:.3f})'[v6]",
        f"[v6][hcard]overlay={HX}:{HY}:enable='between(t,{S:.3f},{DEND:.3f})'[v7]",
        f"[v7]{i(5)}overlay=enable='between(t,{S:.3f},{DEND:.3f})'[v8]",
        f"[v8]subtitles={ass}:fontsdir={FONTS},trim=duration={TOTAL:.3f},setsar=1,format=yuv420p[out]",
    ]
    sh(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[out]",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-an", out])


# ------------------------------------------------------------------ 音
def koto_layer(total, hook, sr=44100):
    """旅館用: 琴風の撥弦（Karplus-Strong）と鈴の音を合成（F都節音階）"""
    rng = np.random.default_rng(3)
    outp = np.zeros(int(sr * total))

    def pluck(f, dur=2.5, bright=0.5):
        n = int(sr * dur)
        p = max(2, int(sr / f))
        buf = rng.uniform(-1, 1, p)
        buf = np.convolve(buf, [bright, 1 - bright], "same")
        y = np.zeros(n)
        for i in range(n):
            y[i] = buf[i % p]
            buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
        return y * np.exp(-np.arange(n) / (sr * 1.2))

    def bell(f, dur=5.0):
        tt = np.arange(int(sr * dur)) / sr
        parts = [(1, 1, 3.5), (2.76, 0.5, 2.0), (5.4, 0.25, 1.2), (8.9, 0.12, 0.7)]
        return sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / dcy) for r, a, dcy in parts) / 1.9

    def put(x, at, g):
        i = int(at * sr)
        x = x[: len(outp) - i]
        outp[i:i + len(x)] += g * x

    F4 = 349.23
    scale = [0, 1, 5, 7, 8, 12, 13, 17]  # F Gb Bb C Db F Gb Bb（都節）
    freq = lambda s: F4 * 2 ** (s / 12)
    put(bell(F4 / 2), hook, 0.35)
    phrase = [(0.0, 7), (0.35, 5), (0.7, 4), (1.4, 3), (2.8, 5), (3.15, 6), (3.5, 7), (4.9, 4)]
    tt = hook + 0.2
    while tt < total - 3:
        for off, s in phrase:
            if tt + off < total - 3:
                put(pluck(freq(scale[s])), tt + off, 0.22)
        tt += 7.0
    put(bell(F4), total - END_LEN, 0.25)
    return outp


def build_audio(key, t, times, out_wav):
    TOTAL, S, DEND = times["TOTAL"], times["S"], times["DEND"]
    start = times["music_start"]
    tmp = os.path.join(CACHE, f"{key}_layers")
    os.makedirs(tmp, exist_ok=True)
    inputs = ["-ss", f"{start:.3f}", "-t", f"{TOTAL + 0.5:.3f}", "-i", music_path(t["music"])]
    sfx = [("1492", HOOK, 0.7), (t["sfx_reveal"], HOOK, 0.55), (t["sfx_hero"], S, 0.55), ("1489", DEND, 0.45)]
    for n, _, _ in sfx:
        inputs += ["-i", sfx_path(n)]
    fc = [f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit[m1][m2]",
          f"[m1]atrim=0:{HOOK:.3f},lowpass=f=500,lowpass=f=500,volume=1.4[pre]",
          f"[m2]atrim={HOOK:.3f},asetpts=PTS-STARTPTS[post]",
          f"[pre][post]concat=n=2:v=0:a=1,afade=t=in:d=0.3,afade=t=out:st={TOTAL - 1.6:.3f}:d=1.6,volume=0.9[mus]"]
    mix = ["[mus]"]
    for k, (n, at, g) in enumerate(sfx):
        pk = peak_time(sfx_path(n)) if n != "2350" else 0.3
        delay = max(0, int((at - pk) * 1000))
        fc.append(f"[{k + 1}:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay={delay}|{delay},volume={g}[s{k}]")
        mix.append(f"[s{k}]")
    if t.get("koto"):
        from scipy.io import wavfile
        kp = os.path.join(tmp, "koto.wav")
        k = koto_layer(TOTAL, HOOK)
        k = k / (np.max(np.abs(k)) + 1e-9) * 0.8
        wavfile.write(kp, 44100, (np.stack([k, k], 1) * 32767).astype(np.int16))
        inputs += ["-i", kp]
        fc.append(f"[{len(sfx) + 1}:a]aecho=0.8:0.6:120|260:0.3|0.2,volume=0.55[koto]")
        mix.append("[koto]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
              f"atrim=0:{TOTAL:.3f},loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    sh(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[a]",
        "-ar", "44100", out_wav])


# ------------------------------------------------------------------ テロップ（ASS）
def ac(c):
    return f"&H{c[2]:02X}{c[1]:02X}{c[0]:02X}&"


def ts(x):
    x = max(0.0, x)
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


def build_ass(key, t, times, path):
    S, DEND, TOTAL = times["S"], times["DEND"], times["TOTAL"]
    TX, SUB, ACC, BASE = ac(t["text"]), ac(t["sub"]), ac(t["accent"]), ac(t["base"])
    light = t["light"]
    punch = key == "gym"
    shadow = "" if light else r"\shad2\4c&H000000&\4a&H70&"
    ev = []

    def add(t0, t1, txt, layer=5):
        ev.append(f"Dialogue: {layer},{ts(t0)},{ts(t1)},Base,,0,0,0,,{txt}")

    def reveal(x, y, dur_in=450, rise=18, an=5, fade_out=250):
        if punch:
            return (rf"\an{an}\move({x - 60},{y},{x},{y},0,180)\fscx112\fscy112\t(0,180,\fscx100\fscy100)"
                    rf"\fad(80,{fade_out})")
        return rf"\an{an}\move({x},{y + rise},{x},{y},0,{dur_in})\blur7\t(0,{dur_in},\blur0)\fad({dur_in},{fade_out})"

    def txt(font, size, color, sp=0, bold=0, italic=0):
        return rf"\fn{font}\fs{size}\1c{color}\fsp{sp}\b{bold}\i{italic}\bord0{shadow}"

    def rule(x, y, w, t0, t1, color=ACC, alpha="&H30&"):
        add(t0, t1, rf"{{\an7\pos({x},{y})\bord0\shad0\1c{color}\1a{alpha}"
                    rf"\clip({x},{y},{x},{y + 2})\t(0,500,\clip({x},{y},{x + w},{y + 2}))\fad(0,200)\p1}}"
                    f"m 0 0 l {w} 0 l {w} 2 l 0 2{{\\p0}}", layer=4)

    # ヘッダー（ブランド名 + カテゴリ）: 全編
    bi = 1 if t.get("brand_italic") else 0
    add(0, TOTAL, rf"{{{reveal(540, 150, 700)}{txt(t['brand_font'], t['brand_size'], TX, t['brand_sp'], 0, bi)}}}{t['brand']}")
    add(0.2, TOTAL, rf"{{{reveal(540, 238, 700)}{txt(t['f_lbl'], 24, SUB, 9)}}}{t['category']}  ·  LP BEFORE / AFTER")

    # カードのラベル（分割表示中）
    add(HOOK, S, rf"{{\an1\pos({CX + 6},{A_Y - 16})\fad(300,0){txt(t['f_lbl'], 30, ACC, 8, 1)}}}AFTER"
                 rf"{{{txt(t['f_jp'], 26, SUB, 2)}}}   スクロール連動LP")
    add(0.1, S, rf"{{\an1\pos({CX + 6},{B_Y - 16})\fad(300,0){txt(t['f_lbl'], 30, SUB, 8, 1)}}}BEFORE"
                rf"{{{txt(t['f_jp'], 26, SUB, 2)}}}   静止LP")

    # フック（0〜HOOK）: AFTERカード位置に問いかけ
    cy = A_Y + CH // 2
    h1, h2 = t["hook"]
    add(0.05, HOOK - 0.02, rf"{{{reveal(540, cy - 48, 400, fade_out=120)}{txt(t['f_jp'], 44, SUB, 4)}}}{h1}")
    add(0.35, HOOK - 0.02, rf"{{{reveal(540, cy + 40, 450, fade_out=120)}{txt(t['f_jp'], 64, TX, 3, 1)}}}{h2}")
    add(0.6, HOOK - 0.02, rf"{{\an5\pos(540,{cy + 130})\fad(300,100){txt(t['f_lbl'], 22, ACC, 12)}}}SCROLL  ↓  AFTER")

    # AFTER登場: フラッシュ + 光のスイープ
    add(HOOK, HOOK + 0.35, rf"{{\an7\pos({CX},{A_Y})\bord0\shad0\1c&HFFFFFF&\1a&H40&\fad(0,320)\p1}}"
                           f"m 0 0 l {CW} 0 l {CW} {CH} l 0 {CH}{{\\p0}}", layer=6)
    add(HOOK, HOOK + 0.7, rf"{{\an7\clip({CX},{A_Y},{CX + CW},{A_Y + CH})\move({CX - 400},{A_Y},{CX + CW + 100},{A_Y},0,650)"
                          rf"\bord0\shad0\1c&HFFFFFF&\1a&H90&\blur20\p1}}m 120 0 l 260 0 l 140 {CH} l 0 {CH}{{\p0}}", layer=6)

    # 見どころキャプション（下段）
    for (c0, c1, en, jp) in t["captions"]:
        c1 = min(c1, S - 0.1)
        add(c0, c1, rf"{{{reveal(540, CAP_Y1, 400)}{txt(t['f_lbl'], 24, ACC, 10, 1)}}}{en}")
        add(c0 + 0.1, c1, rf"{{{reveal(540, CAP_Y2, 450)}{txt(t['f_jp'], 46, TX, 3, 1)}}}{jp}")

    # ヒーロー（AFTER単独）
    add(S, DEND, rf"{{\an1\pos({HX + 6},{HY - 16})\fad(250,0){txt(t['f_lbl'], 30, ACC, 8, 1)}}}AFTER")
    c1_, c2_ = t["hero_copy"]
    add(S + 0.15, DEND, rf"{{{reveal(540, HY + HH + 110, 450, fade_out=200)}{txt(t['f_jp'], 46, SUB, 4)}}}{c1_}")
    add(S + 0.4, DEND, rf"{{{reveal(540, HY + HH + 200, 500, fade_out=200)}{txt(t['f_jp'], 74, ACC, 4, 1)}}}{c2_}")
    add(S, S + 0.3, rf"{{\an7\pos(0,0)\bord0\shad0\1c&HFFFFFF&\1a&H70&\fad(0,280)\p1}}m 0 0 l {W} 0 l {W} {H} l 0 {H}{{\p0}}", layer=6)

    # エンドカード
    add(DEND, TOTAL, rf"{{\an7\pos(0,0)\bord0\shad0\1c{BASE}\1a&H50&\fad(350,0)\p1}}m 0 0 l {W} 0 l {W} {H} l 0 {H}{{\p0}}", layer=3)
    add(DEND + 0.1, TOTAL, rf"{{{reveal(540, 700, 500)}{txt(t['f_lbl'], 28, ACC, 14, 1)}}}BEFORE  →  AFTER")
    add(DEND + 0.3, TOTAL, rf"{{{reveal(540, 880, 600)}{txt(t['f_jp'], 72, TX, 4, 1)}\q2}}{COMMON_END['main']}")
    rule(390, 1050, 300, DEND + 0.7, TOTAL)
    add(DEND + 0.8, TOTAL, rf"{{{reveal(540, 1130, 450)}{txt(t['f_jp'], 36, TX, 2)}}}{COMMON_END['cta']}")
    add(DEND + 1.1, TOTAL, rf"{{{reveal(540, 1210, 450)}{txt(t['f_lbl'], 22, SUB, 6)}}}{COMMON_END['save']}")

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{t['f_jp']},48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(ev) + "\n")


# ------------------------------------------------------------------ main
def plan(t, srcs):
    dr = DROPS[t.get("drop_key") or {"dff55191": "car", "717474a4": "kebab", "f0664387": "salon",
                                     "b4302077": "ryokan", "24585873": "gym"}[t["src"]]]
    start = dr["drop"] - HOOK
    beats = beats_of(t["music"], start)
    snap = lambda x, lim=0.35: float(beats[np.argmin(np.abs(beats - x))]) if np.min(np.abs(beats - x)) < lim else x
    if "rec" in t:
        S, DEND = snap(t["rec"]["hero_v"]), snap(t["rec"]["dend_v"])
    else:
        S, DEND = snap(t["hero"]), snap(duration(srcs["src"]) - 0.1)
    return dict(S=S, DEND=DEND, TOTAL=DEND + END_LEN, music_start=start)


def main():
    src_dir = sys.argv[1]
    keys = sys.argv[2:] or list(THEMES)
    os.makedirs(OUT, exist_ok=True)
    for key in keys:
        t = THEMES[key]
        find = lambda tag: glob.glob(os.path.join(src_dir, f"*{tag}*.mp4"))[0]
        if "rec" in t:
            use_rec_layout()
            srcs = dict(after=find(t["rec"]["after"]), before=find(t["rec"]["before"]))
        else:
            srcs = dict(src=find(t["src"]))
        d = os.path.join(CACHE, key)
        make_assets(key, t, d)
        times = plan(t, srcs)
        print(key, {k: round(v, 2) for k, v in times.items()})
        ass = os.path.join(d, "telop.ass")
        build_ass(key, t, times, ass)
        vid = os.path.join(d, "video.mp4")
        wav = os.path.join(d, "audio.wav")
        build_audio(key, t, times, wav)
        build_video(key, t, srcs, times, ass, d, vid)
        out_dir = os.path.join(OUT, "rec") if "rec" in t else OUT
        os.makedirs(out_dir, exist_ok=True)
        final = os.path.join(out_dir, f"{t['idx'] + 1:02d}_{key.replace('_rec', '')}.mp4")
        sh(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final])
        print("wrote", final)


if __name__ == "__main__":
    main()
