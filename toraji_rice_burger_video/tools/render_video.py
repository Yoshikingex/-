"""完成版動画をレンダリングする（本編 1920x1080 / ショート 1080x1920）。

素材: 高画質化したコマ(assets/panels_hd) ＋ ソアちゃん(assets/panels/host_cutout.png)
音声: ナレーション(work/voice_kokoro) ＋ 効果音・BGM(assets/audio)
使い方: python tools/render_video.py main   → output/toraji_rice_burger_main_1080p.mp4 ＋ 字幕・チャプター・timings
        python tools/render_video.py shorts → output/toraji_rice_burger_shorts_1080x1920.mp4
        python tools/render_video.py main --clips work/clips   → 動画クリップ版（写真は使わない）…_clips.mp4
シーンごとに4並列でレンダリングし、最後に連結して音声を重ねる。
"""
import json
import re
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
OUT = ROOT / "output"
WORK = ROOT / "work"
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
FPS = 30
XF = 6                   # クロスフェード(フレーム)

MODE = sys.argv[1] if len(sys.argv) > 1 else "main"
if MODE == "shorts":
    W, H, KEY, END_HOLD, PAD = 1080, 1920, "shorts", 1.5, 0.25
else:
    W, H, KEY, END_HOLD, PAD = 1920, 1080, "scenes", 20.0, 0.45
S = min(W, H) / 720      # 文字サイズの倍率（720px基準で設計）
# 動画クリップ版: --clips <フォルダ> に <素材名>.mp4（例 sb22_05.mp4, S03.mp4）があればそれを使う
CLIP_DIR = Path(sys.argv[sys.argv.index("--clips") + 1]) if "--clips" in sys.argv else None
if CLIP_DIR is not None and not CLIP_DIR.is_absolute():
    CLIP_DIR = ROOT / CLIP_DIR
# ナレーション: --voice <名前> で work/voice_<名前>/ を使う（既定 elevenlabs＝Luna×1.08、旧版は kokoro）
VOICE_DIR = WORK / f"voice_{sys.argv[sys.argv.index('--voice') + 1] if '--voice' in sys.argv else 'elevenlabs'}"

DELA = str(A / "fonts" / "DelaGothicOne.ttf")
NOTO = str(A / "fonts" / "NotoSansJP.ttf")
RED = (214, 22, 32)
YELLOW = (255, 214, 60)
FACE_BOX = (400, 35, 700, 335)   # 01_host_girl.jpg 上の顔の範囲（ワイプ用）

# 効果音：scenes.json の se 列のキーワード → (ファイル名, 開始秒, 音量)
SE_RULES = [("ジャッ", "stirfry", 0.2, 0.55), ("ジュー", "sizzle", 0.0, 0.5), ("ジュワ", "sizzle", 0.0, 0.5),
            ("ジュッ", "sizzle", 0.1, 0.45), ("チリチリ", "sizzle", 0.0, 0.35), ("ポン", "pop", 0.25, 0.5),
            ("キラ", "chime", 0.1, 0.35), ("シュッ", "whoosh", 0.0, 0.5), ("ドン", "impact", 0.0, 0.6),
            ("ジャーン", "impact", 0.3, 0.55), ("シャキーン", "impact", 0.0, 0.55), ("ザクッ", "crunch", 0.3, 0.8),
            ("シャキッ", "crunch", 0.2, 0.55), ("パカッ", "crunch", 0.2, 0.5), ("カチャ", "clink", 0.2, 0.5),
            ("コトッ", "clink", 0.1, 0.4), ("ピッ", "beep", 0.2, 0.4), ("ブーン", "microwave", 0.2, 0.6),
            ("ドサッ", "thud", 0.2, 0.6), ("スッ", "swish", 0.2, 0.5), ("カサッ", "swish", 0.2, 0.4),
            ("水しぶき", "splash", 0.3, 0.5)]


# ---------------- 共通 ----------------
@lru_cache(None)
def noto(size, weight="Black"):
    f = ImageFont.truetype(NOTO, int(size * S))
    f.set_variation_by_name(weight)
    return f


