"""主人公画像(白背景)から人物を切り抜いて透過PNGにする。

方法: 画像の外周から「ほぼ白」の画素を塗りつぶし(flood fill)して背景と判定。
肌や白い部分が人物の輪郭の内側にあれば消えない。腕と胴の間など閉じた白い隙間は
面積が小さく純白に近い領域だけ追加で背景扱いにする。
出力: assets/panels/host_cutout.png
※ 簡易処理。最終版は Photoshop / remove.bg / CapCut の「背景削除」で作り直すと髪の毛先がきれいになる。
"""
from collections import deque
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "source" / "01_host_girl.jpg"
OUT = ROOT / "assets" / "panels" / "host_cutout.png"

TOL = 34          # 背景の白(約245)からの許容差
POCKET_MIN = 238  # 閉じた隙間を背景とみなす明るさ下限


def is_bg(p, ref):
    return all(abs(c - r) <= TOL for c, r in zip(p, ref)) and min(p) >= 200


def main():
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    px = im.load()
    ref = px[5, 5]
    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.append((x, 0)); q.append((x, h - 1))
    for y in range(h):
        q.append((0, y)); q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        i = y * w + x
        if bg[i] or not is_bg(px[x, y], ref):
            continue
        bg[i] = 1
        if x > 0: q.append((x - 1, y))
        if x < w - 1: q.append((x + 1, y))
        if y > 0: q.append((x, y - 1))
        if y < h - 1: q.append((x, y + 1))

    # 閉じた白い隙間（腕と腰の間など）
    seen = bytearray(w * h)
    for sy in range(h):
        for sx in range(w):
            i = sy * w + sx
            if bg[i] or seen[i] or min(px[sx, sy]) < POCKET_MIN:
                continue
            region, q2 = [], deque([(sx, sy)])
            while q2:
                x, y = q2.popleft()
                j = y * w + x
                if seen[j] or bg[j] or min(px[x, y]) < POCKET_MIN:
                    continue
                seen[j] = 1
                region.append(j)
                if x > 0: q2.append((x - 1, y))
                if x < w - 1: q2.append((x + 1, y))
                if y > 0: q2.append((x, y - 1))
                if y < h - 1: q2.append((x, y + 1))
            if 400 < len(region) < 40000:
                for j in region:
                    bg[j] = 1

    mask = Image.frombytes("L", (w, h), bytes(0 if b else 255 for b in bg))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert("RGBA")
    out.putalpha(mask)
    out = out.crop(out.getbbox())
    out.save(OUT)
    print("saved", OUT, out.size)


if __name__ == "__main__":
    main()
