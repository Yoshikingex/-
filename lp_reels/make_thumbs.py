"""リール用サムネイル（1080x1920）を6枚生成する。

  python3 make_thumbs.py <画面録画mp4フォルダ>

上半分=AFTERの実フレーム / 下半分=BEFOREの実フレーム / 中央に見出し。
重要な要素はプロフィールグリッド(3:4, y=240〜1680)の内側に収める。
"""
import glob
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(HERE, "fonts", n)
W, H, MID = 1080, 1920, 960

# key: (AFTER素材, 秒, 横位置, BEFORE素材, 秒, 横位置, カテゴリ, 見出し1, 見出し2, 基調色, アクセント, 明るい?, 見出しフォント)
MINCHO = F("ShipporiMincho_700Bold.ttf")
GOTHIC = F("ZenKakuGothicNew_900Black.ttf")
THUMBS = {
    "01_car": ("3b20a6ff", 1.5, 0.45, "d3312809", 3.0, 0.5, "高級車ブランド",
               "止まったLPに、", "エンジンを。", (8, 8, 10), (214, 190, 140), False, MINCHO),
    "02_kebab": ("316a4e2b", 1.0, 0.40, "50b8f99f", 3.0, 0.5, "ケバブ専門店",
                 "“美味しそう”が", "動き出すLP。", (14, 9, 6), (255, 164, 82), False, GOTHIC),
    "03_salon": ("a434abb1", 5.0, 0.46, "31284b49", 3.0, 0.5, "ヘアサロン",
                 "艶まで伝わる、", "動くLP。", (20, 16, 14), (214, 170, 130), False, MINCHO),
    "04_ryokan": ("251d8ce9", 4.5, 0.50, "69674589", 3.0, 0.5, "高級旅館",
                  "静けさまで", "伝わるLP。", (10, 12, 11), (201, 164, 92), False, MINCHO),
    "05_gym": ("e266aba8", 7.5, 0.80, "b7040fab", 3.0, 0.5, "パーソナルジム",
               "読まれないLPを", "“動かす”。", (9, 9, 9), (245, 196, 0), False, GOTHIC),
    "06_estate": ("1fb50556", 3.0, 0.40, "b355ab52", 3.0, 0.5, "不動産",
                  "間取り図から、", "歩けるLPへ。", (242, 237, 228), (150, 110, 72), True, MINCHO),
}


def frame(src_dir, tag, t):
    f = glob.glob(os.path.join(src_dir, f"*{tag}*.mp4"))[0]
    out = os.path.join(HERE, "_cache", f"thumb_{tag}_{t}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", f, "-frames:v", "1", out], check=True)
    return Image.open(out).convert("RGB")


def cover(img, w, h, cx):
    s = h / img.height
    img = img.resize((round(img.width * s), h), Image.LANCZOS)
    x = int(min(max(img.width * cx - w / 2, 0), img.width - w))
    return img.crop((x, 0, x + w, h))


def vgrad(w, h, color, a0, a1):
    a = np.linspace(a0, a1, h)[:, None] * np.ones((1, w))
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def text_center(d, y, s, font, fill, spacing=0):
    w = sum(font.getlength(ch) for ch in s) + spacing * (len(s) - 1)
    x = (W - w) / 2
    for ch in s:
        d.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + spacing


def pill(d, x, y, label, sub, bg, fg, subfg):
    f1 = ImageFont.truetype(F("Montserrat_600SemiBold.ttf"), 34)
    f2 = ImageFont.truetype(F("ZenKakuGothicNew_700Bold.ttf"), 30)
    w = f1.getlength(label) + 8 * len(label) + (f2.getlength(sub) + 30 if sub else 0) + 56
    d.rounded_rectangle([x, y, x + w, y + 66], 33, fill=bg)
    xx = x + 28
    for ch in label:
        d.text((xx, y + 13), ch, font=f1, fill=fg)
        xx += f1.getlength(ch) + 8
    if sub:
        d.text((xx + 22, y + 15), sub, font=f2, fill=subfg)


def make(key, cfg, src_dir, out_dir):
    a_tag, a_t, a_cx, b_tag, b_t, b_cx, cat, h1, h2, base, acc, light, hfont = cfg
    canvas = Image.new("RGB", (W, H), base)
    after = cover(frame(src_dir, a_tag, a_t), W, MID, a_cx)
    after = ImageEnhance.Contrast(after).enhance(1.06)
    before = cover(frame(src_dir, b_tag, b_t), W, H - MID, b_cx)
    before = ImageEnhance.Color(before).enhance(0.8)
    canvas.paste(after, (0, 0))
    canvas.paste(before, (0, MID))
    img = canvas.convert("RGBA")

    # 上下の端を締める（グリッド外は暗く/明るく）
    img.alpha_composite(vgrad(W, 420, base, 0.85, 0.0), (0, 0))
    img.alpha_composite(vgrad(W, 200, base, 0.0, 0.9), (0, H - 200))
    # 中央の見出し帯
    band_h = 440
    band = Image.new("RGBA", (W, band_h), (*base, 255))
    img.alpha_composite(vgrad(W, 90, base, 0.0, 1.0), (0, MID - band_h // 2 - 90))
    img.alpha_composite(band, (0, MID - band_h // 2))
    img.alpha_composite(vgrad(W, 90, base, 1.0, 0.0), (0, MID + band_h // 2))

    d = ImageDraw.Draw(img)
    txt = (40, 33, 27) if light else (255, 255, 255)
    sub = (110, 96, 84) if light else (200, 196, 190)
    # 帯の上下に細いアクセント線
    for yy in (MID - band_h // 2, MID + band_h // 2 - 3):
        d.rectangle([120, yy, W - 120, yy + 3], fill=(*acc, 255))

    # 上部: BEFORE → AFTER とカテゴリ（3:4の内側 y=270〜）
    f_top = ImageFont.truetype(F("Montserrat_600SemiBold.ttf"), 36)
    text_center(d, 280, "BEFORE  →  AFTER", f_top, (*acc, 255), spacing=10)
    f_cat = ImageFont.truetype(F("ZenKakuGothicNew_700Bold.ttf"), 40)
    text_center(d, 338, f"{cat}のLP", f_cat, (255, 255, 255) if not light else (40, 33, 27), spacing=4)

    # ラベル
    pill(d, 40, MID - band_h // 2 - 100, "AFTER", "スクロール連動LP", (*acc, 255),
         (255, 255, 255) if light else (15, 12, 10), (255, 255, 255) if light else (15, 12, 10))
    pill(d, 40, MID + band_h // 2 + 24, "BEFORE", "静止LP", (60, 60, 64, 235), (235, 235, 235), (200, 200, 200))

    # 見出し
    f1 = ImageFont.truetype(hfont, 96)
    f2 = ImageFont.truetype(hfont, 124)
    text_center(d, MID - 190, h1, f1, (*txt, 255), spacing=2)
    text_center(d, MID - 70, h2, f2, (*acc, 255), spacing=2)
    # 見出し下の誘導
    f_cta = ImageFont.truetype(F("ZenKakuGothicNew_700Bold.ttf"), 36)
    text_center(d, MID + 128, "▶  動く方を、見てください", f_cta, (*sub, 255), spacing=2)

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{key}.png")
    img.convert("RGB").save(path, optimize=True)
    return path


if __name__ == "__main__":
    src = sys.argv[1]
    out = os.path.join(HERE, "output", "thumbs")
    for k, c in THUMBS.items():
        print(make(k, c, src, out))
