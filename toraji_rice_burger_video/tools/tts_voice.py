"""ソアちゃんのナレーションを全シーン分生成する（無料・ローカル実行・APIキー不要）。

エンジン:
  sbv2   … Style-Bert-VITS2 / JVNVコーパスモデル F1（CC BY-SA 4.0：クレジット表記が必要）  ← 比較用
  kokoro … Kokoro-82M / jf_alpha（Apache 2.0）                                          ← 採用（Whisper聞き取り精度 平均91.4% vs sbv2 89.0%）
使い方: python tools/tts_voice.py [kokoro|sbv2] [scenes.json内のキー(既定: scenes)]
出力:   work/voice_<engine>/<ID>.wav（44.1kHz mono）
読み補正は scenes.json の tts_readings を上から順に適用（字幕・台本は漢字のまま）。
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
SR = 44100

SBV2_REPO = "litagin/style_bert_vits2_jvnv"
SBV2_DIR, SBV2_WEIGHTS = "jvnv-F1-jp", "jvnv-F1-jp_e160_s14000.safetensors"
SBV2_STYLE, SBV2_STYLE_WEIGHT = "Happy", 1.5   # 明るく元気な話し方
SBV2_LENGTH = 0.92                              # 1未満で速く（料理動画のテンポ）
SBV2_PITCH = 1.0


def apply_readings(text, readings):
    for a, b in readings:
        text = text.replace(a, b)
    return text


def load_sbv2():
    from huggingface_hub import hf_hub_download
    from style_bert_vits2.constants import Languages
    from style_bert_vits2.nlp import bert_models
    from style_bert_vits2.tts_model import TTSModel
    bert = "ku-nlp/deberta-v2-large-japanese-char-wwm"
    # 新しい transformers は重みを float16 のまま読むことがあり、CPU推論で型エラーになるため float32 に揃える
    bert_models.load_model(Languages.JP, bert).float()
    bert_models.load_tokenizer(Languages.JP, bert)
    model = TTSModel(model_path=hf_hub_download(SBV2_REPO, f"{SBV2_DIR}/{SBV2_WEIGHTS}"),
                     config_path=hf_hub_download(SBV2_REPO, f"{SBV2_DIR}/config.json"),
                     style_vec_path=hf_hub_download(SBV2_REPO, f"{SBV2_DIR}/style_vectors.npy"), device="cpu")

    def synth(text):
        sr, a = model.infer(text=text, style=SBV2_STYLE, style_weight=SBV2_STYLE_WEIGHT,
                            length=SBV2_LENGTH, pitch_scale=SBV2_PITCH)
        a = a.astype(np.float32) / (32768.0 if a.dtype == np.int16 else 1.0)
        return resample(a, sr)
    return synth


def load_kokoro():
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="j", repo_id="hexgrad/Kokoro-82M")

    def synth(text):
        a = np.concatenate([r.audio.numpy() for r in pipe(text, voice="jf_alpha", speed=1.05)])
        return resample(a, 24000)
    return synth


def resample(a, sr):
    if sr == SR:
        return a
    t_old = np.arange(len(a)) / sr
    t_new = np.arange(int(len(a) * SR / sr)) / SR
    return np.interp(t_new, t_old, a).astype(np.float32)


def trim_and_normalize(a, peak_db=-1.5):
    thr = 0.01 * np.max(np.abs(a))
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx):
        a = a[max(idx[0] - int(0.03 * SR), 0): idx[-1] + int(0.08 * SR)]
    return a * (10 ** (peak_db / 20) / max(np.max(np.abs(a)), 1e-6))


def main():
    engine = sys.argv[1] if len(sys.argv) > 1 else "kokoro"
    key = sys.argv[2] if len(sys.argv) > 2 else "scenes"
    cfg = json.loads((ROOT / "tools" / "scenes.json").read_text(encoding="utf-8"))
    out = ROOT / "work" / f"voice_{engine}"
    out.mkdir(parents=True, exist_ok=True)
    synth = load_sbv2() if engine == "sbv2" else load_kokoro()
    for sc in cfg[key]:
        text = apply_readings(sc["narr"], cfg["tts_readings"])
        a = trim_and_normalize(synth(text))
        sf.write(out / f"{sc['id']}.wav", a, SR)
        print(sc["id"], f"{len(a) / SR:.2f}s", text)


if __name__ == "__main__":
    main()
