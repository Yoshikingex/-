"""ストーリーボードの切り出しコマ(幅230〜630px)を Real-ESRGAN x4plus で4倍に高画質化する。

モデル: RealESRGAN_x4plus（BSD-3-Clause）を Hugging Face から取得し、spandrel で読み込んでCPU実行。
入力: assets/panels/sb22_*.png, sb12_*.png   出力: assets/panels_hd/同名.png
"""
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image, ImageFilter
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "panels"
OUT = ROOT / "assets" / "panels_hd"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    torch.set_num_threads(4)
    model = ModelLoader().load_from_file(hf_hub_download("lllyasviel/Annotators", "RealESRGAN_x4plus.pth"))
    model.eval()
    files = sorted(SRC.glob("sb*.png"))
    for f in files:
        dst = OUT / f.name
        if dst.exists():
            continue
        im = Image.open(f).convert("RGB")
        x = torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0).permute(2, 0, 1)[None]
        with torch.inference_mode():
            y = model(x).clamp(0, 1)[0].permute(1, 2, 0).numpy()
        out = Image.fromarray((y * 255).round().astype(np.uint8))
        # AI特有ののっぺり感を少し戻す（軽いシャープ＋粒状感）
        out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=40, threshold=2))
        out.save(dst)
        print(f.name, im.size, "->", out.size)
    print("done", len(files))


if __name__ == "__main__":
    main()
