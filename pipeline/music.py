"""저작권 걱정 없는 배경음악을 코드로 직접 작곡 (로파이 피아노 + 가벼운 비트).
seed가 다르면 아르페지오·코드 진행이 조금씩 달라짐."""
import numpy as np, wave

SR = 44100
PROGRESSIONS = [
    [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],  # Fmaj7 Em7 Dm7 Cmaj7
    [[48, 52, 55, 59], [45, 48, 52, 55], [53, 57, 60, 64], [55, 59, 62, 65]],  # Cmaj7 Am7 Fmaj7 G7
    [[45, 48, 52, 55], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]],  # Am7 Fmaj7 Cmaj7 G7
]


def make(out_path, dur, seed=7, bpm=84):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bar = beat * 4
    N = int(SR * dur)
    out = np.zeros(N)
    chords = PROGRESSIONS[seed % len(PROGRESSIONS)]

    def note(m): return 440 * 2 ** ((m - 69) / 12)

    def env(n, a, r):
        e = np.ones(n); ai, ri = max(1, int(a * SR)), max(1, int(r * SR))
        e[:ai] = np.linspace(0, 1, ai); e[-ri:] *= np.linspace(1, 0, ri)
        return e

    def add(sig, start):
        s = int(start * SR)
        if s >= N: return
        e = min(N, s + len(sig)); out[s:e] += sig[: e - s]

    t, ci = 0.0, 0
    while t < dur:
        ch = chords[ci % 4]; L = bar * 2
        n = int(L * SR); tt = np.arange(n) / SR
        pad = sum(np.sin(2 * np.pi * note(m) * tt) * 0.6 + np.sin(2 * np.pi * note(m) * 2.003 * tt) * 0.15 for m in ch)
        add(pad * env(n, 0.6, 0.8) * 0.045 * (1 + 0.15 * np.sin(2 * np.pi * 0.5 * tt)), t)
        bn = int(bar * SR); bt = np.arange(bn) / SR
        for k in range(2):
            add(np.sin(2 * np.pi * note(ch[0] - 12) * bt) * env(bn, 0.02, 0.5) * 0.16, t + k * bar)
        pat = [0, 2, 1, 3, 2, 1, 3, 2]
        for k in range(16):
            if rng.random() < 0.18: continue
            m = ch[pat[k % 8]] + 12
            pn = int(beat * 1.5 * SR); pt = np.arange(pn) / SR
            add((np.sin(2 * np.pi * note(m) * pt) + 0.3 * np.sin(4 * np.pi * note(m) * pt)) * np.exp(-pt * 3.5) * 0.07,
                t + k * beat / 2 + rng.uniform(0, 0.015))
        t += L; ci += 1

    kn = int(0.35 * SR); kt = np.arange(kn) / SR
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 9) * 0.32
    sn = int(0.25 * SR); st = np.arange(sn) / SR
    snare = (rng.normal(0, 1, sn) * 0.5 + np.sin(2 * np.pi * 190 * st)) * np.exp(-st * 18) * 0.07
    hn = int(0.06 * SR); ht = np.arange(hn) / SR
    hat = np.diff(rng.normal(0, 1, hn + 1)) * np.exp(-ht * 70) * 0.025
    b, t = 0, bar
    while t < dur:
        if b % 4 in (0, 2): add(kick, t)
        if b % 4 in (1, 3): add(snare, t + 0.01)
        add(hat, t); add(hat * 0.6, t + beat / 2)
        t += beat; b += 1

    out += rng.normal(0, 1, N) * 0.0035
    fi, fo = int(0.8 * SR), int(min(2.0, dur / 4) * SR)
    out[:fi] *= np.linspace(0, 1, fi); out[-fo:] *= np.linspace(1, 0, fo)
    out = out / np.max(np.abs(out)) * 0.7
    pcm = (np.stack([out, np.roll(out, 200)], axis=1) * 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
