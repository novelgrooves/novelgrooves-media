#!/usr/bin/env python3
"""Crossfaded playlist from a track list. Usage: playlist_mix.py tracks.txt out.m4a chapters.json [xfade]
tracks.txt: one 'path|label' per line."""
import subprocess, json, sys
lst, out, chap = sys.argv[1:4]; XF = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
rows = [l.rstrip("\n").split("|") for l in open(lst) if l.strip()]
def dur(f): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f]))
ds = [dur(p) for p, _ in rows]
t = 0; chapters = []
for i, ((p, n), d) in enumerate(zip(rows, ds)):
    chapters.append((t, n)); t += d - (XF if i < len(ds) - 1 else 0)
inp = []
for p, _ in rows: inp += ["-i", p]
fc = ""; prev = "[0:a]"
for i in range(1, len(rows)):
    fc += f"{prev}[{i}:a]acrossfade=d={XF}:c1=tri:c2=tri[x{i}];"; prev = f"[x{i}]"
fc += f"{prev}afade=t=in:d=2,afade=t=out:st={t-4}:d=4,aresample=48000[a]"
subprocess.check_call(["ffmpeg","-y","-loglevel","error",*inp,"-filter_complex",fc,"-map","[a]","-c:a","aac","-b:a","192k",out])
json.dump({"total": t, "chapters": chapters}, open(chap, "w"), indent=1)
print(t)
