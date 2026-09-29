"""BGM + 効果音をゼロから合成する（外部素材なし＝著作権フリー）。
120BPM / Aマイナー / 53秒。build_video.py のタイムラインと同期している。
出力: output/bgm.wav
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import os

SR = 44100
BPM = 120
BEAT = 60 / BPM          # 0.5s
BAR = BEAT * 4           # 2.0s
DUR = 53.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

# ---- タイムライン（build_video.py と共通） ----
HOOK_END = 3.0
REVEAL_END = 7.0
CASE_LEN = 8.0
CASE_SPLIT = 5.0
CASE_STARTS = [REVEAL_END + i * CASE_LEN for i in range(5)]   # 7,15,23,31,39
OUTRO = CASE_STARTS[-1] + CASE_LEN                            # 47

L = np.zeros(N)
R = np.zeros(N)


def t_arr(d):
    return np.arange(int(SR * d)) / SR


def add(x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    x = x[: N - i]
    lg = gain * np.sqrt(0.5 * (1 - pan))
    rg = gain * np.sqrt(0.5 * (1 + pan))
    L[i:i + len(x)] += x * lg
    R[i:i + len(x)] += x * rg


def env(d, a=0.005, dec=0.2):
    t = t_arr(d)
    e = np.exp(-t / dec)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def lp(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR / 2 - 100) / (SR / 2), "low", output="sos")
    return signal.sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc / (SR / 2), "high", output="sos")
    return signal.sosfilt(sos, x)


def bp(x, lo, hi):
    sos = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos")
    return signal.sosfilt(sos, x)


def saw(f, d, detune=0.0):
    t = t_arr(d)
    out = np.zeros_like(t)
    for k in (-detune, 0, detune) if detune else (0,):
        ff = f * (1 + k)
        out += 2 * ((t * ff + rng.random()) % 1.0) - 1
    return out / (3 if detune else 1)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ---- 音色 ----
def kick():
    d = 0.45
    t = t_arr(d)
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 0.18)
    x += 0.4 * lp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.004)
    return np.tanh(1.6 * x)


def clap():
    d = 0.35
    t = t_arr(d)
    n = bp(rng.standard_normal(len(t)), 900, 5000)
    e = np.exp(-t / 0.12)
    for off in (0.0, 0.011, 0.022):
        i = int(off * SR)
        e[i:i + 200] += 0.8
    return n * e * 0.6


def hat(open_=False):
    d = 0.3 if open_ else 0.06
    t = t_arr(d)
    n = hp(rng.standard_normal(len(t)), 7000)
    return n * np.exp(-t / (0.09 if open_ else 0.015))


def tick():
    d = 0.05
    t = t_arr(d)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.008) + 0.3 * hp(rng.standard_normal(len(t)), 5000) * np.exp(-t / 0.004)


def snare():
    d = 0.2
    t = t_arr(d)
    n = bp(rng.standard_normal(len(t)), 1500, 8000) * np.exp(-t / 0.06)
    b = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04)
    return 0.7 * n + 0.5 * b


def crash():
    d = 2.5
    t = t_arr(d)
    n = hp(rng.standard_normal(len(t)), 4000)
    return n * np.exp(-t / 0.7) * 0.5


def impact():
    d = 2.5
    t = t_arr(d)
    f = 30 + 70 * np.exp(-t / 0.08)
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = np.sin(ph) * np.exp(-t / 0.9)
    n = lp(rng.standard_normal(len(t)), 1800) * np.exp(-t / 0.35)
    return np.tanh(1.8 * (boom + 0.5 * n))


def whoosh(d=0.6, up=True):
    t = t_arr(d)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = 512
    for i in range(0, len(n), seg):
        p = i / len(n)
        fc = 300 + (6000 if up else 6000 * (1 - p)) * (p if up else 1)
        out[i:i + seg] = bp(n[max(0, i - 2048):i + seg], max(80, fc * 0.5), min(18000, fc * 1.5))[-len(n[i:i + seg]):]
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return out * e * 0.9


def riser(d):
    t = t_arr(d)
    f = 200 * 2 ** (3 * t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sign(np.sin(ph)) * 0.15 + np.sin(ph * 1.5) * 0.1
    n = rng.standard_normal(len(t))
    nn = np.zeros_like(n)
    seg = 1024
    for i in range(0, len(n), seg):
        fc = 400 + 9000 * (i / len(n)) ** 2
        nn[i:i + seg] = bp(n[max(0, i - 4096):i + seg], fc * 0.6, min(19000, fc * 1.4))[-len(n[i:i + seg]):]
    e = (t / d) ** 2
    return (tone + 0.8 * nn) * e


def pluck(f, d=0.25):
    t = t_arr(d)
    x = saw(f, d, 0.004)
    x = lp(x, 2500) * np.exp(-t / 0.09)
    return x


def pad(notes, d, cutoff=1800):
    t = t_arr(d)
    x = sum(saw(midi(n), d, 0.006) for n in notes) / len(notes)
    x = lp(x, cutoff, 2)
    a = np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.3)
    return x * a


def sub(f, d):
    t = t_arr(d)
    x = np.sin(2 * np.pi * f * t) + 0.3 * lp(saw(f, d), 400)
    return x * np.minimum(1, (d - t) / 0.02) * np.minimum(1, t / 0.005)


# Am - F - C - G （ルートMIDI, 構成音）
PROG = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]

K, C, HC, HO, S, T = kick(), clap(), hat(), hat(True), snare(), tick()

# ===== HOOK 0-3s：時計のチクタク＋こもったパッド＋ライザー =====
for i in range(6):
    add(T, i * BEAT, 0.5, pan=0.3 if i % 2 else -0.3)
add(lp(pad([57, 60, 64], 3.0), 700), 0.0, 0.35)
add(riser(1.9), 1.05, 0.55)
roll = [2.0 + k * 0.125 for k in range(4)] + [2.5 + k * 0.0625 for k in range(6)]
for k, at in enumerate(roll):
    add(S, at, 0.15 + 0.04 * k)
add(whoosh(0.5), 2.45, 0.5)

# ===== ドロップ 3s〜：本編ビート =====
add(impact(), HOOK_END, 1.0)
add(crash(), HOOK_END, 0.6)

beat_end = OUTRO + 4.0
nb = int((beat_end - HOOK_END) / BEAT)
for b in range(nb):
    at = HOOK_END + b * BEAT
    bar = int((at - HOOK_END) // BAR)
    beat_in_bar = b % 4
    root, chord = PROG[bar % 4]
    in_outro = at >= OUTRO
    add(K, at, 0.9)
    if beat_in_bar in (1, 3):
        add(C, at, 0.55)
    add(HC, at + BEAT / 2, 0.22, pan=0.2)
    add(HC, at + BEAT * 0.25, 0.08, pan=-0.2)
    add(HC, at + BEAT * 0.75, 0.08, pan=-0.2)
    if beat_in_bar == 3:
        add(HO, at + BEAT / 2, 0.15, pan=0.3)
    # サブベース（8分）
    for h in range(2):
        add(sub(midi(root), BEAT / 2 * 0.9), at + h * BEAT / 2, 0.35)
    # アルペジオ（16分）
    if not in_outro:
        arp = chord + [chord[0] + 12]
        for s in range(4):
            n = arp[(b * 4 + s) % 4] + 12
            add(pluck(midi(n)), at + s * BEAT / 4, 0.10, pan=0.4 if s % 2 else -0.4)

# パッド（小節ごと）
for bar in range(int((beat_end - HOOK_END) / BAR)):
    at = HOOK_END + bar * BAR
    root, chord = PROG[bar % 4]
    add(pad(chord, BAR + 0.1, 2200), at, 0.18)

# ケース切替ごとのフィル＋ウーシュ＋クラッシュ
for cs in CASE_STARTS + [OUTRO]:
    add(whoosh(0.6), cs - 0.55, 0.55)
    add(crash(), cs, 0.35)
    for k in range(4):
        add(S, cs - BEAT + k * BEAT / 4, 0.18 + 0.05 * k)
# ハイライト切替（split→zoom）で短いウーシュ
for cs in CASE_STARTS:
    add(whoosh(0.35), cs + CASE_SPLIT - 0.3, 0.35)

# ===== OUTRO 47s〜：インパクト→余韻 =====
add(impact(), OUTRO, 0.8)
add(pad([57, 60, 64, 69], 6.0, 1500), OUTRO, 0.3)
add(impact(), OUTRO + 4.0, 0.9)
add(crash(), OUTRO + 4.0, 0.5)

# ===== ミックス：リバーブ・マスタリング =====
def reverb(x, sec=1.6, mix=0.18):
    t = t_arr(sec)
    ir = rng.standard_normal(len(t)) * np.exp(-t / (sec / 5))
    ir = lp(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = signal.fftconvolve(x, ir)[: len(x)]
    return x + mix * wet

L2, R2 = reverb(L), reverb(R)
mix = np.stack([L2, R2], axis=1)
mix = hp(mix.T, 25).T
# 軽いサイドチェーン風：キックに合わせて全体をダッキング（ドロップ以降）
duck = np.ones(N)
for b in range(nb):
    i = int((HOOK_END + b * BEAT) * SR)
    seg = np.linspace(0.65, 1.0, int(0.18 * SR))
    duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg[: len(duck[i:i + len(seg)])])
mix *= duck[:, None]
# 終端フェード
fade = int(1.2 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
# ソフトリミッター
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(1.5 * mix) / np.tanh(1.5)
mix *= 0.89  # ≒ -1dBFS
os.makedirs("output", exist_ok=True)
wavfile.write("output/bgm.wav", SR, (mix * 32767).astype(np.int16))
print("wrote output/bgm.wav", mix.shape[0] / SR, "s")