@lru_cache(None)
def dela(size):
    return ImageFont.truetype(DELA, int(size * S))


def cfg():
    return json.loads((ROOT / "tools" / "scenes.json").read_text(encoding="utf-8"))


@lru_cache(None)
def panel(name):
    return Image.open(A / "panels_hd" / f"{name}.png").convert("RGB")


@lru_cache(None)
def host_img():
    """ソアちゃんの切り抜き。本編は頭〜太ももまで（大きく見せる）、ショートは全身。"""
    im = Image.open(A / "panels" / "host_cutout.png")
    return im.crop((0, 0, im.width, int(im.height * 0.72))) if MODE == "main" else im


@lru_cache(None)
def hero_soft(size):
    """完成品写真のフチを楕円グラデーションで透明にする（四角い切れ目を見せない）。"""
    im = Image.open(A / "source" / "04_hero_burger.png").convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((size * 0.06, size * 0.04, size * 0.94, size * 0.98), fill=255)
    im.putalpha(m.filter(ImageFilter.GaussianBlur(size * 0.05)))
    return im


@lru_cache(None)
def face_wipe(d):
    src = Image.open(A / "source" / "01_host_girl.jpg").convert("RGB").crop(FACE_BOX).resize((d, d), Image.LANCZOS)
    m = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d * 4, d * 4), fill=255)
    m = m.resize((d, d), Image.LANCZOS)
    ring = int(d * 0.06)
    out = Image.new("RGBA", (d + ring * 2, d + ring * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(out)
    dr.ellipse((0, 0, out.width - 1, out.height - 1), fill=(255, 255, 255, 255))
    dr.ellipse((ring // 2, ring // 2, out.width - 1 - ring // 2, out.height - 1 - ring // 2), fill=RED + (255,))
    face = src.convert("RGBA")
    face.putalpha(m)
    out.alpha_composite(face, (ring, ring))
    tag = text_img("ソア", noto(22), (255, 255, 255), int(5 * S), RED)
    canvas = Image.new("RGBA", (out.width, out.height + tag.height // 2), (0, 0, 0, 0))
    canvas.alpha_composite(out)
    canvas.alpha_composite(tag, ((out.width - tag.width) // 2, out.height - tag.height // 2))
    return canvas


def cover(im, size):
    r = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    return im.crop((x, y, x + size[0], y + size[1]))


@lru_cache(None)
def blurred(name, dark=0.5):
    src = panel(name) if name != "hero" else Image.open(A / "source" / "04_hero_burger.png").convert("RGB")
    small = cover(src, (W // 4, H // 4)).filter(ImageFilter.GaussianBlur(8))
    return ImageEnhance.Brightness(small.resize((W, H), Image.BILINEAR)).enhance(dark).convert("RGBA")


def text_img(text, fnt, fill=(255, 255, 255), stroke=None, stroke_fill=(20, 12, 8)):
    stroke = int(8 * S) if stroke is None else stroke
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = d.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, 2 - t), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def fit_w(im, mw):
    return im if im.width <= mw else im.resize((mw, int(im.height * mw / im.width)), Image.LANCZOS)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ---------------- 動画クリップ ----------------
def clip_path(key):
    if CLIP_DIR is None:
        return None
    p = CLIP_DIR / f"{key}.mp4"
    return p if p.exists() else None


@lru_cache(maxsize=2)
def clip_frames(key):
    """クリップを元の解像度のまま読み込む（1080pに拡大して保持するとメモリ不足で落ちるため、拡大は1コマずつ行う）。"""
    trim = cfg().get("clip_trim", {}).get(key)   # 例 {"sb22_21": [0, 2.6]}：崩れた後半を使わない
    cut = ["-ss", str(trim[0]), "-t", str(trim[1] - trim[0])] if trim else []
    probe = subprocess.run([FF, "-i", str(clip_path(key))], capture_output=True, text=True).stderr
    w, h = map(int, re.search(r", (\d{3,4})x(\d{3,4})", probe).groups())
    cmd = [FF, "-loglevel", "error", *cut, "-i", str(clip_path(key)), "-an", "-vf", f"fps={FPS}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    size = w * h * 3
    return (w, h), [raw[i * size:(i + 1) * size] for i in range(len(raw) // size)]


def clip_frame(key, box, t, seg_len):
    """シーンの長さに合わせてクリップを再生。短いときはスロー（最低0.5倍）→それでも足りなければ往復再生。"""
    (w, h), fr = clip_frames(key)
    n = len(fr)
    speed = max(min(1.0, (n / FPS) / max(seg_len, 1e-3)), 0.5)
    k = int(t * speed * FPS)
    if k >= n and n > 1:
        m = k % (2 * n - 2)
        k = m if m < n else 2 * n - 2 - m
    im = Image.frombytes("RGB", (w, h), fr[min(k, n - 1)])
    return cover(im, box).convert("RGBA")


def clip_bg(frame_rgba):
    small = frame_rgba.convert("RGB").resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
    return ImageEnhance.Brightness(small.resize((W, H), Image.BILINEAR)).enhance(0.5).convert("RGBA")


# ---------------- レイヤー ----------------
@lru_cache(None)
def telop_imgs(lines):
    lines = list(lines)
    if not lines:
        return None
    first = lines[0]
    big = 60 if MODE == "shorts" else 54
    imgs = [fit_w(text_img(first, noto(big), YELLOW if first.startswith("POINT") else (255, 255, 255), int(9 * S)), W - int(60 * S))]
    if len(lines) > 1:
        imgs.append(fit_w(text_img(lines[1], noto(big * 0.74, "Bold"), (255, 255, 255), int(7 * S)), W - int(60 * S)))
    return imgs


@lru_cache(None)
def telop_band(h):
    band = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    a = np.linspace(0, 160, h).astype(np.uint8)[:, None].repeat(W, 1)
    band.putalpha(Image.fromarray(a))
    return band


@lru_cache(None)
def chapter_img(chapter):
    f = noto(30)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = d.textbbox((0, 0), chapter, font=f)
    pad = int(20 * S)
    im = Image.new("RGBA", (r - l + pad * 3, int(54 * S)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.polygon([(0, 0), (im.width, 0), (im.width - pad, im.height), (0, im.height)], fill=RED + (240,))
    dr.text((pad - l, (im.height - (b + t)) // 2), chapter, font=f, fill=(255, 255, 255))
    return im


@lru_cache(None)
def special_layer(kind, sid):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if kind == "title":
        t1 = fit_w(text_img("トラジライスバーガー", dela(86), YELLOW, int(12 * S), (120, 0, 0)), W - int(100 * S))
        t2 = fit_w(text_img("スペシャル", dela(100), YELLOW, int(12 * S), (120, 0, 0)), W - int(100 * S))
        y = int(H * 0.2)
        lay.alpha_composite(t1, ((W - t1.width) // 2, y))
        lay.alpha_composite(t2, ((W - t2.width) // 2, y + t1.height))
    elif kind == "ingredients":
        items = ["ごはん 400g", "牛こま肉 160g", "玉ねぎ 1/2個", "卵 2個", "トマト 1個", "レタス 2〜4枚",
                 "マヨネーズ 大さじ2", "ケチャップ 大さじ1", "焼肉のタレ 大さじ3＋小さじ1", "片栗粉 小さじ2",
                 "塩・醤油・ごま油・黒こしょう 各少々"]
        f = noto(27, "Bold")
        lh = int(47 * S)
        x0, y0 = int(W * 0.575), int(88 * S)
        d.rounded_rectangle((x0, y0, W - int(20 * S), y0 + lh * len(items) + int(26 * S)), int(18 * S), fill=(255, 250, 240, 235))
        for i, it in enumerate(items):
            d.text((x0 + int(22 * S), y0 + int(16 * S) + i * lh), "● " + it, font=f, fill=(40, 20, 10))
    elif kind == "end":
        if MODE == "shorts":
            t = fit_w(text_img("本編で詳しく！", dela(96), YELLOW, int(12 * S), (120, 0, 0)), W - int(60 * S))
            sub = fit_w(text_img("トラジライスバーガー・スペシャルの作り方", noto(40), (255, 255, 255), int(7 * S)), W - int(60 * S))
            lay.alpha_composite(t, ((W - t.width) // 2, int(H * 0.16)))
            lay.alpha_composite(sub, ((W - sub.width) // 2, int(H * 0.16) + t.height + int(16 * S)))
        else:
            # YouTube終了画面の要素（動画枠・登録ボタン）を置く場所をあけたデザイン
            t = text_img("ご視聴ありがとうございました！", noto(44), (255, 255, 255), int(8 * S))
            lay.alpha_composite(t, ((W - t.width) // 2, int(70 * S)))
            nx = text_img("次はこちら ▶", noto(34), YELLOW, int(7 * S))
            lay.alpha_composite(nx, (int(120 * S), int(170 * S)))
            cr = text_img("音声：ElevenLabs（Higgsfield経由）／BGM・効果音：オリジナル", noto(16, "Bold"), (230, 230, 230), int(3 * S))
            lay.alpha_composite(cr, (W - cr.width - int(24 * S), H - cr.height - int(16 * S)))
    return lay


# ---------------- 音声 ----------------
def load_voice(sid):
    a, sr = sf.read(VOICE_DIR / f"{sid}.wav", dtype="float32")
    return a


@lru_cache(None)
def load_se(name):
    a, _ = sf.read(A / "audio" / f"se_{name}.wav", dtype="float32")
    return a


def voice_env(voice, n_frames, offset):
    """フレームごとの声の大きさ(0〜1)。ワイプ・人物を声に合わせて弾ませる。"""
    hop = SR // FPS
    e = np.zeros(n_frames)
    for i in range(n_frames):
        s = int(i * hop - offset * SR)
        seg = voice[max(s, 0): max(s + hop, 0)]
        e[i] = np.sqrt((seg ** 2).mean()) if len(seg) else 0
    e = e / (e.max() + 1e-6)
    return np.convolve(e, np.ones(3) / 3, "same")


# ---------------- タイムライン ----------------
def timeline():
    scenes = cfg()[KEY]
    out, t = [], 0.0
    for sc in scenes:
        v = load_voice(sc["id"])
        dur = len(v) / SR + PAD + 0.2
        dur = max(dur, 2.0 if MODE == "main" else 1.2)
        if "imgs" in sc:
            dur = max(dur, 0.75 * len(sc["imgs"]))
        if sc["kind"] == "end":
            dur += END_HOLD
        out.append({"sc": sc, "start": t, "dur": dur, "n": int(round(dur * FPS)), "voice_end": len(v) / SR + 0.9})
        t += out[-1]["n"] / FPS
    return out


# ---------------- 1フレーム描画 ----------------
def render_frame(item, i, prev_chapter, envelope, telop=True):
    sc, n = item["sc"], item["n"]
    p = i / max(n - 1, 1)
    ts = i / FPS
    kind = sc["kind"]
    idx = int(sc["id"][1:])
    used_clip = False
    host_key = sc["id"] if MODE == "main" else "S03"
    if kind == "host" and clip_path(host_key):
        frame = clip_frame(host_key, (W, H), ts, item["dur"])
        used_clip = True
    elif kind == "host":
        frame = blurred("hero", 0.42).copy()
        h = host_img()
        hh = int(H * (0.93 if MODE == "main" else 0.62))
        bounce = 1.0 + 0.012 * envelope[i] + 0.006 * np.sin(ts * 2.4)
        hw, hh2 = int(h.width * hh / h.height * bounce), int(hh * bounce)
        hi = h.resize((hw, hh2), Image.BILINEAR)
        tilt = 1.2 * np.sin(ts * 1.7)
        hi = hi.rotate(tilt, resample=Image.BILINEAR, expand=True)
        slide = int((1 - ease(ts / 0.35)) * W * 0.25)
        if MODE == "main":
            x = int(W * 0.10) - slide
            b = hero_soft(int(H * 0.86)) if sc["id"] in ("S28", "S30") else None
            if b is not None:
                frame.alpha_composite(b, (int(W * 0.47), int(H * 0.02)))
            else:
                card = text_img("焼肉トラジ", dela(50), (255, 255, 255), int(8 * S))
                name = text_img("看板娘　ソア", noto(56), YELLOW, int(8 * S))
                frame.alpha_composite(card, (int(W * 0.52), int(H * 0.30)))
                frame.alpha_composite(name, (int(W * 0.52), int(H * 0.30) + card.height + int(10 * S)))
            frame.alpha_composite(hi, (x, H - hi.height + int(20 * S)))
        else:
            b = hero_soft(int(W * 0.66))
            frame.alpha_composite(b, (W - b.width + int(W * 0.04), int(H * 0.12)))
            frame.alpha_composite(hi, (int(W * 0.02) - slide, H - hi.height + int(20 * S)))
    else:
        imgs = sc["imgs"] if "imgs" in sc else [sc["img"]]
        k = min(int(p * len(imgs)), len(imgs) - 1)
        name = imgs[k]
        src = panel(name)
        frame = blurred(name).copy()
        lp = (p * len(imgs)) - k
        zoom_in = (idx + k) % 2 == 0
        z = 1.0 + 0.08 * (lp if zoom_in else 1 - lp)
        pan = 0.03 * (lp - 0.5) * (1 if idx % 3 else -1)
        ar = src.width / src.height
        if MODE == "main" and sc.get("fit"):   # 全体を見せたいコマ（パッケージ等）：高さ合わせ＋ぼかし背景
            box = (min(int(H * ar), W), H)
            base_w, base_h = box
            pos = ((W - box[0]) // 2, 0)
        elif MODE == "main" and ar <= 2.0 and kind != "ingredients":
            base_w, base_h = W, H          # 画面いっぱい（cover）
            box = (W, H)
            pos = (0, 0)
        elif MODE == "shorts":             # 縦動画：正方形に大きく切り出す（下の余白にテロップ）
            box = (W, W)
            base_w, base_h = box
            pos = (0, int(H * 0.17))
        else:                              # 横長コマ・材料カード：幅合わせ＋ぼかし背景
            bw = int(W * (0.56 if kind == "ingredients" else 1.0))
            box = (bw, int(bw / ar))
            base_w, base_h = box
            pos = (int(20 * S) if kind == "ingredients" else 0, (H - box[1]) // 2)
        if clip_path(name):
            # 動画クリップ版：本編は画面いっぱい（材料だけ左寄せ）、ショートは正方形
            if MODE == "main":
                box = (W, H) if kind != "ingredients" else (int(W * 0.56), int(W * 0.56 * 9 / 16))
                pos = (0, 0) if kind != "ingredients" else (int(20 * S), (H - box[1]) // 2)
            seg_len = item["dur"] / len(imgs)
            cf = clip_frame(name, box, lp * seg_len, seg_len)
            frame = clip_bg(cf) if box != (W, H) else frame
            frame.alpha_composite(cf, pos)
            used_clip = True
        else:
            cw, ch = int(base_w * z), int(base_h * z)
            r = max(cw / src.width, ch / src.height)
            im = src.resize((int(src.width * r) + 1, int(src.height * r) + 1), Image.BILINEAR)
            x0 = (im.width - box[0]) // 2 + int(pan * im.width)
            y0 = (im.height - box[1]) // 2
            x0 = min(max(x0, 0), im.width - box[0])
            frame.alpha_composite(im.crop((x0, y0, x0 + box[0], y0 + box[1])).convert("RGBA"), pos)
        # ソアのワイプ（料理カット中に右上。声に合わせて弾む）※動画クリップ版では写真を使わないので出さない
        if kind in ("broll", "title") and CLIP_DIR is None:
            d = int(118 * S)
            wp = face_wipe(d)
            sc_w = 1.0 + 0.07 * envelope[i]
            wpi = wp.resize((int(wp.width * sc_w), int(wp.height * sc_w)), Image.BILINEAR)
            pop_in = ease(ts / 0.25)
            if pop_in < 1:
                wpi = wpi.resize((max(int(wpi.width * pop_in), 1), max(int(wpi.height * pop_in), 1)), Image.BILINEAR)
            cx = W - int(40 * S) - wp.width // 2
            cy = int((160 if MODE == "shorts" else 40) * S) + wp.height // 2
            frame.alpha_composite(wpi, (cx - wpi.width // 2, cy - wpi.height // 2))
    end_screen = kind == "end" and ts > item.get("voice_end", 0)
    if end_screen and used_clip:
        frame = clip_bg(frame)   # 背景の動画をぼかして暗くし、文字を読みやすくする
        frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 90)))
        frame.alpha_composite(special_layer(kind, sc["id"]))
    elif end_screen:
        frame = blurred("hero", 0.38).copy()
        b = hero_soft(int(H * (0.62 if MODE == "main" else 0.3) / 0.7))
        frame.alpha_composite(b, ((W - b.width) // 2, H - int(b.height * 0.92)))
        frame.alpha_composite(special_layer(kind, sc["id"]))
    elif kind != "end":
        frame.alpha_composite(special_layer(kind, sc["id"]))
    # 章ラベル（章が変わった時だけスライドイン）
    if sc.get("chapter"):
        ci = chapter_img(sc["chapter"])
        k = ease(ts / 0.3) if sc["chapter"] != prev_chapter else 1.0
        frame.alpha_composite(ci, (int(-ci.width + (ci.width + int(24 * S)) * k), int(24 * S)))
    # テロップ（下からスライドイン）
    lines = () if end_screen else tuple(sc["telop"][1:] if kind == "title" else sc["telop"])
    imgs = telop_imgs(lines) if telop else None
    if imgs:
        gap = int(8 * S)
        total = sum(t.height for t in imgs) + gap * (len(imgs) - 1)
        bottom = int((330 if MODE == "shorts" else 38) * S)
        band = telop_band(total + int(70 * S)) if MODE == "main" else None
        if band is not None:
            frame.alpha_composite(band, (0, H - band.height))
        k = ease(ts / 0.22)
        y = H - bottom - total + int((1 - k) * 40 * S)
        for t in imgs:
            ti = t if k >= 1 else Image.blend(Image.new("RGBA", t.size, (0, 0, 0, 0)), t, k)
            frame.alpha_composite(ti, ((W - t.width) // 2, y))
            y += t.height + gap
    return frame.convert("RGB")


def render_segment(args):
    k, items = args
    item = items[k]
    prev = items[k - 1] if k > 0 else None
    seg = WORK / f"seg_{MODE}_{k:02d}.mp4"
    voice = load_voice(item["sc"]["id"])
    env = voice_env(voice, item["n"], 0.15)
    prev_last = None
    if prev is not None:
        pe = voice_env(load_voice(prev["sc"]["id"]), prev["n"], 0.15)
        pprev = items[k - 2]["sc"].get("chapter") if k > 1 else None
        prev_last = render_frame(prev, prev["n"] - 1, pprev, pe, telop=False)  # 前テロップの二重写り防止
    prev_ch = prev["sc"].get("chapter") if prev else None
    proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-g", str(FPS * 2), str(seg)], stdin=subprocess.PIPE)
    for i in range(item["n"]):
        fr = render_frame(item, i, prev_ch, env)
        if prev_last is not None and i < XF:
            fr = Image.blend(prev_last, fr, (i + 1) / (XF + 1))
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    proc.wait()
    return seg


# ---------------- 音声ミックス ----------------
def se_list(se_text):
    out = []
    for kw, name, off, gain in SE_RULES:
        if kw in se_text and name not in [o[0] for o in out]:
            out.append((name, off, gain))
    return out


def mix_audio(items, total):
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    fx = np.zeros(n, np.float32)
    prev_ch = None
    for it in items:
        sc = it["sc"]
        st = it["start"]
        v = load_voice(sc["id"])
        o = int((st + 0.15) * SR)
        voice[o:o + len(v)] += v[: n - o]
        for name, off, gain in se_list(sc.get("se", "")):
            reps = 6 if "×6" in sc.get("se", "") else 1
            for r in range(reps):
                s = load_se(name)
                oo = int((st + off + r * 0.55) * SR)
                fx[oo:oo + len(s)] += s[: n - oo] * gain
        if sc.get("chapter") and sc["chapter"] != prev_ch and prev_ch is not None:
            s = load_se("whoosh")
            oo = max(int((st - 0.2) * SR), 0)
            fx[oo:oo + len(s)] += s * 0.35
        prev_ch = sc.get("chapter")
    bgm, _ = sf.read(A / "audio" / "bgm_loop.wav", dtype="float32")
    bg = np.tile(bgm, n // len(bgm) + 1)[:n]
    # ダッキング：声がある所はBGMを下げる
    hop = 1024
    e = np.array([np.abs(voice[i:i + hop]).max() if i < n else 0 for i in range(0, n, hop)])
    act = (e > 0.02).astype(float)
    act = np.convolve(act, np.ones(9) / 9, "same")
    act_s = np.repeat(np.clip(act * 1.5, 0, 1), hop)[:n]
    duck = 1.0 - 0.80 * act_s          # 声の間はBGMを約-14dBまで下げる（ElevenLabsの声がBGMに埋もれないよう深めに）
    fade_in = np.minimum(1, np.arange(n) / (0.8 * SR))
    fade_out = np.clip((total - np.arange(n) / SR) / 2.5, 0, 1)
    bg = bg * 0.30 * duck * fade_in * fade_out
    mix = voice * 1.0 + fx * 0.8 * (1.0 - 0.45 * act_s) + bg   # 効果音も声の間は少し下げる
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)          # ソフトリミッター
    mix = mix / max(np.abs(mix).max(), 1e-6) * 0.89   # ピーク -1dB
    path = WORK / f"mix_{MODE}.wav"
    sf.write(path, mix[: int(total * SR)], SR)
    return path


# ---------------- 字幕・チャプター ----------------
def ts_srt(x):
    h, r = divmod(x, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


def write_meta(items, total):
    srt = []
    for k, it in enumerate(items, 1):
        v = len(load_voice(it["sc"]["id"])) / SR
        srt.append(f"{k}\n{ts_srt(it['start'] + 0.15)} --> {ts_srt(it['start'] + 0.15 + v + 0.1)}\n{it['sc']['narr']}\n")
    suffix = "" if MODE == "main" else "_shorts"
    (OUT / f"subtitles_ja{suffix}.srt").write_text("\n".join(srt), encoding="utf-8")
    tl = {"total_sec": round(total, 2), "fps": FPS,
          "scenes": [{"id": it["sc"]["id"], "start": round(it["start"], 2), "dur": round(it["n"] / FPS, 2),
                      "narr": it["sc"]["narr"]} for it in items]}
    (OUT / f"timings{suffix}.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    items = timeline()
    total = sum(it["n"] for it in items) / FPS
    print(f"{MODE}: {len(items)} scenes, {total:.1f}s, {W}x{H}@{FPS}")
    WORK.mkdir(exist_ok=True)
    with Pool(3 if CLIP_DIR is not None else 4) as pool:   # クリップ版はメモリを多く使うので3並列
        segs = pool.map(render_segment, [(k, items) for k in range(len(items))], chunksize=1)
    lst = WORK / f"segs_{MODE}.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    wav = mix_audio(items, total)
    name = "toraji_rice_burger_main_1080p.mp4" if MODE == "main" else "toraji_rice_burger_shorts_1080x1920.mp4"
    if CLIP_DIR is not None:
        name = name.replace(".mp4", "_clips.mp4")
        missing = sorted({(it["sc"]["id"] if it["sc"]["kind"] == "host" else it["sc"].get("img", ""))
                          for it in items if not clip_path(it["sc"]["id"] if it["sc"]["kind"] == "host" and MODE == "main"
                                                            else ("S03" if it["sc"]["kind"] == "host" else it["sc"].get("img", "")))} - {""})
        if missing:
            print("クリップが無い素材（写真のズーム表示で代用）:", ", ".join(missing))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", str(OUT / name)], check=True)
    write_meta(items, total)
    print("done", OUT / name, (OUT / name).stat().st_size, "bytes")


if __name__ == "__main__":
    main()
