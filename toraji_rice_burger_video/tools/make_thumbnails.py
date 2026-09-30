"""YouTubeサムネイル3案を生成（1280x720 / JPG 2MB以下）。

A: 主人公(左)＋巨大バーガー(右)＋「焼肉屋が本気で作った／ライスバーガー」   ← 本命
B: バーガー(左)＋主人公(右)＋「ごはんで挟む！／焼肉バーガー」＋「フライパン1つ」
C: 人物なし・バーガー全面＋「黄身とろ〜り」＋「お家でトラジ」バッジ                  ← 顔あり/なし比較用
YouTube Studio の「テストと比較」に3枚まとめて登録して、総再生時間の多い案を採用する。
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
W, H = 1280, 720
DELA = str(A / "fonts" / "DelaGothicOne.ttf")
MARU = str(A / "fonts" / "ZenMaruGothic-Black.ttf")

YELLOW = ((255, 246, 140), (255, 190, 20))   # 上→下グラデーション
RED = (214, 22, 32)
BLACK = (15, 10, 8)


def font(path, size):
    return ImageFont.truetype(path, size)


def gradient(size, top, bottom):
    w, h = size
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h))


def text_layer(text, fnt, fill, strokes, shadow=True, spacing=0, align="left"):
    """strokes: 外側から [(太さ, 色), ...]。fill は色 or (上色, 下色) のグラデーション。"""
    pad = max(s for s, _ in strokes) + 24
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = (int(v) for v in tmp.multiline_textbbox((0, 0), text, font=fnt, spacing=spacing, align=align))
    size = (r - l + pad * 2, b - t + pad * 2)
    org = (pad - l, pad - t)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    if shadow:
        m = Image.new("L", size, 0)
        ImageDraw.Draw(m).multiline_text((org[0] + 8, org[1] + 10), text, font=fnt, fill=255,
                                         stroke_width=strokes[0][0], spacing=spacing, align=align)
        sh = Image.new("RGBA", size, (0, 0, 0, 170))
        sh.putalpha(m.filter(ImageFilter.GaussianBlur(8)).point(lambda v: v * 170 // 255))
        layer.alpha_composite(sh)
    for width, color in strokes:
        m = Image.new("L", size, 0)
        ImageDraw.Draw(m).multiline_text(org, text, font=fnt, fill=255, stroke_width=width,
                                         stroke_fill=255, spacing=spacing, align=align)
        c = Image.new("RGBA", size, color + (255,))
        c.putalpha(m)
        layer.alpha_composite(c)
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).multiline_text(org, text, font=fnt, fill=255, spacing=spacing, align=align)
    body = gradient(size, *fill).convert("RGBA") if isinstance(fill[0], tuple) else Image.new("RGBA", size, fill + (255,))
    body.putalpha(m)
    layer.alpha_composite(body)
    return layer


def paste(canvas, layer, xy, anchor="lt", rotate=0):
    if rotate:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
    x, y = xy
    if anchor[0] == "m": x -= layer.width // 2
    if anchor[0] == "r": x -= layer.width
    if anchor[1] == "m": y -= layer.height // 2
    if anchor[1] == "b": y -= layer.height
    canvas.alpha_composite(layer, (int(x), int(y)))


def badge(text, diameter, bg=RED, fg=(255, 255, 255), size=58):
    d = diameter
    im = Image.new("RGBA", (d + 20, d + 20), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((10, 10, d + 10, d + 10), fill=(255, 255, 255, 255))
    dr.ellipse((18, 18, d + 2, d + 2), fill=bg + (255,))
    t = text_layer(text, font(DELA, size), fg, [(6, (120, 0, 0))], shadow=False, spacing=4, align="center")
    im.alpha_composite(t, ((im.width - t.width) // 2, (im.height - t.height) // 2))
    return im


def ribbon(text, size=44, bg=RED, fg=(255, 255, 255)):
    f = font(DELA, size)
    l, t, r, b = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    im = Image.new("RGBA", (r - l + 70, b - t + 34), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.polygon([(18, 0), (im.width, 0), (im.width - 18, im.height), (0, im.height)], fill=bg + (255,))
    dr.text((35 - l, 17 - t), text, font=f, fill=fg)
    return im


def burger(size, zoom=1.0, crop_center=(0.5, 0.52)):
    im = Image.open(A / "source" / "04_hero_burger.png").convert("RGB")
    s = int(im.width / zoom)
    cx, cy = int(im.width * crop_center[0]), int(im.height * crop_center[1])
    im = im.crop((max(cx - s // 2, 0), max(cy - s // 2, 0), min(cx + s // 2, im.width), min(cy + s // 2, im.height)))
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.18)).enhance(1.08)
    return im.resize(size, Image.LANCZOS).convert("RGBA")


def feather(layer, left=0, right=0, top=0, bottom=0):
    """レイヤーの端をグラデーションで透明にして背景となじませる（継ぎ目対策）。"""
    w, h = layer.size
    m = Image.new("L", (w, h), 255)
    px = m.load()
    for x in range(w):
        for y in range(h):
            v = 1.0
            if left and x < left: v = min(v, x / left)
            if right and x > w - right: v = min(v, (w - x) / right)
            if top and y < top: v = min(v, y / top)
            if bottom and y > h - bottom: v = min(v, (h - y) / bottom)
            px[x, y] = int(255 * v)
    layer.putalpha(m)
    return layer


def host_upper(height):
    im = Image.open(A / "panels" / "host_cutout.png")
    im = im.crop((0, 0, im.width, int(im.height * 0.47)))  # 頭〜腰
    im = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(1.04)
    # 白フチ(人物を背景から浮かせる)
    a = im.getchannel("A").filter(ImageFilter.MaxFilter(13))
    rim = Image.new("RGBA", im.size, (255, 255, 255, 0))
    rim.putalpha(a)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(rim)
    out.alpha_composite(im)
    return out


def dark_bg():
    bg = burger((W, W)).crop((0, 280, W, 280 + H)).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    return bg


def vignette(canvas, strength=150):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((-200, -160, W + 200, H + 160), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, strength))
    dark.putalpha(m.point(lambda v: (255 - v) * strength // 255))
    canvas.alpha_composite(dark)


def thumb_a():
    c = dark_bg()
    c.alpha_composite(feather(burger((820, 820), zoom=1.08), left=160), (470, -40))
    vignette(c)
    c.alpha_composite(host_upper(700), (-10, 40))
    paste(c, ribbon("焼肉屋が本気で作った", 50), (455, 30), rotate=3)
    main = text_layer("ライスバーガー", font(DELA, 132), YELLOW, [(26, BLACK), (14, RED), (5, (255, 255, 255))])
    paste(c, main, (W // 2 + 170, H + 18), anchor="mb", rotate=3)
    paste(c, badge("黄身\nとろ〜り", 230, size=50), (W - 10, 70), anchor="rt", rotate=-8)
    return c


def thumb_b():
    c = dark_bg()
    c.alpha_composite(feather(burger((860, 860), zoom=1.12), right=180), (-150, -40))
    vignette(c, 120)
    host = host_upper(640)
    c.alpha_composite(host, (W - host.width + 30, H - host.height))
    l1 = text_layer("ごはんで挟む！", font(DELA, 92), (255, 255, 255), [(20, BLACK), (8, RED)])
    l2 = text_layer("焼肉バーガー", font(DELA, 124), YELLOW, [(26, BLACK), (14, RED), (5, (255, 255, 255))])
    paste(c, l1, (30, 10), rotate=4)
    paste(c, l2, (10, H + 20), anchor="lb", rotate=4)
    paste(c, badge("フライパン\n1つで", 210, bg=(20, 20, 20), size=34), (705, 70), rotate=8)
    return c


def thumb_c():
    c = burger((W, W), zoom=1.02, crop_center=(0.5, 0.5)).crop((0, 150, W, 150 + H))
    vignette(c, 170)
    l1 = text_layer("黄身とろ〜り", font(DELA, 150), YELLOW, [(28, BLACK), (15, RED), (6, (255, 255, 255))])
    paste(c, l1, (W // 2, H + 20), anchor="mb", rotate=-2)
    paste(c, ribbon("焼肉屋の本気ライスバーガー", 46), (20, 24), rotate=-2)
    paste(c, badge("お家で\nトラジ", 210, size=46), (W - 14, 18), anchor="rt", rotate=8)
    return c


def save(img, name):
    p = OUT / name
    img.convert("RGB").save(p, quality=92, optimize=True)
    return p, None


if __name__ == "__main__":
    results = [save(thumb_a(), "thumbnail_A.jpg"), save(thumb_b(), "thumbnail_B.jpg"), save(thumb_c(), "thumbnail_C.jpg")]
    # 比較シート: 2x2 の左上/右上/左下 = A/B/C、右下 = 検索結果サイズ(196x110)での見え方
    cw, ch = W // 2 - 20, (W // 2 - 20) * 9 // 16
    sheet = Image.new("RGB", (W, ch * 2 + 30), (245, 245, 245))
    for i, (p, _) in enumerate(results):
        sheet.paste(Image.open(p).resize((cw, ch), Image.LANCZOS), ((i % 2) * (W // 2) + 10, (i // 2) * (ch + 10) + 10))
    for i, (p, _) in enumerate(results):
        sheet.paste(Image.open(p).resize((196, 110), Image.LANCZOS), (W // 2 + 10 + i * 206, ch + 20 + (ch - 110) // 2))
    sheet.save(OUT / "thumbnail_compare.jpg", quality=88)
    for p, _ in results:
        print(p.name, p.stat().st_size, "bytes")
