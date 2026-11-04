#!/usr/bin/env python3
"""Find the first chorus in a song and print a clip window (start, duration).

Approach: the chorus is the section that repeats most clearly later in the song
and is usually louder than the verse. We score every candidate start (on beats)
by how well a ~16 s window matches a later part of the song (chroma
self-similarity), weighted by loudness, then take the earliest strong match.
The clip starts a little before that (about two lyric lines, ~4 bars) and runs
through the chorus plus a bit of what follows, capped under one minute.

Usage: choose_clip.py AUDIO [--max 55] [--json]
"""
import argparse, json, sys
import numpy as np
import librosa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--max", type=float, default=55.0, help="max clip length in seconds")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    y, sr = librosa.load(a.audio, sr=22050, mono=True)
    dur = len(y) / sr
    hop = 512
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    tempo = float(np.atleast_1d(tempo)[0]) or 100.0
    beat_t = librosa.frames_to_time(beats, sr=sr, hop_length=hop)
    bar = 4 * 60.0 / tempo

    # Beat-synchronous features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    cs = librosa.util.sync(chroma, beats, aggregate=np.median)
    rs = librosa.util.sync(rms[np.newaxis, :], beats, aggregate=np.mean)[0]
    cs = librosa.util.normalize(cs, axis=0)
    n = cs.shape[1]
    sim = cs.T @ cs  # beat x beat cosine similarity

    win = max(8, int(round(16.0 / (60.0 / tempo))))  # ~16 s in beats
    min_lag = win  # repeat must come at least one window later
    energy = (rs - rs.min()) / (rs.max() - rs.min() + 1e-9)

    scores = np.zeros(n)
    for i in range(n - win):
        t0 = beat_t[i] if i < len(beat_t) else 0
        if t0 < 15.0 or t0 > 0.6 * dur:
            continue
        best = 0.0
        for j in range(i + min_lag, n - win):
            d = np.mean([sim[i + k, j + k] for k in range(win)])
            if d > best:
                best = d
        e = float(np.mean(energy[i:i + win]))
        scores[i] = best * (0.6 + 0.4 * e)

    if scores.max() <= 0:
        chorus = 0.25 * dur
        method = "fallback"
    else:
        thr = 0.92 * scores.max()
        idx = int(np.argmax(scores >= thr))
        chorus = float(beat_t[idx])
        method = "repetition"
        # Refine: a chorus usually lifts in loudness (drums/bass come in).
        # Look for the strongest loudness step within -4..+8 s of the estimate.
        rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
        sm = np.convolve(rms, np.ones(43) / 43, mode="same")  # ~1 s smoothing
        best_step, best_t = 0.0, None
        for bt in beat_t[(beat_t >= chorus - 4) & (beat_t <= chorus + 8)]:
            before = sm[(rt >= bt - 4) & (rt < bt)].mean()
            after = sm[(rt >= bt) & (rt < bt + 4)].mean()
            step = (after - before) / (before + 1e-9)
            if step > best_step:
                best_step, best_t = step, float(bt)
        if best_t is not None and best_step > 0.15:
            chorus = best_t
            method = "repetition+lift"

    lead = min(max(4 * bar, 6.0), 12.0)  # about two lyric lines before the chorus
    start = max(0.0, chorus - lead)
    # snap start to the nearest beat at or before it
    prior = beat_t[beat_t <= start]
    if len(prior):
        start = float(prior[-1])
    length = min(a.max, dur - start)
    # end on a bar boundary
    bars = int(length // bar)
    if bars >= 8:
        length = round(bars * bar, 2)
    out = {"duration": round(dur, 2), "tempo": round(tempo, 1), "chorus": round(chorus, 2),
           "start": round(start, 2), "length": round(length, 2), "method": method}
    print(json.dumps(out) if a.json else f"{out['start']} {out['length']}")


if __name__ == "__main__":
    sys.exit(main())
