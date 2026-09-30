"""BGMと効果音をプログラムで合成する（著作権フリー・外部素材なし）。

BGM: 104BPM・ハ長調・C-G-Am-F の明るいウクレレ風ポップ（撥弦=Karplus-Strong、ベース、キック、クラップ、シェイカー、鉄琴）
効果音: 焼き音・炒め音・ポン・キラーン・シュッ・ドン・ザクッ 等（scenes.json の se 列のキーワードに対応）
出力: assets/audio/bgm_loop.wav, assets/audio/se_<name>.wav（44.1kHz mono）
"""
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "audio"
OUT.mkdir(parents=True, exist_ok=True)
SR = 44100
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def bp(x, lo=None, hi=None, order=2):
    if lo and hi:
        b, a = butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    elif lo:
        b, a = butter(order, lo / (SR / 2), "high")
    else:
        b, a = butter(order, hi / (SR / 2), "low")
    return lfilter(b, a, x)


def env(n, attack=0.005, release=None, curve=4.0):
    e = np.ones(n)
    na = max(int(attack * SR), 1)
    e[:na] = np.linspace(0, 1, na)
    if release is None:
        e[na:] = np.exp(-curve * np.linspace(0, 1, n - na))
    return e


def norm(x, peak=0.9):
    return x * peak / max(np.max(np.abs(x)), 1e-9)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ---------------- BGM ----------------
def pluck(freq, dur, bright=0.5):
    """Karplus-Strong 撥弦（ウクレレ風）。"""
    n = int(dur * SR)
    p = max(int(SR / freq), 2)
    buf = rng.uniform(-1, 1, p) * bright + bp(rng.uniform(-1, 1, p + 64), hi=4000)[:p] * (1 - bright)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out * env(n, 0.002, curve=3.0)


def bell(freq, dur):
    x = t(dur)
    s = np.sin(2 * np.pi * freq * x) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * x) + 0.15 * np.sin(2 * np.pi * freq * 5.4 * x)
    return s * env(len(x), 0.002, curve=6.0)


def make_bgm():
    bpm = 104
    beat = 60 / bpm
    bars = 8
    total = bars * 4 * beat
    n = int(total * SR)
    mix = np.zeros(n + SR * 3)   # 余韻は後で先頭に回して継ぎ目なくループさせる

    def add(sig, at, gain):
        i = int(at * SR)
        mix[i:i + len(sig)] += sig[: len(mix) - i] * gain

    # C - G - Am - F ×2（ボイシングはウクレレ風の中音域）
    chords = [[60, 64, 67, 72], [59, 62, 67, 71], [57, 60, 64, 69], [57, 60, 65, 69]] * 2
    roots = [48, 43, 45, 41] * 2
    strum = [(0, "D"), (1, "D"), (1.5, "U"), (2.5, "U"), (3, "D"), (3.5, "U")]
    cache = {}
    for b, (ch, root) in enumerate(zip(chords, roots)):
        t0 = b * 4 * beat
        for pos, d in strum:
            notes = ch if d == "D" else ch[::-1]
            for k, m in enumerate(notes):
                key = (m, d)
                if key not in cache:
                    cache[key] = pluck(midi(m), beat * 1.6, bright=0.6 if d == "D" else 0.4)
                add(cache[key], t0 + pos * beat + k * 0.012, 0.16 if d == "D" else 0.10)
        # ベース（1・3拍＋裏）
        for pos in (0, 2, 2.5):
            x = t(beat * 0.9)
            f = midi(root)
            s = np.tanh(2.0 * (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x))) * env(len(x), 0.004, curve=3)
            add(s, t0 + pos * beat, 0.30)
        # キック（1・3拍）
        for pos in (0, 2):
            x = t(0.25)
            f = 110 * np.exp(-x * 25) + 45
            add(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.001, curve=7), t0 + pos * beat, 0.45)
        # クラップ（2・4拍）
        for pos in (1, 3):
            s = bp(rng.uniform(-1, 1, int(0.12 * SR)), 900, 5000) * env(int(0.12 * SR), 0.001, curve=9)
            add(s, t0 + pos * beat, 0.30)
        # シェイカー（8分）
        for k in range(8):
            s = bp(rng.uniform(-1, 1, int(0.06 * SR)), lo=6000) * env(int(0.06 * SR), 0.01, curve=6)
            add(s, t0 + k * beat / 2, 0.10 if k % 2 else 0.06)
    # 鉄琴メロディ（後半4小節だけ。ペンタトニック）
    mel = [(0, 76), (1, 79), (2, 81), (3, 79), (4, 76), (6, 74), (8, 74), (9, 76), (10, 79), (12, 84), (13, 81), (14, 79)]
    for pos, m in mel:
        add(bell(midi(m), 1.2), 4 * 4 * beat + pos * beat, 0.10)
    # ループの継ぎ目処理：はみ出した余韻を先頭に足す
    tail = mix[n:]
    mix = mix[:n]
    mix[: len(tail)] += tail
    mix = bp(mix, lo=35)
    return norm(mix, 0.8)


