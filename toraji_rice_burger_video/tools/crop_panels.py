"""ストーリーボード2枚からパネルを1枚ずつ切り出す。

出力: assets/panels/sb22_01.png ... sb22_22.png / sb12_01.png ... sb12_12.png
キャプション帯（パネル下部の文字）は除外して、映像部分だけを切り出す。
グリッド座標は元画像の区切り線を画素解析して特定した値。
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "source"
OUT = ROOT / "assets" / "panels"
OUT.mkdir(parents=True, exist_ok=True)

# 02_storyboard_22.jpg (935x1683)  区切り線: 行 96/344/569/798/1055/1327, 列 237/466/698
SB22_ROWS = [(97, 344), (345, 569), (570, 798), (799, 1055), (1056, 1327)]
SB22_COLS = [(0, 237), (238, 466), (467, 698), (699, 935)]
SB22_CAPTION = 58  # 下部キャプション帯の高さ(px)
SB22_BADGE = 34    # 左上の番号バッジを避けるため上端を削る量(px)

# 03_storyboard_12.png (1224x1285)  区切り線: 行 76/354/634/919, 列 408/816
SB12_ROWS = [(77, 354), (355, 634), (635, 919), (920, 1285)]
SB12_COLS = [(0, 408), (409, 816), (817, 1224)]
SB12_CAPTION = 70
SB12_BADGE = 46


def crop_grid(src, rows, cols, caption, badge, prefix, extra=None):
    im = Image.open(src).convert("RGB")
    n = 0
    for (y0, y1) in rows:
        for (x0, x1) in cols:
            n += 1
            im.crop((x0 + 2, y0 + badge, x1 - 2, y1 - caption)).save(OUT / f"{prefix}_{n:02d}.png")
    for box in extra or []:
        n += 1
        x0, y0, x1, y1, cap = box
        im.crop((x0 + 2, y0 + badge, x1 - 2, y1 - cap)).save(OUT / f"{prefix}_{n:02d}.png")
    return n


if __name__ == "__main__":
    # 最下段は2コマ（21=ワックスペーパー / 22=エンド）で幅が違う
    n22 = crop_grid(SRC / "02_storyboard_22.jpg", SB22_ROWS, SB22_COLS, SB22_CAPTION, SB22_BADGE, "sb22",
                    extra=[(0, 1328, 296, 1683, 80), (297, 1328, 935, 1683, 62)])
    n12 = crop_grid(SRC / "03_storyboard_12.png", SB12_ROWS, SB12_COLS, SB12_CAPTION, SB12_BADGE, "sb12")
    print(f"sb22: {n22} panels / sb12: {n12} panels -> {OUT}")
