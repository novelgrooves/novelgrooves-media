#!/usr/bin/env python3
"""One-shot long-form builder. Usage: make_longform.py spec.json
spec: {slug, folder, image, mode: snow|glow|rain, repeats, xfade, order(optional list of names),
       title, intro (list of paragraphs), credit, hashtags, thumb_title, thumb_sub, kids(bool), outname}
Tracks: *_01.wav in folder, else plain *.wav (no .pkf-only check). Originals first, then alternates."""
import json, sys, os, glob, math, subprocess, random
from PIL import Image, ImageDraw, ImageFont
S = json.load(open(sys.argv[1]))
T = os.path.dirname(os.path.abspath(__file__))
W = f"/home/claude/lf/{S['slug']}"; os.makedirs(W, exist_ok=True); os.chdir(W)
def run(*a): subprocess.check_call(list(a))
fs = sorted(glob.glob(os.path.join(S["folder"], "*_01.wav"))) or sorted(f for f in glob.glob(os.path.join(S["folder"], "*.wav")))
def name(f): return os.path.basename(f).replace("_01.wav", "").replace(".wav", "")
orig = [f for f in fs if "(Alternate Version)" not in f]; alt = [f for f in fs if "(Alternate Version)" in f]
random.Random(3).shuffle(alt)
rows = [f"{f}|{name(f)}" for f in orig + alt]
open("tracks.txt", "w").write("\n".join(rows) + "\n")
run("python3", f"{T}/playlist_mix.py", "tracks.txt", "mix1.m4a", "chapters.json", str(S.get("xfade", 3)))
rep = S.get("repeats", 1)
open("al.txt", "w").write("".join("file 'mix1.m4a'\n" for _ in range(rep)))
run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "al.txt", "-c", "copy", "mix.m4a")
script = {"snow": "snow_loop.py", "glow": "glow_loop.py", "rain": "rain_loop.py"}[S["mode"]]
run("python3", f"{T}/{script}", S["image"], "loop_hq.mp4", "18")
run("ffmpeg", "-y", "-loglevel", "error", "-i", "loop_hq.mp4", "-c:v", "libx265", "-preset", "medium", "-crf", str(S.get("crf", 27)),
    "-x265-params", "keyint=600:min-keyint=600:log-level=error", "-tag:v", "hvc1", "-pix_fmt", "yuv420p", "loop.mp4")
c = json.load(open("chapters.json")); one = c["total"]; total = one * rep
open("list.txt", "w").write("".join("file 'loop.mp4'\n" for _ in range(math.ceil(total / 20) + 1)))
run("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-i", "mix.m4a", "-map", "0:v", "-map", "1:a",
    "-c", "copy", "-shortest", "-movflags", "+faststart", "video.mp4")
run("ffmpeg", "-y", "-loglevel", "error", "-ss", "8", "-i", "loop_hq.mp4", "-frames:v", "1", "f.png")
run("ffmpeg", "-y", "-loglevel", "error", "-ss", "400", "-t", "25", "-i", "video.mp4", "-c", "copy", "preview.mp4")
def ts(s):
    s = int(round(s)); h, m = divmod(s, 3600); m, s = divmod(m, 60)
    return f"{m}:{s:02d}" if not h else f"{h}:{m:02d}:{s:02d}"
ch = c["chapters"] + [[one * k, f"Play-through {k+1}: {c['chapters'][0][1]}"] for k in range(1, rep)]
tl = "\n".join(f"{ts(t)} {n}" for t, n in ch)
desc = "\n\n".join(S["intro"]) + f"\n\nTracklist\n{tl}\n\n{S['credit']}\nMore at novelgrooves.com\n\n{S['hashtags']}\n"
assert "—" not in desc
head = f"Title: {S['title']}\n\nDoelgroep: {'Ja, gemaakt voor kinderen' if S.get('kids') else 'Nee, niet gemaakt voor kinderen'}. Label gewijzigde content: Nee. Zichtbaarheid: Openbaar.\n\n"
open("youtube-titel-en-beschrijving.txt", "w").write(head + desc)
im = Image.open("f.png").resize((1280, 720), Image.LANCZOS).convert("RGBA")
ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
for y in range(260): d.line([(0, y), (1280, y)], fill=(10, 12, 35, int(150 * (1 - y / 260))))
im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
F = "/usr/share/fonts/truetype/google-fonts/"
f1 = ImageFont.truetype(F + "Poppins-Bold.ttf", 80)
while d.textlength(S["thumb_title"], font=f1) > 1180: f1 = ImageFont.truetype(F + "Poppins-Bold.ttf", f1.size - 4)
for txt, f, y in [(S["thumb_title"], f1, 40), (S["thumb_sub"], ImageFont.truetype(F + "Poppins-Medium.ttf", 40), 145)]:
    w = d.textlength(txt, font=f); d.text(((1280 - w) / 2, y), txt, font=f, fill=(255, 248, 236), stroke_width=3, stroke_fill=(20, 20, 50))
im.convert("RGB").save("thumbnail.jpg", quality=92)
O = f"/mnt/user-data/outputs/{S['slug']}"; os.makedirs(O, exist_ok=True)
run("split", "-b", "20000000", "-d", "-a", "2", f"{W}/video.mp4", f"{O}/part")
parts = sorted(p for p in os.listdir(O) if p.startswith("part"))
out = S["outname"]
open(f"{O}/samenvoegen.bat", "w", newline="").write(
    f'@echo off\r\ncd /d "%~dp0"\r\ncopy /b {"+".join(parts)} "{out}.mp4"\r\nif exist "{out}.mp4" del part*\r\necho Klaar.\r\npause\r\n')
for f in ["thumbnail.jpg", "youtube-titel-en-beschrijving.txt", "preview.mp4"]: run("cp", f, O)
print(json.dumps({"slug": S["slug"], "parts": len(parts), "minutes": round(total / 60, 1), "bytes": os.path.getsize("video.mp4")}))