# ---------------- 効果音 ----------------
def sizzle(dur=2.5):
    n = int(dur * SR)
    base = bp(rng.normal(0, 1, n), 2500, 11000) * 0.35
    crack = np.zeros(n)
    idx = rng.integers(0, n, int(dur * 180))
    crack[idx] = rng.uniform(0.5, 1.0, len(idx)) * rng.choice([-1, 1], len(idx))
    crack = bp(crack, lo=1500)
    e = np.minimum(1, np.minimum(np.arange(n) / (0.15 * SR), (n - np.arange(n)) / (0.4 * SR)))
    return norm((base + crack) * e, 0.7)


def stirfry():
    out = np.zeros(int(2.4 * SR))
    for k in range(3):
        s = sizzle(0.7) * np.linspace(1.3, 0.6, int(0.7 * SR))
        thud = bp(rng.normal(0, 1, int(0.08 * SR)), 80, 400) * env(int(0.08 * SR), 0.001, curve=8)
        i = int(k * 0.75 * SR)
        out[i:i + len(s)] += s
        out[i:i + len(thud)] += thud * 0.8
    return norm(out, 0.8)


def pop():
    x = t(0.12)
    f = 900 * np.exp(-x * 30) + 350
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.001, curve=10), 0.8)


def chime():
    out = np.zeros(int(1.4 * SR))
    for k, m in enumerate([84, 88, 91, 96]):
        s = bell(midi(m), 1.0)
        i = int(k * 0.06 * SR)
        out[i:i + len(s)] += s * (0.8 - k * 0.1)
    return norm(out, 0.6)


def whoosh(dur=0.5):
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    out = np.zeros(n)
    seg = n // 8
    for k in range(8):
        c = 600 + 3000 * (k / 7)
        out[k * seg:(k + 1) * seg] = bp(x, c * 0.6, c * 1.4)[k * seg:(k + 1) * seg]
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return norm(out * e, 0.6)


def impact():
    x = t(0.9)
    f = 80 * np.exp(-x * 6) + 38
    low = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.001, curve=4)
    hit = bp(rng.normal(0, 1, len(x)), 200, 3000) * env(len(x), 0.001, curve=14)
    return norm(low + 0.5 * hit, 0.85)


def crunch(n_bursts=5, dur=0.35):
    out = np.zeros(int(dur * SR))
    for k in range(n_bursts):
        b = bp(rng.normal(0, 1, int(0.03 * SR)), 1500, 9000) * env(int(0.03 * SR), 0.0005, curve=8)
        i = int(rng.uniform(0, dur - 0.04) * SR)
        out[i:i + len(b)] += b * rng.uniform(0.5, 1)
    return norm(out, 0.7)


def clink(hits=3):
    out = np.zeros(int(0.9 * SR))
    for k in range(hits):
        x = t(0.25)
        s = sum(np.sin(2 * np.pi * f * x) for f in (2700, 4100, 6300)) * env(len(x), 0.0005, curve=18)
        i = int(k * 0.22 * SR)
        out[i:i + len(s)] += s
    return norm(out, 0.5)


def beep():
    x = t(0.09)
    return norm(np.sin(2 * np.pi * 2000 * x) * np.minimum(1, (len(x) - np.arange(len(x))) / 200), 0.4)


def microwave():
    x = t(1.6)
    hum = (np.sin(2 * np.pi * 120 * x) + 0.4 * np.sin(2 * np.pi * 240 * x)) * 0.25
    ding = np.zeros_like(hum)
    b = bell(midi(93), 1.0)
    ding[int(1.0 * SR):int(1.0 * SR) + len(b)] = b[: len(ding) - int(1.0 * SR)]
    hum[int(1.0 * SR):] *= np.linspace(1, 0, len(hum) - int(1.0 * SR))
    return norm(hum + ding, 0.6)


def thud():
    x = t(0.3)
    return norm(bp(rng.normal(0, 1, len(x)), 60, 600) * env(len(x), 0.002, curve=10), 0.8)


def swish():
    return whoosh(0.25)


def splash():
    out = np.zeros(int(0.8 * SR))
    for k in range(12):
        b = bp(rng.normal(0, 1, int(0.05 * SR)), 800, 6000) * env(int(0.05 * SR), 0.001, curve=6)
        i = int(rng.uniform(0, 0.7) * SR)
        out[i:i + len(b)] += b * rng.uniform(0.3, 1)
    return norm(out, 0.5)


SE = {"sizzle": sizzle, "stirfry": stirfry, "pop": pop, "chime": chime, "whoosh": whoosh, "impact": impact,
      "crunch": crunch, "clink": clink, "beep": beep, "microwave": microwave, "thud": thud, "swish": swish,
      "splash": splash}

if __name__ == "__main__":
    sf.write(OUT / "bgm_loop.wav", make_bgm().astype(np.float32), SR)
    for name, fn in SE.items():
        sf.write(OUT / f"se_{name}.wav", fn().astype(np.float32), SR)
    print("bgm +", len(SE), "SE ->", OUT)
