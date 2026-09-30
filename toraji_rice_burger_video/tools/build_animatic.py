"""仮編集動画（アニマティック）を scenes.json から自動生成する。

- 映像: ストーリーボードの各コマ（ゆっくりズーム）＋テロップ＋章ラベル
- 音声: 仮ナレーション（gTTS の機械音声。本番は ElevenLabs 等で差し替え）
- 出力: output/animatic_720p.mp4 / output/subtitles_ja.srt / output/timings.json
本番のHiggsfield生成クリップが揃ったら、同じ尺(timings.json)で差し替えるだけで本編になる。
"""
import json
import subprocess
import wave
from array import array
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
OUT = ROOT / "output"
WORK = ROOT / "work"
TTS = WORK / "tts"
TTS.mkdir(parents=True, exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1280, 720, 24
SR = 44100
XFADE = 5            # 場面転換のクロスフェード(フレーム)
PAD_AFTER = 0.45     # ナレ後の余白(秒)
MIN_DUR = 2.2
END_HOLD = 8.0       # 終了画面の保持（本番は20秒）
TEMPO = 1.12         # 仮ナレの話速

DELA = str(A / "fonts" / "DelaGothicOne.ttf")
NOTO = str(A / "fonts" / "NotoSansJP.ttf")
RED = (214, 22, 32)
YELLOW = (255, 214, 60)


def noto(size, weight="Black"):
    f = ImageFont.truetype(NOTO, size)
    f.set_variation_by_name(weight)
    return f


def dela(size):
    return ImageFont.truetype(DELA, size)


# ---------- 音声 ----------
def tts(scene, text):
    mp3 = TTS / f"{scene}.mp3"
    wav = TTS / f"{scene}.wav"
    if not wav.exists():
        from gtts import gTTS
        gTTS(text, lang="ja").save(str(mp3))
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp3), "-filter:a", f"atempo={TEMPO}",
                        "-ar", str(SR), "-ac", "1", str(wav)], check=True)
    with wave.open(str(wav)) as w:
        data = array("h", w.readframes(w.getnframes()))
    return data


# ---------- 画像 ----------
def cover(im, size):
    r = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    return im.crop((x, y, x + size[0], y + size[1]))


def blurred_bg(im, dark=0.5):
    bg = cover(im.convert("RGB"), (W, H)).filter(ImageFilter.GaussianBlur(30))
    return ImageEnhance.Brightness(bg).enhance(dark).convert("RGBA")


def panel(name):
    return Image.open(A / "panels" / f"{name}.png").convert("RGB")


def text_img(text, fnt, fill=(255, 255, 255), stroke=8, stroke_fill=(20, 12, 8)):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = d.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, 2 - t), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def fit_width(im, max_w):
    if im.width <= max_w:
        return im
    return im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)


def telop_layer(lines, chapter, unconfirmed):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # 下部テロップ（1行目=大、2行目=小）
    if lines:
        imgs = [fit_width(text_img(lines[0], noto(54), YELLOW if lines[0].startswith("POINT") else (255, 255, 255), 9), W - 80)]
        if len(lines) > 1:
            imgs.append(fit_width(text_img(lines[1], noto(40, "Bold"), (255, 255, 255), 7), W - 80))
        total = sum(i.height for i in imgs) + 8 * (len(imgs) - 1)
        y = H - 38 - total
        band = Image.new("RGBA", (W, total + 56), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        for yy in range(band.height):
            bd.line([(0, yy), (W, yy)], fill=(0, 0, 0, int(150 * yy / band.height)))
        lay.alpha_composite(band, (0, H - band.height))
        for im in imgs:
            lay.alpha_composite(im, ((W - im.width) // 2, y))
            y += im.height + 8
    # 章ラベル（左上）
    if chapter:
        f = noto(30)  # Dela Gothic One は丸数字(①〜⑧)のグリフが無いため Noto を使う
        l, t, r, b = d.textbbox((0, 0), chapter, font=f)
        d.polygon([(24, 22), (r - l + 84, 22), (r - l + 68, 74), (24, 74)], fill=RED + (235,))
        d.text((46 - l, 48 - (b + t) // 2), chapter, font=f, fill=(255, 255, 255))
    # 仮編集の注記（右上）
    note = "ANIMATIC｜仮映像・仮ナレ" + ("｜要確認：市販品" if unconfirmed else "")
    ni = text_img(note, noto(20, "Bold"), (255, 255, 255), 3)
    lay.alpha_composite(ni, (W - ni.width - 18, 16))
    return lay


def host_base(scene):
    bg = blurred_bg(panel("sb12_09"), 0.55)
    host = Image.open(A / "panels" / "host_cutout.png")
    hh = 700
    host = host.resize((int(host.width * hh / host.height), hh), Image.LANCZOS)
    extra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if scene["id"] in ("S28", "S30"):
        b = Image.open(A / "source" / "04_hero_burger.png").convert("RGBA").resize((560, 560), Image.LANCZOS)
        extra.alpha_composite(b, (620, 60))
    else:  # 自己紹介: 名前カード
        card = text_img("焼肉トラジ", dela(46), (255, 255, 255), 8)
        name = text_img("{NAME}（名前を入れる）", noto(40), YELLOW, 7)
        extra.alpha_composite(card, (660, 190))
        extra.alpha_composite(name, (660, 260))
    return bg, host, extra


def overlay_special(scene, frame_layer):
    d = ImageDraw.Draw(frame_layer)
    if scene["kind"] == "title":
        t1 = fit_width(text_img("トラジライスバーガー", dela(86), YELLOW, 12, (120, 0, 0)), W - 100)
        t2 = fit_width(text_img("スペシャル", dela(96), YELLOW, 12, (120, 0, 0)), W - 100)
        frame_layer.alpha_composite(t1, ((W - t1.width) // 2, 150))
        frame_layer.alpha_composite(t2, ((W - t2.width) // 2, 150 + t1.height + 4))
    elif scene["kind"] == "ingredients":
        items = ["ごはん 400g", "牛こま肉 160g", "玉ねぎ 1/2個", "卵 2個", "トマト 1個", "レタス 2〜4枚",
                 "マヨネーズ 大さじ2", "ケチャップ 大さじ1", "焼肉のタレ 大さじ3＋小さじ1", "片栗粉 小さじ2",
                 "塩・醤油・ごま油・黒こしょう 各少々"]
        x0, y0 = 740, 88
        d.rounded_rectangle((x0, y0, W - 20, y0 + 47 * len(items) + 26), 18, fill=(255, 250, 240, 235))
        for i, it in enumerate(items):
            d.text((x0 + 22, y0 + 16 + i * 47), "● " + it, font=noto(27, "Bold"), fill=(40, 20, 10))
    elif scene["kind"] == "end":
        d.rounded_rectangle((70, 150, 560, 426), 16, outline=(255, 255, 255), width=4)
        d.text((110, 270), "終了画面：おすすめ動画", font=noto(30, "Bold"), fill=(255, 255, 255))
        d.ellipse((800, 170, 1040, 410), outline=(255, 255, 255), width=4)
        d.text((838, 272), "登録ボタン", font=noto(34, "Bold"), fill=(255, 255, 255))


def build():
    cfg = json.loads((ROOT / "tools" / "scenes.json").read_text(encoding="utf-8"))
    name = cfg["host_name_tts_fallback"]
    scenes = cfg["scenes"]

    # 1) 音声と尺
    timeline, t = [], 0.0
    audio_parts = []
    for sc in scenes:
        narr = sc["narr"].replace("{NAME}", name)
        data = tts(sc["id"], narr)
        dur = max(MIN_DUR, len(data) / SR + PAD_AFTER + 0.15)
        if sc["kind"] == "end":
            dur += END_HOLD
        timeline.append({"id": sc["id"], "start": round(t, 2), "dur": round(dur, 2), "narr": narr})
        audio_parts.append((t + 0.15, data))
        t += dur
    total = t

    # 2) 音声を1本に
    pcm = array("h", bytes(int(total * SR + SR) * 2))
    for start, data in audio_parts:
        o = int(start * SR)
        pcm[o:o + len(data)] = data
    wav_path = WORK / "narration_temp.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    # 3) 映像
    mp4 = OUT / "animatic_720p.mp4"
    proc = subprocess.Popen([FF, "-y", "-loglevel", "error",
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-i", str(wav_path),
                             "-c:v", "libx264", "-preset", "medium", "-crf", "27", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(mp4)],
                            stdin=subprocess.PIPE)
    prev_last = None
    for sc, tl in zip(scenes, timeline):
        n = int(round(tl["dur"] * FPS))
        lines = [s.replace("{NAME}", "〇〇") for s in sc["telop"]]
        if sc["kind"] == "title":
            lines = lines[1:]
        tel = telop_layer(lines, sc["chapter"], sc.get("unconfirmed"))
        special = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        overlay_special(sc, special)
        if sc["kind"] == "host":
            bg, host, extra = host_base(sc)
        else:
            src = panel(sc["img"])
            bg = blurred_bg(src)
            # 前景はストーリーボードのコマ。16:9に収まるよう高さ基準で配置
            fh = H if sc["kind"] != "ingredients" else H - 40
            fg = src.resize((int(src.width * fh * 1.08 / src.height), int(fh * 1.08)), Image.LANCZOS)
        last = None
        for i in range(n):
            p = i / max(n - 1, 1)
            frame = bg.copy()
            if sc["kind"] == "host":
                frame.alpha_composite(extra)
                s = 1.0 + 0.015 * (1 - abs(2 * p - 1))
                hw, hh = int(host.width * s), int(host.height * s)
                frame.alpha_composite(host.resize((hw, hh), Image.BILINEAR), (140 - (hw - host.width) // 2, H - hh + 10))
            else:
                z = 1.0 + 0.07 * p                           # ゆっくりズームイン
                cw, ch = int(fg.width / 1.08 * z), int(fg.height / 1.08 * z)
                im = fg.resize((cw, ch), Image.BILINEAR)
                fw, fh2 = int(fg.width / 1.08), int(fg.height / 1.08)
                x0, y0 = (cw - fw) // 2, (ch - fh2) // 2
                im = im.crop((x0, y0, x0 + fw, y0 + fh2)).convert("RGBA")
                px = (W - fw) // 2 if sc["kind"] != "ingredients" else 30
                frame.alpha_composite(im, (px, (H - fh2) // 2))
            frame.alpha_composite(special)
            frame.alpha_composite(tel)
            out = frame.convert("RGB")
            if prev_last is not None and i < XFADE:
                out = Image.blend(prev_last, out, (i + 1) / (XFADE + 1))
            proc.stdin.write(out.tobytes())
            last = out
        prev_last = last
    proc.stdin.close()
    proc.wait()

    # 4) 字幕・タイミング
    def ts(x):
        h, r = divmod(x, 3600); m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    srt = []
    for i, tl in enumerate(timeline, 1):
        end = tl["start"] + tl["dur"] - (END_HOLD if tl["id"] == scenes[-1]["id"] else 0.2)
        srt.append(f"{i}\n{ts(tl['start'] + 0.15)} --> {ts(end)}\n{tl['narr'].replace('看板娘', '{NAME}')}\n")
    (OUT / "subtitles_ja.srt").write_text("\n".join(srt), encoding="utf-8")
    (OUT / "timings.json").write_text(json.dumps({"total_sec": round(total, 2), "fps": FPS, "scenes": timeline},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done: {mp4.name} {total:.1f}s, {mp4.stat().st_size} bytes, {len(scenes)} scenes")


if __name__ == "__main__":
    build()
